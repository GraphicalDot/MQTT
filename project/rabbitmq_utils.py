import json
import pika
import sys
import requests

from project.app_settings import *

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

        rabbitmq_api_response = requests.get('http://{}:{}/api/queues'.format(RABBITMQ_HOSTNAME, RABBITMQ_PORT),
                                             auth=(BROKER_USERNAME, BROKER_PASSWORD))
        res = json.loads(rabbitmq_api_response.content)
    except Exception as e:
        raise e

def delete_queues():
    try:
        channel = get_rabbitmq_connection()
        rabbitmq_api_response = requests.get('http://{}:{}/api/queues'.format(RABBITMQ_HOSTNAME, RABBITMQ_PORT),
                                                 auth=(BROKER_USERNAME, BROKER_PASSWORD))
        res = json.loads(rabbitmq_api_response.content)
        for queue in res:
            channel.queue_delete(queue=queue['name'])
    except Exception as e:
        raise e
