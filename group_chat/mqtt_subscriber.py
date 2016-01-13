from paho.mqtt.client import Client
from settings import *


def on_subscriber_message(client, user_data, message):
    try:
        print 'ON SUBSCRIBER MESSAGE!!'
        print 'MESSAGE:', message.payload
    except Exception as e:
        raise e


def on_subscriber_connect(client, user_data, flags, rc):
    (result, mid) = client.subscribe(topic=user_data.get('topic', ''), qos=1)


def group_chat_subscriber(client_id, user_data):
    client = Client(client_id=client_id, clean_session=False, userdata=user_data)
    client.on_connect = on_subscriber_connect
    client.on_message = on_subscriber_message

    try:
        client.username_pw_set(username=BROKER_USERNAME, password=BROKER_PASSWORD)
        client.connect_async(host='localhost', port=1883)
        client.loop_start()
    except Exception as e:
        raise e
