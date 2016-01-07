import base64
import json
import os
import random
import string
import tornado
import tornado.escape
import tornado.httpclient
import tornado.ioloop
import tornado.web

from db_handler import *
from errors import *
from app_settings import *
from utils import *
from group_chat.rabbitmq_utils import *


class SendMessageToContact(tornado.web.RequestHandler):

    def data_validation(self, sender, receiver, message=''):
        print "inside data validation"
        response = {'info': '', 'status': 0}
        try:
            # Sender invalid
            query = " SELECT id FROM users WHERE username = %s;"
            variables = (sender,)
            result = QueryHandler.get_results(query, variables)
            if not result:
                response['info'] = INVALID_SENDER_SIMPLE_CHAT_ERR
                response['status'] = 404

            # Receiver invalid
            query = " SELECT id from users WHERE username = %s;"
            variables = (receiver,)
            result = QueryHandler.get_results(query, variables)
            if not result:
                response['info'] = INVALID_RECEIVER_SIMPLE_CHAT_ERR
                response['status'] = 404

            # No message present
            if message == '':
                response['info'] = INVALID_MESSAGE_SIMPLE_CHAT_ERR
                response['status'] = 404

        except Exception as e:
            response['info'] = " Error: %s" % e
            response['status'] = 500
        finally:
            return (response['info'], response['status'])

    def generate_random_client_id(self):
        # return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
        return "paho/" + "".join(random.choice("0123456789ADCDEF") for x in range(23-5))

    def initiate_simple_chat_single_tick_subscriber(self):
        print '*' * 10
        print "inside initiate_simple_chat_single_tick_subscriber"
        try:
            routing_key = 'single_tick.' + BROKER_USERNAME
            channel = get_rabbitmq_connection()
            result = channel.queue_declare()
            channel.queue_bind(exchange=SIMPLE_CHAT_SINGLE_TICK_EXCHANGE, queue=result.method.queue, routing_key=routing_key)
            # client_id = 'single_tick_' + user[2:]
            client_id = self.generate_random_client_id()
            subscribe_simple_chat_single_tick(client_id=client_id, user_data={'topic': routing_key})
        except Exception as e:
            raise e

    def initiate_simple_chat_double_tick_subscriber(self):
        print "inside initiate_simple_chat_double_tick_subscriber"
        try:
            routing_key = 'double_tick.' + BROKER_USERNAME
            channel = get_rabbitmq_connection()
            result = channel.queue_declare()
            channel.queue_bind(exchange=SIMPLE_CHAT_DOUBLE_TICK_EXCHANGE, queue=result.method.queue, routing_key=routing_key)
            # client_id = 'double_tick_' + user[2:]
            client_id = self.generate_random_client_id()
            subscribe_simple_chat_double_tick(client_id=client_id, user_data={'topic': routing_key})
        except Exception as e:
            raise e

    def get(self):
        print "inside get of SendMessageToContact"
        response = {}
        try:
            sender = str(self.get_argument("sender", ''))
            receiver = str(self.get_argument("receiver", ''))
            message = str(self.get_argument("message", ''))
            (response['info'], response['status']) = self.data_validation(sender, receiver, message)

            if not response['status'] in [404, 400, 500]:
                # start single tick subscriber for the message
                self.initiate_simple_chat_single_tick_subscriber()

                # start double tick subscriber for the message
                self.initiate_simple_chat_double_tick_subscriber()

                # TODO: start double colored tick subscriber for the message

                client_id = sender[2:] + "to" + receiver[2:]
                user_data = {'topic': 'simple_chat_' + receiver + '.' + sender , 'sender': sender,
                             'receiver': receiver, 'message': sender + ':' + receiver + ':' + message}
                publish_to_simple_chat(client_id, user_data)

        except Exception as e:
            response['info'] = " Error: %s" % e
            response['status'] = 500
        finally:
            self.write(response)


class SendMediaToContact(tornado.web.RequestHandler):

    def data_validation(self, info):
        print "inside data_validation"
        response = {'info': '', 'status': 0}
        try:
            # sender invalid
            query = " SELECT id FROM users WHERE username = %s;"
            variables = (info.get('sender', ''),)
            result = QueryHandler.get_results(query, variables)
            if not result:
                response['info'] = INVALID_SENDER_SIMPLE_CHAT_ERR
                response['status'] = 404

            # Receiver invalid
            query = " SELECT id FROM users WHERE username = %s;"
            variables = (info.get('receiver', ''),)
            result = QueryHandler.get_results(query, variables)
            if not result:
                response['info'] = INVALID_RECEIVER_SIMPLE_CHAT_ERR
                response['status'] = 404

            # Invalid filename
            if not info.get('name'):
                response['info'] = " Error: Media Name not given!"

            # Media already exists with same name
            if os.path.isfile(info.get('name')):
                response['info'] = " Error: Media with same name already exists!"
                response['status'] = 404

        except Exception as e:
            response['info'] = " Error: %s" % e
            response['status'] = 500
        finally:
            return (response['info'], response['status'])


    def post(self):  # change to post later on
        print "inside get of SendMediaToContact"
        response = {}
        try:
            request_info = json.loads(self.request.body)
            (response['info'], response['status']) = self.data_validation(request_info)

            sender = str(request_info.get('sender', ''))
            receiver = str(request_info.get('receiver', ''))
            file_content = base64.b64decode(request_info.get('body', ''))
            file_name = "media/" + request_info.get('name', '')

            if os.path.isfile(file_name):
                response['info'] = "Error: Media with same name already exists!"
                response['status'] = 500
            else:
                media_file = open(file_name, 'w')
                media_file.write(file_content)
                media_file.flush()

                # publish the media
                client_id =
                publish_simple_chat_media(client_id, user_data)

                response['info'] = "Success"
                response['status'] = 200
        except Exception as e:
            response['info'] = " Error: %s" % e
            response['status'] = 500
        finally:
            self.write(response)

