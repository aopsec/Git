# -*- coding: utf-8 -*-
"""Generate annotated hardware 'structure plates' (numbered badges over board photos)."""
import pathlib
from PIL import Image
HW = pathlib.Path(__file__).parent / "figs" / "hw"

# category colors
C = {"mem":"#2E6FA8","pwr":"#E8A819","io":"#1F9E75","dbg":"#8A1F3D","soc":"#0C2233","clk":"#B5651D"}

def badge(num, x, y, cat, d=3.4):
    col = C[cat]
    return (f'<div class="b" style="left:{x}%;top:{y}%;width:{d}%;'
            f'background:{col};">{num}</div>')

def redact(x, y, w, h, label="MAC redigido"):
    return (f'<div class="rd" style="left:{x}%;top:{y}%;width:{w}%;height:{h}%;">{label}</div>')

def plate(img, markers, extra="", redactions=""):
    w, h = Image.open(HW/img).size
    badges = "".join(badge(*m) for m in markers)
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;padding:0}}
.wrap{{position:relative;width:{w}px;height:{h}px;font-family:Arial,sans-serif}}
.wrap img{{width:{w}px;height:{h}px;display:block}}
.b{{position:absolute;transform:translate(-50%,-50%);aspect-ratio:1;border-radius:50%;
   border:2.5px solid #fff;box-shadow:0 0 0 1.5px rgba(0,0,0,.45),0 2px 5px rgba(0,0,0,.5);
   color:#fff;font-weight:700;display:flex;align-items:center;justify-content:center;
   font-size:{int(w*0.022)}px;}}
.rd{{position:absolute;background:#16191f;border:1.5px solid #E8A819;border-radius:4px;
   color:#E8A819;font-size:{int(w*0.018)}px;font-weight:700;display:flex;align-items:center;
   justify-content:center;letter-spacing:1px;}}
</style></head><body><div class="wrap"><img src="{(HW/img).as_uri()}">{badges}{redactions}{extra}</div></body></html>"""
    out = HW/f"_{img.replace('.jpg','')}.html"
    out.write_text(html, encoding="utf-8")
    print(out.name, f"{w}x{h}")
    return w, h

# ---- TOP plate (top.jpg 720x1280) ----
plate("top.jpg", [
    (1, 33, 41, "mem"),   # eMMC Samsung KLM8G1GETF
    (2, 30, 28, "clk"),   # R-série (resistores em série)
    (3, 20, 36, "clk"),   # CLK breakout
    (4, 57, 32, "io"),    # QFN PHY/companion SVS6Z56F
    (5, 88, 41, "io"),    # PPT PM44-11BP
    (6, 83, 27, "pwr"),   # cap eletrolítico CK 100uF
    (7, 67, 52, "pwr"),   # LDO 1117C
    (8, 33, 70, "pwr"),   # bucks 3R3
    (9, 56, 82, "soc"),   # heatsink (SoC RK3229)
    (10, 26, 84, "dbg"),  # header R/T/G
])

# ---- BOTTOM plate (bottom.jpg 1280x720) ----
plate("bottom.jpg", [
    (11, 17, 42, "mem"),  # Hynix DDR3 #1
    (12, 14, 72, "mem"),  # Hynix DDR3 #2
    (13, 38, 58, "pwr"),  # rede de resistores (term. DDR)
    (14, 54, 66, "pwr"),  # LDO 1117
    (15, 66, 77, "mem"),  # footprint BGA vazio (NAND alt)
], redactions=redact(71, 9, 26, 89, "MAC redigido"))

# ---- DRAM plate (dram.jpg 720x1280) ----
plate("dram.jpg", [
    (11, 56, 52, "mem"),  # Hynix H5TQ2G43BFR #1
    (12, 56, 73, "mem"),  # Hynix H5TQ2G43BFR #2
    (16, 36, 50, "clk"),  # cristal/oscilador
    (10, 22, 82, "dbg"),  # header R/T/G
])

# ---- PORTS plate (ports.jpg 1280x720) ----
plate("ports.jpg", [
    (17, 15, 47, "io"),   # USB-A host
    (18, 30, 52, "io"),   # AV 3.5mm #1
    (19, 40, 52, "io"),   # AV 3.5mm #2
    (20, 55, 54, "io"),   # HDMI
    (21, 72, 46, "io"),   # RJ45 Ethernet
    (22, 88, 49, "pwr"),  # DC jack
    (9, 49, 38, "soc"),   # heatsink (SoC)
])
print("done")
