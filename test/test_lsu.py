import unittest
from StringIO import StringIO
import re
from mock import patch
from swift.common.swob import Request, Response
from large_single_uploads import lsu

class FakeApp(object):
    def __init__(self):
        self.resps = []

    def __call__(self, env, start_response):
        self.resps.append(env)
        return Response(status=201)(env, start_response)

TEST_DATA = '1234567890ABCDEFGHIJabcdefghij@@@@@@'

class TestLargeSingleUploads(unittest.TestCase):

    def setUp(self):
        self.app = FakeApp()
        self.conf = {'segments_container_suffix': '_segments',
                     'max_object_size': 29,
                     'split_chunk_size': 10}
        self.lsu = lsu.filter_factory(conf)(self.app)

    def tearDown(self):
        pass

    def test_create_seg_cont(self):
        req = Request.blank('/v/a/c/o')
        req.method = 'PUT'
        req.environ['wsgi.input'] = StringIO(TEST_DATA)
        req.headers['content-length'] = len(TEST_DATA)
        resp = self.lsu.create_seg_cont(req)
        resp_env = self.app.resps[0]
        del self.app.resps[0]
        self.assertEquals(resp_env['PATH_INFO'], '/v/a/c_segments')

    def test_split_object_upload(self):
        req = Request.blank('/v/a/c/o')
        req.method = 'PUT'
        req.environ['wsgi.input'] = StringIO(TEST_DATA)
        req.headers['content-length'] = len(TEST_DATA)
        resp = self.lsu.split_object_upload(req)
        for i, e in zip(range(5), self.app.resps):
            if i == 0:
                self.assertTrue(re.match('/v/a/c_segments/o/\d+\.\d+/36/00000000', e['PATH_INFO']) \
                                    and e['wsgi.input'].getvalue() == '1234567890')
            elif i == 1:
                self.assertTrue(re.match('/v/a/c_segments/o/\d+\.\d+/36/00000001', e['PATH_INFO']) \
                                    and e['wsgi.input'].getvalue() == 'ABCDEFGHIJ')
            elif i == 2:
                self.assertTrue(re.match('/v/a/c_segments/o/\d+\.\d+/36/00000002', e['PATH_INFO']) \
                                    and e['wsgi.input'].getvalue() == 'abcdefghij')
            elif i == 3:
                self.assertTrue(re.match('/v/a/c_segments/o/\d+\.\d+/36/00000003', e['PATH_INFO']) \
                                    and e['wsgi.input'].getvalue() == '@@@@@@')
            elif i == 4:
                self.assertTrue(e['PATH_INFO'] == '/v/a/c/o' and \
                                    re.match('c_segments/o/\d+\.\d+/36/', e['HTTP_X_OBJECT_MANIFEST']))
            else:
                self.fail()

if __name__ == '__main__':
    unittest.main()
