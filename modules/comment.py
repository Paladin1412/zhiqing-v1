#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    : comment.py
@Time    : 2020/5/3 09:29
@Author  : Qi
@Email   : 18821723039@163.com
@Software: PyCharm
"""
import os

from flask import g

from main import mongo
from utils import response_code
from utils.mongo_id import create_uuid
from utils.setResJson import set_resjson


class CommentHandler(object):
    def __init__(self, extra_data, model_action):
        self.temporary_path = os.path.abspath(
            os.path.dirname(os.path.dirname(__file__)))
        abs_path = os.path.dirname(self.temporary_path)
        self.path = abs_path + '/static'
        self.extra_data = extra_data
        self.model_action = model_action

    def handle_model(self):
        func_name = 'func_{}'.format(self.model_action)
        func_name = func_name.lower()
        handle_function = getattr(CommentHandler, func_name)
        res = handle_function(self)
        return res

    def func_comment_post(self):
        """
        发布评论
        """
        user = g.user
        if not user:
            raise response_code.UserERR(errmsg='用户未登录')
        video_id = self.extra_data.get("video_id", "")
        parent_id = self.extra_data.get("parent_id", "")
        content = self.extra_data.get("content", "")
        comment_time = self.extra_data.get("time", "")
        if video_id == "" or content == "" or parent_id == "" or comment_time == "":
            raise response_code.ParamERR(
                errmsg="[video_id, content, parent_id, time] must be provided")
        comment_info = {"_id": create_uuid(), "video_id": video_id,
                        "content": content, "time": comment_time,
                        "parent_id": parent_id, "user_id": user["_id"]}
        try:
            mongo.db.comment.insert(comment_info)
        except Exception as e:
            raise response_code.DatabaseERR(errmsg="{}".format(e))
        return set_resjson()

    def func_comment_like(self):

        pass
