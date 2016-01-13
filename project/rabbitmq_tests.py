import json
import os
import requests
import sys
from nose.tools import *

sys.path.append(os.path.dirname(os.path.abspath(__file__)).rsplit('/', 1)[0])

from project.app_settings import *
from project.rabbitmq_utils import *

# global variables
test_channel = None


def create_new_connection():
    global test_channel
    test_channel = get_rabbitmq_connection()


def close_connection():
    global test_channel
    test_channel.close()


@with_setup(setup=create_new_connection, teardown=close_connection)
def test_create_exchanges():
    global test_channel
    url = CREATE_EXCHANGES_URL
    response = requests.get(url)
    exchanges_response = requests.get(RABBITMQ_ALL_EXCHANGES_GET_URL, auth=(BROKER_USERNAME, BROKER_PASSWORD))
    exchanges_list = json.loads(exchanges_response.content)
    exchanges = [str(exchange.get('name')) for exchange in exchanges_list]

    assert_equal(response.status_code, STATUS_200)
    assert_equal(exchanges_response.status_code, STATUS_200)
    assert_not_equal(exchanges_list, [])
    for name in RABBITMQ_EXCHANGES:
        assert_in(name, exchanges)
