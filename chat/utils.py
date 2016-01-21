import random
import string
import thread
import time
from paho.mqtt.client import Client

from chat.media_publisher import *
from chat.message_publisher import *
from project.db_handler import *


def generate_random_client_id(len):
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(23-len))
