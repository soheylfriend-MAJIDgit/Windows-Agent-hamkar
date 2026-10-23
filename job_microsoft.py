# job_microsoft.py
# کار این فایل: باز کردن سایت مایکروسافت در مرورگر پیش‌فرض و گرفتن اسکرین‌شات در پایان.
# فقط کتابخانه‌های استاندارد پایتون — بدون نیاز به pip install.
# اسکرین‌شات با PowerShell داخلی ویندوز (System.Drawing) گرفته می‌شود.
# بدون ورودی تعاملی (input) و بدون انتظار برای بسته شدن مرورگر.

import os
import subprocess
import time
import webbrowser
from datetime import datetime

URL = "https://www.microsoft.com"
JOB_NAME = "microsoft"

# پوشه ذخیره اسکرین‌شات‌ها (گوگل درایو)
SCREENSHOT_DIR = r"C:\Users\alibatel\My Drive\Windows-Agent-DB\ScreenShots"

# چند ثانیه صبر برای بارگذاری صفحه پیش از اسکرین‌شات
WAIT_SECONDS = 8


def open_site():
    print("در حال باز کردن سایت مایکروسافت در مرورگر پیش‌فرض...")

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

    print("سایت مایکروسافت در مرورگر باز شد")


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

    # CREATE_NO_WINDOW + WindowStyle Hidden: پنجره پاورشل روی صفحه باز نمی‌شود
    # تا مرورگر در لحظه اسکرین‌شات در پیش‌زمینه بماند و روی عکس دیده شود.
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
    )

    if result.returncode != 0:
        error = result.stderr.strip() or "خطای ناشناخته در PowerShell"
        raise RuntimeError(error)


def main():
    # ۱) باز کردن سایت
    open_site()

    # ۲) صبر برای بارگذاری صفحه پیش از اسکرین‌شات
    print(f"صبر {WAIT_SECONDS} ثانیه‌ای برای بارگذاری صفحه پیش از اسکرین‌شات...")
    time.sleep(WAIT_SECONDS)

    # ۳) اطمینان از وجود پوشه اسکرین‌شات‌ها
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    # ۴) گرفتن و ذخیره اسکرین‌شات با نام یکتا (نام کار + زمان اجرا)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_path = os.path.join(
        SCREENSHOT_DIR, f"{JOB_NAME}_{timestamp}.png"
    )

    try:
        take_screenshot(screenshot_path)
        print(f"اسکرین‌شات ذخیره شد: {screenshot_path}")
    except Exception as exc:
        # خطای اسکرین‌شات نباید باعث اجرای ناموفق کل کار شود؛ در لاگ ثبت می‌شود
        print(f"خطا در گرفتن اسکرین‌شات: {exc}")


if __name__ == "__main__":
    main()
