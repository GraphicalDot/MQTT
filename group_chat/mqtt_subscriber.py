import os
import sys
from paho.mqtt.client import Client

sys.path.append(os.path.dirname(os.path.abspath(__file__)).rsplit('/', 1)[0])
import mqtt_publisher
from chat import utils
from project import app_settings, rabbitmq_utils


def on_subscriber_message(client, user_data, message):
    try:
        msg = str(message.payload).split(':')
        group_owner = msg[0]
        group_name = msg[1]
        sender = msg[2]
        message = msg[3]
        total_members = msg[4]

        # publish for double tick
        client_id = group_name[:5] + '_msg_received/' + utils.generate_random_client_id(20)
        user_data = {'topic': 'msg_received.' + group_owner + '.' + group_name,
                     'message': group_owner + ':' + group_name + ':' + sender + ':' + message + ':' + total_members}
        mqtt_publisher.publish_group_msg_received(client_id, user_data)

    except Exception as e:
        # raise e
        pass

def on_subscriber_connect(client, user_data, flags, rc):
    (result, mid) = client.subscribe(topic=user_data.get('topic', ''), qos=1)


def group_chat_subscriber(client_id, user_data):
    client = Client(client_id=client_id, clean_session=False, userdata=user_data)
    client.on_connect = on_subscriber_connect
    client.on_message = on_subscriber_message

    try:
        client.username_pw_set(username=app_settings.BROKER_USERNAME, password=app_settings.BROKER_PASSWORD)
        client.connect_async(host='localhost', port=1883)
        client.loop_start()
    except Exception as e:
        # raise e
        pass
