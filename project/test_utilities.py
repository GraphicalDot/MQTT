import os
import random
import sys
from paho.mqtt.client import Client

sys.path.append(os.path.dirname(os.path.abspath(__file__)).rsplit('/', 1)[0])
from project import db_handler, app_settings


def on_presence_subscriber_message(client, user_data, message):
    client.loop_stop()


def on_presence_subscriber_connect(client, user_data, flags, rc):
    (result, mid) = client.subscribe(topic='user_presence.' + str(user_data.get('user')) + '_presence', qos=1)


def start_presence_subscriber(client_id, user_data):
    client = Client(client_id=client_id, clean_session=False, userdata=user_data)
    client.on_connect = on_presence_subscriber_connect
    client.on_message = on_presence_subscriber_message
    try:
        client.username_pw_set(username=app_settings.BROKER_USERNAME, password=app_settings.BROKER_PASSWORD)
        client.connect_async(host='localhost', port=1883)
        client.loop_start()
    except Exception as e:
        raise e

def generate_random_id():
        return "testing/" + "".join(random.choice("0123456789ADCDEF") for x in range(23-8))


def delete_chat_messages():
    query = "DELETE FROM chat_messages;"
    try:
        db_handler.QueryHandler.execute(query)
    except Exception as e:
        raise e

def delete_registered_users():
    try:
        query = " DELETE from registered_users;"
        db_handler.QueryHandler.execute(query)
    except Exception as e:
        raise e

def delete_users():
    query = " DELETE FROM users;"
    try:
        db_handler.QueryHandler.execute(query)
    except Exception as e:
        raise e


def create_users(users_list):
    for user in users_list:
        query = " INSERT INTO users(username, password, member_of_groups, status, contacts) values (%s, %s, %s, %s, %s);"
        variables = (str(user), '', '{}', '0', '{}')
        try:
            db_handler.QueryHandler.execute(query, variables)
        except Exception as e:
            raise e


def delete_groups():
    query = " DELETE FROM groups_info;"
    try:
        db_handler.QueryHandler.execute(query)
    except Exception as e:
        raise e


def delete_group_messages():
    query = " DELETE FROM group_messages;"
    try:
        db_handler.QueryHandler.execute(query)
    except Exception as e:
        raise e
