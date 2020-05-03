# -*- encoding: utf-8 -*-
"""
@File    : common.py
@Time    : 2020-02-20 16:51
@Author  : QI
@Email   : 18821723039@163.com
@Software: PyCharm
"""
# import functools
#
# import jwt
# from flask import request, current_app, g
# from app import mongo
#
#
# def query_user_data(func):
#     # 使用 @functools.wraps,去装饰函数, 可以保持当前装饰器去装饰的函数名字不变, 如果两个函数名字相同的话,flask会报错
#     @functools.wraps(func)
#     def wrapper(*args, **kwargs):
#
#         mobile = None
#         user = None
#         try:
#             authorization = request.headers.get("Authorization")
#             token = authorization.strip()[7:]
#             payload = jwt.decode(token, current_app.config['JWT_SECRET'],
#                                  algorithm=['HS256'])
#             if payload:
#                 mobile = payload["data"].get("mobile")
#                 user = mongo.db.users.find_one({"mobile": mobile})
#         except Exception as e:
#             current_app.logger.error(e)
#         g.user = user
#         g.mobile = mobile
#         return func(*args, **kwargs)
#
#     return wrapper

