"""Generate the Leshan's Omniverse logo as an SVG.

Concept: a Maasai beadwork ring + crossed warrior spears forming a shield that
opens onto a galaxy — heritage on the outside, an infinite universe within.
"""
import math, random

W = 512
cx = cy = W / 2
random.seed(11)

# Maasai-cosmic palette
RED, GOLD, WHITE, GREEN, BLUE, BLACK = "#c4161c", "#e0a73c", "#f7f2ea", "#1f9d57", "#1f6fd6", "#120c0a"
BEADS = [RED, GOLD, WHITE, GREEN, BLUE, BLACK]

r_disc = 150      # starry portal disc
r_bead = 176      # bead ring centre
bead_r = 13
n_beads = 42

def spear(angle_deg):
    """A slim gold warrior spear, centred and rotated."""
    return f'''<g transform="rotate({angle_deg} {cx} {cy})">
      <rect x="{cx-3}" y="{cy-210}" width="6" height="420" rx="3" fill="url(#brass)"/>
      <path d="M {cx} {cy-238} L {cx-13} {cy-196} L {cx} {cy-206} L {cx+13} {cy-196} Z" fill="url(#brass)"/>
      <path d="M {cx} {cy+232} L {cx-8} {cy+204} L {cx+8} {cy+204} Z" fill="url(#brass)"/>
    </g>'''

# stars inside the disc
stars = []
for _ in range(70):
    a = random.random() * 2 * math.pi
    rr = (random.random() ** 0.5) * (r_disc - 10)
    x, y = cx + rr * math.cos(a), cy + rr * math.sin(a)
    rad = random.random() * 1.6 + 0.4
    op = random.random() * 0.7 + 0.3
    col = WHITE if random.random() > 0.25 else GOLD
    stars.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rad:.1f}" fill="{col}" opacity="{op:.2f}"/>')
# a bright north star
stars.append(f'<circle cx="{cx}" cy="{cy-70}" r="3.2" fill="{WHITE}"/>')
stars.append(f'<circle cx="{cx}" cy="{cy-70}" r="8" fill="{WHITE}" opacity="0.25"/>')

# beadwork ring
beads = []
for i in range(n_beads):
    a = (i / n_beads) * 2 * math.pi - math.pi / 2
    x, y = cx + r_bead * math.cos(a), cy + r_bead * math.sin(a)
    col = BEADS[i % len(BEADS)]
    beads.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{bead_r}" fill="{col}" stroke="#0a0706" stroke-width="1.2"/>')
    beads.append(f'<circle cx="{x-3:.1f}" cy="{y-3:.1f}" r="{bead_r*0.34:.1f}" fill="#ffffff" opacity="0.35"/>')

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {W}" width="{W}" height="{W}">
  <defs>
    <radialGradient id="bg" cx="50%" cy="42%" r="65%">
      <stop offset="0%" stop-color="#241033"/>
      <stop offset="55%" stop-color="#120a1c"/>
      <stop offset="100%" stop-color="#0a0706"/>
    </radialGradient>
    <radialGradient id="portal" cx="50%" cy="50%" r="55%">
      <stop offset="0%" stop-color="#3a1a4d"/>
      <stop offset="55%" stop-color="#160a20"/>
      <stop offset="100%" stop-color="#0b0710"/>
    </radialGradient>
    <linearGradient id="brass" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#f6c96a"/>
      <stop offset="50%" stop-color="#c98b25"/>
      <stop offset="100%" stop-color="#8a5d12"/>
    </linearGradient>
    <radialGradient id="glow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#8b5cf6" stop-opacity="0.55"/>
      <stop offset="100%" stop-color="#8b5cf6" stop-opacity="0"/>
    </radialGradient>
  </defs>

  <circle cx="{cx}" cy="{cy}" r="{W/2}" fill="url(#bg)"/>

  {spear(-30)}
  {spear(30)}

  <!-- portal -->
  <circle cx="{cx}" cy="{cy}" r="{r_disc+8}" fill="#0a0706"/>
  <circle cx="{cx}" cy="{cy}" r="{r_disc}" fill="url(#portal)"/>
  <circle cx="{cx}" cy="{cy}" r="{r_disc*0.9}" fill="url(#glow)"/>
  {''.join(stars)}

  <!-- thin brass rims -->
  <circle cx="{cx}" cy="{cy}" r="{r_disc+8}" fill="none" stroke="url(#brass)" stroke-width="2.5"/>
  <circle cx="{cx}" cy="{cy}" r="{r_bead+bead_r+4}" fill="none" stroke="url(#brass)" stroke-width="3"/>

  <!-- Maasai beadwork ring -->
  {''.join(beads)}
</svg>'''

with open("/tmp/claude-0/-home-user-youtue/6378df18-80c5-5648-ac2f-428e3f059862/scratchpad/logo.svg", "w") as f:
    f.write(svg)
print("logo.svg written", len(svg), "bytes")
