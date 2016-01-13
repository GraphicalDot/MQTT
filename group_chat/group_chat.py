import json

import tornado
import tornado.escape
import tornado.httpclient
import tornado.ioloop
import tornado.web

from errors import *
from mqtt_publisher import *
from mqtt_subscriber import *
from project.app_settings import *
from project.rabbitmq_utils import *


class SendMessageToGroup(tornado.web.RequestHandler):
    topic = None

    def data_validations(self, sender, group_name, message):
        response = {'info': '', 'status': 0}
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
        response = {}
        try:
            sender = str(self.get_argument('sender', ''))
            group_name = str(self.get_argument('group_name', ''))
            message = str(self.get_argument('message', ''))

            # data validations
            res = self.data_validations(sender, group_name, message)
            if res['status'] in [400, 404]:
                return self.write(res)

            # Get group's owner
            query = " SELECT id,owner FROM groups_info WHERE name=%s AND %s=ANY(members);"
            variables = (group_name, sender)
            group = LocalQueryHandler.get_results(query, variables)
            owner = str(group[0]['owner'])

            channel = get_rabbitmq_connection()
            self.topic = 'group_chat.' + owner + '.' + group_name
            user_data = {'topic': self.topic + '.' + sender, 'group_owner': owner, 'group_name': group_name, 'sender': sender,
                         'message': message}
            group_id = str(group[0]['id'])
            client_id = 'pub_' + sender[2:] + '_' + group_id
            group_chat_publisher(client_id , user_data)
        except Exception as e:
            response['info'] = " Error: %s" % e
            response['status'] = 500
        finally:
            self.write(response)


class CreateGroup(tornado.web.RequestHandler):
    topic = None

    def validate_group_owner(self, owner):
        response = {'info': '', 'status': 0}
        if not owner:
            response['info'] = GROUP_OWNER_NOT_PROVIDED_ERR
            response['status'] = 400
            return response

        if len(owner) != 12:
            response['info'] = GROUP_OWNER_INVALID_CONTACT_ERR
            response['status'] = 400
            return response
        return response

    def validate_group_name(self, name):
        response = {'info': '', 'status': 0}
        if not name:
            response['info'] = GROUP_NAME_NOT_PROVIDED_ERR
            response['status'] = 400

        # TODO: Validate if this group name already exists for this user(owner/creator)
        return response

    def validate_group_members(self, group_members):
        response = {'info': '', 'status': 0}
        members = group_members[1:-1].split(',')
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
            response['info'] = NON_REGISTERED_MEMBER_ERR
            response['status'] = 404
            return response

        response['members'] = members
        return response

    def data_validation(self, group_owner, group_name, group_members):
        res = {}
        owner_response = self.validate_group_owner(group_owner)

        name_response = self.validate_group_name(group_name)

        members_response = self.validate_group_members(group_members)

        if owner_response['status'] == 400:
            return owner_response
        elif name_response['status'] == 400:
            return name_response
        else:
            return members_response

    def add_groups_for_users(self, owner, name, members):
        try:
            query = " SELECT id FROM groups_info WHERE name=%s AND owner=%s;"
            variables = (name, owner,)
            group_id = LocalQueryHandler.get_results(query, variables)[0]['id']

            for member in members:
                query = " UPDATE users SET member_of_groups = array_append(member_of_groups, %s) WHERE username=%s;"
                variables = (str(group_id), member)
                LocalQueryHandler.execute(query, variables)
            return group_id
        except Exception as e:
            raise e

    def create_queue(self, topic):
        try:
            routing_key = topic + '.*'
            channel = get_rabbitmq_connection()
            result = channel.queue_declare()
            channel.queue_bind(exchange=GROUP_CHAT_MESSAGES_EXCHANGE, queue=result.method.queue, routing_key=routing_key)
        except Exception as e:
            raise e


    def get(self, *args, **kwargs):
        response = {}
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

            # add group details in "groups_info" table
            query = " INSERT INTO groups_info (name, owner, admins, members, total_members) " \
                    "VALUES (%s, %s, %s, %s, %s);"
            variables = (group_name, group_owner, [group_owner], group_members, int(len(group_members)))
            LocalQueryHandler.execute(query, variables)

            # update group-membership details in "users" table
            group_id = self.add_groups_for_users(group_owner, group_name, group_members)

            self.topic = 'group_chat.' + str(group_owner) + '.' + str(group_name)
            self.create_queue(self.topic)

            # Create new topic in mqtt, add subscribers
            user_data = {'topic': self.topic + '.*'}
            for member in group_members:
                client_id = str(member) + '_' + str(group_id)
                group_chat_subscriber(client_id, user_data)
            response['info'] = "Success"
            response['status'] = 200
        except Exception as e:
            response['info'] = " Error: %s" % e
            response['status'] = 500
        self.write(response)


class GetGroupsInfo(tornado.web.RequestHandler):

    def user_validation(self, user):
        response = {'info': '', 'status': 0}
        if not user:
            response['info'] = INCOMPLETE_USER_INFO_ERR
            response['status'] = 400
        return response

    def get_user_groups(self, user):
        query = " SELECT member_of_groups FROM users WHERE username=%s;"
        variables = (user,)
        user_groups = LocalQueryHandler.get_results(query, variables)
        return user_groups[0]['member_of_groups'] if user_groups else []

    def get(self, *args, **kwargs):
        response = {}
        try:
            groups = []
            current_user = str(self.get_argument('user', ''))

            # data validation
            res = self.user_validation(current_user)
            if res['status'] == 400:
                return self.write(res)

            user_groups = self.get_user_groups(current_user)
            if user_groups:
                for group_id in user_groups:
                    query = " SELECT total_members,name,admins,members,owner FROM groups_info WHERE id=%s;"
                    variables = (int(group_id),)
                    groups.extend(LocalQueryHandler.get_results(query, variables))
                response['groups'] = json.dumps(groups)
                response['info'] = ''
                response['status'] = 200
            else:
                response['info'] = "This user has no associated groups!"
                response['status'] = 200
            return self.write(response)
        except Exception as e:
            response['info'] = "ERROR: {}".format(e)
            response['status'] = 500
            return self.write(response)


class CreateExchanges(tornado.web.RequestHandler):

    def get(self):
        response = {}
        try:
            channel = get_rabbitmq_connection()
            for name in RABBITMQ_EXCHANGES:
                channel.exchange_declare(exchange=name, type='topic', durable=True, auto_delete=False)

            response['status'] = 200
            response['info'] = SUCCESS_RESPONSE
        except Exception as e:
            response['status'] = 500
            response['info'] = INTERNAL_ERROR
        return self.write(response)


# def make_app():
#     return tornado.web.Application([
#         (r"/", CreateExchanges),
#         (r"/create_group", CreateGroup),
#         (r"/send_message", SendMessageToGroup),
#         (r"/get_groups", GetGroupsInfo),
#     ],
#         autoreload=True,
#     )

#
# if __name__ == "__main__":
#     app = make_app()
#     enable_pretty_logging(options=options)
#     app.listen(3000)
#     tornado.ioloop.IOLoop.current().start()
