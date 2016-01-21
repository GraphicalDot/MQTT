import random
from paho.mqtt.client import Client

from project.db_handler import *
from project.app_settings import *


def on_presence_subscriber_message(client, user_data, message):
    client.loop_stop()


def on_presence_subscriber_connect(client, user_data, flags, rc):
    (result, mid) = client.subscribe(topic='user_presence.' + str(user_data.get('user')) + '_presence', qos=1)


def start_presence_subscriber(client_id, user_data):
    client = Client(client_id=client_id, clean_session=False, userdata=user_data)
    client.on_connect = on_presence_subscriber_connect
    client.on_message = on_presence_subscriber_message
    try:
        client.username_pw_set(username=BROKER_USERNAME, password=BROKER_PASSWORD)
        client.connect_async(host='localhost', port=1883)
        client.loop_start()
    except Exception as e:
        raise e

def generate_random_id():
        return "testing/" + "".join(random.choice("0123456789ADCDEF") for x in range(23-8))


def delete_chat_messages():
    query = "DELETE FROM chat_messages;"
    try:
        QueryHandler.execute(query)
    except Exception as e:
        raise e

def delete_registered_users():
    try:
        query = " DELETE from registered_users;"
        QueryHandler.execute(query)
    except Exception as e:
        raise e

def delete_users():
    query = " DELETE FROM users;"
    try:
        QueryHandler.execute(query)
    except Exception as e:
        raise e


def create_users(users_list):
    for user in users_list:
        query = " INSERT INTO users(username, password, member_of_groups, status, contacts) values (%s, %s, %s, %s, %s);"
        variables = (str(user), '', '{}', '0', '{}')
        try:
            QueryHandler.execute(query, variables)
        except Exception as e:
            raise e
