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
from modules.aimodels.subtitle import Subtitle
from utils import response_code


def play_video(query_str, mode, video_ids):
    """
    查询视频
    :param query_str:
    :param mode:
    :param video_ids:
    :return:
    """
    s = Search()
    try:
        result = s.video_search(query_str=query_str, mode=mode,
                                video_ids=video_ids)
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
            subtitle = Subtitle(task_id)
            subtitle.generate_configs(video_id=task_id, lang=lang)
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
    subtitle = Subtitle(task_id)
    result = subtitle.update_configs(subtitling, task_id, style)
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
