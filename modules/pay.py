#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    : pay.py
@Time    : 2020/6/8 10:13
@Author  : Qi
@Email   : 18821723039@163.com
@Software: PyCharm
"""

from flask import g

from config.settings import config
from utils import response_code
from utils.mongo_id import create_uuid
from utils.setResJson import set_resjson


class PaymentHandler(object):
    """
    系列
    """

    def __init__(self, extra_data, model_action):
        self.extra_data = extra_data
        self.model_action = model_action

    def handle_model(self):
        func_name = 'func_{}'.format(self.model_action)
        func_name = func_name.lower()
        try:
            handle_function = getattr(PaymentHandler, func_name)
            if self.model_action not in ["get_series"]:
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
    def func_payment(self):
        """
        支付
        """
        price = self.extra_data.get("price")
        subject = self.extra_data.get("subject")
        user = g.user
        if not user:
            raise response_code.UserERR(errmsg='用户未登录')
        app_private_key_path = 'static/keys/应用私钥2048.txt'  # 应用私钥路径
        alipay_public_key_path = 'static/keys/支付宝公钥2048.txt'  # 支付宝公钥路径

        with open(app_private_key_path, 'r') as f:
            _app_private_key_string = f.read()
        with open(alipay_public_key_path, 'r') as f:
            _alipay_public_key_string = f.read()

        alipay = AliPay(
            appid=config.ALIPAY,
            app_notify_url=None,
            app_private_key_string=_app_private_key_string,
            alipay_public_key_string=_alipay_public_key_string,
            sign_type="RSA2",
            debug=config.ALIPAY_DEBUG
        )
        order_id = create_uuid()
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=int(order_id),  # 商户订单号，时间戳生成即可
            total_amount=str(price),  # 订单金额
            subject=subject,  # 订单标题
            return_url=None,
            notify_url=None,
        )


# 先安装下包
# pip install python-alipay-sdk --upgrade

from alipay import AliPay

app_private_key_path = 'static/keys/应用私钥2048.txt'  # 应用私钥路径
alipay_public_key_path = 'static/keys/支付宝公钥2048.txt'  # 支付宝公钥路径

with open(app_private_key_path, 'r') as f:
    _app_private_key_string = f.read()
with open(alipay_public_key_path, 'r') as f:
    _alipay_public_key_string = f.read()

alipay = AliPay(
    appid="2016102400749416",
    app_notify_url=None,
    app_private_key_string=_app_private_key_string,
    alipay_public_key_string=_alipay_public_key_string,
    sign_type="RSA2",
    debug=True
)


def get_trade_page(total_pay, subject):
    """
    获取支付页面
    :param total_pay:
    :param subject:
    :return:
    """
    order_string = alipay.api_alipay_trade_page_pay(
        out_trade_no=1231231312313,  # 商户订单号，时间戳生成即可
        total_amount=str(total_pay),  # 订单金额
        subject=subject,  # 订单标题
        return_url=None,
        notify_url=None,
    )

    # toDO:数据库插入一条记录

    pay_url = "https://openapi.alipaydev.com/gateway.do?" + order_string  # 返回应答
    return pay_url


def trade_query(order_id):
    while True:
        # 调用支付宝的交易查询接口
        """
        response = {
            "trade_no": # 支付宝交易号
            "code": "10000" # 接口调用是否成功
            "trade_status": "TRADE_SUCCESS" # 支付成功
        }
        """
        response = alipay.api_alipay_trade_query(out_trade_no=order_id)
        code = response.get('code')
        if code == '10000' and response.get('trade_status') == 'TRADE_SUCCESS':
            message = '支付成功'
            trade_no = response.get("trade_no")  # 获取支付宝交易号

            # toDo 更新订单状态，插入trade_no

            return message
        elif code == '40004' or (code == '10000' and response.get(
                "trade_status") == 'WAIT_BUYER_PAY'):
            # 等待买家付款/业务处理失败，可能一会就会成功
            import time
            time.sleep(5)
            continue
        else:
            message = '支付失败'
            return message


# total_pay = 1.25
# subject = '测试text%s' % 1
# pay_url = get_trade_page(total_pay, subject)
# print(pay_url)  # 此地址可以直接访问

order_id = 1231231312313
message = trade_query(order_id)
print(message)
