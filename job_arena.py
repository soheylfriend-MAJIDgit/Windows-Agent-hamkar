# job_arena.py
# کار این فایل:
#   ۱) باز کردن لینک صفحه Arena در مرورگر پیش‌فرض
#   ۲) صبر برای بارگذاری کامل صفحه (با فاصله زمانی)
#   ۳) بررسی حالت پنجره مرورگر: اگر تمام‌صفحه (Maximized) نبود، اول Maximize می‌شود
#   ۴) بررسی وجود پنجره "Was this task successful?":
#        - اگر نبود → مستقیم سراغ تایپ می‌رود
#        - اگر بود → آخرین دکمه "Yes" را کلیک می‌کند، کمی صبر می‌کند، بعد تایپ می‌کند
#   ۵) تایپ متن فارسی در کادر چت و زدن Enter
#   ۶) گرفتن اسکرین‌شات در پایان
# فقط کتابخانه‌های استاندارد پایتون — بدون نیاز به pip install.
# بدون ورودی تعاملی (input) و بدون انتظار برای بسته شدن مرورگر.
#
# نکته فنی ۱: SendKeys ویندوز حروف فارسی (یونیکد) را مستقیم تایپ نمی‌کند؛
# متن ابتدا داخل کلیپ‌بورد گذاشته می‌شود و بعد با Ctrl+V جای‌گذاری می‌شود.
# نکته فنی ۲: تشخیص متن و کلیک روی دکمه‌ها با UI Automation داخلی ویندوز
# (UIAutomationClient) از داخل PowerShell انجام می‌شود، نه با پکیج پایتونی.
# نکته فنی ۳: کادر چت فقط داخل درخت صفحه وب جستجو می‌شود تا نوار آدرس مرورگر
# (که خودش یک کنترل Edit است) اشتباهی به‌عنوان کادر چت انتخاب نشود.

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

# صبر بعد از Maximize کردن مرورگر تا چیدمان صفحه تثبیت شود
MAXIMIZE_WAIT = 2

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


# اسکریپت UI Automation برای اطمینان از تمام‌صفحه (Maximize) بودن مرورگر:
#   - پنجره مرورگر فعال (یا آخرین مرورگر) پیدا می‌شود
#   - اگر از قبل Maximized بود کاری نمی‌کند
#   - وگرنه با WindowPattern و در صورت نیاز ShowWindow ویندوزی، Maximize می‌کند
# خروجی: ARENA_ALREADY_MAXIMIZED / ARENA_WINDOW_MAXIMIZED /
# ARENA_WINDOW_MAXIMIZED_FALLBACK / ARENA_NO_BROWSER
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

# WindowVisualState: 0=Normal, 1=Maximized, 2=Minimized
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

# راهبرد جایگزین: ShowWindow ویندوزی با SW_MAXIMIZE = 3
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
        # خطای Maximize نباید بقیه کار را متوقف کند
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


# اسکریپت UI Automation برای تایپ و ارسال — چند راهبرد پشت سر هم با تأیید خودکار:
#   ۱) پنجره مرورگر فعال (Foreground) می‌شود
#   ۲) نگهبان URL: اگر تب از arena.ai خارج شده، دوباره لینک باز می‌شود
#   ۳) کادر چت فقط داخل درخت صفحه وب (بزرگ‌ترین Document) جستجو می‌شود تا نوار آدرس
#      مرورگر (omnibox) که خودش یک کنترل Edit است اشتباهی انتخاب نشود
#   ۴) راهبرد اول: ValuePattern.SetValue (بدون کیبورد/کلیپ‌بورد)
#   ۵) راهبرد دوم: فوکوس + کلیک + Paste سخت‌افزاری (keybd_event Ctrl+V)
#   ۶) بعد از هر تلاش، متن داخل کادر خوانده و تأیید می‌شود
#   ۷) ارسال: Enter سخت‌افزاری → دکمه Send → SendKeys؛ هرکدام با تأیید پاک شدن متن
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
    [WinApi]::mouse_event(4, 0, 0, 0, 0)
}

# Paste سخت‌افزاری: Ctrl پایین → V → V بالا → Ctrl بالا (فلگ‌ها: 0=down, 2=KEYUP)
function Hardware-Paste {
    [WinApi]::keybd_event(0x11, 0x1D, 0, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 80
    [WinApi]::keybd_event(0x56, 0x2F, 0, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 80
    [WinApi]::keybd_event(0x56, 0x2F, 2, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 80
    [WinApi]::keybd_event(0x11, 0x1D, 2, [UIntPtr]::Zero)
}

# Enter سخت‌افزاری واقعی: VK_RETURN با فلگ صفر برای keydown و ۲ برای keyup
function Hardware-Enter {
    [WinApi]::keybd_event(0x0D, 0x1C, 0, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 80
    [WinApi]::keybd_event(0x0D, 0x1C, 2, [UIntPtr]::Zero)
}

# خواندن متن فعلی کادر برای تأیید
function Get-ElText($el) {
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

# تشخیص نوار آدرس/جستجوی خود مرورگر تا با کادر چت اشتباه گرفته نشود
function Test-Omnibox($el, $winTop) {
    try {
        $r = $el.Current.BoundingRectangle
        $n = [string]$el.Current.Name
        if ($r.Top -le ($winTop + 120)) { return $true }
        if ($n -and ($n -match 'address|search bar|آدرس|نوار')) { return $true }
    } catch {}
    return $false
}

$browserNames = @('chrome','msedge','firefox','brave','opera','vivaldi')
$composer = $null
$page = $null
$browserWin = $null
$textInComposer = $false

# دو round: اول عادی؛ اگر نگهبان URL مجبور به باز کردن دوباره صفحه شد، round دوم
for ($round = 1; $round -le 2 -and -not $textInComposer; $round++) {
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

    # مرورگر را پیش‌زمینه کن تا ورودی‌ها قطعاً به آن برسد
    try { [WinApi]::SetForegroundWindow($browserWin.Current.NativeWindowHandle) | Out-Null } catch {}
    Start-Sleep -Milliseconds 500
    Write-Output 'ARENA_BROWSER_FG'

    $winRect = $browserWin.Current.BoundingRectangle
    $editCond = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Edit)
    $docCond = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Document)
    $winEdits = Get-Visible ($browserWin.FindAll([System.Windows.Automation.TreeScope]::Descendants, $editCond))

    # نگهبان URL: مقدار نوار آدرس را بخوان؛ اگر روی arena.ai نیستیم، صفحه را دوباره باز کن
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

    # بزرگ‌ترین Document قابل‌مشاهده = خود صفحه وب (نه نوار ابزار مرورگر)
    $docs = Get-Visible ($browserWin.FindAll([System.Windows.Automation.TreeScope]::Descendants, $docCond))
    $page = $null
    $maxArea = 0
    foreach ($d in $docs) {
        $r = $d.Current.BoundingRectangle
        $area = $r.Width * $r.Height
        if ($area -gt $maxArea) { $maxArea = $area; $page = $d }
    }
    Write-Output ("ARENA_CANDIDATES=" + $winEdits.Count + " window edits, " + $docs.Count + " docs")

    # کادرهای Edit فقط داخل درخت صفحه وب جستجو می‌شوند؛ نوار آدرس اینجا اصلاً وجود ندارد
    $pageEdits = @()
    if ($page) { $pageEdits = Get-Visible ($page.FindAll([System.Windows.Automation.TreeScope]::Descendants, $editCond)) }
    $safeEdits = @()
    foreach ($e in $pageEdits) {
        if (Test-Omnibox $e $winRect.Top) { continue }
        $safeEdits += $e
    }

    if ($safeEdits.Count -gt 0) {
        # پایین‌ترین کادر ویرایشی صفحه = کادر چت
        $composer = $safeEdits[0]
        foreach ($e in $safeEdits) {
            if ($e.Current.BoundingRectangle.Top -gt $composer.Current.BoundingRectangle.Top) { $composer = $e }
        }
        Write-Output 'ARENA_COMPOSER_EDIT_IN_DOC'
    } elseif ($page) {
        # کادر چت contenteditable است و خودش را به‌صورت Document نشان می‌دهد
        $composer = $page
        Write-Output 'ARENA_COMPOSER_DOCUMENT'
    } else {
        # آخرین راهبرد: کلیک روی ناحیه کادر چت در پایین-وسط پنجره و Paste
        Left-Click ($winRect.X + $winRect.Width / 2) ($winRect.Bottom - 80)
        Start-Sleep -Milliseconds 500
        Set-Clipboard -Value $env:ARENA_PROMPT
        Start-Sleep -Milliseconds 300
        Hardware-Paste
        Write-Output 'ARENA_FALLBACK_CLICK_PASTE'
        Start-Sleep -Milliseconds 900
        $textInComposer = $true
        break
    }

    # راهبرد اول: نوشتن مستقیم با ValuePattern (رویدادهای ورودی واقعی مرورگر را فعال می‌کند)
    try {
        $vp = $null
        if ($composer.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern, [ref]$vp)) {
            $vp.SetValue($env:ARENA_PROMPT)
            Start-Sleep -Milliseconds 500
            $now = Get-ElText $composer
            if ($now -and $now.Contains($env:ARENA_PROMPT)) {
                $textInComposer = $true
                Write-Output 'ARENA_VALUE_SET_OK'
            } else {
                Write-Output 'ARENA_VALUE_SET_UNVERIFIED'
            }
        } else {
            Write-Output 'ARENA_VALUE_UNSUPPORTED'
        }
    } catch {
        Write-Output 'ARENA_VALUE_FAILED'
    }

    # راهبرد دوم در صورت شکست: فوکوس + کلیک فیزیکی + Paste سخت‌افزاری (دو بار تلاش)
    if (-not $textInComposer) {
        try { $composer.SetFocus() } catch {}
        Start-Sleep -Milliseconds 400
        try {
            $pt = $composer.GetClickablePoint()
            Left-Click $pt.X $pt.Y
        } catch {}
        Start-Sleep -Milliseconds 400

        for ($try = 1; $try -le 2 -and -not $textInComposer; $try++) {
            Set-Clipboard -Value $env:ARENA_PROMPT
            Start-Sleep -Milliseconds 300
            Hardware-Paste
            Start-Sleep -Milliseconds 900
            $now = Get-ElText $composer
            if ($now -and $now.Contains($env:ARENA_PROMPT)) {
                $textInComposer = $true
                Write-Output ("ARENA_PASTE_OK_TRY" + $try)
            } else {
                Write-Output ("ARENA_PASTE_UNVERIFIED_TRY" + $try)
            }
        }
    }
}

if ($textInComposer) { Write-Output 'ARENA_TEXT_VERIFIED' } else { Write-Output 'ARENA_TEXT_MISSING' }

# ارسال پیام — هر راهبرد با تأیید پاک شدن متن از کادر
function Composer-Cleared {
    if (-not $composer) { return $false }
    $t = Get-ElText $composer
    if (-not $t) { return $true }
    return (-not $t.Contains($env:ARENA_PROMPT))
}

$sent = $false

# ۱) Enter سخت‌افزاری
Hardware-Enter
Start-Sleep -Milliseconds 1200
if (Composer-Cleared) {
    $sent = $true
    Write-Output 'ARENA_SUBMIT_ENTER'
}

# ۲) دکمه Send (داخل همان صفحه وب جستجو می‌شود)
if (-not $sent) {
    $scope = $browserWin
    if ($page) { $scope = $page }
    $btnCond = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Button)
    $buttons = $scope.FindAll([System.Windows.Automation.TreeScope]::Descendants, $btnCond)
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
            } else {
                $pt = $sendBtn.GetClickablePoint()
                Left-Click $pt.X $pt.Y
            }
            Start-Sleep -Milliseconds 1200
            if (Composer-Cleared) { $sent = $true; Write-Output 'ARENA_SUBMIT_BUTTON' }
        } catch {}
    }
}

# ۳) آخرین راهبرد: SendKeys Enter
if (-not $sent) {
    try {
        [System.Windows.Forms.SendKeys]::SendWait('~')
        Start-Sleep -Milliseconds 1200
        if (Composer-Cleared) { $sent = $true; Write-Output 'ARENA_SUBMIT_SENDKEYS' }
    } catch {}
}

if ($sent) { Write-Output 'ARENA_SENT_VERIFIED' } else { Write-Output 'ARENA_SEND_UNCERTAIN' }
exit 0
"""


def type_and_submit():
    # متن از طریق متغیر محیطی به پاورشل داده می‌شود تا هیچ مشکل کوتیشن/یونیکدی پیش نیاید.
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
    if "ARENA_COMPOSER_DOCUMENT" in output:
        print("کادر چت از نوع contenteditable تشخیص داده شد")
    elif "ARENA_COMPOSER_EDIT_IN_DOC" in output:
        print("کادر چت داخل صفحه وب پیدا شد (نوار آدرس کنار گذاشته شد)")
    if "ARENA_VALUE_SET_OK" in output:
        print("متن به‌صورت مستقیم داخل کادر چت نوشته شد (ValuePattern)")
    elif any(m.startswith("ARENA_PASTE_OK") for m in markers):
        print("متن با Paste سخت‌افزاری داخل کادر چت نشست")
    elif "ARENA_FALLBACK_CLICK_PASTE" in output:
        print("کادر چت شناسایی نشد؛ با کلیک روی ناحیه پایین صفحه و Paste تلاش شد")

    if "ARENA_TEXT_VERIFIED" in output:
        print("حضور متن در کادر چت تأیید شد")
    else:
        print("هشدار: حضور متن در کادر چت تأیید نشد")

    if "ARENA_SENT_VERIFIED" in output:
        print("ارسال پیام تأیید شد (متن بعد از ارسال از کادر پاک شد)")
    else:
        print("هشدار: ارسال پیام قطعی تأیید نشد؛ اسکرین‌شات را بررسی کنید")

    # چاپ نشانه‌های فنی برای عیب‌یابی در لاگ
    if markers:
        print("گزارش فنی: " + " | ".join(markers))


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

    # ۳) اطمینان از تمام‌صفحه (Maximize) بودن پنجره مرورگر پیش از هر اقدام دیگری
    maximize_browser()

    # ۴) در صورت وجود پنجره تأیید، آخرین Yes کلیک می‌شود
    handle_dialog_if_present()

    # ۵) تایپ متن فارسی و زدن Enter
    try:
        type_and_submit()
    except Exception as exc:
        # حتی اگر تایپ شکست خورد، ادامه می‌دهیم تا اسکرین‌شات وضعیت صفحه را ثبت کند
        print(f"خطا در تایپ/ارسال متن: {exc}")

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


if __name__ == "__main__":
    main()
