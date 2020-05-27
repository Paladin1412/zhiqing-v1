# -*- coding: utf-8 -*-
"""
regular identify
"""
import re

pwd_re = re.compile(r"^([a-zA-Z0-9])[a-zA-Z0-9-_*/+.~!@#$%^&()]{5,20}$")
name_re = re.compile(
    r"([\u4e00-\u9fa5]{2,4})|([A-Za-z0-9_]{4,16})|([a-zA-Z0-9_\u4e00-\u9fa5]{3,20})}$")
email_re = re.compile(r"^[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$")
mobile_re = re.compile(r"^1[3-9][0-9]{9}$")
url_re = re.compile(r'http[s]?://api\.haetek\.com:9191/static/(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
