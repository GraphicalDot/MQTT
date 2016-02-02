import json
import Queue
import os
import sys
import tornado
import tornado.escape
import tornado.httpclient
import tornado.ioloop
import tornado.web
from samba.dcerpc.dns import res_rec

sys.path.append(os.path.dirname(os.path.abspath(__file__)).rsplit('/', 1)[0])
import errors
import mqtt_publisher
import mqtt_subscriber
from chat import utils
from project import app_settings, rabbitmq_utils, db_handler


class SendMessageToGroup(tornado.web.RequestHandler):
    topic = None

    def data_validations(self, sender, group_name, message):
        response = {'info': '', 'status': 0}
        if (not sender) or (not group_name) or (not message):
            response['info'] = errors.SEND_MESSAGE_INCOMPLETE_INFO_ERR
            response['status'] = app_settings.STATUS_400
            return response

        query = " SELECT id FROM users WHERE username=%s;"
        variables = (sender,)
        user = db_handler.QueryHandler.get_results(query, variables)
        if not user:
            response['info'] = errors.SEND_MESSAGE_NO_USER_PROVIDED_ERR
            response['status'] = app_settings.STATUS_404
            return response

        query = " SELECT id FROM groups_info WHERE name=%s AND %s=ANY(members);"
        variables = (group_name, sender)
        group = db_handler.QueryHandler.get_results(query, variables)
        if not group:
            response['info'] = errors.SEND_MESSAGE_INVALID_GROUP_DETAILS_ERR
            response['status'] = app_settings.STATUS_404
        return response

    def post(self, *args, **kwargs):
        response = {}
        try:
            sender = str(self.get_argument('sender', ''))
            group_name = str(self.get_argument('group_name', ''))
            message = str(self.get_argument('message', ''))

            # data validations
            response = self.data_validations(sender, group_name, message)
            if response['status'] not in app_settings.ERROR_CODES_LIST:
                # Get group's owner
                query = " SELECT id,owner,members,total_members FROM groups_info WHERE name=%s AND %s=ANY(members);"
                variables = (group_name, sender)
                group = db_handler.QueryHandler.get_results(query, variables)
                owner = str(group[0]['owner'])
                group_id = str(group[0]['id'])
                total_members = str(group[0]['total_members'])

                self.topic = 'group_chat.' + owner + '.' + group_name
                user_data = {'topic': self.topic + '.' + sender,
                             'message': owner + ':' + group_name + ':' + sender + ':' + message + ':' + total_members,
                            'group_id': group_id, 'number_of_members': total_members}

                client_id = 'pub_' + group_id + utils.generate_random_client_id(len('pub_' + group_id))
                mqtt_publisher.group_chat_publisher(client_id , user_data)

                response['info'] = app_settings.SUCCESS_RESPONSE
                response['status'] = app_settings.STATUS_200
        except Exception as e:
            response['info'] = " Error: %s" % e
            response['status'] = app_settings.STATUS_500
        finally:
            self.write(response)


class CreateGroup(tornado.web.RequestHandler):
    topic = None

    def add_groups_for_users(self, group_id, members):
        try:
            for member in members:
                query = " UPDATE users SET member_of_groups = array_append(member_of_groups, %s) WHERE username=%s;"
                variables = (str(group_id), str(member))
                db_handler.QueryHandler.execute(query, variables)
        except Exception as e:
            raise e

    def data_validation(self, group_owner, group_name, group_members):
        response = {'info': '', 'status': 0}
        try:
            # No group onwer
            if not group_owner:
                response['info'] = errors.GROUP_OWNER_NOT_PROVIDED_ERR
                response['status'] = app_settings.STATUS_400
                return response

            # Invalid group owner
            query = " SELECT id FROM users WHERE username=%s;"
            variables = (group_owner,)
            result = db_handler.QueryHandler.get_results(query, variables)
            if not result:
                response['info'] = errors.INVALID_GROUP_OWNER_ERR
                response['status'] = app_settings.STATUS_400
                return response

            # No group name
            if not group_name:
                response['info'] = errors.GROUP_NAME_NOT_PROVIDED_ERR
                response['status'] = app_settings.STATUS_400
                return response

            # Group with same name already exists for the onwer
            query = " SELECT id FROM groups_info WHERE name=%s AND owner=%s;"
            variables = (group_name, group_owner)
            result = db_handler.QueryHandler.get_results(query, variables)
            if len(result) > 0:
                response['info'] = errors.GROUP_NAME_ALREADY_EXISTS_ERR
                response['status'] = app_settings.STATUS_400
                return response

            # No group members added
            if not group_members:
                response['info'] = errors.NO_GROUP_MEMBER_ADDED_ERR
                response['status'] = app_settings.STATUS_400
                return response

            # Non registered group members
            query = " SELECT username FROM users;"
            users_result = db_handler.QueryHandler.get_results(query)
            users = list(int(user['username']) for user in users_result) if users_result else []
            if not set(group_members).issubset(users):
                response['info'] = errors.NON_REGISTERED_MEMBER_ERR
                response['status'] = app_settings.STATUS_404
            return response

        except Exception as e:
            response['info'] = "Error: %s" % e
            response['status'] = app_settings.STATUS_500
            return response

    def get(self, *args, **kwargs):
        response = {}
        try:
            # data validations
            group_owner = self.get_argument('owner', '')
            group_name = self.get_argument('name', '')
            group_members = json.loads(self.get_argument('members', '[]'))

            response = self.data_validation(group_owner, group_name, group_members)
            if response['status'] not in app_settings.ERROR_CODES_LIST:
                group_members = group_members
                group_members.append(str(group_owner))

                # add group details in "groups_info" table
                query = " INSERT INTO groups_info (name, owner, admins, members, total_members) " \
                        "VALUES (%s, %s, %s, %s, %s) RETURNING id;"
                variables = (group_name, group_owner, [group_owner], group_members, int(len(group_members)))
                result  = db_handler.QueryHandler.get_results(query, variables)

                group_id = str(result[0]['id'])
                # update group-membership details in "users" table
                self.add_groups_for_users(group_id, group_members)

                self.topic = 'group_chat.' + str(group_owner) + '.' + str(group_name)

                # Create new topic in mqtt, add subscribers
                user_data = {'topic': self.topic + '.*'}
                for member in group_members:
                    client_id = 'sub_' + group_id + utils.generate_random_client_id(len('sub_' + group_id))
                    mqtt_subscriber.group_chat_subscriber(client_id, user_data)
                response['info'] = app_settings.SUCCESS_RESPONSE
                response['status'] = app_settings.STATUS_200
        except Exception as e:
            response['info'] = " Error: %s" % e
            response['status'] = app_settings.STATUS_500
        finally:
            self.write(response)


class GetGroupsInfo(tornado.web.RequestHandler):

    def user_validation(self, user):
        response = {'info': '', 'status': 0}
        if not user:
            response['info'] = errors.INCOMPLETE_USER_INFO_ERR
            response['status'] = app_settings.STATUS_400

        if response['status'] == 0:
            query = " SELECT id FROM users WHERE username=%s;"
            variables = (user,)
            try:
                result = db_handler.QueryHandler.get_results(query, variables)
                if len(result) < 1:
                    response['info'] = errors.USER_NOT_REGISTERED_ERR
                    response['status'] = app_settings.STATUS_404
            except Exception as e:
                raise e
        return response

    def get_user_groups(self, user):
        query = " SELECT member_of_groups FROM users WHERE username=%s;"
        variables = (user,)
        user_groups = db_handler.QueryHandler.get_results(query, variables)
        return user_groups[0]['member_of_groups'] if user_groups else []

    def get(self, *args, **kwargs):
        response = {}
        try:
            groups = []
            current_user = str(self.get_argument('user', ''))

            # data validation
            res = self.user_validation(current_user)
            if res['status'] in app_settings.ERROR_CODES_LIST:
                return self.write(res)

            user_groups = self.get_user_groups(current_user)
            if user_groups:
                for group_id in user_groups:
                    query = " SELECT total_members,name,admins,members,owner FROM groups_info WHERE id=%s;"
                    variables = (int(group_id),)
                    groups.extend(db_handler.QueryHandler.get_results(query, variables))
                response['groups'] = json.dumps(groups)
                response['info'] = app_settings.SUCCESS_RESPONSE
                response['status'] = app_settings.STATUS_200
            else:
                response['info'] = errors.NO_ASSOCIATED_GROPS_ERR
                response['status'] = app_settings.STATUS_200
            return self.write(response)
        except Exception as e:
            response['info'] = "ERROR: {}".format(e)
            response['status'] = app_settings.STATUS_500
            return self.write(response)


class CreateExchanges(tornado.web.RequestHandler):

    def get(self):
        response = {}
        try:
            channel = rabbitmq_utils.get_rabbitmq_connection()
            for name in app_settings.RABBITMQ_EXCHANGES:
                channel.exchange_declare(exchange=name, type='topic', durable=True, auto_delete=False)

            response['status'] = app_settings.STATUS_200
            response['info'] = app_settings.SUCCESS_RESPONSE
        except Exception as e:
            response['status'] = app_settings.STATUS_500
            response['info'] = errors.INTERNAL_ERROR
        return self.write(response)
