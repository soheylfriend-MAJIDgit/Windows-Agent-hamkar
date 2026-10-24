# job_telegram_report.py
# کار این فایل: ثبت ۵ پیام گزارش نمونه (فارسی) در صف ربات تلگرام با فاصله دقیق ۶۰ ثانیه‌ای.
# از قابلیت ربات تعریف‌شده در فایل پیکربندی استفاده می‌کند:
#   %LOCALAPPDATA%\Windows-Agent\bot_api.json  (کلیدها: send و token)
# فقط کتابخانه‌های استاندارد پایتون — بدون نیاز به pip install.
# بدون ورودی تعاملی (input). کل اجرا چند ثانیه طول می‌کشد چون پیام‌ها یک‌جا با
# ساعت دقیق (scheduled_at) وارد صف می‌شوند و کارگر ربات در زمان مقرر ارسالشان می‌کند.
#
# قرارداد API:
#   - فقط یکی از delay یا scheduled_at مجاز است؛ ارسال هر دو → خطای 400
#     (CONFLICTING_SCHEDULE_FIELDS). این فایل فقط scheduled_at می‌فرستد.
#   - scheduled_at به وقت تهران با افست ثابت +03:30 (از ۱۴۰۴ ساعت تابستانی حذف شده).
#   - پیام اول ۲۰ ثانیه پس از اجرا زمان می‌خورد تا هرگز به خطای PAST_SCHEDULED_TIME
#     نخورد؛ بقیه پیام‌ها دقیقاً هر ۶۰ ثانیه یک‌بار.
#   - سرور در پاسخ، ساعت قطعی ارسال را در scheduled_at و send_at_jalali برمی‌گرداند.
# اعداد داخل متن پیام‌ها «فرضی/نمونه» هستند و صرفاً برای آزمایش کنترل صف ربات است.

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

# روی ویندوز LOCALAPPDATA همیشه مقدار دارد؛ get با پیش‌فرض خالی فقط برای جلوگیری
# از کرش در محیط‌های غیرویندوزی/غیرعادی است (در main بررسی وجود فایل انجام می‌شود).
CFG = os.path.join(
    os.environ.get("LOCALAPPDATA", ""), "Windows-Agent", "bot_api.json"
)

# فاصله دقیق بین پیام‌ها (ثانیه) و حاشیه امن پیش از پیام اول
INTERVAL_SECONDS = 60
FIRST_MESSAGE_LEAD_SECONDS = 20

# افست ثابت تهران (UTC+3:30) — بدون نیاز به پایگاه داده منطقه زمانی خارجی
TEHRAN_TZ = timezone(timedelta(hours=3, minutes=30))


def tell(text, scheduled_at, chat_id=None):
    """پیام را با ساعت دقیق scheduled_at (رشته ISO 8601 با افست) به صف ربات می‌دهد."""
    with open(CFG, encoding="utf-8") as fh:
        cfg = json.load(fh)
    payload = {"text": text, "scheduled_at": scheduled_at}
    if chat_id:
        payload["chat_id"] = chat_id
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        cfg["send"],
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
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
    print("در حال آماده‌سازی ۵ پیام گزارش نمونه برای صف ربات تلگرام (فاصله یک دقیقه)...")

    # بررسی اولیه فایل پیکربندی تا در صورت نبودش، پیام خطای واضح داده شود
    if not os.path.exists(CFG):
        print(f"خطا: فایل پیکربندی ربات پیدا نشد: {CFG}")
        return

    messages = build_messages()

    # مبنای زمان‌بندی: پیام اول با حاشیه امن، بقیه با پله ۶۰ ثانیه‌ای
    base_time = datetime.now(TEHRAN_TZ) + timedelta(seconds=FIRST_MESSAGE_LEAD_SECONDS)
    schedule = [
        base_time + timedelta(seconds=index * INTERVAL_SECONDS)
        for index in range(len(messages))
    ]
    queued = 0

    for index, (text, when) in enumerate(zip(messages, schedule)):
        # حذف میکروثانیه تا خروجی دقیقاً مثل فرمت ISO نمونه مستندات باشد
        scheduled_at = when.replace(microsecond=0).isoformat()
        try:
            response = tell(text, scheduled_at=scheduled_at)
            queued += 1
            confirmed = response.get("send_at_jalali") or response.get("scheduled_at") or scheduled_at
            print(
                f"پیام {index + 1} از ۵ برای ساعت {confirmed} در صف قرار گرفت. "
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
