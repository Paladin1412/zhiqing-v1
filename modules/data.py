#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    : data.py
@Time    : 2020/5/20 15:22
@Author  : Qi
@Email   : 18821723039@163.com
@Software: PyCharm
"""

from flask import g

from main import mongo
from utils import response_code
from utils.setResJson import set_resjson


class DataHandler(object):
    """
    数据中心
    """

    def __init__(self, extra_data, model_action):
        self.extra_data = extra_data
        self.model_action = model_action

    def handle_model(self):
        func_name = 'func_{}'.format(self.model_action)
        func_name = func_name.lower()
        try:
            handle_function = getattr(DataHandler, func_name)
            if self.model_action not in ["get_data"]:
                if self.extra_data == '':
                    raise response_code.ParamERR(
                        errmsg="[ extra_data ] must be provided ")
            resp = handle_function(self)
        except AttributeError as e:
            resp = set_resjson(err=-4,
                               errmsg="{} is incorrect !".format(
                                   self.model_action))
        return resp

    def func_get_data(self):
        """
        获取数据
        """
        user = g.user
        if not user:
            raise response_code.UserERR(errmsg='用户未登录')
        view_counts = 0
        download_counts = 0
        like_counts = 0
        collections_counts = 0
        share_counts = 0
        comment_counts = 0
        subscription_counts = mongo.db.subcription.find({"relation_id": user["_id"]}).count()
        video_cursor = mongo.db.video.find({"user_id": user["_id"]})
        for video in video_cursor:
            pass

