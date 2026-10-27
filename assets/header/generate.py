#!/usr/bin/env python3
"""
Renders `header.webp`: the animated terminal header on the profile README.

Scenes:
  1. Handshake: a CRT line opens into a terminal, `ssh` logs in, and `neofetch` prints who I am
     beside a faint, glowing WSO2 logo.
  2. Interests: `cat ~/interests` draws a radar chart of the areas I am most interested in.
  3. Projects: `ls ~/projects` lights up each project as a glowing node in a drifting web.
The last frame fades out so the loop reads as a power cycle.

Every frame is drawn with Pillow; there is no source footage. The rain uses a
fixed seed, so a re-run produces the same file.

Deps: pillow >= 10
Run:  python3 assets/header/generate.py
"""

from __future__ import annotations

import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# Layout is authored at W x H and delivered at EXPORT times that size.
W, H = 880, 440
EXPORT = int(os.environ.get("HEADER_EXPORT", "2"))
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "header.webp")

# Palette: GitHub dark neutrals, Ballerina teal accent, amber for one highlight.
BG = (13, 17, 23)
TEXT = (201, 209, 217)
DIM = (139, 148, 158)
FAINT = (48, 54, 61)
TEAL = (70, 192, 188)
AMBER = (240, 162, 59)

# How much the projects web drifts (0 = still). Drift moves every pixel, so it roughly doubles the file size.
WEB_DRIFT = float(os.environ.get("HEADER_WEB_DRIFT", "1"))

TYPE_MS = 32     # a frame where a character lands
MOTION_MS = 40   # a frame where only something moves
RNG = random.Random(7)


def S(v: float) -> int:
    return round(v * EXPORT)


def font(candidates, size, index_names=()):
    """First available font from `candidates`; for .ttc files, the face whose name matches."""
    for path in candidates:
        if not os.path.exists(path):
            continue
        if path.endswith(".ttc") and index_names:
            for i in range(16):
                try:
                    f = ImageFont.truetype(path, S(size), index=i)
                except OSError:
                    break
                if f.getname()[1] in index_names:
                    return f
        return ImageFont.truetype(path, S(size))
    raise SystemExit(f"no font found in {candidates}")


MONO = ["/System/Library/Fonts/Menlo.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"]
MONO_B = ["/System/Library/Fonts/Menlo.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"]

F_XS = font(MONO, 12, ("Regular",))
F_MONO = font(MONO, 14, ("Regular",))
F_MONO_B = font(MONO_B, 14, ("Bold",))


# The full WSO2 logo (mark and wordmark); the mark alone reads as a heart-rate icon.
LOGO_W = 280
_logo = Image.open(os.path.join(HERE, "wso2-logo.png")).getchannel("A")
LOGO_H = round(LOGO_W * _logo.height / _logo.width)
WSO2_LOGO = _logo.resize((S(LOGO_W), S(LOGO_H)), Image.LANCZOS)


def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def paste_glow(img, mask, blur, colour=TEAL, gain=1.0):
    """Blur `mask` and paste `colour` through it: a soft glow behind whatever the mask outlines."""
    halo = mask.filter(ImageFilter.GaussianBlur(S(blur)))
    if gain != 1.0:
        halo = halo.point(lambda v: min(255, v * gain))
    img.paste(Image.new("RGB", img.size, colour), (0, 0), halo)


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


class Rain:
    """Sparse hex glyphs drifting down the right edge: texture, not content."""

    def __init__(self, n=26):
        self.drops = [[RNG.uniform(560, W - 20), RNG.uniform(-H, H), RNG.uniform(0.6, 1.6),
                       RNG.choice("0123456789abcdef")] for _ in range(n)]

    def step(self):
        for d in self.drops:
            d[1] += d[2] * 2.2
            if d[1] > H:
                d[1] = RNG.uniform(-60, 0)
                d[3] = RNG.choice("0123456789abcdef")

    def draw(self, d, alpha):
        for x, y, speed, ch in self.drops:
            d.text((S(x), S(y)), ch, font=F_XS, fill=mix(BG, FAINT, alpha * (0.5 + speed / 3)))


def frame_base(open_t=1.0, fade=1.0):
    """Background, scanlines and corner brackets. `open_t` animates the CRT opening."""
    img = Image.new("RGB", (S(W), S(H)), BG)
    d = ImageDraw.Draw(img)
    if open_t < 1.0:
        h = max(1, S(H) * ease_out(open_t))
        y0 = (S(H) - h) / 2
        d.rectangle([0, y0, S(W), y0 + h], fill=mix(BG, (22, 27, 34), 1))
        d.line([0, S(H) / 2, S(W), S(H) / 2], fill=mix(BG, TEAL, 1 - open_t), width=S(1))
        return img, d
    for y in range(0, H, 3):  # scanlines pinned to layout pixels
        d.line([0, S(y), S(W), S(y)], fill=mix(BG, (0, 0, 0), 0.25), width=1)
    c, L = mix(BG, FAINT, fade), 18
    for (x, y, sx, sy) in [(12, 12, 1, 1), (W - 12, 12, -1, 1), (12, H - 12, 1, -1), (W - 12, H - 12, -1, -1)]:
        d.line([S(x), S(y), S(x + sx * L), S(y)], fill=c, width=S(1))
        d.line([S(x), S(y), S(x), S(y + sy * L)], fill=c, width=S(1))
    return img, d


def footer(d, left, fade):
    c = mix(BG, DIM, 0.7 * fade)
    d.line([S(20), S(H - 34), S(W - 20), S(H - 34)], fill=mix(BG, FAINT, fade), width=S(1))
    d.text((S(24), S(H - 28)), left, font=F_XS, fill=c)
    right = "github.com/NipunaRanasinghe"
    d.text((S(W - 24) - d.textlength(right, font=F_XS), S(H - 28)), right, font=F_XS, fill=c)


def prompt(d, x, y, cmd, cursor, fade=1.0):
    d.text((S(x), S(y)), "→", font=F_MONO_B, fill=mix(BG, TEAL, fade))
    d.text((S(x + 18), S(y)), cmd, font=F_MONO, fill=mix(BG, TEXT, fade))
    if cursor:
        cx = S(x + 18) + d.textlength(cmd, font=F_MONO)
        d.rectangle([cx + S(1), S(y + 2), cx + S(9), S(y + 17)], fill=mix(BG, TEXT, fade))


def render():
    frames, delays = [], []
    rain = Rain()

    def push(img, ms):
        frames.append(img)
        delays.append(round(ms / 10) * 10)

    def typed(cmd, render_with, base=TYPE_MS, jitter=25):
        """One frame per character, with uneven gaps so it reads as typing."""
        for k in range(1, len(cmd) + 1):
            push(render_with(cmd[:k]), base + RNG.randint(0, jitter))

    def fade_out(render_fade):
        """12 frames fading the scene to black; `render_fade(i, fade)` draws frame i."""
        for i in range(12):
            push(render_fade(i, 1 - (i + 1) / 12), MOTION_MS)

    # Scene 1a: CRT line opens.
    for i in range(10):
        img, d = frame_base(open_t=i / 9)
        push(img, MOTION_MS)

    # Scene 1b: handshake. `ssh` in, then `neofetch` prints who I am beside a faint, glowing WSO2 logo.
    X, Y0 = 44, 52
    INFO = [("name", "Nipuna Ranasinghe"),
            ("role", "technical lead · wso2"),
            ("building", "wso2 integrator · ballerina"),
            ("uptime", "8+ years"),
            ("focus", "integration platforms · developer tooling"),
            ("before", "machine learning research · sutd")]
    PALETTE = [FAINT, mix(BG, TEAL, 0.45), TEAL, mix(TEAL, (255, 255, 255), 0.4),
               mix(BG, AMBER, 0.55), AMBER, DIM, TEXT]
    AY, IX = 178, X  # info block top and left

    def segments(d, y, parts, fade=1.0):
        """Draw (text, colour, font) parts left to right, like a shell theme's prompt line."""
        x = S(X)
        for text, colour, f in parts:
            d.text((x, S(y)), text, font=f, fill=mix(BG, colour, fade))
            x += d.textlength(text, font=f)

    def handshake(cmd1, cursor1, login_a=0.0, cmd2=None, cursor2=False, t=0.0, fade=1.0):
        """`t` runs 0..1 as neofetch prints: art rows top to bottom, info lines a beat behind."""
        img, d = frame_base(fade=fade)
        rain.step(); rain.draw(d, fade)
        segments(d, Y0, [("nipuna", TEAL, F_MONO_B), (" in ", DIM, F_MONO), ("~/wso2", TEXT, F_MONO),
                         (" on ", DIM, F_MONO), ("main", DIM, F_MONO)], fade)
        prompt(d, X, Y0 + 22, cmd1, cursor1, fade)
        if login_a > 0:
            d.text((S(X), S(Y0 + 48)), "Last login: Sun Oct 19 09:12:44 2026 from colombo.lk",
                   font=F_MONO, fill=mix(BG, DIM, login_a * fade))
        if cmd2 is not None:
            segments(d, 126, [("nipuna", TEAL, F_MONO_B), ("@", DIM, F_MONO), ("wso2", TEXT, F_MONO),
                              (" in ", DIM, F_MONO), ("~", TEXT, F_MONO)], fade)
            prompt(d, X, 148, cmd2, cursor2, fade)
        # The faint WSO2 logo sits on the right from the first frame; its glow breathes every 2 s.
        pulse = (1 - math.cos(sum(delays) / 2000 * 2 * math.pi)) / 2
        mask = Image.new("L", img.size, 0)
        mask.paste(WSO2_LOGO, (S(W - 50 - LOGO_W), S(230 - LOGO_H / 2)))
        paste_glow(img, mask, 12, TEAL, gain=(0.15 + 0.35 * pulse) * fade)
        img.paste(Image.new("RGB", img.size, mix(BG, TEAL, (0.16 + 0.12 * pulse) * fade)), (0, 0), mask)
        if t > 0:
            a = ease_out(t * 3 - 0.3) * fade
            hx = S(IX)
            for text, colour in [("nipuna", TEAL), ("@", DIM), ("wso2", TEAL)]:
                d.text((hx, S(AY)), text, font=F_MONO_B, fill=mix(BG, colour, a))
                hx += d.textlength(text, font=F_MONO_B)
            d.text((S(IX), S(AY + 20)), "-" * 11, font=F_MONO, fill=mix(BG, FAINT, a))
            for i, (k, v) in enumerate(INFO):
                a = ease_out(t * 3 - 0.6 - i * 0.2) * fade
                y = AY + 44 + i * 21
                d.text((S(IX), S(y)), k, font=F_MONO_B, fill=mix(BG, TEAL, a))
                lead = " " + "." * (10 - len(k)) + " "
                kx = S(IX) + d.textlength(k, font=F_MONO_B)
                d.text((kx, S(y)), lead, font=F_MONO, fill=mix(BG, FAINT, a))
                d.text((kx + d.textlength(lead, font=F_MONO), S(y)), v, font=F_MONO,
                       fill=mix(BG, AMBER if k == "uptime" else TEXT, a))
            a = ease_out(t * 3 - 1.9) * fade
            for i, c in enumerate(PALETTE):  # neofetch's colour blocks, in the theme's colours
                x = IX + i * 26
                d.rectangle([S(x), S(AY + 180), S(x + 22), S(AY + 192)], fill=mix(BG, c, a))
        footer(d, "session", fade)
        return img

    push(handshake("", True), 240)   # two cursor blinks before typing
    push(handshake("", False), 240)
    ssh = "ssh nipuna@wso2.com"
    typed(ssh, lambda c: handshake(c, True))
    push(handshake(ssh, False), 200)
    for i in range(3):
        push(handshake(ssh, False, login_a=(i + 1) / 3), MOTION_MS)
    push(handshake(ssh, False, login_a=1), 200)
    push(handshake(ssh, False, 1, cmd2="", cursor2=True), 240)
    typed("neofetch", lambda c: handshake(ssh, False, 1, cmd2=c, cursor2=True))
    push(handshake(ssh, False, 1, cmd2="neofetch"), 250)
    N = 24
    for i in range(N):
        push(handshake(ssh, False, 1, cmd2="neofetch", t=(i + 1) / N), MOTION_MS)
    for i in range(36):  # hold long enough to read, in short frames so the mark keeps breathing
        push(handshake(ssh, False, 1, cmd2="neofetch", t=1), 170)
    fade_out(lambda i, f: handshake(ssh, False, 1, cmd2="neofetch", t=1, fade=f))

    # Scene 2: interests. `cat ~/interests` draws a radar chart; the teal shape grows out along each axis.
    RX, RY, RR = 440, 236, 100
    RADAR_FLOOR = 0.4  # the centre plots this value, not 0, so the gaps between close ratings show
    interests = [  # (label, detail, value 0..1), clockwise from the top; neighbours are related areas
        ("AI agents", "agentic systems · copilots", 0.95),
        ("Integration", "WSO2 Integrator", 0.85),
        ("Open-source community", "maintaining · contributing", 0.7),
        ("Languages & compilers", "Ballerina · runtimes", 0.75),
        ("Developer tooling", "LSP · debuggers · IDEs", 0.9),
    ]
    cat = "cat ~/interests"

    def axis_pt(k, r):
        ang = -math.pi / 2 + k * 2 * math.pi / len(interests)
        return RX + r * math.cos(ang), RY + r * math.sin(ang)

    def radar(cmd, grid_a, grow, tt, fade=1.0, out_a=0.0):
        img, d = frame_base(fade=fade)
        rain.step(); rain.draw(d, 0.3 * fade)
        prompt(d, X, Y0, cmd, cursor=grid_a == 0 and fade == 1.0, fade=fade)
        if out_a > 0:
            d.text((S(X + 18), S(Y0 + 24)), f"{len(interests)} areas", font=F_MONO, fill=mix(BG, DIM, out_a * fade))
        if grid_a > 0:  # rings and axes
            for ring in (0.25, 0.5, 0.75, 1.0):
                pts = [axis_pt(k, RR * ring) for k in range(len(interests))]
                d.line([(S(x), S(y)) for x, y in pts + pts[:1]], fill=mix(BG, FAINT, grid_a * fade), width=S(1))
            for k in range(len(interests)):
                x, y = axis_pt(k, RR)
                d.line([S(RX), S(RY), S(x), S(y)], fill=mix(BG, FAINT, grid_a * fade), width=S(1))
        breathe = 1 + 0.025 * math.sin(tt * 0.15)
        shape = [axis_pt(k, RR * (v - RADAR_FLOOR) / (1 - RADAR_FLOOR) * ease_out(grow) * breathe)
             for k, (_, _, v) in enumerate(interests)]
        if grow > 0:
            fill = Image.new("L", img.size, 0)
            ImageDraw.Draw(fill).polygon([(S(x), S(y)) for x, y in shape], fill=round(255 * 0.2 * fade))
            img.paste(Image.new("RGB", img.size, TEAL), (0, 0), fill)
            glow = Image.new("L", img.size, 0)
            g = ImageDraw.Draw(glow)
            g.line([(S(x), S(y)) for x, y in shape + shape[:1]], fill=round(200 * fade), width=S(3))
            for x, y in shape:
                g.ellipse([S(x - 9), S(y - 9), S(x + 9), S(y + 9)], fill=round(255 * ease_out(grow) * fade))
            paste_glow(img, glow, 8)
            d = ImageDraw.Draw(img)
            d.line([(S(x), S(y)) for x, y in shape + shape[:1]], fill=mix(BG, TEAL, fade), width=S(1.5))
            for x, y in shape:
                d.ellipse([S(x - 4), S(y - 4), S(x + 4), S(y + 4)], fill=mix(BG, (220, 250, 248), ease_out(grow) * fade))
        for k, (label, detail, v) in enumerate(interests):  # labels appear as the shape reaches each axis
            a = ease_out(grow * 1.6 - 0.3 - k * 0.12) * fade
            if a <= 0:
                continue
            x, y = axis_pt(k, RR + 22)
            anchor_x = "ma" if abs(x - RX) < 10 else ("la" if x > RX else "ra")
            ty = y - 30 if y < RY - RR * 0.9 else (y - 4 if y > RY + 10 else y - 12)
            d.text((S(x), S(ty)), label, font=F_MONO_B, fill=mix(BG, TEXT, a), anchor=anchor_x)
            d.text((S(x), S(ty + 18)), detail, font=F_XS, fill=mix(BG, DIM, a), anchor=anchor_x)
        footer(d, "interests", fade)
        return img

    push(radar("", 0, 0, 0), 500)
    typed(cat, lambda c: radar(c, 0, 0, 0))
    push(radar(cat, 0, 0, 0), 300)
    tt = 0
    for i in range(10):  # grid fades in
        tt += 1
        push(radar(cat, (i + 1) / 10, 0, tt, out_a=(i + 1) / 10), MOTION_MS)
    for i in range(32):  # shape grows out to each value
        tt += 1
        push(radar(cat, 1, (i + 1) / 32, tt, out_a=1), MOTION_MS)
    for i in range(36):  # hold, breathing
        tt += 1
        push(radar(cat, 1, 1, tt, out_a=1), MOTION_MS)
    push(radar(cat, 1, 1, tt, out_a=1), 1400)
    fade_out(lambda i, f: radar(cat, 1, 1, tt + i + 1, out_a=1, fade=f))

    # Scene 3: projects, as a living web. Faint background dots drift and link to their neighbours;
    # the projects light up one by one, link to the centre and to related projects, and signals travel the links.
    CX, CY = 440, 222
    projects = [  # (x, y, name, role, stars)
        (170, 150, "lsp4intellij", "creator & maintainer", "★ 479"),
        (710, 150, "awesome-ai-agents", "creator & maintainer", "★ 58"),
        (130, 285, "Ballerina Debugger", "creator", ""),
        (720, 285, "Ballerina VS Code", "core contributor", ""),
        (320, 340, "Ballerina Semver Checker", "creator", ""),
        (580, 340, "Ballerina IntelliJ Plugin", "core contributor", ""),
    ]
    # Related projects: lsp4intellij-IntelliJ plugin, debugger-VS Code, debugger-IntelliJ plugin, semver-VS Code.
    links = [(0, 5), (2, 3), (2, 5), (4, 3)]
    web_rng = random.Random(11)
    dots = [(web_rng.uniform(30, W - 30), web_rng.uniform(110, H - 50), web_rng.uniform(4, 10),
             web_rng.uniform(4, 10), web_rng.uniform(0, 6.3), web_rng.uniform(0.5, 1.0)) for _ in range(34)]
    LINE = (52, 96, 98)
    ls = "ls ~/projects"

    def drift(x, y, ax, ay, ph, sp, tt):
        tt *= WEB_DRIFT
        return x + ax * math.sin(tt * 0.035 * sp + ph), y + ay * math.cos(tt * 0.03 * sp + ph * 1.3)

    def node_pos(i, tt):
        x, y = projects[i][:2]
        return drift(x, y, 3, 2.5, i * 1.7, 1.0, tt)

    def edge_ends(e, nodes_now):
        if e[0] == "c":  # centre to project, starting just outside the hub's orbiting arcs
            x, y = nodes_now[e[1]]
            L = math.hypot(x - CX, y - CY)
            return (CX + (x - CX) / L * 34, CY + (y - CY) / L * 34), (x, y)
        return nodes_now[e[1]], nodes_now[e[2]]

    all_edges = [("c", i) for i in range(6)] + [("l", a, b) for a, b in links]

    def web(cmd, centre_a, lit, tt, web_a, signals=(), fade=1.0, out_a=0.0):
        """`lit[i]` in 0..1: how far project i has lit up (edge drawn, then node glows)."""
        img, d = frame_base(fade=fade)
        rain.step(); rain.draw(d, 0.3 * fade)
        prompt(d, X, Y0, cmd, cursor=centre_a == 0 and fade == 1.0, fade=fade)
        if out_a > 0:
            d.text((S(X + 18), S(Y0 + 24)), f"{len(projects)} projects", font=F_MONO, fill=mix(BG, DIM, out_a * fade))
        nodes_now = [node_pos(i, tt) for i in range(6)]
        node_a = [ease_out(l * 2 - 1) for l in lit]
        if web_a > 0:  # background web, dimmed as projects light so it stays behind their labels
            web_a *= 1 - 0.55 * sum(node_a) / len(node_a)
            pts = [drift(*p, tt) for p in dots]
            for i, p in enumerate(pts):
                for q in pts[i + 1:]:
                    dd = math.dist(p, q)
                    if dd < 120:
                        d.line([S(p[0]), S(p[1]), S(q[0]), S(q[1])], fill=mix(BG, (40, 62, 66), (1 - dd / 120) * web_a * fade), width=S(1))
                for k, n in enumerate(nodes_now):
                    dd = math.dist(p, n)
                    if node_a[k] > 0 and dd < 150:
                        d.line([S(p[0]), S(p[1]), S(n[0]), S(n[1])], fill=mix(BG, (40, 70, 72), (1 - dd / 150) * node_a[k] * web_a * fade), width=S(1))
            for x, y in pts:
                d.ellipse([S(x - 1.6), S(y - 1.6), S(x + 1.6), S(y + 1.6)], fill=mix(BG, (70, 92, 98), web_a * fade))
        for i in range(6):  # centre to projects, growing outwards
            e = ease_out(lit[i] * 2)
            if e > 0:
                (sx, sy), (x, y) = edge_ends(("c", i), nodes_now)
                d.line([S(sx), S(sy), S(sx + (x - sx) * e), S(sy + (y - sy) * e)], fill=mix(BG, LINE, fade), width=S(1))
        for a, b in links:  # related projects, once both are lit
            la = min(node_a[a], node_a[b])
            if la > 0:
                (x0, y0), (x1, y1) = nodes_now[a], nodes_now[b]
                d.line([S(x0), S(y0), S(x1), S(y1)], fill=mix(BG, LINE, 0.8 * la * fade), width=S(1))
        glow = Image.new("L", img.size, 0)
        g = ImageDraw.Draw(glow)
        for i, (x, y) in enumerate(nodes_now):
            if node_a[i] > 0:
                breathe = 0.8 + 0.2 * math.sin(tt * 0.18 + i * 1.1)
                g.ellipse([S(x - 11), S(y - 11), S(x + 11), S(y + 11)], fill=round(255 * node_a[i] * breathe * fade))
        if centre_a > 0:
            g.ellipse([S(CX - 17), S(CY - 17), S(CX + 17), S(CY + 17)], fill=round(240 * centre_a * fade))
        sig_pts = []
        for e, s_, fwd in signals:
            p0, p1 = edge_ends(e, nodes_now)
            k = s_ if fwd else 1 - s_
            px, py = p0[0] + (p1[0] - p0[0]) * k, p0[1] + (p1[1] - p0[1]) * k
            sig_pts.append((px, py))
            g.ellipse([S(px - 5), S(py - 5), S(px + 5), S(py + 5)], fill=round(150 * fade))
        paste_glow(img, glow, 22, mix(BG, TEAL, 0.7), gain=1.6)  # wide, soft halo
        paste_glow(img, glow, 7)                                 # tight, bright halo
        d = ImageDraw.Draw(img)
        for px, py in sig_pts:
            d.ellipse([S(px - 2), S(py - 2), S(px + 2), S(py + 2)], fill=mix(BG, (220, 250, 248), fade))
        if centre_a > 0:  # the hub: larger core, a ring, and three arcs orbiting it
            a = centre_a * fade
            d.ellipse([S(CX - 18), S(CY - 18), S(CX + 18), S(CY + 18)], outline=mix(BG, TEAL, 0.55 * a), width=S(1))
            spin = tt * 2.5
            for k in range(3):
                start = spin + k * 120
                d.arc([S(CX - 27), S(CY - 27), S(CX + 27), S(CY + 27)], start, start + 42, fill=mix(BG, TEAL, a), width=S(1.5))
            d.ellipse([S(CX - 8), S(CY - 8), S(CX + 8), S(CY + 8)], fill=mix(BG, (236, 240, 244), a))
            d.text((S(CX), S(CY + 36)), "localhost", font=F_MONO_B, fill=mix(BG, TEXT, a), anchor="ma",
                   stroke_width=S(3), stroke_fill=BG)  # outline in BG hides edges passing behind
        for i, (x, y) in enumerate(nodes_now):
            n = node_a[i] * fade
            if n <= 0:
                continue
            _, _, name, role, stars = projects[i]
            d.ellipse([S(x - 5), S(y - 5), S(x + 5), S(y + 5)], fill=mix(BG, (220, 250, 248), n))
            d.text((S(x), S(y + 14)), name, font=F_MONO, fill=mix(BG, TEXT, n), anchor="ma",
                   stroke_width=S(3), stroke_fill=BG)  # outline in BG hides web lines behind the label
            sub_w = d.textlength(role, font=F_XS) + (d.textlength("  " + stars, font=F_XS) if stars else 0)
            sx = S(x) - sub_w / 2
            d.text((sx, S(y + 33)), role, font=F_XS, fill=mix(BG, DIM, n), stroke_width=S(3), stroke_fill=BG)
            if stars:
                d.text((sx + d.textlength(role + "  ", font=F_XS), S(y + 33)), stars, font=F_XS, fill=mix(BG, AMBER, n),
                       stroke_width=S(3), stroke_fill=BG)
        footer(d, "projects", fade)
        return img

    tt = 0
    push(web("", 0, [0] * 6, tt, 0), 500)
    typed(ls, lambda c: web(c, 0, [0] * 6, tt, 0))
    push(web(ls, 0, [0] * 6, tt, 0), 300)
    for i in range(8):  # centre and background web fade in
        tt += 1
        push(web(ls, (i + 1) / 8, [0] * 6, tt, (i + 1) / 16, out_a=(i + 1) / 8), MOTION_MS)
    lit = [0.0] * 6
    for i in range(63):  # one project every 9 frames, each taking 18 to fully light
        tt += 1
        for j in range(6):
            lit[j] = max(0.0, min(1.0, (i - j * 9) / 18))
        push(web(ls, 1, lit, tt, min(1.0, 0.5 + i / 30), out_a=1), MOTION_MS)
    signals = []  # [edge, progress, forwards]
    sig_rng = random.Random(5)
    for i in range(50):  # everything lit: the web drifts and signals travel the links
        tt += 1
        if i % 4 == 0:
            signals.append([sig_rng.choice(all_edges), 0.0, sig_rng.random() < 0.6])
        for sg in signals:
            sg[1] += 0.06
        signals = [sg for sg in signals if sg[1] < 1]
        push(web(ls, 1, lit, tt, 1, signals, out_a=1), MOTION_MS)
    push(web(ls, 1, lit, tt, 1, signals, out_a=1), 1200)
    fade_out(lambda i, f: web(ls, 1, lit, tt + i + 1, 1, signals, out_a=1, fade=f))
    img, _ = frame_base(open_t=0.0)
    push(img, 400)
    return frames, delays


def save(frames, delays):
    # Animated WebP: full colour (no GIF palette banding on the glow) at under half the GIF's size.
    frames[0].save(OUT, format="WEBP", save_all=True, append_images=frames[1:], duration=delays, loop=0,
                   quality=70, method=4, allow_mixed=True)  # mixed: no lossy residue left on the fade-out frames
    print(f"{OUT}: {len(frames)} frames, {sum(delays) / 1000:.1f}s, {os.path.getsize(OUT) / 1e6:.2f} MB")


if __name__ == "__main__":
    save(*render())
