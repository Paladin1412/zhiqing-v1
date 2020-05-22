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
import re
import time
from ast import literal_eval
from collections import Counter
from copy import deepcopy
from threading import Thread

import cv2
from flask import request, g

from config.settings import config
from main import mongo
from modules.aimodels import run_ai
from modules.aimodels.run_ai import generate_subtitle as generate_subtitle1, \
    edit_video
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

        ret = run_ai.global_play_video(query_string, mode, video_ids, max_size,
                                       page)
        user = g.user
        if user:
            user_id = user["_id"]
        else:
            user_id = "1"
        try:
            mongo.db.search_history.insert(
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
            mongo.db.search_history.insert(
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
                video_info = mongo.db.video.find_one({'_id': task_id})
            except Exception as e:
                raise response_code.DatabaseERR(errmsg="{}".format(e))
            if not video_info:
                resp = set_resjson(err=-1, errmsg='_id is Incorrect!')
            else:
                try:
                    run_ai.update_subtitle(task_id, subtitling, style)
                except Exception as e:
                    raise response_code.ParamERR(errmsg='{}'.format(e))
                resp = set_resjson()
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
        tool = mongo.db.tool.find_one({'type': 'category'})
        video = mongo.db.video.find_one({'_id': video_id})
        video_user_info = mongo.db.user.find_one({"_id": video["user_id"]},
                                                 {"name": 1, "_id": 1,
                                                  "headshot": 1})
        like_counts = mongo.db.like.find(
            {"relation_id": video_id, "type": "video"}).count()
        collection_counts = mongo.db.collection.find(
            {"video_id": video_id}).count()
        author_id = video['user_id']
        view_counts = 0 if 'view_counts' not in list(video.keys()) else video[
            'view_counts']
        category_list = []
        for category in video['category']:
            category_list.append(tool["data"].get(category))
        data_dict = {'video_id': video_id, 'video_path': video['video_path'],
                     'audio_path': video['audio_path'],
                     'lang': video['lang'], 'ass_path': video['ass_path'],
                     'upload_time': video['upload_time'],
                     'title': video['title'], 'user_id': video_user_info["_id"],
                     'user_name': video_user_info['name'],
                     'headshot': video_user_info['headshot'],
                     # 'category': tool['data'][video['category']],
                     'category': category_list,
                     'description': video['description'],
                     'image_path': video['image_path'],
                     'view_counts': video["view_counts"],
                     'like_counts': like_counts,
                     'collection_counts': collection_counts,
                     "is_like": 0,
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
        res_list = []
        for video in video_cursor:
            video["upload_date"] = video.pop("upload_time")
            res_list.append(deepcopy(video))
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
            related_cursor = mongo.db.video.find(
                {"series": series_id, "state": 2}).sort(
                "view_counts", -1).limit(max_size).skip(max_size * (page - 1))
            series_info = mongo.db.series.find_one({"_id": series_id})
            for video in related_cursor:
                if video["_id"] == video_id:
                    continue
                video_dict["video_id"] = video["_id"]
                video_dict["video_title"] = video["title"]
                video_dict["video_time"] = video["video_time"]
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
            tool = mongo.db.tool.find_one({'type': 'category'})
            for video in video_cursor:
                likes = mongo.db.like.find(
                    {"relation_id": video.get("_id"), "type": "video"}).count()
                comments = mongo.db.comment.find(
                    {"video_id": video.get("_id")}).count()
                user_info = mongo.db.user.find_one(
                    {"_id": video.get("user_id")})

                category_list = []
                for category in video['category']:
                    category_list.append(tool["data"].get(category))
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
                    like_counts = 0
                    comment_counts = 0
                    series_video_cursor = mongo.db.video.find(
                        {"series": series_id, "state": 2})
                    for video in series_video_cursor:
                        likes = mongo.db.like.find(
                            {"relation_id": video.get("_id"),
                             "type": "video"}).count()
                        comments = mongo.db.comment.find(
                            {"video_id": video.get("_id")}).count()
                        view_counts += video["view_counts"]
                        like_counts += likes
                        comment_counts += comments
                    series_info = mongo.db.series.find_one({"_id": series_id})
                    series_user_info = mongo.db.user.find_one(
                        {"_id": series_info["user_id"]})
                    res_dict["series_id"] = series_info["_id"]
                    res_dict["image_path"] = series_info["image_path"]
                    res_dict["title"] = series_info["title"]
                    res_dict["time"] = series_info["time"]
                    res_dict["user_id"] = series_info["user_id"]
                    res_dict["user_name"] = series_user_info["name"]
                    res_dict["headshot"] = series_user_info["headshot"]
                    res_dict["view_counts"] = view_counts
                    res_dict["comment_counts"] = comment_counts
                    res_dict["like_counts"] = like_counts
                else:
                    res_dict["video_id"] = video["_id"]
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
            raise response_code.DatabaseERR(errmsg="{}".format(e))
        return set_resjson(res_array=res_list)


    def func_hot_author(self):
        """
        热门作者
        @return:
        """
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
            video_dict = {}
            video_list = []
            for relation_id_set in relation_sort:
                author_info = mongo.db.user.find_one(
                    {"_id": relation_id_set[0]},
                    {"name": 1, "headshot": 1, "introduction": 1,
                     "background": 1})
                res_dict["user_id"] = author_info["_id"]
                res_dict["user_name"] = author_info["name"]
                res_dict["headshot"] = author_info["headshot"]
                res_dict["background"] = author_info["background"]
                res_dict["introduction"] = author_info["introduction"]
                res_dict["description_counts"] = relation_id_set[1]
                video_cursor = mongo.db.video.find(
                    {"user_id": relation_id_set[0], "state": 2}).sort(
                    "view_counts", -1).limit(video_size)
                for video in video_cursor:
                    tool = mongo.db.tool.find_one({'type': 'category'})
                    category_list = []
                    for category in video['category']:
                        category_list.append(tool["data"].get(category))
                    like_counts = mongo.db.like.find(
                        {"relation_id": video["_id"], "type": "video"}).count()
                    comment_counts = mongo.db.comment.find(
                        {"video_id": video["_id"]}).count()
                    video_dict["video_id"] = video["_id"]
                    video_dict["image_path"] = video["image_path"]
                    video_dict["title"] = video["title"]
                    video_dict["update_time"] = video["upload_time"]
                    video_dict["view_counts"] = video["view_counts"]
                    video_dict["category"] = category_list
                    video_dict["comment_counts"] = comment_counts
                    video_dict["like_counts"] = like_counts
                    video_list.append(deepcopy(video_dict))
                res_dict["video_data"] = video_list

                res_list.append(deepcopy(res_dict))
        except Exception as e:
            raise response_code.DatabaseERR(errmsg="{}".format(e))

        return set_resjson(res_array=res_list)

def func_check():
    """
    视频审核
    """
    user = g.user
    if not user:
        raise response_code.UserERR(errmsg='用户未登录')
    task_id = request.form.get('task_id')
    title = request.form.get('title')
    description_title = request.form.get('description_title', "")
    description = request.form.get('description')
    category = request.form.get('category')

    series_title = request.form.get('series_title')
    image_name = None

    try:
        category = literal_eval(category)
    except Exception as e:
        raise response_code.ParamERR(
            errmsg="Incorrect subtitling format: {}".format(e))

    if not all([task_id, description, category]):
        raise response_code.ParamERR(
            errmsg="[task_id, description, category] must be provided ！")
    try:
        video_info = mongo.db.video.find_one(
            {"_id": task_id, "user_id": user["_id"]})
        category_cursor = mongo.db.tool.find({}, {"_id": 0, "data": 1})
        category_list = [category for category in category_cursor][0].get(
            "data")
    except Exception as e:
        raise response_code.DatabaseERR(errmsg="{}".format(e))

    for i in category:
        if i not in category_list:
            raise response_code.ParamERR(errmsg="{} 标签不存在".format(i))
    if not video_info:
        raise response_code.ParamERR(errmsg='task_id 不存在')

    # if video_info["state"] == 1:
    #     raise response_code.ReqERR(errmsg="正在审核请耐心等待")
    try:
        image_file = request.files["image"]
        image_name = image_file.filename
    except Exception as e:
        pass
    if image_name:

        image_path = 'static/image/{}.{}'.format(task_id,
                                                 image_name.rsplit('.', 1)[1])
        image_file.save(image_path)
        update_video_info = {"description": description, "category": category,
                             "image_path": image_path,
                             "state": 2}
    else:
        update_video_info = {"description": description, "category": category,
                             "state": 2}

    if title:
        update_video_info["title"] = title

    try:
        mongo.db.video.update_one({"_id": task_id}, {"$set": update_video_info})
    except Exception as e:
        raise response_code.DatabaseERR(errmsg='{}'.format(e))

    if series_title:
        try:
            series_info = mongo.db.series.find_one(
                {"user_id": user["_id"], "title": series_title})
            if series_info:
                mongo.db.video.update_one({"_id": task_id},
                                          {"$set": {
                                              "series": series_info["_id"]}})

            else:
                image_path_info = mongo.db.video.find_one({"_id": task_id})
                _id = create_uuid()
                mongo.db.series.insert_one({"_id": _id, "title": series_title,
                                            "description": description_title,
                                            "image_path": image_path_info[
                                                "image_path"],
                                            "category": category,
                                            "user_id": user["_id"],
                                            "time": time.time()})
                mongo.db.video.update_one({"_id": task_id},
                                          {"$set": {"series": _id}})
        except Exception as e:
            raise response_code.DatabaseERR(errmsg="{}".format(e))

    return set_resjson()


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
            if not title:
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

        resp = set_resjson(errmsg='Video uploaded successfully!',
                           res_array=[video_info])
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


def allowed_image_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[
        1] in config.ALLOWED_IMAGE_EXTENSIONS


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
