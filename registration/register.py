import random
import string
import time
import tornado
import tornado.web

from app_settings import *
from db_handler import *
from errors import *
from chat.utils import *
from chat.media_utils import *
from group_chat.rabbitmq_utils import *
from group_chat.mqtt_subscriber import *
from utils import *


class RegisterUser(tornado.web.RequestHandler):

    def get(self):
        print 'inside get of RegisterUser'
        response = {}
        try:
            number = str(self.get_argument("phone_number", ''))
            username = str.strip(number)
            print 'username:', username
            user = User(username)
            response['info'], response['status'] = user.handle_registration()
        except Exception, e:
            response['info'] = " Error: %s " % e
            response['status'] = 500
        finally:
            self.write(response)


class CreateUser(tornado.web.RequestHandler):

    def data_validation(self, username, auth_code):
        print "inside data validation of create user"
        query = " SELECT authorization_code FROM registered_users WHERE username = %s;"
        variables = (username, )
        result = QueryHandler.get_results(query, variables)
        print 'result:', result
        return ('Success', 200) if result and result[0]['authorization_code'] == auth_code \
            else (PHONE_AUTH_CODE_MISMATCH_ERR, 404)

    def create_user_presence_queue(self, username):
        print 'inside create user presence queue'
        try:
            # routing_key = 'chat_presence.' + username + '_presence'
            routing_key = 'user_presence.' + username + '_presence'
            channel = get_rabbitmq_connection()
            result = channel.queue_declare()
            print 'result:', result
            channel.queue_bind(exchange=CHAT_PRESENCE_EXCHANGE, queue=result.method.queue, routing_key=routing_key)
        except Exception as e:
            print "inside exception"
            raise e

    def get(self):
        response = {}
        try:
            print 'phone:', self.get_argument("phone_number", '')
            username = str.strip(str(self.get_argument("phone_number", '')))
            print 'username:', username
            auth_code = str(self.get_argument("auth_code", ''))
            print 'auth code:', auth_code
            password = str(self.get_argument("password", ''))
            print 'password:', password

            (response['info'], response['status']) = self.data_validation(username, auth_code)
            if response['status'] != 404:
                user = User(username, password)
                response['info'], response['status'], response['password'] = user.handle_creation(auth_code)
                self.create_user_presence_queue(username)
        except Exception, e:
            response['info'] = " Error %s " % e
            response['status'] = 500
        finally:
            self.write(response)


class SaveContacts(tornado.web.RequestHandler):

    def data_validation(self, username):
        print "inside data validation of SaveContacts"
        try:
            query = " SELECT id FROM users WHERE username = %s;"
            variables = (username,)
            result = QueryHandler.get_results(query, variables)
            return ("Success", 200) if result else (INVALID_USER_ERR, 404)
        except Exception as e:
            raise e

    def save_user_contacts(self, username, contacts_list):
        print "inside save_user_contacts"
        print 'contacts list:', contacts_list
        try:
            query = " UPDATE users SET contacts = %s WHERE username=%s;"
            variables = (contacts_list, username, )
            QueryHandler.execute(query, variables)
        except Exception as e:
            raise e

    def generate_random_client_id(self):
        # return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
        return "paho/" + "".join(random.choice("0123456789ADCDEF") for x in range(23-5))

    def initiate_simple_chat_user_subscriber(self, user):
        try:
            print "inside initiate_simple_chat_user_subscriber"
            routing_key = 'simple_chat_' + user + '.*'
            channel = get_rabbitmq_connection()
            result = channel.queue_declare()
            channel.queue_bind(exchange=SIMPLE_CHAT_MESSAGES_EXCHANGE, queue=result.method.queue, routing_key=routing_key)
            client_id = self.generate_random_client_id()
            simple_chat_subscriber(client_id=client_id, user_data={'topic': routing_key, 'receiver': user})
        except Exception as e:
            raise e

    def initiate_media_to_contact_subscriber(self, user):
        try:
            print "inside initiate_media_to_contact_subscriber"
            routing_key = 'group_media_' + user + '.*'
            channel = get_rabbitmq_connection()
            result = channel.queue_declare()
            channel.queue_bind(exchange=SIMPLE_CHAT_MEDIA_EXCHANGE, queue=result.method.queue, routing_key=routing_key)
            client_id = "simple_media/" + "".join(random.choice(user) for x in range(23-13))
            simple_chat_media_subscriber(client_id=client_id, user_data={'topic': routing_key, 'receiver': user})
        except Exception as e:
            raise e

    def get(self):
        print "inside get of SaveContacts"
        response = {}
        try:
            user = str(self.get_argument('user', '')).strip()
            contacts = str(self.get_argument('contacts', ''))
            (response['info'], response['status']) = self.data_validation(user)
            if response['status'] != 404:
                contacts_list = contacts[1:-1].split(',')

                self.save_user_contacts(user, contacts_list)
                self.initiate_simple_chat_user_subscriber(user)
                self.initiate_media_to_contact_subscriber(user)

                response['info'] = "Success"
                response['status'] = 200
        except Exception as e:
            response['info'] = " Error: %s" % e
            response['status'] = 500
        finally:
            self.write(response)
