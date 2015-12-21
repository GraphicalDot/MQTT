import json
import tornado
import tornado.escape
import tornado.httpclient
import tornado.ioloop
import tornado.web

from tornado.log import enable_pretty_logging
from tornado.options import options

from errors import *
from mqtt_publisher import *
from mqtt_subscriber import *
from rabbitmq_utils import *
from rabbitmq_subscriber import *


class SendMessageToGroup(tornado.web.RequestHandler):
    topic = None

    def data_validations(self, sender, group_name, message):
        response = {'info': '', 'status': 0}
        print "inside data validations"
        print 'sender:', sender
        print 'name:', group_name
        print 'message:', message
        if (not sender) or (not group_name) or (not message):
            response['info'] = SEND_MESSAGE_INCOMPLETE_INFO_ERR
            response['status'] = 400
            return response

        query = " SELECT id FROM users WHERE username=%s;"
        variables = (sender,)
        user = LocalQueryHandler.get_results(query, variables)
        if not user:
            response['info'] = SEND_MESSAGE_NO_USER_PROVIDED_ERR
            response['status'] = 404
            return response

        query = " SELECT id FROM groups_info WHERE name=%s AND %s=ANY(members);"
        variables = (group_name, sender)
        group = LocalQueryHandler.get_results(query, variables)
        if not group:
            response['info'] = SEND_MESSAGE_INVALID_GROUP_DETAILS_ERR
            response['status'] = 404
            return response
        return response

    def get(self, *args, **kwargs):
        print "inside get of SendMessageToGroup"
        response = {}
        try:
            sender = str(self.get_argument('sender', ''))
            group_name = str(self.get_argument('group_name', ''))
            message = str(self.get_argument('message', ''))

            # data validations
            res = self.data_validations(sender, group_name, message)
            print 'res:', res
            if res['status'] in [400, 404]:
                return self.write(res)

            # Get group's owner
            query = " SELECT id,owner FROM groups_info WHERE name=%s AND %s=ANY(members);"
            variables = (group_name, sender)
            group = LocalQueryHandler.get_results(query, variables)
            owner = str(group[0]['owner'])
            print 'group details:', group

            # get rabbitmq connection
            rabbitmq_connection = get_rabbitmq_connection()
            print 'connection:', rabbitmq_connection
            channel = rabbitmq_connection.channel()

            self.topic = 'group_chat.' + owner + '.' + group_name
            user_data = {'topic': self.topic, 'group_owner': owner, 'group_name': group_name, 'sender': sender,
                         'message': message}
            group_id = str(group[0]['id'])
            client_id = sender + '_' + group_id
            group_chat_publisher(client_id , user_data)
        except Exception as e:
            print "inside exception:", e
            response['info'] = " Error: %s" % e
            response['status'] = 500
        finally:
            self.write(response)




class CreateGroup(tornado.web.RequestHandler):
    topic = None

    def validate_group_owner(self, owner):
        print "inside validate_group_owner"
        print "owner:", owner
        response = {'info': '', 'status': 0}
        if not owner:
            print 'if no owner provided'
            response['info'] = GROUP_OWNER_NOT_PROVIDED_ERR
            response['status'] = 400
            return response

        if len(owner) != 12:
            print 'if length is not 12'
            response['info'] = GROUP_OWNER_INVALID_CONTACT_ERR
            response['status'] = 400
            return response
        return response

    def validate_group_name(self, name):
        print "inside validate_group_name"
        response = {'info': '', 'status': 0}
        if not name:
            print 'no name'
            response['info'] = GROUP_NAME_NOT_PROVIDED_ERR
            response['status'] = 400

        # TODO: Validate if this group name already exists for this user(owner/creator)
        return response

    def validate_group_members(self, group_members):
        print "inside validate_group_members"
        response = {'info': '', 'status': 0}
        print 'initial members:', group_members
        members = group_members[1:-1].split(',')
        print 'members:', members, type(members)
        if not group_members:
            response['info'] = NO_GROUP_MEMBER_ADDED_ERR
            response['status'] = 400
            return response

        # Check if members are registered or not.
        query = " SELECT username FROM users;"
        variables = ()
        users_result = LocalQueryHandler.get_results(query, variables)
        users = list(user['username'] for user in users_result) if users_result else []

        if not set(members).issubset(users):
            print "if group member is not registered!"
            response['info'] = NON_REGISTERED_MEMBER_ERR
            response['status'] = 404
            return response

        response['members'] = members
        return response

    def data_validation(self, group_owner, group_name, group_members):
        print "inside validate data"
        res = {}
        owner_response = self.validate_group_owner(group_owner)
        print 'owner response:', owner_response

        name_response = self.validate_group_name(group_name)
        print 'name response:', name_response

        members_response = self.validate_group_members(group_members)
        print "members response:", members_response

        if owner_response['status'] == 400:
            return owner_response
        elif name_response['status'] == 400:
            return name_response
        else:
            return members_response

    def add_groups_for_users(self, owner, name, members):
        print "inside add groups for users"
        try:
            query = " SELECT id FROM groups_info WHERE name=%s AND owner=%s;"
            variables = (name, owner,)
            group_id = LocalQueryHandler.get_results(query, variables)[0]['id']
            print "group id:", group_id

            for member in members:
                print '************************************'
                print 'member:', group_id
                query = " UPDATE users SET member_of_groups = array_append(member_of_groups, %s) WHERE username=%s;"
                variables = (str(group_id), member)
                LocalQueryHandler.execute(query, variables)
            return group_id
        except Exception as e:
            raise e

    def get(self, *args, **kwargs):
        response = {}
        print "inside get of CreateGroup"
        try:
            # data validations
            group_owner = self.get_argument('owner', '')
            group_name = self.get_argument('name', '')
            group_members = str(self.get_argument('members', ''))
            res = self.data_validation(group_owner, group_name, group_members)
            if res['status'] in [400, 404]:
                return res

            group_members = res['members']
            group_members.append(str(group_owner))
            print 'NOW GROUP MEMBERS:', group_members

            # add group details in "groups_info" table
            query = " INSERT INTO groups_info (name, owner, admins, members, total_members) " \
                    "VALUES (%s, %s, %s, %s, %s);"
            variables = (group_name, group_owner, [group_owner], group_members, int(len(group_members)))
            print 'variables:', variables
            LocalQueryHandler.execute(query, variables)

            # update group-membership details in "users" table
            group_id = self.add_groups_for_users(group_owner, group_name, group_members)

            create_queue()




class CreateExchanges(tornado.web.RequestHandler):

    def get(self):
        response = {}
        try:
            print 'inside get of CreateExchanges'
            rabbitmq_connection = get_rabbitmq_connection()
            print 'connection:', rabbitmq_connection
            channel = rabbitmq_connection.channel()
            print "channel:", channel
            channel.exchange_declare(exchange=GROUP_CHAT_MESSAGES_EXCHANGE, type='topic', durable=True, auto_delete=False)
            response['status'] = 200
            response['info'] = 'Success'
        except Exception as e:
            response['status'] = 500
            response['info'] = "Some Internal Error occured! Please try again later!"
        return self.write(response)


def make_app():
    return tornado.web.Application([
        (r"/", CreateExchanges),
        (r"/create_group", CreateGroup),
        (r"/send_message", SendMessageToGroup),
    ],
        autoreload=True,
    )


if __name__ == "__main__":
    app = make_app()
    options.log_file_prefix = "tornado_log"
    enable_pretty_logging(options=options)
    app.listen(3000)
    tornado.ioloop.IOLoop.current().start()
