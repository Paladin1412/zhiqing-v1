#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    : category.py
@Time    : 2020/5/14 15:39
@Author  : Qi
@Email   : 18821723039@163.com
@Software: PyCharm
"""

from main import mongo
from utils import response_code
from utils.setResJson import set_resjson


class CategoryHandler(object):
    """
    标签
    """
    def __init__(self, extra_data, model_action):
        self.extra_data = extra_data
        self.model_action = model_action

    def handle_model(self):
        func_name = 'func_{}'.format(self.model_action)
        func_name = func_name.lower()
        try:
            handle_function = getattr(CategoryHandler, func_name)
            resp = handle_function(self)
        except AttributeError as e:
            resp = set_resjson(err=-4,
                               errmsg="{} is incorrect !".format(
                                   self.model_action))
        return resp

    def func_get_category(self):
        """
        查看标签信息
        """
        try:
            category_cursor = mongo.db.tool.find({},{"data":1, "_id": 0})
        except Exception as e:
            raise response_code.DatabaseERR(errmsg="{}".format(e))
        return set_resjson(res_array=[[category for category in category_cursor][0].get("data")])
