import base64
import json
import os
import random
import requests
import string
import shutil
import sys
import time
import unittest
from nose.tools import *

sys.path.append(os.path.dirname(os.path.abspath(__file__)).rsplit('/', 1)[0])

from chat.errors import *
from chat.media_subscriber import *
from chat.message_subscriber import *
from project.rabbitmq_tests import *
from project.test_utilities import *


class SendMessageToContactTests(unittest.TestCase):
    url = None
    sender = 911111111111
    receiver = 912222222222
    users = None
    exchanges = None
    channel = None
    msg_count = 51
    senders_count = 51
    receivers_count = 21

    def create_exchanges(self):
        self.channel = get_rabbitmq_connection()
        for name in self.exchanges:
            self.channel.exchange_declare(exchange=name, type='topic', durable=True, auto_delete=False)

    def delete_exchanges(self):
        for name in self.exchanges:
            self.channel.exchange_delete(exchange=name)

    def setUp(self):
        self.url = SIMPLE_CHAT_SEND_MESSAGE_URL
        self.users = [self.sender, self.receiver]
        self.exchanges = [SIMPLE_CHAT_MESSAGES_EXCHANGE, SIMPLE_CHAT_MESSAGE_RECEIVED_EXCHANGE]
        delete_users()     # delete all users created from any of the previous tests
        create_users(self.users)   # create users
        self.create_exchanges()
        delete_chat_messages()

    def test_validation(self):

        # Invalid sender
        response = requests.post(self.url, data={'sender': '', 'receiver': self.receiver, 'message': 'test_message_1'})
        res = json.loads(response.content)
        assert_equal(response.status_code, STATUS_200)
        assert_equal(res['info'], INVALID_SENDER_SIMPLE_CHAT_ERR)
        assert_equal(res['status'], STATUS_404)

        # Invalid receiver
        response = requests.post(self.url, data={'sender': self.sender, 'receiver': '917777777777', 'message': ''})
        res = json.loads(response.content)
        assert_equal(response.status_code, STATUS_200)
        assert_equal(res['info'], INVALID_RECEIVER_SIMPLE_CHAT_ERR)
        assert_equal(res['status'], STATUS_404)

        # No msg present
        response = requests.post(self.url, data={'sender': self.sender, 'receiver': self.receiver})
        res = json.loads(response.content)
        assert_equal(response.status_code, STATUS_200)
        assert_equal(res['info'], INVALID_MESSAGE_SIMPLE_CHAT_ERR)
        assert_equal(res['status'], STATUS_404)

    def test_post(self):

        # result = self.channel.queue_declare()
        # self.channel.queue_bind(exchange=SIMPLE_CHAT_MESSAGES_EXCHANGE, queue=result.method.queue,
        #                        routing_key='simple_chat_' + str(self.receiver) + '.*' )

        # start chat message subscriber
        simple_chat_subscriber(client_id="testing/" + generate_random_client_id(8), user_data={'topic': 'simple_chat_' + str(self.receiver) + '.*',
                                                                                               'receiver': str(self.receiver)})

        time.sleep(10)
        response = requests.post(self.url, data={'sender': str(self.sender), 'receiver': str(self.receiver),
                                                 'message': 'test_message_3'})
        res = json.loads(response.content)
        assert_equal(response.status_code, STATUS_200)
        assert_equal(res['info'], SUCCESS_RESPONSE)
        assert_equal(res['status'], STATUS_200)

        time.sleep(20)
        # check if message reached to the database
        query = "SELECT single_tick, double_tick FROM chat_messages WHERE sender=%s AND receiver=%s AND message=%s;"
        variables = (str(self.sender), str(self.receiver), 'test_message_3')
        try:
            result = QueryHandler.get_results(query, variables)
            assert_equal(len(result), 1)
            assert_equal(result[0]['single_tick'], 'done')
            assert_equal(result[0]['double_tick'], 'done')
        except Exception as e:
            raise e

    def test_multiple_msg_single_sender_single_receiver(self):

        # start chat message subsriber
        simple_chat_subscriber(client_id="testing/" + generate_random_client_id(8),
                               user_data={'topic': 'simple_chat_' + str(self.receiver) + '.*',
                                          'receiver': str(self.receiver)})


        time.sleep(10)
        msgs_list = ['msg_' + str(index) for index in range(1,self.msg_count)]
        for msg in msgs_list:
            response = requests.post(self.url, data={'sender': str(self.sender), 'receiver': str(self.receiver),
                                                     'message': msg})
            res = json.loads(response.content)
            assert_equal(response.status_code, STATUS_200)
            assert_equal(res['info'], SUCCESS_RESPONSE)
            assert_equal(res['status'], STATUS_200)

        time.sleep(20)
        # check if all messages have reached to the server and subscribers.
        for msg in msgs_list:
            query = "SELECT single_tick, double_tick FROM chat_messages WHERE sender=%s AND receiver=%s AND message=%s;"
            variables = (str(self.sender), str(self.receiver), msg)
            try:
                result = QueryHandler.get_results(query, variables)
                assert_equal(len(result), 1)
                assert_equal(result[0]['single_tick'], 'done')
                assert_equal(result[0]['double_tick'], 'done')
            except Exception as e:
                raise e

    def test_multiple_senders_single_receiver(self):

        # start chat message subscriber
        simple_chat_subscriber(client_id="testing/" + generate_random_client_id(8), user_data={'topic': 'simple_chat_' + str(self.receiver) + '.*',
                                                                                               'receiver': str(self.receiver)})

        message_to_send = 'test_message'
        senders_list = []
        for sender in range(1, self.senders_count):
            senders_list.append('91' + "".join(random.choice(string.digits) for _ in range(10)))

        # create senders in 'users' table
        create_users(senders_list)

        for sender in senders_list:
            response = requests.post(self.url, data={'sender': str(sender), 'receiver': str(self.receiver),
                                                     'message': message_to_send})
            res = json.loads(response.content)
            assert_equal(response.status_code, STATUS_200)
            assert_equal(res['info'], SUCCESS_RESPONSE)
            assert_equal(res['status'], STATUS_200)

        time.sleep(20)
        # check if all messages have reached to the server and subscribers.
        for sender in senders_list:
            query = "SELECT single_tick, double_tick FROM chat_messages WHERE sender=%s AND receiver=%s AND message=%s;"
            variables = (str(sender), str(self.receiver), message_to_send)
            try:
                result = QueryHandler.get_results(query, variables)
                assert_equal(len(result), 1)
                assert_equal(result[0]['single_tick'], 'done')
                assert_equal(result[0]['double_tick'], 'done')
            except Exception as e:
                raise e

    def test_single_sender_multiple_receivers(self):

        receivers_list = []
        for receiver in range(1, self.receivers_count):
            receivers_list.append('91' + "".join(random.choice(string.digits) for _ in range(10)))

        # create receivers in 'users' table
        create_users(receivers_list)

        # start chat message subscriber for each of the receiver
        for receiver in receivers_list:
            simple_chat_subscriber(client_id="testing/" + generate_random_client_id(8), user_data={'topic': 'simple_chat_' + str(receiver) + '.*',
                                                                                               'receiver': str(receiver)})
            time.sleep(5)

        message_to_send = 'test_message'
        for receiver in receivers_list:
            response = requests.post(self.url, data={'sender': str(self.sender), 'receiver': str(receiver),
                                                     'message': message_to_send})
            res = json.loads(response.content)
            assert_equal(response.status_code, STATUS_200)
            assert_equal(res['info'], SUCCESS_RESPONSE)
            assert_equal(res['status'], STATUS_200)

        time.sleep(20)
        # check if all messages have reached to the server and subscribers.
        for receiver in receivers_list:
            query = "SELECT single_tick, double_tick FROM chat_messages WHERE sender=%s AND receiver=%s AND message=%s;"
            variables = (str(self.sender), str(receiver), message_to_send)
            try:
                result = QueryHandler.get_results(query, variables)
                assert_equal(len(result), 1)
                assert_equal(result[0]['single_tick'], 'done')
                assert_equal(result[0]['double_tick'], 'done')
            except Exception as e:
                raise e

    def test_multiple_senders_multiple_receivers(self):

        senders_list = []
        for sender in range(1, self.senders_count):
            senders_list.append('91' + "".join(random.choice(string.digits) for _ in range(10)))

        receivers_list = []
        for receiver in range(1, self.receivers_count):
            receivers_list.append('91' + "".join(random.choice(string.digits) for _ in range(10)))

        assert_not_equal(senders_list, receivers_list)

        # create 'senders' and 'receivers' as valid users
        create_users(senders_list)
        create_users(receivers_list)

        # start chat message subscriber for each of the receiver
        for receiver in receivers_list:
            simple_chat_subscriber(client_id="testing/" + generate_random_client_id(8), user_data={'topic': 'simple_chat_' + str(receiver) + '.*',
                                                                                               'receiver': str(receiver)})
            time.sleep(5)

        for i in range(1, 51):
            sender = random.choice(senders_list)
            receiver = random.choice(receivers_list)
            message = "".join(random.choice(string.ascii_letters) for _ in range(5))
            response = requests.post(self.url, data={'sender': str(sender), 'receiver': str(receiver),
                                                     'message': message})

            res = json.loads(response.content)
            assert_equal(response.status_code, STATUS_200)
            assert_equal(res['info'], SUCCESS_RESPONSE)
            assert_equal(res['status'], STATUS_200)

        time.sleep(20)
        query = " SELECT id FROM chat_messages WHERE double_tick='';"
        result = QueryHandler.get_results(query)
        assert_equal(len(result), 0)


class SendMediaToContactTests(unittest.TestCase):
    url = None
    sender = 911111111111
    receiver = 912222222222
    users = None
    exchanges = None
    channel = None
    media_path = None
    media_count = 6
    senders_count = 21
    receivers_count = 21

    def create_exchanges(self):
        self.channel = get_rabbitmq_connection()
        for name in self.exchanges:
            self.channel.exchange_declare(exchange=name, type='topic', durable=True, auto_delete=False)

    def delete_exchanges(self):
        self.channel = get_rabbitmq_connection()
        try:
            for name in self.exchanges:
                self.channel.exchange_delete(exchange=name)
        except Exception as e:
            raise e

    def delete_media_files(self):
        media_files = os.listdir(self.media_path)
        for file in media_files:
            os.remove(self.media_path + file)

    def make_post_request(self, file_name):
        file_content = open(file_name, 'r').read()
        content = {'sender': str(self.sender), 'receiver': str(self.receiver), 'name': str(file_name),
                   'body': base64.b64encode(file_content)}
        response = requests.post(self.url, data=json.dumps(content))
        return response

    def setUp(self):
        self.url = SIMPLE_CHAT_SEND_MEDIA_URL
        self.media_path = 'media/'
        self.media_files = {
            'image': 'test_image.jpg',
            'pdf': 'test_pdf.pdf',
            'audio': 'test_audio.mp3',
            'video': 'test_video.mp4',
            'rar': 'test_rar.rar',
        }
        self.users = [self.sender, self.receiver]
        self.exchanges = [SIMPLE_CHAT_MEDIA_EXCHANGE]

        # delete irrelevant users, exchanges, queues and chat messages
        delete_users()
        delete_chat_messages()
        self.delete_exchanges()
        delete_queues()
        self.delete_media_files()

        # create required users and exchange(s)
        create_users(self.users)
        self.create_exchanges()

    def test_validation(self):

        # Invalid sender
        content = {'sender': '910000000000', 'receiver': str(self.receiver), 'name': self.media_files['image']}
        response = requests.post(self.url, data=json.dumps(content))
        res = json.loads(response.content)
        assert_equal(response.status_code, STATUS_200)
        assert_equal(res['info'], INVALID_SENDER_SIMPLE_CHAT_ERR)
        assert_equal(res['status'], STATUS_404)

        # Invalid receiver
        content = {'sender': str(self.sender), 'receiver': '910000000000', 'name': self.media_files['image']}
        response = requests.post(self.url, data=json.dumps(content))
        res = json.loads(response.content)
        assert_equal(response.status_code, STATUS_200)
        assert_equal(res['info'], INVALID_RECEIVER_SIMPLE_CHAT_ERR)
        assert_equal(res['status'], STATUS_404)

        # Media name not given
        content = {'sender': str(self.sender), 'receiver': str(self.receiver)}
        response = requests.post(self.url, data=json.dumps(content))
        res = json.loads(response.content)
        assert_equal(response.status_code, STATUS_200)
        assert_equal(res['info'], INVALID_MEDIA_NAME_ERR)
        assert_equal(res['status'], STATUS_404)

        # Same media already exists
        shutil.copyfile('test_image.jpg', 'media/test_image.jpg')
        content = {'sender': str(self.sender), 'receiver': str(self.receiver), 'name': self.media_files['image']}
        response = requests.post(self.url, data=json.dumps(content))
        res = json.loads(response.content)
        assert_equal(response.status_code, STATUS_200)
        assert_equal(res['info'], SAME_NAME_MEDIA_ALREADY_EXISTS_ERR)
        assert_equal(res['status'], STATUS_500)

    def test_post(self):
        # test uploading image, pdf, audio, video, rar
        for key, value in self.media_files.items():
            file_name = value
            response = self.make_post_request(file_name)
            res = json.loads(response.content)
            assert_equal(res['info'], SUCCESS_RESPONSE)
            assert_equal(res['status'], STATUS_200)
        assert_equal(len(os.listdir(self.media_path)), len(self.media_files))

    def test_publisher_subscriber(self):
        # start simple chat media subsciber
        simple_chat_media_subscriber(client_id="testing/" + generate_random_client_id(8),
                                     user_data={'topic': 'simple_media_' + str(self.receiver) + '.*',
                                                'receiver': str(self.receiver)})

        time.sleep(10)

        file_name = self.media_files['image']
        response = self.make_post_request(file_name)
        res = json.loads(response.content)
        assert_equal(res['info'], SUCCESS_RESPONSE)
        assert_equal(res['status'], STATUS_200)

        time.sleep(20)
        # check if media has reached to the server and subcriber.
        query = "SELECT * FROM chat_messages WHERE sender=%s AND receiver=%s AND message=%s;"
        variables = (str(self.sender), str(self.receiver), self.media_path + file_name)
        try:
            result = QueryHandler.get_results(query, variables)
            assert_equal(len(result), 1)
            assert_equal(result[0]['is_media_message'], True)
            assert_equal(result[0]['single_tick'], 'done')
            assert_equal(result[0]['double_tick'], 'done')
        except Exception as e:
            raise e

    def test_multiple_msg_single_sender_single_receiver(self):

        # ensure 'test_media/' is non-empty
        assert_not_equal(os.listdir('test_media/'), [])

        # start chat message subsriber
        simple_chat_media_subscriber(client_id="testing/" + generate_random_client_id(8),
                               user_data={'topic': 'simple_media_' + str(self.receiver) + '.*',
                                          'receiver': str(self.receiver)})
        time.sleep(5)

        msgs_list = ['test_image_{}.jpeg'.format(str(index)) for index in range(1, self.media_count)]
        for msg in msgs_list:
            shutil.copyfile('test_media/' + msg, msg)
            file_content = open(msg, 'r').read()
            content = {'sender': str(self.sender), 'receiver': str(self.receiver), 'name': msg,
                       'body': base64.b64encode(file_content)}
            response = requests.post(self.url, data=json.dumps(content))
            res = json.loads(response.content)
            assert_equal(response.status_code, STATUS_200)
            assert_equal(res['info'], SUCCESS_RESPONSE)
            assert_equal(res['status'], STATUS_200)

            # remove the copied media
            os.remove(msg)

        time.sleep(20)
        # check if all messages have reached to the server and subscribers.
        for msg in msgs_list:
            query = "SELECT * FROM chat_messages WHERE sender=%s AND receiver=%s AND message=%s;"
            variables = (str(self.sender), str(self.receiver), self.media_path + msg)
            try:
                result = QueryHandler.get_results(query, variables)
                assert_equal(len(result), 1)
                assert_equal(result[0]['is_media_message'], True)
                assert_equal(result[0]['single_tick'], 'done')
                assert_equal(result[0]['double_tick'], 'done')
            except Exception as e:
                raise e

    def test_multiple_senders_single_receiver(self):

        # start chat message subscriber
        simple_chat_media_subscriber(client_id="testing/" + generate_random_client_id(8),
                               user_data={'topic': 'simple_media_' + str(self.receiver) + '.*',
                                        'receiver': str(self.receiver)})

        media_files = os.listdir('test_media/')
        filename = media_files[0]
        shutil.copyfile('test_media/' + filename, filename)
        file_content = open(filename, 'r').read()

        senders_list = []
        for sender in range(1, self.senders_count):
            senders_list.append('91' + "".join(random.choice(string.digits) for _ in range(10)))

        # create senders in 'users' table
        create_users(senders_list)

        for sender in senders_list:
            content = {'sender': str(sender), 'receiver': str(self.receiver), 'name': filename,
                       'body': base64.b64encode(file_content)}
            response = requests.post(self.url, data=json.dumps(content))
            res = json.loads(response.content)
            assert_equal(response.status_code, STATUS_200)
            assert_equal(res['info'], SUCCESS_RESPONSE)
            assert_equal(res['status'], STATUS_200)
            os.remove('media/' + filename)

        time.sleep(20)
        # check if all messages have reached to the server and subscribers.
        for sender in senders_list:
            query = "SELECT single_tick, double_tick FROM chat_messages WHERE sender=%s AND receiver=%s AND message=%s;"
            variables = (str(sender), str(self.receiver), 'media/' + filename)
            try:
                result = QueryHandler.get_results(query, variables)
                assert_equal(len(result), 1)
                assert_equal(result[0]['single_tick'], 'done')
                assert_equal(result[0]['double_tick'], 'done')
            except Exception as e:
                raise e
        os.remove(filename)

    def test_single_sender_multiple_receivers(self):

        receivers_list = []
        for receiver in range(1, self.receivers_count):
            receivers_list.append('91' + "".join(random.choice(string.digits) for _ in range(10)))

        # create receivers in 'users' table
        create_users(receivers_list)

        # start chat message subscriber for each of the receiver
        for receiver in receivers_list:
            simple_chat_media_subscriber(client_id="testing/" + generate_random_client_id(8),
                                         user_data={'topic': 'simple_media_' + str(receiver) + '.*',
                                                    'receiver': str(receiver)})
            time.sleep(5)

        media_files = os.listdir('test_media/')
        filename = random.choice(media_files)
        shutil.copyfile('test_media/' + filename, filename)
        file_content = open(filename, 'r').read()

        for receiver in receivers_list:
            content = {'sender': str(self.sender), 'receiver': str(receiver), 'name': filename,
                       'body': base64.b64encode(file_content)}
            response = requests.post(self.url, data=json.dumps(content))
            res = json.loads(response.content)
            assert_equal(response.status_code, STATUS_200)
            assert_equal(res['info'], SUCCESS_RESPONSE)
            assert_equal(res['status'], STATUS_200)
            os.remove('media/' + filename)

        time.sleep(20)
        # check if all messages have reached to the server and subscribers.
        for receiver in receivers_list:
            query = "SELECT single_tick, double_tick FROM chat_messages WHERE sender=%s AND receiver=%s AND message=%s;"
            variables = (str(self.sender), str(receiver), 'media/' + filename)
            try:
                result = QueryHandler.get_results(query, variables)
                assert_equal(len(result), 1)
                assert_equal(result[0]['single_tick'], 'done')
                assert_equal(result[0]['double_tick'], 'done')
            except Exception as e:
                raise e
        os.remove(filename)

    def test_multiple_senders_multiple_receivers(self):

        senders_list = []
        for sender in range(1, self.senders_count):
            senders_list.append('91' + "".join(random.choice(string.digits) for _ in range(10)))

        receivers_list = []
        for receiver in range(1, self.receivers_count):
            receivers_list.append('91' + "".join(random.choice(string.digits) for _ in range(10)))

        assert_not_equal(senders_list, receivers_list)

        # create 'senders' and 'receivers' as valid users
        create_users(senders_list)
        create_users(receivers_list)

        media_files = os.listdir('test_media/')

        # start chat message subscriber for each of the receiver
        for receiver in receivers_list:
            simple_chat_subscriber(client_id="testing/" + generate_random_client_id(8),
                                   user_data={'topic': 'simple_media_' + str(receiver) + '.*',
                                              'receiver': str(receiver)})
            time.sleep(10)

        for i in range(1, 21):
            sender = random.choice(senders_list)
            receiver = random.choice(receivers_list)
            filename = random.choice(media_files)
            shutil.copyfile('test_media/' + filename, filename)
            file_content = open(filename, 'r').read()
            content = {'sender': str(self.sender), 'receiver': str(receiver), 'name': filename,
                       'body': base64.b64encode(file_content)}
            response = requests.post(self.url, data=json.dumps(content))
            res = json.loads(response.content)
            assert_equal(response.status_code, STATUS_200)
            assert_equal(res['info'], SUCCESS_RESPONSE)
            assert_equal(res['status'], STATUS_200)
            os.remove(filename)
            os.remove('media/' + filename)

        time.sleep(20)
        query = " SELECT id FROM chat_messages WHERE double_tick='';"
        result = QueryHandler.get_results(query)
        assert_equal(len(result), 0)
