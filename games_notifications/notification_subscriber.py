import os
import sys
from paho.mqtt.client import Client

sys.path.append(os.path.dirname(os.path.abspath(__file__)).rsplit('/', 1)[0])

import utils


def notification_subscriber_message(client, user_data, message):
    print 'message reached to the subscriber:', str(message.payload)


def notification_subscriber_connect(client, user_data, flags, rc):
    try:
        (result, mid) = client.subscribe(topic=user_data.get('topic', ''), qos=1)
    except Exception as e:
        # raise e
        pass


def notification_subscriber(client_id, user_data):
    try:
        user_data['client_id'] = str(client_id)
        client = Client(client_id=client_id, clean_session=False, userdata=user_data)
        client.on_connect = notification_subscriber_connect
        client.on_message = notification_subscriber_message
        utils.connect_to_server(client)
    except Exception as e:
        # raise e
        pass
