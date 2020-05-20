#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    : document.py
@Time    : 2020/5/14 14:25
@Author  : Qi
@Email   : 18821723039@163.com
@Software: PyCharm
"""
from copy import deepcopy

from main import mongo
from utils import response_code
from utils.setResJson import set_resjson


class DocumentHandler(object):
    def __init__(self, extra_data, model_action):
        self.extra_data = extra_data
        self.model_action = model_action

    def handle_model(self):
        func_name = 'func_{}'.format(self.model_action)
        func_name = func_name.lower()
        try:
            handle_function = getattr(DocumentHandler, func_name)
            resp = handle_function(self)
        except AttributeError as e:
            resp = set_resjson(err=-4,
                               errmsg="{} is incorrect !".format(
                                   self.model_action))
        return resp

    def func_view_file(self):
        """
        查看课件
        """
        video_id = self.extra_data.get('video_id')
        video_document = {}
        res_list = []
        try:
            video_document_cursor = mongo.db.document.find(
                {"video_id": video_id})

        except Exception as e:
            raise response_code.DatabaseERR(errmsg="{}".format(e))

        for document in video_document_cursor:
            video_document["file_id"] = document["_id"]
            video_document["file_name"] = document["file_name"]
            video_document["file_path"] = document["file_path"]
            video_document["price"] = document["price"]
            video_document["time"] = document["time"]
            res_list.append(deepcopy(video_document))

        if not video_document:
            raise response_code.RoleERR(errmsg="这个视频没有课件")
        return set_resjson(res_array=res_list)

    def func_download_file(self):
        """
        课件下载
        @return:
        """
        res_list = []
        file_id = self.extra_data.get("file_id", "")
        if file_id == "" or type(file_id) != list:
            raise response_code.ParamERR(
                errmsg="file_id be provide or type must array")
        for document_id in file_id:
            try:
                video_document = mongo.db.document.find_one(
                    {"_id": document_id},
                    {"_id": 0,
                     "file_path": 1, "download_counts": 1})

                if not video_document:
                    video_document = {document_id: "此ID不存在"}
                else:
                    if "download_counts" in video_document.keys():
                        download_counts = video_document.pop("download_counts")
                    else:
                        download_counts = 0
                    mongo.db.document.update_one({"_id": document_id}, {
                        "$set": {"download_counts": download_counts + 1}})

                res_list.append(deepcopy(video_document))
            except Exception as e:
                raise response_code.DatabaseERR(errmsg="{}".format(e))

        return set_resjson(res_array=res_list)
