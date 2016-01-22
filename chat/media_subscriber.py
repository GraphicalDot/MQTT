import os
import requests
import sys
from paho.mqtt.client import Client

sys.path.append(os.path.dirname(os.path.abspath(__file__)).rsplit('/', 1)[0])
import utils, message_publisher
from project import app_settings, db_handler


def on_simple_chat_media_subscriber_message(client, user_data, message):
    try:
        msg = str(message.payload).split(':')
        sender = msg[0]
        receiver = msg[1]

        # publish for double tick
        client_id = 'chat_media_received/' + utils.generate_random_client_id(20)
        user_data = {'topic': 'chat_media_received_' + receiver + '.' + sender + ':' + msg[2],
                     'message': str(message.payload)}
        message_publisher.publish_msg_received(client_id, user_data)

    except Exception as e:
        raise e
        # pass


def on_subscriber_connect(client, user_data, flags, rc):
    try:
        (result, mid) = client.subscribe(topic=user_data.get('topic', ''), qos=1)
    except Exception as e:
        raise e
        # pass


def simple_chat_media_subscriber(client_id, user_data):
    try:
        user_data['client_id'] = str(client_id)
        client = Client(client_id=client_id, clean_session=False, userdata=user_data)
        client.on_connect = on_subscriber_connect
        client.on_message = on_simple_chat_media_subscriber_message

        client.username_pw_set(username=app_settings.BROKER_USERNAME, password=app_settings.BROKER_PASSWORD)
        client.connect_async(host='localhost', port=1883)
        client.loop_start()
    except Exception as e:
        raise e
        # pass
