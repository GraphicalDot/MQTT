import random
import string
from paho.mqtt.client import Client

from project.db_handler import *


def generate_random_client_id(len):
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(23-len))


def connect_to_server(client):
    try:
        client.username_pw_set(username=BROKER_USERNAME, password=BROKER_PASSWORD)
        client.connect_async(host='localhost', port=1883)
        client.loop_start()
    except Exception as e:
        raise e
        # pass