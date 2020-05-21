#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    : history.py
@Time    : 2020/5/21 16:00
@Author  : Qi
@Email   : 18821723039@163.com
@Software: PyCharm
"""
import time

from flask import g

from main import mongo
from utils import response_code
from utils.mongo_id import create_uuid
from utils.setResJson import set_resjson


class HistoryHandler(object):
    """
    历史记录
    """

    def __init__(self, extra_data, model_action):
        self.extra_data = extra_data
        self.model_action = model_action

    def handle_model(self):
        func_name = 'func_{}'.format(self.model_action)
        func_name = func_name.lower()
        try:
            handle_function = getattr(HistoryHandler, func_name)
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

    def func_watch_history(self):
        """
        观看播放历史
        """
        user = g.user
        if not user:
            raise response_code.ParamERR(errmsg="用户未登陆")
        user_id = user["_id"]
        video_id = self.extra_data.get("video_id", "")
        end_time = self.extra_data.get("end_time", "")
        if end_time == "" or video_id == "":
            raise response_code.ParamERR(
                errmsg="video_id, end_time must be provide")
        try:
            time.strptime(end_time, "%H:%M:%S")
        except Exception as e:
            raise response_code.ParamERR("end_time format incorrect")
        video_info = mongo.db.video.find_one({"_id": video_id})
        if not video_info:
            raise response_code.ParamERR(errmsg="video_id 不存在")
        else:
            history_info = mongo.db.video_history.find_one(
                {"video_id": video_id, "user_id": user_id,
                 "record.action": "watch"})
            if not history_info:
                mongo.db.video_history.insert_one(
                    {"_id": create_uuid(), "time": time.time(),
                     "video_id": video_id, "user_id": user_id, "record": {
                        "action": "watch", "end_time": end_time}})
            else:
                mongo.db.video_history.update_one(
                    {"video_id": video_id, "user_id": user_id,
                     "record.action": "watch"},
                    {"$set": {"record.end_time": end_time}})

        return set_resjson()

    def func_search_history(self):
        """
        局部搜索历史记录
        @return:
        """
        user = g.user
        if not user:
            raise response_code.ParamERR(errmsg="用户未登陆")
        user_id = user["_id"]
        video_id = self.extra_data.get("video_id", "")
        query_string = self.extra_data.get("query_string", "")
        end_time = self.extra_data.get("end_time", "")
        if end_time == "" or video_id == "" or query_string:
            raise response_code.ParamERR(
                errmsg="video_id, end_time, query_string must be provide")
        try:
            time.strptime(end_time, "%H:%M:%S")
        except Exception as e:
            raise response_code.ParamERR("end_time format incorrect")
        video_info = mongo.db.video.find_one({"_id": video_id})
        if not video_info:
            raise response_code.ParamERR(errmsg="video_id 不存在")
        else:
            history_info = mongo.db.video_history.find_one(
                {"video_id": video_id, "user_id": user_id,
                 "record.action": "search",
                 "record.query_string": query_string})
            if not history_info:
                mongo.db.video_history.insert_one(
                    {"_id": create_uuid(), "time": time.time(),
                     "video_id": video_id, "user_id": user_id,
                     "record": {"action": "search",
                                "query_string": query_string,
                                "end_time": end_time}})
            else:
                mongo.db.video_history.update_one(
                    {"video_id": video_id, "user_id": user_id,
                     "record.action": "search",
                     "record.query_string": query_string},
                    {"$set": {"record.end_time": end_time}})

        return set_resjson()
