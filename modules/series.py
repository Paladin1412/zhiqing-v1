#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    : series.py
@Time    : 2020/5/13 15:19
@Author  : Qi
@Email   : 18821723039@163.com
@Software: PyCharm
"""
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
            resp = handle_function(self)
        except AttributeError as e:
            resp = set_resjson(err=-4,
                               errmsg="{} is incorrect !".format(
                                   self.model_action))
        return resp

    def func_get_series(self):
        """
        获得系列信息
        """
        user = g.user
        print(user)
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
