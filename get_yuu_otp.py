import os

import requests
from datetime import datetime,UTC
from dateutil import parser

import env_loader  # noqa: F401  # 加载同目录 .env（密钥不入库）

# 填入自己的密钥
# API_URL = "https://api.loginradius.com/identity/v2/manage/account/smsotp/passwordlesslogin"

# 后端manage key（真实值在 .env：LR_API_KEY / LR_API_SECRET）
# API_KEY = "738db112-c41d-4647-8203-a9cfb5aba16d"
# API_SECRET = "c287b2ed-e1ab-45f6-86d7-04b2ffbbdd1f"

# 前端key
API_URL = "https://api.loginradius.com/identity/v2/manage/account/smsotp/passwordlesslogin"
API_KEY = os.getenv("LR_API_KEY", "")
API_SECRET = os.getenv("LR_API_SECRET", "")

def get_sms_otp(phone_number: str) -> dict:
    params = {
        "apikey": API_KEY.strip(),
        "apisecret": API_SECRET.strip()
        # "ReturnOtpInResponse": "true"
    }
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "phone": phone_number
    }
    try:
        resp = requests.post(
            url=API_URL,
            params=params,
            json=payload,
            headers=headers,
            timeout=15
        )
        # 打印状态码+返回报文，定位403根源
        print("====接口返回详情====")
        print(f"状态码：{resp.status_code}")
        print(f"返回内容：{resp.text}")
        print("===================")
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as http_err:
        # http错误单独捕获，带上返回文本
        msg = f"HTTP请求异常：{str(http_err)}，接口返回：{resp.text}"
        raise RuntimeError(f"获取验证码接口调用失败: {msg}")
    except Exception as err:
        raise RuntimeError(f"获取验证码接口调用失败: {str(err)}")

def check_token_expired(expire_utc_str: str) -> bool:
    expire_dt = parser.isoparse(expire_utc_str)
    now_utc = datetime.now(UTC)
    return now_utc >= expire_dt


# 如果get_sms_otp返回的token不是验证码，就需要先手动触发再读取返回的验证码
def get_otp_code(step_num: int, target_phone="+8613613008664") -> str:
    try:
        res = get_sms_otp(target_phone)
        real_code = res.get("Token")
        expire_str = res["ExpiresIn"]

        if not real_code:
            raise RuntimeError("接口未返回OTP，请确认接口地址为auth前缀")
        if check_token_expired(expire_str):
            raise RuntimeError("获取的验证码已过期，无法使用")
        print(step_num, "调用接口获取短信验证码", "成功", f"验证码：{real_code}")
        return real_code
    except Exception as e:
        print(step_num, "调用接口获取短信验证码", "失败", f"异常：{str(e)}")
        raise RuntimeError(f"步骤{step_num}失败：{str(e)}")

if __name__ == "__main__":
    result = get_sms_otp("+8613613008664")
    token = result.get("Token")
    expire_time = result.get("ExpiresIn")
    print(f"验证码：{token}，过期时间：{expire_time}")
    if check_token_expired(expire_time):
        print("验证码已过期")
    else:
        print("验证码有效")