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

from flask import g

from main import mongo
from utils import response_code
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

# def change_information():
#     """
#     编辑个人信息
#     @return:
#     """
#     user = g.user
#     if not user:
#         raise response_code.UserERR(errmsg='用户未登录')
#     gender = request.form.get('gender', "")
#     user_name = request.form.get('user_name', "")
#     birthday = request.form.get('birthday', "")
#     introduction = request.form.get('introduction', "")
#     background = request.files['background']
#     headshot = request.files['headshot']
#     if not all(
#             [gender, user_name, birthday, introduction, background, headshot]):
#         raise response_code.ParamERR(errmsg="Parameter is not complete")
#     elif not name_re.match('{}'.format(user_name)):
#         raise response_code.ParamERR(errmsg="Incorrect user name format")
#     elif not allowed_image_file(background) or not allowed_image_file(headshot):
#         raise response_code.ParamERR(errmsg="The image type is incorrect")
#     elif gender not in ["男", "女", "保密"]:
#         response_code.ParamERR(errmsg="gender must be 男 or 女 or 保密")
#     is_birthday = verify_date_str_lawyer(birthday)
#     if not is_birthday:
#         raise response_code.ParamERR(errmsg="birthday Incorrect format")
#     background_path = 'static/background/{}'.format(
#         allowed_image_file(background))
#     headshot_path = 'static/headershot/{}'.format(allowed_image_file(headshot))
#     background.save(background_path)
#     headshot.save(headshot_path)
#     user_update_info = {"gender": gender, "name": user_name,
#                         "birthday": birthday, "introduction": introduction,
#                         "background": 'http://api.haetek.com:9191/' + background_path,
#                         "headshot": 'http://api.haetek.com:9191/' + headshot_path, }
#     mongo.db.user.update_one({"_id": user["_id"]}, {"$set": user_update_info})
#     return set_resjson()
