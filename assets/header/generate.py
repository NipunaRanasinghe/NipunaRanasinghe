#!/usr/bin/env python3
"""
Renders `header.webp`: the animated terminal header on the profile README.

Scenes:
  1. Handshake: a CRT line opens into a terminal, `ssh` and `whoami` are typed.
  2. Identity: the `whoami` answer as a card.
  3. Interests: `cat ~/interests` draws a radar chart of the areas I work in.
  4. Projects: `ls ~/projects` lights up each project as a glowing node in a drifting web.
  (Integration: `bal run` starts a service and messages flow through it.
   Disabled by ENABLE_INTEGRATION_SCENE; when on, it plays between 2 and 3.)
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

# The integration-flow scene is kept but switched off. Set True to play it between the identity card and projects.
ENABLE_INTEGRATION_SCENE = False
# How much the projects web drifts (0 = still). Drift moves every pixel, so it roughly doubles the file size.
WEB_DRIFT = float(os.environ.get("HEADER_WEB_DRIFT", "1"))

TYPE_MS = 45     # a frame where a character lands
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
DISP = ["/System/Library/Fonts/HelveticaNeue.ttc", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]
DISP_R = ["/System/Library/Fonts/HelveticaNeue.ttc", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]

F_XS = font(MONO, 10, ("Regular",))
F_MONO = font(MONO, 14, ("Regular",))
F_MONO_B = font(MONO_B, 14, ("Bold",))
F_NAME = font(DISP, 50, ("Bold",))
F_TAG = font(DISP_R, 20, ("Regular",))


# The WSO2 symbol (the circle with the pulse line) is the left square of the logo.
_logo = Image.open(os.path.join(HERE, "wso2-logo.png")).convert("RGBA")
WSO2_MARK = _logo.crop((0, 0, _logo.height, _logo.height)).resize((S(230), S(230)), Image.LANCZOS).getchannel("A")


def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


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

    # Scene 1a: CRT line opens.
    for i in range(10):
        img, d = frame_base(open_t=i / 9)
        push(img, MOTION_MS)

    # Scene 1b: handshake.
    X, Y0 = 44, 52
    status = "nipuna on master  ·  wso2 integrator"
    lines = []  # (text, colour) printed output so far

    def term(cmd, cursor, extra=()):
        img, d = frame_base()
        rain.step(); rain.draw(d, 1.0)
        d.text((S(X), S(Y0)), status, font=F_MONO, fill=DIM)
        y = Y0 + 26
        for kind, text in lines + list(extra):
            if kind == "cmd":
                prompt(d, X, y, text, False)
            else:
                d.text((S(X + 18), S(y)), text, font=F_MONO, fill=kind)
            y += 22
        if cmd is not None:
            prompt(d, X, y, cmd, cursor)
        footer(d, "session", 1.0)
        return img

    def type_cmd(cmd):
        for blink in range(6):  # idle cursor before typing
            push(term("", blink % 2 == 0), 120)
        for k in range(1, len(cmd) + 1):
            push(term(cmd[:k], True), TYPE_MS + RNG.randint(0, 40))
        push(term(cmd, True), 260)
        lines.append(("cmd", cmd))

    type_cmd("ssh nipuna@wso2.com")
    for out in [(DIM, "connecting to wso2.com ..."), (TEAL, "welcome back, nipuna.")]:
        lines.append(out)
        push(term("", True), 380)
    type_cmd("whoami")
    push(term(None, False), 300)

    # Scene 2: identity card. Fades in, holds, fades out.
    rows = [("role", "technical lead · wso2"),
            ("building", "wso2 integrator · ballerina"),
            ("experience", "8+ years · integration & developer tooling"),
            ("before", "machine learning research · sutd")]

    def card(t, fade=1.0):
        img, d = frame_base(fade=fade)
        rain.step(); rain.draw(d, fade)
        mark_c = mix(BG, TEAL, 0.16 * ease_out(t * 2 - 0.4) * fade)  # faint watermark
        img.paste(Image.new("RGB", WSO2_MARK.size, mark_c), (S(W - 60 - 230), S(92)), mask=WSO2_MARK)
        name_c =mix(BG, (236, 240, 244), ease_out(t * 3) * fade)
        d.text((S(70), S(64)), "Nipuna Ranasinghe", font=F_NAME, fill=name_c)
        rule_w = 300 * ease_out(t * 2.2 - 0.3)
        if rule_w > 0:
            d.line([S(72), S(136), S(72 + rule_w), S(136)], fill=mix(BG, TEAL, fade), width=S(2))
        tag = "Integration platforms & developer tooling."
        d.text((S(72), S(152)), tag, font=F_TAG, fill=mix(BG, DIM, ease_out(t * 2.5 - 0.6) * fade))
        for i, (k, v) in enumerate(rows):
            a = ease_out(t * 3 - 1.2 - i * 0.25) * fade
            y = 206 + i * 26
            d.text((S(72), S(y)), k, font=F_MONO, fill=mix(BG, DIM, a))
            d.text((S(190), S(y)), v, font=F_MONO, fill=mix(BG, AMBER if k == "experience" else TEXT, a))
        footer(d, "identity", fade)
        return img

    N = 36
    for i in range(N):
        push(card(i / (N - 1)), MOTION_MS)
    push(card(1.0), 3600)  # hold long enough to read the card
    for i in range(12):
        push(card(1.0, fade=1 - (i + 1) / 12), MOTION_MS)

    if ENABLE_INTEGRATION_SCENE:
        # Integration flow (disabled by default). `bal run`, then the service's flow with messages moving through it.
        nodes = {  # name: (x, y, title, subtitle), boxes are 150 x 46 layout px
            "in": (40, 190, "http:Listener", "POST /orders"),
            "val": (240, 190, "validate", "json → Order"),
            "map": (440, 190, "transform", "Order → Event"),
            "kafka": (680, 140, "kafka:Producer", "orders.events"),
            "db": (680, 240, "mysql:Client", "INSERT orders"),
        }
        BW, BH = 150, 46
        order = ["in", "val", "map", "kafka", "db"]

        def edge_path(a, b):
            ax, ay = nodes[a][0] + BW, nodes[a][1] + BH / 2
            bx, by = nodes[b][0], nodes[b][1] + BH / 2
            if ay == by:
                return [(ax, ay), (bx, by)]
            mx = (ax + bx) / 2
            return [(ax, ay), (mx, ay), (mx, by), (bx, by)]

        edges = [("in", "val"), ("val", "map"), ("map", "kafka"), ("map", "db")]
        routes = [edge_path("in", "val") + edge_path("val", "map")[1:] + edge_path("map", t)[1:] for t in ("kafka", "db")]

        def point_on(path, s):
            """Point at fraction `s` of the polyline's length."""
            segs = [((x0, y0), (x1, y1), abs(x1 - x0) + abs(y1 - y0)) for (x0, y0), (x1, y1) in zip(path, path[1:])]
            dist = s * sum(L for *_, L in segs)
            for p0, p1, L in segs:
                if dist <= L:
                    k = dist / L if L else 0
                    return p0[0] + (p1[0] - p0[0]) * k, p0[1] + (p1[1] - p0[1]) * k
                dist -= L
            return path[-1]

        def draw_polyline(d, path, s, colour):
            """Draw the first `s` fraction of `path`."""
            pts = [path[0]] + [point_on(path, s * k / 24) for k in range(1, 25)]
            d.line([(S(x), S(y)) for x, y in pts], fill=colour, width=S(1), joint="curve")

        packets = []  # [route index, progress 0..1]
        stats = {"req": 1180}

        def flow(cmd, out_a, node_t, edge_t, packets_on, caption_a, fade=1.0):
            img, d = frame_base(fade=fade)
            rain.step(); rain.draw(d, 0.45 * fade)  # quieter: the diagram shares the right side
            prompt(d, X, Y0, cmd, cursor=out_a == 0 and fade == 1.0, fade=fade)
            if out_a > 0:
                d.text((S(X + 18), S(Y0 + 24)), "Running executable · listening on :9090", font=F_MONO,
                       fill=mix(BG, DIM, out_a * fade))
            for i, (a, b) in enumerate(edges):
                s = ease_out(edge_t * 2.5 - i * 0.35)
                if s > 0:
                    draw_polyline(d, edge_path(a, b), s, mix(BG, FAINT if not packets_on else (60, 90, 92), fade))
            for r, s in (packets if packets_on else []):
                x, y = point_on(routes[r], s)
                d.ellipse([S(x - 6), S(y - 6), S(x + 6), S(y + 6)], fill=mix(BG, TEAL, 0.18 * fade))
                d.ellipse([S(x - 2.5), S(y - 2.5), S(x + 2.5), S(y + 2.5)], fill=mix(BG, TEAL, fade))
            for i, n in enumerate(order):
                a = ease_out(node_t * 3 - i * 0.45) * fade
                if a <= 0:
                    continue
                x, y, title, sub = nodes[n]
                d.rounded_rectangle([S(x), S(y), S(x + BW), S(y + BH)], radius=S(6), fill=mix(BG, (22, 27, 34), a),
                                    outline=mix(BG, (60, 68, 77), a), width=S(1))
                d.text((S(x + 12), S(y + 8)), title, font=F_MONO, fill=mix(BG, TEXT, a))
                d.text((S(x + 12), S(y + 28)), sub, font=F_XS, fill=mix(BG, DIM, a))
            if packets_on:
                line = f"requests {stats['req']:,}  ·  avg latency 8 ms"
                d.text((S(X + 18), S(318)), line, font=F_MONO, fill=mix(BG, AMBER, fade))
            if caption_a > 0:
                d.text((S(X + 18), S(346)), "integrations as code.", font=F_MONO, fill=mix(BG, DIM, caption_a * fade))
            footer(d, "integration", fade)
            return img

        run = "bal run order_sync.bal"
        push(flow("", 0, 0, 0, False, 0), 600)  # empty prompt before typing
        for k in range(1, len(run) + 1):
            push(flow(run[:k], 0, 0, 0, False, 0), TYPE_MS + RNG.randint(0, 40))
        push(flow(run, 0, 0, 0, False, 0), 300)
        for i in range(6):
            push(flow(run, (i + 1) / 6, 0, 0, False, 0), MOTION_MS)
        for i in range(24):  # nodes and edges build left to right
            push(flow(run, 1, i / 23, i / 23, False, 0), MOTION_MS)
        for i in range(70):  # messages flow
            if i % 5 == 0:
                packets.append([i // 5 % 2, 0.0])
            for p in packets:
                p[1] += 0.03
            done = [p for p in packets if p[1] >= 1]
            stats["req"] += len(done) * 7
            packets[:] = [p for p in packets if p[1] < 1]
            push(flow(run, 1, 1, 1, True, min(1, max(0, (i - 30) / 12))), MOTION_MS)
        push(flow(run, 1, 1, 1, True, 1), 1600)
        for i in range(12):
            push(flow(run, 1, 1, 1, True, 1, fade=1 - (i + 1) / 12), MOTION_MS)

    # Scene 3: interests. `cat ~/interests` draws a radar chart; the teal shape grows out along each axis.
    RX, RY, RR = 440, 236, 100
    interests = [  # (label, detail, value 0..1), clockwise from the top; neighbours are related areas
        ("AI agents", "agentic systems · copilots", 0.95),
        ("Integration", "WSO2 Integrator", 0.85),
        ("Open-source community", "lsp4intellij · Ballerina", 0.7),
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
        shape = [axis_pt(k, RR * v * ease_out(grow) * breathe) for k, (_, _, v) in enumerate(interests)]
        if grow > 0:
            fill = Image.new("L", img.size, 0)
            ImageDraw.Draw(fill).polygon([(S(x), S(y)) for x, y in shape], fill=round(255 * 0.2 * fade))
            img.paste(Image.new("RGB", img.size, TEAL), (0, 0), fill)
            glow = Image.new("L", img.size, 0)
            g = ImageDraw.Draw(glow)
            g.line([(S(x), S(y)) for x, y in shape + shape[:1]], fill=round(200 * fade), width=S(3))
            for x, y in shape:
                g.ellipse([S(x - 9), S(y - 9), S(x + 9), S(y + 9)], fill=round(255 * ease_out(grow) * fade))
            img.paste(Image.new("RGB", img.size, TEAL), (0, 0), glow.filter(ImageFilter.GaussianBlur(S(8))))
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
    for k in range(1, len(cat) + 1):
        push(radar(cat[:k], 0, 0, 0), TYPE_MS + RNG.randint(0, 40))
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
    for i in range(12):
        tt += 1
        push(radar(cat, 1, 1, tt, out_a=1, fade=1 - (i + 1) / 12), MOTION_MS)

    # Scene 4: projects, as a living web. Faint background dots drift and link to their neighbours;
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
            d.text((S(X + 18), S(Y0 + 24)), "6 projects · 2 maintained", font=F_MONO, fill=mix(BG, DIM, out_a * fade))
        nodes_now = [node_pos(i, tt) for i in range(6)]
        node_a = [ease_out(l * 2 - 1) for l in lit]
        if web_a > 0:  # background web
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
        wide = glow.filter(ImageFilter.GaussianBlur(S(22))).point(lambda v: min(255, v * 1.6))
        tight = glow.filter(ImageFilter.GaussianBlur(S(7)))
        img.paste(Image.new("RGB", img.size, mix(BG, TEAL, 0.7)), (0, 0), wide)
        img.paste(Image.new("RGB", img.size, TEAL), (0, 0), tight)
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
    for k in range(1, len(ls) + 1):
        push(web(ls[:k], 0, [0] * 6, tt, 0), TYPE_MS + RNG.randint(0, 40))
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
    for i in range(70):  # everything lit: the web drifts and signals travel the links
        tt += 1
        if i % 4 == 0:
            signals.append([sig_rng.choice(all_edges), 0.0, sig_rng.random() < 0.6])
        for sg in signals:
            sg[1] += 0.06
        signals = [sg for sg in signals if sg[1] < 1]
        push(web(ls, 1, lit, tt, 1, signals, out_a=1), MOTION_MS)
    push(web(ls, 1, lit, tt, 1, signals, out_a=1), 1200)
    for i in range(12):
        tt += 1
        push(web(ls, 1, lit, tt, 1, signals, out_a=1, fade=1 - (i + 1) / 12), MOTION_MS)
    img, _ = frame_base(open_t=0.0)
    push(img, 400)
    return frames, delays


def save(frames, delays):
    # Animated WebP: full colour (no GIF palette banding on the glow) at under half the GIF's size.
    frames[0].save(OUT, format="WEBP", save_all=True, append_images=frames[1:], duration=delays, loop=0,
                   quality=70, method=4)
    print(f"{OUT}: {len(frames)} frames, {sum(delays) / 1000:.1f}s, {os.path.getsize(OUT) / 1e6:.2f} MB")


if __name__ == "__main__":
    save(*render())
