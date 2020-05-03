#!/usr/bin/env python 
# -*- coding: utf-8 -*-
"""
@File     : send_sms.py
@Time     : 2020-04-14 21:53
@Author   : Qi
@Email    : 18821723039@163.com
@Software : PyCharm
"""
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest
import json
from config.settings import config

# 注意：不要更改
REGION = "cn-hangzhou"
PRODUCT_NAME = "Dysmsapi"
DOMAIN = "dysmsapi.aliyuncs.com"


def send_sms(phone_numbers, template_code, sign_name, sms_code):
    """
    发送短信
    :param phone_numbers:
    :param template_code:
    :param sign_name:
    :param sms_code:
    :return:
    """
    client = AcsClient(config.SMS_ACCESS_KEY_ID, config.SMS_ACCESS_KEY_SECRET,
                       REGION)

    request = CommonRequest()
    request.set_accept_format('json')
    request.set_domain(DOMAIN)
    request.set_method('POST')
    request.set_protocol_type('https')  # https | http
    request.set_version('2017-05-25')
    request.set_action_name('SendSms')

    request.add_query_param('RegionId', REGION)
    request.add_query_param('PhoneNumbers', "{}".format(phone_numbers))
    request.add_query_param('SignName', "{}".format(sign_name))
    request.add_query_param('TemplateCode', "{}".format(template_code))
    # request.add_query_param('TemplateParam', "{\"code\":\"" + sms_code + "\"}")
    request.add_query_param('TemplateParam', json.dumps({'code': sms_code}))

    response = client.do_action(request)
    # python2:  print(response)
    print(str(response, encoding='utf-8'))
    return response
