import json
import os
import sys
import random
import requests
import time
import unittest
from nose.tools import *

sys.path.append(os.path.dirname(os.path.abspath(__file__)).rsplit('/', 1)[0])

import test_utilities, rabbitmq_utils, db_handler, app_settings
from chat import utils
from group_chat import errors, mqtt_subscriber, mqtt_publisher


class CreateGroupTests(unittest.TestCase):
    url = None
    data = {}
    users = None
    user1 = 911111111111
    user2 = 912222222222
    group_owner = None
    group_members = []

    def setUp(self):
        self.url = app_settings.CREATE_GROUP_URL
        test_utilities.delete_users()
        test_utilities.delete_groups()
        test_utilities.delete_group_messages()
        rabbitmq_utils.delete_exchanges(app_settings.RABBITMQ_EXCHANGES)
        rabbitmq_utils.delete_queues()

        self.users = [self.user1, self.user2]
        test_utilities.create_users(self.users)


    def test_validation(self):

        # No group owner provided
        self.data = {'name': 'test_group', 'members': json.dumps([self.user1])}
        response = requests.get(self.url, data=self.data)
        res = json.loads(response.content)
        assert_equal(res['info'], errors.GROUP_OWNER_NOT_PROVIDED_ERR)
        assert_equal(res['status'], app_settings.STATUS_400)

        # Invalid group owner
        self.data = {'owner': '913333333333', 'name': 'test_group', 'members': json.dumps([self.user1])}
        response = requests.get(self.url, data=self.data)
        res = json.loads(response.content)
        assert_equal(res['info'], errors.INVALID_GROUP_OWNER_ERR)
        assert_equal(res['status'], app_settings.STATUS_400)

        # No group name provided
        self.data = {'owner': self.user1, 'members': [self.user2]}
        response = requests.get(self.url, data=self.data)
        res = json.loads(response.content)
        assert_equal(res['info'], errors.GROUP_NAME_NOT_PROVIDED_ERR)
        assert_equal(res['status'], app_settings.STATUS_400)

        # Duplicate group names for same owner
        group_name = 'test_group_1'
        query = ' INSERT INTO groups_info (name, owner, admins, members, total_members) VALUES (%s, %s, %s, %s, %s);'
        variables = (group_name, self.user1, [], [], 1)
        db_handler.QueryHandler.execute(query, variables)

        self.data = {'owner': self.user1, 'name': group_name, 'members': json.dumps([self.user2])}
        response = requests.get(self.url, data=self.data)
        res = json.loads(response.content)
        assert_equal(res['info'], errors.GROUP_NAME_ALREADY_EXISTS_ERR)
        assert_equal(res['status'], app_settings.STATUS_400)

        # No group member provided
        self.data = {'owner': self.user1, 'name': 'test_group_2'}
        response = requests.get(self.url, data=self.data)
        res = json.loads(response.content)
        assert_equal(res['info'], errors.NO_GROUP_MEMBER_ADDED_ERR)
        assert_equal(res['status'], app_settings.STATUS_400)

        # Non-registered group member
        self.data = {'owner': self.user1, 'name': 'test_group_2', 'members': json.dumps([910000000000])}
        response = requests.get(self.url, data=self.data)
        res = json.loads(response.content)
        assert_equal(res['info'], errors.NON_REGISTERED_MEMBER_ERR)
        assert_equal(res['status'], app_settings.STATUS_404)

    def test_get(self):

        self.data = {'owner': self.user1, 'name': 'test_group', 'members': json.dumps([self.user2])}
        response = requests.get(self.url, data=self.data)
        res = json.loads(response.content)
        assert_equal(res['info'], app_settings.SUCCESS_RESPONSE)
        assert_equal(res['status'], app_settings.STATUS_200)

        time.sleep(10)
        rabbitmq_response = requests.get(app_settings.RABBITMQ_GET_ALL_QUEUES_URL,
                                         auth=(app_settings.BROKER_USERNAME, app_settings.BROKER_PASSWORD))
        assert_equal(rabbitmq_response.status_code, app_settings.STATUS_200)
        res = json.loads(rabbitmq_response.text)
        assert_not_equal(len(res), 0)


class SendMessageToGroupTests(unittest.TestCase):
    url = None
    data = {}
    user1 = 911111111111
    user2 = 912222222222
    user3 = 913333333333
    users = []
    msgs_count = 11
    groups_count = 3

    def create_new_group(self, group_owner, group_name, group_members):
        query = " INSERT INTO groups_info (name, owner, admins, members, total_members) VALUES (%s, %s, %s, %s, %s) RETURNING id;"
        variables = (group_name, group_owner, [group_owner], group_members, len(group_members))
        try:
            result = db_handler.QueryHandler.get_results(query, variables)
            return result
        except Exception as e:
            raise e

    def get_group_details(self, group_name, group_owner):
        query = " SELECT * FROM groups_info WHERE name=%s AND owner=%s;"
        variables = (group_name, group_owner)
        try:
            result = db_handler.QueryHandler.get_results(query, variables)
            return result
        except Exception as e:
            raise e

    def create_exchanges(self):
        response = requests.get(url='http://localhost:3000/')
        assert_equal(response.status_code, app_settings.STATUS_200)

    def setUp(self):
        self.url = app_settings.SEND_MESSAGE_TO_GROP_URL
        test_utilities.delete_users()
        test_utilities.delete_groups()
        test_utilities.delete_group_messages()
        rabbitmq_utils.delete_exchanges(app_settings.RABBITMQ_EXCHANGES)
        rabbitmq_utils.delete_queues()

        self.users = [self.user1, self.user2, self.user3]
        self.create_exchanges()
        test_utilities.create_users(self.users)
        self.create_new_group(group_owner=self.user1, group_name='test_group_1', group_members=[self.user1, self.user2])

    def test_validations(self):

        # Incomplete data provided
        self.data = {'sender': self.user1, 'message': 'test_message'}
        response = requests.post(self.url, data=self.data)
        res = json.loads(response.content)
        assert_equal(res['info'], errors.SEND_MESSAGE_INCOMPLETE_INFO_ERR)
        assert_equal(res['status'], app_settings.STATUS_400)

        # check if atleast 1 group exists
        query = " SELECT id FROM groups_info;"
        try:
            result = db_handler.QueryHandler.get_results(query)
        except Exception as e:
            raise e
        assert_not_equal(len(result), 0)

        # Invalid user provided as sender
        self.data = {'sender': '910000000000', 'group_name': 'test_group_1', 'message': 'test_message_1'}
        response = requests.post(self.url, data=self.data)
        res = json.loads(response.content)
        assert_equal(res['info'], errors.SEND_MESSAGE_NO_USER_PROVIDED_ERR)
        assert_equal(res['status'], app_settings.STATUS_404)

        # Invalid group_name provided
        self.data = {'sender': str(self.user1), 'group_name': 'test_group_2', 'message': 'test_message_2'}
        response = requests.post(self.url, data=self.data)
        res = json.loads(response.content)
        assert_equal(res['info'], errors.SEND_MESSAGE_INVALID_GROUP_DETAILS_ERR)
        assert_equal(res['status'], app_settings.STATUS_404)

        # Invalid  provided for valid group
        self.data = {'sender': str(self.user3), 'group_name': 'test_group_1', 'message': 'test_message_3'}
        response = requests.post(self.url, data=self.data)
        res = json.loads(response.content)
        assert_equal(res['info'], errors.SEND_MESSAGE_INVALID_GROUP_DETAILS_ERR)
        assert_equal(res['status'], app_settings.STATUS_404)

    def test_post(self):

        result = self.get_group_details('test_group_1', str(self.user1))
        group_id = str(result[0]['id'])
        group_owner = str(result[0]['owner'])
        group_name = str(result[0]['name'])

        # start subscribers for group's members
        user_data = {'topic': 'group_chat.' + str(self.user1) + '.test_group_1.*'}
        for user in result[0]['members']:
            client_id = 'sub_' + group_id + utils.generate_random_client_id(len('sub_' + group_id))
            mqtt_subscriber.group_chat_subscriber(client_id, user_data)

        time.sleep(10)
        self.data = {'sender': str(self.user2), 'group_name': 'test_group_1', 'message': 'this is test message 1'}
        response = requests.post(self.url, data=self.data)
        res = json.loads(response.content)
        assert_equal(res['info'], app_settings.SUCCESS_RESPONSE)
        assert_equal(res['status'], app_settings.STATUS_200)

        time.sleep(20)
        # check if message reached to the database
        query = "SELECT single_tick, double_tick, colored_double_tick FROM group_messages WHERE group_owner=%s AND group_name=%s AND " \
                "sender=%s AND message=%s;"
        variables = (group_owner, group_name, str(self.user2), 'this is test message 1')
        try:
            result = db_handler.QueryHandler.get_results(query, variables)
            assert_equal(len(result), 1)
            assert_equal(result[0]['single_tick'], 'done')
            assert_equal(result[0]['double_tick'], 'done')
            assert_equal(result[0]['colored_double_tick'], 'done')

        except Exception as e:
            raise e

    def test_multiple_msg_single_sender_single_group(self):

        result = self.get_group_details('test_group_1', str(self.user1))
        group_id = str(result[0]['id'])
        group_members = result[0]['members']

        # start subscribers for group's members
        user_data = {'topic': 'group_chat.' + str(self.user1) + '.test_group_1.*'}
        for user in group_members:
            client_id = 'sub_' + group_id + utils.generate_random_client_id(len('sub_' + group_id))
            mqtt_subscriber.group_chat_subscriber(client_id, user_data)
            time.sleep(5)

        test_utilities.delete_group_messages()
        # send multiple msgs continuously, on group by user1
        msgs_list = ['msg_' + str(i) for i in range(self.msgs_count)]
        for msg in msgs_list:
            self.data = {'sender': self.user1, 'group_name': 'test_group_1', 'message': msg}
            response = requests.post(self.url, data=self.data)
            res = json.loads(response.content)
            assert_equal(res['info'], app_settings.SUCCESS_RESPONSE)
            assert_equal(res['status'], app_settings.STATUS_200)
            time.sleep(10)

        time.sleep(20)

        # check if messages reached to the database
        for msg in msgs_list:
            query = "SELECT single_tick, double_tick, colored_double_tick FROM group_messages WHERE group_owner=%s AND group_name=%s AND " \
                    "sender=%s AND message=%s;"
            variables = (str(self.user1), 'test_group_1', str(self.user1), msg)
            try:
                result = db_handler.QueryHandler.get_results(query, variables)
                assert_equal(len(result), 1)
                assert_equal(result[0]['single_tick'], 'done')
                assert_equal(result[0]['double_tick'], 'done')
                assert_equal(result[0]['colored_double_tick'], 'done')
            except Exception as e:
                raise e

    def test_multiple_msg_multiple_senders_single_group(self):

        result = self.create_new_group(group_owner=self.user2, group_name='test_group_2',
                                       group_members=[self.user1, self.user2, self.user3])
        group_id = str(result[0]['id'])
        group_members=[self.user1, self.user2, self.user3]

        # start subscribers for group's members
        user_data = {'topic': 'group_chat.' + str(self.user2) + '.test_group_2.*'}
        for user in group_members:
            client_id = 'sub_' + group_id + utils.generate_random_client_id(len('sub_' + group_id))
            mqtt_subscriber.group_chat_subscriber(client_id, user_data)
            time.sleep(5)
        time.sleep(10)

        # send multiple msgs on group by randomly chosen senders
        msgs_list = ['test_msg_' + str(i) for i in range(self.msgs_count)]
        senders_list = []
        for msg in msgs_list:
            sender = str(random.choice(group_members))
            senders_list.append(sender)
            self.data = {'sender': sender, 'group_name': 'test_group_2', 'message': msg}
            response = requests.post(self.url, data=self.data)
            res = json.loads(response.content)
            assert_equal(res['info'], app_settings.SUCCESS_RESPONSE)
            assert_equal(res['status'], app_settings.STATUS_200)
            time.sleep(10)

        time.sleep(40)
        senders_list.reverse()
        # check if messages reached to the database
        for msg in msgs_list:
            query = "SELECT single_tick, double_tick, colored_double_tick FROM group_messages WHERE group_owner=%s AND group_name=%s AND " \
                    "sender=%s AND message=%s;"
            variables = (str(self.user2), 'test_group_2', senders_list.pop(), msg)
            try:
                result = db_handler.QueryHandler.get_results(query, variables)
                assert_equal(len(result), 1)
                assert_equal(result[0]['single_tick'], 'done')
                assert_equal(result[0]['double_tick'], 'done')
                assert_equal(result[0]['colored_double_tick'], 'done')
            except Exception as e:
                raise e

    def test_single_msg_single_sender_multiple_groups(self):
        result = self.create_new_group(group_owner=self.user2, group_name='test_group_2',
                                       group_members=[self.user1, self.user2, self.user3])

        result = self.create_new_group(group_owner=self.user3, group_name='test_group_3',
                                       group_members=[self.user1, self.user3])

        sender = str(self.user1)
        groups_details = {'test_group_1': str(self.user1), 'test_group_2': str(self.user2), 'test_group_3': str(self.user3)}
        message = 'TEST MESSAGE'

        # start subscribers for ALL groups
        for group_name, group_owner in groups_details.items():
            user_data = {'topic': 'group_chat.' + group_owner + '.' + group_name + '.*'}
            result = self.get_group_details(group_name, group_owner)
            group_id = str(result[0]['id'])
            group_members = result[0]['members']

            for user in group_members:
                client_id = 'sub_' + group_id + utils.generate_random_client_id(len('sub_' + group_id))
                mqtt_subscriber.group_chat_subscriber(client_id, user_data)
                time.sleep(5)
        time.sleep(10)

        test_utilities.delete_group_messages()
        for i in range(1, self.msgs_count):
            group = random.choice(groups_details.keys())
            self.data = {'sender': sender, 'group_name': group, 'message': message}
            response = requests.post(self.url, data=self.data)
            res = json.loads(response.content)
            assert_equal(res['info'], app_settings.SUCCESS_RESPONSE)
            assert_equal(res['status'], app_settings.STATUS_200)
            time.sleep(10)

        time.sleep(50)
        # check if messages reached to the database
        query = "SELECT * FROM group_messages;"
        try:
            result = db_handler.QueryHandler.get_results(query)
            assert_equal(len(result), self.msgs_count-1)
            for msg in result:
                assert_equal(msg['single_tick'], 'done')
                assert_equal(msg['double_tick'], 'done')
                assert_equal(msg['colored_double_tick'], 'done')
        except Exception as e:
            raise e

    def test_multiple_msg_multiple_senders_multiple_groups(self):

        senders_list = []
        msgs_list = ['test_msg_' + str(i) for i in range(self.msgs_count)]
        group_members_list = [[self.user1, self.user2], [self.user2, self.user3], [self.user1, self.user3],
                              [self.user1, self.user2, self.user3]]
        groups_details = {}
        for i in range(1, self.groups_count):
            group_name = 'group_{}_{}'.format(i, "".join(random.choice("abcde") for i in range(4)))
            random_number = random.randint(1, 3)
            group_members = random.choice(group_members_list)
            group_owner = str(random.choice(group_members))
            senders_list.append(group_members)
            self.create_new_group(group_owner, group_name, group_members)
            groups_details[group_name] = group_owner

        message_senders_list = {}
        # start subscribers for ALL groups
        for group_name, group_owner in groups_details.items():
            user_data = {'topic': 'group_chat.' + group_owner + '.' + group_name + '.*'}
            result = self.get_group_details(group_name, group_owner)
            group_id = str(result[0]['id'])
            group_members = result[0]['members']
            message_senders_list[group_name] = random.choice(group_members)

            for user in group_members:
                client_id = 'sub_' + group_id + utils.generate_random_client_id(len('sub_' + group_id))
                mqtt_subscriber.group_chat_subscriber(client_id, user_data)
                time.sleep(5)
        time.sleep(10)

        # make post requests
        for i in range(1, self.msgs_count):
            group = str(random.choice(groups_details.keys()))
            sender = message_senders_list[group]
            message = random.choice(msgs_list)
            self.data = {'sender': sender, 'group_name': group, 'message': message}
            response = requests.post(self.url, data=self.data)
            res = json.loads(response.content)
            assert_equal(res['info'], app_settings.SUCCESS_RESPONSE)
            assert_equal(res['status'], app_settings.STATUS_200)
            time.sleep(10)

        time.sleep(50)
        # check if messages reached to the database
        query = "SELECT * FROM group_messages;"
        try:
            result = db_handler.QueryHandler.get_results(query)
            assert_equal(len(result), self.msgs_count-1)
            for msg in result:
                assert_equal(msg['single_tick'], 'done')
                assert_equal(msg['double_tick'], 'done')
                assert_equal(msg['colored_double_tick'], 'done')
        except Exception as e:
            raise e
