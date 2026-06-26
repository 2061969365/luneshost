import os
import time
import requests
from playwright.sync_api import sync_playwright

SERVER_URL = os.getenv("LUNES_SERVER_URL")
LUNES_EMAIL = os.getenv("LUNES_EMAIL")
LUNES_PASSWORD = os.getenv("LUNES_PASSWORD")

def send_tg_notification(message, photo_path=None):
    """发送结果和截图至 Telegram"""
    token = os.getenv("TG_BOT_TOKEN")
    chat_id = os.getenv("TG_CHAT_ID")
    if not token or not chat_id:
        print("未配置 TG 机器人变量，跳过发送 TG 推送。")
        return

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        requests.post(url, json=payload)
        print("TG 状态通知发送成功。")
    except Exception as e:
        print(f"发送 TG 消息异常: {e}")

    if photo_path and os.path.exists(photo_path):
        try:
            url = f"https://api.telegram.org/bot{token}/sendPhoto"
            with open(photo_path, "rb") as f:
                files = {"photo": f}
                data = {"chat_id": chat_id, "caption": "Lunes Host 实时画面"}
                requests.post(url, data=data, files=files)
            print("TG 截图发送成功。")
        except Exception as e:
            print(f"发送 TG 截图异常: {e}")

def login_lunes(page, email, password):
    """模拟真人输入账号密码直接在 Lunes Host 登录"""
    print("正在尝试使用账号密码登录 Lunes Host...")
    try:
        # 访问登录页
        page.goto("https://betadash.lunes.host/auth/login")
        page.wait_for_timeout(3000)

        if "login" not in page.url:
            page.goto("https://betadash.lunes.host/login")
            page.wait_for_timeout(3000)

        # 1. 输入邮箱/用户名
        username_input = page.locator("input[name='username']").first
        if not username_input.is_visible():
            username_input = page.locator("input[type='text']").first
        if not username_input.is_visible():
            username_input = page.locator("input[type='email']").first
        
        username_input.fill(email)

        # 2. 输入密码
        password_input = page.locator("input[type='password']").first
        password_input.fill(password)

        # 3. 勾选“记住我”
        remember_checkbox = page.locator("input[type='checkbox']").first
        if remember_checkbox.is_visible():
            remember_checkbox.check()

        # 4. 点击登录
        submit_btn = page.locator("button[type='submit']").first
        if not submit_btn.is_visible():
            submit_btn = page.locator("button:has-text('Login')").first
        if not submit_btn.is_visible():
            submit_btn = page.locator("button:has-text('Zaloguj')").first
        if not submit_btn.is_visible():
            submit_btn = page.locator("button:has-text('登录')").first

        submit_btn.click()
        print("登录表单已提交，等待页面跳转...")
        page.wait_for_timeout(10000)

        if "login" in page.url:
            print("❌ 自动登录失败：仍停留在登录页面。")
            return False

        print("✓ 自动登录成功！")
        return True
    except Exception as e:
        print(f"❌ 自动登录过程中发生异常: {e}")
        return False

def run():
    if not SERVER_URL or not LUNES_EMAIL or not LUNES_PASSWORD:
        print("错误: 缺少必要配置 LUNES_SERVER_URL、LUNES_EMAIL 或 LUNES_PASSWORD")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ]
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )

        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        page = context.new_page()

        # 执行自动登录
        if login_lunes(page, LUNES_EMAIL, LUNES_PASSWORD):
            print(f"正在跳转至目标保活控制面板: {SERVER_URL}")
            page.goto(SERVER_URL)
            
            # 停留 15 秒，确保 Lunes 服务器接收到完整的登录活跃打卡心跳
            page.wait_for_timeout(15000)

            # 保存打卡截图
            page.screenshot(path="lunes_debug_screenshot.png")
            print("已截取登录打卡画面。")

            if "login" in page.url or page.locator("input[type='email']").first.is_visible():
                msg = "❌ <b>Lunes Host 登录失效！</b>\n跳转至面板页面时，发现仍处于登录页面状态。"
                print(msg)
                send_tg_notification(msg, "lunes_debug_screenshot.png")
            else:
                msg = "✅ <b>Lunes Host 每日自动登录打卡成功！</b>\n已通过账号密码模式刷新控制面板活跃状态。"
                print(msg)
                send_tg_notification(msg, "lunes_debug_screenshot.png")
        else:
            page.screenshot(path="lunes_debug_screenshot.png")
            msg = "❌ <b>Lunes Host 运行异常</b>\n使用账号密码执行第一步自动登录时失败。"
            print(msg)
            send_tg_notification(msg, "lunes_debug_screenshot.png")

        browser.close()

if __name__ == "__main__":
    run()
