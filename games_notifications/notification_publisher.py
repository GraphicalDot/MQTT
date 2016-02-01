import json
import os
import sys
from paho.mqtt.client import Client

sys.path.append(os.path.dirname(os.path.abspath(__file__)).rsplit('/', 1)[0])

import utils


def notification_publisher_message(client, user_data, mid):
    try:
        # stop the publishing thread
        client.loop_stop()
        client.reinitialise(client_id=user_data['client_id'], clean_session=False)
    except Exception as e:
        raise e
        # pass

def notification_publisher_connect(client, user_data, flags, rc):
    try:
        client.publish(topic=user_data['topic'], payload=json.dumps(user_data['message']), qos=1, retain=True)
    except Exception as e:
        raise e
        # pass


def notification_publisher(client_id, user_data):
    try:
        user_data['client_id'] = str(client_id)
        client = Client(client_id=client_id, clean_session=False, userdata=user_data)
        client.on_connect = notification_publisher_connect
        client.on_publish = notification_publisher_message

        utils.connect_to_server(client)
    except Exception as e:
        raise e
        # pass
