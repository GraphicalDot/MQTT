import json
import os
import pika
import requests
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)).rsplit('/', 1)[0])
from project import app_settings

connection = None
channel = None

def get_rabbitmq_connection():
    global connection
    global channel
    try:
        if not connection:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
            channel = connection.channel()
    except Exception as e:
        return e
    return channel


def delete_exchanges(exchanges_list):
    try:
        channel = get_rabbitmq_connection()
        for exchange in exchanges_list:
            channel.exchange_delete(exchange)

        rabbitmq_api_response = requests.get('http://{}:{}/api/queues'.format(app_settings.RABBITMQ_HOSTNAME, app_settings.RABBITMQ_PORT),
                                             auth=(app_settings.BROKER_USERNAME, app_settings.BROKER_PASSWORD))
        res = json.loads(rabbitmq_api_response.content)
    except Exception as e:
        raise e

def delete_queues():
    try:
        channel = get_rabbitmq_connection()
        rabbitmq_api_response = requests.get('http://{}:{}/api/queues'.format(app_settings.RABBITMQ_HOSTNAME, app_settings.RABBITMQ_PORT),
                                                 auth=(app_settings.BROKER_USERNAME, app_settings.BROKER_PASSWORD))
        res = json.loads(rabbitmq_api_response.content)
        for queue in res:
            channel.queue_delete(queue=queue['name'])
    except Exception as e:
        raise e


def create_bind_queue(exchange, routing_key):
    try:
        channel = get_rabbitmq_connection()
        result = channel.queue_declare()
        channel.queue_bind(exchange=exchange, queue=result.method.queue, routing_key=routing_key)
    except Exception as e:
        raise e
