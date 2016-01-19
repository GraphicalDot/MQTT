import random
import string
from paho.mqtt.client import Client

from chat.utils import *
from chat.mqtt_publisher import *
from project.db_handler import *


def on_subscriber_message(client, user_data, message):
    try:
        msg = str(message.payload).split(':')
        sender = msg[0]
        receiver = msg[1]

        # publish for double tick
        client_id = 'msg_received/' + generate_random_client_id(13)
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
    user_data['client_id'] = str(client_id)
    client = Client(client_id=client_id, clean_session=False, userdata=user_data)
    client.on_connect = on_subscriber_connect
    client.on_message = on_subscriber_message
    connect_to_server(client)
