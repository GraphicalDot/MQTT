import time
import thread
from paho.mqtt.client import Client

from chat.utils import *
from project.app_settings import *
from project.db_handler import *


def send_media_again_if_unreached(client, user_data, msg_id):
    print 'inside send_media_again_if_unreached'
    try:
        message = str(user_data.get('message', '')).split(':')
        for i in range(1, 6):
            query = " SELECT double_tick FROM chat_messages WHERE id=%s;"
            variables = (str(msg_id),)
            result = QueryHandler.get_results(query, variables)

            if result and result[0]['double_tick'] == '':
                time.sleep(5)
            else:
                client.loop_stop()
                client.reinitialise(client_id=user_data['client_id'], clean_session=False)
                break

        if i >= 5:
            new_message = message[0] + ':' + message[1] + ':' + message[2] + ':again'
            client_id = generate_random_client_id(0)
            user_data = {'topic': 'simple_media_' + message[1] + '.' + message[0],
                         'message': new_message, 'msg_id': msg_id}
            simple_chat_media_publisher(client_id, user_data)

        thread.exit_thread()
    except Exception as e:
        raise e
        # pass


def on_simple_chat_media_publisher_message(client, user_data, mid):
    try:
        msg = str(user_data.get('message', '')).split(':')
        result = []

        if len(msg) <= 3:
            # add message to database
            query = " INSERT INTO chat_messages(sender, receiver, message, single_tick, is_media_message) " \
                    "VALUES (%s, %s, %s, %s, %s) RETURNING id;"
            variables = (msg[0], msg[1], msg[2], 'done', True)
            QueryHandler.execute(query, variables)

        msg_id = result[0]['id'] if result else user_data.get('msg_id', 0)
        thread.start_new_thread(send_media_again_if_unreached, (client, user_data, msg_id))
    except Exception as e:
        raise e
        # pass


def on_simple_chat_media_publisher_connect(client, user_data, flags, rc):
    try:
        client.publish(topic=user_data['topic'], payload=user_data['message'], qos=1, retain=True)
    except Exception as e:
        raise e
        # pass


def simple_chat_media_publisher(client_id, user_data):
    try:
        user_data['client_id'] = str(client_id)
        client = Client(client_id=client_id, clean_session=False, userdata=user_data)
        client.on_connect = on_simple_chat_media_publisher_connect
        client.on_publish = on_simple_chat_media_publisher_message

        client.username_pw_set(username=BROKER_USERNAME, password=BROKER_PASSWORD)
        client.connect_async(host='localhost', port=1883)
        client.loop_start()
    except Exception as e:
        raise e
        # pass
