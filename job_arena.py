# rerun: ۲ آبان ۱۴۰۵ — ۱۶:۱۲:۰۵ تهران — 2be154
# job_arena.py
# کار این فایل:
#   ۱) باز کردن لینک صفحه Arena در مرورگر پیش‌فرض
#   ۲) صبر برای بارگذاری کامل صفحه (با فاصله زمانی)
#   ۳) بررسی حالت پنجره مرورگر: اگر تمام‌صفحه (Maximized) نبود، اول Maximize می‌شود
#   ۴) بررسی وجود پنجره "Was this task successful?":
#        - اگر نبود → مستقیم سراغ تایپ می‌رود
#        - اگر بود → آخرین دکمه "Yes" را کلیک می‌کند، کمی صبر می‌کند، بعد تایپ می‌کند
#   ۵) کلیک روی کادر چت (محل متن کمرنگ "What would you like to do?")، تایپ متن فارسی و ارسال
#   ۶) گرفتن اسکرین‌شات در پایان
# فقط کتابخانه‌های استاندارد پایتون — بدون نیاز به pip install.
# بدون ورودی تعاملی (input) و بدون انتظار برای بسته شدن مرورگر.
#
# نکته فنی ۱: SendKeys ویندوز حروف فارسی (یونیکد) را مستقیم تایپ نمی‌کند؛
# متن ابتدا داخل کلیپ‌بورد گذاشته می‌شود و بعد با Ctrl+V جای‌گذاری می‌شود.
# نکته فنی ۲: همه تعامل‌ها (تشخیص، کلیک، تایپ) با UI Automation داخلی ویندوز
# (UIAutomationClient) از داخل PowerShell انجام می‌شود، نه با پکیج پایتونی.
# نکته فنی ۳: کادر چت با متن placeholder و موقعیت پایین صفحه پیدا می‌شود تا نه با
# نوار آدرس و نه با سند بزرگ کل صفحه اشتباه گرفته شود.

import json
import os
import traceback
import urllib.request
import subprocess
import time
import webbrowser
from datetime import datetime

URL = "https://arena.ai/agent/01a16a94-648c-7294-8d19-f276beecb74c"

# متنی که باید در کادر چت تایپ و ارسال شود
PROMPT_TEXT = "ازت میخوام یک نامه عاشقانه کوتاه بنویسی و در این پوشه: \nC:\\Users\\alibatel\\My Drive\\Windows-Agent-DB\\TESTS\nذخیره کنی."

# عبارتی که قبل از تایپ باید در صفحه بررسی شود
DIALOG_PHRASE = "Was this task successful?"

# متن کمرنگ داخل خود کادر چت (placeholder)
COMPOSER_PLACEHOLDER = "What would you like to do?"

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

# صبر بعد از Maximize کردن مرورگر تا چیدمان صفحه تثبیت شود
MAXIMIZE_WAIT = 2

# صبر بعد از زدن Enter، پیش از گرفتن اسکرین‌شات
AFTER_ENTER_WAIT = 5


# management-arena-bridge: 3
# گزارش نتیجه از راه صف محلی رباتِ خود Windows Agent ارسال می‌شود؛
# هیچ توکن تلگرامی داخل این فایل یا گیت‌هاب قرار نمی‌گیرد.
TELEGRAM_REPORT_MODE = "final"
PROMPT_REQUEST_ID = "20261024185650-71e3ce"
FAILURE_FEEDBACK_ATTEMPTS = 3
BOT_API_CONFIG = os.path.join(
    os.environ.get("LOCALAPPDATA", ""), "Windows-Agent", "bot_api.json"
)


def send_telegram_status(kind, detail):
    """گزارش را به مقصد پیش‌فرض ربات می‌فرستد؛ شکست تلگرام اجرای کار را خراب نمی‌کند."""
    if TELEGRAM_REPORT_MODE == "off":
        return False
    try:
        with open(BOT_API_CONFIG, encoding="utf-8") as fh:
            cfg = json.load(fh)
        text = (
            f"[Arena / {kind}]\n"
            f"درخواست: {PROMPT_REQUEST_ID}\n"
            f"پرامپت: {PROMPT_TEXT[:700]}\n"
            f"جزئیات: {str(detail)[:1800]}"
        )
        body = json.dumps({"text": text, "delay": 0, "chat_id": None}).encode("utf-8")
        request = urllib.request.Request(
            cfg["send"],
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-Agent-Token": cfg["token"],
            },
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            response.read()
        print(f"گزارش تلگرام در صف قرار گرفت: {kind}")
        return True
    except Exception as exc:
        print(f"هشدار: ثبت گزارش تلگرام ممکن نشد: {exc}")
        return False


def save_failure_artifacts(detail):
    """پیش از بازخورد، لاگ و اسکرین‌شات شکست را در Google Drive می‌گذارد."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_id = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in PROMPT_REQUEST_ID)
    base_dir = os.path.dirname(SCREENSHOT_DIR)
    errors_dir = os.path.join(base_dir, "logs", "errors")
    report_path = os.path.join(errors_dir, f"arena_failure_{safe_id}_{stamp}.txt")
    screenshot_path = os.path.join(SCREENSHOT_DIR, f"arena_failure_{safe_id}_{stamp}.png")
    saved = []
    try:
        os.makedirs(errors_dir, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as fh:
            fh.write(
                "زمان: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " تهران\n"
                "موضوع: شکست job_arena.py و نیاز به بررسی ایجنت همکار\n"
                "نسخه برنامه: Arena Bridge 3\n"
                "شناسه درخواست: " + PROMPT_REQUEST_ID + "\n"
                "پرامپت: " + PROMPT_TEXT + "\n\n"
                "جزئیات خطا:\n" + str(detail)
            )
        saved.append(report_path)
    except Exception as exc:
        print(f"هشدار: ذخیره گزارش شکست ممکن نشد: {exc}")
    try:
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
        take_screenshot(screenshot_path)
        saved.append(screenshot_path)
    except Exception as exc:
        print(f"هشدار: گرفتن اسکرین‌شات شکست ممکن نشد: {exc}")
    return saved


def handle_failure_dialog_if_present():
    """اگر پرسش نتیجه باز است، برای اجرای ناموفق گزینه No را انتخاب می‌کند."""
    try:
        failure_script = DIALOG_PS_SCRIPT.replace(
            "$el.Current.Name -eq 'Yes'", "$el.Current.Name -eq 'No'"
        )
        output = run_hidden_powershell(failure_script, timeout=60)
        if "ARENA_DIALOG_CLICKED" in output:
            print("پنجره نتیجه پیدا شد؛ گزینه No برای اجرای ناموفق کلیک شد")
            time.sleep(DIALOG_CLICK_WAIT)
            return True
    except Exception as exc:
        print(f"هشدار: انتخاب No در پنجره نتیجه ممکن نشد: {exc}")
    return False


def send_failure_feedback(detail, artifact_paths):
    """حداکثر سه بار تلاش می‌کند شکست را به گفت‌وگوی ایجنت همکار برگرداند."""
    global PROMPT_TEXT
    original_prompt = PROMPT_TEXT
    paths_text = "، ".join(artifact_paths) if artifact_paths else "پوشه‌های logs و ScreenShots"
    feedback = (
        "اجرای درخواست ناموفق بود. لطفاً گزارش‌ها و در صورت نیاز اسکرین‌شات‌ها را "
        "در Google Drive بررسی کن، علت را پیدا کن و کد را اصلاح یا دوباره بازنویسی و commit کن. "
        f"شناسه درخواست: {PROMPT_REQUEST_ID}. مسیرهای مرتبط: {paths_text}"
    )
    last_error = None
    try:
        for attempt in range(1, FAILURE_FEEDBACK_ATTEMPTS + 1):
            try:
                print(f"تلاش {attempt} از {FAILURE_FEEDBACK_ATTEMPTS} برای ارسال بازخورد شکست...")
                PROMPT_TEXT = feedback
                open_site()
                time.sleep(PAGE_LOAD_WAIT)
                maximize_browser()
                handle_failure_dialog_if_present()
                type_and_submit()
                print("بازخورد اجرای ناموفق به ایجنت همکار ارسال شد")
                return True
            except Exception as exc:
                last_error = exc
                print(f"ارسال بازخورد در تلاش {attempt} ناموفق بود: {exc}")
                if attempt < FAILURE_FEEDBACK_ATTEMPTS:
                    time.sleep(4)
    finally:
        PROMPT_TEXT = original_prompt
    print(f"بازخورد شکست پس از سه تلاش ارسال نشد: {last_error}")
    return False
def open_site():
    print("در حال باز کردن لینک Arena در مرورگر پیش‌فرض...")

    opened = False
    try:
        browser = webbrowser.get()
        opened = browser.open(URL, new=2)
    except webbrowser.Error:
        opened = False

    if not opened:
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


# اسکریپت UI Automation برای اطمینان از تمام‌صفحه (Maximize) بودن مرورگر
MAXIMIZE_PS_SCRIPT = r"""
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class WinMax {
    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
'@

$browserNames = @('chrome','msedge','firefox','brave','opera','vivaldi')
$root = [System.Windows.Automation.AutomationElement]::RootElement
$topWindows = $root.FindAll([System.Windows.Automation.TreeScope]::Children, [System.Windows.Automation.Condition]::TrueCondition)

$foregroundHandle = [WinMax]::GetForegroundWindow()
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

$handle = $browserWin.Current.NativeWindowHandle
try { [WinMax]::SetForegroundWindow($handle) | Out-Null } catch {}

$winPattern = $null
$hasPattern = $browserWin.TryGetCurrentPattern([System.Windows.Automation.WindowPattern]::Pattern, [ref]$winPattern)
if ($hasPattern -and $winPattern) {
    if ($winPattern.Current.WindowVisualState -eq [System.Windows.Automation.WindowVisualState]::Maximized) {
        Write-Output 'ARENA_ALREADY_MAXIMIZED'
        exit 0
    }
    try {
        $winPattern.SetWindowVisualState([System.Windows.Automation.WindowVisualState]::Maximized)
        Write-Output 'ARENA_WINDOW_MAXIMIZED'
        exit 0
    } catch {}
}

try {
    [WinMax]::ShowWindow($handle, 3) | Out-Null
    Write-Output 'ARENA_WINDOW_MAXIMIZED_FALLBACK'
} catch {
    Write-Output 'ARENA_MAXIMIZE_FAILED'
}
exit 0
"""


def maximize_browser():
    print("بررسی حالت تمام‌صفحه بودن پنجره مرورگر...")
    try:
        output = run_hidden_powershell(MAXIMIZE_PS_SCRIPT)
    except Exception as exc:
        print(f"هشدار: بررسی/Maximize مرورگر با خطا مواجه شد: {exc}")
        return

    if "ARENA_ALREADY_MAXIMIZED" in output:
        print("پنجره مرورگر از قبل تمام‌صفحه (Maximized) است")
    elif "ARENA_WINDOW_MAXIMIZED" in output or "ARENA_WINDOW_MAXIMIZED_FALLBACK" in output:
        print("پنجره مرورگر تمام‌صفحه (Maximize) شد")
        print(f"صبر {MAXIMIZE_WAIT} ثانیه‌ای برای تثبیت چیدمان صفحه...")
        time.sleep(MAXIMIZE_WAIT)
    elif "ARENA_NO_BROWSER" in output:
        print("هشدار: پنجره مرورگری برای Maximize پیدا نشد")
    else:
        print("هشدار: Maximize مرورگر قطعی تأیید نشد؛ ادامه می‌دهیم")


# اسکریپت UI Automation تشخیص پنجره "Was this task successful?" و کلیک آخرین Yes
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
    for attempt in range(1, DIALOG_CHECK_ATTEMPTS + 1):
        print(
            f"بررسی وجود پنجره «{DIALOG_PHRASE}» "
            f"(تلاش {attempt} از {DIALOG_CHECK_ATTEMPTS})..."
        )
        try:
            output = run_hidden_powershell(DIALOG_PS_SCRIPT, timeout=60)
        except Exception as exc:
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


# اسکریپت تایپ و ارسال:
#   ۱) مرورگر Foreground و در صورت انحراف از arena.ai لینک دوباره باز می‌شود (نگهبان URL)
#   ۲) کادر چت با اولویت پیدا می‌شود:
#        الف) عنصر متنی placeholder «What would you like to do?»
#        ب) Document باریکِ پایین صفحه (ناحیه کادر چت، نه سند بزرگ کل صفحه)
#        ج) پایین‌ترین Edit داخل صفحه وب (نوار آدرس طرد می‌شود)
#   ۳) روی نقطه دقیق کادر کلیک فیزیکی می‌شود تا فوکوس واقعی بگیرد
#   ۴) متن با Paste سخت‌افزاری وارد و با خواندن متن عنصر فوکوس‌شده تأیید می‌شود (۳ تلاش)
#   ۵) ارسال با Enter سخت‌افزاری، دکمه Send (نامی/موقعیتی)، سپس SendKeys
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
    public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")]
    public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint cButtons, uint dwExtraInfo);
    [DllImport("user32.dll")]
    public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);
}
'@

function Left-Click($x, $y) {
    [System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point([int]$x, [int]$y)
    Start-Sleep -Milliseconds 200
    [WinApi]::mouse_event(2, 0, 0, 0, 0)
    Start-Sleep -Milliseconds 60
    [WinApi]::mouse_event(4, 0, 0, 0, 0)
}

function Hardware-Paste {
    [WinApi]::keybd_event(0x11, 0x1D, 0, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 80
    [WinApi]::keybd_event(0x56, 0x2F, 0, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 80
    [WinApi]::keybd_event(0x56, 0x2F, 2, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 80
    [WinApi]::keybd_event(0x11, 0x1D, 2, [UIntPtr]::Zero)
}

function Hardware-Enter {
    [WinApi]::keybd_event(0x0D, 0x1C, 0, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 80
    [WinApi]::keybd_event(0x0D, 0x1C, 2, [UIntPtr]::Zero)
}

function Get-ElText($el) {
    if (-not $el) { return $null }
    try {
        $vp = $null
        if ($el.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern, [ref]$vp)) {
            return [string]$vp.Current.Value
        }
    } catch {}
    try {
        $tp = $null
        if ($el.TryGetCurrentPattern([System.Windows.Automation.TextPattern]::Pattern, [ref]$tp)) {
            return [string]$tp.DocumentRange.GetText(500)
        }
    } catch {}
    return $null
}

function Get-Visible($elements) {
    $list = @()
    foreach ($el in $elements) {
        try {
            $r = $el.Current.BoundingRectangle
            if ($el.Current.IsEnabled -and $r.Width -gt 1 -and $r.Height -gt 1) { $list += $el }
        } catch {}
    }
    return $list
}

function Test-Omnibox($el, $winTop) {
    try {
        $r = $el.Current.BoundingRectangle
        $n = [string]$el.Current.Name
        if ($r.Top -le ($winTop + 120)) { return $true }
        if ($n -and ($n -match 'address|search bar|آدرس|نوار')) { return $true }
    } catch {}
    return $false
}

# مرکز قابل کلیک یک عنصر با محافظت در برابر خطای GetClickablePoint
function Get-ClickPoint($el) {
    try {
        $pt = $el.GetClickablePoint()
        if ($pt.X -gt 0 -and $pt.Y -gt 0) { return $pt }
    } catch {}
    $r = $el.Current.BoundingRectangle
    return New-Object System.Windows.Point(($r.X + $r.Width / 2), ($r.Y + $r.Height / 2))
}

$browserNames = @('chrome','msedge','firefox','brave','opera','vivaldi')
$composer = $null
$clickPoint = $null
$page = $null
$browserWin = $null
$textConfirmed = $false

for ($round = 1; $round -le 2 -and -not $textConfirmed; $round++) {
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

    try { [WinApi]::SetForegroundWindow($browserWin.Current.NativeWindowHandle) | Out-Null } catch {}
    Start-Sleep -Milliseconds 500
    Write-Output 'ARENA_BROWSER_FG'

    $winRect = $browserWin.Current.BoundingRectangle
    $editCond = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Edit)
    $docCond = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Document)
    $textCond = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Text)
    $winEdits = Get-Visible ($browserWin.FindAll([System.Windows.Automation.TreeScope]::Descendants, $editCond))

    # نگهبان URL: نوار آدرس نباید روی دامنه‌ای غیر از arena.ai باشد
    $omnibox = $null
    foreach ($e in $winEdits) {
        if (Test-Omnibox $e $winRect.Top) { $omnibox = $e; break }
    }
    if ($omnibox) {
        $urlText = Get-ElText $omnibox
        if ($urlText -and ($urlText -notmatch 'arena\.ai')) {
            Write-Output 'ARENA_URL_GUARD_REOPEN'
            Start-Process $env:ARENA_URL | Out-Null
            Start-Sleep -Seconds 12
            continue
        }
    }

    # بزرگ‌ترین Document = محدوده صفحه وب؛ فقط برای محدود کردن جستجو استفاده می‌شود
    $docs = Get-Visible ($browserWin.FindAll([System.Windows.Automation.TreeScope]::Descendants, $docCond))
    $page = $null
    $maxArea = 0
    foreach ($d in $docs) {
        $r = $d.Current.BoundingRectangle
        $area = $r.Width * $r.Height
        if ($area -gt $maxArea) { $maxArea = $area; $page = $d }
    }
    if (-not $page) { $page = $browserWin }
    $pageRect = $page.Current.BoundingRectangle

    # ----- اولویت الف: متن placeholder کادر چت -----
    $texts = Get-Visible ($page.FindAll([System.Windows.Automation.TreeScope]::Descendants, $textCond))
    $placeholder = $null
    foreach ($t in $texts) {
        $n = [string]$t.Current.Name
        if ($n -and ($n -match 'What would you like')) { $placeholder = $t; break }
    }
    if ($placeholder) {
        $pr = $placeholder.Current.BoundingRectangle
        # روی خود سطر placeholder کلیک می‌کنیم (کمی داخل باکس، نه روی لبه)
        $cx = $pr.X + [Math]::Min(120, $pr.Width / 2)
        $cy = $pr.Y + $pr.Height / 2
        $clickPoint = New-Object System.Windows.Point($cx, $cy)
        $composer = $placeholder
        Write-Output 'ARENA_COMPOSER_PLACEHOLDER'
    }

    # ----- اولویت ب: Document باریک در پایین صفحه (خود کادر contenteditable) -----
    if (-not $clickPoint) {
        $bandTop = $pageRect.Bottom - ($pageRect.Height * 0.35)
        $minWidth = $pageRect.Width * 0.4
        $best = $null
        foreach ($d in $docs) {
            $r = $d.Current.BoundingRectangle
            if ($r.Top -ge $bandTop -and $r.Width -ge $minWidth -and $r.Height -lt ($pageRect.Height * 0.5)) {
                if (-not $best -or $r.Top -gt $best.Current.BoundingRectangle.Top) { $best = $d }
            }
        }
        if ($best) {
            $composer = $best
            $clickPoint = Get-ClickPoint $best
            Write-Output 'ARENA_COMPOSER_BOTTOM_DOC'
        }
    }

    # ----- اولویت ج: پایین‌ترین Edit داخل صفحه وب (به‌جز نوار آدرس) -----
    if (-not $clickPoint) {
        $pageEdits = Get-Visible ($page.FindAll([System.Windows.Automation.TreeScope]::Descendants, $editCond))
        $safeEdits = @()
        foreach ($e in $pageEdits) {
            if (Test-Omnibox $e $winRect.Top) { continue }
            $safeEdits += $e
        }
        if ($safeEdits.Count -gt 0) {
            $composer = $safeEdits[0]
            foreach ($e in $safeEdits) {
                if ($e.Current.BoundingRectangle.Top -gt $composer.Current.BoundingRectangle.Top) { $composer = $e }
            }
            $clickPoint = Get-ClickPoint $composer
            Write-Output 'ARENA_COMPOSER_PAGE_EDIT'
        }
    }

    # ----- اولویت د: کلیک هندسی روی ناحیه کادر چت در پایین-وسط پنجره -----
    if (-not $clickPoint) {
        $cx = $winRect.X + $winRect.Width / 2
        $cy = $winRect.Bottom - 90
        $clickPoint = New-Object System.Windows.Point($cx, $cy)
        Write-Output 'ARENA_COMPOSER_GEOMETRY_FALLBACK'
    }

    # حلقه ورود متن: هر تلاش ابتدا کادر را پاک می‌کند و یک روش Paste متفاوت دارد.
    # چون contenteditable کروم همیشه متن را از UI Automation برنمی‌گرداند، تأیید نهایی
    # با Select All + Copy و مقایسه‌ی دقیق محتوای کپی‌شده انجام می‌شود.
    for ($try = 1; $try -le 3 -and -not $textConfirmed; $try++) {
        if ($composer) { try { $composer.SetFocus() } catch {} }
        Start-Sleep -Milliseconds 300
        Left-Click $clickPoint.X $clickPoint.Y
        Start-Sleep -Milliseconds 500

        # متن باقی‌مانده از تلاش قبلی نباید باعث Paste تکراری شود.
        try {
            [System.Windows.Forms.SendKeys]::SendWait('^a')
            Start-Sleep -Milliseconds 100
            [System.Windows.Forms.SendKeys]::SendWait('{BACKSPACE}')
        } catch {}

        Set-Clipboard -Value $env:ARENA_PROMPT
        Start-Sleep -Milliseconds 300
        if ($try -eq 1) {
            Hardware-Paste
            Write-Output 'ARENA_PASTE_HARDWARE'
        } elseif ($try -eq 2) {
            [System.Windows.Forms.SendKeys]::SendWait('^v')
            Write-Output 'ARENA_PASTE_SENDKEYS'
        } else {
            [System.Windows.Forms.SendKeys]::SendWait('+{INSERT}')
            Write-Output 'ARENA_PASTE_SHIFT_INSERT'
        }
        Start-Sleep -Milliseconds 1000

        $focused = [System.Windows.Automation.AutomationElement]::FocusedElement
        $focusedText = Get-ElText $focused
        $composerText = Get-ElText $composer
        $promptNormalized = ([string]$env:ARENA_PROMPT).Replace("`r`n", "`n").TrimEnd([char[]]"`r`n")
        $focusedNormalized = ([string]$focusedText).Replace("`r`n", "`n").TrimEnd([char[]]"`r`n")
        $composerNormalized = ([string]$composerText).Replace("`r`n", "`n").TrimEnd([char[]]"`r`n")
        $okFocused = ($focusedText -and $focusedNormalized.Contains($promptNormalized))
        $okComposer = ($composerText -and $composerNormalized.Contains($promptNormalized))

        # مقدار قبلی Clipboard خود پرامپت است؛ قبل از Copy یک sentinel می‌گذاریم
        # تا موفقیت Copy واقعاً ثابت کند متن داخل کادر قرار گرفته است.
        $okCopied = $false
        try {
            $sentinel = "__ARENA_VERIFY_$([Guid]::NewGuid().ToString('N'))__"
            Set-Clipboard -Value $sentinel
            [System.Windows.Forms.SendKeys]::SendWait('^a')
            Start-Sleep -Milliseconds 150
            [System.Windows.Forms.SendKeys]::SendWait('^c')
            Start-Sleep -Milliseconds 350
            $copiedText = [string](Get-Clipboard -Raw)
            $copiedNormalized = $copiedText.Replace("`r`n", "`n").TrimEnd([char[]]"`r`n")
            $okCopied = ($copiedNormalized -eq $promptNormalized)
            [System.Windows.Forms.SendKeys]::SendWait('{END}')
        } catch {}

        if ($okFocused -or $okComposer -or $okCopied) {
            $textConfirmed = $true
            if ($okCopied) { Write-Output ("ARENA_SELECTION_COPY_VERIFIED_TRY" + $try) }
            Write-Output ("ARENA_PASTE_VERIFIED_TRY" + $try)
        } else {
            Write-Output ("ARENA_PASTE_UNVERIFIED_TRY" + $try)
        }
    }
}

if ($textConfirmed) { Write-Output 'ARENA_TEXT_VERIFIED' } else { Write-Output 'ARENA_TEXT_MISSING' }

# ارسال فقط وقتی «تأیید شده» تلقی می‌شود که متن قبلاً حضورش ثابت شده باشد
$sent = $false

if ($textConfirmed) {
    # ۱) Enter سخت‌افزاری
    Hardware-Enter
    Start-Sleep -Milliseconds 1200
    $focused = [System.Windows.Automation.AutomationElement]::FocusedElement
    $afterText = Get-ElText $focused
    if (-not $afterText -or -not $afterText.Contains($env:ARENA_PROMPT)) {
        $sent = $true
        Write-Output 'ARENA_SUBMIT_ENTER'
    }

    # ۲) دکمه Send: اول با نام، بعد با موقعیت (دکمه سمت راست هم‌تراز کادر چت)
    if (-not $sent) {
        $scope = $page
        $btnCond = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Button)
        $buttons = Get-Visible ($scope.FindAll([System.Windows.Automation.TreeScope]::Descendants, $btnCond))
        $sendBtn = $null
        foreach ($b in $buttons) {
            $n = [string]$b.Current.Name
            if ($n -and ($n -match 'send|ارسال')) { $sendBtn = $b; break }
        }
        if (-not $sendBtn -and $clickPoint) {
            $bandY = $clickPoint.Y
            $rightLimit = $pageRect.Right - 40
            $bestX = -1.0
            foreach ($b in $buttons) {
                $r = $b.Current.BoundingRectangle
                $cy = $r.Y + $r.Height / 2
                if ([Math]::Abs($cy - $bandY) -lt 120 -and $r.X -gt ($pageRect.X + $pageRect.Width * 0.7)) {
                    if ($r.X -gt $bestX) { $bestX = $r.X; $sendBtn = $b }
                }
            }
            if ($sendBtn) { Write-Output 'ARENA_SEND_BUTTON_GEOMETRY' }
        }
        if ($sendBtn) {
            try {
                $pattern = $null
                if ($sendBtn.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern, [ref]$pattern)) {
                    $pattern.Invoke()
                } else {
                    $pt = Get-ClickPoint $sendBtn
                    Left-Click $pt.X $pt.Y
                }
                Start-Sleep -Milliseconds 1200
                $focused = [System.Windows.Automation.AutomationElement]::FocusedElement
                $afterText = Get-ElText $focused
                if (-not $afterText -or -not $afterText.Contains($env:ARENA_PROMPT)) {
                    $sent = $true
                    Write-Output 'ARENA_SUBMIT_BUTTON'
                }
            } catch {}
        }
    }

    # ۳) آخرین راهبرد: SendKeys Enter
    if (-not $sent) {
        try {
            [System.Windows.Forms.SendKeys]::SendWait('~')
            Start-Sleep -Milliseconds 1200
            $focused = [System.Windows.Automation.AutomationElement]::FocusedElement
            $afterText = Get-ElText $focused
            if (-not $afterText -or -not $afterText.Contains($env:ARENA_PROMPT)) {
                $sent = $true
                Write-Output 'ARENA_SUBMIT_SENDKEYS'
            }
        } catch {}
    }
} else {
    # متن تأیید نشده؛ فقط یک Enter محتاطانه برای حالتی که تأیید خودکار شکست خورده ولی متن نشسته
    Hardware-Enter
    Write-Output 'ARENA_SUBMIT_SKIPPED_UNVERIFIED'
}

if ($sent) { Write-Output 'ARENA_SENT_VERIFIED' } else { Write-Output 'ARENA_SEND_UNCERTAIN' }
exit 0
"""


def type_and_submit():
    output = run_hidden_powershell(
        TYPE_PS_SCRIPT,
        extra_env={"ARENA_PROMPT": PROMPT_TEXT, "ARENA_URL": URL},
        timeout=120,
    )
    markers = [line.strip() for line in output.splitlines() if line.strip()]

    if "ARENA_NO_BROWSER" in output:
        print("هشدار: پنجره مرورگر برای تایپ پیدا نشد")
    if "ARENA_URL_GUARD_REOPEN" in output:
        print("هشدار: تب از صفحه Arena خارج شده بود؛ لینک دوباره باز شد")

    if "ARENA_COMPOSER_PLACEHOLDER" in output:
        print("کادر چت از روی متن «What would you like to do?» پیدا و کلیک شد")
    elif "ARENA_COMPOSER_BOTTOM_DOC" in output:
        print("کادر چت از موقعیت پایین صفحه تشخیص داده و کلیک شد")
    elif "ARENA_COMPOSER_PAGE_EDIT" in output:
        print("کادر چت داخل صفحه وب پیدا و کلیک شد (نوار آدرس کنار گذاشته شد)")
    elif "ARENA_COMPOSER_GEOMETRY_FALLBACK" in output:
        print("کادر چت مستقیم شناسایی نشد؛ کلیک هندسی روی ناحیه پایین صفحه انجام شد")

    if "ARENA_TEXT_VERIFIED" in output:
        print("حضور متن در کادر چت با خواندن عنصر فوکوس‌شده تأیید شد")
    else:
        raise RuntimeError("حضور متن در کادر چت تأیید نشد")

    if "ARENA_SENT_VERIFIED" in output:
        print("ارسال پیام تأیید شد (متن بعد از ارسال از کادر پاک شد)")
    else:
        raise RuntimeError("ارسال پیام در Arena قطعی تأیید نشد")

    if markers:
        print("گزارش فنی: " + " | ".join(markers))


def take_screenshot(path):
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


def _run_arena_task():
    # ۱) باز کردن لینک
    open_site()

    # ۲) صبر برای بارگذاری کامل صفحه و کادر چت
    print(f"صبر {PAGE_LOAD_WAIT} ثانیه‌ای برای بارگذاری کامل صفحه...")
    time.sleep(PAGE_LOAD_WAIT)

    # ۳) اطمینان از تمام‌صفحه (Maximize) بودن پنجره مرورگر
    maximize_browser()

    # ۴) در صورت وجود پنجره تأیید، آخرین Yes کلیک می‌شود
    handle_dialog_if_present()

    # ۵) کلیک روی کادر چت، تایپ متن فارسی و ارسال
    try:
        type_and_submit()
    except Exception as exc:
        print(f"خطا در تایپ/ارسال متن: {exc}")
        raise

    # ۶) صبر کوتاه بعد از Enter تا نتیجه ارسال در صفحه دیده شود
    print(f"صبر {AFTER_ENTER_WAIT} ثانیه‌ای پیش از اسکرین‌شات...")
    time.sleep(AFTER_ENTER_WAIT)

    # ۷) اطمینان از وجود پوشه و گرفتن اسکرین‌شات
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
        raise





def main():
    started_at = datetime.now()
    if TELEGRAM_REPORT_MODE == "start_final":
        send_telegram_status("شروع", "اجرای پرامپت در ویندوز آغاز شد.")
    try:
        _run_arena_task()
    except BaseException as exc:
        elapsed = (datetime.now() - started_at).total_seconds()
        trace = traceback.format_exc()
        summary = f"پس از {elapsed:.1f} ثانیه ناموفق شد: {type(exc).__name__}: {exc}"
        print(summary)
        artifacts = save_failure_artifacts(summary + "\n" + trace)
        feedback_sent = send_failure_feedback(summary, artifacts)
        feedback_note = "بازخورد به ایجنت همکار ارسال شد." if feedback_sent else "ارسال بازخورد پس از سه تلاش ناموفق بود."
        send_telegram_status("ناموفق", summary + "\n" + feedback_note + "\n" + trace[-1200:])
        raise
    else:
        elapsed = (datetime.now() - started_at).total_seconds()
        send_telegram_status("موفق", f"پرامپت پس از {elapsed:.1f} ثانیه تایپ و ارسال شد.")


if __name__ == "__main__":
    main()
