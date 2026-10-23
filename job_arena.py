# job_arena.py
# کار این فایل:
#   ۱) باز کردن لینک صفحه Arena در مرورگر پیش‌فرض
#   ۲) صبر برای بارگذاری کامل صفحه (با فاصله زمانی)
#   ۳) بررسی وجود پنجره "Was this task successful?":
#        - اگر نبود → مستقیم سراغ تایپ می‌رود
#        - اگر بود → آخرین دکمه "Yes" را کلیک می‌کند، کمی صبر می‌کند، بعد تایپ می‌کند
#   ۴) تایپ متن فارسی در کادر چت و زدن Enter
#   ۵) گرفتن اسکرین‌شات در پایان
# فقط کتابخانه‌های استاندارد پایتون — بدون نیاز به pip install.
# بدون ورودی تعاملی (input) و بدون انتظار برای بسته شدن مرورگر.
#
# نکته فنی ۱: SendKeys ویندوز حروف فارسی (یونیکد) را مستقیم تایپ نمی‌کند؛
# متن ابتدا داخل کلیپ‌بورد گذاشته می‌شود و بعد با Ctrl+V جای‌گذاری می‌شود.
# نکته فنی ۲: تشخیص متن و کلیک روی دکمه‌ها با UI Automation داخلی ویندوز
# (UIAutomationClient) از داخل PowerShell انجام می‌شود، نه با پکیج پایتونی.

import os
import subprocess
import time
import webbrowser
from datetime import datetime

URL = "https://arena.ai/agent/01a16a94-648c-7294-8d19-f276beecb74c"

# متنی که باید در کادر چت تایپ و ارسال شود
PROMPT_TEXT = "یک کد دیگه بنویس که سایت ورسل رو باز کنه"

# عبارتی که قبل از تایپ باید در صفحه بررسی شود
DIALOG_PHRASE = "Was this task successful?"

JOB_NAME = "arena"

# پوشه ذخیره اسکرین‌شات‌ها (گوگل درایو)
SCREENSHOT_DIR = r"C:\Users\alibatel\My Drive\Windows-Agent-DB\ScreenShots"

# صبر تا صفحه و کادر چت کاملاً بارگذاری شود (قابل تغییر در صورت اینترنت کند)
PAGE_LOAD_WAIT = 15

# چند بار و با چه فاصله‌ای وجود پنجره تأیید بررسی شود
DIALOG_CHECK_ATTEMPTS = 3
DIALOG_CHECK_GAP = 3

# صبر بعد از کلیک روی Yes، پیش از تایپ
DIALOG_CLICK_WAIT = 3

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


def run_hidden_powershell(ps_script, extra_env=None, timeout=60):
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
        timeout=timeout,
        creationflags=creation_flags,
        env=env,
    )

    if result.returncode != 0:
        error = result.stderr.strip() or "خطای ناشناخته در PowerShell"
        raise RuntimeError(error)

    return result.stdout or ""


# اسکریپت UI Automation:
#   - پنجره مرورگرها را پیدا می‌کند
#   - دنبال متن "Was this task successful?" می‌گردد
#   - اگر پیدا کرد، همه دکمه‌های Yes را جمع می‌کند و آخرینشان را کلیک می‌کند
# خروجی: یکی از نشانه‌های ARENA_DIALOG_CLICKED / ARENA_DIALOG_NOT_FOUND /
# ARENA_DIALOG_FOUND_BUT_NO_YES
DIALOG_PS_SCRIPT = r"""
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$dialogPhrase = 'WAS_THIS_TASK_SUCCESSFUL'
$browserNames = @('chrome','msedge','firefox','brave','opera','vivaldi')

$root = [System.Windows.Automation.AutomationElement]::RootElement
$topWindows = $root.FindAll([System.Windows.Automation.TreeScope]::Children, [System.Windows.Automation.Condition]::TrueCondition)

$dialogWindow = $null
foreach ($win in $topWindows) {
    $procId = $win.Current.ProcessId
    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
    if ($proc -and ($browserNames -contains $proc.ProcessName)) {
        $textCond = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Text)
        $texts = $win.FindAll([System.Windows.Automation.TreeScope]::Descendants, $textCond)
        foreach ($t in $texts) {
            $name = $t.Current.Name
            if ($name -and $name.Contains($dialogPhrase)) {
                $dialogWindow = $win
                break
            }
        }
        if ($dialogWindow) { break }
    }
}

if (-not $dialogWindow) {
    Write-Output 'ARENA_DIALOG_NOT_FOUND'
    exit 0
}

# همه دکمه‌ها و آیتم‌های لیست با نام Yes را جمع می‌کنیم؛ آخرین مورد مد نظر است.
$btnCond = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Button)
$itemCond = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::ListItem)
$orCond = New-Object System.Windows.Automation.OrCondition($btnCond, $itemCond)
$candidates = $dialogWindow.FindAll([System.Windows.Automation.TreeScope]::Descendants, $orCond)

$yesList = @()
foreach ($el in $candidates) {
    if ($el.Current.Name -eq 'Yes') { $yesList += $el }
}

if ($yesList.Count -eq 0) {
    Write-Output 'ARENA_DIALOG_FOUND_BUT_NO_YES'
    exit 0
}

$lastYes = $yesList[$yesList.Count - 1]

# اول با الگوی Invoke کلیک می‌کنیم (تمیزترین روش)
$clicked = $false
try {
    $pattern = $null
    if ($lastYes.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern, [ref]$pattern)) {
        $pattern.Invoke()
        $clicked = $true
    }
} catch {
    $clicked = $false
}

# اگر Invoke در دسترس نبود، با انتقال موس به نقطه قابل کلیک و کلیک فیزیکی
if (-not $clicked) {
    Add-Type @'
using System;
using System.Runtime.InteropServices;
public class MouseClicker {
    [DllImport("user32.dll")]
    public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint cButtons, uint dwExtraInfo);
}
'@
    $pt = $lastYes.GetClickablePoint()
    [System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point([int]$pt.X, [int]$pt.Y)
    Start-Sleep -Milliseconds 200
    [MouseClicker]::mouse_event(2, 0, 0, 0, 0)
    [MouseClicker]::mouse_event(4, 0, 0, 0, 0)
}

Write-Output 'ARENA_DIALOG_CLICKED'
exit 0
""".replace("WAS_THIS_TASK_SUCCESSFUL", DIALOG_PHRASE)


def handle_dialog_if_present():
    # چند بار بررسی می‌کند چون ممکن است پنجره با کمی تأخیر ظاهر شود.
    for attempt in range(1, DIALOG_CHECK_ATTEMPTS + 1):
        print(
            f"بررسی وجود پنجره «{DIALOG_PHRASE}» "
            f"(تلاش {attempt} از {DIALOG_CHECK_ATTEMPTS})..."
        )
        try:
            output = run_hidden_powershell(DIALOG_PS_SCRIPT, timeout=60)
        except Exception as exc:
            # خطای بررسی نباید کل کار را متوقف کند؛ یک بار دیگر تلاش می‌شود
            print(f"خطا در بررسی پنجره تأیید: {exc}")
            output = ""

        if "ARENA_DIALOG_CLICKED" in output:
            print("پنجره تأیید پیدا شد؛ روی آخرین گزینه Yes کلیک شد")
            print(f"صبر {DIALOG_CLICK_WAIT} ثانیه‌ای پس از کلیک...")
            time.sleep(DIALOG_CLICK_WAIT)
            return True

        if "ARENA_DIALOG_FOUND_BUT_NO_YES" in output:
            print("پنجره تأیید پیدا شد ولی گزینه Yes قابل کلیک شناسایی نشد؛ ادامه می‌دهیم")
            return True

        if attempt < DIALOG_CHECK_ATTEMPTS:
            time.sleep(DIALOG_CHECK_GAP)

    print("پنجره تأیید دیده نشد؛ مستقیم سراغ تایپ متن می‌رویم")
    return False


# اسکریپت UI Automation برای تایپ و ارسال:
#   ۱) پنجره مرورگر فعال پیدا می‌شود
#   ۲) آخرین کادر ویرایشی (Edit) همان کادر چت پایین صفحه است؛ فوکوس و رویش کلیک می‌شود
#      (اگر کادری پیدا نشد، کلیک در مرکز-پایین پنجره به‌عنوان جایگزین)
#   ۳) متن از کلیپ‌بورد با Ctrl+V داخل کادر می‌نشیند
#   ۴) ارسال: اول دکمه Send، و اگر نبود Enter سخت‌افزاری (keybd_event)
TYPE_PS_SCRIPT = r"""
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class WinApi {
    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")]
    public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint cButtons, uint dwExtraInfo);
    [DllImport("user32.dll")]
    public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);
}
'@

$browserNames = @('chrome','msedge','firefox','brave','opera','vivaldi')
$root = [System.Windows.Automation.AutomationElement]::RootElement
$topWindows = $root.FindAll([System.Windows.Automation.TreeScope]::Children, [System.Windows.Automation.Condition]::TrueCondition)

$foregroundHandle = [WinApi]::GetForegroundWindow()
$browserWin = $null
$lastBrowser = $null
foreach ($win in $topWindows) {
    $proc = Get-Process -Id $win.Current.ProcessId -ErrorAction SilentlyContinue
    if ($proc -and ($browserNames -contains $proc.ProcessName)) {
        $lastBrowser = $win
        if ($win.Current.NativeWindowHandle -eq $foregroundHandle) { $browserWin = $win }
    }
}
if (-not $browserWin) { $browserWin = $lastBrowser }
if (-not $browserWin) { Write-Output 'ARENA_NO_BROWSER'; exit 0 }

# پیدا کردن کادر چت: آخرین کادر ویرایشی فعال در کل پنجره مرورگر
$editCond = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Edit)
$edits = $browserWin.FindAll([System.Windows.Automation.TreeScope]::Descendants, $editCond)
$composer = $null
for ($i = $edits.Count - 1; $i -ge 0; $i--) {
    if ($edits[$i].Current.IsEnabled) { $composer = $edits[$i]; break }
}

function Left-Click($x, $y) {
    [System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point([int]$x, [int]$y)
    Start-Sleep -Milliseconds 200
    [WinApi]::mouse_event(2, 0, 0, 0, 0)
    [WinApi]::mouse_event(4, 0, 0, 0, 0)
}

if ($composer) {
    try { $composer.SetFocus() } catch {}
    Start-Sleep -Milliseconds 400
    try {
        $pt = $composer.GetClickablePoint()
        Left-Click $pt.X $pt.Y
    } catch {}
    Write-Output 'ARENA_FOCUS_EDIT_OK'
} else {
    # جایگزین: کلیک نزدیک کادر چت در پایین وسط پنجره مرورگر
    $r = $browserWin.Current.BoundingRectangle
    Left-Click ($r.X + $r.Width / 2) ($r.Bottom - 80)
    Write-Output 'ARENA_FOCUS_CLICK_FALLBACK'
}

Start-Sleep -Milliseconds 500
Set-Clipboard -Value $env:ARENA_PROMPT
Start-Sleep -Milliseconds 300
[System.Windows.Forms.SendKeys]::SendWait('^v')
Start-Sleep -Milliseconds 900

# ارسال پیام: اول دکمه Send اگر در دسترس بود
$btnCond = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Button)
$buttons = $browserWin.FindAll([System.Windows.Automation.TreeScope]::Descendants, $btnCond)
$sendBtn = $null
foreach ($b in $buttons) {
    $n = $b.Current.Name
    if ($n -and ($n -match 'send|ارسال')) { $sendBtn = $b }
}

if ($sendBtn) {
    try {
        $pattern = $null
        if ($sendBtn.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern, [ref]$pattern)) {
            $pattern.Invoke()
            Write-Output 'ARENA_SEND_BUTTON'
        } else {
            $pt = $sendBtn.GetClickablePoint()
            Left-Click $pt.X $pt.Y
            Write-Output 'ARENA_SEND_BUTTON_CLICK'
        }
    } catch {
        [WinApi]::keybd_event(0x0D, 0x1C, 0x0008, [UIntPtr]::Zero)
        [WinApi]::keybd_event(0x0D, 0x1C, 0x0008 -bor 0x0002, [UIntPtr]::Zero)
        Write-Output 'ARENA_SEND_ENTER'
    }
} else {
    # Enter سخت‌افزاری با کد اسکن — مرورگرها و چت‌های وب این را مثل کیبورد واقعی می‌گیرند
    [WinApi]::keybd_event(0x0D, 0x1C, 0x0008, [UIntPtr]::Zero)
    [WinApi]::keybd_event(0x0D, 0x1C, 0x0008 -bor 0x0002, [UIntPtr]::Zero)
    Write-Output 'ARENA_SEND_ENTER'
}
exit 0
"""


def type_and_submit():
    # متن از طریق متغیر محیطی به پاورشل داده می‌شود تا هیچ مشکل کوتیشن/یونیکدی پیش نیاید.
    output = run_hidden_powershell(
        TYPE_PS_SCRIPT, extra_env={"ARENA_PROMPT": PROMPT_TEXT}
    )
    if "ARENA_NO_BROWSER" in output:
        print("هشدار: پنجره مرورگر برای تایپ پیدا نشد")
    elif "ARENA_FOCUS_CLICK_FALLBACK" in output:
        print("کادر چت مستقیم شناسایی نشد؛ با کلیک روی ناحیه پایین صفحه فوکوس شد")
    else:
        print("کادر چت پیدا و فوکوس شد")

    if "ARENA_SEND_BUTTON" in output:
        print("متن در کادر چت قرار گرفت و با دکمه Send ارسال شد")
    else:
        print("متن در کادر چت قرار گرفت و با Enter ارسال شد")


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

    # ۳) در صورت وجود پنجره تأیید، آخرین Yes کلیک می‌شود
    handle_dialog_if_present()

    # ۴) تایپ متن فارسی و زدن Enter
    try:
        type_and_submit()
    except Exception as exc:
        # حتی اگر تایپ شکست خورد، ادامه می‌دهیم تا اسکرین‌شات وضعیت صفحه را ثبت کند
        print(f"خطا در تایپ/ارسال متن: {exc}")

    # ۵) صبر کوتاه بعد از Enter تا نتیجه ارسال در صفحه دیده شود
    print(f"صبر {AFTER_ENTER_WAIT} ثانیه‌ای پیش از اسکرین‌شات...")
    time.sleep(AFTER_ENTER_WAIT)

    # ۶) اطمینان از وجود پوشه و گرفتن اسکرین‌شات
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
