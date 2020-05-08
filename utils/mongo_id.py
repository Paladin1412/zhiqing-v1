#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    : mongo_id.py
@Time    : 2020/5/3 10:25
@Author  : Qi
@Email   : 18821723039@163.com
@Software: PyCharm
"""
import datetime
import random


def create_uuid():
    """
    生成唯一 id
    :return:
    """
    now_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")  # 生成当前时间
    random_num = '{}'.format(random.randint(0, 999999))  # 生成的随机整数
    unique_num = now_time + random_num
    return unique_num
