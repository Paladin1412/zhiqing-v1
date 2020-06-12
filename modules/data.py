#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    : data.py
@Time    : 2020/5/20 15:22
@Author  : Qi
@Email   : 18821723039@163.com
@Software: PyCharm
"""
import datetime

from flask import g, request

from main import mongo
from utils import response_code
from utils.common import allowed_image_file
from utils.setResJson import set_resjson


class DataHandler(object):
    """
    数据中心
    """

    def __init__(self, extra_data, model_action):
        self.extra_data = extra_data
        self.model_action = model_action

    def handle_model(self):
        func_name = 'func_{}'.format(self.model_action)
        func_name = func_name.lower()
        try:
            handle_function = getattr(DataHandler, func_name)
            if self.model_action not in ["get_data"]:
                if self.extra_data == '':
                    raise response_code.ParamERR(
                        errmsg="[ extra_data ] must be provided ")
            resp = handle_function(self)
        except AttributeError as e:
            resp = set_resjson(err=-4,
                               errmsg="{} is incorrect !".format(
                                   self.model_action))
        return resp

    def func_get_data(self):
        """
        获取数据
        """
        user = g.user
        if not user:
            raise response_code.UserERR(errmsg='用户未登录')
        view_counts = 0
        download_counts = 0
        like_counts = 0
        collections_counts = 0
        share_counts = 0
        comment_counts = 0
        now = datetime.datetime.now()
        # 上一周
        # last_week_end = now - timedelta(days=now.weekday() + 1)
        # week_end_second = str(last_week_end).split()[0] + " " + "23:59:59"
        # timestamp = time.mktime(time.strptime(week_end_second, "%Y-%m-%d %H:%M:%S"))
        week_ago = (now - datetime.timedelta(days=7)).timestamp()
        # timestamp = time.mktime(
        #     time.strptime(str(week_ago), "%Y-%m-%d %H:%M:%S"))
        week_end_sub_count = mongo.db.subscription.find(
            {"relation_id": user["_id"], "state": 0,
             "time": {"$lte": week_ago}}).count()
        fans_counts = mongo.db.subscription.find(
            {"relation_id": user["_id"], "state": 0}).count()
        video_cursor = mongo.db.video.find({"user_id": user["_id"]})
        for video in video_cursor:
            view_counts += video["view_counts"]
            if "share_counts" in video.keys():
                share_counts += video.pop("download_counts")
            document_cursor = mongo.db.document.find({"video_id": video["_id"]})
            for document in document_cursor:
                if "download_counts" in document.keys():
                    download_counts += document.pop("download_counts")
            like_counts += mongo.db.like.find(
                {"relation_id": video["_id"]}).count()
            collections_counts += mongo.db.collection.find(
                {"relation_id": video["_id"]}).count()
            comment_counts += mongo.db.comment.find(
                {"video_id": video["_id"], "state": 2}).count()
        res_dict = {"fans_counts": fans_counts,
                    "view_counts": view_counts,
                    "fans_change": fans_counts - week_end_sub_count,
                    "share_counts": share_counts,
                    "download_counts": download_counts,
                    "collections_counts": collections_counts,
                    "comment_counts": comment_counts}

        return set_resjson(res_array=[res_dict])

    def func_change_color(self):
        """
        字体改变颜色
        @return:
        """
        start_RGB = self.extra_data.get("start_RGB")
        middle_RGB = self.extra_data.get("middle_RGB")
        end_RGB = self.extra_data.get("end_RGB")
        result_data = demo_display(start_RGB,
                                   middle_RGB,
                                   end_RGB)
        return set_resjson(res_array=result_data)


def upload_file():
    """
    上传图片
    @return:
    """
    user = g.user
    if not user:
        raise response_code.UserERR(errmsg='用户未登录')
    image_type = request.form.get('type', "")
    try:
        file = request.files['file']
    except Exception as e:
        raise response_code.ParamERR(errmsg="{}".format(e))
    if not all([image_type, file]):
        raise response_code.ParamERR(errmsg="Parameter is not complete")
    elif not allowed_image_file(file):
        raise response_code.ParamERR(errmsg="The image type is incorrect")
    if image_type == "background":
        file_path = 'static/background/{}'.format(allowed_image_file(file))
        res_url = "http://api.haetek.com:8181/" + file_path
    elif image_type == "headshot":
        file_path = 'static/headershot/{}'.format(allowed_image_file(file))
        res_url = "http://api.haetek.com:8181/" + file_path
    elif image_type in ["video_image", "series_image"] :
        file_path = 'static/image/{}'.format(allowed_image_file(file))
        res_url = file_path
    elif image_type == "document":
        file_path = 'static/document/{}'.format(allowed_image_file(file))
        res_url = file_path
    else:
        raise response_code.ParamERR(errmsg="type is incorrect")
    file.save(file_path)
    return set_resjson(res_array=[res_url])


def density_to_RGB(start_RGB, middle_RGB, end_RGB, dens_val):
    res_RGB = []
    for color_id in range(3):
        if dens_val < 0.5:
            curr_color_val = start_RGB[color_id] + 2 * dens_val * (
                        middle_RGB[color_id] - start_RGB[color_id])
        else:
            curr_color_val = 2 * middle_RGB[color_id] - end_RGB[
                color_id] + 2 * dens_val * (end_RGB[color_id] - middle_RGB[
                color_id])

        res_RGB.append(round(min(255, max(0, curr_color_val))))

    return res_RGB


def dist_to_colors(density_list, start_RGB, middle_RGB, end_RGB):
    res_list = []
    for str_val, str_pos, str_dens in density_list:
        curr_RGB = density_to_RGB(start_RGB, middle_RGB, end_RGB, str_dens)
        res_list.append([str_val, curr_RGB])

    return res_list


def demo_display(start_RGB, middle_RGB, end_RGB):
    res_list = []
    for sample_id in test_samples:
        curr_res = dist_to_colors(test_samples[sample_id]['density_dist'],
                                  start_RGB, middle_RGB, end_RGB)
        res_list.append(
            {
                'id': sample_id,
                'query_str': test_samples[sample_id]['query_str'],
                'result': curr_res
            }
        )

    return res_list


test_samples = {
    'sample1': {
        'query_str': '瞥了几眼一排一长',
        'source_str': '这时我瞥了一眼一长排一长排床',
        'density_dist': [['这', 253, 0.0], ['时', 254, 0.21], ['我', 255, 0.59],
                         ['瞥', 256, 0.7], ['了', 257, 0.96], ['一', 258, 0.97],
                         ['眼', 259, 1.0], ['一', 260, 0.93], ['长', 261, 0.85],
                         ['排', 262, 0.61], ['一', 263, 0.42], ['长', 264, 0.27],
                         ['排', 265, 0.04], ['床', 266, 0.02]]
    },
    'sample2': {
        'query_str': '历史悠久的神话',
        'source_str': '这个古老而美丽的故事世代在坦桑尼亚人民中间传诵',
        'density_dist': [['这', 198, 0.72], ['个', 199, 0.86], ['古', 200, 0.89],
                         ['老', 201, 0.92], ['而', 202, 1.0], ['美', 203, 0.9],
                         ['丽', 204, 0.87], ['的', 205, 0.76], ['故', 206, 0.61],
                         ['事', 207, 0.51], ['世', 208, 0.3], ['代', 209, 0.1],
                         ['在', 210, 0.0], ['坦', 211, 0.0], ['桑', 212, 0.13],
                         ['尼', 213, 0.31], ['亚', 214, 0.5], ['人', 215, 0.59],
                         ['民', 216, 0.66], ['中', 217, 0.67], ['间', 218, 0.65],
                         ['传', 219, 0.57], ['诵', 220, 0.49]]
    },
    'sample3': {
        'query_str': '意义非常关键',
        'source_str': '高斯分布对我们很有意义',
        'density_dist': [['高', 3650, 0.0], ['斯', 3651, 0.03], ['分', 3652, 0.12],
                         ['布', 3653, 0.3], ['对', 3654, 0.51], ['我', 3655, 0.86],
                         ['们', 3656, 0.98], ['很', 3657, 1.0], ['有', 3658, 0.86],
                         ['意', 3659, 0.55], ['义', 3660, 0.25]]
    },
    'sample4': {
        'query_str': '意义非常关键',
        'source_str': '因此网络舆情监测具有十分重要的意义',
        'density_dist': [['因', 21, 0.19], ['此', 22, 0.07], ['网', 23, 0.04],
                         ['络', 24, 0.0], ['舆', 25, 0.02], ['情', 26, 0.1],
                         ['监', 27, 0.23], ['测', 28, 0.53], ['具', 29, 0.84],
                         ['有', 30, 0.99], ['十', 31, 1.0], ['分', 32, 0.94],
                         ['重', 33, 0.82], ['要', 34, 0.77], ['的', 35, 0.71],
                         ['意', 36, 0.56], ['义', 37, 0.4]]
    },
    'sample5': {
        'query_str': '如何描述基础粒子',
        'source_str': '理论将这些基本粒子表达成弦的振动',
        'density_dist': [['理', 1, 0.55], ['论', 2, 0.65], ['将', 3, 0.83],
                         ['这', 4, 1.0], ['些', 5, 0.92], ['基', 6, 0.77],
                         ['本', 7, 0.46], ['粒', 8, 0.34], ['子', 9, 0.39],
                         ['表', 10, 0.47], ['达', 11, 0.57], ['成', 12, 0.55],
                         ['弦', 13, 0.44], ['的', 14, 0.26], ['振', 15, 0.09],
                         ['动', 16, 0.0]]
    },
    'sample6': {
        'query_str': 'kd树',
        'source_str': '这是高层的想法在kd树后面',
        'density_dist': [['这', 9631, 0.0], ['是', 9632, 0.0], ['高', 9633, 0.0],
                         ['层', 9634, 0.0], ['的', 9635, 0.0], ['想', 9636, 0.0],
                         ['法', 9637, 0.0], ['在', 9638, 0.0], ['k', 9639, 1.0],
                         ['d', 9640, 1.0], ['树', 9641, 1.0], ['后', 9642, 0.0],
                         ['面', 9643, 0.0]]
    },
    'sample7': {
        'query_str': '传统的粒子',
        'source_str': '只是这和传统粒子描述方法不同',
        'density_dist': [['只', 18, 0.33], ['是', 19, 0.51], ['这', 20, 0.72],
                         ['和', 21, 0.97], ['传', 22, 1.0], ['统', 23, 0.95],
                         ['粒', 24, 0.82], ['子', 25, 0.68], ['描', 26, 0.55],
                         ['述', 27, 0.46], ['方', 28, 0.0]]
    },
    'sample8': {
        'query_str': '聪明的',
        'source_str': '这位机智勇敢的男孩为了避免恶魔的伤害',
        'density_dist': [['这', 480, 0.38], ['位', 481, 0.63], ['机', 482, 0.73],
                         ['智', 483, 1.0], ['勇', 484, 0.69], ['敢', 485, 0.54],
                         ['的', 486, 0.18], ['男', 487, 0.05], ['孩', 488, 0.03],
                         ['为', 489, 0.0], ['了', 490, 0.09], ['避', 491, 0.09],
                         ['免', 492, 0.29], ['恶', 493, 0.19], ['魔', 494, 0.24],
                         ['的', 495, 0.19], ['伤', 496, 0.18], ['害', 497, 0.25]]
    },
}
