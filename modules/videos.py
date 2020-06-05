#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File     : videos.py
@Time     : 2020-03-29 21:32
@Author   : Qi
@Email    : 18821723039@163.com
@Software : PyCharm
"""
import hashlib
import math
import os
import random
import re
import time
import traceback
from ast import literal_eval
from collections import Counter
from copy import deepcopy
from threading import Thread

import cv2
from flask import request, g, current_app

from config.settings import config
from main import mongo
from modules.aimodels import run_ai
from modules.aimodels.run_ai import generate_subtitle as generate_subtitle1, \
    edit_video, edit_document
from utils import response_code
from utils.mongo_id import create_uuid
from utils.setResJson import set_resjson
from utils.video_upload.uploadVideo import upload_video


class VideoHandler(object):
    """
    视频
    """

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
        handle_function = getattr(VideoHandler, func_name)
        if self.model_action not in ["global_search", "logout"]:
            if self.extra_data == '':
                raise response_code.ParamERR(
                    errmsg="[ extra_data ] must be provided ")
        res = handle_function(self)
        return res

    def func_global_search(self):
        """
        全局搜索视频
        :return:
        """
        query_string = self.extra_data.get("query_string", "")
        video_ids = self.extra_data.get("video_ids", "")
        mode = self.extra_data.get("type", "")
        max_size = self.extra_data.get("max_size", "")
        page = self.extra_data.get("page", 1)
        if query_string == "":
            raise response_code.ParamERR(errmsg="query_string is provided")
        elif mode not in ["all", "video", "series", "user", "document"]:
            raise response_code.ParamERR(
                errmsg="type must be all or video or series or user or document")
        elif video_ids == "":
            video_ids = []
        try:
            max_size = int(max_size)
            page = int(page)
        except Exception as e:
            raise response_code.ParamERR(
                errmsg="max_size or page type incorrect")
        current_app.logger.info("开始")
        ret = run_ai.global_play_video(query_string, mode, video_ids, max_size,
                                       page)
        current_app.logger.info("结束")
        user = g.user
        if user:
            user_id = user["_id"]
        else:
            user_id = "1"
        try:
            mongo.db.search_history.insert_one(
                {"_id": create_uuid(), "key": query_string, "user_id": user_id,
                 "time": time.time(), "type": "global"})
        except Exception as e:
            raise response_code.ParamERR(errmsg="{}".format(e))
        response = set_resjson(res_array=ret)
        return response

    def func_local_search(self):
        """
        局部搜索视频
        :return:
        """
        user = g.user
        if not user:
            raise response_code.UserERR(errmsg='用户未登录')
        query_string = self.extra_data.get('query_string', "")
        video_id = self.extra_data.get('video_id', "")
        if query_string == "" or video_id == "":
            response = set_resjson(err=-1,
                                   errmsg="[ query_string, video_id] must be provided ！")

        elif type(video_id) is not list:
            response = set_resjson(err=-1, errmsg="video_id type must array")
        else:
            ret = run_ai.local_play_video(query_string, video_id)
            response = set_resjson(res_array=ret)
        try:
            mongo.db.search_history.insert_one(
                {"_id": create_uuid(), "key": query_string,
                 "user_id": user["_id"],
                 "time": time.time(), "type": "local"})
        except Exception as e:
            raise response_code.ParamERR(errmsg="{}".format(e))

        return response

    def func_breakpoint(self):
        """
        视频断点续传
        """
        user = g.user
        if not user:
            raise response_code.UserERR(errmsg='用户未登录')
        task = self.extra_data.get('task_id', "")
        if task == "":
            raise response_code.ParamERR(errmsg="[ task ] must be provided ！")
        folder_file_list = os.listdir('static/upload')
        file_list = [file for file in folder_file_list if
                     re.match(r'{}'.format(task), file)]
        return set_resjson(res_array=file_list)

    def func_generate_subtitle(self):
        """
        生成字幕
        :return:
        """
        user = g.user
        if not user:
            raise response_code.UserERR(errmsg='用户未登录')
        lang = self.extra_data.get('lang')
        task_id = self.extra_data.get('task_id')

        if not task_id:
            resp = set_resjson(err=-1, errmsg='[ task_id ] must be provided ！')
        else:
            try:
                video_info = mongo.db.video.find_one({'_id': task_id})
            except Exception as e:
                raise response_code.DatabaseERR(errmsg="{}".format(e))
            if not video_info:
                resp = set_resjson(err=-1, errmsg='_id is Incorrect!')
            else:
                if 'subtitling' in video_info:
                    resp = set_resjson(err=-1,
                                       errmsg='Subtitles have been created or are being created. Please be patient')
                elif lang not in ['cn', 'en']:
                    resp = set_resjson(err=-1, errmsg='lang is cn or en')

                else:
                    thread = Thread(target=generate_subtitle1,
                                    args=(task_id, lang))
                    thread.start()
                    try:
                        mongo.db.video.update_one({'_id': task_id},
                                                  {"$set": {"subtitling": 0}})
                    except Exception as e:
                        raise response_code.DatabaseERR(errmsg="{}".format(e))
                    resp = set_resjson(
                        errmsg='Please wait. Generating subtitles!')

        return resp

    def func_query_subtitle(self):
        """
        查询字幕
        :return:
        """
        user = g.user
        if not user:
            raise response_code.UserERR(errmsg='用户未登录')
        task_id = self.extra_data.get('task_id', '')
        if task_id == '':
            resp = set_resjson(err=-1, errmsg='[ task_id ] must be provided ！')
        else:
            try:
                video_info = mongo.db.video.find_one({'_id': task_id})
            except Exception as e:
                raise response_code.DatabaseERR(errmsg="{}".format(e))
            if not video_info:
                resp = set_resjson(err=-1, errmsg='_id is Incorrect!')
            else:
                try:
                    video_info = mongo.db.video.find_one({"_id": task_id},
                                                         {'video_path': 1,
                                                          'subtitling': 1,
                                                          "_id": 0})
                except Exception as e:
                    raise response_code.DatabaseERR(errmsg="{}".format(e))
                if 'subtitling' in video_info:
                    sub_info = video_info.get('subtitling')
                    if sub_info == 0:
                        resp = set_resjson(
                            errmsg="Subtitles are being generated, please wait")
                    else:
                        resp = set_resjson(res_array=[video_info])
                else:
                    resp = set_resjson(
                        errmsg='Subtitle generation failed or not generated. Please regenerate the subtitle')
        return resp

    def func_update_subtitle(self):
        """
        更新字幕
        :return:
        """
        user = g.user
        if not user:
            raise response_code.UserERR(errmsg='用户未登录')
        style = self.extra_data.get('style')
        task_id = self.extra_data.get('task_id')
        subtitling = self.extra_data.get('subtitling', '')
        if not task_id:
            resp = set_resjson(err=-1, errmsg='[ task_id ] must be provided ！')
        elif subtitling == "" or type(subtitling) != list:
            resp = set_resjson(err=-1,
                               errmsg='subtitling can not be empty, Its type is list')
        else:
            try:
                video_info = mongo.db.video.find_one(
                    {'_id': task_id, "user_id": user["_id"]})
            except Exception as e:
                raise response_code.DatabaseERR(errmsg="{}".format(e))
            if not video_info:
                resp = set_resjson(err=-1, errmsg='_id is Incorrect!')
            else:
                try:
                    run_ai.update_subtitle(task_id, subtitling, style)
                    vtt = mongo.db.video.find_one({"_id": task_id}, {"vtt_path":1, "_id": 0})
                except Exception as e:
                    raise response_code.ParamERR(errmsg='{}'.format(e))
                resp = set_resjson(res_array=vtt)
        return resp

    def func_download(self):
        """
        导出视频
        """
        user = g.user
        if not user:
            raise response_code.UserERR(errmsg='用户未登录')

        task_id = self.extra_data.get('task_id', '')
        if task_id == '':
            raise response_code.ParamERR(errmsg="task_id not can be empty")

        try:
            video_info = mongo.db.video.find_one({"_id": task_id})
        except Exception as e:
            raise response_code.ParamERR(errmsg="{}".format(e))
        sub_path = video_info.get('ass_path', '')

        if sub_path == '':
            raise response_code.ParamERR(errmsg="请先生成字幕")
        input_path = video_info.get('video_path')
        output_path = "static/synthetic/" + input_path.split('/')[-1]
        compress = "ffmpeg -i {} -vf subtitles={} -y {}".format(input_path,
                                                                sub_path,
                                                                output_path)
        try:
            is_run = os.system(compress)
        except Exception as e:
            raise response_code.RoleERR(errmsg="视频合并失败 {}".format(e))
        if is_run != 0:
            raise response_code.RoleERR(errmsg="视频合并失败")
        editor_video_md5 = video_to_md5(output_path)
        editor_video_name = "static/synthetic/" + editor_video_md5 + "." + \
                            input_path.split('.')[-1]
        os.rename(output_path, editor_video_name)
        response = upload_video(editor_video_name)
        os.remove(editor_video_name)
        video_path = response.pop("video_url")
        video_update_info = {'composite_video_message': response,
                             "composite_video": video_path}
        try:
            mongo.db.video.update_one({"_id": task_id},
                                      {"$set": video_update_info})
        except Exception as e:
            raise response_code.DatabaseERR(errmsg="{}".format(e))

        back_info = {"video_editor_path": video_path,
                     "video_path": video_path,
                     "image_path": video_info.pop("image_path")
                     }
        return set_resjson(res_array=[back_info])

    def func_verify(self):
        """
        验证服务器是否有此视频
        """
        user = g.user
        if not user:
            raise response_code.UserERR(errmsg='用户未登录')
        md5_token = self.extra_data.get('token', "")
        if md5_token == '':
            raise response_code.ParamERR(
                errmsg="[ md5_token ] must be provided ！")
        try:
            mongo_md5_token = mongo.db.video.find_one({'_id': str(md5_token)},
                                                      {'video_path': 1,
                                                       '_id': 0})
        except Exception as e:
            raise response_code.DatabaseERR(errmsg="{}".format(e))
        if mongo_md5_token:
            resp = set_resjson(err=-1,
                               errmsg="This videos is already available!")
        else:
            resp = set_resjson(err=0, errmsg='This videos can be uploaded!')
        return resp

    def func_generate_thumbnail(self):
        """
        生成缩略图
        """
        user = g.user
        if not user:
            raise response_code.UserERR(errmsg='用户未登录')
        video_id = self.extra_data.get('video_id', '')
        try:
            video_info = mongo.db.video.find_one({'_id': video_id})
        except Exception as e:
            raise response_code.DatabaseERR(errmsg="{}".format(e))
        input_path = video_info.get('video_path')
        height = 48
        out_path = 'static/picture/{}'.format(video_id)
        if not os.path.exists(out_path):
            os.makedirs(out_path)
            from main import app
            with app.app_context():
                video_resolution = get_resolution2(input_path, height)
                video_to_image(input_path, out_path, video_resolution)

        file_list = ['static/picture/{}/{}'.format(video_id, filename) for
                     filename in
                     os.listdir('static/picture/{}/'.format(video_id))]
        return set_resjson(res_array=sorted(file_list))

    def func_video_play(self):
        """
        视频播放
        """
        res_data = []
        user = g.user
        video_id = self.extra_data.get('video_id', '')
        if video_id == '':
            raise response_code.ParamERR(errmsg="[video_id] must be provided")
        tool = mongo.db.tool.find_one({'type': 'category'}).get("data")
        video = mongo.db.video.find_one({'_id': video_id})
        video_user_info = mongo.db.user.find_one({"_id": video["user_id"]},
                                                 {"name": 1, "_id": 1,
                                                  "headshot": 1})
        video_counts = mongo.db.video.find(
            {"user_id": video_user_info["_id"], "state": 2}).count()
        fans_counts = mongo.db.subscription.find(
            {"relation_id": video_user_info["_id"], "state": 0}).count()
        like_counts = mongo.db.like.find(
            {"relation_id": video_id, "type": "video"}).count()
        collection_counts = mongo.db.collection.find(
            {"video_id": video_id}).count()
        author_id = video['user_id']
        view_counts = 0 if 'view_counts' not in list(video.keys()) else video[
            'view_counts']
        category_list = []
        for category in video['category']:
            for data_category in tool:
                if category == data_category["id"]:
                    category_list.append(data_category["name"])
        data_dict = {'video_id': video_id, 'video_path': video['video_path'],
                     'audio_path': video['audio_path'],
                     'lang': video['lang'], 'vtt_path': video['vtt_path'],
                     'upload_time': video['upload_time'],
                     'title': video['title'], 'user_id': video_user_info["_id"],
                     'user_name': video_user_info['name'],
                     'headshot': video_user_info['headshot'],
                     'category': category_list, 'fans_counts': fans_counts,
                     'description': video['description'],
                     'image_path': video['image_path'],
                     'view_counts': video["view_counts"],
                     'like_counts': like_counts,
                     'collection_counts': collection_counts,
                     "is_like": 0, "video_counts": video_counts,
                     "is_collect": 0,
                     "is_subscribe": 0}

        if user:
            user_id = user["_id"]
            like = mongo.db.like.find_one(
                {'relation_id': video_id, 'type': 'video', 'user_id': user_id})
            collection = mongo.db.collection.find_one(
                {'relation_id': video_id, 'type': 'video', 'user_id': user_id,
                 "state": 0})
            subscription = mongo.db.subscription.find_one(
                {'relation_id': author_id, 'type': 'author',
                 'user_id': user_id, "state": 0})
            data_dict['is_like'] = 1 if like else 0
            data_dict['is_collect'] = 1 if collection else 0
            data_dict['is_subscribe'] = 1 if subscription else 0
        res_data.append(data_dict)
        mongo.db.video.update_one({'_id': video_id},
                                  {'$set': {'view_counts': view_counts + 1}})
        return set_resjson(res_array=res_data)

    @staticmethod
    def func_video_list(self):
        """
        获取视频列表
        """
        try:
            video_cursor = mongo.db.video.find({"state": 2},
                                               {"video_id": 1, "video_path": 1,
                                                "upload_time": 1, "title": 1,
                                                "image_path": 1})
        except Exception as e:
            raise response_code.DatabaseERR(errmsg="{}".format(e))
        res_list = [video for video in video_cursor]
        return set_resjson(res_array=res_list)

    def func_get_related_video(self):
        """
        获取相关视频
        """
        video_id = self.extra_data.get("video_id", "")
        related_type = self.extra_data.get("related_type", "")
        max_size = self.extra_data.get("max_size", 10)
        page = self.extra_data.get("page", 1)
        video_dict = {}
        series_dict = {}
        video_list = []
        res_list = []
        if video_id == "" or related_type == "":
            raise response_code.ParamERR(
                errmsg="video_id related_type must be provide")
        elif related_type not in ["series", "recommend"]:
            raise response_code.ParamERR(
                errmsg="related_type must be series or recommend")
        try:
            max_size = int(max_size)
            page = int(page)
        except Exception as e:
            raise response_code.ParamERR(
                errmsg="max_size or page type is incorrect")
        try:
            video_info = mongo.db.video.find_one({"_id": video_id, "state": 2})
        except Exception as e:
            raise response_code.DatabaseERR(errmsg="{}".format(e))
        if not video_info:
            raise response_code.ParamERR(errmsg="video_id 不存在")
        elif related_type == "series":
            series_id = video_info.get("series", "")
            if not series_id:
                raise response_code.ParamERR(errmsg="There's no video")

            # related_cursor = mongo.db.video.find(
            #     {"series": series_id, "state": 2}).sort(
            #     "view_counts", -1).limit(max_size).skip(max_size * (page - 1))
            related_cursor = mongo.db.video.find(
                {"series": series_id, "state": 2}).sort(
                [("number", 1), ("upload_time", -1)]).limit(max_size).skip(
                max_size * (page - 1))
            series_info = mongo.db.series.find_one({"_id": series_id})
            for video in related_cursor:
                if video["_id"] == video_id:
                    continue
                video_dict["video_id"] = video["_id"]
                video_dict["video_title"] = video["title"]
                video_dict["video_time"] = video["video_time"]
                video_dict["upload_time"] = video["upload_time"]
                video_dict["image_path"] = video["image_path"]
                video_dict["view_counts"] = video["view_counts"]

                video_list.append(deepcopy(video_dict))

            series_dict["series_id"] = series_info["_id"]
            series_dict["series_title"] = series_info["title"]
            series_dict["video_counts"] = len(video_list)
            series_dict["video_data"] = video_list
            res_list.append(series_dict)
        else:
            video_cursor = mongo.db.video.find({"state": 2}).sort("view_counts",
                                                                  -1).limit(
                max_size).skip(max_size * (page - 1))
            for video in video_cursor:
                video_dict["video_id"] = video["_id"]
                video_dict["video_title"] = video["title"]
                video_dict["video_time"] = video["video_time"]
                video_dict["upload_time"] = video["upload_time"]
                video_dict["image_path"] = video["image_path"]
                video_dict["view_counts"] = video["view_counts"]
                res_list.append(deepcopy(video_dict))
        return set_resjson(res_array=res_list)

    # def func_hot_video(self):
    #     """
    #     热门视频
    #     @return:
    #     """
    #     max_size = self.extra_data.get("max_size", 10)
    #     page = self.extra_data.get("page", 1)
    #     res_dict = {}
    #     res_list = []
    #     try:
    #         max_size = int(max_size)
    #         page = int(page)
    #     except Exception as e:
    #         raise response_code.ParamERR(errmsg="max_size or page type error")
    #     if max_size > 50:
    #         raise response_code.ParamERR(errmsg="max_size No more than fifty")
    #     try:
    #         video_cursor = mongo.db.video.find({"state": 2}).sort("view_counts",
    #                                                               -1).limit(
    #             max_size).skip(
    #             max_size * (page - 1))
    #         for video in video_cursor:
    #             likes = mongo.db.like.find(
    #                 {"relation_id": video.get("_id"), "type": "video"}).count()
    #             comments = mongo.db.comment.find(
    #                 {"video_id": video.get("_id")}).count()
    #             user_info = mongo.db.user.find_one(
    #                 {"_id": video.get("user_id")})
    #             tool = mongo.db.tool.find_one({'type': 'category'})
    #             category_list = []
    #             for category in video['category']:
    #                 category_list.append(tool["data"].get(category))
    #             res_dict["video_id"] = video["_id"]
    #             res_dict["image_path"] = video["image_path"]
    #             res_dict["title"] = video["title"]
    #             res_dict["category"] = category_list
    #             res_dict["update_time"] = video["upload_time"]
    #             res_dict["user_id"] = video["user_id"]
    #             res_dict["view_counts"] = video["view_counts"]
    #             res_dict["user_name"] = user_info["name"]
    #             res_dict["head_shot"] = user_info["headshot"]
    #             res_dict["comment_counts"] = comments
    #             res_dict["like_counts"] = likes
    #             res_list.append(deepcopy(res_dict))
    #     except Exception as e:
    #         raise response_code.DatabaseERR(errmsg="{}".format(e))
    #     return set_resjson(res_array=res_list)

    def func_hot_video(self):
        """
        热门视频
        @return:
        """
        max_size = self.extra_data.get("max_size", 10)
        page = self.extra_data.get("page", 1)
        res_dict = {}
        res_list = []
        series_dict = {}
        try:
            max_size = int(max_size)
            page = int(page)
        except Exception as e:
            raise response_code.ParamERR(errmsg="max_size or page type error")
        if max_size > 50:
            raise response_code.ParamERR(errmsg="max_size No more than fifty")
        try:
            video_cursor = mongo.db.video.find({"state": 2}).sort("view_counts",
                                                                  -1).limit(
                max_size).skip(
                max_size * (page - 1))
            tool = mongo.db.tool.find_one({'type': 'category'}).get("data")
            for video in video_cursor:
                likes = mongo.db.like.find(
                    {"relation_id": video.get("_id"), "type": "video"}).count()
                comments = mongo.db.comment.find(
                    {"video_id": video.get("_id")}).count()
                user_info = mongo.db.user.find_one(
                    {"_id": video.get("user_id")})

                category_list = []
                for category in video['category']:
                    for data_category in tool:
                        if category == data_category["id"]:
                            category_list.append(data_category["name"])
                series_id = video.get("series", None)
                a = 0
                if series_id:
                    for i in res_list:
                        if series_id == i.get("series_id", None):
                            a = 1
                            break
                    if a == 1:
                        continue

                    view_counts = 0
                    # like_counts = 0
                    # comment_counts = 0
                    video_id_list = []
                    series_video_cursor = mongo.db.video.find(
                        {"series": series_id, "state": 2})
                    for video in series_video_cursor:
                        video_id_list.append(video["_id"])
                        # likes = mongo.db.like.find(
                        #     {"relation_id": video.get("_id"),
                        #      "type": "video"}).count()
                        # comments = mongo.db.comment.find(
                        #     {"video_id": video.get("_id")}).count()
                        view_counts += video["view_counts"]
                        # like_counts += likes
                        # comment_counts += comments
                    series_info = mongo.db.series.find_one({"_id": series_id})
                    series_user_info = mongo.db.user.find_one(
                        {"_id": series_info["user_id"]})
                    series_dict["series_id"] = series_info["_id"]
                    series_dict["type"] = 'series'
                    series_dict["image_path"] = series_info["image_path"]
                    series_dict["title"] = series_info["title"]
                    series_dict["time"] = series_info["time"]
                    series_dict["user_id"] = series_info["user_id"]
                    series_dict["user_name"] = series_user_info["name"]
                    series_dict["head_shot"] = series_user_info["headshot"]
                    series_dict["view_counts"] = view_counts
                    like_counts = mongo.db.like.find(
                        {"relation_id": {"$in": video_id_list}}).count()
                    comment_counts = mongo.db.comment.find(
                        {"state": 2,
                         "video_id": {"$in": video_id_list}}).count()
                    series_dict["comment_counts"] = comment_counts
                    series_dict["like_counts"] = like_counts
                    res_list.append(deepcopy(series_dict))
                else:
                    res_dict["video_id"] = video["_id"]
                    res_dict["type"] = "video"
                    res_dict["image_path"] = video["image_path"]
                    res_dict["title"] = video["title"]
                    res_dict["category"] = category_list
                    res_dict["update_time"] = video["upload_time"]
                    res_dict["user_id"] = video["user_id"]
                    res_dict["view_counts"] = video["view_counts"]
                    res_dict["user_name"] = user_info["name"]
                    res_dict["head_shot"] = user_info["headshot"]
                    res_dict["comment_counts"] = comments
                    res_dict["like_counts"] = likes
                    res_list.append(deepcopy(res_dict))
        except Exception as e:
            traceback.print_exc()
            raise response_code.DatabaseERR(errmsg="{}".format(e))
        return set_resjson(res_array=res_list)

    def func_hot_author(self):
        """
        热门作者
        @return:
        """
        user = g.user
        max_size = self.extra_data.get("max_size", 10)
        page = self.extra_data.get("page", 1)
        video_size = self.extra_data.get("video_size", 4)
        res_dict = {}
        res_list = []
        try:
            max_size = int(max_size)
            page = int(page)
            video_size = int(video_size)
        except Exception as e:
            raise response_code.ParamERR(errmsg="max_size or page type error")
        if max_size > 50 or video_size > 10:
            raise response_code.ParamERR(
                errmsg="max_size No more than fifty or video_size No more than ten")
        try:
            relation_id_cursor = mongo.db.subscription.find({"type": "author"},
                                                            {"_id": 0,
                                                             "relation_id": 1}).limit(
                max_size).skip(max_size*(page - 1))
            relation_id_list = [user_id.get("relation_id") for user_id in
                                relation_id_cursor]
            relation_sort = sorted(Counter(relation_id_list).items(),
                                   key=lambda x: x[1], reverse=True)
            for relation_id_set in relation_sort:
                author_info = mongo.db.user.find_one(
                    {"_id": relation_id_set[0]},
                    {"name": 1, "headshot": 1, "introduction": 1,
                     "background": 1})
                subscribe = None
                if user:
                    subscribe = mongo.db.subscription.find_one(
                        {"user_id": user["_id"],
                         "relation_id": author_info["_id"]})
                res_dict["user_id"] = author_info["_id"]
                res_dict["is_subscribe"] = 1 if subscribe else 0
                res_dict["user_name"] = author_info["name"]
                res_dict["headshot"] = author_info["headshot"]
                res_dict["background"] = author_info["background"]
                res_dict["introduction"] = author_info["introduction"]
                res_dict["fans_counts"] = relation_id_set[1]
                video_cursor = mongo.db.video.find(
                    {"user_id": relation_id_set[0], "state": 2}).sort(
                    "view_counts", -1).limit(video_size)
                video_list = []
                for video in video_cursor:
                    video_dict = {}
                    tool = mongo.db.tool.find_one({'type': 'category'}).get("data")
                    category_list = []
                    for category in video['category']:
                        for data_category in tool:
                            if category == data_category["id"]:
                                category_list.append(data_category["name"])
                    like_counts = mongo.db.like.find(
                        {"relation_id": video["_id"], "type": "video"}).count()
                    comment_counts = mongo.db.comment.find(
                        {"video_id": video["_id"]}).count()
                    video_dict["video_id"] = video["_id"]
                    video_dict["image_path"] = video["image_path"]
                    video_dict["title"] = video["title"]
                    video_dict["upload_time"] = video["upload_time"]
                    video_dict["view_counts"] = video["view_counts"]
                    video_dict["category"] = category_list
                    video_dict["comment_counts"] = comment_counts
                    video_dict["like_counts"] = like_counts
                    video_list.append(video_dict)
                res_dict["video_data"] = video_list
                res_list.append(deepcopy(res_dict))
        except Exception as e:
            raise response_code.DatabaseERR(errmsg="{}".format(e))

        return set_resjson(res_array=res_list)

    def func_get_video(self):
        """
        查看作品
        @return:
        """
        user = g.user
        res_dict = {}
        res_list = []
        if not user:
            raise response_code.UserERR(errmsg='用户未登录')
        get_type = self.extra_data.get("type", "")
        if get_type not in ["video", "series"]:
            raise response_code.ParamERR(errmsg="type must be video or series")
        elif get_type == "video":
            video_cursor = mongo.db.video.find(
                {"user_id": user["_id"], "series": {"$exists": False}})
            for video in video_cursor:
                like_counts = mongo.db.like.find(
                    {"relation_id": video["_id"], "type": "video"}).count()
                comment_counts = mongo.db.comment.find(
                    {"video_id": video.get("_id")}).count()
                res_dict["video_id"] = video["_id"]
                res_dict["title"] = video["title"]
                res_dict["upload_time"] = video["upload_time"]
                res_dict["state"] = video["state"]
                res_dict["image_path"] = video["image_path"]
                res_dict["video_time"] = video["video_time"]
                res_dict["view_counts"] = video["view_counts"]
                res_dict["like_counts"] = like_counts
                res_dict["comment_counts"] = comment_counts
                res_list.append(deepcopy(res_dict))
        elif get_type == "series":
            view_counts = 0
            like_counts = 0
            comment_counts = 0
            series_cursor = mongo.db.series.find(
                {"user_id": user["_id"]})
            for series in series_cursor:
                res_dict["series_id"] = series["_id"]
                res_dict["series_title"] = series["title"]
                res_dict["update_time"] = series["time"]
                res_dict["image_path"] = series["image_path"]
                res_dict["description"] = series["description"]
                video_cursor = mongo.db.video.find(
                    {"series": series["_id"]}).sort(
                    [("number", 1), ("upload_time", -1)])
                video_list = []
                for video in video_cursor:
                    video_dict = {}
                    view_counts += video["view_counts"]
                    likes = mongo.db.like.find(
                        {"relation_id": video["_id"]}).count()
                    comments = mongo.db.comment.find(
                        {"video_id": video["_id"]}).count()
                    like_counts += likes
                    comment_counts += comments
                    video_dict["video_id"] = video["_id"]
                    video_dict["video_title"] = video["title"]
                    video_dict["video_time"] = video["video_time"]
                    video_dict["image_path"] = video["image_path"]
                    video_dict["view_counts"] = video["view_counts"]
                    video_dict["like_counts"] = likes
                    video_dict["comment_counts"] = comments
                    video_list.append(deepcopy(video_dict))
                res_dict["view_counts"] = view_counts
                res_dict["video_counts"] = series.get("video_counts",
                                                      None) if series.get(
                    "video_counts", None) else mongo.db.video.find(
                    {"series": series["_id"]}).count()
                res_dict["like_counts"] = like_counts
                res_dict["comment_counts"] = comment_counts
                res_dict["video_data"] = video_list
                res_list.append(deepcopy(res_dict))
        return set_resjson(res_array=res_list)

    def func_delete_video(self):
        """
        删除视频
        @return:
        """
        user = g.user
        if not user:
            raise response_code.UserERR(errmsg='用户未登录')
        res_list= []
        video_id_list = self.extra_data.get("video_id", "")
        if video_id_list == "":
            raise response_code.ParamERR(errmsg="[ video_id ] is must provided")
        for video_id in video_id_list:
            video_info = mongo.db.video.find_one(
                {"_id": video_id, "user_id": user["_id"]})
            document_info = mongo.db.document.find_one({"video_id": video_id})
            if not video_info:
                res = {video_id: "此视频不存在 "}
                res_list.append(res)
                continue
            if "series" in video_info.keys():
                series_info = mongo.db.series.find_one(
                    {"_id": video_info["series"]})
                series_video_count = series_info.get("video_counts",
                                                     None) if series_info.get(
                    "video_counts", None) else mongo.db.video.find(
                    {"series": series_info["_id"]}).count() - 1
                if series_video_count <= 0:
                    mongo.db.series.delete_one(series_info)
                else:
                    mongo.db.series.update(series_info, {
                        "$set": {"video_counts": series_video_count}})
            video_info["data_type"] = "video"
            if document_info:
                document_info["data_type"] = "document"
                mongo.db.rubbish.insert_many([video_info, document_info])
                mongo.db.video.delete_one(video_info)
                mongo.db.document.delete_one(document_info)
            else:
                mongo.db.rubbish.insert_one(video_info)
                mongo.db.video.delete_one(video_info)
            if os.path.exists(video_info["image_path"]):
                os.remove(video_info["image_path"])
        return set_resjson(res_array=res_list)

    def func_movie_video(self):
        """
        移动视频
        @return:
        """
        user = g.user
        if not user:
            raise response_code.UserERR(errmsg='用户未登录')
        res_list = []
        video_id_list = self.extra_data.get("video_id")
        series_id = self.extra_data.get("series_id")
        if not all([video_id_list, series_id]):
            raise response_code.ParamERR(errmsg="Parameter is not complete!")
        elif type(video_id_list) != list or len(video_id_list) <= 0:
            raise response_code.ParamERR(errmsg="video_id type is a list")
        series_info = mongo.db.series.find_one(
            {"_id": series_id, "user_id": user["_id"]})
        if not series_info:
            raise response_code.ParamERR(errmsg="series_id is incorrect")
        video_list = []
        for video_id in set(video_id_list):
            video_info = mongo.db.video.find_one(
                {"user_id": user["_id"], "_id": video_id})
            if video_info:
                video_list.append(video_id)
            else:
                resp = {video_id: "This ID is incorrect"}
                res_list.append(deepcopy(resp))
            mongo.db.video.update({"_id": {"$in": video_list}},
                                  {"$set": {"series": series_id}})
            series_video = mongo.db.video.find(
                {"series": series_id, "state": 2})
            latest_time = \
            [i for i in series_video.sort("upload_time", -1).skip(0).limit(1)][
                0].get("upload_time")
            mongo.db.series.update_one({"_id": series_id}, {"$set": {
                "video_counts": series_video.count(), "time": latest_time}})
        return set_resjson(res_array=res_list)

    def func_sort_video(self):
        """
        系列视频排序：
        @return:
        """
        user = g.user
        if not user:
            raise response_code.UserERR(errmsg='用户未登录')
        video_id_list = self.extra_data.get("video_id", "")
        res_list = []
        if type(video_id_list) != list or len(video_id_list) <= 0:
            raise response_code.ParamERR(errmsg="video_id type is a list")
        id_to_heavy = []
        verify_video = []
        [id_to_heavy.append(i) for i in video_id_list if i not in id_to_heavy]
        for video_id in id_to_heavy:
            video_info = mongo.db.video.find_one(
                {"user_id": user["_id"], "_id": video_id}, {"_id": 1})
            if not video_info:
                resp = {video_id: "This ID is incorrect"}
                res_list.append(deepcopy(resp))
            else:
                verify_video.append(deepcopy(video_id))
        for num, video in enumerate(verify_video, 1):
            mongo.db.video.update_one({"_id": video}, {"$set": {"number": num}})
        return set_resjson(res_array=res_list)

    def func_category_information(self):
        """
        频道信息
        @return:
        """
        category = self.extra_data.get("category", "")
        res_list = []
        video_dict = {}
        series_dict = {}
        if category == "":
            raise response_code.ParamERR(
                errmsg="The classification information cannot be empty")
        tool = mongo.db.tool.find_one({"type": "category"}).get("data")
        if category not in [i["id"] for i in tool]:
            raise response_code.ParamERR(errmsg="Tag information error")
        series_distinct_list = mongo.db.video.distinct(
            "series", {"state": 2, "category": {"$in": [category]}})
        video_cursor = mongo.db.video.find(
            {"series": {"$exists": False}, "state": 2,
             "category": {"$in": [category]}})
        for video in video_cursor:
            category_list = []
            for category in video['category']:
                for data_category in tool:
                    if category == data_category["id"]:
                        category_list.append(data_category["name"])
            user_info = mongo.db.user.find_one({"_id": video["user_id"]})
            video_dict["type"] = "video"
            video_dict["video_id"] = video["_id"]
            video_dict["image_path"] = video["image_path"]
            video_dict["title"] = video["title"]
            video_dict["category"] = category_list
            video_dict["view_counts"] = video["view_counts"]
            video_dict["upload_time"] = video["upload_time"]
            video_dict["video_time"] = video["video_time"]
            video_dict["user_id"] = user_info["_id"]
            video_dict["user_name"] = user_info["name"]
            video_dict["headshot"] = user_info["headshot"]
            video_dict["view_counts"] = video["view_counts"]
            video_dict["like_counts"] = mongo.db.like.find(
                {"relation_id": video["_id"]}).count()
            video_dict["comment_counts"] = mongo.db.comment.find(
                {"state": 2, "video_id": video["_id"]}).count()
            res_list.append(deepcopy(video_dict))
        for series_id in series_distinct_list:
            series_info = mongo.db.series.find_one({"_id": series_id})
            series_category_list = []
            for category in series_info['category']:
                for data_category in tool:
                    if category == data_category["id"]:
                        series_category_list.append(data_category["name"])
            series_dict["type"] = "series"
            series_dict["series_id"] = series_info["_id"]
            series_dict["image_path"] = series_info["image_path"]
            series_dict["title"] = series_info["title"]
            series_dict["category"] = series_category_list
            series_dict["update_time"] = series_info["time"]
            series_user_info = mongo.db.user.find_one(
                {"_id": series_info["user_id"]})
            series_dict["user_id"] = series_user_info["_id"]
            series_dict["user_name"] = series_user_info["name"]
            series_dict["headshot"] = series_user_info["headshot"]
            view_counts = 0
            video_cursor_series = mongo.db.video.find(
                {"state": 2, "series": series_info["_id"]})
            video_id_list = []
            for video in video_cursor_series:
                view_counts += video["view_counts"]
                video_id_list.append(video["_id"])
            like_counts = mongo.db.like.find(
                {"relation_id": {"$in": video_id_list}}).count()
            comment_counts = mongo.db.comment.find(
                {"state": 2,
                 "video_id": {"$in": video_id_list}}).count()
            series_dict["view_counts"] = view_counts
            series_dict["like_counts"] = like_counts
            series_dict["comment_counts"] = comment_counts
            res_list.append(deepcopy(series_dict))
        return set_resjson(res_array=res_list)

    def func_check(self):
        """
        视频审核
        """
        user = g.user
        if not user:
            raise response_code.UserERR(errmsg='用户未登录')
        task_id = self.extra_data.get('task_id')
        title = self.extra_data.get('title')
        description_title = self.extra_data.get('description_title')
        description = self.extra_data.get('description')
        series_image_path = self.extra_data.get('series_image_path', None)
        image_path = self.extra_data.get('image_path', None)
        # category = self.extra_data.get('category')
        series_title = self.extra_data.get('series_title')
        document = self.extra_data.get('document')

        if not all([task_id, description]):
            raise response_code.ParamERR(
                errmsg="[task_id, description, category] must be provided ！")
        # elif type(category) != list or len(category) < 1 or len(category) > 4:
        #     raise response_code.ParamERR(
        #         errmsg="category type is list, Greater than 0 is less than 4")
        must_fields = ["subtitling", "char_id_to_time", "full_cn_str"]
        try:
            video_info = mongo.db.video.find_one(
                {"_id": task_id, "user_id": user["_id"]})
            # category_data = mongo.db.tool.find_one({"type": "category"}).get("data")
            # category_list = [category["id"] for category in category_data]
        except Exception as e:
            raise response_code.DatabaseERR(errmsg="{}".format(e))
        if not video_info:
            raise response_code.ParamERR(errmsg='task_id 不存在')
        elif video_info["state"] == 1:
            raise response_code.ReqERR(errmsg="正在审核请耐心等待")
        elif not (set(video_info.keys()) > set(must_fields)):
            raise response_code.ParamERR(errmsg="请先生成字幕")

        update_video_info = {"description": description, "category": [],
                             "image_path": image_path if image_path else
                             video_info["image_path"],
                             "state": 2 if 11 in user.get("authority",
                                                          []) else 1,
                             "title": title if title else video_info["title"]}

        if series_title:
            try:
                series_info = mongo.db.series.find_one(
                    {"user_id": user["_id"], "title": series_title})
                if series_info:
                    mongo.db.series.update_one(
                        {series_info, {"$set": {
                            "title": series_title if series_title else
                            series_info['title'],
                            "description": description_title if description else
                            series_info["description"],
                            "image_path": series_image_path if series_image_path else
                            video_info["image_path"], "category": [],
                            "user_id": user["_id"], "time": time.time()}}})
                    update_video_info["series"] = series_info["_id"]
                else:
                    _id = create_uuid()
                    mongo.db.audit.insert_one(
                        {"_id": _id, "title": series_title, "type": "series",
                         "description": description_title,
                         "image_path": series_image_path if series_image_path else
                         video_info["image_path"], "category": [],
                         "user_id": user["_id"], "time": time.time()})
                    update_video_info["series"] = _id
            except Exception as e:
                raise response_code.DatabaseERR(errmsg="{}".format(e))
        try:
            mongo.db.video.update_one(video_info, {"$set": update_video_info})
        except Exception as e:
            raise response_code.DatabaseERR(errmsg='{}'.format(e))
        res_list = []
        if document:
            if type(document) != list:
                raise response_code.ParamERR(errmsg="document type is list")
            elif len(document) >= 1:
                for dmt in document:
                    file_name = dmt.get("file_name")
                    file_path = dmt.get("file_path")
                    if not all([file_name, file_path]):
                        res_list.append(deepcopy({dmt: "参数不全"}))
                    else:
                        if 12 in user.get("authority", []):
                            flag = edit_document(create_uuid(), file_name,
                                                 file_path,
                                                 image_path, 0, task_id,
                                                 user["_id"])
                        else:
                            mongo.db.audit.insert_one(
                                {"_id": create_uuid(), "file_name": file_name,
                                 "video_id": task_id, "user_id": user["_id"],
                                 "data_type": "document", "price": 0})
        return set_resjson()

    def func_verify_title(self):
        """
        视频标题验重
        @return:
        """
        user = g.user
        if not user:
            raise response_code.UserERR(errmsg='用户未登录')
        title = self.extra_data.get('title', "")
        if title == "":
            raise response_code.ParamERR(errmsg="视频标题不能为空")
        title = mongo.db.video.find_one(
            {"user_id": user["_id"], "title": title})
        if title:
            return set_resjson(err=-1, errmsg="This title already exists!")
        else:
            return set_resjson(err=0)

    def func_update_subtitle_again(self):
        """
        二次编辑字幕
        @return:
        """
        user = g.user
        if not user:
            raise response_code.UserERR(errmsg='用户未登录')
        res_dict = {}
        video_id = self.extra_data.get("video_id", "")
        if video_id == "":
            raise response_code.ParamERR(errmsg="video_id must be provide")
        video_info = mongo.db.video.find_one(
            {"_id": video_id, "user_id": user["_id"]})
        if not video_info:
            raise response_code.ParamERR(errmsg="video_id is incorrect")
        category_list = []
        for category in video_info.get("category", []):
            for tag in mongo.db.tool.find_one({"type": "category"}).get("data"):
                if category == tag["id"]:
                    category_list.append(tag["name"])
        res_dict["video_id"] = video_id
        res_dict["video_path"] = video_info["video_path"]
        res_dict["image_path"] = video_info["image_path"]
        res_dict["title"] = video_info["title"]
        res_dict["category"] = category_list
        res_dict["description"] = video_info.get("description", "")
        res_dict["subtitle"] = video_info["subtitling"]
        res_dict["style"] = video_info["ass_path"]
        res_dict["series_id"] = video_info.get("series", "")
        document_dict = {}
        document_list = []
        for document in mongo.db.document.find({"video_id": video_id},
                                               {"file_name": 1,
                                                "file_path": 1}):
            document_dict["file_name"] = document["file_name"]
            document_dict["file_path"] = document["file_path"]
            document_list.append(deepcopy(document_dict))
        res_dict["document"] = document_list
        return set_resjson(res_array=[res_dict])


def upload():
    """
    上传文件
    """
    user = g.user
    if not user:
        raise response_code.UserERR(errmsg='用户未登录')
    task_id = request.form.get('task_id')
    chunk = request.form.get('chunk')
    chunks = request.form.get('chunks')
    file_type = request.form.get('video_type')
    if not all([task_id, chunk, chunks, file_type]):
        resp = set_resjson(err=-1,
                           errmsg='[ task_id, chunk, chunks, file, video_type ] can not be empty!')
    elif not allowed_video_file(file_type):
        resp = set_resjson(err=-1, errmsg='Incorrect file type!')
    else:
        if not os.path.isfile('static/upload/{}{}'.format(task_id, chunk)):
            upload_file = request.files['file']
            title = upload_file.filename
            data_title = mongo.db.video.find_one({"title": title})
            if data_title:
                title = '{}{}'.format(title, random.randint(0, 999))
            elif not title:
                raise response_code.ParamERR(errmsg='file not can be empty')
            upload_file.save('static/upload/{}{}'.format(task_id, chunk))
            folder_file_list = os.listdir('static/upload')
            file_list = [file for file in folder_file_list if
                         re.match(r'{}'.format(task_id), file)]
            if len(file_list) == int(chunks):
                resp = upload_success(file_type, task_id, user["_id"], title)
            else:
                resp = set_resjson(err=1,
                                   errmsg='Video shard acceptance completed!')
        else:
            resp = set_resjson(err=1, errmsg="Shards have been uploaded")
    return resp


def upload_update():
    """
    上传文件
    """
    user = g.user
    if not user:
        raise response_code.UserERR(errmsg='用户未登录')
    task_id = request.form.get('task_id', "")
    chunk = request.form.get('chunk', "")
    chunks = request.form.get('chunks', "")
    file_type = request.form.get('video_type', "")
    subtitling = request.form.get('subtitling', "")
    lang = request.form.get('lang', "")
    style = request.form.get('style', "")

    try:
        subtitling_list = literal_eval(subtitling)
    except Exception as e:
        raise response_code.ParamERR(
            errmsg="Incorrect subtitling format: {}".format(e))

    if not all([task_id, chunk, chunks, file_type, subtitling]):
        resp = set_resjson(err=-1,
                           errmsg='[ task_id, chunk, chunks, file, video_type ] can not be empty!')
    elif not allowed_video_file(file_type):
        resp = set_resjson(err=-1, errmsg='Incorrect file type!')
    elif lang not in ['en', 'cn']:
        raise response_code.ParamERR(errmsg='lang must be en or cn')
    else:
        upload_file = request.files['file']
        title = upload_file.filename
        if not title:
            raise response_code.ParamERR(errmsg='file not can be empty')
        upload_file.save('static/upload/{}{}'.format(task_id, chunk))
        folder_file_list = os.listdir('static/upload')
        file_list = [file for file in folder_file_list if
                     re.match(r'{}'.format(task_id), file)]
        if len(file_list) == int(chunks):
            resp = upload_success_update(file_type, task_id, subtitling_list,
                                         style, lang, user["_id"], title)
        else:
            resp = set_resjson(err=1,
                               errmsg='Video shard acceptance completed!')
    return resp


def upload_success_update(file_type, task_id, subtitling_list, style, lang,
                          user_id, title):
    """
    合并视频
    """
    chunk = 0
    current_name = 'static/videos/{}.{}'.format(task_id, file_type)
    with open(current_name, 'wb') as target_file:
        while True:
            try:
                filename = 'static/upload/{}{}'.format(task_id, chunk)
                source_file = open(filename, 'rb')
                target_file.write(source_file.read())
                source_file.close()
            except IOError:
                break
            chunk += 1
            os.remove(filename)

    md5_token = video_to_md5('static/videos/{}.{}'.format(task_id, file_type))

    try:
        video_info = mongo.db.video.find_one({'_id': md5_token},
                                             {'video_path': 1, "_id": 1,
                                              'image_path': 1})
    except Exception as e:
        raise response_code.DatabaseERR(errmsg="{}".format(e))
    if not video_info:

        filename = 'static/videos/{}.{}'.format(md5_token, file_type)
        os.rename(current_name, filename)
        video_time = get_video_time(filename)
        converted_video_picture(md5_token)
        response = upload_video(filename)
        os.remove(filename)

        video_path = response.pop("video_url")
        upload_time = time.time()
        video_info = {'_id': md5_token, 'video_message': response,
                      'video_path': video_path, "title": title,
                      'image_path': 'static/image/{}.jpg'.format(md5_token),
                      "upload_time": upload_time, "user_id": user_id,
                      "state": 0, "video_time": video_time, "view_counts": 0}
        try:
            mongo.db.video.insert_one(video_info)
        except Exception as e:
            raise response_code.DatabaseERR(errmsg="{}".format(e))

        back_info = {'video_id': md5_token,
                     'video_path': video_path}
        resp = set_resjson(errmsg='Video uploaded successfully!',
                           res_array=[back_info])

    else:
        os.remove('static/videos/{}.{}'.format(task_id, file_type))

        resp = set_resjson(errmsg='Video uploaded successfully!',
                           res_array=[video_info])
    edit_video(subtitling_list, md5_token, style, lang)

    return resp


def upload_success(file_type, task_id, user_id, title):
    """
    合并视频
    """
    chunk = 0
    current_name = 'static/videos/{}.{}'.format(task_id, file_type)
    with open(current_name, 'wb') as target_file:
        while True:
            try:
                filename = 'static/upload/{}{}'.format(task_id, chunk)
                source_file = open(filename, 'rb')
                target_file.write(source_file.read())
                source_file.close()
            except IOError:
                break
            chunk += 1
            os.remove(filename)

    md5_token = video_to_md5('static/videos/{}.{}'.format(task_id, file_type))
    try:
        video_info = mongo.db.video.find_one({'_id': md5_token},
                                             {'video_path': 1, "_id": 1,
                                              'image_path': 1})
    except Exception as e:
        raise response_code.DatabaseERR(errmsg="{}".format(e))
    if not video_info:

        filename = 'static/videos/{}.{}'.format(md5_token, file_type)
        os.rename(current_name, filename)
        video_time = get_video_time(filename)
        converted_video_picture(md5_token)
        response = upload_video(filename)
        os.remove(filename)
        video_path = response.pop("video_url")
        # upload_date = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        upload_date = time.time()
        video_info = {'_id': md5_token, 'video_message': response,
                      'video_path': video_path, "title": title,
                      'image_path': 'static/image/{}.jpg'.format(md5_token),
                      "upload_time": upload_date, "user_id": user_id,
                      "state": 0, "video_time": video_time, "view_counts": 0}
        try:
            mongo.db.video.insert_one(video_info)
        except Exception as e:
            raise response_code.DatabaseERR(errmsg="{}".format(e))

        back_info = {'video_id': md5_token,
                     'video_path': video_path,
                     'image_path': 'static/image/{}.jpg'.format(md5_token)
                     }
        resp = set_resjson(errmsg='Video uploaded successfully!',
                           res_array=[back_info])

    else:
        os.remove('static/videos/{}.{}'.format(task_id, file_type))

        resp = set_resjson(errmsg='The video has been uploaded !')
    return resp


def converted_video_picture(video_name):
    compress = "ffmpeg -i static/videos/{}.mp4 -y -ss 00:00:00 -vframes 1 -f image2  static/image/{}.jpg".format(
        video_name, video_name)
    is_run = os.system(compress)
    if is_run != 0:
        return (is_run, "没有安装ffmpeg")
    else:
        return (is_run, "转化成功")


def allowed_video_file(file_type):
    return file_type in config.ALLOWED_VIDEO_EXTENSIONS


def video_to_md5(_path):
    video = open(_path, 'rb').read()
    m1 = hashlib.md5()
    m1.update(video)
    token = m1.hexdigest()
    return token


def get_resolution2(input_path, height):
    cap = cv2.VideoCapture(input_path)
    width_now = cap.get(3)
    height_now = cap.get(4)
    width = math.floor(height / height_now * width_now)
    print('width:', width)
    video_resolution = str(width) + 'x' + str(height)
    return video_resolution


def video_to_image(input_path, out_path, video_resolution):
    compress = "ffmpeg -i {} -s {} -r 1  {}/image%5d.png".format(input_path,
                                                                 video_resolution,
                                                                 out_path)
    print("************", compress)
    is_run = os.system(compress)
    if is_run != 0:
        raise response_code.RoleERR(errmsg="{} 没有安装 ffmpeg".format(is_run))
    else:
        return (is_run, "转化成功")


def time_format(float_data):
    data_string = time.strftime('%H:%M:%S', time.gmtime(float_data))
    return data_string


def get_video_time(input_path):
    cap = cv2.VideoCapture(input_path)
    if cap.isOpened():
        rate = cap.get(5)  # 帧速率
        FrameNumber = cap.get(7)  # 视频文件的帧数
        duration = FrameNumber / rate
        data_string = time.strftime('%H:%M:%S', time.gmtime(duration))
    return data_string
