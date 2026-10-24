# job_telegram_report.py
# کار این فایل: ثبت ۵ پیام گزارش نمونه (فارسی) در صف ربات تلگرام با فاصله ۳۰ ثانیه‌ای.
# از قابلیت ربات تعریف‌شده در فایل پیکربندی استفاده می‌کند:
#   %LOCALAPPDATA%\Windows-Agent\bot_api.json  (کلیدها: send و token)
# فقط کتابخانه‌های استاندارد پایتون — بدون نیاز به pip install.
# بدون ورودی تعاملی (input). کل اجرا چند ثانیه طول می‌کشد چون پیام‌ها یک‌جا با
# تأخیر (delay) وارد صف می‌شوند و خود ربات در زمان مقرر ارسالشان می‌کند.
#
# تأخیرها: ۰، ۳۰، ۶۰، ۹۰ و ۱۲۰ ثانیه — یعنی پنج پیام با فاصله ۳۰ ثانیه از هم.
# اعداد داخل متن پیام‌ها «فرضی/نمونه» هستند و صرفاً برای آزمایش کنترل صف ربات است.

import json
import os
import urllib.error
import urllib.request
from datetime import datetime

# روی ویندوز LOCALAPPDATA همیشه مقدار دارد؛ get با پیش‌فرض خالی فقط برای جلوگیری
# از کرش در محیط‌های غیرویندوزی/غیرعادی است (در main بررسی وجود فایل انجام می‌شود).
CFG = os.path.join(
    os.environ.get("LOCALAPPDATA", ""), "Windows-Agent", "bot_api.json"
)

# فاصله زمانی بین پیام‌ها (ثانیه)
INTERVAL_SECONDS = 30


def tell(text, delay=0, chat_id=None):
    """پیام را به صف ربات تلگرام می‌دهد؛ delay=0 یعنی همین حالا."""
    with open(CFG, encoding="utf-8") as fh:
        cfg = json.load(fh)
    body = json.dumps(
        {"text": text, "delay": delay, "chat_id": chat_id}
    ).encode("utf-8")
    req = urllib.request.Request(
        cfg["send"],
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Agent-Token": cfg["token"],
        },
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def build_messages():
    """پنج پیام گزارش نمونه و متفاوت درباره عملکرد برنامه (اعداد فرضی)."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return [
        (
            "[گزارش ۱ از ۵] گزارش نمونه عملکرد ایجنت همکار\n"
            "سلام! این یک گزارش فرضی برای آزمایش صف پیام تلگرام است.\n"
            f"زمان ثبت گزارش: {now}\n"
            "وضعیت کلی: پایدار — همه سرویس‌های برنامه فعال و در دسترس هستند."
        ),
        (
            "[گزارش ۲ از ۵] آمار کارهای اجراشده (اعداد فرضی)\n"
            "در ۲۴ ساعت گذشته ۱۲ کار اجرا شده است: ۱۱ کار موفق در اجرای نخست،\n"
            "و ۱ کار که پس از یک تلاش مجدد با موفقیت کامل شده است.\n"
            "نرخ موفقیت: ۹۲ درصد."
        ),
        (
            "[گزارش ۳ از ۵] منابع سیستم (اعداد فرضی)\n"
            "میانگین مصرف پردازنده: ۱۸ درصد\n"
            "حافظه RAM: ۲.۴ گیگابایت از ۱۶ گیگابایت\n"
            "فضای آزاد دیسک D: حدود ۸۴ گیگابایت."
        ),
        (
            "[گزارش ۴ از ۵] خروجی‌ها و لاگ‌ها (اعداد فرضی)\n"
            "۸ اسکرین‌شات جدید در پوشه ScreenShots ذخیره شده و\n"
            "۶ فایل لاگ تازه در گوگل درایو بارگذاری شده است.\n"
            "میانگین مدت اجرای هر کار: حدود ۱۴ ثانیه."
        ),
        (
            "[گزارش ۵ از ۵] جمع‌بندی (اعداد فرضی)\n"
            "هیچ خطای بازمانده یا کار ناتمامی وجود ندارد.\n"
            "اجرای بعدی طبق زمان‌بندی برنامه در ساعت مقرر انجام می‌شود.\n"
            "پایان گزارش نمونه — این پیام‌ها صرفاً برای آزمایش ربات ارسال شده‌اند."
        ),
    ]


def main():
    print("در حال آماده‌سازی ۵ پیام گزارش نمونه برای صف ربات تلگرام...")

    # بررسی اولیه فایل پیکربندی تا در صورت نبودش، پیام خطای واضح داده شود
    if not os.path.exists(CFG):
        print(f"خطا: فایل پیکربندی ربات پیدا نشد: {CFG}")
        return

    messages = build_messages()
    queued = 0

    for index, text in enumerate(messages):
        delay = index * INTERVAL_SECONDS  # 0، 30، 60، 90، 120
        try:
            response = tell(text, delay=delay)
            queued += 1
            print(
                f"پیام {index + 1} از ۵ با تأخیر {delay} ثانیه در صف قرار گرفت. "
                f"پاسخ سرور: {json.dumps(response, ensure_ascii=False)}"
            )
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            print(f"خطای HTTP در صف پیام {index + 1} (کد {exc.code}): {detail}")
        except urllib.error.URLError as exc:
            print(f"خطای ارتباطی در صف پیام {index + 1}: {exc.reason}")
        except Exception as exc:
            # شکست یک پیام نباید مانع تلاش برای بقیه پیام‌ها شود
            print(f"خطای غیرمنتظره در صف پیام {index + 1}: {exc}")

    print(f"کار تمام شد؛ {queued} از ۵ پیام با موفقیت در صف ربات قرار گرفت.")


if __name__ == "__main__":
    main()
