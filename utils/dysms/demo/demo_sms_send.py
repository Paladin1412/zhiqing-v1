# -*- coding: utf-8 -*-
import sys
import uuid

# from aliyunsdkdysmsapi.request.v20170525 import SendSmsRequest
# from aliyunsdkdysmsapi.request.v20170525 import QuerySendDetailsRequest
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.profile import region_provider

# import const
from utils.dysms.aliyunsdkdysmsapi.request.v20170525 import SendSmsRequest
from utils.dysms.demo import const

"""
短信业务调用接口示例，版本号：v20170525

Created on 2017-06-12

"""
try:
    reload(sys)
    sys.setdefaultencoding('utf8')
except NameError:
    pass
except Exception as err:
    raise err

# 注意：不要更改
REGION = "cn-hangzhou"
PRODUCT_NAME = "Dysmsapi"
DOMAIN = "dysmsapi.aliyuncs.com"

acs_client = AcsClient(const.ACCESS_KEY_ID, const.ACCESS_KEY_SECRET, REGION)
region_provider.add_endpoint(PRODUCT_NAME, REGION, DOMAIN)


def send_sms(business_id, phone_numbers, sign_name, template_code,
             template_param=None):
    smsRequest = SendSmsRequest.SendSmsRequest()
    # 申请的短信模板编码,必填
    smsRequest.set_TemplateCode(template_code)

    # 短信模板变量参数
    if template_param is not None:
        smsRequest.set_TemplateParam(template_param)

    # 设置业务请求流水号，必填。
    smsRequest.set_OutId(business_id)

    # 短信签名
    smsRequest.set_SignName(sign_name)

    # 数据提交方式
    # smsRequest.set_method(MT.POST)

    # 数据提交格式
    # smsRequest.set_accept_format(FT.JSON)

    # 短信发送的号码列表，必填。
    smsRequest.set_PhoneNumbers(phone_numbers)

    # 调用短信发送接口，返回json
    smsResponse = acs_client.do_action_with_exception(smsRequest)

    # TODO 业务处理

    return smsResponse
    # try:
    #     smsResponse = acs_client.do_action_with_exception(smsRequest)
    # except ServerException as e:
    #     # 这里可以添加您自己的错误处理逻辑
    #     # 例如，打印具体的错误信息
    #     print(e)
    #     print(e.get_http_status())
    #     print(e.get_error_code())
    #     print(e.get_error_msg())
    #
    # resp_dict = json.loads(smsResponse.decode('utf-8'))
    # print(resp_dict)


if __name__ == '__main__':
    __business_id = uuid.uuid1()
    # print(__business_id)
    # params = "{\"code\":\"12345\",\"product\":\"云通信\"}"
    params = "{\"code\":\"12345\",\"product\":\"云通信\"}"
    # params = u'{"name":"wqb","code":"12345678","address":"bz","phone":"13000000000"}'
    print(send_sms(__business_id, "13000000000", "云通信测试", "SMS_182545292",
                   params))
