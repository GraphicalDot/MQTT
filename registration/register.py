import random
import time
import tornado
import tornado.web

from app_settings import *
from db_handler import *

from utils import *


class RegisterUser(tornado.web.RequestHandler):

    def get(self):
        print 'inside get of RegisterUser'
        response = {}
        try:
            number = str(self.get_arguments("phone_number"))
            username = str.strip(number)
            user = User(username)
            response['info'], response['status'] = user.handle_registration()
        except Exception, e:
            response['info'] = " Error: %s " % e
            response['status'] = 500
        finally:
            self.write(response)


class CreateUser(tornado.web.RequestHandler):
    def get(self):
        response = {}
        try:
            username = str.strip(self.get_arguments("phone_number"))
            auth_code = str(self.get_arguments("auth_code"))
            password = str(self.get_arguments("password", ''))
            user = User(username, password)
            response['info'], response['status'], response['password'] = user.handle_creation(auth_code)
        except Exception, e:
            response['info'] = " Error %s " % e
            response['status'] = 500
        finally:
            self.write(response)
