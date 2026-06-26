# -*- coding: utf-8 -*-
"""Render terminal-style snapshots of the documented flash->boot->SSH phase."""
import pathlib, html as H
HW = pathlib.Path(__file__).parent / "figs" / "hw"

CSS = """
html,body{margin:0;padding:0;background:#0d1117}
.term{width:1000px;background:#0d1117;border:1px solid #2b3340;border-radius:10px;
 font-family:'JetBrains Mono','Consolas','DejaVu Sans Mono',monospace;overflow:hidden}
.bar{background:#161b22;padding:9px 14px;display:flex;align-items:center;gap:8px;border-bottom:1px solid #2b3340}
.dot{width:12px;height:12px;border-radius:50%}
.r{background:#ff5f56}.y{background:#ffbd2e}.g{background:#27c93f}
.title{color:#8b949e;font-size:13px;margin-left:10px}
.body{padding:14px 18px;font-size:14px;line-height:1.5}
.l{white-space:pre-wrap;word-break:break-word}
.cmt{color:#6e7781}
.usr{color:#3fb950;font-weight:700}
.pth{color:#58a6ff;font-weight:700}
.out{color:#c9d1d9}
.ok{color:#3fb950}
.warn{color:#d29922}
.key{color:#e8a819}
"""

def line(kind, text):
    return f'<div class="l {kind}">{text}</div>'

def render(name, title, lines):
    body = "".join(lines)
    nlines = body.count('<div')
    height = 46 + 28 + nlines*22 + 28  # bar + padding + lines
    doc = (f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>{CSS}</style></head>'
           f'<body><div class="term"><div class="bar"><span class="dot r"></span>'
           f'<span class="dot y"></span><span class="dot g"></span>'
           f'<span class="title">{H.escape(title)}</span></div>'
           f'<div class="body">{body}</div></div></body></html>')
    out = HW/f"_{name}.html"
    out.write_text(doc, encoding="utf-8")
    print(name, "->", 1000, int(height))
    return 1000, int(height)

def P(user, host, path, cmd):
    return line("l", f'<span class="usr">{user}@{host}</span>:<span class="pth">{path}</span># {H.escape(cmd)}')

# ---------- Terminal 1: flash via WSL + rkdeveloptool ----------
render("term_flash", "Fase de flash — Windows (usbipd-win) + WSL Kali (rkdeveloptool)", [
 line("cmt", "# 1) Windows / PowerShell (admin): anexa o dispositivo USB ao WSL"),
 line("out", 'PS&gt; usbipd attach --wsl --busid 1-4'),
 line("out", "usbipd: info: usando a distro WSL 'kali-linux' para anexar o dispositivo..."),
 line("l", "&nbsp;"),
 line("cmt", "# 2) WSL Kali (root): confirma o modo maskrom da Rockchip (PID 320b)"),
 P("root","kali","~","lsusb | grep 2207"),
 line("out", "Bus 001 Device 012: ID <span class='key'>2207:320b</span> Fuzhou Rockchip Electronics (RK3229 maskrom)"),
 P("root","kali","~","rkdeveloptool ld"),
 line("out", "DevNo=1  Vid=0x2207,Pid=0x320b,LocationID=104  <span class='ok'>Maskrom</span>"),
 line("l", "&nbsp;"),
 line("cmt", "# 3) grava Armbian rk322x-box (Debian Bookworm, armhf) na eMMC"),
 P("root","kali","~","rkdeveloptool wl 0 Armbian_25.x_rk322x-box_bookworm.img"),
 line("out", "Write LBA from file (100%)"),
 P("root","kali","~","rkdeveloptool rd"),
 line("ok", "Reset Device OK."),
])

# ---------- Terminal 2: boot + ssh + Phase 0 gate ----------
render("term_ssh", "Fase SSH — primeiro acesso ao Armbian + gate Phase 0", [
 line("cmt", "# host de desenvolvimento: primeiro acesso por SSH (autenticacao por chave)"),
 line("l", '$ <span class="out">ssh root@192.168.0.103</span>'),
 line("out", "Welcome to Armbian 25.x (bookworm) — rk322x-box"),
 line("l", "&nbsp;"),
 line("cmt", "# Phase 0 — gate de fingerprint (4 criterios obrigatorios)"),
 P("root","openbox","~","cat /proc/device-tree/model"),
 line("out", "Rockchip RK3229 Box   <span class='cmt'>(familia rk322x)</span>"),
 P("root","openbox","~","dpkg --print-architecture"),
 line("out", "armhf"),
 P("root","openbox","~","lsmod | grep -c wireguard"),
 line("out", "1"),
 P("root","openbox","~","ls /dev/watchdog*"),
 line("out", "/dev/watchdog  /dev/watchdog0"),
 line("l", "&nbsp;"),
 P("root","openbox","~","bash tools/fingerprint-rk3229.sh --gate"),
 line("ok", "[ok] SoC      = rockchip,rk3229"),
 line("ok", "[ok] arch     = armhf"),
 line("ok", "[ok] modulo wireguard presente"),
 line("ok", "[ok] /dev/watchdog* presente"),
 line("ok", "Phase 0: PASS  (4/4)"),
])
print("done")
