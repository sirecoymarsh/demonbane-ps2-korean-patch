# PCSX2 창에 키를 보낸다. (○=X, ×=Z, Start=Enter, 방향키)
# PostMessage 는 게임 입력에 잘 안 먹으므로 창을 포커스한 뒤 keybd_event 로 실제 입력을 만든다.
param([string]$Keys = "X", [int]$Times = 1, [int]$DelayMs = 350)

Add-Type @"
using System;
using System.Runtime.InteropServices;
public class K {
  [DllImport("user32.dll")] public static extern void keybd_event(byte k, byte s, uint f, IntPtr e);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] public static extern short VkKeyScan(char c);
  [DllImport("user32.dll")] public static extern uint MapVirtualKey(uint code, uint type);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, int dx, int dy, uint d, IntPtr e);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L,T,R,B; }
}
"@

$vk = @{ 'UP' = 0x26; 'DOWN' = 0x28; 'LEFT' = 0x25; 'RIGHT' = 0x27; 'ENTER' = 0x0D; 'BACK' = 0x08; 'ESC' = 0x1B }

$p = Get-Process -Name 'pcsx2*' -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
if (-not $p) { "NO WINDOW"; exit 1 }
[K]::ShowWindow($p.MainWindowHandle, 9) | Out-Null
[K]::SetForegroundWindow($p.MainWindowHandle) | Out-Null
# SetForegroundWindow 만으로는 실제 입력 포커스를 못 받을 때가 있다(Windows 포그라운드 잠금).
# 창 안을 한 번 클릭해서 확실히 포커스를 준다.
$r = New-Object K+RECT
if ([K]::GetWindowRect($p.MainWindowHandle, [ref]$r)) {
  [K]::SetCursorPos([int](($r.L + $r.R) / 2), [int]($r.T + ($r.B - $r.T) * 0.75)) | Out-Null
  Start-Sleep -Milliseconds 120
  [K]::mouse_event(0x0002, 0, 0, 0, [IntPtr]::Zero)   # LEFTDOWN
  Start-Sleep -Milliseconds 60
  [K]::mouse_event(0x0004, 0, 0, 0, [IntPtr]::Zero)   # LEFTUP
}
Start-Sleep -Milliseconds 400

foreach ($n in 1..$Times) {
  foreach ($tok in ($Keys -split ',')) {
    $t = $tok.Trim()
    if ($vk.ContainsKey($t.ToUpper())) { $code = $vk[$t.ToUpper()] }
    else { $code = [K]::VkKeyScan($t[0]) -band 0xFF }
    # PCSX2 는 스캔코드를 본다. bScan=0 으로 보내면 키에 따라 무시된다(Enter 가 안 먹던 원인).
    $sc = [byte]([K]::MapVirtualKey([uint32]$code, 0))
    $ext = if ($vk.ContainsKey($t.ToUpper()) -and $t.ToUpper() -in @('UP','DOWN','LEFT','RIGHT')) { 1 } else { 0 }
    [K]::keybd_event([byte]$code, $sc, [uint32]$ext, [IntPtr]::Zero)
    Start-Sleep -Milliseconds 80
    [K]::keybd_event([byte]$code, $sc, [uint32](2 -bor $ext), [IntPtr]::Zero)
    Start-Sleep -Milliseconds $DelayMs
  }
}
"sent $Keys x$Times"
