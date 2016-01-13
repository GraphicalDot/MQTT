import os
import sys
import tornado
import tornado.ioloop
import tornado.web
from tornado.log import enable_pretty_logging
from tornado.options import options

sys.path.append(os.path.dirname(os.path.abspath(__file__)).rsplit('/', 1)[0])

from chat.simple_chat import *
from registration.register import *
from group_chat.group_chat import *
from registration.presence_notification import *


def make_app():
    return tornado.web.Application([
        (r"/", CreateExchanges),

        # Registeration URLs
        (r"/register", RegisterUser),
        (r"/create", CreateUser),
        (r"/save_contacts", SaveContacts),
        (r"/start_stop_app", StartStopApp),

        # Normal Chat URLs
        (r"/simple_send_message", SendMessageToContact),
        (r"/simple_send_media", SendMediaToContact),

        # Group Chat URLs
        (r"/create_group", CreateGroup),
        (r"/group_send_message", SendMessageToGroup),
        (r"/get_groups", GetGroupsInfo),
    ],
        autoreload=True,
    )


if __name__ == "__main__":
    app = make_app()
    options.log_file_prefix = "tornado_log"
    enable_pretty_logging(options=options)

    app.listen(3000)
    tornado.ioloop.IOLoop.current().start()
