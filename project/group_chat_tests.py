import json
import os
import sys
import random
from chardet import test
from jinja2.testsuite import res

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
        self.url = app_settings.SEND_MESSAGE_TO_GROUP_URL
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


class GetGroupsInfoTests(unittest.TestCase):
    url = None
    groups = []
    users = []
    user1 = 914444444444
    user2 = 915555555555
    user3 = 916666666666
    user4 = 917777777777


    def create_groups(self, groups_list):
        for group in groups_list:
            query = " INSERT INTO groups_info (name, owner, admins, members, total_members) VALUES (%s, %s, %s, %s, %s) RETURNING id;"
            variables = (str(group['name']), str(group['owner']), [str(group['owner'])], group['members'], len(group['members']))
            try:
                result = db_handler.QueryHandler.get_results(query, variables)

                for member in group['members']:
                    query = " UPDATE users SET member_of_groups = array_append(member_of_groups, %s) WHERE username=%s;"
                    variables = (str(result[0]['id']), str(member))
                    db_handler.QueryHandler.execute(query, variables)
            except Exception as e:
                raise e

    def setUp(self):
        self.url = app_settings.GET_GROUPS_INFO_URL
        self.users = [self.user1, self.user2, self.user3, self.user4]
        self.groups = [{'owner': self.user1, 'name': 'group_1', 'members': [self.user1, self.user2]},
                       {'owner': self.user3, 'name': 'group_2', 'members': [self.user2, self.user3, self.user1]},
                       {'owner': self.user1, 'name': 'group_3', 'members': [self.user1]}]
        rabbitmq_utils.delete_exchanges(app_settings.RABBITMQ_EXCHANGES)
        rabbitmq_utils.delete_queues()
        test_utilities.delete_groups()
        test_utilities.delete_users()

        test_utilities.create_users(self.users)
        self.create_groups(groups_list=self.groups)

    def test_validation(self):

        # User not provided
        response = requests.get(self.url, data={})
        res = json.loads(response.content)
        assert_equal(response.status_code, app_settings.STATUS_200)
        assert_equal(res['status'], app_settings.STATUS_400)
        assert_equal(res['info'], errors.INCOMPLETE_USER_INFO_ERR)

        # Non-registered user provided
        response = requests.get(self.url, data={'user': '910000000000'})
        res = json.loads(response.content)
        assert_equal(response.status_code, app_settings.STATUS_200)
        assert_equal(res['status'], app_settings.STATUS_404)
        assert_equal(res['info'], errors.USER_NOT_REGISTERED_ERR)

    def test_get(self):

        # user with some groups associated
        response = requests.get(self.url, data={'user': str(self.user1)})
        res = json.loads(response.content)

        try:
            query = " SELECT member_of_groups FROM users WHERE username=%s;"
            variables = (str(self.user1),)
            result = db_handler.QueryHandler.get_results(query, variables)
            user_groups = []

            for group_id in result[0]['member_of_groups']:
                query = " SELECT total_members,name,admins,members,owner FROM groups_info WHERE id=%s;"
                variables = (group_id,)
                group_result = db_handler.QueryHandler.get_results(query, variables)
                user_groups.append(group_result[0])
        except Exception as e:
            raise e

        assert_equal(len(user_groups), 3)
        assert_equal(response.status_code, app_settings.STATUS_200)
        assert_equal(res.has_key('groups'), True)
        assert_equal(json.loads(res['groups']), user_groups)
        assert_equal(res['info'], app_settings.SUCCESS_RESPONSE)
        assert_equal(res['status'], app_settings.STATUS_200)

        # user with no group(s) associated
        response = requests.get(self.url, data={'user': str(self.user4)})
        res = json.loads(response.content)
        assert_equal(response.status_code, app_settings.STATUS_200)
        assert_equal(res['info'], errors.NO_ASSOCIATED_GROPS_ERR)
        assert_equal(res['status'], app_settings.STATUS_200)


class AddContactToGroupTests(unittest.TestCase):
    url = None
    users = None
    data = None
    group_id = None
    group_name = None
    group_owner = None
    group_members = None
    user1 = 912222222222
    user2 = 913333333333
    user3 = 914444444444

    def create_group(self, name, owner, members):
        query = " INSERT INTO groups_info (name, owner, admins, members, total_members) VALUES (%s, %s, %s, %s, %s) RETURNING id;"
        variables = (name, owner, [owner], members, len(members))
        try:
            result = db_handler.QueryHandler.get_results(query, variables)
            return result[0]['id']
        except Exception as e:
            raise e

    def setUp(self):
        self.url = app_settings.ADD_CONTACT_TO_GROUP_URL
        self.users = [self.user1, self.user2, self.user3]
        rabbitmq_utils.delete_exchanges(app_settings.RABBITMQ_EXCHANGES)
        rabbitmq_utils.delete_queues()
        test_utilities.delete_groups()
        test_utilities.delete_users()
        test_utilities.delete_group_messages()

        self.users = [self.user1, self.user2, self.user3]
        test_utilities.create_users(self.users)
        self.group_name = 'test_group'
        self.group_owner = str(self.user1)
        self.group_members = [str(self.user1), str(self.user2)]
        self.group_id = str(self.create_group(self.group_name, self.group_owner, self.group_members))

    def test_validations(self):
        # No group_id provided
        response = requests.post(self.url, data={'contact': str(self.user1)})
        test_utilities.assert_info_status(response, errors.INCOMPLETE_GROUP_INFO_ERR, app_settings.STATUS_400)

        # Invalid group_id provided
        response = requests.post(self.url, data={'contact': str(self.user1), 'group_id': int(self.group_id) + 200})
        test_utilities.assert_info_status(response, errors.INVALID_GROUP_ID_ERR, app_settings.STATUS_404)

        # No user data provided
        response = requests.post(self.url, data={'group_id': self.group_id})
        test_utilities.assert_info_status(response, errors.INCOMPLETE_USER_INFO_ERR, app_settings.STATUS_400)

        # Non-registered user provided
        response = requests.post(self.url, data={'contact':'910000000000', 'group_id': self.group_id})
        test_utilities.assert_info_status(response, errors.INVALID_USER_CONTACT_ERR, app_settings.STATUS_404)

    def test_post(self):

        # start group-users' subscribers
        user_data = {'topic': 'group_chat.' + self.group_owner + '.' + self.group_name + '.*'}
        for user in self.group_members:
            client_id = 'sub_' + self.group_id + utils.generate_random_client_id(len('sub_' + self.group_id))
            mqtt_subscriber.group_chat_subscriber(client_id, user_data)
        time.sleep(10)

        # send message before adding new contact in the group
        self.data = {'sender': str(self.user1), 'group_name': self.group_name, 'message': 'this is test message!!'}
        response = requests.post(url=app_settings.SEND_MESSAGE_TO_GROUP_URL, data=self.data)
        assert_equal(response.status_code, app_settings.STATUS_200)

        time.sleep(20)
        # check if message reached to the database
        query = "SELECT single_tick, double_tick, colored_double_tick FROM group_messages WHERE group_owner=%s AND group_name=%s AND " \
                "sender=%s AND message=%s;"
        variables = (self.group_owner, self.group_name, str(self.user1), 'this is test message!!')
        try:
            result = db_handler.QueryHandler.get_results(query, variables)
            assert_equal(len(result), 1)
            assert_equal(result[0]['single_tick'], 'done')
            assert_equal(result[0]['double_tick'], 'done')
            assert_equal(result[0]['colored_double_tick'], 'done')

        except Exception as e:
            raise e

        # add new contact to the group
        response = requests.post(self.url, data={'contact': str(self.user3), 'group_id': self.group_id})
        test_utilities.assert_info_status(response, app_settings.SUCCESS_RESPONSE, app_settings.STATUS_200)

        # send another message to the same group
        self.data = {'sender': str(self.user3), 'group_name': self.group_name, 'message': 'this is another test message!!'}
        response = requests.post(url=app_settings.SEND_MESSAGE_TO_GROUP_URL, data=self.data)
        assert_equal(response.status_code, app_settings.STATUS_200)

        time.sleep(20)
        # check if message reached to the database
        query = "SELECT single_tick, double_tick, colored_double_tick FROM group_messages WHERE group_owner=%s AND group_name=%s AND " \
                "sender=%s AND message=%s;"
        variables = (self.group_owner, self.group_name, str(self.user3), 'this is another test message!!')
        try:
            result = db_handler.QueryHandler.get_results(query, variables)
            assert_equal(len(result), 1)
            assert_equal(result[0]['single_tick'], 'done')
            assert_equal(result[0]['double_tick'], 'done')
            assert_equal(result[0]['colored_double_tick'], 'done')
        except Exception as e:
            raise e


class RemoveContactFromGroupTests(unittest.TestCase):
    url = None
    users = None
    data = None
    group_id = None
    group_name = None
    group_owner = None
    group_members = None
    user1 = 914444444444
    user2 = 915555555555
    user3 = 916666666666

    def create_group(self, name, owner, members):
        query = " INSERT INTO groups_info (name, owner, admins, members, total_members) VALUES (%s, %s, %s, %s, %s) RETURNING id;"
        variables = (name, owner, [owner], members, len(members))
        try:
            result = db_handler.QueryHandler.get_results(query, variables)
            return result[0]['id']
        except Exception as e:
            raise e

    def update_group_members(self, group_members, group_id):
        for member in group_members:
            query = " UPDATE users SET member_of_groups = array_append(member_of_groups, %s) WHERE username=%s;"
            variables = (str(group_id), member)
            try:
                db_handler.QueryHandler.execute(query, variables)
            except Exception as e:
                raise e

    def setUp(self):
        self.url = app_settings.REMOVE_CONTACT_FROM_GROUP_URL
        rabbitmq_utils.delete_exchanges(app_settings.RABBITMQ_EXCHANGES)
        rabbitmq_utils.delete_queues()
        test_utilities.delete_users()
        test_utilities.delete_groups()
        test_utilities.delete_group_messages()

        self.users = [self.user1, self.user2, self.user3]
        test_utilities.create_users(self.users)
        self.group_name = 'test_group'
        self.group_owner = str(self.user1)
        self.group_members = [str(self.user1), str(self.user3)]
        self.group_id = str(self.create_group(self.group_name, self.group_owner, self.group_members))
        self.update_group_members(self.group_members, self.group_id)

    def test_validations(self):
        # No user contact provided
        response = requests.post(self.url, data={'group_id': self.group_id})
        test_utilities.assert_info_status(response, errors.INCOMPLETE_USER_INFO_ERR, app_settings.STATUS_400)

        # Non-registered User provided
        response = requests.post(self.url, data={'contact': '910000000000','group_id': self.group_id})
        test_utilities.assert_info_status(response, errors.INVALID_USER_CONTACT_ERR, app_settings.STATUS_404)

        # No group_id provided
        response = requests.post(self.url, data={'contact': str(self.user1)})
        test_utilities.assert_info_status(response, errors.INCOMPLETE_GROUP_INFO_ERR, app_settings.STATUS_400)

        # Invalid group_id provided
        response = requests.post(self.url, data={'contact': str(self.user1), 'group_id': int(self.group_id) + 100})
        test_utilities.assert_info_status(response, errors.INVALID_GROUP_ID_ERR, app_settings.STATUS_404)

        # User and group doesn't match
        response = requests.post(self.url, data={'contact': str(self.user2), 'group_id': self.group_id})
        test_utilities.assert_info_status(response, errors.USER_GROUP_NOT_MATCH_ERR, app_settings.STATUS_404)

        # If user is owner of the group
        response = requests.post(self.url, data={'contact': str(self.user1), 'group_id': self.group_id})
        test_utilities.assert_info_status(response, errors.DELETED_USER_IS_GROUP_OWNER_ERR, app_settings.STATUS_400)

    def test_post(self):

        # remove user3 from the group
        response = requests.post(self.url, data={'contact': str(self.user3),'group_id': self.group_id})
        test_utilities.assert_info_status(response, app_settings.SUCCESS_RESPONSE, app_settings.STATUS_200)
        query = " SELECT * FROM groups_info WHERE id=%s;"
        try:
            result = db_handler.QueryHandler.get_results(query, (self.group_id,))
            assert_equal(result[0]['members'], [str(self.user1)])
            assert_equal(result[0]['total_members'], 1)

            query = " SELECT member_of_groups FROM users WHERE username=%s;"
            result = db_handler.QueryHandler.get_results(query, (str(self.user3),))
            assert_equal(result[0]['member_of_groups'], [])
        except Exception as e:
            raise e

        # remove user1 from the group
        response = requests.post(self.url, data={'contact': str(self.user1),'group_id': self.group_id})
        test_utilities.assert_info_status(response, app_settings.SUCCESS_RESPONSE, app_settings.STATUS_200)
        query = " SELECT * FROM groups_info WHERE id=%s;"
        try:
            result = db_handler.QueryHandler.get_results(query, (self.group_id,))
            assert_equal(len(result), 0)

            query = " SELECT member_of_groups FROM users WHERE username=%s;"
            result = db_handler.QueryHandler.get_results(query, (str(self.user1),))
            assert_equal(result[0]['member_of_groups'], [])
        except Exception as e:
            raise e


class AddAdminToGroupTests(unittest.TestCase):
    url = None
    users = None
    data = None
    group_id = None
    group_name = None
    group_owner = None
    group_members = None
    user1 = 914444444444
    user2 = 915555555555
    user3 = 916666666666
    user4 = 917777777777

    def create_group(self, name, owner, members):
        query = " INSERT INTO groups_info (name, owner, admins, members, total_members) VALUES (%s, %s, %s, %s, %s) RETURNING id;"
        variables = (name, owner, [owner], members, len(members))
        try:
            result = db_handler.QueryHandler.get_results(query, variables)
            return result[0]['id']
        except Exception as e:
            raise e

    def update_group_members(self, group_members, group_id):
        for member in group_members:
            query = " UPDATE users SET member_of_groups = array_append(member_of_groups, %s) WHERE username=%s;"
            variables = (str(group_id), member)
            try:
                db_handler.QueryHandler.execute(query, variables)
            except Exception as e:
                raise e

    def setUp(self):
        self.url = app_settings.ADD_ADMIN_TO_GROUP_URL
        rabbitmq_utils.delete_exchanges(app_settings.RABBITMQ_EXCHANGES)
        rabbitmq_utils.delete_queues()
        test_utilities.delete_users()
        test_utilities.delete_groups()

        self.users = [self.user1, self.user2, self.user3, self.user4]
        test_utilities.create_users(self.users)
        self.group_name = 'test_group'
        self.group_owner = str(self.user1)
        self.group_members = [str(self.user1), str(self.user2), str(self.user3)]
        self.group_id = str(self.create_group(self.group_name, self.group_owner, self.group_members))
        self.update_group_members(self.group_members, self.group_id)

    def test_validations(self):

        # User data not provided
        self.data = {'contact': self.user3, 'group_id': self.group_id}
        response = requests.post(self.url, data=self.data)
        test_utilities.assert_info_status(response, errors.INCOMPLETE_USER_DETAILS_ERR, app_settings.STATUS_400)

        # Group id not provided
        self.data = {'contact': self.user3, 'user': self.user1}
        response = requests.post(self.url, data=self.data)
        test_utilities.assert_info_status(response, errors.INCOMPLETE_GROUP_INFO_ERR, app_settings.STATUS_400)

        # Contact to be added as admin, not provided
        self.data = {'user': self.user1, 'group_id': self.group_id}
        response = requests.post(self.url, data=self.data)
        test_utilities.assert_info_status(response, errors.INCOMPLETE_CONTACT_DETAILS_ERR, app_settings.STATUS_400)

        # Non-registered users (either user or new added admin)
        self.data = {'user': '910000000000', 'group_id': self.group_id, 'contact': self.user2}
        response = requests.post(self.url, data=self.data)
        test_utilities.assert_info_status(response, errors.NON_REGISTERED_USER_CONTACT_ERR, app_settings.STATUS_404)

        # Invalid Group-id
        self.data = {'user': self.user1, 'group_id': int(self.group_id) + 200, 'contact': self.user2}
        response = requests.post(self.url, data=self.data)
        test_utilities.assert_info_status(response, errors.INVALID_GROUP_ID_ERR, app_settings.STATUS_404)

        # Already an admin
        self.data = {'user': self.user1, 'group_id': self.group_id, 'contact': self.user1}
        response = requests.post(self.url, data=self.data)
        test_utilities.assert_info_status(response, errors.ALREADY_GROUP_ADMIN_INFO, app_settings.STATUS_400)

        # Ensure 'user' is an admin (has permissions to add an admin)
        self.data = {'user': self.user3, 'group_id': self.group_id, 'contact': self.user2}
        response = requests.post(self.url, data=self.data)
        test_utilities.assert_info_status(response, errors.OUTSIDE_USER_PERMISSIONS_ERR, app_settings.STATUS_400)

        # New admin not a member of the group
        self.data = {'user': self.user1, 'group_id': self.group_id, 'contact': self.user4}
        response = requests.post(self.url, data=self.data)
        test_utilities.assert_info_status(response, errors.CONTACT_GROUP_NOT_MATCH_ERR, app_settings.STATUS_400)

    def test_post(self):
        self.data = {'user': self.user1, 'contact': self.user3, 'group_id': self.group_id}
        response = requests.post(self.url, data=self.data)
        test_utilities.assert_info_status(response, app_settings.SUCCESS_RESPONSE, app_settings.STATUS_200)

        query = " SELECT admins FROM groups_info WHERE id=%s;"
        try:
            result = db_handler.QueryHandler.get_results(query, (self.group_id, ))
            assert_equal(result[0]['admins'], [str(self.user1), str(self.user3)])
        except Exception as e:
            raise e


class RemoveAdminFromGroupTests(unittest.TestCase):
    url = None
    users = None
    data = None
    group_id = None
    group_name = None
    group_owner = None
    group_members = None
    user1 = 914444444444
    user2 = 915555555555
    user3 = 916666666666
    user4 = 917777777777

    def create_group(self, name, owner, admins, members):
        query = " INSERT INTO groups_info (name, owner, admins, members, total_members) VALUES (%s, %s, %s, %s, %s) RETURNING id;"
        variables = (name, owner, admins, members, len(members))
        try:
            result = db_handler.QueryHandler.get_results(query, variables)
            return result[0]['id']
        except Exception as e:
            raise e

    def update_group_members(self, group_members, group_id):
        for member in group_members:
            query = " UPDATE users SET member_of_groups = array_append(member_of_groups, %s) WHERE username=%s;"
            variables = (str(group_id), member)
            try:
                db_handler.QueryHandler.execute(query, variables)
            except Exception as e:
                raise e

    def setUp(self):
        self.url = app_settings.REMOVE_ADMIN_FROM_GROUP_URL
        rabbitmq_utils.delete_exchanges(app_settings.RABBITMQ_EXCHANGES)
        rabbitmq_utils.delete_queues()
        test_utilities.delete_users()
        test_utilities.delete_groups()

        self.users = [self.user1, self.user2, self.user3, self.user4]
        test_utilities.create_users(self.users)
        self.group_name = 'test_group'
        self.group_owner = str(self.user1)
        self.group_members = [str(self.user1), str(self.user2), str(self.user3)]
        self.group_id = str(self.create_group(self.group_name, self.group_owner, [self.group_owner, str(self.user2)], self.group_members))
        self.update_group_members(self.group_members, self.group_id)

    def test_validations(self):

        # User data not provided
        self.data = {'contact': self.user2, 'group_id': self.group_id}
        response = requests.post(self.url, data=self.data)
        test_utilities.assert_info_status(response, errors.INCOMPLETE_USER_DETAILS_ERR, app_settings.STATUS_400)

        # Group id not provided
        self.data = {'contact': self.user2, 'user': self.user1}
        response = requests.post(self.url, data=self.data)
        test_utilities.assert_info_status(response, errors.INCOMPLETE_GROUP_INFO_ERR, app_settings.STATUS_400)

        # Contact to be removed is not provided
        self.data = {'group_id': self.group_id, 'user': self.user1}
        response = requests.post(self.url, data=self.data)
        test_utilities.assert_info_status(response, errors.INCOMPLETE_CONTACT_DETAILS_ERR, app_settings.STATUS_400)

        # Non-registered users (either user or to-be-removed-admin)
        self.data = {'group_id': self.group_id, 'user': '910000000000', 'contact': self.user2}
        response = requests.post(self.url, data=self.data)
        test_utilities.assert_info_status(response, errors.NON_REGISTERED_USER_CONTACT_ERR, app_settings.STATUS_404)

        # Invalid Group-id
        self.data = {'group_id': int(self.group_id) + 100, 'user': self.user1, 'contact': self.user2}
        response = requests.post(self.url, data=self.data)
        test_utilities.assert_info_status(response, errors.INVALID_GROUP_ID_ERR, app_settings.STATUS_404)

        # Already a non-admin
        self.data = {'group_id': self.group_id, 'user': self.user1, 'contact': self.user3}
        response = requests.post(self.url, data=self.data)
        test_utilities.assert_info_status(response, errors.ALREADY_NOT_ADMIN_INFO, app_settings.STATUS_400)

        # Ensure 'user' is an admin (has permissions to add an admin)
        self.data = {'group_id': self.group_id, 'user': self.user3, 'contact': self.user2}
        response = requests.post(self.url, data=self.data)
        test_utilities.assert_info_status(response, errors.OUTSIDE_USER_PERMISSIONS_ERR, app_settings.STATUS_400)

        # contact to be removed is not a member of the group
        self.data = {'group_id': self.group_id, 'user': self.user1, 'contact': self.user4}
        response = requests.post(self.url, data=self.data)
        test_utilities.assert_info_status(response, errors.CONTACT_GROUP_NOT_MATCH_ERR, app_settings.STATUS_400)

    def test_post(self):

        # when admin removes self; group has > 1 members and > 1 admins
        self.data = {'user': self.user2, 'contact': self.user2, 'group_id': self.group_id}
        response = requests.post(self.url, data=self.data)
        test_utilities.assert_info_status(response, app_settings.SUCCESS_RESPONSE, app_settings.STATUS_200)
        query = " SELECT admins FROM groups_info WHERE id=%s;"
        try:
            result = db_handler.QueryHandler.get_results(query, (self.group_id,))
            assert_equal(len(result[0]['admins']), 1)
            assert_equal(result[0]['admins'], [str(self.user1)])
        except Exception as e:
            raise e

        # when admin removes self; group has > 1 members and 1 admin
        self.data = {'user': self.user1, 'contact': self.user1, 'group_id': self.group_id}
        response = requests.post(self.url, data=self.data)
        test_utilities.assert_info_status(response, errors.DELETED_USER_IS_GROUP_OWNER_ERR, app_settings.STATUS_400)
        query = " SELECT admins FROM groups_info WHERE id=%s;"
        try:
            result = db_handler.QueryHandler.get_results(query, (self.group_id,))
            assert_equal(len(result[0]['admins']), 1)
            assert_equal(result[0]['admins'], [str(self.user1)])
        except Exception as e:
            raise e

        # when admin removes self; group has 1 member and 1 admin
        query = " UPDATE groups_info SET total_members = total_members - 1, members = array_remove(members, %s) WHERE id=%s;"
        try:
            db_handler.QueryHandler.execute(query, (str(self.user3), self.group_id))
            query = " UPDATE groups_info SET total_members = total_members - 1, members = array_remove(members, %s) WHERE id=%s;"
            db_handler.QueryHandler.execute(query, (str(self.user2), self.group_id))
        except Exception as e:
            raise e

        self.data = {'user': self.user1, 'contact': self.user1, 'group_id': self.group_id}
        response = requests.post(self.url, data=self.data)
        test_utilities.assert_info_status(response, app_settings.SUCCESS_RESPONSE, app_settings.STATUS_200)
        query = " SELECT id FROM groups_info WHERE id=%s;"
        try:
            result = db_handler.QueryHandler.get_results(query, (self.group_id,))
            assert_equal(len(result), 0)
        except Exception as e:
            raise e

        # when user and admin-to-remove are different
        test_utilities.delete_groups()
        self.group_id = str(self.create_group('test_group', str(self.user2), [str(self.user2), str(self.user3)],
                          [str(self.user1), str(self.user2), str(self.user3)]))

        self.data = {'user': self.user2, 'contact': self.user3, 'group_id': self.group_id}
        response = requests.post(self.url, data=self.data)
        test_utilities.assert_info_status(response, app_settings.SUCCESS_RESPONSE, app_settings.STATUS_200)
        query = " SELECT admins FROM groups_info WHERE id=%s;"
        try:
            result = db_handler.QueryHandler.get_results(query, (self.group_id,))
            assert_equal(result[0]['admins'], [str(self.user2)])
        except Exception as e:
            raise e
