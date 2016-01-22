import json
import os
import random
import requests
import string
import sys
import time
import unittest
from nose.tools import *

sys.path.append(os.path.dirname(os.path.abspath(__file__)).rsplit('/', 1)[0])
from chat import errors as chat_errors
from chat import message_subscriber
from project import rabbitmq_tests, test_utilities, app_settings, db_handler, rabbitmq_utils
from registration import errors as registration_errors


class RegistrationTests(unittest.TestCase):
    url = None
    valid_number = None

    def setUp(self):
        self.url = app_settings.REGISTER_URL
        self.valid_number = app_settings.TESTING_VALID_CONTACT

    def test_get(self):
        # No number provided
        response = requests.get(self.url, data={'phone_number': ''})
        res_content = json.loads(response.content)
        assert_equal(response.status_code, app_settings.STATUS_200)
        assert_equal(res_content['info'], registration_errors.INVALID_REGISTRATION_NUMBER_ERR)
        assert_equal(res_content['status'], app_settings.STATUS_404)

        # Wrong number of digits provided
        response = requests.get(self.url, data={'phone_number': '+9199'})
        res_content = json.loads(response.content)
        assert_equal(response.status_code, app_settings.STATUS_200)
        assert_equal(res_content['info'], registration_errors.WRONG_DIGITS_ERR)
        assert_equal(res_content['status'], app_settings.STATUS_404)

        # Invalid Number provided
        response = requests.get(self.url, data={'phone_number': '+910000000000'})
        res_content = json.loads(response.content)
        assert_equal(response.status_code, app_settings.STATUS_200)
        assert_equal(res_content['info'], registration_errors.INVALID_REGISTRATION_NUMBER_ERR)
        assert_equal(res_content['status'], app_settings.STATUS_404)

        # Valid number provided
        response = requests.get(self.url, data={'phone_number': self.valid_number})
        res_content = json.loads(response.content)
        assert_equal(response.status_code, app_settings.STATUS_200)
        assert_equal(res_content['info'], app_settings.SUCCESS_RESPONSE)
        assert_equal(res_content['status'], app_settings.STATUS_200)

    def tearDown(self):
        query = " DELETE from registered_users WHERE username=%s;"
        variables = (self.valid_number, )
        db_handler.QueryHandler.execute(query, variables)


class CreateUserTests(unittest.TestCase):
    url = None
    valid_number = None
    auth_code = None
    channel = None
    user_presence_exchange_name = None

    def setUp(self):
        self.url = app_settings.USER_CREATION_URL
        self.valid_number = app_settings.TESTING_VALID_CONTACT
        self.auth_code = 6754
        self.user_presence_exchange_name = app_settings.CHAT_PRESENCE_EXCHANGE

        # create rabbitmq exchange for user's presence
        self.channel = rabbitmq_utils.get_rabbitmq_connection()
        self.channel.exchange_declare(exchange=self.user_presence_exchange_name, type='topic', durable=True,
                                      auto_delete=False)

    def tearDown(self):
        # delete the exchange
        self.channel.exchange_delete(exchange=self.user_presence_exchange_name)

    def test_validation(self):

        # User is not registered
        response = requests.get(self.url, data={'phone_number': self.valid_number, 'auth_code': self.auth_code})
        res_content = json.loads(response.content)
        assert_equal(response.status_code, app_settings.STATUS_200)
        assert_equal(res_content['info'], registration_errors.PHONE_AUTH_CODE_MISMATCH_ERR)
        assert_equal(res_content['status'], app_settings.STATUS_404)

        # Invalid auth code for the user
        query = " INSERT INTO registered_users (username, authorization_code, expiration_time) VALUES (%s, %s, %s); "
        variables = (self.valid_number, random.randint(1000,9999), int(time.time()) + app_settings.EXPIRY_PERIOD_SEC)
        try:
            db_handler.QueryHandler.execute(query, variables)
            response = requests.get(self.url, data={'phone_number': self.valid_number, 'auth_code': self.auth_code})
            res_content = json.loads(response.content)
            assert_equal(response.status_code, app_settings.STATUS_200)
            assert_equal(res_content['info'], registration_errors.PHONE_AUTH_CODE_MISMATCH_ERR)
            assert_equal(res_content['status'], app_settings.STATUS_404)
        except Exception as e:
            raise e

    def test_get(self):

        # Valid phone number and auth code
        self.auth_code = random.randint(1000,9999)
        query = " INSERT INTO registered_users (username, authorization_code, expiration_time) VALUES (%s, %s, %s); "
        variables = (self.valid_number, self.auth_code, int(time.time()) + app_settings.EXPIRY_PERIOD_SEC)
        try:
            db_handler.QueryHandler.execute(query, variables)
            response = requests.get(self.url, data={'phone_number': self.valid_number, 'auth_code': self.auth_code})
            res_content = json.loads(response.content)

            assert_equal(response.status_code, app_settings.STATUS_200)
            assert_equal(res_content['info'], app_settings.SUCCESS_RESPONSE)
            assert_equal(res_content['status'], app_settings.STATUS_200)

            # check if user created in 'users' table
            query = " SELECT id FROM users WHERE username=%s;"
            variables = (self.valid_number,)
            result = db_handler.QueryHandler.get_results(query, variables)
            assert_equal(len(result), 1)

            # check if queue binded to user_presence exchange
            rabbitmq_api_response = requests.get(app_settings.RABBITMQ_ALL_BINDINGS_GET_URL,
                                                 auth=(app_settings.BROKER_USERNAME, app_settings.BROKER_PASSWORD))
            res = json.loads(rabbitmq_api_response.content)
            bindings_list = []
            for binding in res:
                bindings_list.append({'routing_key': binding.get('routing_key'), 'source': binding.get('source'),
                                      'destination_type': binding.get('destination_type')})
            assert_in({'routing_key': 'user_presence.' + self.valid_number + '_presence',
                       'source': app_settings.CHAT_PRESENCE_EXCHANGE, 'destination_type': 'queue'}, bindings_list)
        except Exception as e:
            raise e


class SaveContactsTests(unittest.TestCase):
    url = None
    users_list = None
    user_number = 918888888888
    contact_1 = 919999999999
    contact_2 = 910000000000
    non_registered_number_1 = 915555555555
    non_registered_number_2 = 916666666666

    def create_users(self, users_list):
        try:
            for user in users_list:
                query = " INSERT INTO users(username, password, member_of_groups, status, contacts) values (%s, %s, %s, %s, %s);"
                variables = (user, '', '{}', '0', '{}')
                db_handler.QueryHandler.execute(query, variables)
        except Exception as e:
            raise e

    def delete_users(self):
        try:
            query = " DELETE FROM users;"
            db_handler.QueryHandler.execute(query)
        except Exception as e:
            raise e

    def setUp(self):
        self.url = app_settings.SAVE_CONTACTS_URL

        test_utilities.delete_registered_users()       # delete registered users
        test_utilities.delete_users()      # delete users
        rabbitmq_utils.delete_queues()     # delete all created queues
        rabbitmq_utils.delete_exchanges(app_settings.RABBITMQ_EXCHANGES)

        rabbitmq_tests.test_create_exchanges()     # create testing exchanges
        users_list = [self.user_number, self.contact_1, self.contact_2]     # create 3 valid users
        self.create_users(users_list)

    def test_validation(self):

        # Non-registered user
        response = requests.post(self.url, data={'user': self.non_registered_number_1,
                                                 'contacts': [self.non_registered_number_2]})
        res_content = json.loads(response.content)
        assert_equal(response.status_code, app_settings.STATUS_200)
        assert_equal(res_content['info'], registration_errors.INVALID_USER_ERR)
        assert_equal(res_content['status'], app_settings.STATUS_404)

    def test_post(self):
        response = requests.post(self.url, data={'user': self.user_number, 'contacts': '[919999999999,910000000000]'})
        res_content = json.loads(response.content)

        assert_equal(response.status_code, app_settings.STATUS_200)
        assert_equal(res_content['info'], app_settings.SUCCESS_RESPONSE)
        assert_equal(res_content['status'], app_settings.STATUS_200)

        try:
            # check if contacts saved for the user
            query = " SELECT contacts FROM users WHERE username=%s;"
            variables = (str(self.user_number),)
            result = db_handler.QueryHandler.get_results(query, variables)
            assert_equal(len(result), 1)
            assert_equal(result[0]['contacts'], [str(self.contact_1), str(self.contact_2)])


            rabbitmq_api_response = requests.get(app_settings.RABBITMQ_ALL_BINDINGS_GET_URL,
                                                 auth=(app_settings.BROKER_USERNAME, app_settings.BROKER_PASSWORD))
            res = json.loads(rabbitmq_api_response.content)
            bindings_list = []
            for binding in res:
                bindings_list.append({'routing_key': binding.get('routing_key'), 'source': binding.get('source'),
                                      'destination_type': binding.get('destination_type')})

            self.assert_simple_chat_messages_queue_bind(bindings_list)
            self.assert_simple_chat_media_queue_bind(bindings_list)
        except Exception as e:
            raise e

    def assert_simple_chat_messages_queue_bind(self, bindings_list):
        assert_in({'routing_key': 'simple_chat_918888888888.*',
                   'source': app_settings.SIMPLE_CHAT_MESSAGES_EXCHANGE, 'destination_type': 'queue'}, bindings_list)

    def assert_simple_chat_media_queue_bind(self, bindings_list):
        assert_in({'routing_key': 'simple_media_918888888888.*',
                   'source': app_settings.SIMPLE_CHAT_MEDIA_EXCHANGE, 'destination_type': 'queue'}, bindings_list)


class StartStopAppTests(unittest.TestCase):
    url = None
    channel = None
    invalid_user_contact = app_settings.TESTING_INVALID_CONTACT
    valid_user_1 = 911111111111
    valid_user_2 = 912222222222
    valid_user_3 = 913333333333

    def create_valid_user(self, users_list):
        for user in users_list:
            query = " INSERT INTO users(username, password, member_of_groups, status, contacts) values (%s, %s, %s, %s, %s);"
            variables = (str(user), '', '{}', '0', '{}')
            try:
                db_handler.QueryHandler.execute(query, variables)
            except Exception as e:
                raise e

    def create_presence_notification_exchange_queue(self, routing_keys):
        self.channel = rabbitmq_utils.get_rabbitmq_connection()
        self.channel.exchange_declare(exchange=app_settings.CHAT_PRESENCE_EXCHANGE, type='topic', durable=True,
                                      auto_delete=False)

        for key in routing_keys:
            result = self.channel.queue_declare()
            self.channel.queue_bind(exchange=app_settings.CHAT_PRESENCE_EXCHANGE, queue=result.method.queue,
                                routing_key=key)

    def delete_presence_notification_exchange(self):
        self.channel.exchange_delete(exchange=app_settings.CHAT_PRESENCE_EXCHANGE)

    def add_contacts(self):
        try:
            query = " UPDATE users SET contacts = %s WHERE username=%s;"
            variables = ([str(self.valid_user_2), str(self.valid_user_3)], str(self.valid_user_1), )
            db_handler.QueryHandler.execute(query, variables)
        except Exception as e:
            raise e

    def setUp(self):
        self.url = app_settings.START_STOP_APP_URL
        test_utilities.delete_users()
        rabbitmq_utils.delete_exchanges(app_settings.RABBITMQ_EXCHANGES)
        rabbitmq_utils.delete_queues()

        self.users = [self.valid_user_1, self.valid_user_2, self.valid_user_3]
        self.create_valid_user(self.users)
        self.routing_keys = ['user_presence.' + str(self.valid_user_1) + '_presence',
                        'user_presence.' + str(self.valid_user_2) + '_presence',
                        'user_presence.' + str(self.valid_user_3) + '_presence']
        self.create_presence_notification_exchange_queue(self.routing_keys)

    def test_validation(self):

        # Invalid user
        response = requests.post(self.url, data={'user': app_settings.TESTING_INVALID_CONTACT, 'event': '1'})
        res = json.loads(response.content)
        assert_equal(response.status_code, app_settings.STATUS_200)
        assert_equal(res['info'], registration_errors.INVALID_USER_ERR)
        assert_equal(res['status'], app_settings.STATUS_404)

        # Invalid event type
        response = requests.post(self.url, data={'user': self.valid_user_1, 'event': '4'})
        res = json.loads(response.content)
        assert_equal(response.status_code, app_settings.STATUS_200)
        assert_equal(res['info'], registration_errors.INVALID_EVENT_ERR)
        assert_equal(res['status'], app_settings.STATUS_400)

        # Event not provided
        response = requests.post(self.url, data={'user': self.valid_user_1})
        res = json.loads(response.content)
        assert_equal(response.status_code, app_settings.STATUS_200)
        assert_equal(res['info'], registration_errors.EVENT_NOT_PROVIDED_ERR)
        assert_equal(res['status'], app_settings.STATUS_400)

    def test_post(self):
        # start a subscriber for valid_user_1 presence notification
        test_utilities.start_presence_subscriber(client_id=test_utilities.generate_random_id(),
                         user_data={'topic': 'user_presence.' + str(self.valid_user_1) + '_presence',
                                    'user': str(self.valid_user_1)})
        time.sleep(10)
        # add user contacts
        self.add_contacts()

        # online notification
        response = requests.post(self.url, data={'user': str(self.valid_user_1), 'event': '1'})
        res = json.loads(response.content)
        assert_equal(response.status_code, app_settings.STATUS_200)
        assert_equal(res['info'], app_settings.SUCCESS_RESPONSE)
        assert_equal(res['status'], app_settings.STATUS_200)

        time.sleep(10)
        # check if status set in database
        query = " SELECT status FROM users WHERE username=%s;"
        variables = (str(self.valid_user_1),)
        try:
            result = db_handler.QueryHandler.get_results(query, variables)
            assert_equal(len(result), 1)
            assert_equal(result[0]['status'], '1')
        except Exception as e:
            raise e

        # offline notification
        response = requests.post(self.url, data={'user': str(self.valid_user_1), 'event': '0'})
        res = json.loads(response.content)
        assert_equal(response.status_code, app_settings.STATUS_200)
        assert_equal(res['info'], app_settings.SUCCESS_RESPONSE)
        assert_equal(res['status'], app_settings.STATUS_200)

        time.sleep(10)
        # check if status set in database
        query = " SELECT status FROM users WHERE username=%s;"
        variables = (str(self.valid_user_1),)
        try:
            result = db_handler.QueryHandler.get_results(query, variables)
            assert_equal(len(result), 1)
            assert_equal(result[0]['status'], '0')
        except Exception as e:
            raise e
