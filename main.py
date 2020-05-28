#!/usr/bin/env python 
# -*- coding: utf-8 -*-
"""
@File     : main.py
@Time     : 2020-03-29 20:44
@Author   : Qi
@Email    : 18821723039@163.com
@Software : PyCharm
"""

from flask import Flask, request, current_app
from flask_apscheduler import APScheduler
from flask_cors import CORS
from flask_mail import Mail
from flask_pymongo import PyMongo

from config.settings import config
from utils import response_code
from utils.log import setup_log
from utils.response_code import ApiException
from utils.setResJson import set_resjson

setup_log()
app = Flask(__name__, instance_relative_config=True)
app.config.from_object(config)
CORS(app, resources=r'/*')
mongo = PyMongo(app)
mail = Mail(app)
scheduler = APScheduler(app)


@app.route("/api/v1/gateway", methods=['POST'])
def index():
    from utils.auth import authenticate
    authenticate()
    model_action = request.form.get('model_action')
    if model_action == 'upload':
        from modules.videos import upload
        resp = upload()
    elif model_action == 'update':
        from modules.videos import upload_update
        resp = upload_update()
    elif model_action == "check":
        from modules.videos import func_check
        resp = func_check()
    elif model_action == "upload_file":
        from modules.data import upload_file
        resp = upload_file()
    else:
        post_data = request.get_json()
        model_name = post_data.get('model_name', "")
        model_action = post_data.get('model_action', "")
        extra_data = post_data.get('extra_data', "")
        # model_type = post_data.get('model_type', "")
        if model_action == "":
            resp = set_resjson(err=-8, errmsg="[ extra_data ] must be provided")
        else:
            if model_name == "video":
                from modules.videos import VideoHandler
                video_main = VideoHandler(extra_data, model_action)
                resp = video_main.handle_model()
            elif model_name == "user":
                from modules.user import UserHandler
                user_main = UserHandler(extra_data, model_action)
                resp = user_main.handle_model()
            # elif model_name == "comment":
            #     from modules.comment import CommentHandler
            #     comment_main = CommentHandler(extra_data, model_action)
            #     resp = comment_main.handle_model()
            elif model_name == "collection":
                from modules.collection import CollectHandler
                comment_main = CollectHandler(extra_data, model_action)
                resp = comment_main.handle_model()
            elif model_name == "like":
                from modules.like import LikeHandler
                comment_main = LikeHandler(extra_data, model_action)
                resp = comment_main.handle_model()
            elif model_name == "series":
                from modules.series import SeriesHandler
                comment_main = SeriesHandler(extra_data, model_action)
                resp = comment_main.handle_model()
            elif model_name == "document":
                from modules.document import DocumentHandler
                comment_main = DocumentHandler(extra_data, model_action)
                resp = comment_main.handle_model()
            elif model_name == "category":
                from modules.category import CategoryHandler
                comment_main = CategoryHandler(extra_data, model_action)
                resp = comment_main.handle_model()
            elif model_name == "subscription":
                from modules.subscription import SubscriptionHandler
                comment_main = SubscriptionHandler(extra_data, model_action)
                resp = comment_main.handle_model()
            elif model_name == "data":
                from modules.data import DataHandler
                comment_main = DataHandler(extra_data, model_action)
                resp = comment_main.handle_model()
            elif model_name == "video_history":
                from modules.history import HistoryHandler
                comment_main = HistoryHandler(extra_data, model_action)
                resp = comment_main.handle_model()
            elif model_name == "home":
                from modules.home import IndexHandler
                comment_main = IndexHandler(extra_data, model_action)
                resp = comment_main.handle_model()
            else:
                resp = set_resjson(err=-1, errmsg="model_name is incorrect")
    return resp


@app.errorhandler(ApiException)
def raise_info(error):
    """
    capture all exception information
    :param error:
    :return:
    """
    if isinstance(error, response_code.ApiException):
        return set_resjson(error.err_code, error.errmsg, [])
    current_app.logger.error(error)
    return set_resjson(error.err_code, errmsg=error)


# @app.errorhandler(Exception)
# def raise_info(error):
#     """
#     capture all exception information
#     :param error:
#     :return:
#     """
#     if isinstance(error, response_code.ApiException):
#         return set_resjson(error.err_code, error.errmsg)
#     current_app.logger.error(error)
#     return set_resjson(err=400, errmsg="{}".format(error))


@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Expose-Headers', 'Authorization')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    if not request.path.startswith('/static/'):
        if 'Content-Type' in response.headers:  # sets the return data type
            response.headers['Content-Type'] = 'application/json'
        else:
            response.headers.add('Content-Type', 'application/json')
        return response
    return response


if __name__ == '__main__':
    # print(app.url_map)
    app.run(host='0.0.0.0', port=8181, debug=True)
