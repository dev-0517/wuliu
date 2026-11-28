# -*- coding: utf-8 -*-
"""真实短信发送。支持两个通道（按环境变量自动选择，都没配置则退回演示模式）：
1. Spug 推送短信验证码：SPUG_SMS_URL=https://push.spug.cc/send/xxxx
   （免签名模板审核，参数 to=手机号 code=验证码 number=有效分钟）
2. 阿里云短信：SMS_ACCESS_KEY_ID/SECRET/SIGN_NAME/TEMPLATE_CODE
"""
import base64
import datetime
import hashlib
import hmac
import os
import urllib.parse
import urllib.request

ENDPOINT = "https://dysmsapi.aliyuncs.com/"


def sms_configured() -> bool:
    if os.getenv("SPUG_SMS_URL"):
        return True
    return all([
        os.getenv("SMS_ACCESS_KEY_ID"),
        os.getenv("SMS_ACCESS_KEY_SECRET"),
        os.getenv("SMS_SIGN_NAME"),
        os.getenv("SMS_TEMPLATE_CODE"),
    ])


def send_sms(phone: str, code: str) -> dict:
    """发送验证码短信。成功返回 {}，失败抛异常（含错误信息）。"""
    if os.getenv("SPUG_SMS_URL"):
        return _send_spug(phone, code)
    return _send_aliyun(phone, code)


def _send_spug(phone: str, code: str) -> dict:
    url = os.getenv("SPUG_SMS_URL").rstrip("/")
    qs = urllib.parse.urlencode({"to": phone, "code": code, "number": 5})
    with urllib.request.urlopen(f"{url}?{qs}", timeout=10) as r:
        data = r.read().decode()
    import json
    result = json.loads(data)
    if result.get("code") not in (0, "0", 200, "200"):
        raise RuntimeError(f"spug: {result}")
    return result


def _send_aliyun(phone: str, code: str) -> dict:
    params = {
        "AccessKeyId": os.getenv("SMS_ACCESS_KEY_ID"),
        "Action": "SendSms",
        "Format": "JSON",
        "PhoneNumbers": phone,
        "SignName": os.getenv("SMS_SIGN_NAME"),
        "SignatureMethod": "HMAC-SHA1",
        "SignatureNonce": os.urandom(16).hex(),
        "SignatureVersion": "1.0",
        "TemplateCode": os.getenv("SMS_TEMPLATE_CODE"),
        "TemplateParam": f'{{"code":"{code}"}}',
        "Timestamp": datetime.datetime.now(datetime.timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "Version": "2017-05-25",
    }
    params["Signature"] = _sign(params, os.getenv("SMS_ACCESS_KEY_SECRET", ""))
    url = ENDPOINT + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=10) as r:
        data = r.read().decode()
    import json
    result = json.loads(data)
    if result.get("Code") != "OK":
        raise RuntimeError(f"{result.get('Code')}: {result.get('Message')}")
    return result


def _sign(params: dict, secret: str) -> str:
    sorted_qs = "&".join(
        f"{k}={urllib.parse.quote(str(v), safe='-_.~')}"
        for k, v in sorted(params.items()))
    to_sign = "GET&%2F&" + urllib.parse.quote(sorted_qs, safe="-_.~")
    h = hmac.new((secret + "&").encode(), to_sign.encode(), hashlib.sha1)
    return base64.b64encode(h.digest()).decode()
