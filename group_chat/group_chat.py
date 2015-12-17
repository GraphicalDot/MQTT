import json
import tornado
import tornado.escape
import tornado.httpclient
import tornado.ioloop
import tornado.web

from tornado.log import enable_pretty_logging
from tornado.options import options

from errors import *
from publisher import *
from subscriber import *
from utils.presence_notification import *


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

            # Create new topic in mqtt, add subscribers
            # self.topic = '$SYS/sportsunity/group_chat/' + str(group_owner) + '/' + str(group_name)
            self.topic = '$SYS/sportsunity/chat'
            user_data = {'topic': self.topic}
            for member in group_members:
                client_id = str(member) + '_' + str(group_id)
                group_chat_subscriber(client_id, user_data)

        except Exception as e:
            print 'inside Exception:', e
            response['info'] = " Error: %s" % e
            response['status'] = 500
        self.write(response)


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

            # self.topic = '$SYS/sportsunity/group_chat/' + owner + '/' + group_name
            self.topic = '$SYS/sportsunity/chat'
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


class GetGroupsInfo(tornado.web.RequestHandler):

    def user_validation(self, user):
        print "inside user_validation"
        response = {'info': '', 'status': 0}
        if not user:
            response['info'] = INCOMPLETE_USER_INFO_ERR
            response['status'] = 400
        return response

    def get_user_groups(self, user):
        print "inside get_user_groups"
        query = " SELECT member_of_groups FROM users WHERE username=%s;"
        variables = (user,)
        user_groups = LocalQueryHandler.get_results(query, variables)
        print 'user groups:', user_groups[0]['member_of_groups']
        return user_groups[0]['member_of_groups']

    def get(self, *args, **kwargs):
        print "inside get of GetGroupsInfo"
        response = {}
        try:
            groups = []
            current_user = str(self.get_argument('user', ''))

            # data validation
            res = self.user_validation(current_user)
            print 'res:', res
            if res['status'] == 400:
                return self.write(res)

            user_groups = self.get_user_groups(current_user)
            print 'type of user groups:', type(user_groups)
            if user_groups:
                for group_id in user_groups:
                    print 'group id:', group_id
                    query = " SELECT total_members,name,admins,members,owner FROM groups_info WHERE id=%s;"
                    variables = (int(group_id),)
                    groups.extend(LocalQueryHandler.get_results(query, variables))
                print 'FINAL GROUP DETAILS:', groups
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


class StartStopApp(tornado.web.RequestHandler):
    topic = None
    status = None

    def data_validation(self, user, event, contacts):
        print 'inside data validation'
        response = {'info': '', 'status': 0}
        if not user:
            print 'if user not provided'
            response['info'] = INCOMPLETE_USER_INFO_ERR
            response['status'] = 400
            return response

        if len(user) != 12:
            print 'if length is not 12'
            response['info'] = INVALID_USER_CONTACT_ERR
            response['status'] = 400
            return response

        query = " SELECT id FROM users WHERE username=%s;"
        variables = (user,)
        result = LocalQueryHandler.get_results(query, variables)
        if not result:
            response['info'] = USER_NOT_REGISTERED_ERR
            response ['status'] = 400
            return response

        if not event:
            response['info'] = EVENT_NOT_PROVIDED_ERR
            response['status'] = 400
            return response

        print 'contacts:', contacts
        if contacts:
            for contact in contacts:
                query = " SELECT id FROM users WHERE username=%s;"
                variables = (contact,)
                result = LocalQueryHandler.get_results(query, variables)
                if not result:
                    response['info'] = NON_REGISTERED_CONTACT_ERR
                    response ['status'] = 400
                    return response
        return response

    def get(self, *args, **kwags):
        print "inside get of StartApp"
        user = str(self.get_argument('user', ''))
        event = str(self.get_argument('event', ''))
        contacts = str(self.get_argument('contacts', '')).replace(" ", "")
        print 'contacts:', contacts[1:-1]
        friends = contacts[1:-1].split(',') if contacts else ''
        print 'user:', user
        print 'event:', event
        print 'friends:', friends

        res =  self.data_validation(user, event, friends)
        if res['status'] == 400:
            return self.write(res)

        client_id = user + '_presence'
        self.topic = '$SYS/sportsunity/client/' + client_id
        print 'TOPIC:', self.topic

        # TODO: make an entry into ACL file for this topic in registeration process

        # publish presence status for the client.
        self.status = '1' if event == 'start' else '0'
        user_data = {'topic': self.topic, 'event': event, 'status': self.status, 'user': user}
        publish_presence_notification(client_id, user_data)

        friends_status = dict()
        if friends:
            print 'inside if'
            # Subscribe to all contacts so as to get notified if user comes online/offline.
            for friend in friends:
                print 'for friend:', friend
                client_id = user + 'subscribes_to_' + friend + '_presence'
                print 'client_id:', client_id
                user_data = {'topic': '$SYS/sportsunity/client/' +  friend + '_presence'}
                subscribe_contacts_presence(client_id, user_data)  ## will be a frontend function
            print 'modified user data:', user_data

            # Get all contacts status
            for friend in friends:
                query = " SELECT status FROM users WHERE username=%s;"
                variables = (friend,)
                result = LocalQueryHandler.get_results(query, variables)
                friends_status[friend] = result[0]['status']
            print 'status dictionary:', friends_status
        return self.write(friends_status)


def make_app():
    return tornado.web.Application([
        (r"/create_group", CreateGroup),
        (r"/send_message", SendMessageToGroup),
        (r"/get_groups", GetGroupsInfo),
        # (r"/call_method", callMethod),
        (r"/start_stop_app", StartStopApp),
    ],
        autoreload=True,
    )


if __name__ == "__main__":
    app = make_app()
    options.log_file_prefix = "tornado_log"
    enable_pretty_logging(options=options)
    app.listen(3000)
    tornado.ioloop.IOLoop.current().start()
