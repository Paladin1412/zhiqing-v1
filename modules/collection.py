#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    : collection.py
@Time    : 2020/5/11 15:48
@Author  : Qi
@Email   : 18821723039@163.com
@Software: PyCharm
"""
import time
from copy import deepcopy

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
            if self.model_action not in ["get_collection"]:
                if self.extra_data == '':
                    raise response_code.ParamERR(
                        errmsg="[ extra_data ] must be provided ")
            resp = handle_function(self)
        except AttributeError as e:
            resp = set_resjson(err=-4,
                               errmsg="{} is incorrect !".format(
                                   self.model_action))
        return resp

    def func_add_collection(self):
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
        else:
            try:
                video_info = mongo.db.series.find_one({"_id": relation_id})
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
                             "time": collect_time, "state": 0})
                    except Exception as e:
                        raise response_code.DatabaseERR(
                            errmsg="{}".format(e))

                elif collect_info["state"] == -1:
                    mongo.db.collection.update_one({"_id": collect_info["_id"]},
                                                   {"$set": {"state": 0}})
                else:
                    raise response_code.ParamERR(errmsg="该视频已经收藏")
            else:
                if collect_info:
                    if collect_info["state"] == 0:
                        try:
                            mongo.db.collection.update_one(
                                {"user_id": user["_id"],
                                 "relation_id": relation_id},
                                {"$set": {"state": -1}})
                        except Exception as e:
                            raise response_code.DatabaseERR(
                                errmsg="{}".format(e))
                    else:
                        raise response_code.ParamERR(errmsg="没有收藏此视频")
                else:
                    raise response_code.ParamERR(errmsg="没有收藏此视频")

        return set_resjson()

    def func_get_collection(self):
        """
        查看收藏
        @return:
        """
        user = g.user
        if not user:
            raise response_code.UserERR(errmsg='用户未登录')
        video_dict = {}
        series_dict = {}
        res_list = []
        view_counts = 0
        # like_counts = 0
        # comment_counts = 0
        collections_cursor = mongo.db.collection.find(
            {"user_id": user["_id"], "state": 0})
        for video_collect in collections_cursor:
            if video_collect["type"] == "video":
                video = mongo.db.video.find_one(
                    {"_id": video_collect["relation_id"]})
                video_dict["type"] = "video"
                video_dict["video_id"] = video["_id"]
                video_dict["title"] = video["title"]
                video_dict["update_time"] = video["upload_time"]
                video_dict["image_path"] = video["image_path"]
                video_dict["video_time"] = video["video_time"]
                video_dict["view_counts"] = video["view_counts"]
                video_dict["like_counts"] = mongo.db.like.find(
                    {"relation_id": video["_id"]}).count()
                video_dict["comment_counts"] = mongo.db.comment.find(
                    {"video_id": video["_id"]}).count()
                res_list.append(deepcopy(video_dict))
            else:
                video_id = []
                series_info = mongo.db.series.find_one(
                    {"_id": video_collect["relation_id"]})
                video_cursor = mongo.db.video.find(
                    {"series": series_info["_id"], "state": 2})
                for video in video_cursor:
                    video_id.append(video["_id"])
                    view_counts += video["view_counts"]
                    # like_counts += mongo.db.like.find(
                    #     {"relation_id": video["_id"]}).count()
                    # comment_counts += mongo.db.comment.find(
                    #     {"video_id": video["_id"]}).count()
                series_dict["type"] = "series"
                series_dict["series_id"] = series_info["_id"]
                series_dict["title"] = series_info["title"]
                series_dict["image_path"] = series_info["image_path"]
                series_dict["view_counts"] = view_counts
                series_dict["video_counts"] = series_info.get("video_counts",
                                                              None) if series_info.get(
                    "video_counts", None) else mongo.db.video.find(
                    {"series": series_info["_id"]}).count()
                like_counts = mongo.db.like.find(
                    {"relation_id": {"$in": video_id}}).count()
                comment_counts = mongo.db.comment.find(
                    {"state": 0, "video_id": {"$in": video_id}}).count()
                series_dict["like_counts"] = like_counts
                series_dict["comment_counts"] = comment_counts
                res_list.append(deepcopy(series_dict))

        return set_resjson(res_array=res_list)
