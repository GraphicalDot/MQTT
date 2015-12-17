from db_handler import *


class User:
    def __init__(self, username, password = None):
        self.username = username
        self.password = str(password)

    def delete_registered(self):
        print "deleting registered user"
        query = " DELETE FROM registered_users WHERE username = %s ;"
        variables = (self.username,)
        QueryHandler.execute(query, variables)

    def register(self):
        print 'inside register'
        random_integer = random.randint(1000,9999)
        expiration_time = int(time.time()) + EXPIRY_PERIOD_SEC

        query = " INSERT INTO registered_users (username, authorization_code, expiration_time) VALUES (%s, %s, %s); "
        variables = (self.username, random_integer, expiration_time)
        try:
            QueryHandler.execute(query, variables)
            return self.send_message(random_integer)
        except Exception, e:
            return " Error while sending message : % s" % e, 500

    def handle_registration(self):
        print 'inside handle_registration'
        self.delete_registered()
        response, status = self.register()
        return response, status

    def is_token_correct(self, auth_code):
        query = " SELECT * FROM registered_users WHERE username = %s AND authorization_code = %s ;"
        variables = (self.username, auth_code,)
        record = QueryHandler.get_results(query, variables)
        is_token_correct = True if record and (record[0]['expiration_time'] > int(time.time())) else False
        return is_token_correct

    def exists(self):
        query = " SELECT * FROM users WHERE username = %s;"
        variables = (str.split(self.username, '@')[0],)
        user_info = QueryHandler.get_results(query, variables)
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
            print 'inside create_new'
            query = " INSERT INTO users (username, password, member_of_groups, status, contacts) values (%s, %s, %s, %s, %s);"
            variables = (self.username, self.password, '{}', '0', '{}')
            QueryHandler.execute(query, variables)
            response, status = "Success", 200
        except Exception as e:
            response, status = str(e), 500
        finally:
            return response, status

    def handle_creation(self, auth_code):
        print 'inside handle_creation'
        if self.is_token_correct(auth_code):
            is_created, password = self.exists()
            if not is_created:
                response, status = self.create_new()
                password = self.password
            else:
                response, status = " User already created ", 200
                self.password = password
        else:
            response, status, password = " Wrong or Expired Token ", 400, None
        self.delete_registered()
        return response, status, password

    def send_message(self, random_integer):
        print 'inside send message'
        number = str.strip(self.username)
        message = str.strip(REGISTRATION_MESSAGE + "  " + str(random_integer))
        payload = {
            'method': 'SendMessage',
            'send_to': number,
            'msg': message,
            'msg_type': 'TEXT',
            'userid': GUPSHUP_ID,
            'auth_scheme': 'plain',
            'password': GUPSHUP_PASSWORD,
            'v': '1.1',
            'format': 'text',
        }
        response = requests.get(GUPSHUP_MESSAGE_GATEWAY, params=payload)
        response = str.split(str(response.text),'|')
        if str.strip(str.lower(response[0])) == "success":
            return "Success", 200
        else:
            error = response[2]
            return error, 500
