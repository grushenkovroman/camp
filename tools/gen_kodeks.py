#!/usr/bin/env python3
"""Generate Кодекс Базы 4:12 — Cyber Charter PDF (A4)"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

# ── Fonts (Menlo — monospace + Cyrillic) ────────────────────────────
pdfmetrics.registerFont(TTFont('M',  '/System/Library/Fonts/Menlo.ttc', subfontIndex=0))
pdfmetrics.registerFont(TTFont('MB', '/System/Library/Fonts/Menlo.ttc', subfontIndex=1))
pdfmetrics.registerFont(TTFont('MI', '/System/Library/Fonts/Menlo.ttc', subfontIndex=2))

W, H = A4  # 595.28 × 841.89 pt

def hx(h):
    h = h.lstrip('#')
    return colors.Color(int(h[0:2],16)/255, int(h[2:4],16)/255, int(h[4:6],16)/255)

BG     = hx('#06071a')
PANEL  = hx('#090b20')
GREEN  = hx('#00ff41')
CYAN   = hx('#00e5ff')
ORANGE = hx('#ff7b2c')
BLUE   = hx('#4477ff')
RED    = hx('#ff3366')
WHITE  = hx('#cdd8f0')
DIM    = hx('#1e2244')
DIM2   = hx('#404870')
YELLOW = hx('#ffe066')

BINARY = ('01101011 01100001 01101001 01110010 01101111 01110011 '
          '00100000 01101111 01101110 01101100 01101001 01101110 01100101')

# ── Layout — all positions calculated to fit A4 ──────────────────────
# Usable vertical space from BINARY_Y down to bottom border:
# BINARY_Y ≈ H-57mm, border = 7mm → ~234mm available.
# Modules: 58+66+58 = 182mm + gaps (6+6+4+footer~22) = 46mm → 228mm ✓

M1_H = 58*mm    # module 01 (3 items)
M2_H = 66*mm    # module 02 (4 items)
M3_H = 58*mm    # module 03 (3 items)

BINARY_Y    = H - 57*mm          # binary strip text baseline

M1_TOP      = BINARY_Y - 9*mm    # 9mm gap below binary
M1_Y        = M1_TOP - M1_H      # bottom of module 01

M2_TOP      = M1_Y  - 6*mm
M2_Y        = M2_TOP - M2_H

M3_TOP      = M2_Y  - 6*mm
M3_Y        = M3_TOP - M3_H

FSEP_Y      = M3_Y  - 5*mm       # footer separator
FTEXT1_Y    = FSEP_Y - 12
FTEXT2_Y    = FSEP_Y - 21
KAIROS_Y    = FSEP_Y - 47        # kairos bar bottom — enough gap above glow

MX = 9*mm
CX = MX + 2*mm
CW = W - 2*MX - 4*mm

# ── Drawing helpers ───────────────────────────────────────────────────

def draw_bg(c):
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setStrokeColor(hx('#0c0f2a'))
    c.setLineWidth(0.35)
    step = 5*mm
    x = 0
    while x <= W: c.line(x, 0, x, H); x += step
    y = 0
    while y <= H: c.line(0, y, W, y); y += step

def scan_lines(c):
    c.setFillColor(colors.Color(0, 0, 0, 0.07))
    y = 0
    while y < H:
        c.rect(0, y, W, 1.5, fill=1, stroke=0); y += 4

def outer_border(c):
    m = 7*mm
    for i in range(6, 0, -1):
        c.setStrokeColor(colors.Color(0.0, 0.9, 1.0, 0.04*i))
        c.setLineWidth(i * 2.5)
        c.rect(m-i, m-i, W-2*m+2*i, H-2*m+2*i, fill=0, stroke=1)
    c.setStrokeColor(CYAN)
    c.setLineWidth(1.1)
    c.rect(m, m, W-2*m, H-2*m, fill=0, stroke=1)

def px_corner(c, cx, cy, fx, fy, color, size=3.0):
    """Pixel-art L-corner."""
    c.setFillColor(color)
    p, g = size, size*0.4
    step = p + g
    for i in range(7):
        dx = i*step * (-1 if fx else 1) + (-p if fx else 0)
        c.rect(cx+dx, cy+(-p if fy else 0), p, p, fill=1, stroke=0)
    for i in range(1, 6):
        dy = i*step * (-1 if fy else 1) + (-p if fy else 0)
        c.rect(cx+(-p if fx else 0), cy+dy, p, p, fill=1, stroke=0)

def all_corners(c, x, y, w, h, color, size=2.5):
    px_corner(c, x,   y+h, False, False, color, size)
    px_corner(c, x+w, y+h, True,  False, color, size)
    px_corner(c, x,   y,   False, True,  color, size)
    px_corner(c, x+w, y,   True,  True,  color, size)

def glow_box(c, x, y, w, h, color, bg=None):
    if bg:
        c.setFillColor(bg)
        c.rect(x, y, w, h, fill=1, stroke=0)
    for i in range(5, 0, -1):
        c.setStrokeColor(colors.Color(color.red, color.green, color.blue, 0.055*i))
        c.setLineWidth(i * 2.2)
        c.rect(x-i, y-i, w+2*i, h+2*i, fill=0, stroke=1)
    c.setStrokeColor(color)
    c.setLineWidth(1.2)
    c.rect(x, y, w, h, fill=0, stroke=1)

def rule_dots(c, x, y, w, color):
    c.setStrokeColor(color)
    c.setLineWidth(0.8)
    c.line(x, y, x+w, y)
    c.setFillColor(color)
    i = 0
    while i < w:
        c.rect(x+i, y-2, 3, 3, fill=1, stroke=0); i += 18

def dashed(c, x, y, w, color):
    c.setStrokeColor(color)
    c.setLineWidth(0.6)
    c.setDash(2, 5)
    c.line(x, y, x+w, y)
    c.setDash()

def _wrap(c, text, font, size, max_w):
    """Split text into lines fitting max_w. Returns list of strings."""
    words = text.split()
    lines, cur = [], ''
    for word in words:
        candidate = (cur + ' ' + word).strip()
        if c.stringWidth(candidate, font, size) <= max_w:
            cur = candidate
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines or [text]

def token_bar(c, x, y, w, loss, gain):
    c.setFillColor(hx('#07091c'))
    c.rect(x, y, w, 17, fill=1, stroke=0)
    c.setStrokeColor(DIM)
    c.setLineWidth(0.5)
    c.line(x, y+17, x+w, y+17)
    c.setFont('MB', 8.5)
    c.setFillColor(RED)
    c.drawString(x+10, y+5.5, f'[-]  НАРУШЕНИЕ: {loss}')
    c.setFillColor(GREEN)
    c.drawRightString(x+w-10, y+5.5, f'БЕЗУПРЕЧНОСТЬ: {gain}  [+]')

def draw_module(c, mx, my, mh, mw, color, header_label, directive, items, loss, gain):
    """Draw a module box with word-wrap and vertical centering."""
    glow_box(c, mx, my, mw, mh, color, PANEL)
    token_bar(c, mx, my, mw, loss, gain)

    # Header bar at top
    hbar_y = my + mh - 22
    c.setFillColor(colors.Color(color.red, color.green, color.blue, 0.20))
    c.rect(mx, hbar_y, mw, 22, fill=1, stroke=0)
    c.setFillColor(color)
    c.rect(mx, hbar_y, 5, 22, fill=1, stroke=0)
    c.setFont('MB', 10)
    c.drawString(mx+13, hbar_y+7, header_label)

    # Pre-wrap every item
    ISIZE  = 9.5          # item font size
    ILH    = ISIZE + 4    # inter-line height within one item (13.5 pt)
    IGAP   = 6            # gap between separate items
    NUM_W  = 27           # horizontal offset for text after "01."
    avail_text_w = mw - 10 - NUM_W

    wrapped = []          # list of (num, lines, block_h)
    for num, text in items:
        lines   = _wrap(c, text, 'M', ISIZE, avail_text_w)
        block_h = (len(lines) - 1) * ILH + ISIZE
        wrapped.append((num, lines, block_h))

    # Total height: all item blocks + gaps between them
    items_stack_h = sum(bh for _, _, bh in wrapped) + (len(wrapped) - 1) * IGAP
    # Separator block above items: gap(8) + sep(1) + gap(7) + directive(8.5)
    sep_block_h   = 8 + 1 + 7 + 8.5
    content_h     = items_stack_h + sep_block_h

    available = mh - 22 - 17
    v_offset  = max(8, (available - content_h) // 2)

    # Draw items bottom-up
    cur_y = my + 17 + v_offset   # baseline of bottom line of lowest item
    for num, lines, block_h in reversed(wrapped):
        n = len(lines)
        # lines[0] is top line → drawn at cur_y + (n-1)*ILH
        # lines[-1] is bottom line → drawn at cur_y
        for i, line in enumerate(lines):
            ly = cur_y + (n - 1 - i) * ILH
            c.setFillColor(WHITE)
            c.setFont('M', ISIZE)
            c.drawString(mx + 10 + NUM_W, ly, line)
        # Number aligns with top line
        c.setFillColor(BLUE)
        c.setFont('MB', ISIZE)
        c.drawString(mx + 10, cur_y + (n - 1) * ILH, f'{num:02}.')
        cur_y += block_h + IGAP

    # cur_y is now just above top item (+ extra IGAP); top of stack:
    top_of_stack = cur_y - IGAP   # remove the last unused gap
    sep_y = top_of_stack + 8
    dashed(c, mx+5, sep_y, mw-10, DIM)

    dir_y = sep_y + 7
    c.setFillColor(colors.Color(color.red, color.green, color.blue, 0.5))
    c.setFont('MI', 8.5)
    c.drawString(mx+10, dir_y, f'ДИРЕКТИВА: {directive}')

    all_corners(c, mx, my, mw, mh, color)


def generate(output_path):
    c = canvas.Canvas(output_path, pagesize=A4)

    draw_bg(c)
    scan_lines(c)
    outer_border(c)

    # Page corner decorations
    bm = 7*mm
    px_corner(c, bm,   H-bm, False, False, CYAN)
    px_corner(c, W-bm, H-bm, True,  False, CYAN)
    px_corner(c, bm,   bm,   False, True,  CYAN)
    px_corner(c, W-bm, bm,   True,  True,  CYAN)

    # ── STATUS BAR ───────────────────────────────────────────────────
    c.setFillColor(hx('#0b0d26'))
    c.rect(CX, H-13.5*mm, CW, 14, fill=1, stroke=0)
    c.setFillColor(GREEN)
    c.setFont('MB', 7)
    c.drawString(CX+8, H-13.5*mm+4,
        '>> ПРОТОКОЛ АКТИВИРОВАН  //  СТАТУС: ОНЛАЙН  //  УРОВЕНЬ ДОПУСКА: АГЕНТ')
    c.setFillColor(DIM2)
    c.drawRightString(CX+CW-8, H-13.5*mm+4, 'BASE-4:12 // REV 2.0')

    # ── TITLE ────────────────────────────────────────────────────────
    ty = H - 30*mm
    for i in range(5, 0, -1):
        c.setFillColor(colors.Color(0.0, 0.9, 1.0, 0.04*i))
        c.setFont('MB', 33)
        c.drawCentredString(W/2, ty + i*0.5, 'КОДЕКС БАЗЫ 4:12')
    c.setFillColor(CYAN)
    c.setFont('MB', 33)
    c.drawCentredString(W/2, ty, 'КОДЕКС БАЗЫ 4:12')

    c.setFillColor(DIM2)
    c.setFont('M', 9.5)
    c.drawCentredString(W/2, H-38*mm, '─ ─ ─   ПРОТОКОЛ АКТИВАЦИИ КИБЕР-АГЕНТА   ─ ─ ─')

    rule_dots(c, CX, H-43.5*mm, CW, CYAN)

    c.setFillColor(YELLOW)
    c.setFont('MI', 10)
    c.drawCentredString(W/2, H-50*mm, '" Помни, Кайрос наблюдает за тобой... "')

    # Binary strip
    c.setFillColor(colors.Color(0.0, 0.9, 1.0, 0.28))
    c.setFont('M', 6)
    c.drawCentredString(W/2, BINARY_Y, BINARY)

    # ── MODULE 01 ────────────────────────────────────────────────────
    draw_module(c, CX, M1_Y, M1_H, CW, GREEN,
                '[МОДУЛЬ 01]  ТЕХНИЧЕСКОЕ ОБСЛУЖИВАНИЕ АГЕНТА',
                'Неисправный агент угрожает всей миссии',
                [
                    (1, 'Регулярно умывайся и следи за чистотой тела и рук.'),
                    (2, 'Держи спальное место в идеальном порядке: одежда сложена, вещи не разбросаны.'),
                    (3, 'Соблюдай чистоту на всей территории базы: сразу убирай мусор.'),
                ],
                '−2 ТОКЕНА', '+2 ТОКЕНА')

    # ── MODULE 02 ────────────────────────────────────────────────────
    draw_module(c, CX, M2_Y, M2_H, CW, CYAN,
                '[МОДУЛЬ 02]  ПРОТОКОЛ СУБОРДИНАЦИИ',
                'Цепочка команд не обсуждается — она выполняется',
                [
                    (4, 'В присутствии Кайроса — строгое молчание, говори только по разрешению.'),
                    (5, 'Слушайся своих навигаторов без возражений — их слово есть команда базы.'),
                    (6, 'Будь пунктуален: опоздание — это сбой, который роняет рейтинг всего кибер-отряда.'),
                    (7, 'На сборах и построениях занимай своё место, внимательно слушай команды.'),
                ],
                '−3 ТОКЕНА', '+3 ТОКЕНА')

    # ── MODULE 03 ────────────────────────────────────────────────────
    draw_module(c, CX, M3_Y, M3_H, CW, ORANGE,
                '[МОДУЛЬ 03]  СЕТЕВАЯ ЭТИКА КИБЕР-АГЕНТА',
                'Сила базы — в связях между агентами',
                [
                    (8,  'Никаких конфликтов, грубых слов и физических столкновений.'),
                    (9,  'Поддерживай товарищей, защищай слабых, береги кибер-отряд.'),
                    (10, 'В ночное время и дневной сон — тишина. Уважение к отдыху других — это уважение к миссии.'),
                ],
                '−2 ТОКЕНА', '+5 ТОКЕНОВ')

    # ── FOOTER ───────────────────────────────────────────────────────
    rule_dots(c, CX, FSEP_Y, CW, CYAN)

    c.setFillColor(WHITE)
    c.setFont('M', 8)
    c.drawCentredString(W/2, FTEXT1_Y,
        'Соблюдение кодекса поднимает рейтинг кибер-отряда и приближает человечество ко спасению.')
    c.setFillColor(DIM2)
    c.setFont('M', 7.5)
    c.drawCentredString(W/2, FTEXT2_Y,
        'Нарушение кодекса ослабляет базу и ставит миссию под угрозу.')

    # Kairos bar
    c.setFillColor(hx('#08091f'))
    c.rect(CX, KAIROS_Y, CW, 15, fill=1, stroke=0)
    c.setFillColor(colors.Color(0.0, 1.0, 0.25, 0.10))
    c.rect(CX, KAIROS_Y, CW, 15, fill=1, stroke=0)
    for i in range(4, 0, -1):
        c.setStrokeColor(colors.Color(0.0, 1.0, 0.25, 0.055*i))
        c.setLineWidth(i*1.6)
        c.rect(CX-i, KAIROS_Y-i, CW+2*i, 15+2*i, fill=0, stroke=1)
    c.setStrokeColor(GREEN)
    c.setLineWidth(0.8)
    c.rect(CX, KAIROS_Y, CW, 15, fill=0, stroke=1)
    c.setFillColor(GREEN)
    c.setFont('MB', 8.5)
    c.drawCentredString(W/2, KAIROS_Y+4.5,
        '// КАЙРОС ОНЛАЙН. ВЕДЁТСЯ ВИДЕО НАБЛЮДЕНИЕ ПО ВСЕЙ БАЗЕ 4:12 //')

    c.save()
    print(f'Saved → {output_path}')

    # Print key Y positions for debugging
    border_bottom = 7*mm
    print(f'\nLayout check (border bottom = {border_bottom:.1f}pt):')
    for label, y in [('KAIROS_Y', KAIROS_Y), ('FSEP_Y', FSEP_Y),
                     ('M3_Y', M3_Y), ('M2_Y', M2_Y), ('M1_Y', M1_Y)]:
        status = 'OK' if y > border_bottom else 'OVERFLOW'
        print(f'  {label:<12} = {y:6.1f}pt  [{status}]')


if __name__ == '__main__':
    out = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                       'kodeks_bazy_412.pdf')
    generate(out)
