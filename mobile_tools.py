import requests
import os
from dotenv import load_dotenv

load_dotenv()
BRIDGE_URL = "http://localhost:8766"

# 1. 启动APP
def open_app(package_name: str):
    """
    打开安卓APP
    :param package_name: 应用包名，如 com.taobao.taobao
    """
    res = requests.post(f"{BRIDGE_URL}/open_app", json={"package": package_name})
    return res.json()

# 2. 点击页面元素
def click_element(text: str = None, resource_id: str = None):
    """
    点击页面按钮/控件
    :param text: 控件显示文字
    :param resource_id: 控件资源ID
    """
    payload = {"text": text, "id": resource_id}
    res = requests.post(f"{BRIDGE_URL}/click", json=payload)
    return res.json()

# 3. 输入文本
def input_text(text: str):
    """在输入框输入文字"""
    res = requests.post(f"{BRIDGE_URL}/input", json={"text": text})
    return res.json()

# 4. 页面滑动
def scroll_screen(direction: str = "down"):
    """滑动页面，支持 up/down/left/right"""
    res = requests.post(f"{BRIDGE_URL}/scroll", json={"dir": direction})
    return res.json()

# 5. 页面文本断言
def assert_text_exist(target_text: str) -> bool:
    """校验页面是否存在指定文字，用于测试断言"""
    res = requests.post(f"{BRIDGE_URL}/ocr_check", json={"text": target_text})
    return res.json()["exist"]

# 6. 截图保存
def capture_screen():
    """截图并保存到test_screenshot文件夹"""
    save_dir = "test_screenshot"
    if not os.path.exists(save_dir):
        os.mkdir(save_dir)
    save_path = f"{save_dir}/screen.png"
    res = requests.get(f"{BRIDGE_URL}/screenshot", json={"path": save_path})
    return save_path


if __name__ == "__main__":
    import time

    PKG = "com.dfg.anfield.sit"

    print("==== 1. 启动 Yuu SIT 应用 ====")
    print(open_app(PKG))
    time.sleep(3)

    print("\n==== 2. 截图保存 ====")
    try:
        path = capture_screen()
        print(f"截图已保存：{path}")
    except Exception as e:
        print(f"截图失败：{e}")

    print("\n==== 3. 断言页面存在「Log in」文字 ====")
    exists = assert_text_exist("Log in")
    print(f"断言结果：{'✅ 通过' if exists else '❌ 未找到'}")