import random
import string
import time
from paho.mqtt.client import Client

from project.db_handler import *
from project.rabbitmq_utils import *


def generate_random_client_id(len):
        return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(23-len))


def initiate_simple_chat_single_tick_subscriber(msg_data):
    try:
        # client_id = 'single_tick_' + user[2:]
        routing_key = 'single_tick.' + BROKER_USERNAME
        create_bind_queue(SIMPLE_CHAT_SINGLE_TICK_EXCHANGE, routing_key)
        client_id = "scst/" + generate_random_client_id(len("scst/"))
        subscribe_simple_chat_single_tick(client_id=client_id, user_data={'topic': routing_key, 'msg_data': msg_data})
    except Exception as e:
        raise e



def initiate_simple_chat_double_tick_subscriber(msg_data):
    print "INITIATE SIMPLE CHAT DOUBLE TICK SUBSCRIBER"
    print 'MSG DATA:', msg_data, type(msg_data)
    try:
        # client_id = 'double_tick_' + user[2:]
        routing_key = 'double_tick.' + BROKER_USERNAME
        create_bind_queue(SIMPLE_CHAT_DOUBLE_TICK_EXCHANGE, routing_key)
        client_id = "scdt/" + generate_random_client_id(len("scdt/"))
        subscribe_simple_chat_double_tick(client_id=client_id, user_data={'topic': routing_key, 'msg_data': msg_data})
    except Exception as e:
        raise e


def connect_to_server(client):
    print "inside connect to server"
    try:
        client.username_pw_set(username=BROKER_USERNAME, password=BROKER_PASSWORD)
        client.connect_async(host='localhost', port=1883)
        client.loop_start()
    except Exception as e:
        print "Inside exception:", e
        raise e


def chat_publisher_on_connect(client, user_data, flags, rc):
    print 'ON PUBLISHER CONNECT:::::', user_data['message']
    try:
        client.publish(topic=user_data['topic'], payload=user_data['message'], qos=1, retain=True)
    except Exception as e:
        print 'inside exception:', e
        # raise e
        pass

####################### SINGLE TICK SUBSCRIBER ############################
def on_single_tick_subscriber_connect(client, user_data, flags, rc):
    print 'ON SINGLE TICK SUBSCRIBER CONNECT'
    try:
        (result, mid) = client.subscribe(topic=user_data.get('topic', ''), qos=1)
        initiate_simple_chat_double_tick_subscriber(user_data.get('msg_data'))
    except Exception as e:
        print 'inside exception:', e
        raise e

def on_single_tick_subscriber_message(client, user_data, message):
    print 'IN SINGLE TICK SUBSCRIBER MESSAGE::::', message
    try:
        msg = message.payload.split(':')
        chat_message_id = check_database(msg)
        query = " UPDATE chat_messages SET single_tick=%s WHERE id=%s AND single_tick='';"
        variables = ('done', chat_message_id)
        QueryHandler.execute(query, variables)
        client.loop_stop()
    except Exception as e:
        # raise e
        pass

def subscribe_simple_chat_single_tick(client_id, user_data):
    client = Client(client_id=client_id, clean_session=False, userdata=user_data)
    client.on_connect = on_single_tick_subscriber_connect
    client.on_message = on_single_tick_subscriber_message
    connect_to_server(client)

################ SINGLE TICK PUBLISHER #############

def simple_chat_single_tick_on_publisher_message(client, user_data, mid):
    print 'IN SINGLE TICK PUBLISHER MESSAGE::::', user_data['message']


def publish_simple_chat_single_tick(client_id, user_data):
    user_data['client_id'] = str(client_id)
    client = Client(client_id=client_id, clean_session=False, userdata=user_data)
    client.on_connect = chat_publisher_on_connect
    client.on_publish = simple_chat_single_tick_on_publisher_message
    connect_to_server(client)


################### DOUBLE TICK SUBSCRIBER ##############################
def on_double_tick_subscriber_connect(client, user_data, flags, rc):
    print 'ON DOUBLE TICK SUBSCRIBER CONNECT'
    try:
        (result, mid) = client.subscribe(topic=user_data.get('topic', ''), qos=1)

        # publish the chat message
        client_id = "send_msg/" + generate_random_client_id(len("send_msg/"))
        msg_data = user_data.get('msg_data')
        publish_to_simple_chat(client_id, msg_data)

    except Exception as e:
        print 'inside exception:', e
        raise e

def check_database(msg):
    print 'inside check database'
    try:
        query = " SELECT id FROM chat_messages WHERE sender=%s AND receiver=%s AND message=%s;"
        variables = (msg[0], msg[1], msg[2])
        result = QueryHandler.get_results(query, variables)
        print 'result:', result
        if len(result) > 0:
            print 'if mg entered in db'
            id = result[0]['id']
        else:
            print 'if msg not present in db...wait'
            time.sleep(10)
            id = check_database(msg)
    except Exception as e:
        raise e
    finally:
        return id

def on_double_tick_subscriber_message(client, user_data, message):
    print 'IN DOUBLE TICK SUBSCRIBER MESSAGE::::', message
    try:
        msg = message.payload.split(':')

        chat_message_id = check_database(msg)
        query = " UPDATE chat_messages SET double_tick=%s WHERE id=%s AND double_tick='';"
        variables = ('done', chat_message_id)
        QueryHandler.execute(query, variables)
        client.loop_stop()
    except Exception as e:
        print 'exception:', e
        # raise e
        pass

def subscribe_simple_chat_double_tick(client_id, user_data):
    client = Client(client_id=client_id, clean_session=False, userdata=user_data)
    client.on_connect = on_double_tick_subscriber_connect
    client.on_message = on_double_tick_subscriber_message
    connect_to_server(client)

############# DOUBLE TICK PUBLISHER ################

def on_double_tick_publisher_message(client, user_data, mid):
    print 'IN DOUBLE TICK PUBLISHER MESSAGE:::::', user_data['message']
    try:
        client.loop_stop()
        client.reinitialise(client_id=user_data['client_id'], clean_session=False)
    except Exception as e:
        print "inside exception:", e
        # raise e
        pass

def publish_simple_chat_double_tick(client_id, user_data):
    user_data['client_id'] = str(client_id)
    client = Client(client_id=client_id, clean_session=False, userdata=user_data)
    client.on_connect = chat_publisher_on_connect
    client.on_publish = on_double_tick_publisher_message
    connect_to_server(client)

################# SIMPLE CHAT PUBLISHER ####################
def on_simple_chat_publisher_connect(client, user_data, flags, rc):
    print "SIMPLE CHAT PUBLISHER CONNECT:::::", user_data['message']
    try:
        client.publish(topic=user_data['topic'], payload=user_data['message'], qos=1, retain=True)
    except Exception as e:
        print "inside exception:", e
        raise e

def on_simple_chat_publisher_message(client, user_data, mid):
    print 'SIMPLE CHAT PUBLISHER MESSAGE:::::', user_data['message']
    try:
        msg = str(user_data.get('message', ''))
        sender = str(user_data.get('sender', ''))
        receiver = str(user_data.get('receiver', ''))
        message = msg.split(':')

        # add message to database
        query = " INSERT INTO chat_messages(sender, receiver, message) VALUES (%s, %s, %s);"
        variables = (message[0], message[1], message[2])
        QueryHandler.execute(query, variables)

        # publish for single tick
        client_id = sender[2:] + "scstpub_" + "".join(random.choice(msg) for x in range(23-18))
        publish_simple_chat_single_tick(client_id=client_id, user_data={'topic': 'single_tick.' + BROKER_USERNAME,
                                                                        'message': msg})
        client.loop_stop()
    except Exception as e:
        print 'inside exception:', e
        # raise e
        pass

def publish_to_simple_chat(client_id, user_data):
    user_data['client_id'] = str(client_id)
    client = Client(client_id=client_id, clean_session=False, userdata=user_data)
    client.on_connect = on_simple_chat_publisher_connect
    client.on_publish = on_simple_chat_publisher_message
    connect_to_server(client)


######################## SIMPLE CHAT SUBSCRIBER ##################
def on_simple_chat_subscriber_message(client, user_data, message):
    print 'ON SIMPLE CHAT SUBSCRIBER MESSAGE::::', message
    try:
        msg = str(message.payload).split(':')
        sender = msg[0]

        # publish for double tick
        client_id = sender[2:] + "scdtpub_" + "".join(random.choice(message.payload) for x in range(23-18))
        publish_simple_chat_double_tick(client_id=client_id, user_data={'topic': 'double_tick.' + BROKER_USERNAME,
                                                                        'message': str(message.payload)})
    except Exception as e:
        print 'inside exception:', e
        # raise e
        pass

def on_simple_chat_subscriber_connect(client, user_data, flags, rc):
    print 'ON SIMPLE CHAT SUBSCRIBER CONNECT::::', user_data
    (result, mid) = client.subscribe(topic=user_data.get('topic', ''), qos=1)

def simple_chat_subscriber(client_id, user_data):
    print 'insie simple chat subscriber', client_id, len(client_id)
    user_data['client_id'] = str(client_id)
    client = Client(client_id=client_id, clean_session=False, userdata=user_data)
    client.on_connect = on_simple_chat_subscriber_connect
    client.on_message = on_simple_chat_subscriber_message
    connect_to_server(client)
