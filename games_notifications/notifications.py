import json
import os
import sys
import tornado
import tornado.ioloop
import tornado.web

sys.path.append(os.path.dirname(os.path.abspath(__file__)).rsplit('/', 1)[0])

import errors
import notification_publisher as pub
import notification_subscriber as sub
from project import app_settings
from chat import utils


class StartNotificationSubscribers(tornado.web.RequestHandler):

    def get(self):
        response = {}

        try:
            # initiate cricket subscriber
            client_id = "cricket_sub/" + utils.generate_random_client_id(12)
            user_data = {'topic': 'notifications.cricket.*'}
            sub.notification_subscriber(client_id, user_data)

            # # initiate football subscriber
            # client_id = "football_sub/" + utils.generate_random_client_id(13)
            # user_data = {'topic': 'notifications.football.*'}
            # sub.notification_subscriber(client_id, user_data)
            #
            # # initiate tennis subscriber
            # client_id = "tennis_sub/" + utils.generate_random_client_id(11)
            # user_data = {'topic': 'notifications.tennis.*'}
            # sub.notification_subscriber(client_id, user_data)

            response['info'] = app_settings.SUCCESS_RESPONSE
            response['status'] = app_settings.STATUS_200
        except Exception as e:
            response['info'] = "Error: %s" % e
            response['status'] = app_settings.STATUS_500
        finally:
            self.write(response)


class SportsNotifications(tornado.web.RequestHandler):

    def data_validation(self, event, data):
        response = {'info': '', 'status': 0}
        try:
            if event == '' or event not in ['cricket', 'football', 'tennis']:
                response['info'] = errors.INVALID_EVENT_ERR
                response['status'] = app_settings.STATUS_404

            if response['status'] == 0 and not data:
                response['info'] = errors.INVALID_DATA_ERR
                response['status'] = app_settings.STATUS_404
        except Exception as e:
            response['info'] = " Error: %s" % e
            response['status'] = app_settings.STATUS_500
        finally:
            return (response['info'], response['status'])

    def post(self):
        response = {}
        try:
            body = json.loads(self.request.body)
            event = str(body.get('event', ''))
            data = body.get('data', None)

            response['info'], response['status'] = self.data_validation(event, data)
            if response['status'] not in app_settings.ERROR_CODES_LIST:
                client_id = event + "_pub/" + utils.generate_random_client_id(len(event + "_pub/"))
                user_data = {'topic': 'notifications.' + event, 'message': data}
                pub.notification_publisher(client_id, user_data)

                response['info'] = app_settings.SUCCESS_RESPONSE
                response['status'] = app_settings.STATUS_200
        except Exception as e:
            response['info'] = "Error: %s" % e
            response['status'] = app_settings.STATUS_500
        finally:
            self.write(response)
