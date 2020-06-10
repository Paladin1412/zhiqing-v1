#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    : like.py
@Time    : 2020/5/11 18:39
@Author  : Qi
@Email   : 18821723039@163.com
@Software: PyCharm
"""
import time
from copy import deepcopy

from flask import g, current_app

from main import mongo
from utils import response_code
from utils.mongo_id import create_uuid
from utils.setResJson import set_resjson


class LikeHandler(object):
    """
    点赞
    """
    def __init__(self, extra_data, model_action):
        self.extra_data = extra_data
        self.model_action = model_action

    def handle_model(self):
        func_name = 'func_{}'.format(self.model_action)
        func_name = func_name.lower()
        try:
            handle_function = getattr(LikeHandler, func_name)
            resp = handle_function(self)
        except AttributeError as e:
            resp = set_resjson(err=-4,
                               errmsg="{} is incorrect !".format(
                                   self.model_action))
        return resp

    def func_give_like(self):
        """
        视频点赞
        :return:
        """
        user = g.user
        if not user:
            raise response_code.UserERR(errmsg='用户未登录')
        relation_id = self.extra_data.get("relation_id", "")
        value = self.extra_data.get("value", "")
        like_type = self.extra_data.get("type", "")
        try:
            value = int(value)
        except Exception as e:
            raise response_code.ParamERR(
                errmsg="value type error: {}".format(e))
        if relation_id == "":
            raise response_code.ParamERR("[relation_id] must be provided")
        elif like_type not in ["video", "series", "comment"]:
            raise response_code.ParamERR(errmsg="type must be video or series")
        elif value not in [1, 0]:
            raise response_code.ParamERR(errmsg="value must be 1 or 0")

        if like_type == "video":
            try:
                video_info = mongo.db.video.find_one({"_id": relation_id})
            except Exception as e:
                raise response_code.DatabaseERR(errmsg="{}".format(e))
        elif like_type == "series":
            try:
                video_info = mongo.db.document.find_one({"_id": relation_id})
            except Exception as e:
                raise response_code.DatabaseERR(errmsg="{}".format(e))
        else:
            try:
                video_info = mongo.db.comment.find_one({"_id": relation_id})
            except Exception as e:
                raise response_code.DatabaseERR(errmsg="{}".format(e))

        if not video_info:
            raise response_code.DatabaseERR(
                errmsg="relation_id is incorrect !")
        else:
            try:
                like_info = mongo.db.like.find_one(
                    {"user_id": user["_id"], "relation_id": relation_id})
            except Exception as e:
                raise response_code.DatabaseERR(errmsg="{}".format(e))
            like_time = time.time()
            if value == 1:
                if not like_info:
                    try:
                        mongo.db.like.insert_one(
                            {"_id": create_uuid(), "user_id": user["_id"],
                             "relation_id": relation_id, "type": like_type,
                             "time": like_time, "read_state": 0})
                    except Exception as e:
                        raise response_code.DatabaseERR(
                            errmsg="{}".format(e))
                else:
                    raise response_code.ParamERR(errmsg="你已经点过赞了")
            else:
                if like_info:
                    try:
                        mongo.db.like.delete_one({"user_id": user["_id"],
                                                  "relation_id": relation_id})
                    except Exception as e:
                        raise response_code.DatabaseERR(
                            errmsg="{}".format(e))
                else:
                    raise response_code.ParamERR(errmsg="你没有点赞过此视频，无法取消")

        return set_resjson()

    @staticmethod
    def func_get_like(self):
        """
        查看点赞
        @return:
        """
        user = g.user
        if not user:
            raise response_code.UserERR(errmsg='用户未登录')
        res_list = []
        try:
            for like in mongo.db.like.find(
                    {"user_id": user["_id"], "type": "video"}).sort("time", -1):
                video_info = mongo.db.video.find_one(
                    {"_id": like["relation_id"]},
                    {"title": 1, "upload_time": 1,
                     "video_time": 1,
                     "image_path": 1})
                if not video_info:
                    continue
                video_id = video_info.pop("_id")
                video_info["video_id"] = video_id
                video_info["like_counts"] = mongo.db.like.find(
                    {"relation_id": video_id}).count()
                res_list.append(deepcopy(video_info))
        except Exception as e:
            current_app.log.error(e)
            raise response_code.ParamERR(errmsg="{}".format(e))
        return set_resjson(res_array=res_list)
