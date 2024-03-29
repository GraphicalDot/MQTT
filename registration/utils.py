import os
import random
import string
import sys
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)).rsplit('/', 1)[0])
from project import db_handler, app_settings


class User:
    def __init__(self, username, password = None):
        self.username = username
        self.password = str(password)

    def delete_registered(self):
        query = " DELETE FROM registered_users WHERE username = %s ;"
        variables = (self.username,)
        db_handler.QueryHandler.execute(query, variables)

    def register(self):
        random_integer = random.randint(1000,9999)
        expiration_time = int(time.time()) + app_settings.EXPIRY_PERIOD_SEC

        query = " INSERT INTO registered_users (username, authorization_code, expiration_time) VALUES (%s, %s, %s); "
        variables = (self.username, random_integer, expiration_time)
        try:
            db_handler.QueryHandler.execute(query, variables)
            return self.send_message(random_integer)
        except Exception, e:
            return " Error while sending message : % s" % e, app_settings.STATUS_500

    def handle_registration(self):
        self.delete_registered()
        response, status = self.register()
        return response, status

    def is_token_correct(self, auth_code):
        query = " SELECT * FROM registered_users WHERE username = %s AND authorization_code = %s ;"
        variables = (self.username, auth_code,)
        record = db_handler.QueryHandler.get_results(query, variables)
        is_token_correct = True if record and (record[0]['expiration_time'] > int(time.time())) else False
        return is_token_correct

    def exists(self):
        query = " SELECT * FROM users WHERE username = %s;"
        variables = (self.username,)
        user_info = db_handler.QueryHandler.get_results(query, variables)
        if len(user_info) == 0:
            registered = False
            password = None
        else:
            password = user_info[0]['password']
            registered = True
        return registered, password

    def create_new(self):
        response = status = None
        try:
            query = " INSERT INTO users (username, password, member_of_groups, status, contacts) values (%s, %s, %s, %s, %s);"
            variables = (self.username, self.password, '{}', '0', '{}')
            db_handler.QueryHandler.execute(query, variables)
            response, status = app_settings.SUCCESS_RESPONSE, app_settings.STATUS_200
        except Exception as e:
            response, status = str(e), app_settings.STATUS_500
        finally:
            return response, status

    def handle_creation(self, auth_code):
        if self.is_token_correct(auth_code):
            is_created, password = self.exists()
            if not is_created:
                response, status = self.create_new()
                password = self.password
            else:
                response, status = " User already created ", app_settings.STATUS_200
                self.password = password
        else:
            response, status, password = " Wrong or Expired Token ", STATUS_400, None
        self.delete_registered()
        return response, status, password

    def send_message(self, random_integer):
        number = str.strip(self.username)
        message = str.strip(app_settings.REGISTRATION_MESSAGE + "  " + str(random_integer))
        payload = {
            'method': 'SendMessage',
            'send_to': number,
            'msg': message,
            'msg_type': 'TEXT',
            'userid': app_settings.GUPSHUP_ID,
            'auth_scheme': 'plain',
            'password': app_settings.GUPSHUP_PASSWORD,
            'v': '1.1',
            'format': 'text',
        }
        return app_settings.SUCCESS_RESPONSE, app_settings.STATUS_200
        # response = requests.get(GUPSHUP_MESSAGE_GATEWAY, params=payload)
        # response = str.split(str(response.text),'|')
        # if str.strip(str.lower(response[0])) == "success":
        #     return SUCCESS_RESPONSE, STATUS_200
        # else:
        #     error = response[2]
        #     return error, STATUS_500


def generate_random_client_id(len):
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(23-len))

