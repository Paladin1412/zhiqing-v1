#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    : home.py
@Time    : 2020/5/28 11:01
@Author  : Qi
@Email   : 18821723039@163.com
@Software: PyCharm
"""
import datetime
from copy import deepcopy

from flask import g

from main import mongo
from utils import response_code
from utils.setResJson import set_resjson


class IndexHandler(object):
    """
    用户账户
    """

    def __init__(self, extra_data, model_action):
        self.extra_data = extra_data
        self.model_action = model_action

    def handle_model(self):
        func_name = 'func_{}'.format(self.model_action)
        func_name = func_name.lower()
        try:
            handle_function = getattr(IndexHandler, func_name)
            if self.model_action not in []:
                if self.extra_data == '':
                    raise response_code.ParamERR(
                        errmsg="[ extra_data ] must be provided ")
            resp = handle_function(self)
        except AttributeError as e:
            resp = set_resjson(err=-4,
                               errmsg="{} is incorrect !".format(
                                   self.model_action))
        return resp

    def func_get_information(self):
        """
        个人中心首页
        @return:
        """
        user = g.user
        if not user:
            raise response_code.UserERR(errmsg='用户未登录')
        video_counts = self.extra_data.get("video_counts", 4)
        collection_counts = self.extra_data.get("collection_counts", 4)
        try:
            p_video_counts = int(video_counts)
            p_collection_counts = int(collection_counts)
        except Exception as e:
            raise response_code.ParamERR(
                errmsg="The parameter is of numeric type")
        res_dict = {}
        res_list = []
        video_dict = {}
        video_list = []
        collection_dict = {}
        collection_list = []
        now = datetime.datetime.now()
        week_ago = (now - datetime.timedelta(days=7)).timestamp()
        week_end_sub_count = mongo.db.subscription.find(
            {"relation_id": user["_id"], "state": 0,
             "time": {"$lte": week_ago}}).count()
        fans_counts = mongo.db.subscription.find(
            {"relation_id": user["_id"], "state": 0}).count()
        res_dict["user_id"] = user["_id"]
        res_dict["user_name"] = user["name"]
        res_dict["introduction"] = user["introduction"]
        res_dict["fans_counts"] = fans_counts
        res_dict["fans_change"] = fans_counts - week_end_sub_count
        res_dict["subscription_counts"] = mongo.db.subscription.find(
            {"user_id": user["_id"], "state": 0}).count()
        view_counts = 0
        download_counts = 0
        like_counts = 0
        collections_counts = 0
        video_id_list = []
        for video in mongo.db.video.find({"user_id": user["_id"]}).sort(
                "upload_time", -1):
            video_id_list.append(video["_id"])
            video_like_counts = mongo.db.like.find(
                {"relation_id": video["_id"],
                 "type": "video"}).count()
            like_counts += video_like_counts
            view_counts += video["view_counts"]
            video_dict["video_id"] = video["_id"]
            video_dict["title"] = video["title"]
            video_dict["update_time"] = video["upload_time"]
            video_dict["image_path"] = video["image_path"]
            video_dict["video_time"] = video["video_time"]
            video_dict["state"] = video["state"]
            video_dict["view_counts"] = video["view_counts"]
            video_dict["like_counts"] = video_like_counts
            video_dict["video_time"] = video["video_time"]
            video_list.append(deepcopy(video_dict))
            document_cursor = mongo.db.document.find({"video_id": video["_id"]})
            if document_cursor.count() > 0:
                for document in document_cursor:
                    download_counts += document["download_counts"]
        for series in mongo.db.series.find({"user_id": user["_id"]}):
            video_id_list.append(series["_id"])
        collections_counts += mongo.db.collection.find(
            {"state": 0, "relation_id": {"$in": video_id_list}}).count()
        # 收藏
        for collection in mongo.db.collection.find(
                {"user_id": user["_id"], "state": 0}).sort("time", -1).limit(
                p_collection_counts):
            if collection["type"] == "video":
                video = mongo.db.video.find_one(
                    {"_id": collection["relation_id"]})
                collection_dict["type"] = "video"
                collection_dict["video_id"] = video["_id"]
                collection_dict["title"] = video["title"]
                collection_dict["update_time"] = video["upload_time"]
                collection_dict["image_path"] = video["image_path"]
                collection_dict["video_time"] = video["video_time"]
                collection_dict["view_counts"] = video["view_counts"]
                collection_dict["like_counts"] = mongo.db.like.find(
                    {"relation": video['_id'], "type": "video"}).count()
            elif collection["type"] == "series":
                series = mongo.db.series.find_one(
                    {"_id": collection["relation_id"]})
                collection_dict["type"] = "series"
                collection_dict["series_id"] = series["_id"]
                collection_dict["title"] = series["title"]
                collection_dict["update_time"] = series["time"]
                collection_dict["image_path"] = series["image_path"]
                collection_dict["video_counts"] = series.get("video_counts",
                                                             None) if series.get(
                    "video_counts", None) else mongo.db.video.find(
                    {"series": series["_id"], "state": 2}).count()
                c_view_counts = 0
                c_like_counts = 0
                for video in mongo.db.video.find({"series": series["_id"]}):
                    c_view_counts += video["view_counts"]
                    c_like_counts += mongo.db.like.find(
                        {"relation_id": video['_id'], "type": "video"}).count()
                collection_dict["view_counts"] = c_view_counts
                collection_dict["like_counts"] = c_like_counts

            collection_list.append(deepcopy(collection_dict))
        res_dict["video"] = video_list[:p_video_counts]
        res_dict["view_count"] = view_counts
        # TODO 分享没有做
        res_dict["share_counts"] = 0
        res_dict["collection"] = collection_list
        res_dict["download_counts"] = download_counts
        res_dict["like_counts"] = like_counts
        res_dict["collections_counts"] = collections_counts
        res_list.append(res_dict)
        return set_resjson(res_array=res_list)
