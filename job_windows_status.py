# job_windows_status.py
# کار این فایل: تهیه گزارش وضعیت ویندوز شامل «پوشه‌های باز» و «برنامه‌های دارای پنجره باز»،
# با تاریخ و ساعت جلالی در ابتدای گزارش، و ذخیره در یک فایل متنی روی دسکتاپ.
# فقط کتابخانه‌های استاندارد پایتون — بدون نیاز به pip install.
# بدون ورودی تعاملی (input). همه اطلاعات با PowerShell مخفی و COM داخلی ویندوز خوانده می‌شود.

import json
import os
import subprocess
from datetime import datetime

# نام ثابت فایل گزارش روی دسکتاپ (هر اجرا بازنویسی می‌شود؛ تاریخ اجرا داخل متن است)
REPORT_FILENAME = "windows_status_report.txt"

# تبدیل رقم‌های لاتین به فارسی (برای شمارش و شماره‌گذاری؛ شناسه‌ها و مسیرها لاتین می‌مانند)
_PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def to_persian_number(value):
    return str(value).translate(_PERSIAN_DIGITS)


# اسکریپت PowerShell:
#   - مسیر واقعی دسکتاپ را می‌خواند (حتی اگر به OneDrive منتقل شده باشد)
#   - تاریخ جلالی (شمسی) و میلادی می‌سازد
#   - پوشه‌های باز (پنجره‌های File Explorer) را با Shell.Application فهرست می‌کند
#   - برنامه‌های دارای پنجره باز را از روی پردازه‌ها با MainWindowTitle می‌گیرد
# خروجی: یک رشته JSON فشرده که در پایتون تجزیه می‌شود (عنوان پنجره‌ها ممکن است
# شامل کاراکترهای خاص باشند، برای همین به‌جای جداکننده متنی از JSON استفاده شده است).
PS_SCRIPT = r"""
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$desktop = [Environment]::GetFolderPath('Desktop')

$fa = New-Object System.Globalization.CultureInfo('fa-IR')
$fa.DateTimeFormat.Calendar = New-Object System.Globalization.PersianCalendar
$now = Get-Date

$folders = @()
$shell = New-Object -ComObject Shell.Application
foreach ($win in @($shell.Windows())) {
    $path = $null
    try { $path = $win.Document.Folder.Self.Path } catch { $path = $null }
    if ($path) {
        $name = [string]$win.LocationName
        if ([string]::IsNullOrWhiteSpace($name)) { $name = Split-Path $path -Leaf }
        $folders += [pscustomobject]@{ name = $name; path = $path }
    }
}

$programs = @()
foreach ($p in Get-Process) {
    $title = [string]$p.MainWindowTitle
    if (-not [string]::IsNullOrWhiteSpace($title)) {
        $programs += [pscustomobject]@{
            process = [string]$p.ProcessName
            title   = $title
            pid     = [int]$p.Id
        }
    }
}

$result = [pscustomobject]@{
    desktop  = $desktop
    faDate   = $now.ToString('yyyy/MM/dd HH:mm:ss', $fa)
    gregDate = $now.ToString('yyyy-MM-dd HH:mm:ss')
    folders  = $folders
    programs = $programs
}
$result | ConvertTo-Json -Depth 5 -Compress
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


def as_list(value):
    # PowerShell 5.1 گاهی آرایه تک‌عضوی را به‌صورت یک شیء و آرایه خالی را خالی برمی‌گرداند
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    return []


def collect_data():
    raw = run_hidden_powershell(PS_SCRIPT)
    data = json.loads(raw)
    return {
        "desktop": str(data.get("desktop") or ""),
        "fa_date": str(data.get("faDate") or ""),
        "greg_date": str(data.get("gregDate") or ""),
        "folders": as_list(data.get("folders")),
        "programs": as_list(data.get("programs")),
    }


def desktop_fallback():
    return os.path.join(os.path.expanduser("~"), "Desktop")


def build_report(data, error_message=None):
    fa_date = data.get("fa_date") or "—"
    greg_date = data.get("greg_date") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    folders = data.get("folders", [])
    programs = data.get("programs", [])

    computer_name = os.environ.get("COMPUTERNAME", "—")
    user_name = os.environ.get("USERNAME", "—")

    lines = []
    # تاریخ و ساعت جلالی در ابتدای گزارش — طبق خواسته
    lines.append("گزارش وضعیت ویندوز — پوشه‌ها و برنامه‌های باز")
    lines.append("=" * 60)
    lines.append(f"تاریخ و ساعت جلالی: {fa_date}")
    lines.append(f"تاریخ و ساعت میلادی: {greg_date}")
    lines.append(f"نام کامپیوتر: {computer_name}    کاربر: {user_name}")
    lines.append("")

    if error_message:
        lines.append("هنگام جمع‌آوری اطلاعات خطا رخ داد:")
        lines.append(error_message)
        lines.append("")

    # بخش ۱: پوشه‌های باز
    lines.append("بخش ۱ — پوشه‌های باز (پنجره‌های File Explorer)")
    lines.append("-" * 60)
    lines.append(f"تعداد پوشه‌های باز: {to_persian_number(len(folders))}")
    if not folders:
        lines.append("هیچ پنجره پوشه بازی باز نیست.")
    else:
        for idx, item in enumerate(folders, start=1):
            name = str(item.get("name") or "—")
            path = str(item.get("path") or "—")
            lines.append(f"{to_persian_number(idx)}) نام پوشه: {name}")
            lines.append(f"     مسیر: {path}")
    lines.append("")

    # بخش ۲: برنامه‌های دارای پنجره باز
    lines.append("بخش ۲ — برنامه‌های باز (پردازه‌های دارای پنجره)")
    lines.append("-" * 60)
    lines.append(f"تعداد برنامه‌های باز: {to_persian_number(len(programs))}")
    if not programs:
        lines.append("هیچ پنجره برنامه‌ای شناسایی نشد.")
    else:
        for idx, item in enumerate(programs, start=1):
            process = str(item.get("process") or "—")
            title = str(item.get("title") or "—")
            pid = item.get("pid")
            pid_text = str(pid) if pid is not None else "—"  # شناسه لاتین می‌ماند تا قابل استفاده باشد
            lines.append(
                f"{to_persian_number(idx)}) برنامه: {process} | "
                f"عنوان پنجره: {title} | PID: {pid_text}"
            )
    lines.append("-" * 60)
    lines.append("")
    lines.append("این گزارش به‌صورت خودکار توسط job_windows_status.py ساخته شده است.")
    lines.append("")
    return "\r\n".join(lines)  # CRLF برای سازگاری کامل با Notepad ویندوز


def main():
    print("در حال جمع‌آوری وضعیت ویندوز (پوشه‌ها و برنامه‌های باز)...")

    data = {
        "desktop": "",
        "fa_date": "",
        "greg_date": "",
        "folders": [],
        "programs": [],
    }
    error_message = None

    try:
        data = collect_data()
        print(
            "اطلاعات جمع‌آوری شد: "
            f"{to_persian_number(len(data['folders']))} پوشه باز، "
            f"{to_persian_number(len(data['programs']))} برنامه باز"
        )
    except Exception as exc:
        error_message = str(exc)
        print(f"هشدار: جمع‌آوری اطلاعات با خطا مواجه شد: {exc}")

    desktop = data.get("desktop") or desktop_fallback()
    try:
        os.makedirs(desktop, exist_ok=True)
    except Exception as exc:
        print(f"هشدار: مسیر دسکتاپ در دسترس نیست ({exc})؛ از مسیر پیش‌فرض استفاده می‌شود.")
        desktop = desktop_fallback()
        os.makedirs(desktop, exist_ok=True)

    report_path = os.path.join(desktop, REPORT_FILENAME)
    report_text = build_report(data, error_message=error_message)

    # utf-8-sig (با BOM) تا Notepad کلاسیک ویندوز متن فارسی را درست نشان دهد
    with open(report_path, "w", encoding="utf-8-sig", newline="") as report_file:
        report_file.write(report_text)

    print(f"گزارش وضعیت ذخیره شد: {report_path}")


if __name__ == "__main__":
    main()
