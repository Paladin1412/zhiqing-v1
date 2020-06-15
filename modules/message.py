#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    : message.py
@Time    : 2020/6/1 18:06
@Author  : Qi
@Email   : 18821723039@163.com
@Software: PyCharm
"""
from copy import deepcopy

from flask import g

from main import mongo
from utils import response_code
from utils.setResJson import set_resjson


class MessageHandler(object):
    """
    系列
    """

    def __init__(self, extra_data, model_action):
        self.extra_data = extra_data
        self.model_action = model_action

    def handle_model(self):
        func_name = 'func_{}'.format(self.model_action)
        func_name = func_name.lower()
        try:
            handle_function = getattr(MessageHandler, func_name)
            if self.model_action not in ["get_message", "read_message"]:
                if self.extra_data == '':
                    raise response_code.ParamERR(
                        errmsg="[ extra_data ] must be provided ")
            resp = handle_function(self)
        except AttributeError as e:
            resp = set_resjson(err=-4,
                               errmsg="{} is incorrect !".format(
                                   self.model_action))
        return resp

    @staticmethod
    def func_get_message(self):
        """
        查看消息：
        @return:
        """
        user = g.user
        if not user:
            return set_resjson()
        else:
            res_list = []
            like_list = []
            like_dict = {}
            res_dict = {}
            subscription_dict = {}
            subscription_list = []
            video_cursor = mongo.db.video.find(
                {"state": 2, "user_id": user["_id"]}, {"_id": 1})
            video_id_list = [video.get("_id") for video in video_cursor]
            like_cursor = mongo.db.like.find(
                {"relation_id": {"$in": video_id_list}}).sort(
                [("read_state", 1), ("time", -1)])
            unread_like_counts = mongo.db.like.find(
                {"relation_id": {"$in": video_id_list},
                 "read_state": 0}).count()
            res_dict["unread_counts"] = unread_like_counts
            res_dict["type"] = "like"
            for like in like_cursor:
                fans = mongo.db.user.find_one({"_id": like["user_id"]},
                                              {"name": 1})
                like_dict["message_id"] = like["_id"]
                like_dict["sender"] = fans["name"]
                like_dict["state"] = like["read_state"]
                like_dict["time"] = like["time"]
                like_dict["message"] = "给你点了赞"
                like_list.append(deepcopy(like_dict))
            res_dict["data"] = like_list
            res_list.append(deepcopy(res_dict))
            fans_cursor = mongo.db.subscription.find(
                {"relation_id": user["_id"], "state": 0, "type": "author"})
            sender_counts = mongo.db.subscription.find(
                {"relation_id": user["_id"], "state": 0, "type": "author",
                 "read_state": 0}).count()
            res_subscription = {}
            res_subscription["type"] = "subscription"
            res_subscription["unread_counts"] = sender_counts
            for sender_user in fans_cursor:
                sender = mongo.db.user.find_one(
                    {"_id": sender_user["user_id"]}, {"name": 1})
                subscription_dict["message_id"] = sender_user["_id"]
                subscription_dict["sender"] = sender["name"]
                subscription_dict["state"] = sender_user["read_state"]
                subscription_dict["time"] = sender_user["time"]
                subscription_dict["message"] = "订阅了你"
                subscription_list.append(deepcopy(subscription_dict))
            res_subscription["data"] = subscription_list
            res_list.append(deepcopy(res_subscription))

        return set_resjson(res_array=res_list)

    def func_read_message(self):
        """
        阅读消息
        @return:
        """
        user = g.user
        if not user:
            raise response_code.UserERR(errmsg='用户未登录')
        message_id_list = self.extra_data.get("message_id")
        date_type = self.extra_data.get("type")
        if type(message_id_list) != list:
            raise response_code.ParamERR(errmsg="message_id must be list")
        elif date_type not in ["like", "subscription", "system"]:
            raise response_code.ParamERR(errmsg="type is Incorrect")
        if date_type == "like":
            mongo.db.like.update({"_id": {"$in": message_id_list}},
                                 {"$set": {"read_state": 1}}, multi=True)
        elif date_type == "subscription":
            mongo.db.subscription.update({"_id": {"$in": message_id_list}},
                                         {"$set": {"read_state": 1}},
                                         multi=True)
        else:
            return set_resjson(errmsg="这个功能暂时没做")
        return set_resjson(errmsg="200")
