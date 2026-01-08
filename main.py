import os
import time
import requests
from playwright.sync_api import sync_playwright

# 从环境变量获取配置
EMAIL = os.environ.get("ZEABUR_EMAIL")
PASSWORD = os.environ.get("ZEABUR_PASSWORD")
TG_TOKEN = os.environ.get("TG_BOT_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")

def send_telegram_msg(text):
    """发送文字消息"""
    if not TG_TOKEN or not TG_CHAT_ID:
        print("未配置 Telegram Token 或 Chat ID，跳过发送消息")
        return
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": text}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"TG 发送消息失败: {e}")

def send_telegram_photo(text, photo_path):
    """发送带图片的文字消息"""
    if not TG_TOKEN or not TG_CHAT_ID:
        print("未配置 Telegram，跳过发送图片")
        return
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
    try:
        with open(photo_path, 'rb') as f:
            files = {'photo': f}
            data = {'chat_id': TG_CHAT_ID, 'caption': text}
            requests.post(url, data=data, files=files)
    except Exception as e:
        print(f"TG 发送图片失败: {e}")

def run():
    with sync_playwright() as p:
        # 启动浏览器 (headless=True 表示无头模式，在服务器上运行必须为 True)
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()

        try:
            # 1. 登录 Zeabur
            print("正在打开登录页面...")
            page.goto("https://zeabur.com/login")
            
            # 等待输入框出现并填充
            page.wait_for_selector('input[type="email"]')
            page.fill('input[type="email"]', EMAIL)
            page.fill('input[type="password"]', PASSWORD)
            
            # 点击登录按钮 (根据文字或类型查找)
            print("点击登录...")
            # 注意：如果按钮文字变了，这里可能需要调整
            page.click('button[type="submit"]') 
            
            # 等待跳转到控制台
            print("等待跳转到控制台...")
            page.wait_for_url("**/dash.zeabur.com/projects**", timeout=30000)
            time.sleep(5) # 等待页面完全渲染
            
            # 截图登录结果
            login_shot = "login_success.png"
            page.screenshot(path=login_shot)
            send_telegram_photo(f"✅ Zeabur 登录成功\n当前时间: {time.strftime('%Y-%m-%d %H:%M:%S')}", login_shot)

            # 2. 获取所有项目
            # 等待项目列表加载，这里假设项目卡片是链接或特定的 div
            # Zeabur 的项目通常是一个列表，我们需要获取它们的链接
            # 注意：这里假设项目链接包含 /projects/
            project_locators = page.locator('a[href^="/projects/"]')
            count = project_locators.count()
            print(f"发现 {count} 个项目")

            if count == 0:
                send_telegram_msg("⚠️ 未发现任何项目，流程结束。")
                return

            # 获取所有项目的 URL，避免在循环中页面跳转导致元素失效
            project_urls = []
            for i in range(count):
                url = project_locators.nth(i).get_attribute("href")
                if url:
                    project_urls.append(f"https://dash.zeabur.com{url}")

            # 3. 遍历每个项目并重启
            for url in project_urls:
                print(f"正在处理项目: {url}")
                page.goto(url)
                time.sleep(5) # 等待项目详情加载
                
                project_name = page.title() # 获取标题作为项目名
                
                # --- 重启逻辑 ---
                # Zeabur 的重启通常是对具体的 "Service" 进行 Redeploy
                # 这里我们需要寻找 "Redeploy" 或 "Restart" 按钮
                # 由于界面复杂，这里尝试一种通用的逻辑：寻找 Settings -> Redeploy 或者直接寻找 Redeploy 按钮
                
                restarted = False
                try:
                    # 策略：查找页面上可能存在的“重新部署”或“Restart”相关按钮
                    # 注意：这部分非常依赖 Zeabur 当时的 UI。
                    # 假设有一个 "Settings" 选项卡或者直接有 "Redeploy" 按钮
                    
                    # 截图当前项目状态
                    proj_shot = f"project_{time.time()}.png"
                    page.screenshot(path=proj_shot)
                    
                    # 这里模拟点击操作，需根据实际 UI 修改选择器
                    # 示例逻辑：如果页面上有 "Redeploy" 文本的按钮
                    if page.get_by_text("Redeploy").is_visible():
                        page.get_by_text("Redeploy").click()
                        restarted = True
                        msg = f"🔄 项目 [{project_name}] 正在尝试重启..."
                    elif page.get_by_text("Restart").is_visible():
                        page.get_by_text("Restart").click()
                        restarted = True
                        msg = f"🔄 项目 [{project_name}] 正在尝试重启..."
                    else:
                        msg = f"ℹ️ 项目 [{project_name}] 未找到明显的重启按钮，仅截图记录。"
                    
                    # 等待一下操作生效
                    time.sleep(3)
                    send_telegram_photo(msg, proj_shot)

                except Exception as e:
                    print(f"处理项目 {url} 时出错: {e}")
                    send_telegram_msg(f"❌ 处理项目 {url} 出错: {str(e)}")

        except Exception as e:
            print(f"全局错误: {e}")
            # 失败时截图
            page.screenshot(path="error.png")
            send_telegram_photo(f"❌ 脚本执行出错: {str(e)}", "error.png")
        
        finally:
            browser.close()

if __name__ == "__main__":
    run()
