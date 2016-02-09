import os
import sys
import tornado
import tornado.ioloop
import tornado.web
from tornado.log import enable_pretty_logging
from tornado.options import options

sys.path.append(os.path.dirname(os.path.abspath(__file__)).rsplit('/', 1)[0])

from chat import simple_chat
from games_notifications import notifications
from group_chat import group_chat
from registration import register
from registration import presence_notification


def make_app():
    return tornado.web.Application([
        (r"/", group_chat.CreateExchanges),

        # Registeration URLs
        (r"/register", register.RegisterUser),
        (r"/create", register.CreateUser),
        (r"/save_contacts", register.SaveContacts),
        (r"/start_stop_app", presence_notification.StartStopApp),

        # Normal Chat URLs
        (r"/simple_send_message", simple_chat.SendMessageToContact),
        (r"/simple_send_media", simple_chat.SendMediaToContact),
        (r"/media_multipart", simple_chat.IOSMediaHandler),

        # Group Chat URLs
        (r"/create_group", group_chat.CreateGroup),
        (r"/group_send_message", group_chat.SendMessageToGroup),
        (r"/get_groups", group_chat.GetGroupsInfo),
        (r"/add_contact_to_group", group_chat.AddContactToGroup),
        (r"/remove_contact_from_group", group_chat.RemoveContactFromGroup),
        (r"/add_admin", group_chat.AddAdminToGroup),
        (r"/remove_admin", group_chat.RemoveAdminFromGroup),

        # Games Notifications
        (r"/start_notification_subscribers",notifications.StartNotificationSubscribers),
        (r"/sport_notifications", notifications.SportsNotifications),
    ],
        autoreload=True,
    )


if __name__ == "__main__":
    app = make_app()
    options.log_file_prefix = "tornado_log"
    enable_pretty_logging(options=options)

    app.listen(3000)
    tornado.ioloop.IOLoop.current().start()
