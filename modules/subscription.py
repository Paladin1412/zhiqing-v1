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
import traceback
from copy import deepcopy
from operator import itemgetter

from flask import g

from main import mongo
from utils import response_code
from utils.mongo_id import create_uuid
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

    def func_add_subscription(self):
        """
        订阅
        @return:
        """
        user = g.user
        if not user:
            raise response_code.UserERR(errmsg='用户未登录')
        sub_type = self.extra_data.get("type", "")
        relation_id = self.extra_data.get("relation_id", "")
        value = self.extra_data.get("value", "")
        if value not in [0, 1]:
            raise response_code.ParamERR(errmsg="value must be 1 or 0")
        elif relation_id == "":
            raise response_code.ParamERR(errmsg="relation_id must be provide")
        elif sub_type != "author":
            raise response_code.ParamERR(errmsg="mode must be author")
        author_info = mongo.db.user.find_one({"_id": relation_id})
        if not author_info:
            raise response_code.ParamERR(errmsg="relation_id 不存在")
        else:
            sub_info = mongo.db.subscription.find_one(
                {"relation_id": relation_id, "user_id": user["_id"]})
            if value == 1:
                if not sub_info:
                    mongo.db.subscription.insert_one(
                        {"_id": create_uuid(), "user_id": user["_id"],
                         "relation_id": relation_id, "read_state": 0,
                         "time": time.time(), "type": sub_type, "state": 0})
                elif sub_info["state"] == -1:
                    mongo.db.subscription.update_one({"_id": sub_info["_id"]},
                                                     {"$set": {"state": 0}})
                else:
                    raise response_code.ParamERR(errmsg="此作者已经订阅")
            else:
                if sub_info:
                    if sub_info["state"] == 0:
                        mongo.db.subscription.update_one(
                            {"_id": sub_info["_id"]},
                            {"$set": {"state": -1}})
                    else:
                        raise response_code.ParamERR(errmsg="此作者还没有订阅")
                else:
                    raise response_code.ParamERR(errmsg="此作者还没有订阅")

        return set_resjson()

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

        sub_cursor = mongo.db.subscription.find(
            {"user_id": user["_id"], "state": 0},
            {"_id": 0,
             "relation_id": 1})
        if sub_cursor.count() == 0:
            raise response_code.RoleERR(errmsg="你还没有订阅")
        tool = mongo.db.tool.find_one({'type': 'category'}).get("data")
        for user_id in sub_cursor:
            video_cursor = mongo.db.video.find(
                {"user_id": user_id.get("relation_id"), "state": 2},
                {"image_path": 1, "title": 1, "category": 1,
                 "upload_time": 1, "video_time": 1, "user_id": 1,
                 "view_counts": 1})
            user_info = mongo.db.user.find_one(
                {"_id": user_id.get("relation_id")})
            for video in video_cursor:
                category_list = []
                for category in video['category']:
                    for data_category in tool:
                        if category == data_category["id"]:
                            category_list.append(data_category["name"])
                video_dict["video_id"] = video["_id"]
                video_dict["image_path"] = video["image_path"]
                video_dict["title"] = video["title"]
                video_dict["category"] = category_list
                video_dict["update_time"] = video["upload_time"]
                video_dict["video_time"] = video["video_time"]
                video_dict["user_id"] = video["user_id"]
                video_dict["view_counts"] = video["view_counts"]
                video_dict["like_counts"] = mongo.db.like.find(
                    {"relation_id": video["_id"]}).count()
                video_dict["user_name"] = user_info["name"]
                video_dict["head_shot"] = user_info["headshot"]
                video_dict["introduction"] = user_info["introduction"]

                video_list.append(deepcopy(video_dict))
        res_list = sorted(video_list, key=itemgetter("update_time"),
                          reverse=True)

        if mode == "web":
            resp = set_resjson(res_array=res_list[:8])
        else:
            if res_list == []:
                return set_resjson()
            app_list = []
            latest_user_id = res_list[0].get("user_id")
            for video_dict in res_list:
                if latest_user_id == video_dict.get("user_id"):
                    app_list.append(video_dict)
                    if len(app_list) == 2:
                        break
            resp = set_resjson(res_array=app_list)

        return resp

    @staticmethod
    def func_get_subscription(self):
        """
        查看订阅
        @return:
        """
        user = g.user
        if not user:
            raise response_code.UserERR(errmsg='用户未登录')
        res_dict = {}
        res_list = []
        video_dict = {}
        series_dict = {}

        sub_cursor = mongo.db.subscription.find(
            {"user_id": user["_id"], "state": 0})
        for sub_author in sub_cursor:
            author_info = mongo.db.user.find_one(
                {"_id": sub_author["relation_id"]})
            res_dict["author_id"] = author_info["_id"]
            res_dict["author_name"] = author_info["name"]
            res_dict["background"] = author_info["background"]
            res_dict["introduction"] = author_info["introduction"]
            res_dict["headshot"] = author_info["headshot"]
            res_dict["video_counts"] = mongo.db.video.find(
                {"user_id": author_info["_id"], "state": 2}).count()
            res_dict["fans_counts"] = mongo.db.subscription.find(
                {"relation_id": author_info["_id"], "state": 0}).count()
            video_cursor = mongo.db.video.find(
                {"user_id": author_info["_id"], "state": 2,
                 "series": {"$exists": False}}).sort("upload_time", -1)
            works = []
            for video in video_cursor:
                video_dict["type"] = "video"
                video_dict["video_id"] = video["_id"]
                video_dict["title"] = video["title"]
                video_dict["update_time"] = video["upload_time"]
                video_dict["image_path"] = video["image_path"]
                video_dict["video_time"] = video["video_time"]
                video_dict["view_counts"] = video["view_counts"]
                video_dict["like_counts"] = mongo.db.like.find(
                    {"relation_id": video["_id"], "type": "video"}).count()
                video_dict["comment_counts"] = mongo.db.comment.find(
                    {"video_id": video["_id"], "state": 0}).count()
                works.append(deepcopy(video_dict))
            series_cursor = mongo.db.series.find(
                {"user_id": author_info["_id"]}).sort("time", -1)
            for series in series_cursor:
                view_counts = 0
                video_id_list = []
                series_dict["type"] = "series"
                series_dict["series_id"] = series["_id"]
                series_dict["title"] = series["title"]
                series_dict["update_time"] = series["time"]
                series_dict["image_path"] = series["image_path"]
                series_video_cursor = mongo.db.video.find(
                    {"series": series["_id"], "state": 2}).sort(
                    [("number", 1), ("upload_time", -1)])
                series_dict["video_counts"] = series.get("video_counts",
                                                         None) if series.get(
                    "video_counts", None) else series_video_cursor.count()
                for video in series_video_cursor:
                    view_counts += video["view_counts"]
                    video_id_list.append(video["_id"])
                like_counts = mongo.db.like.find(
                    {"relation_id": {"$in": video_id_list}}).count()
                comment_counts = mongo.db.comment.find(
                    {"state": 2, "video_id": {"$in": video_id_list}}).count()
                series_dict["like_counts"] = like_counts
                series_dict["comment_counts"] = comment_counts
                series_dict["view_counts"] = view_counts
                works.append(deepcopy(series_dict))
            res_dict["works"] = sorted(works, key=itemgetter("view_counts"),
                                       reverse=True)
            res_list.append(deepcopy(res_dict))
        res_sort_list = sorted(res_list, key=itemgetter("fans_counts"),
                               reverse=True)
        return set_resjson(res_array=res_sort_list)

    @staticmethod
    def func_get_fans(self):
        """
        查看粉丝信息
        @param self:
        @return:
        """
        user = g.user
        if not user:
            raise response_code.UserERR(errmsg='用户未登录')
        try:
            fans_cursor = mongo.db.subscription.find(
                {"relation_id": user["_id"], "type": "author"}).sort("time", -1)
            res_list = []
            for fans in fans_cursor:
                works = []
                fans_info = mongo.db.user.find_one({"_id": fans["relation_id"]},
                                                   {"name": 1,
                                                    "introduction": 1,
                                                    "headshot": 1,
                                                    "background": 1})
                if not fans_info:
                    continue
                video_cursor = mongo.db.video.find(
                    {"user_id": fans_info["_id"]},
                    {"title": 1, "upload_time": 1, "image_path": 1,
                     "video_time": 1, "view_counts": 1, "background": 1})
                fans_id = fans_info.pop("_id")
                fans_info["author_id"] = fans_id
                fans_info["fans_counts"] = mongo.db.subscription.find(
                    {"relation_id": fans_id}).count()
                fans_info["author_name"] = fans_info.pop("name")
                fans_info["video_counts"] = video_cursor.count()
                for video in video_cursor:
                    single_video_id = video.pop("_id")
                    video["type"] = "video"
                    video["video_id"] = single_video_id
                    video["like_counts"] = mongo.db.like.find(
                        {"relation_id": single_video_id,
                         "read_state": 0}).count()
                    video["comment_counts"] = mongo.db.commention.find(
                        {"video_id": single_video_id, "state": 2}).count()
                    works.append(deepcopy(video))
                for series in mongo.db.series.find({"user_id": fans_id},
                                                   {"_id": 1, "title": 1,
                                                    "time": 1,
                                                    "image_path": 1}):
                    series_id = series.pop("_id")
                    series["series_id"] = series_id
                    series["type"] = "series"
                    series["update_time"] = series.pop("time")
                    view_counts = 0
                    series_video_id_List = []
                    for video in mongo.db.video.find(
                            {"series": series_id, "state": 2},
                            {"view_counts": 1}):
                        view_counts += video["view_counts"]
                        series_video_id_List.append(video["_id"])
                    like_counts = mongo.db.like.find(
                        {"relation_id": {"$in": series_video_id_List}}).count()
                    comment_counts = mongo.db.comment.find(
                        {"state": 2,
                         "video_id": {"$in": series_video_id_List}}).count()
                    series["view_counts"] = view_counts
                    series["like_counts"] = like_counts
                    series["comment_counts"] = comment_counts
                    works.append(deepcopy(series))
                fans_info["works"] = sorted(works,
                                            key=itemgetter("view_counts"),
                                            reverse=True)
                res_list.append(deepcopy(fans_info))
        except Exception as e:
            traceback.print_exc()
            raise response_code.ParamERR(errmsg="{}".format(e))
        return set_resjson(res_array=res_list)
