# -*- coding: utf-8; mode: python -*-
from swift.common.swob import Request, Response, wsgify
from swift.common.constraints import MAX_FILE_SIZE
from swift.common.http import is_success, HTTP_CREATED
from urllib import quote
import time

"""
-----
Large Single Uploads

* abstract
Middleware to upload a large object without splitting by client.

* setting

[pipeline:main]
pipeline = healthcheck cache tempauth large_single_uploads proxy-server

[filter:large_single_uploads]
use = egg:large_single_uploads#lsu
segments_container_suffix = _segments
max_object_size = 5368709122
split_chunk_size = 1073741824
-----

"""


class LargeSingleUploads(object):
    """
    """
    def __init__(self, app, conf):
        self.app = app
        self.seg_cont_suffix = str(conf.get('segments_container_suffix', \
                                                '_segments'))
        self.max_object_size = int(conf.get('max_object_size', MAX_FILE_SIZE))
        self.split_chunk_size = int(conf.get('split_chunk_size', 1073741824))

    @wsgify
    def __call__(self, req):
        """
        """
        if req.method != 'PUT':
            return self.app
        try:
            vrs, account, container, obj = req.split_path(1, 4, True)
        except ValueError:
            return self.app
        if req.headers.get('Transfer-Encoding') == 'chunked':
            return self.app
        if container.endswith(self.seg_cont_suffix):
            return self.app
        if req.content_length < self.max_object_size:
            return self.app
        resp = self.create_seg_cont(req)
        if is_success(resp.status_int):
            return self.split_object_upload(req)
        return resp

    def create_seg_cont(self, req):
        """
        """
        vrs, account, container, obj = req.split_path(1, 4, True)
        seg_cont_path = '/%s/%s/%s%s' % \
            (vrs, account, container, self.seg_cont_suffix)
        copied_env = req.environ.copy()
        copied_env['PATH_INFO'] = seg_cont_path
        req = Request.blank(seg_cont_path, environ=copied_env)
        return req.get_response(self.app)

    def split_object_upload(self, req):
        """
        """
        vrs, account, container, obj = req.split_path(1, 4, True)
        obj_size = req.content_length
        max_segments = obj_size / self.split_chunk_size + 1
        cur = str(time.time())
        seg_cont = '%s%s' % (container, self.seg_cont_suffix)
        env = req.environ.copy()
        body = req.body_file
        rest = obj_size
        for seg in range(max_segments):
            copied_env = env.copy()
            if rest >= self.split_chunk_size:
                chunk_size = self.split_chunk_size
            else:
                chunk_size = rest
            """
            <name>/<timestamp>/<size>/<segment>
            foo.dat/1321338039.34/79368/00000075
            """
            split_obj = quote('%s/%s/%s/%08d' % \
                                  (obj, cur, obj_size, seg))
            split_obj_path = '/%s/%s/%s/%s' % \
                (vrs, account, seg_cont, split_obj)
            copied_env['PATH_INFO'] = split_obj_path
            copied_env['CONTENT_LENGTH'] = chunk_size
            req = Request.blank(split_obj_path, environ=copied_env,
                                body=body.read(chunk_size))
            resp = req.get_response(self.app)
            if resp.status_int != HTTP_CREATED:
                return resp
            rest -= chunk_size
        mf_hdrs = {'x-object-manifest': '%s/%s/%s/%s/' % \
                       (seg_cont, obj, cur, obj_size),
                   'content-length': 0}
        mf_req = Request.blank(req.path, environ=env,
                               headers=mf_hdrs, body=None)
        mf_resp = mf_req.get_response(self.app)
        mf_resp.headers['x-large-single-upload'] = 'True; length=%s' % obj_size
        return mf_resp


def filter_factory(global_conf, **local_conf):
    """Returns a WSGI filter app for use with paste.deploy."""
    conf = global_conf.copy()
    conf.update(local_conf)

    def large_single_uploads_filter(app):
        return LargeSingleUploads(app, conf)
    return large_single_uploads_filter
