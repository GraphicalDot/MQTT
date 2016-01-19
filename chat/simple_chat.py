import base64
import json
import os
import string
import tornado
import tornado.escape
import tornado.httpclient
import tornado.ioloop
import tornado.web

from chat.errors import *
from chat.media_utils import *
from chat.mqtt_publisher import *
from chat.utils import *
from project.rabbitmq_utils import *


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
                response['status'] = STATUS_404

            # Receiver invalid
            query = " SELECT id from users WHERE username = %s;"
            variables = (receiver,)
            result = QueryHandler.get_results(query, variables)
            if response['status'] == 0 and not result:
                response['info'] = INVALID_RECEIVER_SIMPLE_CHAT_ERR
                response['status'] = STATUS_404

            # No message present
            if response['status'] == 0 and message == '':
                response['info'] = INVALID_MESSAGE_SIMPLE_CHAT_ERR
                response['status'] = STATUS_404

        except Exception as e:
            response['info'] = " Error: %s" % e
            response['status'] = STATUS_500
        finally:
            return (response['info'], response['status'])

    def generate_random_client_id(self, len):
        return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(23-len))

    def post(self):
        response = {}
        try:
            sender = str(self.get_argument("sender", ''))
            receiver = str(self.get_argument("receiver", ''))
            message = str(self.get_argument("message", ''))
            response['info'], response['status'] = self.data_validation(sender, receiver, message)

            if not response['status'] in ERROR_CODES_LIST:
                client_id = "simple_chat/" + generate_random_client_id(12)
                user_data = msg_data = {'topic': 'simple_chat_' + receiver + '.' + sender, 'sender': sender,
                                        'receiver': receiver, 'message': sender + ':' + receiver + ':' + message}
                simple_chat_publisher(client_id, user_data)

                response['status'] = STATUS_200
                response['info'] = SUCCESS_RESPONSE
        except Exception as e:
            response['info'] = " Error: %s" % e
            response['status'] = STATUS_500
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

