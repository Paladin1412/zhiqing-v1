#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    : series.py
@Time    : 2020/5/13 15:19
@Author  : Qi
@Email   : 18821723039@163.com
@Software: PyCharm
"""
from copy import deepcopy

from flask import g

from main import mongo
from utils import response_code
from utils.setResJson import set_resjson


class SeriesHandler(object):
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
            handle_function = getattr(SeriesHandler, func_name)
            if self.model_action not in ["get_series"]:
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
    def func_get_series(self):
        """
        获得系列信息
        """
        user = g.user
        if not user:
            raise response_code.UserERR(errmsg='用户未登录')
        try:
            series_cursor = mongo.db.series.find({'user_id': user["_id"]},
                                                 {"title": 1, "_id": 0})
        except Exception as e:
            raise response_code.ParamERR(errmsg="{}".format(e))
        # res_data = []
        # for result in results:
        #     data_dict = {'title': result['title']}
        #     res_data.append(data_dict)
        res_list = [i for i in series_cursor]
        return set_resjson(res_array=res_list)

    def func_get_series_details(self):
        """
        系列详情页
        @return:
        """
        user = g.user
        res_dict = {}
        video_dict = {}
        document_dict = {}
        document_list = []
        res_list = []
        video_list = []
        series_id = self.extra_data.get("series_id", "")
        if series_id == "":
            raise response_code.ParamERR(errmsg="[series_id] must be provide")
        series_info = mongo.db.series.find_one({"_id": series_id})
        if not series_info:
            raise response_code.ParamERR(errmsg="series_id is incorrect")
        collect = None
        subscription = None
        if user:
            collect = mongo.db.collection.find_one(
                {"user_id": user["_id"], "relation_id": series_id, "state": 0,
                 "type": "series"})
            subscription = mongo.db.subscription.find_one(
                {'relation_id': series_info["user_id"], 'type': 'author',
                 'user_id': user["_id"], "state": 0})
        document_counts = 0
        like_counts = mongo.db.like.find({"relation_id": series_id}).count()
        collection_counts = mongo.db.collection.find(
            {"relation_id": series_id, "type": "series"}).count()
        author_info = mongo.db.user.find_one({"_id": series_info["user_id"]})
        res_dict["title"] = series_info["title"]
        res_dict["image_path"] = series_info["image_path"]
        res_dict["update_time"] = series_info["time"]
        res_dict["fans_counts"] = mongo.db.subscription.find(
            {"relation_id": author_info["_id"], "state": 0}).count()
        res_dict["description"] = series_info["description"]
        res_dict["author_id"] = series_info["user_id"]
        res_dict["is_collect"] = 1 if collect else 0
        res_dict["is_subscription"] = 1 if subscription else 0
        res_dict["video_counts"] = series_info.get("video_counts",
                                                   None) if series_info.get(
            "video_counts", None) else mongo.db.video.find(
            {"series": series_id, "state": 2}).count()
        res_dict["author_name"] = author_info["name"]
        res_dict["headshot"] = author_info["headshot"]
        # TODO 视频分享没做
        res_dict["share_counts"] = 0
        video_cursor = mongo.db.video.find(
            {"series": series_id, "state": 2}).sort(
            [("number", 1), ("upload_time", -1)])
        video_id_list = []
        for video in video_cursor:
            video_id_list.append(video["_id"])
            video_like_counts = mongo.db.like.find(
                {"relation_id": video["_id"],
                 "type": "video"}).count()
            like_counts += video_like_counts
            video_dict["video_id"] = video["_id"]
            video_dict["video_title"] = video["title"]
            video_dict["description"] = video["description"]
            video_dict["video_time"] = video["video_time"]
            video_dict["upload_time"] = video["upload_time"]
            video_dict["image_path"] = video["image_path"]
            video_dict["view_counts"] = video["view_counts"]
            video_dict["like_counts"] = video_like_counts
            video_dict["comment_counts"] = mongo.db.comment.find(
                {"state": 2, "video_id": video["_id"]}).count()
            video_list.append(deepcopy(video_dict))
            document_cursor = mongo.db.document.find({"video_id": video["_id"]})
            if document_cursor.count() > 0:
                for document in document_cursor:
                    document_counts += 1
                    document_dict["file_id"] = document["_id"]
                    document_dict["file_name"] = document["file_name"]
                    document_dict["file_type"] = document["type"]
                    document_dict["price"] = document["price"]
                    document_dict["image_path"] = document["image_path"]
                    document_dict["download_counts"] = document[
                        "download_counts"]
                    document_list.append(deepcopy(document_dict))
        res_dict["document_counts"] = document_counts

        collection_counts += mongo.db.collection.find(
            {"state": 0, "relation_id": {"$in": video_id_list}}).count()
        res_dict["collection_counts"] = collection_counts
        res_dict["video_data"] = video_list
        res_dict["document_data"] = document_list
        res_dict["like_counts"] = like_counts
        res_list.append(res_dict)
        return set_resjson(res_array=res_list)
