# job_wikipedia.py
# تنها کار این فایل: باز کردن سایت ویکی‌پدیا در مرورگر پیش‌فرض ویندوز.
# فقط کتابخانه‌های استاندارد پایتون — بدون نیاز به pip install.
# بدون ورودی تعاملی (input) و بدون انتظار برای بسته شدن مرورگر.

import webbrowser

URL = "https://fa.wikipedia.org"


def main():
    print("در حال باز کردن ویکی‌پدیا در مرورگر پیش‌فرض...")

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

    print("ویکی‌پدیا در مرورگر باز شد")


if __name__ == "__main__":
    main()
