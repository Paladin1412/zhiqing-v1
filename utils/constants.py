# -*- coding: utf-8 -*-
# 短信签名
SMS_SIGN = '深圳前海黑顿科技有限公司'

# 短信验证码模板ID
SMS_LOGIN_TEMPLATE_ID = 'SMS_187535502'

# 短信验证码的有效时期
SMS_CODE_REDIS_EXPIRES = 300000

# 短信验证码发送的间隔时间
SEND_SMS_CODE_INTERVAL = 60

# 二维码有效时间
QR_CODE_REDIS_EXPIRES = 120000


# 绑定用户的有效时间
BIND_USER_ACCESS_TOKEN_EXPIRES = 10 * 60000

SAVE_USER_TOKEN_EXPIRES = 10 * 600000
