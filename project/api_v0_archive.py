import json
from tornado.log import enable_pretty_logging
from tornado.options import options
import tornado
import tornado.ioloop
import tornado.web
import tornado.escape
import requests
import os
import ConfigParser

# from mqtt_pubsub import MQTTPublishClient, MQTTSubscribeClient
from mqtt_pubsub import mqtt_subscribe_client, mqtt_publish_client

_test_cricket_data = {
    "teams": "Aus Vs India",
    "status": "Aus won by 59 runs",
    "runs": "246",
    "wickets": "10",
    "time": "1441367561.578593",
    "overs": "45.3",
    42.2: "Starc to Mark Wood, 1 run, short delivery on the leg stump, Wood goes for the pull, mistimes it and it rolls to deep mid-wicket (Score after 42.2 Ov - 234)"
}


class StartSubscriber(tornado.web.RequestHandler):

    def get(self, *args, **kwargs):
        user_data = {'topic': '$SYS/sportsunity/notifications/cricket'}
        mqtt_subscribe_client(client_id='subscriber1', user_data=user_data)
        # MQTTSubscribeClient(client_id='subscriber1', user_data=user_data).connect_to_broker()


class CricketEvents(tornado.web.RequestHandler):
    def get(self):
        # event = tornado.escape.json_decode(self.request.body)
        event = self.get_argument('data')
        cricket_data = json.dumps(self.get_argument('data'))
        # cricket_data = json.dumps(_test_cricket_data)
        if event:
            user_data = {'topic': '$SYS/sportsunity/notifications/cricket', 'cricket_notification': cricket_data}
            mqtt_publish_client(user_data)
            # MQTTPublishClient(user_data).connect_to_broker()


def make_app():
    return tornado.web.Application([
        (r"/start_subscriber", StartSubscriber),
        (r"/cricket_notifications", CricketEvents),
        ],
        autoreload=True,
    )


if __name__ == "__main__":
    app = make_app()
    enable_pretty_logging(options=options)
    app.listen(3000)
    tornado.ioloop.IOLoop.current().start()



