#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    : subscription.py
@Time    : 2020/5/18 14:23
@Author  : Qi
@Email   : 18821723039@163.com
@Software: PyCharm
"""
import time
from copy import deepcopy
from operator import itemgetter

from flask import g

from main import mongo
from utils import response_code
from utils.setResJson import set_resjson


class SubscriptionHandler(object):
    """
    订阅
    """
    def __init__(self, extra_data, model_action):
        self.extra_data = extra_data
        self.model_action = model_action

    def handle_model(self):
        func_name = 'func_{}'.format(self.model_action)
        func_name = func_name.lower()
        try:
            handle_function = getattr(SubscriptionHandler, func_name)
            resp = handle_function(self)
        except AttributeError as e:
            resp = set_resjson(err=-4,
                               errmsg="{} is incorrect !".format(
                                   self.model_action))
        return resp

    def func_latest_subscription(self):
        """
        最新订阅
        @return:
        """
        video_list = []
        video_dict = {}
        user = g.user
        if not user:
            raise response_code.UserERR(errmsg='用户未登录')
        mode = self.extra_data.get("type", "")
        if mode == "":
            raise response_code.ParamERR(errmsg="type must be provide")

        sub_cursor = mongo.db.subscription.find({"user_id": user["_id"]},
                                                {"_id": 0,
                                                 "relation_id": 1})
        for user_id in sub_cursor:
            print(user_id)
            video_cursor = mongo.db.video.find(
                {"user_id": user_id.get("relation_id"), "state": 2},
                {"image_path": 1, "title": 1, "category": 1,
                 "upload_time": 1, "video_time": 1, "user_id": 1})
            user_info = mongo.db.user.find_one(
                {"_id": user_id.get("relation_id")})
            for video in video_cursor:
                print(video)
                video_dict["video_id"] = video["_id"]
                video_dict["image_path"] = video["image_path"]
                video_dict["title"] = video["title"]
                video_dict["category"] = video["category"]
                video_dict["update_time"] = video["upload_time"]
                video_dict["video_time"] = video["video_time"]
                video_dict["user_id"] = video["user_id"]
                video_dict["user_name"] = user_info["name"]
                video_dict["head_shot"] = user_info["headshot"]

                video_list.append(deepcopy(video_dict))
        res_list = sorted(video_list, key=itemgetter("update_time"),
                              reverse=True)

        if mode == "web":
            resp = set_resjson(res_array=res_list[:4])
        else:
            app_list = []
            latest_user_id = res_list[0].get("user_id")
            for video_dict in res_list:
                if latest_user_id == video_dict.get("user_id"):
                    app_list.append(video_dict)
                    if len(app_list) == 2:
                        break
            resp = set_resjson(res_array=app_list)

        return resp



