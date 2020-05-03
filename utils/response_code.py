# coding:utf-8
"""
exception info
"""


class ApiException(Exception):
    """
    customize the total exception class
    """

    def __init__(self, err_code, errmsg):
        self.err_code = err_code
        self.errmsg = errmsg

    @property
    def data(self):
        return self.errmsg

    @property
    def code(self):
        return self.err_code


class DatabaseERR(ApiException):
    """ database error """

    def __init__(self, err_code="4001", errmsg="数据库查询错误"):
        super(DatabaseERR, self).__init__(err_code, errmsg)


class NoData(ApiException):
    """ no data """

    def __init__(self, err_code="4002", errmsg="验证码已过期"):
        super(NoData, self).__init__(err_code, errmsg)


class DataExistERR(ApiException):
    """ data exist """

    def __init__(self, err_code="4003", errmsg="短信验证码已过期"):
        super(DataExistERR, self).__init__(err_code, errmsg)


class DataERR(ApiException):
    """ data error """

    def __init__(self, err_code="4004", errmsg="数据错误"):
        super(DataERR, self).__init__(err_code, errmsg)


class TokenERR(ApiException):
    """ token error"""

    def __init__(self, err_code="4101", errmsg="用户认证信息错误"):
        super(TokenERR, self).__init__(err_code, errmsg)


class ParamERR(ApiException):
    """ param error """

    def __init__(self, err_code="4103", errmsg="参数不足"):
        super(ParamERR, self).__init__(err_code, errmsg)


class UserERR(ApiException):
    """ user error """

    def __init__(self, err_code="4104", errmsg="用户不存在"):
        super(UserERR, self).__init__(err_code, errmsg)


class PasswordERR(ApiException):
    """  password error """

    def __init__(self, err_code="4106", errmsg="密码错误"):
        super(PasswordERR, self).__init__(err_code, errmsg)


class ThirdERR(ApiException):
    """ third error """

    def __init__(self, err_code="4301", errmsg="第三方错误"):
        super(ThirdERR, self).__init__(err_code, errmsg)


class RoleERR(ApiException):
    """ user identity error """

    def __init__(self, err_code="4301", errmsg="用户身份错误"):
        super(RoleERR, self).__init__(err_code, errmsg)


class ReqERR(ApiException):
    """ request error """

    def __init__(self, err_code="4201", errmsg="非法请求或请求次数受限"):
        super(ReqERR, self).__init__(err_code, errmsg)


class OAuthQQAPIError(ApiException):
    """ QQ request error"""
    def __init__(self, err_code="4301", errmsg="请求QQ服务器失败"):
        super(OAuthQQAPIError, self).__init__(err_code, errmsg)
