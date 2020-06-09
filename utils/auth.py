# -*- coding: utf-8 -*-
import functools
from datetime import datetime, timedelta

import jwt
from flask import request, current_app, g

from main import mongo


def encode_auth_token(_id, refresh_token=None):
    """
    Generate authentication Token
    :param _id:
    :return:
    """
    try:
        payload = {
            'exp': datetime.utcnow() + timedelta(
                hours=current_app.config['JWT_EXPIRY_HOURS']),
            'iat': datetime.utcnow(),
            'iss': 'heidunkeji',
            'data': {
                '_id': _id,
                "refresh_token": refresh_token
            }
        }

        token = jwt.encode(payload, current_app.config['JWT_SECRET'],
                           algorithm='HS256').decode()

        return token
    except Exception as e:
        current_app.logger.error(e)
        return None


def query_user_data(func):
    # 使用 @functools.wraps,去装饰函数, 可以保持当前装饰器去装饰的函数名字不变, 如果两个函数名字相同的话,flask会报错
    @functools.wraps(func)
    def wrapper(*args, **kwargs):

        _id = None
        user = None
        try:
            authorization = request.headers.get("Authorization")
            if authorization:
                token = authorization.strip()[7:]
                payload = jwt.decode(token, current_app.config['JWT_SECRET'],
                                     algorithm=['HS256'])
                if payload:
                    _id = payload["data"].get("_id")
                    user = mongo.db.user.find_one({"_id": _id})
        except Exception as e:
            current_app.logger.error(e)
        g.user = user
        return func(*args, **kwargs)

    return wrapper


def authenticate():
    _id = None
    user = None
    try:
        authorization = request.headers.get("Authorization")
        if authorization:
            token = authorization.strip()[7:]
            payload = jwt.decode(token, current_app.config['JWT_SECRET'],
                                 algorithm=['HS256'])
            if payload:
                _id = payload["data"].get("_id")
                # refresh_token = payload["data"].get("refresh_token")
                user = mongo.db.user.find_one({"_id": _id})
    except Exception as e:
        # current_app.logger.error(e)
        pass
    g.user = user
