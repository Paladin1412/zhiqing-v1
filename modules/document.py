#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    : document.py
@Time    : 2020/5/14 14:25
@Author  : Qi
@Email   : 18821723039@163.com
@Software: PyCharm
"""
from flask import g

from main import mongo
from utils import response_code
from utils.setResJson import set_resjson


class DocumentHandler(object):
    def __init__(self, extra_data, model_action):
        self.extra_data = extra_data
        self.model_action = model_action

    def handle_model(self):
        func_name = 'func_{}'.format(self.model_action)
        func_name = func_name.lower()
        try:
            handle_function = getattr(DocumentHandler, func_name)
            resp = handle_function(self)
        except AttributeError as e:
            resp = set_resjson(err=-4,
                               errmsg="{} is incorrect !".format(
                                   self.model_action))
        return resp

    def func_view_file(self):
        """
        查看课件
        """
        video_id = self.extra_data.get('video_id')
        try:
            video_document = mongo.db.document.find_one({"video_id": video_id},
                                                        {"_id": 0,
                                                         "file_name": 1,
                                                         "file_path": 1,
                                                         "image_path": 1,
                                                         "price": 1,
                                                         "time": 1,
                                                         })
        except Exception as e:
            raise response_code.DatabaseERR(errmsg="{}".format(e))
        if not video_document:
            raise response_code.RoleERR(errmsg="这个视频没有课件")

        return set_resjson(res_array=[video_document])
