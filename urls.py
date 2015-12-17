import tornado
import tornado.ioloop
import tornado.web
from tornado.log import enable_pretty_logging
from tornado.options import options

from registration.register import *





def make_app():
    return tornado.web.Application([
        (r"/register", RegisterUser),
        (r'/create', CreateUser),
    ],
        autoreload=True,
    )


if __name__ == "__main__":
    app = make_app()
    options.log_file_prefix = "tornado_log"
    enable_pretty_logging(options=options)
    app.listen(3000)
    tornado.ioloop.IOLoop.current().start()
