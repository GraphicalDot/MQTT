import base64
import json
import os

import tornado
import tornado.escape
import tornado.httpclient
import tornado.ioloop
import tornado.web

from errors import *
from media_utils import *
from project.rabbitmq_utils import *
from utils import *


class SendMessageToContact(tornado.web.RequestHandler):

    def data_validation(self, sender, receiver, message=''):
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


@tornado.web.stream_request_body
class SendMediaToContact(tornado.web.RequestHandler):

    def data_validation(self, info):
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
                response['status'] = 404

                # Media already exists with same name
                # print 'path:', os.path
                # if os.path.isfile(info.get('name')):
                #     response['info'] = " Error: Media with same name already exists!"
                #     response['status'] = 404

        except Exception as e:
            response['info'] = " Error: %s" % e
            response['status'] = 500
        finally:
            return (response['info'], response['status'])

    def post(self):     # post without stream header
        response = {}
        try:
            request_info = json.loads(self.request.body)
            (response['info'], response['status']) = self.data_validation(request_info)
            file_name = "media/" + str(request_info.get('name', ''))
            file_content = base64.b64decode(request_info.get('body', ''))
            sender = str(request_info.get('sender', ''))
            receiver = str(request_info.get('receiver', ''))
            if response['status'] not in [404, 500]:
                media_file = open(file_name, 'w')
                media_file.write(file_content)
                media_file.flush()

                # publish the media
                client_id = 'simple_media/' + "".join(random.choice("0123456789ADCDEF") for x in range(23-13))
                user_data = {'topic': 'group_media_' + receiver + '.' + sender,
                             'message': sender + ':' + receiver + ':' + file_name}
                publish_simple_chat_media(client_id, user_data)

                response['status'] = 200
                response['info'] = 'Success'

        except Exception as e:
            response['info'] = " Error: %s" % e
            response['status'] = 500
        finally:
            self.write(response)

    def get(self):
        response = {}
        file_name = "media/" + str(self.get_argument("name", ''))
        try:
            if os.path.isfile(file_name):
                with open(file_name, 'r') as file_content:
                    while 1:
                        data = file_content.read(16384) # or some other nice-sized chunk
                        if not data: break
                        self.write(data)
                    file_content.close()
                    self.finish()
            else:
                response['info'] = 'Not Found'
                response['status'] = 400
                self.write(response)
        except Exception, e:
            response['status'] = 500
            response['info'] = 'error is: %s' % e
            self.write(response)

    # def get(self):
    #     print "inside get of SendMediaToContact"
    #     response = {}
    #     try:
    #         file_name = "media/" + str(self.get_argument('name', ''))
    #         file_content = base64.b64decode(self.get_argument('body', ''))
    #         print 'file content:', file_content
    #         sender = str(self.get_argument('sender', ''))
    #         receiver = str(self.get_argument('receiver', ''))
    #         if response['status'] not in [404, 500]:
    #             media_file = open(file_name, 'w')
    #             media_file.write(file_content)
    #             media_file.flush()
    #
    #             # publish the media
    #             client_id = 'simple_media/' + "".join(random.choice("0123456789ADCDEF") for x in range(23-13))
    #             user_data = {'topic': 'group_media_' + receiver + '.' + sender,
    #                          'message': sender + ':' + receiver + ':' + file_name}
    #             publish_simple_chat_media(client_id, user_data)
    #
    #             response['status'] = 200
    #             response['info'] = 'Success'
    #
    #     except Exception as e:
    #         response['info'] = " Error: %s" % e
    #         response['status'] = 500
    #     finally:
    #         self.write(response)

