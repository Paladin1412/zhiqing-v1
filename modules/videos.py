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
        res_list = []
        query_string = self.extra_data.get("query_string", "")
        video_ids = self.extra_data.get("video_ids", "")
        mode = 'global'
        ret = run_ai.play_video(query_string, mode, video_ids)
        for video_info in ret:
            user_id = video_info.pop("user_id")
            user_info = mongo.db.user.find_one({"_id": user_id})
            video_info["name"] = user_info['name']
            video_info["headshot"] = user_info['headshot']
            res_list.append(video_info)

        response = set_resjson(res_array=ret)
        return response

    def func_local_search(self):
        """
        局部搜索视频
        :return:
        """
        query_string = self.extra_data.get('query_string', "")
        video_ids = self.extra_data.get('video_id', "")
        if query_string == "":
            response = set_resjson(err=-1,
                                   errmsg="[ query_string ] must be provided ！")
        elif video_ids == "":
            response = set_resjson(err=-2,
                                   errmsg="[ video_ids ] must be provided ！")
        else:
            mode = 'local'
            ret = run_ai.play_video(query_string, mode, video_ids)
            response = set_resjson(res_array=ret)

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
        video__update_info = {'composite_video_message': response,
                              "composite_video": video_path}
        try:
            mongo.db.video.update_one({"_id": task_id},
                                      {"$set": video__update_info})
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

    # def func_video_play(self):
    #     """
    #     视频播放
    #     """
    #     user = g.user
    #     if not user:
    #         raise response_code.UserERR(errmsg='用户未登录')
    #     video_id = self.extra_data.get('video_id', '')
    #     if video_id == '':
    #         raise response_code.ParamERR(errmsg="[video_id] must be provided")
    #     try:
    #         video_info = mongo.db.video.find_one({'_id': video_id},
    #                                              {"video_path": 1,
    #                                               "audio_path": 1, "lang": 1,
    #                                               "ass_path": 1, "title": 1,
    #                                               "user_id": 1,
    #                                               "video_view": 1})
    #         like_info = mongo.db.like.find_one(
    #             {"user_id": user["_id"], "relation_id": video_id})
    #         like_count = mongo.db.like.find(
    #             {"relation_id": video_id}).count()
    #         collect_info = mongo.db.collect.find_one(
    #             {"user_id": user["_id"], "relation_id": video_id})
    #         comment_cursor = mongo.db.comment.find({"video_id": video_id})
    #
    #     except Exception as e:
    #         raise response_code.DatabaseERR(errmsg="{}".format(e))
    #     for comment_dict in comment_cursor:
    #         parent_id = comment_dict.get("parent_id", "")
    #         if parent_id in comment_dict:
    #             pass
    #
    #
    #
    #
    #     video_info["is_like"] = 1 if like_info else 0
    #     video_info["is_collect"] = 1 if collect_info else 0
    #     video_info["like"] = 1 if like_count else 0
    #     video_info["comment"] = [i for i in comment_cursor]
    #
    #     return set_resjson(res_array=[video_info])

def func_check():
    """
    视频审核
    """
    user = g.user
    if not user:
        raise response_code.UserERR(errmsg='用户未登录')
    task_id = request.form.get('task_id')
    title = request.form.get('title')
    description = request.form.get('description')
    category = request.form.get('category')
    image = request.files.get('image')
    series_title = request.files.get('series_title')
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
    except Exception as e:
        raise response_code.DatabaseERR(errmsg="{}".format(e))
    if not video_info:
        raise response_code.ParamERR(errmsg='task_id 不存在')
    try:
        image_name = image.filename
    except Exception as e:
        pass
    if image_name:
        image_path = '/static/image/{}'.format(image_name)
        # TODO 后面加上去重  暂时 state 设置为 2
        image.save(image)
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
                mongo.db.video.update_one(
                    {"_id": task_id, "title": series_title})
            else:
                _id = create_uuid()
                mongo.db.series.insert_one({"_id": _id, "title": title,
                                            "description": description,
                                            "image_path": image_path if image_path else
                                            video_info["image_path"],
                                            "user_id": user["_id"],
                                            "time": str(time.time())})
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
        converted_video_picture(md5_token)
        response = upload_video(filename)
        os.remove(filename)

        video_path = response.pop("video_url")
        upload_time = time.time()
        video_info = {'_id': md5_token, 'video_message': response,
                      'video_path': video_path, "title": title,
                      'image_path': 'static/image/{}.jpg'.format(md5_token),
                      "upload_time": upload_time, "user_id": user_id,
                      "state": 0}
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
                      "state":0 }
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
