import requests
import os
import sys
from paho.mqtt.client import Client

sys.path.append(os.path.dirname(os.path.abspath(__file__)).rsplit('/', 1)[0])

from project.app_settings import *
from project.db_handler import *


def connect_to_server(client):
    try:
        client.username_pw_set(username=BROKER_USERNAME, password=BROKER_PASSWORD)
        client.connect_async(host='localhost', port=1883)
        client.loop_start()
    except Exception as e:
        raise e

def subscriber_connect(client, topic):
    (result, mid) = client.subscribe(topic=topic, qos=1)


def publisher_connect(client, user_data, flags, rc):
    try:
        client.publish(topic=user_data['topic'], payload=user_data['message'], qos=1, retain=True)
    except Exception as e:
        raise e




def on_simple_chat_media_subscriber_message(client, user_data, message):
    try:
        msg = str(message.payload.strip(':'))

        # get the media file
        response = requests.get('http://localhost:3000/simple_send_media?name={}'.format(msg[2]))
    except Exception as e:
        raise e


def on_simple_chat_media_subscriber_connect(client, user_data, flags, rc):
    try:
        topic = user_data.get('topic', '')
        subscriber_connect(client, topic)
    except Exception as e:
        raise e


def simple_chat_media_subscriber(client_id, user_data):
    try:
        user_data['client_id'] = str(client_id)
        client = Client(client_id=client_id, clean_session=False, userdata=user_data)
        client.on_connect = on_simple_chat_media_subscriber_connect
        client.on_message = on_simple_chat_media_subscriber_message
        connect_to_server(client)
    except Exception as e:
        raise e


def on_simple_chat_media_publisher_message(client, user_data, mid):
    try:
        msg = str(user_data.get('message', '')).split(':')
        # add message to database
        query = " INSERT INTO chat_messages(sender, receiver, message, is_media_message) VALUES (%s, %s, %s, %s);"
        variables = (msg[0], msg[1], msg[2], True)
        QueryHandler.execute(query, variables)

        # stop the publishing thread
        client.loop_stop()
        client.reinitialise(client_id=user_data['client_id'], clean_session=False)
    except Exception as e:
        raise e


def publish_simple_chat_media(client_id, user_data):
    try:
        user_data['client_id'] = str(client_id)
        client = Client(client_id=client_id, clean_session=False, userdata=user_data)
        client.on_connect = publisher_connect
        client.on_publish = on_simple_chat_media_publisher_message
        connect_to_server(client)
    except Exception as e:
        raise e
