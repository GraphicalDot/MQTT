import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)).rsplit('/', 1)[0])

from project import app_settings


def connect_to_server(client):
    client.username_pw_set(username=app_settings.BROKER_USERNAME, password=app_settings.BROKER_PASSWORD)
    client.connect_async(host='localhost', port=1883)
    client.loop_start()
