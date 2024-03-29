PUBLISH_CLIENT_ID = 'sportsunity@mm'

########## DATABASE ########
LOCAL_DB_HOST = 'localhost'
LOCAL_DB_NAME = 'test'
LOCAL_DB_USER = 'test'
LOCAL_DB_PSWD = 'test'


########### TORNADO ###########
TORNADO_HOSTNAME = 'localhost'
TORNADO_PORT = 3000





########## RABBITMQ ###########
# Server details
RABBITMQ_HOSTNAME = 'localhost'
RABBITMQ_PORT = 15672

# Auth details
BROKER_USERNAME = 'guest'
BROKER_PASSWORD = 'guest'

# Rabbitmq exchanges
GROUP_CHAT_MESSAGES_EXCHANGE = 'group_chat_messages'
CHAT_PRESENCE_EXCHANGE = 'chat_user_presence'
SIMPLE_CHAT_MESSAGES_EXCHANGE = 'simple_chat_messages'
SIMPLE_CHAT_MESSAGE_RECEIVED_EXCHANGE = 'simple_chat_messages_received'

SIMPLE_CHAT_MEDIA_EXCHANGE = 'simple_chat_media'
SIMPLE_CHAT_SINGLE_TICK_EXCHANGE = 'simple_chat_single_tick'
SIMPLE_CHAT_DOUBLE_TICK_EXCHANGE = 'simple_chat_double_tick'
SIMPLE_CHAT_COLORED_DOUBLE_TICK_EXCHANGE = 'simple_chat_colored_double_tick'

NOTIFICATIONS_EXCHANGE = 'sport_notifications'

RABBITMQ_EXCHANGES = [
    CHAT_PRESENCE_EXCHANGE,
    SIMPLE_CHAT_MESSAGES_EXCHANGE,
    SIMPLE_CHAT_MEDIA_EXCHANGE,
    SIMPLE_CHAT_MESSAGE_RECEIVED_EXCHANGE,
    SIMPLE_CHAT_SINGLE_TICK_EXCHANGE,
    SIMPLE_CHAT_DOUBLE_TICK_EXCHANGE,
    SIMPLE_CHAT_COLORED_DOUBLE_TICK_EXCHANGE,
    GROUP_CHAT_MESSAGES_EXCHANGE,

    # NOTIFICATIONS_EXCHANGE,
]


##############

EXPIRY_PERIOD_SEC=1800

REGISTRATION_MESSAGE='Welcome to Sports Unity App. Your authorization code is '
GUPSHUP_ID=2000147230
GUPSHUP_PASSWORD='6u71LGpxDq'
GUPSHUP_MESSAGE_GATEWAY='http://enterprise.smsgupshup.com/GatewayAPI/rest'


##### Constants ######
STATUS_404 = 404
STATUS_400 = 400
STATUS_500 = 500
STATUS_200 = 200
SUCCESS_RESPONSE = "Success"

ERROR_CODES_LIST = [
    STATUS_400,
    STATUS_404,
    STATUS_500
]

GROUP_MESSAGES_FILE_PATH = 'project/group_msg_config.py'

###### Testing Constants ########
TESTING_VALID_CONTACT = '919999823930'
TESTING_INVALID_CONTACT = '910000000000'

CREATE_EXCHANGES_URL = 'http://{}:{}/'.format(TORNADO_HOSTNAME, TORNADO_PORT)
REGISTER_URL = 'http://{}:{}/register'.format(TORNADO_HOSTNAME, TORNADO_PORT)
USER_CREATION_URL = 'http://{}:{}/create'.format(TORNADO_HOSTNAME, TORNADO_PORT)
SAVE_CONTACTS_URL = 'http://{}:{}/save_contacts'.format(TORNADO_HOSTNAME, TORNADO_PORT)
START_STOP_APP_URL = 'http://{}:{}/start_stop_app'.format(TORNADO_HOSTNAME, TORNADO_PORT)

SIMPLE_CHAT_SEND_MESSAGE_URL = 'http://{}:{}/simple_send_message'.format(TORNADO_HOSTNAME, TORNADO_PORT)
SIMPLE_CHAT_SEND_MEDIA_URL = 'http://{}:{}/simple_send_media'.format(TORNADO_HOSTNAME, TORNADO_PORT)
START_NOTIFICATION_SUBSCRIBERS_URL = 'http://{}:{}/start_notification_subscribers'.format(TORNADO_HOSTNAME, TORNADO_PORT)

SPORT_NOTIFICATIONS_URL = 'http://{}:{}/sport_notifications'.format(TORNADO_HOSTNAME, TORNADO_PORT)

CREATE_GROUP_URL = 'http://{}:{}/create_group'.format(TORNADO_HOSTNAME, TORNADO_PORT)
SEND_MESSAGE_TO_GROUP_URL = 'http://{}:{}/group_send_message'.format(TORNADO_HOSTNAME, TORNADO_PORT)
GET_GROUPS_INFO_URL = 'http://{}:{}/get_groups'.format(TORNADO_HOSTNAME, TORNADO_PORT)
ADD_CONTACT_TO_GROUP_URL = 'http://{}:{}/add_contact_to_group'.format(TORNADO_HOSTNAME, TORNADO_PORT)
REMOVE_CONTACT_FROM_GROUP_URL = 'http://{}:{}/remove_contact_from_group'.format(TORNADO_HOSTNAME, TORNADO_PORT)
ADD_ADMIN_TO_GROUP_URL = 'http://{}:{}/add_admin'.format(TORNADO_HOSTNAME, TORNADO_PORT)
REMOVE_ADMIN_FROM_GROUP_URL = 'http://{}:{}/remove_admin'.format(TORNADO_HOSTNAME, TORNADO_PORT)

RABBITMQ_ALL_EXCHANGES_GET_URL = 'http://{}:{}/api/exchanges/'.format(RABBITMQ_HOSTNAME, RABBITMQ_PORT)
RABBITMQ_GET_ALL_QUEUES_URL = 'http://{}:{}/api/queues/'.format(RABBITMQ_HOSTNAME, RABBITMQ_PORT)
RABBITMQ_ALL_BINDINGS_GET_URL = 'http://{}:{}/api/bindings'.format(RABBITMQ_HOSTNAME, RABBITMQ_PORT)
