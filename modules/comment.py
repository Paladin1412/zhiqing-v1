#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    : comment.py
@Time    : 2020/5/3 09:29
@Author  : Qi
@Email   : 18821723039@163.com
@Software: PyCharm
"""
import os
import time
from copy import deepcopy

from flask import g

from main import mongo
from utils import response_code
from utils.mongo_id import create_uuid
from utils.setResJson import set_resjson


class CommentHandler(object):
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
        handle_function = getattr(CommentHandler, func_name)
        res = handle_function(self)
        return res

    def func_comment_post(self):
        """
        发表评论
        """
        user = g.user
        if not user:
            raise response_code.UserERR(errmsg='用户未登录')
        video_id = self.extra_data.get("video_id", "")
        parent_id = self.extra_data.get("parent_id", "")
        content = self.extra_data.get("content", "")

        collect_time = str(time.time())
        try:
            parent_id = int(parent_id)
        except Exception as e:
            raise response_code.ParamERR(errmsg="parent_id is incorrect !")
        if video_id == "" or content == "" or parent_id == "":
            raise response_code.UserERR(
                errmsg="[ video_id, parent_id, content ] must be provided")
        try:
            video_info = mongo.db.video.find_one({"_id": video_id})
        except Exception as e:
            raise response_code.DatabaseERR(errmsg="{}".format(e))
        if not video_info:
            raise response_code.ParamERR(errmsg="video_id is incorrect")
        if parent_id != 0:
            try:
                comment_info = mongo.db.comment.find_one(
                    {"_id": "{}".format(parent_id)})
            except Exception as e:
                raise response_code.DatabaseERR(errmsg="{}".format(e))
            if not comment_info:
                raise response_code.ParamERR(errmsg="parent_id is incorrect")
            try:
                mongo.db.comment.insert(
                    {"_id": create_uuid(), "parent_id": "{}".format(parent_id),
                     "content": content, "time": collect_time,
                     "video_id": video_id,
                     "to_user_id": comment_info["user_id"],
                     "user_name": user["name"], "headshot": user["headshot"],
                     "user_id": user["_id"],
                     "to_user_name": comment_info["user_name"]})
            except Exception as e:
                raise response_code.DatabaseERR(errmsg="{}".format(e))
        else:
            try:
                mongo.db.comment.insert(
                    {"_id": create_uuid(), "parent_id": "{}".format(parent_id),
                     "content": content, "time": collect_time,
                     "video_id": video_id,
                     "user_id": user["_id"], "user_name": user["name"],
                     "headshot": user["headshot"]})
            except Exception as e:
                raise response_code.DatabaseERR(errmsg="{}".format(e))

        return set_resjson()


    def func_database(self):
        from random import choice
        from pprint import pprint
        content_list = ["有关Strang教授有关OCW的相关课程的链接，请访问完整资源网站上的“相关资源”页面：https : //ocw.mit.edu/2020-vision ",
                        "当我在18.06中看到作业中的一个小错误时，我给他发送了电子邮件。他是如此客气，几乎立即做出了回应。活着的传奇",
                        "很高兴见到教授。斯特朗仍然表现良好。请保持健康的教授",
                        "吉尔伯特·斯特兰（Gilbert Strang）到一个空荡荡的教室：“什么是R转置转置？停顿一下，不要一次都讲话。",
                        "刚看完他的旧播放列表。.住在什么时间",
                        "吉尔伯特具有传奇色彩"]

        res_list= []
        temporary_list = []
        user_info = {}
        # video_id_list = [video_info_dict["_id"] for video_info_dict in mongo.db.video.find()]
        # user_info_list = [user_info_dict for user_info_dict in mongo.db.user.find({}, {"headshot": 1, "name": 1})]
        # for _user in user_info_list:
        #     user_info["user_id"] = _user["_id"]
        #     user_info["headshot"] = _user["headshot"]
        #     user_info["user_name"] = _user["name"]
        #     # user_info["_id"] = create_uuid()
        #     # user_info["video_id"] = choice(video_id_list)
        #     # user_info["parent"] = "0"
        #     # user_info["relation_id"] = choice(video_id_list)
        #     # user_info["content"] = choice(content_list)
        #     temporary_list.append(deepcopy(user_info))
        #
        # pprint(temporary_list)
        # for i in range(10):
        #     user_dict = choice(temporary_list)
        #     user_dict["_id"] = create_uuid()
        #     user_dict["video_id"] = choice(video_id_list)
        #     user_dict["parent"] = "0"
        #     # user_dict["relation_id"] = choice(video_id_list)
        #     user_dict["content"] = choice(content_list)
        #     res_list.append(deepcopy(user_dict))

        mongo.db.comment.update_one({"_id": "20200513140205686541"},{"$unset":{"relation_id": ""}})

        return set_resjson(res_array=res_list)