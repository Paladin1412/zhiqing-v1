#!/usr/bin/env python 
# -*- coding: utf-8 -*-
"""
@File     : settings.py
@Time     : 2020-03-29 20:55
@Author   : Qi
@Email    : 18821723039@163.com
@Software : PyCharm
"""
import logging
import os

ENV = os.getenv('APP_ENV', 'DEV')


class Config(object):
    """Project configuration"""
    MONGO_URI = 'mongodb://localhost:27017/ppvideo'
    # MONGO_URI = 'mongodb://ppvideo:ppvid10123@web01cn.haetek.com:37018/ppvideo'
    ALLOWED_EXTENSIONS = {'mp4'}
    MAX_CONTENT_LENGTH = 200 * 1024 * 1024  # 100MB

    REDIS_HOST = "127.0.0.1"
    REDIS_PORT = 6379

    # REDIS_HOST = "web02cn.haetek.com"
    # REDIS_PORT = 7001
    # REDIS_PASSWORD = "!password123"

    JWT_SECRET = 'TPmi4aLWRbyVq8zu9v82dWYW17/z+UvRnYTt4P6fAXA'
    JWT_EXPIRY_HOURS = 4

    # 上传视频配置
    UPLOAD_ACCESS_ID = 'LTAI4Fs68e8VFj5n5H9nPb9B'
    UPLOAD_ACCESS_ID_SECRET = 'E2C9cejeo4R8FcldFtzmpx5OMf8nVE'

    # 发送短信配置
    SMS_ACCESS_KEY_ID = 'LTAI4FwGgRWdjuPnwTsX482J'
    SMS_ACCESS_KEY_SECRET = 'k5pUQrg93Kg3XVmhpwC61riAs6wsXf'
    # QQ 登录信息
    QQ_CLIENT_ID = '101865881'
    QQ_REDIRECT_URI = 'http://kengine.haetek.com/users/login'
    QQ_STATE = ''
    QQ_CLIENT_SECRET = 'b0cb59d333b1ce6030e8e9619f54c379'

    # 微信登录
    WECHAT_APP_ID = 'wx7287a60bb700fd21'
    WECHAT_REDIRECT_URI = 'http://www.txjava.cn/loginServlet'
    WECHAT_STATE = '3d6be0a4035d839573b04816624a415e#wechat_redirect'
    WECHAT_APP_SECRET = '1ef8755f92bebae8ad7bab432ba29cbf'
    # 邮件发送
    MAIL_SERVER = 'smtp.qq.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = '786960910@qq.com'
    MAIL_PASSWORD = 'gtzhqmgrdjkqbbgi'
    MAIL_DEFAULT_SENDER = 'JamesBy <786960910@qq.com>'
    LOG_LEVEL = logging.INFO


class ProdConfig(Config):
    SECRET_KEY = 'pro'


class DevConfig(Config):
    DEBUG = True
    SECRET_KEY = 'dev'


config = {
    'PROD': ProdConfig,
    'DEV': DevConfig,
}[ENV]()
