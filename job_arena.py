# job_arena.py
# کار این فایل:
#   ۱) باز کردن لینک صفحه Arena در مرورگر پیش‌فرض
#   ۲) صبر برای بارگذاری کامل صفحه (با فاصله زمانی)
#   ۳) تایپ متن فارسی در کادر چت و زدن Enter
#   ۴) گرفتن اسکرین‌شات در پایان
# فقط کتابخانه‌های استاندارد پایتون — بدون نیاز به pip install.
# بدون ورودی تعاملی (input) و بدون انتظار برای بسته شدن مرورگر.
#
# نکته فنی: SendKeys ویندوز حروف فارسی (یونیکد) را مستقیم تایپ نمی‌کند؛
# به همین دلیل متن ابتدا داخل کلیپ‌بورد گذاشته می‌شود و بعد با Ctrl+V
# در کادر فعال چت جای‌گذاری (Paste) می‌شود، سپس Enter زده می‌شود.

import os
import subprocess
import time
import webbrowser
from datetime import datetime

URL = "https://arena.ai/agent/01a16a94-648c-7294-8d19-f276beecb74c"

# متنی که باید در کادر چت تایپ و ارسال شود
PROMPT_TEXT = "یک کد دیگه بنویس که سایت ورسل رو باز کنه"

JOB_NAME = "arena"

# پوشه ذخیره اسکرین‌شات‌ها (گوگل درایو)
SCREENSHOT_DIR = r"C:\Users\alibatel\My Drive\Windows-Agent-DB\ScreenShots"

# صبر تا صفحه و کادر چت کاملاً بارگذاری شود (قابل تغییر در صورت اینترنت کند)
PAGE_LOAD_WAIT = 15

# صبر بعد از زدن Enter، پیش از گرفتن اسکرین‌شات
AFTER_ENTER_WAIT = 5


def open_site():
    print("در حال باز کردن لینک Arena در مرورگر پیش‌فرض...")

    opened = False
    try:
        # تلاش برای پیدا کردن و استفاده از مرورگر پیش‌فرض سیستم
        browser = webbrowser.get()
        opened = browser.open(URL, new=2)
    except webbrowser.Error:
        opened = False

    if not opened:
        # اگر مرورگر پیش‌فرض پیدا نشد، روش مستقیم کافی است
        print("مرورگر پیش‌فرض پیدا نشد؛ استفاده از webbrowser.open به‌صورت مستقیم.")
        webbrowser.open(URL)

    print("صفحه Arena در مرورگر باز شد")


def run_hidden_powershell(ps_script, extra_env=None):
    # CREATE_NO_WINDOW + WindowStyle Hidden: پنجره پاورشل روی صفحه باز نمی‌شود
    # تا فوکوس روی مرورگر باقی بماند و کلیدها به کادر چت برسند.
    env = dict(os.environ)
    if extra_env:
        env.update(extra_env)

    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-WindowStyle",
            "Hidden",
            "-Command",
            ps_script,
        ],
        capture_output=True,
        text=True,
        timeout=60,
        creationflags=creation_flags,
        env=env,
    )

    if result.returncode != 0:
        error = result.stderr.strip() or "خطای ناشناخته در PowerShell"
        raise RuntimeError(error)


def type_and_submit():
    # متن از طریق متغیر محیطی به پاورشل داده می‌شود تا هیچ مشکل کوتیشن/یونیکدی پیش نیاید.
    # ^v یعنی Ctrl+V (Paste) و ~ یعنی Enter در زبان SendKeys.
    ps_script = """
Add-Type -AssemblyName System.Windows.Forms
Set-Clipboard -Value $env:ARENA_PROMPT
Start-Sleep -Milliseconds 300
[System.Windows.Forms.SendKeys]::SendWait('^v')
Start-Sleep -Milliseconds 800
[System.Windows.Forms.SendKeys]::SendWait('~')
""".strip()

    run_hidden_powershell(ps_script, extra_env={"ARENA_PROMPT": PROMPT_TEXT})
    print("متن در کادر چت تایپ و Enter زده شد")


def take_screenshot(path):
    # اسکریپت PowerShell: تصویر کل صفحه (همه مانیتورها) را به‌صورت PNG ذخیره می‌کند
    ps_script = f"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$bounds = [System.Windows.Forms.SystemInformation]::VirtualScreen
$bitmap = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($bounds.Left, $bounds.Top, 0, 0, $bitmap.Size)
$bitmap.Save('{path}', [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$bitmap.Dispose()
""".strip()

    run_hidden_powershell(ps_script)


def main():
    # ۱) باز کردن لینک
    open_site()

    # ۲) صبر برای بارگذاری کامل صفحه و کادر چت
    print(f"صبر {PAGE_LOAD_WAIT} ثانیه‌ای برای بارگذاری کامل صفحه...")
    time.sleep(PAGE_LOAD_WAIT)

    # ۳) تایپ متن فارسی و زدن Enter
    try:
        type_and_submit()
    except Exception as exc:
        # حتی اگر تایپ شکست خورد، ادامه می‌دهیم تا اسکرین‌شات وضعیت صفحه را ثبت کند
        print(f"خطا در تایپ/ارسال متن: {exc}")

    # ۴) صبر کوتاه بعد از Enter تا نتیجه ارسال در صفحه دیده شود
    print(f"صبر {AFTER_ENTER_WAIT} ثانیه‌ای پیش از اسکرین‌شات...")
    time.sleep(AFTER_ENTER_WAIT)

    # ۵) اطمینان از وجود پوشه و گرفتن اسکرین‌شات
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_path = os.path.join(
        SCREENSHOT_DIR, f"{JOB_NAME}_{timestamp}.png"
    )

    try:
        take_screenshot(screenshot_path)
        print(f"اسکرین‌شات ذخیره شد: {screenshot_path}")
    except Exception as exc:
        print(f"خطا در گرفتن اسکرین‌شات: {exc}")


if __name__ == "__main__":
    main()
