import base64
import json
import os
import requests
import unittest

from tornado.testing import AsyncHTTPTestCase

from project import urls


# class MediaTest(AsyncHTTPTestCase):
#     url = None
#
#     def setUp(self):
#         print "inside setUp of MediaTest"
#         self.url = "http://localhost:3000/simple_send_media"
#         self.media_files = {
#             'image': 'test_image.jpg',
#             'pdf': 'test_pdf.pdf',
#             'audio': 'test_audio.mp3',
#             'video': 'test_video.mp4',
#             'rar': 'test_rar.rar',
#         }
#
#     def tearDown(self):
#         pass
#
#     def make_post_request(self, file_name):
#         print "inside make post request"
#         file_content = open(file_name, 'r').read()
#         content = {'sender': 'zb', 'receiver': 'za', 'name': str(file_name), 'body': base64.b64encode(file_content)}
#         response = requests.post(self.url, data=json.dumps(content))
#         print response
#         return response
#
#     def test_upload_image(self):
#         print "inside test upload image"
#         file_name = self.media_files['image']
#         response = self.make_post_request(file_name)
#         assert json.loads(response.content)['status'] == 200
#         assert os.path.isfile('media/{}'.format(file_name))
#
#     def test_upload_pdf(self):
#         print "inside test upload pdf"
#         file_name = self.media_files['pdf']
#         response = self.make_post_request(file_name)
#         assert json.loads(response.content)['status'] == 200
#         assert os.path.isfile('media/{}'.format(file_name))
#
#     def test_upload_audio(self):
#         print "inside test upload audio"
#         file_name = self.media_files['audio']
#         response = self.make_post_request(file_name)
#         assert json.loads(response.content)['status'] == 200
#         assert os.path.isfile('media/{}'.format(file_name))
#
#     def test_upload_video(self):
#         print "inside test upload video"
#         file_name = self.media_files['video']
#         response = self.make_post_request(file_name)
#         assert json.loads(response.content)['status'] == 200
#         assert os.path.isfile('media/{}'.format(file_name))
#
#     def test_upload_rar(self):
#         print "inside test upload rar"
#         file_name = self.media_files['rar']
#         response = self.make_post_request(file_name)
#         assert json.loads(response.content)['status'] == 200
#         assert os.path.isfile('media/{}'.format(file_name))
#
#     def get_app(self):
#         return urls.make_app()
#
# if __name__ == '__main__':
#     unittest.main()
