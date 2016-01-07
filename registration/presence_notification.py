import tornado
import tornado.web
from paho.mqtt.client import Client

from app_settings import *
from db_handler import *
from errors import *
from utils import *
from group_chat.mqtt_subscriber import *
from group_chat.mqtt_publisher import *

def on_connect(client, user_data, flags, rc):
    print "ON PUBLISHER CONNECT"
    try:
        print '#################TOPIC ON WHICH TO PUBLISH:', user_data['topic']
        client.publish(topic=user_data['topic'], payload=user_data['message'], qos=1, retain=True)
        print 'PUBLISHED!!!!!!!!!!!!!!!!!!!!!!!'
    except Exception as e:
        print 'INSIDE EXCEPTION!!!!!!!:', e
        raise e


def on_message(client, user_data, mid):
    print "ON PUBLISHER MESSAGE"
    try:
        # add message to database
        (username, status) = (user_data['message'].split(':')[0], user_data['message'].split(':')[1])
        query = " UPDATE users SET status = %s WHERE username = %s;"
        variables = (status, username, )
        QueryHandler.execute(query, variables)
        print "MESSAGE SENT TO THE BROKER!"

        # stop the publishing thread
        client.loop_stop()
        client.reinitialise(client_id=user_data['client_id'], clean_session=False)
    except Exception as e:
        print "inside exception"
        raise e


def publish_self_presence(client_id, user_data):
    print "inside publish_self_presence"
    print 'CLIENT:', client_id
    user_data['client_id'] = str(client_id)
    client = Client(client_id=client_id, clean_session=False, userdata=user_data)
    client.on_connect = on_connect
    client.on_publish = on_message
    try:
        client.username_pw_set(username=BROKER_USERNAME, password=BROKER_PASSWORD)
        client.connect_async(host='localhost', port=1883)
        client.loop_start()
        print 'publisher started'
    except Exception as e:
        print "inside Exception:", e
        raise e


def on_subscriber_message(client, user_data, message):
    try:
        print 'ON SUBSCRIBER MESSAGE!!'
        print 'MESSAGE:', message.payload
    except Exception as e:
        print "inside exception:", e
        raise e


def on_subscriber_connect(client, user_data, flags, rc):
    print "ON SUBSCRIBER CONNECT"
    username = user_data.get('user', '')
    query = " SELECT contacts FROM users WHERE username = %s;"
    variables = (username,)
    result = QueryHandler.get_results(query, variables)
    print "result:", result

    if result:
        contacts_list = result[0]['contacts']
        for friend in contacts_list:
            print 'FRIEND:', friend
            (result, mid) = client.subscribe(topic='user_presence.' + str(friend) + '_presence', qos=1)


def subscribe_contacts_presence(client_id, user_data):
    print "inside subscribe contacts presence"
    client = Client(client_id=client_id, clean_session=False, userdata=user_data)
    client.on_connect = on_subscriber_connect
    client.on_message = on_subscriber_message

    try:
        client.username_pw_set(username=BROKER_USERNAME, password=BROKER_PASSWORD)
        client.connect_async(host='localhost', port=1883)
        client.loop_start()
        print 'SUBSCRIBER STARTED!'
    except Exception as e:
        print "inside Exception:", e


class StartStopApp(tornado.web.RequestHandler):

    def data_validation(self, username, event):
        print "inside data validation of StartApp"
        response = {'info': '', 'status': 0}
        try:
            query = " SELECT id FROM users WHERE username = %s;"
            variables = (username,)
            result = QueryHandler.get_results(query, variables)
            if not result:
                response['info'] = INVALID_USER_ERR
                response['status'] = 404

            if event not in ['0', '1']:
                response['info'] = INVALID_EVENT_ERR
                response['status'] = 404

            if not event:
                response['info'] = EVENT_NOT_PROVIDED_ERR
                response['status'] = 400

            return (response['info'], response['status'])
        except Exception as e:
            raise e

    def get(self):
        print "inside get of StartApp"
        response = {}
        try:
            user = str(self.get_argument('user', '')).strip()
            event = str(self.get_argument('event', '')).strip()
            print 'user:', user
            (response['info'], response['status']) = self.data_validation(user, event)
            print 'response of validation:', response['info']

            if response['status'] not in [404, 400]:
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
                    print "inside ifffffffffff!!"
                    client_id = "paho/" + 'prsnce' + user
                    print 'client id:', client_id, len(client_id)
                    user_data = {'user': user}
                    subscribe_contacts_presence(client_id, user_data)


                response['info'] = "Success"
                response['status'] = 200
        except Exception as e:
            response['info'] = " Error: %s" % e
            response['status'] = 500
        finally:
            self.write(response)

