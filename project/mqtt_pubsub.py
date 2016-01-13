from paho.mqtt.client import Client


def on_publisher_connect(client, user_data, flags, rc):
    topic = user_data.get('topic', '')
    key=None
    if topic:
        key = topic.split('/')[-1]
    payload = user_data.get(key + '_notification', '')
    (result, mid) = client.publish(topic=topic, payload=payload, qos=1)
    if result == 0:
        print "MESSAGE PUBLISHED TO THE BROKER!!"
    else:
        print "MESSAGE NOT PUBLISHED!!!"


def on_publisher_message(client, user_data, mid):
    try:
        client.disconnect()
    except Exception as e:
        raise e

def mqtt_publish_client(user_data=None):
    client_id = "paho/" + str(publish_client_id)
    client = Client(client_id=client_id, clean_session=True, userdata=user_data)
    client.on_connect = on_publisher_connect
    client.on_publish = on_publisher_message

    try:
        client.username_pw_set(username='aakarshi', password='password')
        # test.mosquitto.org
        client.connect_async(host='localhost', port=1883)
        client.loop_start()
    except Exception as e:
        raise e




def on_subscriber_connect(client, user_data, flags, rc):
    (result, mid) = client.subscribe(topic='$SYS/' + user_data.get('topic', ''), qos=1)


def on_subscriber_message(client, user_data, message):
    print 'userdata:', user_data
    print 'message:', message, type(message)


def mqtt_subscribe_client(client_id, user_data=None):
    client = Client(client_id=client_id, clean_session=True, userdata=user_data)
    client.on_connect = on_subscriber_connect
    client.on_message = on_subscriber_message

    try:
        client.username_pw_set(username='aakarshi', password='password')
        # test.mosquitto.org
        client.connect_async(host='localhost', port=1883)
        client.loop_start()
    except Exception as e:
        print "inside Exception:", e
