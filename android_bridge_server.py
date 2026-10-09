from flask import Flask, request, jsonify
import uiautomator2 as u2
import adbutils
import time

app = Flask(__name__)
# 校验ADB设备
adb = adbutils.AdbClient()
devices = adb.device_list()
if not devices:
    print("【错误】未检测到任何安卓设备，请连接手机并开启USB调试！")
    exit(1)
d = u2.connect(serial=devices[0].serial)
print(f"已连接设备序列号：{devices[0].serial}")

# 全局统一异常捕获，所有接口报错都返回JSON
@app.errorhandler(Exception)
def handle_exception(e):
    return jsonify({"code": -1, "msg": f"服务内部异常：{str(e)}"}), 200

@app.route("/open_app", methods=["POST"])
def open_app():
    data = request.json
    pkg = data["package"]
    d.app_start(pkg, stop=True)
    time.sleep(2)
    return jsonify({"code": 0, "msg": "应用启动成功"})

@app.route("/click", methods=["POST"])
def click():
    data = request.json
    if data.get("text"):
        d.xpath(f"//*[@text='{data['text']}']").click_exists(timeout=3)
    elif data.get("id"):
        d(resourceId=data["id"]).click_exists(timeout=3)
    time.sleep(1)
    return jsonify({"code": 0, "msg": "点击完成"})

@app.route("/input", methods=["POST"])
def input_text():
    try:
        req_data = request.get_json()
        text = req_data.get("text", "")
        if not text:
            return jsonify({"code": -1, "msg": "输入内容不能为空"})

        # 优先尝试激活输入框，双重匹配提升命中率
        edit_text = d(className="android.widget.EditText").wait(timeout=3)
        time.sleep(1.5)

        # 清空原有文字
        d.shell("input keyevent 123")
        time.sleep(0.4)
        d.shell("input keyevent 67")
        time.sleep(0.4)

        # 加长单字符间隔，防止模拟器丢字符
        for char in text:
            d.shell(f"input text {char}")
            time.sleep(0.35)
        time.sleep(1.2)

        # 点击空白关闭软键盘
        d.click(x=80, y=150)
        time.sleep(1.2)

        return jsonify({"code": 0, "msg": f"输入完成并关闭键盘：{text}"})
    except Exception as e:
        return jsonify({"code": -1, "msg": f"输入失败：{str(e)}"})

# 输入验证码（当前APP版本为单个输入框 custom_input_otp，整串输入）
@app.route("/input_otp_split", methods=["POST"])
def input_otp_split():
    try:
        req_data = request.get_json()
        code = req_data.get("text", "")
        # 兼容调用方直接传接口返回的dict，取Token字段
        if isinstance(code, dict):
            code = code.get("Token", "")
        code = str(code).strip()
        if not code:
            return jsonify({"code": -1, "msg": "验证码不能为空"})

        # 定位验证码输入框：优先resourceId精确匹配，兜底取页面EditText，click_exists存在即点击
        clicked = d(resourceId="com.dfg.anfield.sit:id/custom_input_otp").click_exists(timeout=3)
        if not clicked:
            clicked = d(className="android.widget.EditText").click_exists(timeout=3)
        if not clicked:
            return jsonify({"code": -1, "msg": "未找到验证码输入框"})

        time.sleep(0.8)

        # 光标移到末尾后逐位删除，清空残留内容
        d.shell("input keyevent 123")
        time.sleep(0.2)
        for _ in range(len(code) + 4):
            d.shell("input keyevent 67")
            time.sleep(0.1)

        # 逐字符输入，加间隔防止丢字符
        for char in code:
            d.shell(f"input text {char}")
            time.sleep(0.2)

        # 输入完成，按返回键收起软键盘，露出登录按钮
        d.shell("input keyevent 4")
        time.sleep(1.2)
        return jsonify({"code": 0, "msg": f"验证码 {code} 输入完成"})
    except Exception as e:
        return jsonify({"code": -1, "msg": f"验证码输入失败：{str(e)}"})

@app.route("/hide_keyboard", methods=["POST"])
def hide_keyboard():
    try:
        # 模拟返回键，收起软键盘
        d.shell("input keyevent 4")
        time.sleep(0.8)
        return jsonify({"code": 0, "msg": "键盘已收起"})
    except Exception as e:
        return jsonify({"code": -1, "msg": f"收起键盘失败：{str(e)}"})

@app.route("/scroll", methods=["POST"])
def scroll():
    dire = request.json["dir"]
    d.swipe_ext(dire, scale=0.6)
    time.sleep(1)
    return jsonify({"code": 0, "msg": "滑动完成"})

def close_fullscreen_ad(d, wait_sec=8):
    """
    等待并点击右上角广告关闭叉号
    三层兜底：文字匹配→描述匹配→右上角坐标点击
    """
    start = time.time()
    while time.time() - start < wait_sec:
        # 方式1：文字匹配 × / 关闭 / Skip
        if d(textContains="×").exists(timeout=0.3):
            d(textContains="×").click()
            print("已点击广告关闭按钮 ×")
            time.sleep(1)
            return True
        # 方式2：content-desc 关闭按钮
        # if d(descriptionContains="close").exists(timeout=0.3):
        #     d(descriptionContains="close").click()
        #     print("已点击广告关闭按钮")
        #     time.sleep(1)
        #     return True
        # 方式3：兜底直接点击屏幕右上角坐标（通用全屏广告）
        # d.click(x=920, y=110)
        # time.sleep(0.8)
    print(f"{wait_sec}秒内未检测到广告弹窗")
    return False

@app.route("/ocr_check", methods=["POST"])
def ocr_check():
    target = request.json["text"]
    page_xml = d.dump_hierarchy()
    has_text = target in page_xml
    return jsonify({"code":0, "exist": has_text})

@app.route("/screenshot", methods=["GET"])
def screenshot():
    path = request.json.get("path", "./screen.png")
    d.screenshot(path)
    return jsonify({"code":0})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8766, debug=False)