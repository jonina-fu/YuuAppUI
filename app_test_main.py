import os
import time
import requests
from dotenv import load_dotenv
from openai import OpenAI
import logging


load_dotenv()
BRIDGE_URL = "http://localhost:8766"

# 初始化大模型客户端
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL")
)

# 封装手机操作函数
def open_app(package_name: str):
    return requests.post(f"{BRIDGE_URL}/open_app", json={"package": package_name}).json()

def click_element(text: str = None, resource_id: str = None):
    return requests.post(f"{BRIDGE_URL}/click", json={"text": text, "id": resource_id}).json()

def input_text(text: str):
    return requests.post(f"{BRIDGE_URL}/input", json={"text": text}).json()

def scroll_screen(direction: str = "down"):
    return requests.post(f"{BRIDGE_URL}/scroll", json={"dir": direction}).json()

def assert_text_exist(target_text: str) -> bool:
    res = requests.post(f"{BRIDGE_URL}/ocr_check", json={"text": target_text})
    return res.json()["exist"]

# 测试任务
test_prompt = """
你是APP自动化测试执行器，根据我的测试流程，一步步调用上面定义的函数执行操作，每执行一步等待2秒，执行完断言：
测试流程：
1. 打开Yuu SIT，包名com.dfg.anfield.sit
2. 如果有开屏页面，点击屏幕右上方的「ignore」，跳过开屏页面
3. 点击中间文字「Log in」
3. 点击文字"+852",2秒后在弹窗中点击+86
4. 在输入框输入13613008664，
5.点击「Get verification code」
6. 等待3秒后，执行脚本get_yuu_otp.py，拿到返回的验证码，输入步骤5跳转后的验证码输入框
7. 点击登录按钮，判断页面包含文字「my coupons」，登录成功
每一步输出执行结果，最后汇总测试是否通过
"""

if __name__ == "__main__":
    print("启动APP自动化测试")
    resp = client.chat.completions.create(
        #model="gpt-4o-mini",
        model='deepseek-v4-pro',
        messages=[{"role": "user", "content": test_prompt}]
    )
    print("AI执行日志：")
    logging.basicConfig(
        filename="test_run_log.txt",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        encoding="utf-8"
    )
    # 打印时同时写入日志
    logging.info("执行启动APP，包名xxx")
    print(resp.choices[0].message.content)