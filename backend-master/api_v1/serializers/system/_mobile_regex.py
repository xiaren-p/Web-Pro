"""手机号常量与验证函数。"""
import re

# 中国大陆手机号校验正则
MOBILE_REGEX = re.compile(r"^1[3-9]\d{9}$")
