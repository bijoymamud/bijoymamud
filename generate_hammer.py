#!/usr/bin/env python3
"""
Hammer contribution animation v1.
- Pixel-art character moves to each active commit box and hits it with a hammer
- First half of year: statically shown
- Second half: starts dark; hammer impacts the LAST 20 committed squares into view,
  one per strike, then loops
"""

import os, json
import urllib.request
import urllib.parse
import urllib.error


# ── Layout ────────────────────────────────────────────────────────────────────
CELL        = 11          # contribution square size
GAP         = 2           # gap between squares
STEP        = CELL + GAP
GRID_X      = 104         # left edge of grid (space for character)
GRID_Y      = 28          # top edge (space for month labels)
ROWS        = 7
HALF        = 26          # weeks 0-25 = first half (shown), 26+ = second half
MAX_HITS    = 20          # animate only the last N committed squares in second half

# ── Timing ────────────────────────────────────────────────────────────────────
START_PAUSE  = 1.5        # pause before first hammer strike (s)
HIT_TOTAL    = 1.4        # total time per hammer strike cycle (s)
FLIGHT_FRAC  = 0.60       # point in the cycle when hammer hits
END_PAUSE    = 1.5        # hold at end before loop restarts

# ── Colors ────────────────────────────────────────────────────────────────────
SKIN    = "#c68642"
JERSEY  = "#1565c0"
JSTRIPE = "#58a6ff"
JNUM    = "#ffffff"
PANTS   = "#d0d7de"
BOOT    = "#21262d"
LCOLORS = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]


def lv(c):
    return 0 if c == 0 else 1 if c <= 2 else 2 if c <= 5 else 3 if c <= 10 else 4

def cell_center(wi, di):
    return GRID_X + wi * STEP + CELL / 2, GRID_Y + di * STEP + CELL / 2

# ── GitHub API / Fallback Data ────────────────────────────────────────────────
def get_data(username, token):
    if token and username:
        try:
            q = ("query($l:String!){user(login:$l){contributionsCollection{"
                 "contributionCalendar{totalContributions "
                 "weeks{contributionDays{contributionCount date}}}}}}")
            req_data = json.dumps({"query": q, "variables": {"login": username}}).encode("utf-8")
            req = urllib.request.Request(
                "https://api.github.com/graphql",
                data=req_data,
                headers={"Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "Python"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
                return cal["weeks"], cal["totalContributions"]
        except Exception as e:
            print(f"GraphQL API failed ({e}), trying public fallback...")

    # Public API fallback for local testing without token
    user = urllib.parse.quote(username or "bijoymamud")
    try:
        req = urllib.request.Request(
            f"https://github-contributions-api.jogruber.de/v4/{user}?y=last",
            headers={"User-Agent": "Python"}
        )

        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            total = data.get("total", {}).get("lastYear", 365)
            raw_contribs = data.get("contributions", [])
            
            # Group by weeks (7 days per week)
            weeks = []
            current_week = []
            for d in raw_contribs:
                current_week.append({
                    "contributionCount": d["count"],
                    "date": d["date"]
                })
                if len(current_week) == 7:
                    weeks.append({"contributionDays": current_week})
                    current_week = []
            if current_week:
                weeks.append({"contributionDays": current_week})
            return weeks, total
    except Exception as e:
        print(f"Public API failed ({e}), generating synthetic mock data for preview...")
        import random
        random.seed(42)
        weeks = []
        total = 0
        for w in range(52):
            days = []
            for d in range(7):
                cnt = random.choice([0, 0, 0, 1, 3, 5, 8, 12]) if w > 20 else random.choice([0, 0, 1, 2])
                total += cnt
                days.append({"contributionCount": cnt, "date": f"2026-01-{d+1:02d}"})
            weeks.append({"contributionDays": days})
        return weeks, total



# ── Pixel character ───────────────────────────────────────────────────────────
def char_svg():
    """
    Pixel-art character facing the contribution grid.
    Returns (svg_string, hammer_contact_x, hammer_contact_y).
    Coordinates are local to the animated character group.
    """
    B = 2  # pixels per block

    hx, hy    = 8, 0
    bx, by    = 8, 8*B
    llx, lly  = bx, by + 12*B            # left leg top-left
    rlx, rly  = bx + 4*B, by + 12*B     # right leg top-left (pivot top-left)

    boot_h    = 3*B                       # shoe height
    leg_h     = 12*B                      # leg height

    shoulder_x = bx + 8*B
    shoulder_y = by + 5*B

    # At contact, #hammer_arm is at 0deg and the hammer face reaches this point.
    hammer_contact_x = shoulder_x + 42
    hammer_contact_y = shoulder_y + 1

    s = f"""
  <!-- Moving pixel character -->
  <g id="character">
    <animateTransform id="move_anim_placeholder"/>

    <!-- Legs stay planted while the arm swings the hammer -->
    <rect x="{llx}"      y="{lly}"     width="{4*B}" height="{leg_h}" fill="{PANTS}"/>
    <rect x="{llx-B}"    y="{lly+leg_h}" width="{5*B}" height="{boot_h}" fill="{BOOT}"/>
    <rect x="{rlx}"      y="{rly}"     width="{4*B}" height="{leg_h}" fill="{PANTS}"/>
    <rect x="{rlx}"      y="{rly+leg_h}" width="{5*B}" height="{boot_h}" fill="{BOOT}"/>

    <!-- Body -->
    <rect x="{bx}"       y="{by}"      width="{8*B}" height="{12*B}" fill="{JERSEY}"/>
    <rect x="{bx+3*B}"   y="{by}"      width="{2*B}" height="{B}"    fill="{JSTRIPE}"/>
    <rect x="{bx}"       y="{by+5*B}"  width="{8*B}" height="{2*B}"  fill="{JSTRIPE}" opacity="0.55"/>

    <!-- Free arm for balance -->
    <g transform="translate({bx-3*B},{by}) rotate(18,{3*B//2},0)">
      <rect x="0" y="0" width="{3*B}" height="{10*B}" fill="{JERSEY}"/>
      <rect x="0" y="{9*B}" width="{3*B}" height="{2*B}" fill="{SKIN}"/>
    </g>

    <!-- Hammer arm: body stays upright, only hand and hammer strike -->
    <g transform="translate({shoulder_x},{shoulder_y})">
      <g id="hammer_arm">
        <animateTransform id="hammer_anim_placeholder"/>
        <rect x="0" y="-2" width="13" height="4" fill="{JERSEY}"/>
        <rect x="11" y="-2" width="5" height="4" fill="{SKIN}"/>
        <rect x="16" y="-1.3" width="23" height="2.6" rx="1" fill="#8b5e34"/>
        <rect x="34" y="-7" width="11" height="14" rx="1" fill="#8b949e" stroke="#f0f6fc" stroke-width="0.55"/>
        <rect x="36" y="-5" width="7" height="10" fill="#6e7681"/>
      </g>
    </g>

    <!-- Head -->
    <rect x="{hx}"       y="{hy}"      width="{8*B}" height="{8*B}" fill="{SKIN}"/>
    <rect x="{hx}"       y="{hy}"      width="{8*B}" height="{2*B}" fill="#3d1f08"/>
    <rect x="{hx+6*B}"   y="{hy+2*B}"  width="{2*B}" height="{B}"   fill="#3d1f08"/>
    <rect x="{hx+B}"     y="{hy+2*B}"  width="{3*B}" height="{2*B}" fill="none" stroke="#aaa" stroke-width="0.6"/>
    <rect x="{hx+4*B}"   y="{hy+2*B}"  width="{3*B}" height="{2*B}" fill="none" stroke="#aaa" stroke-width="0.6"/>
    <rect x="{hx+2*B}"   y="{hy+3*B}"  width="{B}" height="{B}" fill="#1a1a1a"/>
    <rect x="{hx+5*B}"   y="{hy+3*B}"  width="{B}" height="{B}" fill="#1a1a1a"/>
    <rect x="{hx+3*B}"   y="{hy+6*B}"  width="{2*B}" height="{B}" fill="#7a3b2a"/>
  </g>"""

    return s, hammer_contact_x, hammer_contact_y

def character_move_animation(positions, tdur):
    vals, kts = [], []

    def add(t, pos):
        vals.append(f"{pos[0]:.1f} {pos[1]:.1f}")
        kts.append(f"{t/tdur:.4f}")

    if not positions:
        add(0.0, (0, 0))
        add(tdur, (0, 0))
    else:
        add(0.0, positions[0])
        for i, pos in enumerate(positions):
            prev = positions[i - 1] if i else positions[0]
            t0 = START_PAUSE + i * HIT_TOTAL
            t_arrive = t0 + HIT_TOTAL * 0.22
            t_hold = t0 + HIT_TOTAL * 0.82
            add(t0, prev)
            add(t_arrive, pos)
            add(t_hold, pos)
        add(tdur, positions[-1])

    return (f'<animateTransform attributeName="transform" type="translate" '
            f'values="{"; ".join(vals)}" '
            f'keyTimes="{"; ".join(kts)}" '
            f'calcMode="linear" dur="{tdur:.2f}s" repeatCount="indefinite"/>')

def hammer_animation(N, tdur):
    vals, kts = [], []

    def add(t, deg):
        vals.append(f"{deg} 0 0")
        kts.append(f"{t/tdur:.4f}")

    add(0.0, -58)
    for i in range(N):
        t0 = START_PAUSE + i * HIT_TOTAL
        add(t0 + HIT_TOTAL * 0.22, -58)
        add(t0 + HIT_TOTAL * 0.40, -74)
        add(t0 + HIT_TOTAL * 0.60, 0)
        add(t0 + HIT_TOTAL * 0.66, 8)
        add(t0 + HIT_TOTAL * 0.82, -58)
        if i < N - 1:
            add(t0 + HIT_TOTAL * 0.96, -58)
    add(tdur, -58)

    return (f'<animateTransform attributeName="transform" type="rotate" '
            f'values="{"; ".join(vals)}" '
            f'keyTimes="{"; ".join(kts)}" '
            f'calcMode="spline" '
            f'keySplines="{"; ".join(["0.4 0 0.6 1"] * (len(kts) - 1))}" '
            f'dur="{tdur:.2f}s" repeatCount="indefinite" additive="replace"/>')

def impact_flash_svg(i, tx, ty, p_hit, tdur):
    """Small comic impact marks at the target square."""
    eps = 0.003
    p_off = min(1.0, p_hit + 0.045)
    return f"""
  <!-- Impact flash {i} -->
  <g opacity="0">
    <line x1="{tx-8:.1f}" y1="{ty:.1f}" x2="{tx-3:.1f}" y2="{ty:.1f}" stroke="#f0f6fc" stroke-width="1.1"/>
    <line x1="{tx+3:.1f}" y1="{ty:.1f}" x2="{tx+8:.1f}" y2="{ty:.1f}" stroke="#f0f6fc" stroke-width="1.1"/>
    <line x1="{tx:.1f}" y1="{ty-8:.1f}" x2="{tx:.1f}" y2="{ty-3:.1f}" stroke="#f0f6fc" stroke-width="1.1"/>
    <line x1="{tx:.1f}" y1="{ty+3:.1f}" x2="{tx:.1f}" y2="{ty+8:.1f}" stroke="#f0f6fc" stroke-width="1.1"/>
    <animate attributeName="opacity" values="0;0;1;0;0"
             keyTimes="0;{max(0, p_hit - eps):.4f};{p_hit:.4f};{p_off:.4f};1"
             calcMode="discrete" dur="{tdur:.2f}s" repeatCount="indefinite"/>
  </g>"""

# ── Main SVG generation ───────────────────────────────────────────────────────
def generate(weeks, total, outfile):
    nw    = len(weeks)
    svg_w = GRID_X + nw * STEP + 12
    svg_h = GRID_Y + ROWS * STEP + 20

    # ── Character template ────────────────────────────────────────────────────
    char, hammer_contact_x, hammer_contact_y = char_svg()

    # ── Collect second-half commits, pick last MAX_HITS ──────────────────────
    all_second = []
    for wi in range(HALF, len(weeks)):
        for di, day in enumerate(weeks[wi]["contributionDays"]):
            if day["contributionCount"] > 0:
                cx2, cy2 = cell_center(wi, di)
                all_second.append((wi, di, cx2, cy2, day["contributionCount"]))

    animated = all_second[-MAX_HITS:]   # last N committed squares
    animated_keys = {(wi, di) for wi, di, *_ in animated}

    N     = len(animated)
    tdur  = START_PAUSE + N * HIT_TOTAL + END_PAUSE   # total loop duration
    positions = [(tx - hammer_contact_x, ty - hammer_contact_y) for _, _, tx, ty, _ in animated]
    move_anim = character_move_animation(positions, tdur)
    hammer_anim = hammer_animation(N, tdur)
    char = (
        char
        .replace('<animateTransform id="move_anim_placeholder"/>', move_anim)
        .replace('<animateTransform id="hammer_anim_placeholder"/>', hammer_anim)
    )

    # ── Grid cells ─────────────────────────────────────────────────────────────
    # Build index for animated squares
    anim_idx = {(wi, di): i for i, (wi, di, *_) in enumerate(animated)}

    cell_parts = []
    for wi, week in enumerate(weeks):
        for di, day in enumerate(week["contributionDays"]):
            x   = GRID_X + wi * STEP
            y   = GRID_Y + di * STEP
            cnt = day["contributionCount"]
            color = LCOLORS[lv(cnt)]

            if wi < HALF:
                # First half: static
                cell_parts.append(
                    f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                    f'rx="2" fill="{color}"/>'
                )
            elif (wi, di) not in animated_keys:
                # Second half, not animated: static (already committed or empty)
                cell_parts.append(
                    f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                    f'rx="2" fill="{color}"/>'
                )
            else:
                # Second half, ANIMATED: starts dark -> lights up on head impact
                idx      = anim_idx[(wi, di)]
                t_hit    = START_PAUSE + idx * HIT_TOTAL + HIT_TOTAL * FLIGHT_FRAC
                p_reveal = t_hit / tdur
                p_reset  = (tdur - 0.4) / tdur   # go dark just before loop restarts
                eps      = 0.003
                cell_parts.append(
                    f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                    f'rx="2" fill="{LCOLORS[0]}">'
                    f'<animate attributeName="fill" '
                    f'values="{LCOLORS[0]};{LCOLORS[0]};{color};{color};{LCOLORS[0]}" '
                    f'keyTimes="0;{p_reveal - eps:.4f};{p_reveal:.4f};{p_reset:.4f};1" '
                    f'calcMode="discrete" '
                    f'dur="{tdur:.2f}s" repeatCount="indefinite"/>'
                    f'</rect>'
                )

    cells = "\n  ".join(cell_parts)

    # ── Impact flashes ─────────────────────────────────────────────────────────
    flash_parts = []
    for i, (wi, di, tx, ty, _) in enumerate(animated):
        t_hit    = START_PAUSE + i * HIT_TOTAL + HIT_TOTAL * FLIGHT_FRAC
        flash_parts.append(impact_flash_svg(i, tx, ty, t_hit / tdur, tdur))

    flashes = "\n".join(flash_parts)

    # ── Month labels ────────────────────────────────────────────────────────────
    MONTHS = ["Jan","Feb","Mar","Apr","May","Jun",
              "Jul","Aug","Sep","Oct","Nov","Dec"]
    month_parts, pm = [], None
    for wi, week in enumerate(weeks):
        if week["contributionDays"]:
            m = int(week["contributionDays"][0]["date"].split("-")[1]) - 1
            if m != pm:
                x = GRID_X + wi * STEP
                month_parts.append(
                    f'<text x="{x}" y="{GRID_Y - 7}" fill="#2a2a2a" '
                    f'font-size="7" font-family="monospace">{MONTHS[m]}</text>'
                )
                pm = m

    months = "\n  ".join(month_parts)

    # ── Assemble SVG ───────────────────────────────────────────────────────────
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
  width="{svg_w}" height="{svg_h}" viewBox="0 0 {svg_w} {svg_h}">

  <!-- Background -->
  <rect width="{svg_w}" height="{svg_h}" fill="#0d1117"/>

  <!-- Month labels -->
  {months}

  <!-- Contribution grid -->
  {cells}

  <!-- Character moves in front of each target and hits it with a hammer -->
  {char}

  <!-- Hit flashes -->
  {flashes}

  <!-- Footer -->
  <text x="{svg_w // 2}" y="{svg_h - 4}" text-anchor="middle"
    fill="#1e1e1e" font-size="8" font-family="monospace" letter-spacing="1">
    {total} contributions this year
  </text>

</svg>"""

    with open(outfile, "w", encoding="utf-8") as f:
        f.write(svg)

    print(f"[+] {outfile} generated - {len(all_second)} second-half commits, "
          f"animating last {N}, loop={tdur:.1f}s")


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    token    = os.environ.get("GITHUB_TOKEN", "")
    username = os.environ.get("USERNAME") or os.environ.get("GITHUB_REPOSITORY_OWNER") or "bijoymamud"

    if not token:
        print("Note: GITHUB_TOKEN not set. Running with fallback API / mock preview mode...")
    print(f"Fetching contributions for @{username}…")
    weeks, total = get_data(username, token)
    generate(weeks, total, "hammer_animation.svg")


if __name__ == "__main__":
    main()
