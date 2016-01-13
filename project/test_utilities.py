from paho.mqtt.client import Client
from project.db_handler import *
from project.app_settings import *


def on_presence_subscriber_message(client, user_data, message):
    print 'INSIDE ON PRESENCE SUBSCRIBER MESSAGE'
    client.loop_stop()

def on_presence_subscriber_connect(client, user_data, flags, rc):
    print 'INSIDE ON PRESENCE SUBSCRIBER CONNECT'
    (result, mid) = client.subscribe(topic='user_presence.' + str(user_data.get('user')) + '_presence', qos=1)

def start_presence_subscriber(client_id, user_data):
    print "inside start_subscriber", client_id, len(client_id)
    client = Client(client_id=client_id, clean_session=False, userdata=user_data)
    client.on_connect = on_presence_subscriber_connect
    client.on_message = on_presence_subscriber_message

    try:
        client.username_pw_set(username=BROKER_USERNAME, password=BROKER_PASSWORD)
        client.connect_async(host='localhost', port=1883)
        client.loop_start()
        print 'SUBSCRIBER STARTED!'
    except Exception as e:
        print "inside Exception:", e
