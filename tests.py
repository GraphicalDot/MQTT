import base64
import json
import os
import unittest
import requests
import sys
import urls
from tornado.testing import AsyncHTTPTestCase


class MediaTest(AsyncHTTPTestCase):

    def test_upload_and_download(self):
        print "inside test upload and download"
        self.url = "http://localhost:3000/simple_send_media"
        file_name = 'image1.jpg'
        file_content = open(file_name, 'r').read()
        content = {'name': str(file_name), 'body': base64.b64encode(file_content)}
        response = requests.post(self.url, data=json.dumps(content))
        print response.content
        assert json.loads(response.content)['status'] == 200
        assert os.path.isfile('media/{}'.format(file_name))

    def get_app(self):
        return urls.make_app()

if __name__ == '__main__':
    unittest.main()
