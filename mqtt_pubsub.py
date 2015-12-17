from paho.mqtt.client import Client
from app_settings import *


# class MQTTPublishClient(Client):
#
#     def __init__(self, userdata):
#         print "inside init of MQTTPublishClient"
#         self.client_id = "paho/" + str(publish_client_id)
#         self.user_data = userdata
#         self.on_connect = self.on_publisher_connect
#         self.topic = None
#         super(MQTTPublishClient, self).__init__(client_id=self.client_id, clean_session=False, userdata=self.user_data)
#
#     def connect_to_broker(self):
#         print "inside connect to broker"
#         self.username_pw_set(username='aakarshi', password='password')
#         self.connect_async(host='localhost', port=1883, keepalive=60, bind_address="")
#         self.loop_start()
#         print "publisher started"
#
#     def on_publisher_connect(self, client, userdata, flags, rc):
#         print "inside publisher connect"
#         print"self:", self
#         print "client:", client
#         print 'userdata:', userdata
#         print "flags:", flags
#         print 'rc:', rc
#         self.topic = self.user_data.get('topic', '')
#         payload = self.user_data.get(self.topic + '_notification', '')
#         self.publish(topic=self.topic, payload=payload, qos=1)
#         print "MESSAGE PUBLISHED TO THE BROKER!!"

def on_publisher_connect(client, user_data, flags, rc):
    print "inside on_publisher_connect"
    topic = user_data.get('topic', '')
    key=None
    if topic:
        key = topic.split('/')[-1]
    payload = user_data.get(key + '_notification', '')
    print 'topic 1:', topic
    print 'payload 1:', payload, type(payload)
    (result, mid) = client.publish(topic=topic, payload=payload, qos=1)
    if result == 0:
        print "MESSAGE PUBLISHED TO THE BROKER!!"
    else:
        print "MESSAGE NOT PUBLISHED!!!"


def on_publisher_message(client, user_data, mid):
    print "inside on_publisher_message"
    print 'STOPPING THE PUBLISHER!!'
    try:
        client.disconnect()
    except Exception as e:
        print "inside exception:", e

def mqtt_publish_client(user_data=None):
    print 'inside mqtt subscribe client'
    client_id = "paho/" + str(publish_client_id)
    client = Client(client_id=client_id, clean_session=True, userdata=user_data)
    client.on_connect = on_publisher_connect
    client.on_publish = on_publisher_message

    try:
        client.username_pw_set(username='aakarshi', password='password')
        print 'after user pw set'
        # test.mosquitto.org
        client.connect_async(host='localhost', port=1883)
        client.loop_start()
        print 'publisher started'
    except Exception as e:
        print "inside Exception:", e





def on_subscriber_connect(client, user_data, flags, rc):
    print "inside on_subscriber_connect"
    (result, mid) = client.subscribe(topic='$SYS/' + user_data.get('topic', ''), qos=1)
    print 'result:', result
    print 'mid:', mid


def on_subscriber_message(client, user_data, message):
    print "inside on_message!!!!!!!!!!!!!!!!!!!!!YAYYYYYYYYYYYYYYYYEEEEEEEEEEEEEEEEEEEEEEE!!"
    print "client:", client
    print 'userdata:', user_data
    print 'message:', message, type(message)


def mqtt_subscribe_client(client_id, user_data=None):
    print 'inside mqtt subscribe client'
    client = Client(client_id=client_id, clean_session=True, userdata=user_data)
    client.on_connect = on_subscriber_connect
    client.on_message = on_subscriber_message

    try:
        client.username_pw_set(username='aakarshi', password='password')
        print 'after user pw set'
        # test.mosquitto.org
        client.connect_async(host='localhost', port=1883)
        client.loop_start()
        print 'after loop start'
    except Exception as e:
        print "inside Exception:", e



    # class MQTTSubscribeClient():

    # d
    # def __init__(self, client_id, user_data):
    #     print "inside init of MQTTSubscribeClient"
    #     self.client_id = "paho/" + str(client_id)
    #     print "client id:", self.client_id
    #     self.user_data = user_data
    #     self.on_connect = self.on_subscriber_connect
    #     print 'on connect:', self.on_connect
    #     self.client = super(MQTTSubscribeClient, self).__init__(client_id=self.client_id, clean_session=False, userdata=self.user_data)
    #
    #     print 'on connnect 3:', self.on_connect
    #     self.on_connect = self.on_subscriber_connect
    #     self._host = 'test.mosquitto.org'
    #     self.on_message = self.on_message
    #     self.topic = None
    #     print "hello"
    #     print "hello 2"

    # def connect_to_broker(self):
    #     print "inside connect to broker of MQTTSubscribeClient"
    #     try:
    #         self.username_pw_set(username='aakarshi', password='password')
    #         print 'after user pw set'
    #         # test.mosquitto.org
    #         self.connect_async(host='localhost', port=1883)
    #         self.loop_start()
    #         print 'after loop start'
    #     except Exception as e:
    #         print "inside Exception:", e
    #
    # def on_subscriber_connect(self, client, userdata, flags, rc):
    #     print "inside on_subscriber_connect"
    #     (result, mid) = self.subscribe(topic=self.user_data.get('topic', ''), qos=1)
    #     print 'result:', result
    #     print 'mid:', mid
    #
    # def on_message(self, client, userdata, message):
    #     print "inside on_message()"
    #     print "client:", client
    #     print 'userdata:', userdata
    #     print 'message:', message, type(message)
