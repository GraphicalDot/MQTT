import random
import string
from paho.mqtt.client import Client

from project.db_handler import *


def chat_publisher_subscriber(client_id, user_data, on_connect_function, on_message_function):
    user_data['client_id'] = str(client_id)
    client = Client(client_id=client_id, clean_session=False, userdata=user_data)
    client.on_connect = on_connect_function
    client.on_publish = on_message_function
    try:
        client.username_pw_set(username=BROKER_USERNAME, password=BROKER_PASSWORD)
        # client.connect_async(host='localhost', port=1883)
        client.connect(host='localhost', port=1883)
        client.loop_start()
    except Exception as e:
        # raise e
        pass

def chat_publisher_on_connect(client, user_data, flags, rc):
    print 'ON PUBLISHER CONNECT:::::', user_data['message']
    try:
        client.publish(topic=user_data['topic'], payload=user_data['message'], qos=1, retain=True)
    except Exception as e:
        # raise e
        pass

def chat_subsciber_on_connect(client, user_data, flags, rc):
    print 'ON SUBSCRIBER CONNECT::::',
    try:
        (result, mid) = client.subscribe(topic=user_data.get('topic', ''), qos=1)
    except Exception as e:
        # raise e
        pass
##----------------------------------------------------------------------------------------------------------------------

def on_simple_chat_subscriber_message(client, user_data, message):
    print 'ON SIMPLE CHAT SUBSCRIBER MESSAGE::::', message
    try:
        msg = str(message.payload).split(':')
        sender = msg[0]
        print 'sender:', sender

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
    print 'inside SIMPLE CHAT SUBSCRIBER'
    user_data['client_id'] = str(client_id)
    client = Client(client_id=client_id, clean_session=False, userdata=user_data)
    client.on_connect = on_simple_chat_subscriber_connect
    client.on_message = on_simple_chat_subscriber_message

    try:
        client.username_pw_set(username=BROKER_USERNAME, password=BROKER_PASSWORD)
        client.connect_async(host='localhost', port=1883)
        client.loop_start()
    except Exception as e:
        # raise e
        pass

def on_simple_chat_publisher_connect(client, user_data, flags, rc):
    print "SIMPLE CHAT PUBLISHER CONNECT:::::", user_data['message']
    try:
        client.publish(topic=user_data['topic'], payload=user_data['message'], qos=1, retain=True)
    except Exception as e:
        # raise e
        pass

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

        # publish for double click
        # client_id = sender[2:] + "scdtpub_" + "".join(random.choice(message) for x in range(23-18))
        # publish_simple_chat_double_tick(client_id=client_id, user_data={'topic': 'double_tick.' + BROKER_USERNAME,
        #                                                                 'message': str(user_data.get('message'))})

        # publish for single tick
        client_id = sender[2:] + "scstpub_" + "".join(random.choice(msg) for x in range(23-18))
        publish_simple_chat_single_tick(client_id=client_id, user_data={'topic': 'single_tick.' + BROKER_USERNAME,
                                                                        'message': msg})

        client.loop_stop()
    except Exception as e:
        # raise e
        pass

def publish_to_simple_chat(client_id, user_data):
    user_data['client_id'] = str(client_id)
    client = Client(client_id=client_id, clean_session=False, userdata=user_data)
    client.on_connect = on_simple_chat_publisher_connect
    client.on_publish = on_simple_chat_publisher_message
    try:
        client.username_pw_set(username=BROKER_USERNAME, password=BROKER_PASSWORD)
        client.connect_async(host='localhost', port=1883)
        client.loop_start()
    except Exception as e:
        # raise e
        pass
#-----------------------------------------------------------------------------
def publish_simple_chat_single_tick(client_id, user_data):
    chat_publisher_subscriber(client_id=client_id, user_data=user_data, on_connect_function=chat_publisher_on_connect,
                              on_message_function=simple_chat_single_tick_on_publisher_message)


def simple_chat_single_tick_on_publisher_message(client, user_data, mid):
    print 'IN SINGLE TICK PUBLISHER MESSAGE::::', user_data['message']
    try:
        client.loop_stop()
        client.reinitialise(client_id=user_data['client_id'], clean_session=False)
    except Exception as e:
        # raise e
        pass

def subscribe_simple_chat_single_tick(client_id, user_data):
    client = Client(client_id=client_id, clean_session=False, userdata=user_data)
    client.on_connect = chat_subsciber_on_connect
    client.on_message = on_single_tick_subscriber_message

    try:
        client.username_pw_set(username=BROKER_USERNAME, password=BROKER_PASSWORD)
        client.connect_async(host='localhost', port=1883)
        client.loop_start()
    except Exception as e:
        # raise e
        pass

def on_single_tick_subscriber_message(client, user_data, message):
    print 'IN SINGLE TICK SUBSCRIBER MESSAGE::::', message
    try:
        msg = message.payload.split(':')
        query = " UPDATE chat_messages SET single_tick=%s WHERE sender=%s AND receiver=%s AND message=%s AND single_tick='';"
        variables = ('done', msg[0], msg[1], msg[2])
        QueryHandler.execute(query, variables)
        client.loop_stop()
    except Exception as e:
        # raise e
        pass
##------------------------------------------------------------

def on_double_tick_subscriber_message(client, user_data, message):
    print 'IN DOUBLE TICK SUBSCRIBER MESSAGE::::', message
    try:
        msg = message.payload.split(':')
        query = " UPDATE chat_messages SET double_tick=%s WHERE sender=%s AND receiver=%s AND message=%s AND double_tick='';"
        variables = ('done', msg[0], msg[1], msg[2])
        QueryHandler.execute(query, variables)
        client.loop_stop()
    except Exception as e:
        # raise e
        pass

def subscribe_simple_chat_double_tick(client_id, user_data):
    client = Client(client_id=client_id, clean_session=False, userdata=user_data)
    client.on_connect = chat_subsciber_on_connect
    client.on_message = on_double_tick_subscriber_message

    try:
        client.username_pw_set(username=BROKER_USERNAME, password=BROKER_PASSWORD)
        client.connect_async(host='localhost', port=1883)
        client.loop_start()
    except Exception as e:
        # raise e
        pass

def on_double_tick_publisher_connect(client, user_data, flags, rc):
    print 'IN DOUBLE TICK PUBLISHER CONNECT:::::', user_data['message']
    try:
        client.publish(topic=user_data['topic'], payload=user_data['message'], qos=1, retain=True)
    except Exception as e:
        # raise e
        pass

def on_double_tick_publisher_message(client, user_data, mid):
    print 'IN DOUBLE TICK PUBLISHER MESSAGE:::::', user_data['message']
    try:
        client.loop_stop()
        client.reinitialise(client_id=user_data['client_id'], clean_session=False)
    except Exception as e:
        # raise e
        pass

def publish_simple_chat_double_tick(client_id, user_data):
    user_data['client_id'] = str(client_id)
    client = Client(client_id=client_id, clean_session=False, userdata=user_data)
    client.on_connect = on_double_tick_publisher_connect
    client.on_publish = on_double_tick_publisher_message
    try:
        client.username_pw_set(username=BROKER_USERNAME, password=BROKER_PASSWORD)
        client.connect(host='localhost', port=1883)
        client.loop_start()
    except Exception as e:
        # raise e
        pass
