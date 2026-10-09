import base64
import hashlib
import hmac
import json
import os
import re
import time
import requests
from datetime import datetime, timezone
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

import env_loader  # noqa: F401  # 加载同目录 .env（密钥不入库）

# ====================== 全局固定配置 ======================
# RSA公钥（Token接口手机号加密使用）
RAW_PUB_KEY = "MIIBojANBgkqhkiG9w0BAQEFAAOCAY8AMIIBigKCAYEA29bkgb2h+r64OwJr9ABxmYl2UuFGXAZwJgc/O39UhafSm6bBsj1o9vCzF4CPku2FCY8wp5scCZTOrsY2Pu3WBHeJyf/4dBOc5VHiC6Zsx7TVRkLoEancvZ8psgv8bi8guSyVg8dOOrCdFi5ghzGwIRqWqyydz/5fXzwSGv07ooV+22HqVHWim9toxcAmJW2Qa9kKyskCu4krPilQinz8LXY+dre8xkBQVyBwu2CHGaqUfA9S58mYWXbWGXiqSch3OwYjFVkAnRnRCWzJmNKzvuumhAAf7I4GRwqK/IlabRci37lG867R4dAf23psS+fFJrAXZ8Irfw5FDaSDUVyXIDlfmq8ip83BMTqIANoauNAqNj+ez3HI2Q/6qDk7Rr5yFmm3l5tcDZu9Zstu5EPgS754aSAzYoMpnbuc7IUA2zDwaMRK2mbOG8K6hhidfc1aCdvqwdUMgavr5IqOlBU0uBNxm6b86UNmLRuKsTDZzZAtHUUezK5oTschlANDGgtzAgMBAAE="
# 真实值在 .env（密钥不入库）：HASE_SIGN_SECRET / HASE_CLIENT_KEY
SIGN_SECRET = os.getenv("HASE_SIGN_SECRET", "")
BASE_URL = "https://npd-gw.dairyfarm-ipaas-df.com"

# Token接口配置
TOKEN_API_PATH = "/testpnhk/pos/loyalty/exp/v1/member/point-conversion/auth/hase/token"
TOKEN_FULL_URL = BASE_URL + TOKEN_API_PATH
# Transfer-in接口配置
TRANSFER_IN_API_PATH = "/testpnhk/pos/loyalty/exp/v1/member/point-conversion/hase/transfer-in"
TRANSFER_IN_FULL_URL = BASE_URL + TRANSFER_IN_API_PATH

CLIENT_ID = "df26c6d6-94c4-4c4f-80f1-1f80eac5bcd6"
CLIENT_KEY = os.getenv("HASE_CLIENT_KEY", "")
# 固定业务参数（Token接口用）
FIX_PHONE = "+8618639475853"
FIX_YUU_ID = "934480179142326"

# 签名path规则：截取 /v1 之后部分
token_split_part = TOKEN_API_PATH.split("/v1")[-1]
TOKEN_SIGN_PATH = f"/v1{token_split_part}"
transfer_split_part = TRANSFER_IN_API_PATH.split("/v1")[-1]
TRANSFER_IN_SIGN_PATH = f"/v1{transfer_split_part}"


# ====================== 通用工具函数 ======================
def get_current_ms_timestamp() -> str:
    return str(int(time.time() * 1000))


def get_sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def generate_signature(method: str, path: str, ts: str, body_str: str, secret: str):
    body_hash = get_sha256_hex(body_str)
    # 签名拼接规则：method\npath\ntimestamp\nbody_sha256
    sign_content = f"{method}\n{path}\n{ts}\n{body_hash}"
    print("================= 签名对账信息 =================")
    print(f"HTTP_METHOD: {method}")
    print(f"签名PATH(/v1起始): {path}")
    print(f"X-Timestamp: {ts}")
    print(f"请求JSON原文: {body_str}")
    print(f"Body SHA256摘要: {body_hash}")
    print(f"完整待签字符串:\n{repr(sign_content)}")
    print("================================================\n")

    hmac_obj = hmac.new(secret.encode("utf-8"), sign_content.encode("utf-8"), hashlib.sha256)
    digest_bytes = hmac_obj.digest()
    return base64.b64encode(digest_bytes).decode("utf-8")


# ====================== Token接口相关工具函数 ======================
def normalizeBase64Key(key_str: str) -> str:
    return key_str.replace("\n", "").replace("\r", "").replace(" ", "")


def normalizePhone(country_code: str, raw_phone: str) -> str:
    return f"{country_code}{raw_phone}"


def load_rsa_public_key(base64_key: str):
    clean_key = normalizeBase64Key(base64_key)
    key_bytes = base64.b64decode(clean_key)
    return serialization.load_der_public_key(key_bytes)


def rsa_encrypt_mobile(country_code: str, raw_phone: str, pub_key) -> str:
    norm_phone = normalizePhone(country_code, raw_phone)
    plain_bytes = norm_phone.encode("utf-8")
    # OAEP-SHA256，MGF1=SHA1 对齐Java原生JDK
    cipher_bytes = pub_key.encrypt(
        plain_bytes,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA1()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return base64.b64encode(cipher_bytes).decode("utf-8")


def verify_phone(phone: str) -> tuple[bool, str, str]:
    reg_mainland = r"^\+861[3-9]\d{9}$"
    reg_hk = r"^\+852[569]\d{7}$"
    if re.fullmatch(reg_mainland, phone):
        return True, "+86", phone.replace("+86", "")
    elif re.fullmatch(reg_hk, phone):
        return True, "+852", phone.replace("+852", "")
    return False, "", ""


def get_hase_token():
    """获取HASE Token接口的accessToken"""
    print("======== 开始获取HASE Token ========\n")
    # 1. 加载RSA公钥
    pub_key = load_rsa_public_key(RAW_PUB_KEY)

    # 2. 校验并处理手机号
    input_phone = FIX_PHONE
    print(f"使用手机号：{input_phone}")
    valid_flag, country_code, raw_mobile = verify_phone(input_phone)
    if not valid_flag:
        raise ValueError(f"手机号格式非法：{input_phone}")

    # 3. RSA加密手机号
    print(f"加密原文(E.164): {normalizePhone(country_code, raw_mobile)}")
    enc_mobile_val = rsa_encrypt_mobile(country_code, raw_mobile, pub_key)
    print(f"加密mobile密文：\n{enc_mobile_val}\n")

    # 4. 构造Token请求体
    req_body = {
        "countryCode": country_code,
        "mobile": enc_mobile_val,
        "yuuId": FIX_YUU_ID
    }
    body_json_str = json.dumps(req_body, separators=(",", ":"), ensure_ascii=False)

    # 5. 生成签名
    timestamp = get_current_ms_timestamp()
    sign_val = generate_signature(
        method="POST",
        path=TOKEN_SIGN_PATH,
        ts=timestamp,
        body_str=body_json_str,
        secret=SIGN_SECRET
    )

    # 6. 构造Token请求头
    headers = {
        "X-Client-Id": CLIENT_ID,
        "X-Client-Secret":CLIENT_KEY,
        "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
        "Content-Type": "application/json",
        "X-Timestamp": timestamp,
        "X-Signature": sign_val,
        "Accept": "*/*",
        "Host": "npd-gw.dairyfarm-ipaas-df.com",
        "Connection": "keep-alive"
    }

    # 7. 发起Token请求
    try:
        resp = requests.post(url=TOKEN_FULL_URL, headers=headers, data=body_json_str, timeout=20)
        print(f"Token接口响应状态码：{resp.status_code}")
        resp_json = resp.json()
        print("Token接口返回JSON：")
        print(json.dumps(resp_json, ensure_ascii=False, indent=2))

        # 8. 提取Token（兼容两种返回格式）
        if "accessToken" in resp_json:
            token = resp_json["accessToken"]
        elif "token" in resp_json:
            token = resp_json["token"]
        elif "data" in resp_json and "accessToken" in resp_json["data"]:
            token = resp_json["data"]["accessToken"]
        elif "data" in resp_json and "token" in resp_json["data"]:
            token = resp_json["data"]["token"]
        else:
            raise KeyError("返回报文中未找到accessToken/token字段")

        print(f"\n✅ 成功获取Token：{token}\n")
        return token

    except Exception as err:
        raise RuntimeError(f"获取Token失败：{str(err)}")


# ====================== 积分转入主逻辑 ======================
def main():
    print("======== HASE 积分转入 transfer-in 接口请求工具 ========\n")

    # 第一步：自动获取Token
    try:
        BEARER_TOKEN = get_hase_token()
        print("BEARER_TOKEN:", BEARER_TOKEN)
    except Exception as e:
        print(f"❌ 获取Token失败：{e}")
        return

    # 第二步：构造积分转入请求参数
    # 1. 实时当前时间，格式：2026-06-25 15:00:29
    #now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(now_utc)
    # 2. PCT + 时间戳数字，保证唯一且有序递增
    serial_num = str(int(time.time() * 1000))
    trans_id = f"HCT{serial_num}"

    # 请求体（动态字段自动生成）
    req_id = f"JfS{serial_num}"
    req_body = {
        "partnerUserId": "1",
        "partnerValue": 300,
        "remark": "TEST IN 123",
        "requestId": req_id,
        "transactionId": trans_id,
        "transactionTime": now_utc,
        "yuuPoints": 600
    }
    # 无空格紧凑JSON，保证摘要一致
    body_json_str = json.dumps(req_body, separators=(",", ":"), ensure_ascii=False)

    # 生成时间戳 + 计算签名
    timestamp = get_current_ms_timestamp()
    sign_val = generate_signature(
        method="POST",
        path=TRANSFER_IN_SIGN_PATH,
        ts=timestamp,
        body_str=body_json_str,
        secret=SIGN_SECRET
    )
    print(f"X-Timestamp：{timestamp}")
    print(f"X-Signature：{sign_val}\n")
    print(f"本次动态单号 transactionId：{trans_id}")
    print(f"本次动态请求ID requestId：{req_id}")
    print(f"本次交易时间 transactionTime：{now_utc}\n")

    # 完整请求头（使用自动获取的Token）
    headers = {
        "X-Client-Id": CLIENT_ID,
        "X-Client-Secret": CLIENT_KEY,
        "Authorization": f"Bearer {BEARER_TOKEN}",
        "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
        "Content-Type": "application/json",
        "X-Timestamp": timestamp,
        "X-Signature": sign_val,
        "Accept": "*/*",
        "Host": "npd-gw.dairyfarm-ipaas-df.com",
        "Connection": "keep-alive"
    }

    # 发起POST请求
    print("======== 发起积分转入接口请求 ========")
    try:
        resp = requests.post(url=TRANSFER_IN_FULL_URL, headers=headers, data=body_json_str, timeout=20)
        print(f"响应状态码：{resp.status_code}")
        print("接口返回数据：")
        print(json.dumps(resp.json(), ensure_ascii=False, indent=2))
    except Exception as err:
        print(f"请求异常失败：{str(err)}")


if __name__ == "__main__":
    main()