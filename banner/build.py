#!/usr/bin/env python3
"""Собирает profile-dark.svg и profile-light.svg из about.md.

Правишь about.md → запускаешь `python build.py` → коммитишь обе SVG.
Зависимость одна: pip install fonttools
"""
import random, re
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

ROOT = Path(__file__).resolve().parent
W = 800                      # ширина колонки README на GitHub
HEADER_H = 150               # высота шапки с ником
CYCLE = 17.0                 # длина цикла анимации, с
BURSTS = [7.2, 16.1]         # моменты сбоев внутри цикла → паузы 8.9 и 8.1 с
BURST_LEN = 0.65             # длительность одного сбоя, с
GLITCH_CHARS = "░▒▓█▚▞▙▟■◘◙†‡¦§¤¬±×÷ØÞßðħŧŋ∂∆≠≈µ¿‰¥ЖЯЩҨӁ¶Ѯ‽⌐"

THEMES = {
    "dark":  dict(fg="#f0f6fc", muted="#9198a1", border="#3d444d", border_op=".7", code="#656c76", code_op=".2",
                  accent="#3fb950", red="#ff3b5c", cyan="#00e5ff", blend="screen"),
    "light": dict(fg="#1f2328", muted="#59636e", border="#d1d9e0", border_op="1", code="#818b98", code_op=".12",
                  accent="#1a7f37", red="#ff3b5c", cyan="#00b7d4", blend="multiply"),
}

FONT_FILES = {"n": "NotoSans-Regular.ttf", "b": "NotoSans-SemiBold.ttf", "x": "NotoSans-ExtraBold.ttf", "c": "NotoSansMono-Regular.ttf"}
FONTS = {k: TTFont(ROOT / "fonts" / f) for k, f in FONT_FILES.items()}
GS = {k: (f.getGlyphSet(), f.getBestCmap(), f["head"].unitsPerEm) for k, f in FONTS.items()}


def _gname(style, ch):
    cmap = GS[style][1]
    return cmap.get(ord(ch)) or cmap.get(ord("?"))


def adv(style, s, size):
    gs, _, upm = GS[style]
    return sum(gs[_gname(style, ch)].width for ch in s) * size / upm


def _round(d):
    return re.sub(r"-?\d+\.\d+", lambda m: f"{float(m.group()):.1f}".rstrip("0").rstrip("."), d)


def draw(style, s, size, x, y, corrupt=None):
    """Контур строки. corrupt(ch) -> символ-замена или None; замена рисуется моноширинным шрифтом на месте буквы."""
    gs, _, upm = GS[style]
    pen = SVGPathPen(gs)
    pen_c = SVGPathPen(GS["c"][0])
    k = size / upm
    for ch in s:
        g = _gname(style, ch)
        sub = corrupt(ch) if corrupt else None
        if sub:
            kc = size / GS["c"][2]
            GS["c"][0][_gname("c", sub)].draw(TransformPen(pen_c, (kc, 0, 0, -kc, x, y)))
        else:
            gs[g].draw(TransformPen(pen, (k, 0, 0, -k, x, y)))
        x += gs[g].width * k
    return _round(pen.getCommands() + pen_c.getCommands())


# ---------------------------------------------------------------- about.md
def parse_md(text):
    meta, body = {}, text
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if m:
        body = text[m.end():]
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1); meta[k.strip()] = v.strip()
    blocks, para, items = [], [], []

    def flush():
        nonlocal para, items
        if para: blocks.append(("p", " ".join(para))); para = []
        if items: blocks.append(("ul", items)); items = []

    for line in body.splitlines():
        s = line.strip()
        if not s: flush()
        elif s.startswith("## "): flush(); blocks.append(("h2", s[3:]))
        elif s.startswith("- "):
            if para: flush()
            items.append(s[2:])
        else:
            if items: flush()
            para.append(s)
    flush()
    return meta, blocks


def inline_words(md):
    segs = []
    for part in re.split(r"(`[^`]+`|\*\*[^*]+\*\*)", md):
        if not part: continue
        if part.startswith("`"): segs.append((part[1:-1], "c"))
        elif part.startswith("**"): segs.append((part[2:-2], "b"))
        else: segs.append((part, "n"))
    words, cur = [], []
    for text, st in segs:
        if st == "c": cur.append((text, st)); continue
        for i, p in enumerate(text.split(" ")):
            if i > 0 and cur: words.append(cur); cur = []
            if p: cur.append((p, st))
    if cur: words.append(cur)
    return words


# ---------------------------------------------------------------- раскладка
class Layout:
    """Раскладывает блоки в стиле README GitHub. Запоминает элементы, чтобы нарисовать их и «битыми»."""

    def __init__(self, y0):
        self.y = y0; self.glyphs = []; self.shapes = []   # glyphs: (style, text, size, x, y, line_id)
        self.line = 0

    def _seg_w(self, t, st):
        return adv("c", t, 13.6) + 12.8 if st == "c" else adv(st, t, 16)

    def paragraph(self, md, x0=0, after=16, bullet=False):
        space = adv("n", " ", 16)
        lines, cur, cur_w = [], [], 0
        for wd in inline_words(md):
            ww = sum(self._seg_w(*s) for s in wd)
            need = ww if not cur else cur_w + space + ww
            if cur and need > W - x0: lines.append(cur); cur, cur_w = [wd], ww
            else: cur.append(wd); cur_w = need
        if cur: lines.append(cur)
        if bullet: self.shapes.append(("bullet", x0 - 14, self.y + 12.5))
        for ln in lines:
            x, base = x0, self.y + 17
            for i, wd in enumerate(ln):
                if i: x += space
                for t, st in wd:
                    if st == "c":
                        tw = adv("c", t, 13.6)
                        self.shapes.append(("chip", x, base - 14.6, tw + 12.8))
                        self.glyphs.append(("c", t, 13.6, x + 6.4, base, self.line)); x += tw + 12.8
                    else:
                        self.glyphs.append((st, t, 16, x, base, self.line)); x += adv(st, t, 16)
            self.y += 24; self.line += 1
        self.y += after

    def h2(self, text, first=False):
        if not first: self.y += 8
        self.glyphs.append(("b", text, 24, 0, self.y + 23, self.line)); self.line += 1
        self.y += 37.2
        self.shapes.append(("rule", self.y)); self.y += 17


def build_layout(blocks):
    L = Layout(HEADER_H + 14)
    first = True
    for kind, val in blocks:
        if kind == "h2": L.h2(val, first=first)
        elif kind == "p": L.paragraph(val)
        elif kind == "ul":
            for i, it in enumerate(val): L.paragraph(it, x0=32, after=4 if i < len(val) - 1 else 12, bullet=True)
        first = False
    return L


def corrupter(seed, line_heat):
    rs = random.Random(seed)
    def f_for(line):
        p = line_heat.get(line, 0.03)
        def f(ch):
            if ch == " " or rs.random() > p: return None
            return rs.choice(GLITCH_CHARS)
        return f
    return f_for


# ---------------------------------------------------------------- анимация
def burst_steps(rs, n, amp, zero_p=0.35):
    """Случайные значения на n подшагах одного сбоя."""
    return [0 if rs.random() < zero_p else rs.uniform(-amp, amp) for _ in range(n)]


def keyframes(name, prop_fn, rs, n=6, amp=20.0, zero_p=0.35):
    """Ступенчатые ключевые кадры: вне сбоя prop_fn(0), в сбое — прыжки."""
    fr = ["0% {" + prop_fn(0) + "}"]
    for b in BURSTS:
        vals = burst_steps(rs, n, amp, zero_p)
        for j, v in enumerate(vals):
            t = (b + BURST_LEN * j / n) / CYCLE * 100
            fr.append(f"{t:.3f}% {{ {prop_fn(v)} }}")
        fr.append(f"{(b + BURST_LEN) / CYCLE * 100:.3f}% {{ {prop_fn(0)} }}")
    fr.append("100% {" + prop_fn(0) + "}")
    return f"@keyframes {name} {{ {' '.join(fr)} }}"


def window_keyframes(name, on, off, segs):
    """Видимость слоя: segs — список (начало_доли, конец_доли) внутри сбоя, где слой включён."""
    fr = [f"0% {{ opacity: {off}; }}"]
    for b in BURSTS:
        for a, z in segs:
            fr.append(f"{(b + BURST_LEN * a) / CYCLE * 100:.3f}% {{ opacity: {on}; }}")
            fr.append(f"{(b + BURST_LEN * z) / CYCLE * 100:.3f}% {{ opacity: {off}; }}")
    fr.append(f"100% {{ opacity: {off}; }}")
    return f"@keyframes {name} {{ {' '.join(fr)} }}"


def render(theme, meta, L, total_h):
    T = THEMES[theme]
    rs = random.Random(7)
    nick, status = meta.get("nick", "dclxvist"), meta.get("status", "available for hire")

    # --- шапка
    nw = adv("x", nick, 68)
    nick_d = draw("x", nick, 68, (W - nw) / 2, 84)
    pre, st = "$ ", f"status: {status}"
    lw = adv("c", pre + st, 14)
    sx = (W - lw) / 2; sx2 = sx + adv("c", pre, 14)
    pre_d = draw("c", pre, 14, sx, 122)
    st_rs = random.Random(3)
    st_n = draw("c", st, 14, sx2, 122)
    st_a = draw("c", st, 14, sx2, 122, corrupt=lambda ch: st_rs.choice(GLITCH_CHARS) if ch != " " and st_rs.random() < .45 else None)
    cur_x = sx2 + adv("c", st, 14) + 3

    # --- текст: обычный слой и два «битых»
    lines = sorted({g[5] for g in L.glyphs})
    heat = {ln: random.Random(ln * 13).choice([0.0, 0.04, 0.1, 0.22, 0.32]) for ln in lines}
    ca, cb = corrupter(11, heat), corrupter(29, heat)
    fa = {ln: ca(ln) for ln in lines}; fb = {ln: cb(ln) for ln in lines}
    tn = "".join(f'<path d="{draw(s, t, z, x, y)}"/>' for s, t, z, x, y, ln in L.glyphs)
    ta = "".join(f'<path d="{draw(s, t, z, x, y, fa[ln])}"/>' for s, t, z, x, y, ln in L.glyphs)
    tb = "".join(f'<path d="{draw(s, t, z, x, y, fb[ln])}"/>' for s, t, z, x, y, ln in L.glyphs)
    shapes = []
    for sh in L.shapes:
        if sh[0] == "rule": shapes.append(f'<rect x="0" y="{sh[1]:.1f}" width="{W}" height="1" fill="{T["border"]}" fill-opacity="{T["border_op"]}"/>')
        elif sh[0] == "chip": shapes.append(f'<rect x="{sh[1]:.1f}" y="{sh[2]:.1f}" width="{sh[3]:.1f}" height="20.4" rx="6" fill="{T["code"]}" fill-opacity="{T["code_op"]}"/>')
        elif sh[0] == "bullet": shapes.append(f'<circle cx="{sh[1]:.1f}" cy="{sh[2]:.1f}" r="2.6" fill="{T["fg"]}"/>')

    # --- полосы, которые сдвигаются при сбое
    def bands(y0, y1, hmin, hmax):
        out, y = [], y0
        while y < y1:
            h = rs.randint(hmin, hmax); out.append((y, min(y1, y + h) - y)); y += h
        return out
    hb = bands(0, HEADER_H, 12, 34)
    tbands = bands(HEADER_H, total_h, 18, 64)

    css = [f"""
.b {{ animation-timing-function: steps(1, end); animation-duration: {CYCLE}s; animation-iteration-count: infinite; }}
.ln {{ animation-name: vis_n; }} .la {{ animation-name: vis_a; opacity: 0; }} .lb {{ animation-name: vis_b; opacity: 0; }}
.rgb {{ mix-blend-mode: {T["blend"]}; opacity: 0; }}
.blink {{ animation: blink 1.05s steps(1) infinite; }}
@keyframes blink {{ 0%, 50% {{ opacity: 1; }} 50.01%, 100% {{ opacity: 0; }} }}
{window_keyframes("vis_n", 1, 1, [])}
{window_keyframes("vis_a", 1, 0, [(0, .34), (.67, 1)])}
{window_keyframes("vis_b", 1, 0, [(.34, .67)])}
{window_keyframes("vis_n_off", 0, 1, [(0, 1)])}
.ln {{ animation-name: vis_n_off; }}
{keyframes("rr", lambda v: f"transform: translateX({abs(v):.1f}px); opacity: {'.7' if v else '0'};", rs, 5, 5, .3)}
{keyframes("cc", lambda v: f"transform: translateX({-abs(v):.1f}px); opacity: {'.7' if v else '0'};", rs, 5, 5, .3)}
{keyframes("tr", lambda v: f"transform: translateX({abs(v):.1f}px); opacity: {'.35' if v else '0'};", rs, 5, 2.5, .5)}
{keyframes("tc", lambda v: f"transform: translateX({-abs(v):.1f}px); opacity: {'.35' if v else '0'};", rs, 5, 2.5, .5)}
.r {{ animation-name: rr; }} .c {{ animation-name: cc; }} .rt {{ animation-name: tr; }} .ct {{ animation-name: tc; }}
@media (prefers-reduced-motion: reduce) {{ .b, .blink {{ animation: none !important; }} .la, .lb, .rgb {{ display: none; }} }}
"""]
    groups = []

    def banded(ref_n, ref_a, ref_b, band_list, amp, prefix, fill):
        out = []
        for i, (y, h) in enumerate(band_list):
            css.append(keyframes(f"{prefix}{i}", lambda v: f"transform: translateX({v:.1f}px);", rs, 6, amp, .45))
            css.append(f".{prefix}{i} {{ animation-name: {prefix}{i}; }}")
            out.append(f'<clipPath id="{prefix}c{i}"><rect x="-60" y="{y:.1f}" width="{W + 120}" height="{h + .5:.1f}"/></clipPath>')
            out.append(f'<g clip-path="url(#{prefix}c{i})"><g class="b {prefix}{i}">'
                       f'<use href="#{ref_n}" class="b ln" fill="{fill}"/><use href="#{ref_a}" class="b la" fill="{fill}"/>'
                       + (f'<use href="#{ref_b}" class="b lb" fill="{fill}"/>' if ref_b else "") + '</g></g>')
        return out

    body = f'''<defs>
  <g id="hN"><path d="{nick_d}"/><path d="{st_n}"/></g>
  <g id="hA"><path d="{nick_d}"/><path d="{st_a}"/></g>
  <g id="tN">{tn}</g><g id="tA">{ta}</g><g id="tB">{tb}</g>
</defs>
<path d="{pre_d}" fill="{T["accent"]}"/>
<rect class="blink" x="{cur_x:.1f}" y="109" width="8.5" height="16" fill="{T["fg"]}" fill-opacity=".75"/>
{"".join(shapes)}
<use href="#hN" class="b rgb r" fill="{T["red"]}"/><use href="#hN" class="b rgb c" fill="{T["cyan"]}"/>
<use href="#tN" class="b rgb rt" fill="{T["red"]}"/><use href="#tN" class="b rgb ct" fill="{T["cyan"]}"/>
{"".join(banded("hN", "hA", "hA", hb, 34, "h", T["fg"]))}
{"".join(banded("tN", "tA", "tB", tbands, 16, "t", T["fg"]))}'''

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {total_h}" width="{W}" height="{total_h}" role="img" aria-label="{nick} — {status}">
<style>{"".join(css)}</style>
{body}
</svg>'''


def main():
    meta, blocks = parse_md((ROOT / "about.md").read_text(encoding="utf-8"))
    L = build_layout(blocks)
    total_h = int(L.y) + 4
    for theme in THEMES:
        svg = render(theme, meta, L, total_h)
        (ROOT / f"profile-{theme}.svg").write_text(svg, encoding="utf-8")
        print(f"profile-{theme}.svg  {len(svg) // 1024} KB  {W}x{total_h}")


if __name__ == "__main__":
    main()
