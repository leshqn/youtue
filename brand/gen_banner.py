"""Generate the Leshan's Omniverse YouTube channel banner.

Canvas is YouTube's required 2560x1440. Everything essential sits inside the
1546x423 "safe area" (centred), which is all that shows on phones.
"""
import math, random, pathlib

W, H = 2560, 1440
CX, CY = W / 2, H / 2
SAFE_W, SAFE_H = 1546, 423
random.seed(7)

RED, GOLD, WHITE, GREEN, BLUE, BLACK = "#c4161c", "#e0a73c", "#f7f2ea", "#1f9d57", "#1f6fd6", "#120c0a"
BEADS = [RED, GOLD, WHITE, GREEN, BLUE, BLACK]

# ---- starfield across the whole canvas ------------------------------------
stars = []
for _ in range(420):
    x, y = random.random() * W, random.random() * H
    # denser near the middle band
    r = random.random() * 2.0 + 0.3
    op = random.random() * 0.75 + 0.15
    col = WHITE if random.random() > 0.28 else GOLD
    stars.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.1f}" fill="{col}" opacity="{op:.2f}"/>')

# ---- beadwork strips (top & bottom accents) --------------------------------
def bead_strip(y, bead_r=11, gap=30):
    out = []
    i = 0
    x = -gap
    while x < W + gap:
        col = BEADS[i % len(BEADS)]
        out.append(f'<circle cx="{x:.0f}" cy="{y}" r="{bead_r}" fill="{col}" opacity="0.92"/>')
        x += gap
        i += 1
    return "".join(out)

# ---- the portal (left of the wordmark, inside safe area) -------------------
p_cx, p_cy, p_r = CX - 560, CY, 132
portal_stars = []
for _ in range(46):
    a = random.random() * 2 * math.pi
    rr = (random.random() ** 0.5) * (p_r - 14)
    portal_stars.append(
        f'<circle cx="{p_cx + rr*math.cos(a):.1f}" cy="{p_cy + rr*math.sin(a):.1f}" '
        f'r="{random.random()*1.6+0.4:.1f}" fill="{WHITE}" opacity="{random.random()*0.7+0.3:.2f}"/>'
    )
beads = []
n = 34
br = p_r + 30
for i in range(n):
    a = (i / n) * 2 * math.pi - math.pi / 2
    beads.append(
        f'<circle cx="{p_cx + br*math.cos(a):.1f}" cy="{p_cy + br*math.sin(a):.1f}" '
        f'r="11" fill="{BEADS[i % len(BEADS)]}" stroke="#0a0706" stroke-width="1"/>'
    )

def spear(angle):
    return f'''<g transform="rotate({angle} {p_cx} {p_cy})">
      <rect x="{p_cx-3.5}" y="{p_cy-208}" width="7" height="416" rx="3.5" fill="url(#brass)"/>
      <path d="M {p_cx} {p_cy-232} L {p_cx-13} {p_cy-192} L {p_cx} {p_cy-202} L {p_cx+13} {p_cy-192} Z" fill="url(#brass)"/>
      <path d="M {p_cx} {p_cy+228} L {p_cx-8} {p_cy+200} L {p_cx+8} {p_cy+200} Z" fill="url(#brass)"/>
    </g>'''

TX = p_cx + 235  # text starts right of the portal

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="0.35" y2="1">
      <stop offset="0%" stop-color="#1a0a26"/>
      <stop offset="45%" stop-color="#12081a"/>
      <stop offset="100%" stop-color="#0a0605"/>
    </linearGradient>
    <radialGradient id="dawn" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#c4161c" stop-opacity="0.40"/>
      <stop offset="55%" stop-color="#8b5cf6" stop-opacity="0.16"/>
      <stop offset="100%" stop-color="#8b5cf6" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="portalfill" cx="50%" cy="50%" r="55%">
      <stop offset="0%" stop-color="#43205c"/>
      <stop offset="60%" stop-color="#1a0d26"/>
      <stop offset="100%" stop-color="#0b0710"/>
    </radialGradient>
    <linearGradient id="brass" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#f6c96a"/><stop offset="50%" stop-color="#c98b25"/>
      <stop offset="100%" stop-color="#8a5d12"/>
    </linearGradient>
    <linearGradient id="word" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#ffffff"/><stop offset="60%" stop-color="#ffe6b0"/>
      <stop offset="100%" stop-color="#e0a73c"/>
    </linearGradient>
  </defs>

  <rect width="{W}" height="{H}" fill="url(#sky)"/>
  {''.join(stars)}
  <ellipse cx="{CX}" cy="{CY}" rx="1150" ry="560" fill="url(#dawn)"/>

  <!-- horizon glow: savanna meets sky -->
  <ellipse cx="{CX}" cy="{H*0.94}" rx="1500" ry="230" fill="#c4161c" opacity="0.10"/>

  {bead_strip(52)}
  {bead_strip(H-52)}

  <!-- portal emblem -->
  {spear(-30)}
  {spear(30)}
  <circle cx="{p_cx}" cy="{p_cy}" r="{p_r+9}" fill="#0a0706"/>
  <circle cx="{p_cx}" cy="{p_cy}" r="{p_r}" fill="url(#portalfill)"/>
  {''.join(portal_stars)}
  <circle cx="{p_cx}" cy="{p_cy-52}" r="4" fill="{WHITE}"/>
  <circle cx="{p_cx}" cy="{p_cy-52}" r="11" fill="{WHITE}" opacity="0.22"/>
  <circle cx="{p_cx}" cy="{p_cy}" r="{p_r+9}" fill="none" stroke="url(#brass)" stroke-width="3"/>
  <circle cx="{p_cx}" cy="{p_cy}" r="{br+11+4}" fill="none" stroke="url(#brass)" stroke-width="3.5"/>
  {''.join(beads)}

  <!-- wordmark -->
  <text x="{TX}" y="{CY-42}" font-family="Verdana,DejaVu Sans,sans-serif" font-size="118"
        font-weight="bold" fill="url(#word)" letter-spacing="2">LESHAN'S</text>
  <text x="{TX}" y="{CY+78}" font-family="Verdana,DejaVu Sans,sans-serif" font-size="118"
        font-weight="bold" fill="url(#word)" letter-spacing="14">OMNIVERSE</text>
  <rect x="{TX}" y="{CY+108}" width="742" height="3" fill="url(#brass)" opacity="0.85"/>
  <text x="{TX}" y="{CY+166}" font-family="Verdana,DejaVu Sans,sans-serif" font-size="35"
        fill="#f0ddc4" opacity="0.95" letter-spacing="3">A doorway to wonder — we chase beauty in all its forms</text>
</svg>'''

out = pathlib.Path(__file__).parent / "banner.svg"
out.write_text(svg)
print("banner.svg written:", len(svg), "bytes")
print(f"safe area {SAFE_W}x{SAFE_H} centred at ({CX:.0f},{CY:.0f})")
