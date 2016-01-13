from paho.mqtt.client import Client
from db_handler import *
from settings import *


def on_publisher_connect(client, user_data, flags, rc):
    try:
        client.publish(topic=user_data['topic'], payload=user_data['message'], qos=1, retain=True)
    except Exception as e:
        raise e


# event handler called when message has reached to the server.
def on_publisher_message(client, user_data, mid):
    try:
        # add message to database
        query = " INSERT INTO group_messages(group_owner, group_name, sender, message) VALUES (%s, %s, %s, %s);"
        variables = (user_data.get('group_owner'), user_data.get('group_name'), user_data.get('sender'),
                     user_data.get('message'))
        LocalQueryHandler.execute(query, variables)

        # stop the publishing thread
        client.loop_stop()
        client.reinitialise(client_id=user_data['client_id'], clean_session=False)
    except Exception as e:
        raise e


def group_chat_publisher(client_id, user_data):
    user_data['client_id'] = str(client_id)
    client = Client(client_id=client_id, clean_session=False, userdata=user_data)
    client.on_connect = on_publisher_connect
    client.on_publish = on_publisher_message
    try:
        client.username_pw_set(username=BROKER_USERNAME, password=BROKER_PASSWORD)
        client.connect_async(host='localhost', port=1883)
        client.loop_start()
    except Exception as e:
        raise e
