import phonenumbers
import random
import string
import tornado
import tornado.web

from chat.media_utils import *
from chat.mqtt_subscriber import *
from chat.utils import *
from project.rabbitmq_utils import *
from registration.errors import *
from registration.utils import *


class RegisterUser(tornado.web.RequestHandler):

    def data_validation(self, number):
        response = {'info': '', 'status': 0}

        # Number not provided
        if not number:
            response['info'] = INVALID_REGISTRATION_NUMBER_ERR
            response['status'] = STATUS_404

        try:
            if response['status'] == 0:
                if len(number) == 10:
                    number = '+91' + number
                elif len(number) > 10:
                    number = '+' + number

                parsed_number = phonenumbers.parse(number, None)

                # Incorrect number of digits
                if not phonenumbers.is_possible_number(parsed_number):
                    response['info'] = WRONG_DIGITS_ERR
                    response['status'] = STATUS_404

            # Invalid Number
            if response['status'] == 0 and not phonenumbers.is_valid_number(parsed_number):
                response['info'] = INVALID_REGISTRATION_NUMBER_ERR
                response['status'] = STATUS_404

        except phonenumbers.NumberParseException as e:
            response['info'] = " Error: %s" % e
            response['status'] = STATUS_500
        finally:
            return (response['info'], response['status'])

    def get(self):
        response = {}
        try:
            number = str(self.get_argument("phone_number", ''))
            (response['info'], response['status']) = self.data_validation(number)

            if response['status'] not in ERROR_CODES_LIST:
                username = str.strip(number)
                user = User(username)
                response['info'], response['status'] = user.handle_registration()
        except Exception, e:
            response['info'] = " Error: %s " % e
            response['status'] = STATUS_500
        finally:
            self.write(response)


class CreateUser(tornado.web.RequestHandler):

    def data_validation(self, username, auth_code):
        query = " SELECT authorization_code FROM registered_users WHERE username = %s;"
        variables = (username, )
        result = QueryHandler.get_results(query, variables)
        return (SUCCESS_RESPONSE, STATUS_200) if result and result[0]['authorization_code'] == auth_code \
            else (PHONE_AUTH_CODE_MISMATCH_ERR, STATUS_404)

    def create_user_presence_queue(self, username):
        try:
            # routing_key = 'chat_presence.' + username + '_presence'
            routing_key = 'user_presence.' + username + '_presence'
            channel = get_rabbitmq_connection()
            result = channel.queue_declare()
            channel.queue_bind(exchange=CHAT_PRESENCE_EXCHANGE, queue=result.method.queue, routing_key=routing_key)
        except Exception as e:
            raise e

    def get(self):
        response = {}
        try:
            username = str(self.get_argument("phone_number", '')).strip('')
            auth_code = str(self.get_argument("auth_code", ''))
            password = str(self.get_argument("password", ''))

            (response['info'], response['status']) = self.data_validation(username, auth_code)
            if response['status'] not in ERROR_CODES_LIST:
                user = User(username, password)
                response['info'], response['status'], response['password'] = user.handle_creation(auth_code)
                self.create_user_presence_queue(username)
        except Exception, e:
            response['info'] = " Error %s " % e
            response['status'] = STATUS_500
        finally:
            self.write(response)


class SaveContacts(tornado.web.RequestHandler):

    def data_validation(self, username):
        try:
            query = " SELECT id FROM users WHERE username = %s;"
            variables = (username,)
            result = QueryHandler.get_results(query, variables)
            return (SUCCESS_RESPONSE, STATUS_200) if result else (INVALID_USER_ERR, STATUS_404)
        except Exception as e:
            raise e

    def save_user_contacts(self, username, contacts_list):
        try:
            query = " UPDATE users SET contacts = %s WHERE username=%s;"
            variables = (contacts_list, username, )
            QueryHandler.execute(query, variables)
        except Exception as e:
            raise e

    def initiate_simple_chat_user_subscriber(self, user):
        try:
            routing_key = 'simple_chat_' + user + '.*'
            channel = get_rabbitmq_connection()
            result = channel.queue_declare()
            channel.queue_bind(exchange=SIMPLE_CHAT_MESSAGES_EXCHANGE, queue=result.method.queue, routing_key=routing_key)
            client_id = "simple_chat/" + "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(23-12))
            simple_chat_subscriber(client_id=client_id, user_data={'topic': routing_key, 'receiver': user})

            # result = channel.queue_declare()
            # channel.queue_bind(exchange=SIMPLE_CHAT_MESSAGE_RECEIVED_EXCHANGE, queue=result.method.queue,
            #                    routing_key='msg_received_' + user + '.*' )

        except Exception as e:
            raise e

    def initiate_media_to_contact_subscriber(self, user):
        try:
            routing_key = 'group_media_' + user + '.*'
            channel = get_rabbitmq_connection()
            result = channel.queue_declare()
            channel.queue_bind(exchange=SIMPLE_CHAT_MEDIA_EXCHANGE, queue=result.method.queue, routing_key=routing_key)
            client_id = "simple_media/" + "".join(random.choice(user) for x in range(23-13))
            simple_chat_media_subscriber(client_id=client_id, user_data={'topic': routing_key, 'receiver': user})
        except Exception as e:
            raise e

    def post(self):
        response = {}
        try:
            user = str(self.get_argument('user', '')).strip('')
            contacts = str(self.get_argument('contacts', ''))
            (response['info'], response['status']) = self.data_validation(user)
            if response['status'] not in ERROR_CODES_LIST:
                contacts_list = contacts[1:-1].split(',')

                self.save_user_contacts(user, contacts_list)
                self.initiate_simple_chat_user_subscriber(user)     # start simple chat message subscriber
                # self.initiate_media_to_contact_subscriber(user)     # start simple chat media subscriber

                response['info'] = SUCCESS_RESPONSE
                response['status'] = STATUS_200
        except Exception as e:
            response['info'] = " Error: %s" % e
            response['status'] = STATUS_500
        finally:
            self.write(response)
