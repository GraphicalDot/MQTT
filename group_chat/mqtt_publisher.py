import json
import os
import pika
import sys
import thread
import time
from paho.mqtt.client import Client

sys.path.append(os.path.dirname(os.path.abspath(__file__)).rsplit('/', 1)[0])
import settings
from chat import utils
from project import db_handler, app_settings, rabbitmq_utils
import ConfigParser
from ConfigParser import SafeConfigParser


def start_colored_double_tick_subscriber(user_data, msg_id):
    msg = str(user_data.get('message')).split(':')
    group_owner = msg[0]
    group_name = msg[1]
    sender = msg[2]
    group_id = str(user_data.get('group_id'))
    total_members = user_data.get('number_of_members')
    message = msg[3]
    try:
        query = " SELECT double_tick FROM group_messages WHERE id=%s;"
        variables = (msg_id,)
        result = db_handler.QueryHandler.get_results(query, variables)
        if result and result[0]['double_tick'] == 'done':
            query = " UPDATE group_messages SET colored_double_tick='done' WHERE id=%s;"
            variables = (msg_id,)
            db_handler.QueryHandler.execute(query, variables)
        else:
            time.sleep(10)
            thread.start_new_thread(start_colored_double_tick_subscriber, (user_data, msg_id))
        thread.exit_thread()

    except Exception as e:
        # raise e
        pass

def send_group_message_again_if_unreached(client, user_data, msg_id):
    try:
        for i in range(1, 6):
            query = " SELECT double_tick FROM group_messages WHERE id=%s;"
            variables = (str(msg_id),)
            result = db_handler.QueryHandler.get_results(query, variables)
            if result and result[0]['double_tick'] == '':
                time.sleep(10)
            else:
                client.loop_stop()
                client.reinitialise(client_id=user_data['client_id'], clean_session=False)
                break

        if i >= 5:
            msg = str(user_data.get('message', '')).split(':')
            group_owner = msg[0]
            group_name = msg[1]
            sender = msg[2]
            new_message = str(user_data.get('message', '')) + ':again'
            client_id = 'pub_' + group_name + utils.generate_random_client_id(len('pub_' + group_name))
            user_data = {'topic': 'group_chat.' + group_owner + '.' + group_name + '.' + sender,
                         'message': new_message, 'msg_id': msg_id}
            group_chat_publisher(client_id, user_data)

        thread.exit_thread()
    except Exception as e:
        # raise e
        pass


def on_publisher_connect(client, user_data, flags, rc):
    try:
        client.publish(topic=user_data['topic'], payload=user_data['message'], qos=1, retain=True)
    except Exception as e:
        # raise e
        pass

# event handler called when message has reached to the server.
def on_publisher_message(client, user_data, mid):
    try:
        msg = str(user_data.get('message', '')).split(':')
        group_owner = msg[0]
        group_name = msg[1]
        sender = msg[2]
        message = msg[3]

        result = []
        if len(msg) < 6:
            # add message to database
            query = " INSERT INTO group_messages(group_owner, group_name, sender, message, single_tick, double_tick) " \
                    "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;"
            variables = (group_owner, group_name, sender, message, 'done', '')
            result = db_handler.QueryHandler.get_results(query, variables)

            config = ConfigParser.ConfigParser()
            config.add_section(str(result[0]['id']))
            cfgfile = open(app_settings.GROUP_MESSAGES_FILE_PATH, 'a')
            config.write(cfgfile)
            cfgfile.close()

            thread.start_new_thread(start_colored_double_tick_subscriber, (user_data, result[0]['id']))

        msg_id = result[0]['id'] if result else str(user_data.get('msg_id', 0))
        thread.start_new_thread(send_group_message_again_if_unreached, (client, user_data, msg_id))

    except Exception as e:
        raise e
        # pass

def group_chat_publisher(client_id, user_data):
    user_data['client_id'] = str(client_id)
    client = Client(client_id=client_id, clean_session=False, userdata=user_data)
    client.on_connect = on_publisher_connect
    client.on_publish = on_publisher_message
    try:
        client.username_pw_set(username=settings.BROKER_USERNAME, password=settings.BROKER_PASSWORD)
        client.connect_async(host='localhost', port=1883)
        client.loop_start()
    except Exception as e:
        # raise e
        pass

def check_db(msg):
    query = " SELECT id, double_tick FROM group_messages WHERE group_owner=%s AND group_name=%s AND sender=%s AND message=%s " \
            "AND colored_double_tick='';"
    variables = (msg[0], msg[1], msg[2], msg[3])
    result = db_handler.QueryHandler.get_results(query, variables)
    return result


def on_msg_received_publisher_message(client, user_data, mid):
    try:
        msg = str(user_data.get('message', '')).split(':')
        result = check_db(msg)
        if not result:
            time.sleep(10)
            result = check_db(msg)

        if result:
            read_config = ConfigParser.ConfigParser()
            read_config.read(app_settings.GROUP_MESSAGES_FILE_PATH)

            if not read_config.has_section(str(result[0]['id'])):
                read_config.add_section(str(result[0]['id']))

            cfgfile = open(app_settings.GROUP_MESSAGES_FILE_PATH, 'w')
            read_config.set(str(result[0]['id']), user_data['client_id'], user_data['client_id'])
            read_config.write(cfgfile)
            cfgfile.close()

            if len(read_config.items(str(result[0]['id']))) == int(msg[4]):
                query = " UPDATE group_messages SET double_tick='done' WHERE id=%s;"
                variables = (result[0]['id'],)
                db_handler.QueryHandler.execute(query, variables)

        client.loop_stop()
        client.reinitialise(client_id=user_data['client_id'], clean_session=False)
    except Exception as e:
        raise e
        # pass


def publish_group_msg_received(client_id, user_data):
    try:
        user_data['client_id'] = str(client_id)
        client = Client(client_id=client_id, clean_session=False, userdata=user_data)
        client.on_connect = on_publisher_connect
        client.on_publish = on_msg_received_publisher_message

        client.username_pw_set(username=app_settings.BROKER_USERNAME, password=app_settings.BROKER_PASSWORD)
        client.connect_async(host='localhost', port=1883)
        client.loop_start()
    except Exception as e:
        # raise e
        pass
