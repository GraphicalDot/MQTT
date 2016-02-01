import json
import os
import requests
import sys
import time
import unittest
from nose.tools import *

sys.path.append(os.path.dirname(os.path.abspath(__file__)).rsplit('/', 1)[0])
from games_notifications import errors, notification_subscriber as sub, notification_publisher as pub
from project import app_settings, rabbitmq_utils
from project import test_utilities



class StartNotificationSubscribersTests(unittest.TestCase):
    url = None

    def setUp(self):
        self.url = app_settings.START_NOTIFICATION_SUBSCRIBERS_URL
        rabbitmq_utils.delete_exchanges(app_settings.RABBITMQ_EXCHANGES)
        rabbitmq_utils.delete_queues()

    def test_get(self):
        response = requests.get(self.url)
        res = json.loads(response.content)
        assert_equal(res['info'], app_settings.SUCCESS_RESPONSE)
        assert_equal(res['status'], app_settings.STATUS_200)


class SportsNotificationsTests(unittest.TestCase):
    url = None
    event = None
    data = None

    def setUp(self):
        self.url = app_settings.SPORT_NOTIFICATIONS_URL
        rabbitmq_utils.delete_exchanges(app_settings.RABBITMQ_EXCHANGES)
        rabbitmq_utils.delete_queues()

    def test_validations(self):

        # No event provided
        self.data = {'data': {"teams": "Aus Vs India", "status": "Aus won by 59 runs", "overs": "45.3"}}
        response = requests.post(self.url, data=json.dumps(self.data))
        res = json.loads(response.content)
        assert_equal(res['info'], errors.INVALID_EVENT_ERR)
        assert_equal(res['status'], app_settings.STATUS_404)

        # Invalid event provided
        self.data = {"teams": "Aus Vs India", "status": "Aus won by 59 runs", "overs": "45.3", 'event': 'Basketball'}
        response = requests.post(self.url, data=json.dumps(self.data))
        res = json.loads(response.content)
        assert_equal(res['info'], errors.INVALID_EVENT_ERR)
        assert_equal(res['status'], app_settings.STATUS_404)

        # data not provided
        self.data = {'event': 'cricket'}
        response = requests.post(self.url, data=json.dumps(self.data))
        res = json.loads(response.content)
        assert_equal(res['info'], errors.INVALID_DATA_ERR)
        assert_equal(res['status'], app_settings.STATUS_404)

    def test_post(self):

        # start the subscriber for cricket notifications
        client_id = test_utilities.generate_random_id()
        user_data = {'topic': 'notifications.cricket.*'}
        sub.notification_subscriber(client_id, user_data)

        time.sleep(10)
        self.data = {'event': 'cricket', 'data': {"teams": "Aus Vs India", "status": "Aus won by 59 runs",
                    "runs": "246", "wickets": "10", "time": "1441367561.578593", "overs": "45.3",
                    42.2: "Starc to Mark Wood, 1 run, short delivery on the leg stump, " \
                          "Wood goes for the pull, mistimes it and it rolls to deep mid-wicket " \
                          "(Score after 42.2 Ov - 234)"}}
        response = requests.post(self.url, data=json.dumps(self.data))
        res = json.loads(response.content)
        assert_equal(res['info'], app_settings.SUCCESS_RESPONSE)
        assert_equal(res['status'], app_settings.STATUS_200)

        time.sleep(10)
