#!/usr/bin/env python 
# -*- coding: utf-8 -*-
"""
@File     : run_ai.py
@Time     : 2020-03-17 14:24
@Author   : Qi
@Email    : 18821723039@163.com
@Software : PyCharm
"""
from modules.aimodels.search import Search
from modules.aimodels.subtitle import Subtitle, Document
from utils import response_code
from flask import current_app


def global_play_video(query_str, mode, video_ids, max_size, page):
    """
    全局查询视频
    """
    s = Search()
    try:
        current_app.logger.info("全局搜索开始")
        result = s.global_search(query_str, video_ids, mode, max_size, page)
        current_app.logger.info("全局搜索结束")
    except Exception as e:
        raise response_code.RoleERR(errmsg='{}'.format(e))
    return result


def local_play_video(query_str, video_ids):
    """
    局部查询视频
    """
    s = Search()
    try:
        current_app.logger.info("局部搜索开始")
        result = s.local_search(query_str, video_ids)
        current_app.logger.info("局部搜索结束")
    except Exception as e:
        raise response_code.RoleERR(errmsg='{}'.format(e))
    return result


def generate_subtitle(task_id, lang):
    """
    生成字幕
    :param task_id:
    :param lang:
    :return:
    """
    from main import app, mongo
    try:

        with app.app_context():
            current_app.logger.info("生成字幕开始")
            subtitle = Subtitle(task_id)
            subtitle.generate_configs(video_id=task_id, lang=lang)
            current_app.logger.info("生成字幕结束")
    except Exception as e:
        print(e)
        try:
            mongo.db.video.update_one({'_id': task_id},
                                      {'$unset': {'subtitling': ''}})
        except Exception as e:
            raise response_code.DatabaseERR(errmsg='{}'.format(e))


def update_subtitle(task_id, subtitling, style):
    """
    更改字幕，并更新数据库
    :param task_id:
    :param subtitling:
    :param style:
    :return:
    """
    current_app.logger.info("更改字幕，并更新数据库开始")
    subtitle = Subtitle(task_id)
    result = subtitle.update_configs(subtitling, task_id, style)
    current_app.logger.info("更改字幕，并更新数据库结束")
    return result


def edit_video(res_list, video_id, style, lang):
    """
    编辑视频
    """
    try:
        subtitle = Subtitle(video_id)
        subtitle.update_video(res_list, video_id, style, lang)
    except Exception as e:
        raise response_code.ParamERR(errmsg='{}'.format(e))


def edit_document(file_id, file_name, file_path, preview_path, price, video_id,
                  user_id, image_path):
    """
    生成课件内容
    @return:
    """
    document = Document()
    result = document.save_str_to_database(file_id, file_name, file_path,
                                           preview_path, price, video_id,
                                           user_id, image_path)
    return result
