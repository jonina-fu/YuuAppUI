import requests
import time

BRIDGE_SERVER_URL = "http://127.0.0.1:8766"

def test_only_otp():
    # 直接写死4位测试验证码，不用调用接口
    test_code = "4544"
    payload = {"text": test_code}
    resp = requests.post(f"{BRIDGE_SERVER_URL}/input_otp_split", json=payload, timeout=15)
    res = resp.json()
    print("接口返回结果：", res)
    if res["code"] == 0:
        print("✅ 验证码输入接口执行成功，页面查看是否填充4位数字")
    else:
        print("❌ 输入失败：", res["msg"])

# 单独运行调试
if __name__ == "__main__":
    # 先手动在模拟器打开验证码页面，露出4个输入框
    input("请手动打开验证码页面，按回车开始测试输入：")
    test_only_otp()