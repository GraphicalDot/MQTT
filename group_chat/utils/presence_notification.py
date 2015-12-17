from paho.mqtt.client import Client
from db_handler import *


def on_publisher_connect(client, user_data, flags, rc):
    print "INSIDE ON CONNECT"
    try:
        payload = user_data['user'] + ':' + user_data['status']
        client.publish(topic=user_data['topic'], payload=payload, qos=1, retain=True)
        print 'PUBLISHED!!!!!!!!!!!!!!!!!!!!!!!'
    except Exception as e:
        print 'INSIDE EXCEPTION!!!!!!!:', e
        raise e

def on_publisher_publish(client, user_data, mid):
    try:
        print "INSIDE ON PUBLISH"
        print 'STATUS REACHED TO THE SERVER'
        query = " UPDATE users SET status=%s WHERE username=%s;"
        variables = (str(user_data['status']), str(user_data['user']),)
        LocalQueryHandler.execute(query, variables)
        print 'SAVED TO DATABASE!!'
        client_id = str(user_data.get('user', '')) + '_presence'
        print 'client id:', client_id
        client.loop_stop()
        client.reinitialise(client_id=user_data.get('user', '') + '_presence', clean_session=False)
    except Exception as e:
        print "inside exception"
        raise e

def publish_presence_notification(client_id, user_data):
    print "inside publish presence notification"
    client = Client(client_id=client_id, clean_session=False, userdata=user_data)
    client.on_connect = on_publisher_connect
    client.on_publish = on_publisher_publish
    try:
        client.username_pw_set(username=BROKER_USERNAME, password=BROKER_PASSWORD)
        client.connect_async(host=MOSQUITTO_IP, port=MOSQUITTO_PORT)
        client.loop_start()
        print 'publisher started'
    except Exception as e:
        print "inside Exception:", e
        raise e


################ temporary functions: for testing #################################

def on_subscriber_message(client, user_data, message):
    try:
        print 'ON SUBSCRIBER MESSAGE!!'
        print 'MESSAGE:', message.payload
        # client.disconnect()
        # print 'client:', client, client._username
        # client.reinitialise(client_id=user_data['id'], clean_session=False)
    except Exception as e:
        print "inside exception:", e
        raise e

def on_subscriber_connect(client, user_data, flags, rc):
    print "inside on_subscriber_connect"
    print "ON SUBSCRIBER CONNECT, CLIENT:", client
    print 'topic:', user_data.get('topic', '')
    (result, mid) = client.subscribe(topic=user_data.get('topic', ''), qos=1)

def subscribe_contacts_presence(client_id, user_data):
    print 'inside subscribe_contacts_presence'
    print 'client id:', client_id
    print 'userdata:', user_data
    client = Client(client_id=client_id, clean_session=False, userdata=user_data)
    client.on_connect = on_subscriber_connect
    client.on_message = on_subscriber_message

    try:
        client.username_pw_set(username=BROKER_USERNAME, password=BROKER_PASSWORD)
        client.connect_async(host=MOSQUITTO_IP, port=MOSQUITTO_PORT)
        client.loop_start()
        print 'SUBSCRIBER STARTED!'
    except Exception as e:
        print "inside Exception:", e

########################################################################################
