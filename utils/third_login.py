#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    : third_login.py
@Time    : 2020/6/5 13:57
@Author  : Qi
@Email   : 18821723039@163.com
@Software: PyCharm
"""
import base64
import json
import urllib
import urllib.parse
from urllib.request import urlopen

import requests
from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA
from flask import current_app

from config.settings import config
from utils import response_code


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
            refresh_token = resp_dict.get('refresh_token', '')
            openid = resp_dict.get('openid', '')
            unionid = resp_dict.get('unionid', '')

        return access_token, openid, unionid, refresh_token

    @staticmethod
    def get_user_info(access_token, openid):
        """ 获取用户信息 """
        url = 'https://api.weixin.qq.com/sns/userinfo?access_token={}&openid={}'.format(
            access_token, openid)
        resp_dict = send_request_to_third(url)
        if 'errmsg' in resp_dict:
            raise response_code.ThirdERR(errmsg=resp_dict.get('errmsg', ''))
        else:
            nickname = resp_dict.get('nickname', '')
            headimgurl = resp_dict.get('headimgurl', '')
            unionid = resp_dict.get('unionid', '')
            gender = resp_dict.get('gender', "男")

        return nickname, headimgurl, unionid, gender


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


class WeiBo(object):
    """
    微博
    """

    def __init__(self, appid=None, state=None, redirect_uri=None,
                 secret_key=None):
        self.appid = appid or config.MICROBLOG_CLIENT_ID
        self.redirect_uri = redirect_uri or config.MICROBLOG_REDIRECT_URI
        self.state = state or config.MICROBLOG_STATE
        self.secret_key = secret_key or config.MICROBLOG_CLIENT_SECRET

    def get_weibo_login_url(self):
        """
        获取微博登录的的网址
        :return: url 网址
        """
        url = 'https://api.weibo.com/oauth2/authorize?'
        params = {
            "client_id": self.appid,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            # 'scope': 'get_user_info'
        }
        url += urllib.parse.urlencode(params)

        return url

    def get_access_token(self, code):
        """向weibo服务器获取access token"""

        url = "https://api.weibo.com/oauth2/access_token?"
        params = {
            "client_id": self.appid,
            "client_secret": self.secret_key,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
            "code": code
        }
        url += urllib.parse.urlencode(params)
        try:
            resp = requests.post(url).content.decode()
            resp_dict = json.loads(resp)
        except Exception as e:
            current_app.logger.error('获取access_token异常: %s' % e)
            raise response_code.ThirdERR(errmsg="{}".format(e))
        else:
            if not resp_dict or resp_dict.get("error"):
                raise response_code.ParamERR(errmsg='code 失效 {}'.format(
                    resp_dict.get("error_description")))
            access_token = resp_dict.get('access_token')
        return access_token

    @staticmethod
    def get_user_info(access_token):

        url = 'https://api.weibo.com/2/users/show.json?'
        params = {
            "access_token": access_token,
            "screen_name": "screen_name"}

        url += urllib.parse.urlencode(params)
        print(url)
        try:
            resp = urlopen(url)
            resp_byte = resp.read()
            resp_json = json.loads(resp_byte.decode())
        except Exception as e:
            raise response_code.ParamERR(errmsg="{}".format(e))
        return resp_json


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
