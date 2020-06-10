# -*- coding: utf-8 -*-
"""
user_login
"""
import datetime
import hashlib
import json
import random
import time
from copy import deepcopy
from threading import Thread
from uuid import uuid1

import jwt
from flask import request, g, current_app, make_response
from flask_mail import Message
from itsdangerous import TimedJSONWebSignatureSerializer as TJSSerializer

from config.settings import config
from main import mongo, mail
from utils import response_code, constants
from utils.auth import encode_auth_token
# from utils.dysms1.send_sms import send_sms
from utils.mongo_id import get_user_id
from utils.redisConnector import redis_conn
from utils.regular import mobile_re, name_re, url_re
from utils.setResJson import set_resjson
from utils.third_login import WeChat, OAuthQQ, get_phone, get_num, WeiBo


class UserHandler(object):
    """
    用户账户
    """
    def __init__(self, extra_data, model_action):
        self.extra_data = extra_data
        self.model_action = model_action
        self.head_shot_path = 'http://api.haetek.com:9191/static/headershot/image.jpeg'
        self.background_path = 'http://api.haetek.com:9191/static/background/background.jpg'
        self.introduction = '好好学习， 天天向上'

    def handle_model(self):
        func_name = 'func_{}'.format(self.model_action)
        func_name = func_name.lower()
        try:
            handle_function = getattr(UserHandler, func_name)
            if self.model_action not in ["generate_qrcode", "logout",
                                         "is_login", "get_information",
                                         "get_data"]:
                if self.extra_data == '':
                    raise response_code.ParamERR(
                        errmsg="[ extra_data ] must be provided ")
            resp = handle_function(self)
        except AttributeError as e:
            resp = set_resjson(err=-4,
                               errmsg="{} is incorrect !".format(
                                   self.model_action))
        return resp

    @staticmethod
    def func_get_information(self):
        """
        获取个人信息
        @return:
        """
        user = g.user
        res_dict = {}
        if not user:
            raise response_code.ParamERR(errmsg="用户未登陆")
        try:
            subscription_counts = mongo.db.subscription.find(
                {"user_id": user["_id"], "state": 0}).count()
            fans_counts = mongo.db.subscription.find(
                {"relation_id": user["_id"], "state": 0}).count()

            video_id_list = [video.get("_id") for video in
                             mongo.db.video.find({"user_id": user["_id"]},
                                                 {"_id": 1})]
            like_counts = mongo.db.like.find({"user_id": user["_id"],
                                              "relation_id": {
                                                  "$in": video_id_list}}).count()

        except Exception as e:
            raise response_code.DatabaseERR(errmsg="{}".format(e))
        res_dict["user_name"] = user["name"]
        res_dict["user_id"] = user["_id"]
        res_dict["birthday"] = user.get("birthday", time.strftime("%Y-%m-%d",
                                                                  time.localtime(
                                                                      user[
                                                                          "create_time"])))
        res_dict["gender"] = user.get("gender", "男")
        res_dict["introduction"] = user["introduction"]
        res_dict["headshot"] = user["headshot"]
        res_dict["background"] = user["background"]
        res_dict["like_counts"] = like_counts
        res_dict["video_counts"] = len(video_id_list)
        res_dict["user_name"] = user["name"]
        res_dict["binding_webchat"] = 1 if user.get("wechat_unionid",
                                                    None) else 0
        res_dict["binding_qq"] = 1 if user.get("qq_unionid", None) else 0
        res_dict["binding_microblog"] = 1 if user.get("microblog_unionid",
                                                      None) else 0
        res_dict["subscription_counts"] = subscription_counts
        res_dict["fans_counts"] = fans_counts
        return set_resjson(res_array=[res_dict])

    def func_generate_code(self):
        """
         Send SMS verification code
        :return:
        """

        mobile = self.extra_data.get("mobile", "")
        if not mobile_re.match('{}'.format(mobile)):
            raise response_code.ParamERR(errmsg="手机号码不正确")

        send_flag = redis_conn.get("send_flag_{}".format(mobile))
        if send_flag:
            raise response_code.ReqERR(errmsg="请求次数过于频繁")

        # sms_code = "%04d" % random.randint(0, 9999)
        sms_code = "6666"

        # encrypted message
        hash1 = hashlib.sha256()
        hash1.update(bytes(sms_code, encoding="utf-8"))
        hash_sms_code = hash1.hexdigest()
        # Using redis transactions, save SMS and flag to redis,
        # SMS expiration time is 300 seconds, flag expiration time is 60 seconds
        try:
            pl = redis_conn.pipeline()
            pl.set("sms_code_%s" % mobile, sms_code,
                   constants.SMS_CODE_REDIS_EXPIRES)
            pl.set("send_flag_%s" % mobile, sms_code,
                   constants.SEND_SMS_CODE_INTERVAL)
            pl.execute()
        except Exception as error:
            current_app.logger.error(error)
            raise response_code.DatabaseERR(errmsg='{}'.format(error))
        # try:
        #
        #     resp = send_sms(mobile, constants.SMS_LOGIN_TEMPLATE_ID, constants.SMS_SIGN, sms_code)
        # except Exception as e:
        #     current_app.logger.error('[send_verification_code] {}'.format(e))
        #     raise response_code.ThirdERR(errmsg='{}'.format(e))
        # resp_dict = json.loads(resp.decode('utf-8'))
        # resp_code = resp_dict.get('Code', 'OK')
        # if resp_code != 'OK':
        #     redis_conn.delete("send_flag_{}".format(mobile))
        #     message = resp_dict.get('Message', '')
        #     current_app.logger.error(message)
        #     raise response_code.ThirdERR(errmsg=message)
        response = make_response(
            set_resjson(
                res_array=[{"code": hash_sms_code, 'real_code': sms_code}]))
        return response

    def func_code_login(self):
        """
        login
        :return:
        """
        _id = None
        mobile = self.extra_data.get("mobile", "")
        code = self.extra_data.get('code', "")
        if not mobile_re.match('{}'.format(mobile)):
            raise response_code.ParamERR(errmsg="手机号码不正确")
        # 手机验证码验证
        sms_verify(mobile, code)

        try:
            user_info = mongo.db.user.find_one({"mobile": '{}'.format(mobile)},
                                               {"headshot": 1, "name": 1})
        except Exception as error:
            current_app.logger.error(error)
            raise response_code.DatabaseERR(errmsg='{}'.format(error))
        now_time = time.time()
        if not user_info:
            _id = get_user_id("id")
            try:

                mongo.db.user.insert_one(
                    {"gender": "男", "birthday": str(datetime.date.today()),
                     "name": ranstr(16), "mobile": '{}'.format(mobile),
                     "_id": _id, "headshot": self.head_shot_path,
                     "create_time": now_time, "login_time": now_time,
                     "background": self.background_path,
                     "introduction": self.introduction})
            except Exception as error:
                current_app.logger.error(error)
                raise response_code.DatabaseERR(errmsg='{}'.format(error))
            user_info = {"name": ranstr(16), "headshot": self.head_shot_path}
        else:
            _id = user_info.pop("_id")
            try:
                mongo.db.user.update_one({"mobile": '{}'.format(mobile)},
                                         {"$set": {"login_time": now_time}})
            except Exception as err:
                current_app.logger.error(err)
                raise response_code.DatabaseERR(errmsg='{}'.format(err))
        # set the token information in the response
        response = make_response(set_resjson(res_array=[user_info]))
        response.headers["Authorization"] = encode_auth_token(_id)
        return response

    @staticmethod
    def func_generate_qrcode(self):
        """
        生成二维码
        :return:
        """
        qrcode = str(uuid1())
        redis_conn.set(qrcode, 0, constants.QR_CODE_REDIS_EXPIRES)
        return set_resjson(res_array=[{"qrcode": qrcode}])

    def func_enquiry_qrcode(self):
        """
        web 询问接口
        :return:
        """

        qrcode = self.extra_data.get('qrcode', '')
        if qrcode == "":
            raise response_code.ParamERR(errmsg='qrcode can not be empty!')
        try:
            qr_state = (redis_conn.get('{}'.format(qrcode)))
        except Exception as e:
            raise response_code.DatabaseERR(errmsg='{}'.format(e))

        if qr_state == "0":
            resp = set_resjson(err=1, errmsg='未扫描')
        elif qr_state == "1":
            resp = set_resjson(err=-2, errmsg='已扫描未登录')
        elif qr_state is None:
            resp = set_resjson(err=-4, errmsg='验证码已过期')
        else:
            try:
                user_info = mongo.db.user.find_one({"_id": qr_state},
                                                   {"name": 1, "headshot": 1,
                                                    "_id": 0})
            except Exception as e:
                raise response_code.DatabaseERR(errmsg="{}".format(e))
            resp = make_response(set_resjson(res_array=[user_info]))
            resp.headers["Authorization"] = encode_auth_token(qr_state)
        return resp

    def func_scan_qrcode(self):
        """
        移动端扫描二维码
        :return:
        """
        user = g.user
        if not user:
            raise response_code.UserERR(errmsg='用户未登录')
        qrcode = self.extra_data.get('qrcode', '')
        try:
            qr_state_byte = redis_conn.get('{}'.format(qrcode))
        except Exception as e:
            raise response_code.DatabaseERR(errmsg='{}'.format(e))
        if not qr_state_byte:
            raise response_code.ParamERR(errmsg='验证码过期')
        try:
            redis_conn.set(qrcode, user['_id'], constants.QR_CODE_REDIS_EXPIRES)
        except Exception as e:
            raise response_code.DatabaseERR(errmsg='{}'.format(e))

        return set_resjson()

    def func_check_mobile(self):
        """
        查看手机号码重复
        @return:
        """
        mobile = self.extra_data.get('mobile', '')
        if not mobile_re.match('{}'.format(mobile)):
            raise response_code.ParamERR(errmsg="手机号码不正确")

        try:
            user_info = mongo.db.user.find_one({"mobile": '{}'.format(mobile)})
        except Exception as error:
            current_app.logger.error(error)
            raise response_code.DatabaseERR(errmsg='{}'.format(error))
        if user_info:
            resp = set_resjson(err=-1, errmsg='This mobile is already exist!')
        else:
            resp = set_resjson(err=0, errmsg="This mobile can be registered!")
        return resp

    @staticmethod
    def func_logout(self):
        """
        logout
        :return:
        """
        user = g.user
        if not user:
            raise response_code.UserERR(errmsg='用户未登录')
        response = make_response(set_resjson())
        logout_time = time.time()
        try:
            del response.headers["Authorization"]
            mongo.db.user.update_one({"_id": user['_id']},
                                     {"$set": {"logout_time": logout_time}})
        except Exception as error:
            current_app.logger.error(error)
            raise response_code.RoleERR(errmsg="{}".format(error))

        return response

    def func_generate_third_qrcode(self):
        """ 生成 url 连接  """
        mode = self.extra_data.get('type', "")
        next1 = self.extra_data.get('next', "")
        display = self.extra_data.get('display', "")
        log_url = None
        if mode not in ["microblog", "qq", "wechat"]:
            raise response_code.ParamERR(errmsg="type is incorrect")
        elif mode == "qq":
            oauth_qq = OAuthQQ(state=next1, display=display)
            log_url = oauth_qq.get_qq_login_url()
        elif mode == "wechat":
            wechat = WeChat(state=next1)
            log_url = wechat.get_wechat_url()
        elif mode == "microblog":
            weibo = WeiBo(state=next1)
            log_url = weibo.get_weibo_login_url()

        return set_resjson(res_array=[{"url": log_url}])

    def func_third_phone_login(self):
        """
        第三方移动端登陆
        """
        access_token = self.extra_data.get("access_token", "")
        openid = self.extra_data.get("openid", "")
        mode = self.extra_data.get('type', "")
        if access_token == "" or openid == "":
            raise response_code.ParamERR(
                errmsg="[ access_token, openid ] must be provided")
        elif mode not in ["qq", "wechat"]:
            raise response_code.ParamERR(errmsg='type must be qq or wechat')
        elif mode == "qq":
            oauth_qq = OAuthQQ(client_id=config.QQ_PHONE_APP_ID,
                               client_secret=config.QQ_PHONE_APP_Key)
            unionid, openid = oauth_qq.get_unionid(access_token)
            try:
                user_info = mongo.db.user.find_one({"qq_unionid": unionid})
            except Exception as e:
                raise response_code.DatabaseERR(errmsg="{}".format(e))
            if not user_info:
                user_info = oauth_qq.get_user_info(access_token, openid)
                try:
                    pl = redis_conn.pipeline()
                    pl.set("unionid_name_%s" % unionid, user_info['nickname'],
                           constants.SMS_CODE_REDIS_EXPIRES)
                    pl.set("unionid_photo_url_%s" % unionid,
                           user_info['figureurl_qq_1'],
                           constants.SMS_CODE_REDIS_EXPIRES)
                    pl.execute()
                except Exception as e:
                    raise response_code.DatabaseERR(errmsg="{}".format(e))
                access_token = generate_save_user_token(unionid, 'qq')

                return set_resjson(res_array=[{"access_token": access_token}])

            else:
                response = not_first_login(user_info)

            return response
        elif mode == 'wechat':
            wechatlogin = WeChat(appid=config.WECHAT_APP_ID,
                                 secret_key=config.WECHAT_APP_SECRET)

            nickname, headimgurl, unionid, gender = wechatlogin.get_user_info(
                access_token, openid)
            try:
                user_info = mongo.db.user.find_one({"wechat_unionid": unionid})
            except Exception as e:
                raise response_code.DatabaseERR(errmsg="{}".format(e))
            if not user_info:
                # 第一次登录
                nickname, headimgurl, unionid = wechatlogin.get_user_info(
                    access_token,
                    openid)
                try:
                    pl = redis_conn.pipeline()
                    pl.set("unionid_name_%s" % unionid, nickname,
                           constants.SMS_CODE_REDIS_EXPIRES)
                    pl.set("unionid_photo_url_%s" % unionid, headimgurl,
                           constants.SMS_CODE_REDIS_EXPIRES)
                    pl.execute()
                except Exception as e:
                    raise response_code.DatabaseERR(errmsg="{}".format(e))
                access_token = generate_save_user_token(unionid, 'wechat')

                return set_resjson(res_array=[{"access_token": access_token}])
            else:
                response = not_first_login(user_info)

            return response

    def func_third_login(self):
        resp = None
        mode = self.extra_data.get('type', "")
        code = self.extra_data.get('code', '')
        if code == '':
            raise response_code.ParamERR(errmsg='code can be not empty')
        elif mode not in ["microblog", "qq", "wechat"]:
            raise response_code.ParamERR(errmsg="type is incorrect")
        elif mode == "qq":
            resp = qq_login(code)
        elif mode == 'wechat':
            resp = wehcat_login(code)
        elif mode == 'microblog':
            resp = weibo_login(code)
        return resp

    def func_third_bind_mobile(self):
        """
        第一次登录绑定账号
        :return:
        """
        access_token = self.extra_data.get('access_token', "")
        mobile = self.extra_data.get('mobile', "")
        code = self.extra_data.get('code', "")
        refresh_token = None
        if access_token == "" or mobile == "" or code == "":
            raise response_code.ParamERR(
                '[access_token, mobile, code] can not be empty!')
        elif not mobile_re.match('{}'.format(mobile)):
            raise response_code.ParamERR(errmsg="Wrong phone number format!")
        sms_verify(mobile, code)
        now_time = time.time()
        unionid, third_type = check_save_user_token(access_token)
        if unionid is None:
            raise response_code.ReqERR(errmsg="access_token is wrong!")
        else:
            try:
                user_info = mongo.db.user.find_one(
                    {"mobile": '{}'.format(mobile)},
                    {'name': 1, 'headshot': 1})
            except Exception as e:
                raise response_code.DatabaseERR(errmsg="{}".format(e))
            if user_info:
                try:
                    _id = user_info.pop('_id')
                    mongo.db.user.update_one({"mobile": '{}'.format(mobile)},
                                             {'$set': {'{}_unionid'.format(
                                                 third_type): unionid,
                                                       "login_time": now_time}})
                except Exception as e:
                    raise response_code.DatabaseERR(errmsg="{}".format(e))
            else:
                _id = get_user_id("id")
                try:
                    name = redis_conn.get("unionid_name_%s" % unionid)
                    headshot = redis_conn.get("unionid_photo_url_%s" % unionid)
                    gender = redis_conn.get("unionid_gender_%s" % unionid)
                    refresh_token = redis_conn.get(
                        "unionid_refresh_token_%s" % unionid)
                    mongo.db.user.insert_one(
                        {"gender": gender,
                         "birthday": str(datetime.date.today()),
                         "name": name, "mobile": '{}'.format(mobile),
                         "_id": _id, '{}_unionid'.format(third_type): unionid,
                         "headshot": headshot,
                         "create_time": now_time, "login_time": now_time,
                         "background": self.background_path,
                         "introduction": self.introduction})
                except Exception as error:
                    current_app.logger.error(error)
                    raise response_code.ThirdERR(errmsg="{}".format(error))

                user_info = {'name': name, 'headshot': headshot}
            response = make_response(set_resjson(res_array=[user_info]))
            response.headers["Authorization"] = encode_auth_token(_id,
                                                                  refresh_token)
            return response

    @staticmethod
    def func_is_login(self):
        """
        判断登陆
        """
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
            return set_resjson(err=-1, errmsg="ERROR")
        if user:
            return set_resjson()

    def func_quick_login(self):
        """
        手机一键登陆
        """
        login_token = self.extra_data.get("login_token", "")
        if login_token == "":
            raise response_code.ParamERR(
                errmsg="[ login_token ] must be provided")

        curl = 'https://api.verification.jpush.cn/v1/web/loginTokenVerify'
        dict_body = {"loginToken": login_token}
        json_body = json.dumps(dict_body)
        encrypt_phone = get_phone(curl, json_body)
        if not encrypt_phone:
            raise response_code.ParamERR(errmsg="登陆失败")
        phone = get_num(encrypt_phone, config.JI_GUANG_PRIKEY)
        user_info = mongo.db.user.find_one({"mobile": phone},
                                           {"headshot": 1, "name": 1})
        now_time = time.time()
        if not user_info:
            _id = get_user_id("id")
            try:

                mongo.db.user.insert_one(
                    {"gender": "男", "birthday": str(datetime.date.today()),
                     "name": ranstr(16), "mobile": '{}'.format(phone),
                     "_id": _id, "headershot": self.head_shot_path,
                     "create_time": now_time, "login_time": now_time,
                     "background": self.background_path,
                     "introduction": self.introduction})
            except Exception as error:
                current_app.logger.error(error)
                raise response_code.DatabaseERR(errmsg='{}'.format(error))
            user_info = {"name": ranstr(16), "headshot": self.head_shot_path}
        else:
            _id = user_info.pop("_id")
            try:
                mongo.db.user.update_one({"mobile": '{}'.format(phone)},
                                         {"$set": {"login_time": now_time}})
            except Exception as err:
                current_app.logger.error(err)
                raise response_code.DatabaseERR(errmsg='{}'.format(err))
        # set the token information in the response
        response = make_response(set_resjson(res_array=[user_info]))
        response.headers["Authorization"] = encode_auth_token(_id)
        return response

    def func_change_information(self):
        """
        编辑个人信息
        @return:
        """
        user = g.user
        if not user:
            raise response_code.UserERR(errmsg='用户未登录')
        gender = self.extra_data.get('gender')
        user_name = self.extra_data.get('user_name')
        birthday = self.extra_data.get('birthday')
        introduction = self.extra_data.get('introduction')
        background = self.extra_data.get('background')
        headshot = self.extra_data.get('headshot')
        if not all([gender, user_name, birthday, introduction, background,
                 headshot]):
            raise response_code.ParamERR(errmsg="Parameter is not complete")
        elif not name_re.match('{}'.format(user_name)):
            raise response_code.ParamERR(errmsg="Incorrect user name format")
        elif not url_re.match(background) or not url_re.match(headshot):
            raise response_code.ParamERR(errmsg="The image url is incorrect")
        elif gender not in ["男", "女", "保密"]:
            response_code.ParamERR(errmsg="gender must be 男 or 女 or 保密")
        is_birthday = verify_date_str_lawyer(birthday)
        if not is_birthday:
            raise response_code.ParamERR(errmsg="birthday Incorrect format")
        user_update_info = {"gender": gender, "name": user_name,
                            "birthday": birthday, "introduction": introduction,
                            "background": background, "data_type": "user",
                            "headshot": headshot, "_id": user["_id"]}
        mongo.db.audit.insert_one(user_update_info)
        return set_resjson()

    def func_verify_mobile(self):
        """
        修改手机号码时验证手机号
        @return:
        """
        user = g.user
        if not user:
            raise response_code.UserERR(errmsg='用户未登录')
        mobile = self.extra_data.get("mobile", "")
        code = self.extra_data.get('code', "")
        if '{}'.format(mobile) != user["mobile"]:
            raise response_code.ParamERR(errmsg="不是原手机号码")
        # 手机验证码验证
        sms_verify(mobile, code)
        token = str(uuid1())
        redis_conn.set("verify_mobile_%s" % mobile, token,
                       constants.VERIFY_MOBILE_REDIS_EXPIRES)
        res_dict = {"token": token}
        return set_resjson(res_array=[res_dict])

    def func_change_mobile(self):
        """
        修改手机号码时更改手机号
        @return:
        """
        user = g.user
        if not user:
            raise response_code.UserERR(errmsg='用户未登录')
        mobile = self.extra_data.get("new_mobile", "")
        code = self.extra_data.get('code', "")
        token = self.extra_data.get('token', "")
        if mobile == "" or code == "" or token == "":
            raise response_code.ParamERR(errmsg="Parameter is not complete")
        elif not mobile_re.match('{}'.format(mobile)):
            raise response_code.ParamERR(errmsg="手机号码不正确")
        elif mobile == user['mobile']:
            raise response_code.ParamERR(errmsg="The phone number hasn't changed")
        # 手机验证码验证
        sms_verify(mobile, code)
        real_token = redis_conn.get("verify_mobile_%s" % mobile)
        if token != real_token:
            raise response_code.ParamERR(errmsg="token is incorrect ")
        else:
            mongo.db.user.update_one(user, {"$set": {"mobile": mobile}})

        return set_resjson()

    def func_remove_binding(self):
        """
        解除第三方绑定
        @return:
        """
        user = g.user
        if not user:
            raise response_code.UserERR(errmsg='用户未登录')
        third_type = self.extra_data.get("type", "")
        if third_type not in ["microblog", "wechat", "qq"]:
            raise response_code.ParamERR(errmsg="type is incorrect")
        elif third_type.lower() == "microblog":
            mongo.db.user.update_one(user, {"$unset": {"wechat_unionid": ""}})
        elif third_type.lower() == "wechat":
            mongo.db.user.update_one(user, {"$unset": {"microblog_unionid": ""}})
        elif third_type.lower() == "qq":
            mongo.db.user.update_one(user, {"$unset": {"qq_unionid": ""}})
        raise set_resjson()

    def func_get_author_information(self):
        """
        作者首页
        @return:
        """
        author_id = self.extra_data.get("author_id", "")
        if author_id == "":
            raise response_code.ParamERR(errmsg="author_id can be not empty")
        author_info = mongo.db.user.find_one({"_id": author_id})
        if not author_info:
            raise response_code.ParamERR(errmsg="author_id is incorrect")
        res_dict = {}
        res_list = []
        video_dict = {}
        data = []
        res_dict["user_id"] = author_info["_id"]
        res_dict["user_name"] = author_info["name"]
        res_dict["background"] = author_info["background"]
        res_dict["headshot"] = author_info["headshot"]
        res_dict["introduction"] = author_info["introduction"]
        res_dict["description_counts"] = mongo.db.subscription.find(
            {"user_id": author_info["_id"], "state": 0}).count()
        res_dict["fans_counts"] = mongo.db.subscription.find(
            {"relation_id": author_info["_id"], "state": 0}).count()
        res_dict["background"] = author_info["background"]
        like_counts = 0
        comment_counts = 0
        view_counts = 0
        for video in mongo.db.video.find(
                {"user_id": author_info["_id"], "series": {"$exists": False}}).sort("upload_time", -1):
            view_counts += video["view_counts"]
            video_like_counts = mongo.db.like.find(
                {"relation_id": video["_id"]}).count()
            like_counts += video_like_counts
            video_comment_counts = mongo.db.comment.find(
                {"video_id": video["_id"], "state": 2}).count()
            comment_counts += video_comment_counts
            video_dict["type"] = "video"
            video_dict["image_path"] = video["image_path"]
            video_dict["video_id"] = video["_id"]
            video_dict["title"] = video["title"]
            video_dict["video_time"] = video["video_time"]
            video_dict["upload_time"] = video["upload_time"]
            video_dict["view_counts"] = video["view_counts"]
            video_dict["like_counts"] = video_like_counts
            video_dict["comment_counts"] = video_comment_counts
            data.append(deepcopy(video_dict))
        series_cursor = mongo.db.series.find({"user_id": author_info["_id"]}).sort("time", -1)
        series_dict = {}
        ser_video_id = []
        for series in series_cursor:
            series_dict["type"] = "series"
            series_dict["image_path"] = series["image_path"]
            series_dict["series_id"] = series["_id"]
            series_dict["title"] = series["title"]
            series_dict["update_time"] = series["time"]
            series_dict["video_counts"] = series.get("video_counts",
                                                      None) if series.get(
                    "video_counts", None) else mongo.db.video.find(
                    {"series": series["_id"]}).count()
            series_dict["update_time"] = series["time"]
            series_view_counts = 0
            for ser_video in mongo.db.video.find({"series": series["_id"]}):
                ser_video_id.append(ser_video["_id"])
                series_view_counts += ser_video["view_counts"]
            series_like_counts = mongo.db.like.find(
                {"relation_id": {"$in": ser_video_id}}).count()
            series_comment_counts = mongo.db.comment.find(
                {"state": 2,
                 "video_id": {"$in": ser_video_id}}).count()
            series_dict["comment_counts"] = series_comment_counts
            series_dict["like_counts"] = series_like_counts
            series_dict["view_counts"] = series_view_counts
            data.append(deepcopy(series_dict))
            like_counts += series_like_counts
            view_counts += series_view_counts
        res_dict["like_counts"] = like_counts
        res_dict["view_counts"] = view_counts
        res_dict["data"] = data
        res_list.append(res_dict)
        return set_resjson(res_array=res_list)


def send_async_email(msg):
    """
    异步发送邮件
    :param msg:
    :return:
    """
    from main import app
    with app.app_context():
        mail.send(msg)


def send_email():
    """
    发送邮件
    :return:
    """
    params_data = request.get_json()
    email = params_data.get('email')
    # msg = Message('你的信',  recipients=['18821723039@163.com'])
    msg = Message('你的信', recipients=[email])
    msg.body = """
    陈平安一脸怀疑，宁姚怒目相视，指着那串文字，“真念‘滚’！此拳悟自于大骊观雨，拳势滚走之势，拳罡如泼墨大雨，跌落人间后，滚走于大骊皇宫之龙壁，倾泻直下！”
    """
    thread = Thread(target=send_async_email, args=(msg,))
    thread.start()
    return {'success': 'hello'}


def sms_verify(mobile, sms_code):
    """
    手机验证码验证
    :param mobile:
    :param sms_code:
    :return:
    """
    try:
        real_sms_code = redis_conn.get("sms_code_{}".format(mobile))
    except Exception as error:
        current_app.logger.error(error)
        raise response_code.DatabaseERR(errmsg="{}".format(error))

    if not real_sms_code:
        raise response_code.DataExistERR

    elif '{}'.format(sms_code) != real_sms_code:
        raise response_code.DataERR(errmsg="短信验证码输入错误")


def wehcat_login(code):
    """
    微信登陆
    :param code:
    :return:
    """

    wechatlogin = WeChat(state='')
    access_token, openid, unionid, refresh_token = wechatlogin.get_access_token(
        code)
    try:
        user_info = mongo.db.user.find_one({"wechat_unionid": unionid})
    except Exception as e:
        raise response_code.DatabaseERR(errmsg="{}".format(e))
    if not user_info:
        # 第一次登录
        nickname, headimgurl, _, gender = wechatlogin.get_user_info(
            access_token,  openid)
        try:
            pl = redis_conn.pipeline()
            pl.set("unionid_name_%s" % unionid, nickname,
                   constants.SMS_CODE_REDIS_EXPIRES)
            pl.set("unionid_gender_%s" % unionid, gender,
                   constants.SMS_CODE_REDIS_EXPIRES)
            pl.set("unionid_refresh_token_%s" % unionid, refresh_token,
                   constants.SMS_CODE_REDIS_EXPIRES)

            pl.set("unionid_photo_url_%s" % unionid, headimgurl,
                   constants.SMS_CODE_REDIS_EXPIRES)
            pl.execute()
        except Exception as e:
            raise response_code.DatabaseERR(errmsg="{}".format(e))
        access_token = generate_save_user_token(unionid, 'wechat')

        return set_resjson(res_array=[{"access_token": access_token}])
    else:
        response = not_first_login(user_info, refresh_token)

    return response


def qq_login(code):
    """
    QQ 登录
    :param code:
    :return:
    """
    oauth_qq = OAuthQQ()
    access_token = oauth_qq.get_access_token(code)
    unionid, openid = oauth_qq.get_unionid(access_token)
    try:
        user_info = mongo.db.user.find_one({"qq_unionid": unionid})
    except Exception as e:
        raise response_code.DatabaseERR(errmsg="{}".format(e))
    if not user_info:
        # 第一次登录
        user_info = oauth_qq.get_user_info(access_token, openid)
        try:
            pl = redis_conn.pipeline()
            pl.set("unionid_name_%s" % unionid, user_info['nickname'],
                   constants.SMS_CODE_REDIS_EXPIRES)
            pl.set("unionid_photo_url_%s" % unionid,
                   user_info['figureurl_qq_1'],
                   constants.SMS_CODE_REDIS_EXPIRES)
            pl.execute()
        except Exception as e:
            raise response_code.DatabaseERR(errmsg="{}".format(e))
        access_token = generate_save_user_token(unionid, 'qq')

        return set_resjson(res_array=[{"access_token": access_token}])

    else:
        response = not_first_login(user_info)

    return response


def weibo_login(code):
    """
    微博登陆
    @param code:
    @return:
    """
    weibo = WeiBo()
    access_token = weibo.get_access_token(code)
    user_info = weibo.get_user_info(access_token)
    return user_info


def generate_save_user_token(unionid, third_type):
    """
    生成自己服务器的access_token
    :param unionid:
    :param third_type:
    :return:
    """
    serializer = TJSSerializer(config.SECRET_KEY,
                               constants.BIND_USER_ACCESS_TOKEN_EXPIRES)
    unionid = serializer.dumps(
        {'unionid': unionid, 'type': third_type})  # access_token 为字节类型
    return unionid.decode()


def check_save_user_token(access_token):
    """
    从flask生成的access_token取出token
    :param access_token:
    :return:
    """
    serializer = TJSSerializer(secret_key=config.SECRET_KEY,
                               expires_in=constants.SAVE_USER_TOKEN_EXPIRES)
    try:
        data = serializer.loads(access_token)
    except Exception as e:
        raise response_code.ThirdERR(errmsg='{}'.format(e))
    else:
        return data['unionid'], data['type']


def not_first_login(user_info, refresh_token=None):
    """ 已经登陆过 """
    _id = user_info['_id']
    login_time = time.time()
    try:
        mongo.db.user.update_one({"_id": '{}'.format(_id)},
                                 {"$set": {"login_time": login_time}})
    except Exception as e:
        raise response_code.DatabaseERR(errmsg="{}".format(e))
    response = make_response(
        set_resjson(res_array=[
            {"name": user_info['name'],
             'headshot': user_info.get('headshot', "")}]))
    response.headers["Authorization"] = encode_auth_token(_id, refresh_token)
    return response


def ranstr(num):
    """
    生成随机字母
    """
    salt = ''
    for i in range(num):
        salt += random.choice(
            'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789')
    return salt


def verify_date_str_lawyer(datetime_str):
    """
    验证日期格式
    @param datetime_str:
    @return:
    """
    try:
        datetime.datetime.strptime(datetime_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False
