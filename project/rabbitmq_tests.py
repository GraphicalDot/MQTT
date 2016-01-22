import json
import os
import requests
import sys
from nose.tools import *

sys.path.append(os.path.dirname(os.path.abspath(__file__)).rsplit('/', 1)[0])
from project import app_settings, rabbitmq_utils

# global variables
test_channel = None


def create_new_connection():
    global test_channel
    test_channel = rabbitmq_utils.get_rabbitmq_connection()


def close_connection():
    global test_channel
    test_channel.close()


@with_setup(setup=create_new_connection, teardown=close_connection)
def test_create_exchanges():
    global test_channel
    url = app_settings.CREATE_EXCHANGES_URL
    response = requests.get(url)
    exchanges_response = requests.get(app_settings.RABBITMQ_ALL_EXCHANGES_GET_URL,
                                      auth=(app_settings.BROKER_USERNAME, app_settings.BROKER_PASSWORD))
    exchanges_list = json.loads(exchanges_response.content)
    exchanges = [str(exchange.get('name')) for exchange in exchanges_list]

    assert_equal(response.status_code, app_settings.STATUS_200)
    assert_equal(exchanges_response.status_code, app_settings.STATUS_200)
    assert_not_equal(exchanges_list, [])
    for name in app_settings.RABBITMQ_EXCHANGES:
        assert_in(name, exchanges)
