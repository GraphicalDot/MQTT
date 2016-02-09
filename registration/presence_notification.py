import os
import sys
import tornado
import tornado.web
from paho.mqtt.client import Client

sys.path.append(os.path.dirname(os.path.abspath(__file__)).rsplit('/', 1)[0])
import errors
import utils
from group_chat import mqtt_publisher, mqtt_subscriber
from project import app_settings, db_handler


def on_connect(client, user_data, flags, rc):
    try:
        client.publish(topic=user_data['topic'], payload=user_data['message'], qos=1, retain=True)
    except Exception as e:
        raise e


def on_message(client, user_data, mid):
    try:
        # add message to database
        (username, status) = (user_data['message'].split(':')[0], user_data['message'].split(':')[1])
        query = " UPDATE users SET status = %s WHERE username = %s;"
        variables = (status, username, )
        db_handler.QueryHandler.execute(query, variables)

        # stop the publishing thread
        client.loop_stop()
        client.reinitialise(client_id=user_data['client_id'], clean_session=False)
    except Exception as e:
        raise e


def publish_self_presence(client_id, user_data):
    user_data['client_id'] = str(client_id)
    client = Client(client_id=client_id, clean_session=False, userdata=user_data)
    client.on_connect = on_connect
    client.on_publish = on_message
    try:
        client.username_pw_set(username=app_settings.BROKER_USERNAME, password=app_settings.BROKER_PASSWORD)
        client.connect_async(host='localhost', port=1883)
        client.loop_start()
    except Exception as e:
        raise e


def on_contacts_presence_subscriber_message(client, user_data, message):
    try:
        print 'MESSAGE:', message.payload
    except Exception as e:
        raise e


def on_contacts_presence_subscriber_connect(client, user_data, flags, rc):
    username = user_data.get('user', '')
    query = " SELECT contacts FROM users WHERE username = %s;"
    variables = (username,)
    result = db_handler.QueryHandler.get_results(query, variables)

    if result:
        contacts_list = result[0]['contacts']
        for friend in contacts_list:
            (result, mid) = client.subscribe(topic='user_presence.' + str(friend) + '_presence', qos=1)


def subscribe_contacts_presence(client_id, user_data):
    client = Client(client_id=client_id, clean_session=False, userdata=user_data)
    client.on_connect = on_contacts_presence_subscriber_connect
    client.on_message = on_contacts_presence_subscriber_message

    try:
        client.username_pw_set(username=app_settings.BROKER_USERNAME, password=app_settings.BROKER_PASSWORD)
        client.connect_async(host='localhost', port=1883)
        client.loop_start()
    except Exception as e:
        raise e

class StartStopApp(tornado.web.RequestHandler):

    def data_validation(self, username, event):
        response = {'info': '', 'status': 0}
        try:
            query = " SELECT id FROM users WHERE username = %s;"
            variables = (username,)
            result = db_handler.QueryHandler.get_results(query, variables)
            if not result:
                response['info'] = errors.INVALID_USER_ERR
                response['status'] = app_settings.STATUS_404

            if response['status'] == 0 and not event:
                response['info'] = errors.EVENT_NOT_PROVIDED_ERR
                response['status'] = app_settings.STATUS_400

            if response['status'] == 0 and event not in ['0', '1']:
                response['info'] = errors.INVALID_EVENT_ERR
                response['status'] = app_settings.STATUS_400

            return (response['info'], response['status'])
        except Exception as e:
            raise e

    def post(self):
        response = {}
        try:
            user = str(self.get_argument('user', '')).strip()
            event = str(self.get_argument('event', '')).strip()
            response['info'], response['status'] = self.data_validation(user, event)

            if response['status'] not in app_settings.ERROR_CODES_LIST:
                if event == '1':
                    message = user + ':1'
                    presence_type = "on_"
                else:
                    message = user + ':0'
                    presence_type = "off_"

                # publish to its presence queue
                client_id = "paho/" + presence_type + user
                user_data = {'topic': 'user_presence.' + user + '_presence', 'message': message}
                publish_self_presence(client_id, user_data)

                # subscribe to its contacts presence queues
                if event == '1':
                    client_id = "paho/" + 'prsnce' + user
                    user_data = {'user': user}
                    subscribe_contacts_presence(client_id, user_data)

                response['info'] = app_settings.SUCCESS_RESPONSE
                response['status'] = app_settings.STATUS_200
        except Exception as e:
            response['info'] = " Error: %s" % e
            response['status'] = app_settings.STATUS_500
        finally:
            self.write(response)
