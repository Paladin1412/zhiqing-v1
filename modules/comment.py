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
import time

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

    def func_post_comment(self):
        """
        发表评论
        """
        user = g.user
        if not user:
            raise response_code.UserERR(errmsg='用户未登录')
        video_id = self.extra_data.get("video_id", "")
        parent_id = self.extra_data.get("parent_id", "")
        content = self.extra_data.get("content", "")
        # to_user_id = self.extra_data.get("to_user_id", "")
        # to_user_name = self.extra_data.get("to_user_name", "")
        collect_time = time.time()
        try:
            parent_id = int(parent_id)
        except Exception as e:
            raise response_code.ParamERR(errmsg="parent_id is incorrect !")
        if video_id == "" or content == "" or parent_id == "":
            raise response_code.UserERR(
                errmsg="[ video_id, parent_id, content ] must be provided")
        try:
            video_info = mongo.db.video.find_one({"_id": video_id})
        except Exception as e:
            raise response_code.DatabaseERR(errmsg="{}".format(e))
        if not video_info:
            raise response_code.ParamERR(errmsg="video_id is incorrect")
        _id = create_uuid()
        if parent_id != 0:
            try:
                comment_info = mongo.db.comment.find_one(
                    {"_id": "{}".format(parent_id)})
            except Exception as e:
                raise response_code.DatabaseERR(errmsg="{}".format(e))
            if not comment_info:
                raise response_code.ParamERR(errmsg="parent_id is incorrect")
            try:
                mongo.db.comment.insert(
                    {"_id": _id, "parent_id": "{}".format(parent_id),
                     "content": content, "time": collect_time,
                     "video_id": video_id,
                     "to_user_id": comment_info["user_id"],
                     "user_name": user["name"], "headshot": user["headshot"],
                     "user_id": user["_id"],
                     "to_user_name": comment_info["user_name"],
                     "state": 2})
            except Exception as e:
                raise response_code.DatabaseERR(errmsg="{}".format(e))
        else:
            try:
                mongo.db.comment.insert(
                    {"_id": _id, "parent_id": "{}".format(parent_id),
                     "content": content, "time": collect_time,
                     "video_id": video_id,
                     "user_id": user["_id"], "user_name": user["name"],
                     "headshot": user["headshot"],
                     "state": 2})
            except Exception as e:
                raise response_code.DatabaseERR(errmsg="{}".format(e))

        return set_resjson(res_array=[{"comment_id": _id}])

    def func_get_comment(self):
        '''
        获取评论
        :param video_id:
        :param parent_id:
        :param max_size:
        :param page:
        :return res_data:
        '''
        video_id = self.extra_data.get("video_id", "")
        parent_id = self.extra_data.get("parent_id", "")
        max_size = self.extra_data.get("max_size", "")
        page = self.extra_data.get("page", "")

        try:
            max_size = int(max_size)
            page = int(page)
        except Exception as e:
            raise response_code.ParamERR(errmsg="max_size, page must be int")
        res_data = []
        try:
            likes = mongo.db.like.find(
                {'relation_id': video_id, 'type': 'comment'},
                {'_id': 1})
            like_list = []
            if likes:
                for like in likes:
                    like_list.append(like['_id'])
            if parent_id:
                comments = mongo.db.comment.find(
                    {'video_id': video_id, 'parent_id': parent_id,
                     "state": 2}).sort('time',
                                       -1).limit(
                    max_size).skip(max_size * (page - 1))
            else:
                comments = mongo.db.comment.find(
                    {'video_id': video_id, 'parent_id': "0"}).sort(
                    'time', -1).limit(max_size).skip(max_size * (page - 1))
            if comments:
                for comment in comments:
                    if comment['_id'] in like_list:
                        comment['is_like'] = 1
                    else:
                        comment['is_like'] = 0
                    like_counts = mongo.db.like.find(
                        {"relation_id": comment['_id'],
                         "type": "comment"}).count()
                    comment['like_counts'] = like_counts
                    if parent_id == "0":
                        comment_counts = mongo.db.comment.find(
                            {"parent_id": comment['_id'],
                             "state": 2}).count()
                        comment['comment_counts'] = comment_counts
                    res_data.append(comment)
        except Exception as e:
            raise response_code.DatabaseERR(errmsg="{}".format(e))
        return set_resjson(res_array=res_data)

    # def func_database(self):
    #     # info = {
    #     #     "background": "http://api.haetek.com:9191/static/background/background.jpg",
    #     #     "introduction": "这是一个学习的视频， 好好看， 好好学"
    #     # }
    #     # user = mongo.db.user.find()
    #     # for i in user:
    #
    #     mongo.db.collection.update({}, {"$set": {"state": 0}}, multi=True)
    #
    #     return set_resjson()
