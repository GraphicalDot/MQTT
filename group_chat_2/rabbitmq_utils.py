import pika
import sys


def get_rabbitmq_connection():
    connection = pika.BlockingConnection(pika.ConnectionParameters(
        host='localhost'))
    return connection
