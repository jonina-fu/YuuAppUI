import time
import requests
from dotenv import load_dotenv
from android_bridge_server import d,close_fullscreen_ad
from get_yuu_otp import get_sms_otp

# 加载环境配置
load_dotenv()
BRIDGE_SERVER_URL = "http://localhost:8766"

# 全局存储测试步骤记录，用于最后汇总报告
test_records = []
is_all_pass = True


def print_step_log(step_num: int, operate_name: str, result: str, detail: str):
    """统一打印步骤日志，记录测试结果，失败标记全局失败"""
    global is_all_pass
    record = {
        "step": step_num,
        "operate": operate_name,
        "result": result,
        "detail": detail
    }
    test_records.append(record)
    print(f"\n==================== 步骤{step_num} | {result} ====================")
    print(f"操作：{operate_name}")
    print(f"详情：{detail}")
    if result == "失败":
        is_all_pass = False
    # 强制每步等待2秒
    time.sleep(2)


# -------------------------- 设备操作封装函数 --------------------------
def open_app(package_name: str, step_num: int):
    """启动APP"""
    try:
        resp = requests.post(f"{BRIDGE_SERVER_URL}/open_app", json={"package": package_name})
        resp_data = resp.json()
        if resp_data.get("code") == 0:
            print_step_log(step_num, f"启动应用{package_name}", "成功", f"服务返回:{resp_data}")
        else:
            print_step_log(step_num, f"启动应用{package_name}", "失败", f"服务返回:{resp_data}")
        return resp_data
    except Exception as e:
        print_step_log(step_num, f"启动应用{package_name}", "失败", f"接口异常：{str(e)}")
        return None


def click_by_text(text: str, step_num: int, desc: str):
    """根据文字点击页面控件"""
    try:
        payload = {"text": text, "id": None}
        resp = requests.post(f"{BRIDGE_SERVER_URL}/click", json=payload)
        resp_data = resp.json()
        if resp_data.get("code") == 0:
            print_step_log(step_num, desc, "成功", f"点击文字「{text}」，返回:{resp_data}")
        else:
            print_step_log(step_num, desc, "失败", f"点击文字「{text}」失败，返回:{resp_data}")
        return resp_data
    except Exception as e:
        print_step_log(step_num, desc, "失败", f"点击接口异常：{str(e)}")
        return None


def input_text_content(input_str: str, step_num: int, desc: str):
    """输入文本到输入框"""
    """
       调用bridge服务输入手机号，失败直接终止脚本
       :param input_str: 待输入手机号
       :param step_num: 步骤编号
       :param desc: 步骤描述
       """
    try:
        url = f"{BRIDGE_SERVER_URL}/input"
        payload = {"text": input_str}
        resp = requests.post(url, json=payload, timeout=40)
        res = resp.json()

        if res.get("code") != 0:
            err_msg = f"输入接口异常：{res.get('msg')}"
            print(f"【步骤{step_num}】{desc} 失败｜{err_msg}")
            raise RuntimeError(err_msg)

        print(f"【步骤{step_num}】{desc} 成功｜已输入内容：{input_str}")
        return res

    except Exception as e:
        err_msg = f"输入手机号异常：{str(e)}"
        print(f"【步骤{step_num}】{desc} 失败｜{err_msg}")
        raise RuntimeError(f"步骤{step_num} 中断：{err_msg}")


def page_text_assert(target_text: str, step_num: int, desc: str) -> bool:
    """页面文本断言，判断文字是否存在"""
    try:
        resp = requests.post(f"{BRIDGE_SERVER_URL}/ocr_check", json={"text": target_text})
        resp_data = resp.json()
        exist_flag = resp_data.get("exist", False)
        if exist_flag:
            print_step_log(step_num, desc, "成功", f"页面成功识别文字「{target_text}」")
        else:
            print_step_log(step_num, desc, "失败", f"页面未找到文字「{target_text}」")
        return exist_flag
    except Exception as e:
        print_step_log(step_num, desc, "失败", f"断言接口异常：{str(e)}")
        return False

# 分段输入验证码
def input_split_code(input_str: str, step_num: int, desc: str):
    try:
        payload = {"text": input_str}
        resp = requests.post(f"{BRIDGE_SERVER_URL}/input_otp_split", json=payload, timeout=40)
        res = resp.json()
        if res.get("code") != 0:
            err_msg = f"分段验证码输入异常：{res.get('msg')}"
            print(f"【步骤{step_num}】{desc} 失败｜{err_msg}")
            raise RuntimeError(err_msg)
        print(f"【步骤{step_num}】{desc} 成功｜已分段输入验证码 {input_str}")
        return res
    except Exception as e:
        err_msg = f"输入验证码异常：{str(e)}"
        print(f"【步骤{step_num}】{desc} 失败｜{err_msg}")
        raise RuntimeError(f"步骤{step_num} 中断：{err_msg}")


# 各类一次性弹窗的按钮候选（引导跳过、系统权限，兼容中英文）
SKIP_BUTTONS = ("略過", "Skip")
PERMISSION_BUTTONS = ("仅使用期间允许", "允许本次使用", "仅此一次", "While using the app", "Only this time")


def click_if_any(candidates, wait=0.5) -> bool:
    """依次尝试候选文字，命中即点击"""
    for t in candidates:
        if d(text=t).exists(timeout=wait):
            d(text=t).click()
            print(f"已点击弹窗按钮「{t}」")
            time.sleep(2)
            return True
    return False


def click_any_text(candidates: list, step_num: int, desc: str) -> bool:
    """依次尝试候选文字点击（兼容中英文界面），命中任一即成功"""
    for t in candidates:
        try:
            if d(text=t).click_exists(timeout=2):
                print_step_log(step_num, desc, "成功", f"点击文字「{t}」")
                return True
        except Exception as e:
            print(f"点击「{t}」异常：{e}")
    print_step_log(step_num, desc, "失败", f"未找到可点击文字：{candidates}")
    return False


def handle_post_login_setup(max_rounds=10) -> bool:
    """处理登录后的一次性设置页：语言选择弹窗、引导页、系统权限弹窗，直到主页出现或超时"""
    for _ in range(max_rounds):
        try:
            xml = d.dump_hierarchy()
            if "My coupons" in xml:
                return True
            if d(text="English - 英文").exists(timeout=0.5):
                d(text="English - 英文").click()
                time.sleep(1)
                d(text="確定").click_exists(timeout=2)
                print("已选择语言 English 并确认")
                time.sleep(2)
                continue
            if click_if_any(SKIP_BUTTONS) or click_if_any(PERMISSION_BUTTONS):
                continue
            time.sleep(1.5)
        except Exception as e:
            print(f"处理登录后设置异常：{e}")
            time.sleep(1.5)
    return "My coupons" in d.dump_hierarchy()


def dismiss_intro(max_rounds=8) -> bool:
    """关闭启动阶段的引导页/语言弹窗/权限弹窗，直到出现登录入口或主页"""
    for _ in range(max_rounds):
        try:
            if "My coupons" in d.dump_hierarchy():
                return True
            if d(text="English - 英文").exists(timeout=0.5):
                d(text="English - 英文").click()
                time.sleep(1)
                d(text="確定").click_exists(timeout=2)
                print("已选择语言 English 并确认")
                time.sleep(2)
                continue
            if click_if_any(SKIP_BUTTONS) or click_if_any(PERMISSION_BUTTONS):
                continue
            if d(text="Log in").exists(timeout=0.5) or d(text="登入").exists(timeout=0.5):
                return True
            time.sleep(1.5)
        except Exception as e:
            print(f"处理引导页异常：{e}")
            time.sleep(1.5)
    return "My coupons" in d.dump_hierarchy()


# -------------------------- 主测试流程执行 --------------------------
if __name__ == "__main__":
    print("============== YUU SIT 登录自动化测试开始 ==============")

    def login_flow(step: int) -> int:
        """执行一轮登录操作（引导页→登录入口→区号→手机号→验证码→登录按钮），返回下一个步骤号"""
        # 先跳过首次启动的引导页/语言弹窗
        dismiss_intro()

        # 点击登录入口（中英文兼容）
        click_any_text(["Log in", "登入"], step, "点击登录入口进入手机号登录页")
        step += 1

        # 先点开区号下拉弹窗，再选+86
        click_by_text(text="+852", step_num=step, desc="打开区号下拉弹窗")
        step += 1
        time.sleep(2)
        click_by_text(text="+86", step_num=step, desc="选中区号+86")
        step += 1
        time.sleep(2)

        # 激活输入框后输入手机号
        d(className="android.widget.EditText").click_exists(timeout=3)
        input_text_content(input_str="13613008664", step_num=step, desc="输入手机号")
        step += 1
        time.sleep(2)

        # 点击获取验证码；若键盘遮挡未跳转到OTP页，收起键盘重试一次
        click_any_text(["Get verification code", "獲取驗證碼"], step, "点击获取验证码按钮")
        step += 1
        time.sleep(3)
        if not d(resourceId="com.dfg.anfield.sit:id/custom_input_otp").exists(timeout=5):
            d.shell("input keyevent 4")
            time.sleep(1.5)
            click_any_text(["Get verification code", "獲取驗證碼"], step, "收起键盘后重试点击获取验证码")
            step += 1
            time.sleep(3)

        # 请求验证码接口并填入
        otp_res = get_sms_otp("+8613613008664")
        otp_code = str(otp_res.get("Token")).strip()
        print("短信真实验证码：", otp_code)
        input_split_code(input_str=otp_code, step_num=step, desc="输入短信验证码")
        step += 1
        time.sleep(1.2)

        # 点击登录按钮（中英文兼容）
        click_any_text(["Login", "登入"], step, "点击登录按钮")
        step += 1
        time.sleep(2)
        return step

    # 步骤1：打开Yuu SIT，包名com.dfg.anfield.sit
    open_app(package_name="com.dfg.anfield.sit", step_num=1)

    step = 2
    for attempt in (1, 2):
        try:
            step = login_flow(step)
            break
        except RuntimeError as e:
            print(f"\n>>> 第{attempt}轮登录尝试中断：{e}")
            if attempt == 1:
                print(">>> 重启应用后自动重试 <<<\n")
                open_app(package_name="com.dfg.anfield.sit", step_num=step)
                step += 1

    # 关闭全屏广告，处理登录后一次性设置（语言弹窗/引导页）
    close_fullscreen_ad(d, wait_sec=10)
    handle_post_login_setup()

    # 首次安装/清数据后，登录可能被一次性设置中断并弹回登录页，自动补一轮
    xml = d.dump_hierarchy()
    if "My coupons" not in xml and ("登入" in xml or "Log in" in xml):
        print("\n>>> 登录被初始设置弹回登录页，自动重试登录 <<<\n")
        try:
            step = login_flow(step)
            close_fullscreen_ad(d, wait_sec=10)
            handle_post_login_setup()
        except RuntimeError as e:
            print(f"重试登录中断：{e}")

    # 最终断言：页面包含「My coupons」
    page_text_assert(target_text="My coupons", step_num=step, desc="登录成功断言：校验页面存在My coupons")

    # ===================== 输出完整测试汇总报告 =====================
    print("\n\n==================== 测试执行汇总报告 ====================")
    for record in test_records:
        print(f"步骤{record['step']:2d} | {record['result']:<4} | {record['operate']:<40} | {record['detail']}")

    if is_all_pass:
        print("\n✅ 测试结论：全部步骤执行通过，登录流程测试成功")
    else:
        print("\n❌ 测试结论：存在失败步骤，登录流程测试不通过，请查看上方失败日志")