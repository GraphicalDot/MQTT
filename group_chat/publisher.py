from paho.mqtt.client import Client
from db_handler import *


def on_publisher_connect(client, user_data, flags, rc):
    print "ON PUBLISHER CONNECT"
    print 'USERDATA:', user_data['id'], user_data['message']
    try:
        client.publish(topic=user_data['topic'], payload=user_data['message'], qos=1, retain=True)
        print 'PUBLISHED!!!!!!!!!!!!!!!!!!!!!!!'
    except Exception as e:
        print 'INSIDE EXCEPTION!!!!!!!:', e
        raise e


def on_publisher_message(client, user_data, mid):
    print "ON PUBLISHER MESSAGE"
    try:
        # add message to database
        query = " INSERT INTO group_messages(group_owner, group_name, sender, message) VALUES (%s, %s, %s, %s);"
        variables = (user_data.get('group_owner'), user_data.get('group_name'), user_data.get('sender'),
                     user_data.get('message'))
        LocalQueryHandler.execute(query, variables)
        print "MESSAGE SENT TO THE BROKER!"

        # stop the publishing thread
        client.loop_stop()
        client.reinitialise(client_id=user_data['id'], clean_session=False)
    except Exception as e:
        print "inside exception"
        raise e


def group_chat_publisher(client_id, user_data):
    print 'INSIDE PUBLISHER!'
    print 'client id:', client_id, type(client_id)
    print 'userdata:', user_data
    user_data['id'] = str(client_id)
    client = Client(client_id=client_id, clean_session=False, userdata=user_data)
    client.on_connect = on_publisher_connect
    client.on_publish = on_publisher_message
    try:
        client.username_pw_set(username=BROKER_USERNAME, password=BROKER_PASSWORD)
        client.connect_async(host='localhost', port=1883)
        client.loop_start()
        print 'publisher started'
    except Exception as e:
        print "inside Exception:", e
        raise e
