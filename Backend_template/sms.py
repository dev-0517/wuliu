# -*- coding: utf-8 -*-
"""真实短信发送：阿里云短信服务（Dysmsapi）。

通过环境变量 / .env 配置以下项后自动启用真实短信，未配置则由调用方退回演示模式：
    SMS_ACCESS_KEY_ID / SMS_ACCESS_KEY_SECRET   阿里云 AccessKey
    SMS_SIGN_NAME                               短信签名（审核通过后获得）
    SMS_TEMPLATE_CODE                           短信模板 CODE（审核通过后获得）
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
    return all([
        os.getenv("SMS_ACCESS_KEY_ID"),
        os.getenv("SMS_ACCESS_KEY_SECRET"),
        os.getenv("SMS_SIGN_NAME"),
        os.getenv("SMS_TEMPLATE_CODE"),
    ])


def _sign(params: dict, secret: str) -> str:
    sorted_qs = "&".join(
        f"{k}={urllib.parse.quote(str(v), safe='-_.~')}"
        for k, v in sorted(params.items()))
    to_sign = "GET&%2F&" + urllib.parse.quote(sorted_qs, safe="-_.~")
    h = hmac.new((secret + "&").encode(), to_sign.encode(), hashlib.sha1)
    return base64.b64encode(h.digest()).decode()


def send_sms(phone: str, code: str) -> dict:
    """调用阿里云 SendSms 发送验证码。成功返回 {}，失败抛异常（含错误信息）。"""
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
