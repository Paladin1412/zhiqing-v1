# -*- coding: utf-8 -*-
"""
regular identify
"""
import re

pwd_re = re.compile(r"^([a-zA-Z0-9])[a-zA-Z0-9-_*/+.~!@#$%^&()]{5,20}$")
name_re = re.compile(r"^([a-zA-Z])[a-zA-Z0-9-_*/+.~!@#$%^&()]{5,20}$")
email_re = re.compile(r"^[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$")
mobile_re = re.compile(r"^1[3-9][0-9]{9}$")
