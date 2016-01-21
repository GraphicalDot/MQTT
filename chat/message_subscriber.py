import random
import string
from paho.mqtt.client import Client

from chat.utils import *
from chat.message_publisher import *
from project.db_handler import *


def on_subscriber_message(client, user_data, message):
    try:
        msg = str(message.payload).split(':')
        sender = msg[0]
        receiver = msg[1]

        # publish for double tick
        client_id = 'chat_msg_received/' + generate_random_client_id(18)
        user_data = {'topic': 'msg_received_' + receiver + '.' + sender + ':' + msg[2], 'message': str(message.payload)}
        publish_msg_received(client_id, user_data)

    except Exception as e:
        raise e
        # pass


def on_subscriber_connect(client, user_data, flags, rc):
    try:
        (result, mid) = client.subscribe(topic=user_data.get('topic', ''), qos=1)
    except Exception as e:
        raise e
        # pass


def simple_chat_subscriber(client_id, user_data):
    try:
        user_data['client_id'] = str(client_id)
        client = Client(client_id=client_id, clean_session=False, userdata=user_data)
        client.on_connect = on_subscriber_connect
        client.on_message = on_subscriber_message

        client.username_pw_set(username=BROKER_USERNAME, password=BROKER_PASSWORD)
        client.connect_async(host='localhost', port=1883)
        client.loop_start()
    except Exception as e:
        raise e
        # pass
