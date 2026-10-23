# job_folders_report.py
# کار این فایل: گرفتن گزارش پوشه‌های باز (پنجره‌های File Explorer) و ذخیره آن
# در یک فایل متنی فارسی روی دسکتاپ.
# فقط کتابخانه‌های استاندارد پایتون — بدون نیاز به pip install.
# بدون ورودی تعاملی (input) و بدون انتظار برای بسته شدن پنجره‌ای.
#
# فهرست پوشه‌های باز با شیء COM داخلی ویندوز (Shell.Application) از داخل
# PowerShell خوانده می‌شود؛ هیچ پکیجی نصب نمی‌شود و پنجره‌ای هم باز نمی‌شود.

import os
import subprocess
from datetime import datetime

# نام ثابت فایل گزارش روی دسکتاپ (هر اجرا بازنویسی می‌شود؛ تاریخ اجرا داخل متن است)
REPORT_FILENAME = "open_folders_report.txt"

# تبدیل رقم‌های لاتین به فارسی (فقط برای شماره‌گذاری و تعداد، نه مسیر پوشه‌ها)
_PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def to_persian_number(value):
    return str(value).translate(_PERSIAN_DIGITS)


# اسکریپت PowerShell:
#   - مسیر واقعی دسکتاپ را می‌خواند (حتی اگر به OneDrive منتقل شده باشد)
#   - تاریخ شمسی و میلادی می‌سازد
#   - همه پنجره‌های باز File Explorer و مسیر هر پوشه را فهرست می‌کند
# خروجی خط‌به‌خط با جداکننده ||| (کاراکتر | در نام مسیر ویندوز مجاز نیست)
PS_SCRIPT = r"""
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$desktop = [Environment]::GetFolderPath('Desktop')
Write-Output ('DESKTOP|||' + $desktop)

$fa = New-Object System.Globalization.CultureInfo('fa-IR')
$fa.DateTimeFormat.Calendar = New-Object System.Globalization.PersianCalendar
$now = Get-Date
Write-Output ('FADATE|||' + $now.ToString('yyyy/MM/dd HH:mm:ss', $fa))
Write-Output ('GREGDATE|||' + $now.ToString('yyyy-MM-dd HH:mm:ss'))

$shell = New-Object -ComObject Shell.Application
$windows = @($shell.Windows())
$index = 0
foreach ($win in $windows) {
    $path = $null
    try { $path = $win.Document.Folder.Self.Path } catch { $path = $null }
    if ($path) {
        $index++
        $name = [string]$win.LocationName
        if ([string]::IsNullOrWhiteSpace($name)) { $name = Split-Path $path -Leaf }
        Write-Output ('ITEM|||' + $index + '|||' + $name + '|||' + $path)
    }
}
Write-Output ('COUNT|||' + $index)
""".strip()


def run_hidden_powershell(ps_script):
    # CREATE_NO_WINDOW + WindowStyle Hidden: هیچ پنجره پاورشلی روی صفحه باز نمی‌شود.
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
        encoding="utf-8",
        errors="replace",
        timeout=60,
        creationflags=creation_flags,
    )

    if result.returncode != 0:
        error = (result.stderr or "").strip() or "خطای ناشناخته در PowerShell"
        raise RuntimeError(error)

    return result.stdout or ""


def parse_output(output):
    data = {
        "desktop": "",
        "fa_date": "",
        "greg_date": "",
        "count": 0,
        "items": [],
    }

    for line in output.splitlines():
        line = line.strip()
        if not line or "|||" not in line:
            continue
        parts = line.split("|||")
        marker = parts[0]

        if marker == "DESKTOP" and len(parts) >= 2:
            data["desktop"] = parts[1].strip()
        elif marker == "FADATE" and len(parts) >= 2:
            data["fa_date"] = parts[1].strip()
        elif marker == "GREGDATE" and len(parts) >= 2:
            data["greg_date"] = parts[1].strip()
        elif marker == "ITEM" and len(parts) >= 4:
            data["items"].append((parts[2].strip(), parts[3].strip()))
        elif marker == "COUNT" and len(parts) >= 2:
            try:
                data["count"] = int(parts[1].strip())
            except ValueError:
                data["count"] = len(data["items"])

    # شمارش واقعی به‌عنوان مرجع نهایی
    data["count"] = len(data["items"])
    return data


def desktop_fallback():
    # اگر خواندن مسیر دسکتاپ از ویندوز شکست خورد، مسیر پیش‌فرض کاربر
    return os.path.join(os.path.expanduser("~"), "Desktop")


def build_report(data, error_message=None):
    fa_date = data.get("fa_date") or "—"
    greg_date = data.get("greg_date") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    items = data.get("items", [])
    count = len(items)

    lines = []
    lines.append("گزارش پوشه‌های باز (پنجره‌های File Explorer)")
    lines.append("=" * 55)
    lines.append(f"تاریخ و زمان (شمسی): {fa_date}")
    lines.append(f"تاریخ و زمان (میلادی): {greg_date}")
    lines.append(f"تعداد پوشه‌های باز: {to_persian_number(count)}")
    lines.append("")

    if error_message:
        lines.append("هنگام خواندن اطلاعات پوشه‌ها خطا رخ داد:")
        lines.append(error_message)
        lines.append("")

    if count == 0 and not error_message:
        lines.append("هیچ پنجره پوشه بازی باز نیست.")
    elif count > 0:
        lines.append("فهرست پوشه‌های باز:")
        lines.append("-" * 55)
        for idx, (name, path) in enumerate(items, start=1):
            lines.append(f"{to_persian_number(idx)}) نام پوشه: {name}")
            lines.append(f"     مسیر: {path}")
        lines.append("-" * 55)

    lines.append("")
    lines.append("این گزارش به‌صورت خودکار توسط job_folders_report.py ساخته شده است.")
    lines.append("")  # خط خالی پایان فایل
    return "\r\n".join(lines)  # CRLF برای سازگاری کامل با Notepad ویندوز


def main():
    print("در حال تهیه گزارش پوشه‌های باز...")

    data = {
        "desktop": "",
        "fa_date": "",
        "greg_date": "",
        "count": 0,
        "items": [],
    }
    error_message = None

    try:
        output = run_hidden_powershell(PS_SCRIPT)
        data = parse_output(output)
        print(f"تعداد {to_persian_number(data['count'])} پنجره پوشه باز پیدا شد")
    except Exception as exc:
        error_message = str(exc)
        print(f"هشدار: خواندن پوشه‌های باز با خطا مواجه شد: {exc}")

    desktop = data.get("desktop") or desktop_fallback()
    try:
        os.makedirs(desktop, exist_ok=True)
    except Exception as exc:
        # اگر ساخت دسکتاپ هم مشکل داشت، مسیر پیش‌فرض امتحان می‌شود
        print(f"هشدار: مسیر دسکتاپ در دسترس نیست ({exc})؛ از مسیر پیش‌فرض استفاده می‌شود.")
        desktop = desktop_fallback()
        os.makedirs(desktop, exist_ok=True)

    report_path = os.path.join(desktop, REPORT_FILENAME)
    report_text = build_report(data, error_message=error_message)

    # utf-8-sig (با BOM) تا Notepad کلاسیک ویندوز متن فارسی را درست نشان دهد
    with open(report_path, "w", encoding="utf-8-sig", newline="") as report_file:
        report_file.write(report_text)

    print(f"گزارش فارسی ذخیره شد: {report_path}")


if __name__ == "__main__":
    main()
