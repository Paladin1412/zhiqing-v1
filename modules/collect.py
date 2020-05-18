#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    : collect.py
@Time    : 2020/5/11 15:48
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


class CollectHandler(object):
    """
    收藏
    """
    def __init__(self, extra_data, model_action):
        self.extra_data = extra_data
        self.model_action = model_action

    def handle_model(self):
        func_name = 'func_{}'.format(self.model_action)
        func_name = func_name.lower()
        try:
            handle_function = getattr(CollectHandler, func_name)
            resp = handle_function(self)
        except AttributeError as e:
            resp = set_resjson(err=-4,
                               errmsg="{} is incorrect !".format(
                                   self.model_action))
        return resp

    def func_video_collect(self):
        """
        收藏
        :return:
        """
        user = g.user
        if not user:
            raise response_code.UserERR(errmsg='用户未登录')
        relation_id = self.extra_data.get("relation_id", "")
        value = self.extra_data.get("value", "")
        collect_type = self.extra_data.get("type", "")
        collect_time = time.time()
        try:
            value = int(value)
        except Exception as e:
            raise response_code.ParamERR(
                errmsg="value type error: {}".format(e))
        if relation_id == "":
            raise response_code.ParamERR("[relation_id] must be provided")
        elif collect_type not in ["video", "series"]:
            raise response_code.ParamERR(errmsg="type must be video or series")
        elif value not in [1, 0]:
            raise response_code.ParamERR(errmsg="value must be 1 or 0")
        if collect_type == "video":
            try:
                video_info = mongo.db.video.find_one({"_id": relation_id})
            except Exception as e:
                raise response_code.DatabaseERR(errmsg="{}".format(e))

            # if not video_info:
            #     raise response_code.DatabaseERR(
            #         errmsg="video_id is incorrect !")
            # else:
            #     try:
            #         collect_info = mongo.db.collection.find_one(
            #             {"user_id": user["_id"], "relation_id": video_id})
            #     except Exception as e:
            #         raise response_code.DatabaseERR(errmsg="{}".format(e))
            #     if value == 1:
            #         if not collect_info:
            #             try:
            #                 mongo.db.collection.insert_one(
            #                     {"_id": create_uuid(), "user_id": user["_id"],
            #                      "relation_id": video_id, "type": collect_type,
            #                      "time": collect_time})
            #             except Exception as e:
            #                 raise response_code.DatabaseERR(
            #                     errmsg="{}".format(e))
            #         else:
            #             raise response_code.ParamERR(errmsg="该视频已经收藏")
            #     else:
            #         if collect_info:
            #             try:
            #                 mongo.db.collection.delete_one({"user_id": user["_id"],
            #                                              "relation_id": video_id})
            #             except Exception as e:
            #                 raise response_code.DatabaseERR(
            #                     errmsg="{}".format(e))
            #         else:
            #             raise response_code.ParamERR(errmsg="没有收藏此视频")
        else:
            try:
                video_info = mongo.db.document.find_one({"_id": relation_id})
            except Exception as e:
                raise response_code.DatabaseERR(errmsg="{}".format(e))

        if not video_info:
            raise response_code.DatabaseERR(
                errmsg="relation_id is incorrect !")
        else:
            try:
                collect_info = mongo.db.collection.find_one(
                    {"user_id": user["_id"], "relation_id": relation_id})
            except Exception as e:
                raise response_code.DatabaseERR(errmsg="{}".format(e))
            if value == 1:
                if not collect_info:
                    try:
                        mongo.db.collection.insert_one(
                            {"_id": create_uuid(), "user_id": user["_id"],
                             "relation_id": relation_id, "type": collect_type,
                             "time": collect_time})
                    except Exception as e:
                        raise response_code.DatabaseERR(
                            errmsg="{}".format(e))
                else:
                    raise response_code.ParamERR(errmsg="该视频已经收藏")
            else:
                if collect_info:
                    try:
                        mongo.db.collection.delete_one({"user_id": user["_id"],
                                                        "relation_id": relation_id})
                    except Exception as e:
                        raise response_code.DatabaseERR(
                            errmsg="{}".format(e))
                else:
                    raise response_code.ParamERR(errmsg="没有收藏此视频")

        return set_resjson()
