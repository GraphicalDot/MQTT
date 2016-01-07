import random
from paho.mqtt.client import Client
from app_settings import *
from db_handler import *


def connect_to_server(client):
    print "inside connect to server"
    try:
        client.username_pw_set(username=BROKER_USERNAME, password=BROKER_PASSWORD)
        client.connect_async(host='localhost', port=1883)
        client.loop_start()
    except Exception as e:
        raise e

def subscriber_connect(client, topic):
    print "inside subscriber connect"
    (result, mid) = client.subscribe(topic=user_data.get('topic', ''), qos=1)




def on_simple_chat_media_subscriber_message(client, user_data, message):
    print "ON SIMPLE CHAT MEDIA SUBSCRIBER MESSAGE"
    try:
        print "message:", message.payload
    except Exception as e:
        raise e


def on_simple_chat_media_subscriber_connect(client, user_data, flags, rc):
    print "ON SIMPLE CHAT MEDIA SUBSCRIBER CONNECT"
    try:
        subscriber_connect(client, topic)
    except Exception as e:
        raise e


def simple_chat_media_subscriber(client_id, user_data):
    print "ON SIMPLE CHAT MEDIA SUBSCRIBER"
    try:
        user_data['client_id'] = str(client_id)
        client = Client(client_id=client_id, clean_session=False, userdata=user_data)
        client.on_connect = on_simple_chat_media_subscriber_connect
        client.on_message = on_simple_chat_media_subscriber_message
        connect_to_server(client)
    except Exception as e:
        raise e
