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
                # Get group details
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


class AddContactToGroup(tornado.web.RequestHandler):

    def data_validation(self, user, group_id):
        response = {'info': '', 'status': 0}
        try:
            if user:
                query = " SELECT id FROM users WHERE username=%s;"
                result = db_handler.QueryHandler.get_results(query, (user,))
                if not result:      # Non-registered user
                    response['info'] = errors.INVALID_USER_CONTACT_ERR
                    response['status'] = app_settings.STATUS_404
            else:       # No user data
                response['info'] = errors.INCOMPLETE_USER_INFO_ERR
                response['status'] = app_settings.STATUS_400

            if response['status'] == 0:
                if group_id:    # Invalid group_id
                    query = " SELECT * FROM groups_info WHERE id=%s;"
                    result = db_handler.QueryHandler.get_results(query, (group_id,))
                    if not result:
                        response['info'] = errors.INVALID_GROUP_ID_ERR
                        response['status'] = app_settings.STATUS_404
                else:       # No group_id
                    response['info'] = errors.INCOMPLETE_GROUP_INFO_ERR
                    response['status'] = app_settings.STATUS_400

            return response
        except Exception as e:
            raise e

    def get_group_details(self, group_id):
        query = " SELECT * FROM groups_info WHERE id=%s;"
        variables = (group_id,)
        try:
            result = db_handler.QueryHandler.get_results(query, variables)
            return result
        except Exception as e:
            raise e

    def post(self):
        response = {}
        try:
            user = str(self.get_argument('contact', ''))
            group_id = str(self.get_argument('group_id', ''))

            # data validations
            response = self.data_validation(user, group_id)
            if response['status'] not in app_settings.ERROR_CODES_LIST:

                # update group details
                query = " UPDATE groups_info SET members = array_append(members, %s), total_members = total_members + 1" \
                        " WHERE id=%s;"
                variables = (user, group_id)
                db_handler.QueryHandler.execute(query, variables)

                # update user's details
                query = " UPDATE users SET member_of_groups = array_append(member_of_groups, %s)" \
                        " WHERE username=%s;"
                variables = (group_id, user)
                db_handler.QueryHandler.execute(query, variables)

                # start subscriber for the user in this group
                result = self.get_group_details(group_id)
                user_data = {'topic': 'group_chat.' + str(result[0]['owner']) + '.' + str(result[0]['name']) + '.*'}
                client_id = 'sub_' + group_id + utils.generate_random_client_id(len('sub_' + group_id))
                mqtt_subscriber.group_chat_subscriber(client_id, user_data)

                response['info'] = app_settings.SUCCESS_RESPONSE
                response['status'] = app_settings.STATUS_200
        except Exception as e:
            response['info'] = " Error: %s" % e
            response['status'] = app_settings.STATUS_500
        finally:
            self.write(response)


class RemoveContactFromGroup(tornado.web.RequestHandler):

    def data_validations(self, contact, group_id):
        response = {'info': '', 'status': 0}

        # No user contact provided
        if not contact:
            response['info'] = errors.INCOMPLETE_USER_INFO_ERR
            response['status'] = app_settings.STATUS_400
            return response

        # Non-registered User provided
        query = " SELECT id FROM users WHERE username=%s;"
        variables = (contact,)
        user_result = db_handler.QueryHandler.get_results(query, variables)
        if len(user_result) < 1:
            response['info'] = errors.INVALID_USER_CONTACT_ERR
            response['status'] = app_settings.STATUS_404
            return response

        # No group_id provided
        if not group_id:
            response['info'] = errors.INCOMPLETE_GROUP_INFO_ERR
            response['status'] = app_settings.STATUS_400
            return response

        # Invalid group_id provided
        query = " SELECT * FROM groups_info WHERE id=%s;"
        variables = (group_id, )
        group_result = db_handler.QueryHandler.get_results(query, variables)
        if len(group_result) < 1:
            response['info'] = errors.INVALID_GROUP_ID_ERR
            response['status'] = app_settings.STATUS_404
            return response

        # User and group doesn't match
        query = " SELECT id FROM users WHERE username=%s AND %s=ANY(member_of_groups);"
        variables = (contact, group_id,)
        result = db_handler.QueryHandler.get_results(query, variables)
        if len(result) < 1:
            response['info'] = errors.USER_GROUP_NOT_MATCH_ERR
            response['status'] = app_settings.STATUS_404
            return response

        # If user is owner of the group
        if group_result[0]['total_members'] > 1 and group_result[0]['owner'] == contact:
            response['info'] = errors.DELETED_USER_IS_GROUP_OWNER_ERR
            response['status'] = app_settings.STATUS_400
        return response

    def post(self):
        response = {}
        try:
            contact = str(self.get_argument('contact', ''))
            group_id = str(self.get_argument('group_id', ''))

            # data validations
            response = self.data_validations(contact, group_id)
            if response['status'] not in app_settings.ERROR_CODES_LIST:

                query = " SELECT total_members FROM groups_info WHERE id=%s;"
                result = db_handler.QueryHandler.get_results(query, (group_id,))
                if result[0]['total_members'] == 1:
                    # delete the group if it has only one member
                    query = "DELETE FROM groups_info WHERE id=%s;"
                    db_handler.QueryHandler.execute(query, (group_id,))
                else:
                    # Update group details
                    query = " UPDATE groups_info SET members = array_remove(members, %s), admins = array_remove(admins, %s)," \
                            "total_members = total_members - 1 WHERE id=%s;"
                    variables = (contact, contact, group_id)
                    db_handler.QueryHandler.execute(query, variables)

                # update user's details
                query = " UPDATE users SET member_of_groups = array_remove(member_of_groups, %s) WHERE username=%s;"
                variables = (group_id, contact)
                db_handler.QueryHandler.execute(query, variables)
                response['info'] = app_settings.SUCCESS_RESPONSE
                response['status'] = app_settings.STATUS_200
        except Exception as e:
            response['info'] = " Error: %" % e
            response['status'] = app_settings.STATUS_500
        finally:
            self.write(response)


class AddAdminToGroup(tornado.web.RequestHandler):

    def data_validations(self, user, contact_to_add, group_id):
        response = {'info': '', 'status': 0}

        # User data not provided
        if not user:
            response['info'] = errors.INCOMPLETE_USER_DETAILS_ERR
            response['status'] = app_settings.STATUS_400
            return response

        # Group id not provided
        if not group_id:
            response['info'] = errors.INCOMPLETE_GROUP_INFO_ERR
            response['status'] = app_settings.STATUS_400
            return response

        # Contact to be added as admin, not provided
        if not contact_to_add:
            response['info'] = errors.INCOMPLETE_CONTACT_DETAILS_ERR
            response['status'] = app_settings.STATUS_400
            return response

        # Non-registered users (either user or new added admin)
        query = " SELECT id FROM users WHERE username=%s OR username=%s;"
        try:
            result = db_handler.QueryHandler.get_results(query, (user, contact_to_add))
            if len(result) < 2 and user != contact_to_add:
                response['info'] = errors.NON_REGISTERED_USER_CONTACT_ERR
                response['status'] = app_settings.STATUS_404
                return response
        except Exception as e:
            raise e

        # Invalid Group-id
        query = " SELECT * FROM groups_info WHERE id=%s;"
        try:
            result = db_handler.QueryHandler.get_results(query, (group_id,))
            if len(result) < 1:
                response['info'] = errors.INVALID_GROUP_ID_ERR
                response['status'] = app_settings.STATUS_404
                return response
        except Exception as e:
            raise e

        # Already an admin
        query = " SELECT * FROM groups_info WHERE id=%s AND %s = ANY(admins);"
        try:
            result = db_handler.QueryHandler.get_results(query, (group_id, contact_to_add))
            if len(result) > 0:
                response['info'] = errors.ALREADY_GROUP_ADMIN_INFO
                response['status'] = app_settings.STATUS_400
                return response
        except Exception as e:
            raise e

        # Ensure 'user' is an admin (has permissions to add an admin)
        query = " SELECT * FROM groups_info WHERE id=%s AND %s = ANY(admins);"
        try:
            result = db_handler.QueryHandler.get_results(query, (group_id, user))
            if len(result) < 1:
                response['info'] = errors.OUTSIDE_USER_PERMISSIONS_ERR
                response['status'] = app_settings.STATUS_400
                return response
        except Exception as e:
            raise e

        # New admin not a member of the group
        query = " SELECT * FROM groups_info WHERE id=%s AND %s = ANY(members);"
        try:
            result = db_handler.QueryHandler.get_results(query, (group_id, contact_to_add))
            if len(result) < 1:
                response['info'] = errors.CONTACT_GROUP_NOT_MATCH_ERR
                response['status'] = app_settings.STATUS_400
            return response
        except Exception as e:
            raise e

    def post(self):
        response = {}
        try:
            user = str(self.get_argument('user', ''))
            contact_to_add = str(self.get_argument('contact', ''))
            group_id = str(self.get_argument('group_id', ''))

            # data validation
            response = self.data_validations(user, contact_to_add, group_id)

            if response['status'] not in app_settings.ERROR_CODES_LIST:
                # add to admins
                query = " UPDATE groups_info SET admins = array_append(admins, %s) WHERE id=%s;"
                db_handler.QueryHandler.execute(query, (contact_to_add, group_id))

                response['info'] = app_settings.SUCCESS_RESPONSE
                response['status'] = app_settings.STATUS_200
        except Exception as e:
            response['info'] = " Error: %s" % e
            response['status'] = app_settings.STATUS_500
        finally:
            self.write(response)


class RemoveAdminFromGroup(tornado.web.RequestHandler):

    def data_validations(self, user, admin_to_remove, group_id):
        response = {'info': '', 'status': 0}

        # User data not provided
        if not user:
            response['info'] = errors.INCOMPLETE_USER_DETAILS_ERR
            response['status'] = app_settings.STATUS_400
            return response

        # Group id not provided
        if not group_id:
            response['info'] = errors.INCOMPLETE_GROUP_INFO_ERR
            response['status'] = app_settings.STATUS_400
            return response

        # Contact to be removed is not provided
        if not admin_to_remove:
            response['info'] = errors.INCOMPLETE_CONTACT_DETAILS_ERR
            response['status'] = app_settings.STATUS_400
            return response

        # Non-registered users (either user or to-be-removed-admin)
        query = " SELECT id FROM users WHERE username=%s OR username=%s;"
        try:
            result = db_handler.QueryHandler.get_results(query, (user, admin_to_remove))
            if len(result) < 2 and user != admin_to_remove:
                response['info'] = errors.NON_REGISTERED_USER_CONTACT_ERR
                response['status'] = app_settings.STATUS_404
                return response
        except Exception as e:
            raise e

        # Invalid Group-id
        query = " SELECT * FROM groups_info WHERE id=%s;"
        try:
            result = db_handler.QueryHandler.get_results(query, (group_id,))
            if len(result) < 1:
                response['info'] = errors.INVALID_GROUP_ID_ERR
                response['status'] = app_settings.STATUS_404
                return response
        except Exception as e:
            raise e

        # Already a non-admin
        query = " SELECT id FROM groups_info WHERE id=%s AND %s = ANY(admins);"
        try:
            result = db_handler.QueryHandler.get_results(query, (group_id, admin_to_remove))
            if len(result) == 0:
                response['info'] = errors.ALREADY_NOT_ADMIN_INFO
                response['status'] = app_settings.STATUS_400
        except Exception as e:
            raise e

        # Ensure 'user' is an admin (has permissions to add an admin)
        query = " SELECT * FROM groups_info WHERE id=%s AND %s = ANY(admins);"
        try:
            result = db_handler.QueryHandler.get_results(query, (group_id, user))
            if len(result) < 1:
                response['info'] = errors.OUTSIDE_USER_PERMISSIONS_ERR
                response['status'] = app_settings.STATUS_400
                return response
        except Exception as e:
            raise e

        # contact to be removed is not a member of the group
        query = " SELECT * FROM groups_info WHERE id=%s AND %s = ANY(members);"
        try:
            result = db_handler.QueryHandler.get_results(query, (group_id, admin_to_remove))
            if len(result) < 1:
                response['info'] = errors.CONTACT_GROUP_NOT_MATCH_ERR
                response['status'] = app_settings.STATUS_400
            return response
        except Exception as e:
            raise e

    def remove_admin(self, group_id, admin_to_remove):
        try:
            query = " UPDATE groups_info SET admins = array_remove(admins, %s) WHERE id=%s;"
            db_handler.QueryHandler.execute(query, (admin_to_remove, group_id))
        except Exception as e:
            raise e

    def delete_group(self, group_id, user):
        # delete the group
        query = " DELETE FROM groups_info WHERE id=%s;"
        db_handler.QueryHandler.execute(query, (group_id,))

        # update user details
        query = " UPDATE users SET member_of_groups = array_remove(member_of_groups, %s) WHERE username=%s;"
        db_handler.QueryHandler.execute(query, (group_id, user))

    def post(self):
        response = {}
        try:
            user = str(self.get_argument('user', ''))
            admin_to_remove = str(self.get_argument('contact', ''))
            group_id = str(self.get_argument('group_id', ''))
            single_admin = False

            # data validation
            response = self.data_validations(user, admin_to_remove, group_id)

            if response['status'] not in app_settings.ERROR_CODES_LIST:
                if user == admin_to_remove:
                    query = " SELECT total_members, admins FROM groups_info WHERE id=%s;"
                    result = db_handler.QueryHandler.get_results(query, (group_id,))
                    if result[0]['total_members'] > 1:
                        if len(result[0]['admins']) > 1:
                            self.remove_admin(group_id, admin_to_remove)
                        else:
                            response['info'] = errors.DELETED_USER_IS_GROUP_OWNER_ERR
                            response['status'] = app_settings.STATUS_400
                            single_admin = True
                    else:
                        self.delete_group(group_id, user)
                else:
                    self.remove_admin(group_id, admin_to_remove)

                if not single_admin:
                    response['info'] = app_settings.SUCCESS_RESPONSE
                    response['status'] = app_settings.STATUS_200

        except Exception as e:
            response['info'] = " Error: %s" % e
            response['status'] = app_settings.STATUS_500
        finally:
            self.write(response)

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
