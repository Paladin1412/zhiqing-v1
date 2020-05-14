# -*- coding: utf-8 -*-
"""
user_login
"""
import base64
import hashlib
import json
import random
import time
import urllib.parse
from threading import Thread
from urllib.request import urlopen
from uuid import uuid1

import jwt
import requests
from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA
from flask import request, g, current_app, make_response
from flask_mail import Message
from itsdangerous import TimedJSONWebSignatureSerializer as TJSSerializer

from config.settings import config
from main import mongo, mail
from utils import response_code, constants
from utils.auth import encode_auth_token
# from utils.dysms1.send_sms import send_sms
from utils.mongo_id import create_uuid
from utils.redisConnector import redis_conn
from utils.regular import mobile_re
from utils.setResJson import set_resjson


class UserHandler(object):
    def __init__(self, extra_data, model_action):
        self.extra_data = extra_data
        self.model_action = model_action
        self.head_shot_path = 'http://api.haetek.com:9191/static/headershot/image.jpeg'

    def handle_model(self):
        func_name = 'func_{}'.format(self.model_action)
        func_name = func_name.lower()
        try:
            handle_function = getattr(UserHandler, func_name)
            if self.model_action not in ["generate_qrcode", "logout"]:
                if self.extra_data == '':
                    raise response_code.ParamERR(
                        errmsg="[ extra_data ] must be provided ")
            resp = handle_function(self)
        except AttributeError as e:
            resp = set_resjson(err=-4,
                               errmsg="{} is incorrect !".format(
                                   self.model_action))
        return resp

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

        sms_code = "%04d" % random.randint(0, 9999)

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
        now_time = str(time.time())
        if not user_info:
            _id = create_uuid()
            try:

                mongo.db.user.insert_one(
                    {"name": ranstr(16), "mobile": '{}'.format(mobile),
                     "_id": _id, "headshot": self.head_shot_path,
                     "create_time": now_time, "login_time": now_time})
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

    def func_logout(self):
        """
        logout
        :return:
        """
        user = g.user
        if not user:
            raise response_code.UserERR(errmsg='用户未登录')
        response = make_response(set_resjson())
        logout_time = str(time.time())
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
        if mode == "qq":
            oauth_qq = OAuthQQ(state=next1, display=display)
            log_url = oauth_qq.get_qq_login_url()
        elif mode == "wechat":
            wechat = WeChat(state=next1)
            log_url = wechat.get_wechat_url()

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
            wechatlogin = WeChat(client_id=config.QQ_PHONE_APP_ID,
                                 client_secret=config.QQ_PHONE_APP_Key)

            unionid, openid = wechatlogin.get_user_info(access_token, openid)
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
        if mode == "qq":
            resp = qq_login(code)
        elif mode == 'wechat':
            resp = wehcat_login(code)
        return resp

    def func_third_bind_mobile(self):
        """
        第一次登录绑定账号
        :return:
        """
        access_token = self.extra_data.get('access_token', "")
        mobile = self.extra_data.get('mobile', "")
        code = self.extra_data.get('code', "")
        if access_token == "" or mobile == "" or code == "":
            raise response_code.ParamERR(
                '[access_token, mobile, code] can not be empty!')
        elif not mobile_re.match('{}'.format(mobile)):
            raise response_code.ParamERR(errmsg="Wrong phone number format!")
        sms_verify(mobile, code)
        now_time = str(time.time())
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
                _id = create_uuid()
                try:
                    name = redis_conn.get("unionid_name_%s" % unionid)
                    headshot = redis_conn.get("unionid_photo_url_%s" % unionid)
                    mongo.db.user.insert_one(
                        {"name": name, "mobile": '{}'.format(mobile),
                         "_id": _id,
                         '{}_unionid'.format(third_type): unionid,
                         "headshot": headshot,
                         "create_time": now_time, "login_time": now_time})
                except Exception as error:
                    current_app.logger.error(error)
                    raise response_code.ThirdERR(errmsg="{}".format(error))

                user_info = {'name': name, 'headshot': headshot}
            response = make_response(set_resjson(res_array=[user_info]))
            response.headers["Authorization"] = encode_auth_token(_id)
            return response

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
        now_time = str(time.time())
        if not user_info:
            _id = create_uuid()
            try:

                mongo.db.user.insert_one(
                    {"name": ranstr(16), "mobile": '{}'.format(phone),
                     "_id": _id, "headershot": self.head_shot_path,
                     "create_time": now_time, "login_time": now_time})
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


def get_phone(curl, json_body):
    """
    获取RSA加密手机号码
    """
    Authorization = str(
        base64.b64encode(
            (config.JI_GUANG_APP_KEY + ':' + config.JI_GUANG_MASTER_KEY).encode(
                'utf-8')), 'utf-8')
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Basic {}".format(Authorization)
    }
    req = requests.post(url=curl, data=json_body, headers=headers)
    req_dict = req.json()
    phone = req_dict['phone']
    return phone


def get_num(phone, prikey):
    """
    RSA解密，获取手机号
    """
    PREFIX = '-----BEGIN RSA PRIVATE KEY-----'
    SUFFIX = '-----END RSA PRIVATE KEY-----'
    key = "{}\n{}\n{}".format(PREFIX, prikey, SUFFIX)
    cipher = PKCS1_v1_5.new(RSA.import_key(key))
    result = cipher.decrypt(base64.b64decode(phone.encode()), None).decode()
    return result


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
    微信登录
    :param code:
    :return:
    """

    wechatlogin = WeChat(state='')
    access_token, openid, unionid = wechatlogin.get_access_token(code)
    try:
        user_info = mongo.db.user.find_one({"wechat_unionid": unionid})
    except Exception as e:
        raise response_code.DatabaseERR(errmsg="{}".format(e))
    if not user_info:
        # 第一次登录
        nickname, headimgurl, _ = wechatlogin.get_user_info(access_token,
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


class WeChat(object):
    """
    微信认证辅助工具类
    """

    def __init__(self, appid=None, state=None, redirect_uri=None,
                 secret_key=None):
        self.appid = appid or config.WECHAT_APP_ID
        self.redirect_uri = redirect_uri or config.WECHAT_REDIRECT_URI
        self.state = state or config.WECHAT_STATE
        self.secret_key = secret_key or config.WECHAT_APP_SECRET

    def get_wechat_url(self):
        """获取微信登录的连接地址"""

        url = 'https://open.weixin.qq.com/connect/qrconnect?'

        params = {
            "appid": self.appid,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "snsapi_login",
            "state": self.state
        }
        url += urllib.parse.urlencode(params)
        return url

    def get_access_token(self, code):
        """ 获取 access_token """
        url = "https://api.weixin.qq.com/sns/oauth2/access_token?"
        params = {
            "appid": self.appid,
            "secret": self.secret_key,
            "code": code,
            "grant_type": "authorization_code"
        }
        url += urllib.parse.urlencode(params)
        resp_dict = send_request_to_third(url)
        if 'errmsg' in resp_dict:
            raise response_code.ThirdERR(errmsg=resp_dict.get('errmsg', ''))
        else:
            access_token = resp_dict.get('access_token', '')
            # refresh_token = resp_dict.get('refresh_token', '')
            openid = resp_dict.get('openid', '')
            unionid = resp_dict.get('unionid', '')

        return access_token, openid, unionid

    @staticmethod
    def get_user_info(access_token, openid):
        """ 获取用户信息 """
        url = 'https://api.weixin.qq.com/sns/userinfo?access_token={}&openid={}'.format(
            access_token, openid)
        # try:
        #     resp = urlopen(url)
        #     resp_byte = resp.read()  # 为 byte 类型
        #     resp_str = resp_byte.decode()  # 转化为 str 类型
        #     resp_dict = json.loads(resp_str)
        # except Exception as e:
        #     current_app.logger.error('获取access_token异常: %s' % e)
        #     raise response_code.ThirdERR(errmsg="{}".format(e))
        resp_dict = send_request_to_third(url)
        if 'errmsg' in resp_dict:
            raise response_code.ThirdERR(errmsg=resp_dict.get('errmsg', ''))
        else:
            nickname = resp_dict.get('nickname', '')
            headimgurl = resp_dict.get('headimgurl', '')
            unionid = resp_dict.get('unionid', '')

        return nickname, headimgurl, unionid


class OAuthQQ(object):
    """
     QQ认证辅助工具类
    """

    def __init__(self, client_id=None, redirect_uri=None, state=None,
                 client_secret=None,
                 display=None):
        # 申请QQ登录成功后,分配给应用的appid
        self.client_id = client_id or config.QQ_CLIENT_ID
        # 成功授权后的回调地址，必须是注册appid时填写的主域名下的地址，建议设置为网站
        self.redirect_uri = redirect_uri or config.QQ_REDIRECT_URI
        # client端的状态值 在这里是前端next带的地址
        self.state = state or config.QQ_STATE
        # 申请QQ登录成功后，分配给网站的appkey
        self.client_secret = client_secret or config.QQ_CLIENT_SECRET
        # 申请qq网址是pc端还是手机端, 默认为pc端, 手机端则传递display=mobile
        self.display = display

    def get_qq_login_url(self):
        """
        获取qq登录的的网址
        :return: url 网址
        """
        url = 'https://graph.qq.com/oauth2.0/authorize?'

        params = {
            "response_type": "code",
            'scope': 'get_user_info',
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": self.state,
            "display": self.display,
        }

        url += urllib.parse.urlencode(params)

        return url

    def get_access_token(self, code):
        """向QQ服务器获取access token"""

        url = "https://graph.qq.com/oauth2.0/token?"
        params = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "client_secret": self.client_secret
        }

        url += urllib.parse.urlencode(params)

        # 向QQ服务器发送请求 access_token
        # access_token=FE04************************CCE2&expires_in=7776000&refresh_token=88E4************************BE14

        try:
            resp = urlopen(url)
            resp_byte = resp.read()  # 为 byte 类型
            resp_str = resp_byte.decode()  # 转化为 str 类型
            resp_dict = urllib.parse.parse_qs(resp_str)
        except Exception as e:
            current_app.logger.error('获取access_token异常: %s' % e)
            raise response_code.ThirdERR(errmsg="{}".format(e))

        else:
            if not resp_dict:
                raise response_code.ParamERR(errmsg='code 失效')
            # access_token取出是一个列表
            access_token_list = resp_dict.get('access_token')
            access_token = access_token_list[0]

        return access_token

    @staticmethod
    def get_openid(access_token):

        url = 'https://graph.qq.com/oauth2.0/me?access_token=' + access_token

        # 向QQ服务器发送请求 openid

        try:
            resp = urlopen(url)
            resp_byte = resp.read()
            resp_str = resp_byte.decode()

            # openid = callback( {"client_id":"YOUR_APPID","openid":"YOUR_OPENID"} );
            # 字符串切割

            resp_date = resp_str[10:-4]
            resp_dict = json.loads(resp_date)

        except Exception as e:
            raise response_code.ThirdERR(errmsg="{}".format(e))
        else:
            openid = resp_dict.get('openid')
        return openid

    def get_user_info(self, access_token, openid):

        url = 'https://graph.qq.com/user/get_user_info?'
        params = {
            "access_token": access_token,
            "oauth_consumer_key": self.client_id,
            "openid": openid
        }

        url += urllib.parse.urlencode(params)
        try:
            resp = urlopen(url)
            resp_byte = resp.read()
            resp_json = json.loads(resp_byte.decode())
        except Exception as e:
            raise response_code.ParamERR(errmsg="{}".format(e))
        return resp_json

    @staticmethod
    def get_unionid(access_token):
        url = 'https://graph.qq.com/oauth2.0/me?access_token={}&unionid=1'.format(
            access_token)
        try:
            resp = urlopen(url)
            resp_byte = resp.read()
            resp_json = json.loads(resp_byte.decode()[10:-4])
            unionid = resp_json.get('unionid')
            openid = resp_json.get('openid')
        except Exception as e:
            raise response_code.ThirdERR(errmsg="{}".format(e))
        return unionid, openid


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


def not_first_login(user_info):
    """ 已经登陆过 """
    _id = user_info['_id']
    login_time = str(time.time())
    try:
        mongo.db.user.update_one({"_id": '{}'.format(_id)},
                                 {"$set": {"login_time": login_time}})
    except Exception as e:
        raise response_code.DatabaseERR(errmsg="{}".format(e))
    response = make_response(
        set_resjson(res_array=[
            {"name": user_info['name'],
             'headshot': user_info.get('headshot', "")}]))
    response.headers["Authorization"] = encode_auth_token(_id)
    return response


def send_request_to_third(url):
    try:
        resp = urlopen(url)
        resp_byte = resp.read()  # 为 byte 类型
        resp_str = resp_byte.decode()  # 转化为 str 类型
        resp_dict = json.loads(resp_str)
    except Exception as e:
        current_app.logger.error('获取access_token异常: %s' % e)
        raise response_code.ThirdERR(errmsg="{}".format(e))
    return resp_dict


def ranstr(num):
    """
    生成随机字母
    """
    salt = ''
    for i in range(num):
        salt += random.choice(
            'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789')

    return salt
