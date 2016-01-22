import base64
import json
import os
import string
import sys
import tornado
import tornado.escape
import tornado.httpclient
import tornado.ioloop
import tornado.web

sys.path.append(os.path.dirname(os.path.abspath(__file__)).rsplit('/', 1)[0])
import errors, media_publisher, message_publisher, utils
from project import db_handler, app_settings, rabbitmq_utils


class SendMessageToContact(tornado.web.RequestHandler):

    def data_validation(self, sender, receiver, message=''):
        response = {'info': '', 'status': 0}
        try:
            # Sender invalid
            query = " SELECT id FROM users WHERE username = %s;"
            variables = (sender,)
            result = db_handler.QueryHandler.get_results(query, variables)
            if not result:
                response['info'] = errors.INVALID_SENDER_SIMPLE_CHAT_ERR
                response['status'] = app_settings.STATUS_404

            # Receiver invalid
            query = " SELECT id from users WHERE username = %s;"
            variables = (receiver,)
            result = db_handler.QueryHandler.get_results(query, variables)
            if response['status'] == 0 and not result:
                response['info'] = errors.INVALID_RECEIVER_SIMPLE_CHAT_ERR
                response['status'] = app_settings.STATUS_404

            # No message present
            if response['status'] == 0 and message == '':
                response['info'] = errors.INVALID_MESSAGE_SIMPLE_CHAT_ERR
                response['status'] = app_settings.STATUS_404

        except Exception as e:
            response['info'] = " Error: %s" % e
            response['status'] = app_settings.STATUS_500
        finally:
            return (response['info'], response['status'])

    def post(self):
        response = {}
        try:
            sender = str(self.get_argument("sender", ''))
            receiver = str(self.get_argument("receiver", ''))
            message = str(self.get_argument("message", ''))
            response['info'], response['status'] = self.data_validation(sender, receiver, message)

            if not response['status'] in app_settings.ERROR_CODES_LIST:
                client_id = "simple_chat/" + utils.generate_random_client_id(12)
                user_data = msg_data = {'topic': 'simple_chat_' + receiver + '.' + sender, 'sender': sender,
                                        'receiver': receiver, 'message': sender + ':' + receiver + ':' + message}
                message_publisher.simple_chat_publisher(client_id, user_data)
                response['status'] = app_settings.STATUS_200
                response['info'] = app_settings.SUCCESS_RESPONSE
        except Exception as e:
            response['info'] = " Error: %s" % e
            response['status'] = app_settings.STATUS_500
        finally:
            self.write(response)


# @tornado.web.stream_request_body
class SendMediaToContact(tornado.web.RequestHandler):

    def data_validation(self, info):
        response = {'info': '', 'status': 0}
        try:
            # sender invalid
            query = " SELECT id FROM users WHERE username = %s;"
            variables = (info.get('sender', ''),)
            result = db_handler.QueryHandler.get_results(query, variables)
            if not result:
                response['info'] = errors.INVALID_SENDER_SIMPLE_CHAT_ERR
                response['status'] = app_settings.STATUS_404

            # Receiver invalid
            if response['status'] == 0:
                query = " SELECT id FROM users WHERE username = %s;"
                variables = (info.get('receiver', ''),)
                result = db_handler.QueryHandler.get_results(query, variables)
                if not result:
                    response['info'] = errors.INVALID_RECEIVER_SIMPLE_CHAT_ERR
                    response['status'] = app_settings.STATUS_404

            # Invalid filename
            if response['status'] == 0:
                if info.get('name') and os.path.exists('media/' + str(info.get('name'))):
                    response['info'] = errors.SAME_NAME_MEDIA_ALREADY_EXISTS_ERR
                    response['status'] = app_settings.STATUS_500
                elif not info.get('name'):
                    response['info'] = errors.INVALID_MEDIA_NAME_ERR
                    response['status'] = app_settings.STATUS_404

        except Exception as e:
            response['info'] = " Error: %s" % e
            response['status'] = app_settings.STATUS_500
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
            if response['status'] not in [app_settings.STATUS_404, app_settings.STATUS_500]:
                media_file = open(file_name, 'w')
                media_file.write(file_content)
                media_file.flush()

                # publish the media
                client_id = 'simple_media/' + utils.generate_random_client_id(13)
                user_data = {'topic': 'simple_media_' + receiver + '.' + sender,
                             'message': sender + ':' + receiver + ':' + file_name}
                media_publisher.simple_chat_media_publisher(client_id, user_data)

                response['status'] = app_settings.STATUS_200
                response['info'] = app_settings.SUCCESS_RESPONSE

        except Exception as e:
            response['info'] = " Error: %s" % e
            response['status'] = app_settings.STATUS_500
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
                response['status'] = app_settings.STATUS_400
                self.write(response)
        except Exception, e:
            response['status'] = app_settings.STATUS_500
            response['info'] = 'Error is: %s' % e
            self.write(response)
