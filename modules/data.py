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
        subscription_counts = mongo.db.subcription.find({"relation_id": user["_id"], "state": 0}).count()
        video_cursor = mongo.db.video.find({"user_id": user["_id"]})
        for video in video_cursor:
            view_counts += video["view_counts"]
            if "share_counts" in video.keys():
                share_counts += video.pop("download_counts")
            document_cursor = mongo.db.document.find({"video_id": video["_id"]})
            for document in document_cursor:
                if "download_counts" in document.keys():
                    download_counts += document.pop("download_counts")
            like_counts += mongo.db.like.find({"relation_id": video["_id"]}).count()
            collections_counts += mongo.db.collection.find({"relation_id": video["_id"]}).count()
            comment_counts += mongo.db.comment.find({"video_id": video["_id"]}).count()
        res_dict = {"subscription_counts": subscription_counts,
                    "view_counts": view_counts,
                    "share_counts": subscription_counts,
                    "download_counts": download_counts,
                    "collections_counts": collections_counts,
                    "comment_counts": comment_counts}

        return set_resjson(res_array=[res_dict])


