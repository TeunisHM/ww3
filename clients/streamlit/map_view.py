"""A small, offline strategic map. Deliberately schematic, not a boundary map."""

from html import escape
from ww3.core.catalog import COLORS, FACTIONS
from ww3.core.models import Game
from ww3.core.strategy import EPS

LAND = [
    [(-168,70),(-145,72),(-126,69),(-107,75),(-81,73),(-61,61),(-58,49),(-74,43),(-82,25),(-97,18),(-104,23),(-117,32),(-126,49),(-143,59),(-166,60)],
    [(-97,22),(-87,21),(-83,12),(-77,8),(-72,11),(-80,18),(-86,23)],
    [(-80,10),(-67,11),(-49,2),(-35,-6),(-40,-21),(-51,-29),(-59,-39),(-67,-55),(-76,-46),(-73,-29),(-81,-5)],
    [(-53,60),(-44,60),(-24,74),(-29,82),(-47,84),(-62,76)],
    [(-10,36),(-10,44),(-2,49),(5,54),(8,58),(20,70),(31,70),(29,59),(42,56),(45,45),(29,40),(23,35),(16,41),(8,44),(2,41)],
    [(-17,35),(1,37),(13,33),(32,31),(43,12),(51,12),(44,-3),(40,-16),(28,-34),(18,-35),(10,-18),(9,3),(-6,5),(-17,15)],
    [(29,41),(39,58),(54,68),(92,77),(119,73),(141,72),(179,66),(163,58),(142,46),(132,32),(120,25),(109,20),(104,3),(96,6),(90,22),(80,8),(69,25),(55,25),(50,14),(43,13),(34,30)],
    [(113,-11),(130,-11),(141,-15),(151,-25),(151,-36),(136,-39),(115,-34),(111,-23)],
    [(47,-13),(51,-15),(48,-25),(44,-25)],
    [(130,31),(136,34),(141,42),(145,44),(142,34),(136,30)],
    [(96,5),(105,-5),(115,-8),(123,-8),(111,0),(105,6)],
    [(166,-34),(178,-38),(173,-46),(168,-45)],
    [(-8,50),(-2,51),(0,59),(-5,59),(-8,54)],
]
MARKERS = {
    # Longitude, latitude, then the top-left corner of the information card.
    "Eastern Europe": (29, 48, 352, 142),
    "Pacific & South China Sea": (133, 17, 676, 270),
    "Arctic": (49, 77, 676, 44),
    "South America": (-60, -16, 28, 270),
}


def _bar(values, total, x, y, *, metric, height):
    """Two different denominators: troops present, or 100 influence points."""
    width = 264
    parts = [f'<g class="{metric}-bar"><rect x="{x}" y="{y}" width="{width}" height="{height}" rx="2" fill="#364859"/>']
    offset = 0.0
    for faction in FACTIONS:
        value = values[faction]
        fraction = value / total if total > EPS else 0
        if fraction <= EPS:
            continue
        segment = width * fraction
        detail = (f"{faction}: {value:.1f} power, {fraction:.1%} troop share" if metric == "troop" else
            f"{faction}: {value:.1f} influence out of 100")
        parts.append(f'<rect data-faction="{faction}" x="{x + offset:.3f}" y="{y}" width="{segment:.3f}" height="{height}" fill="{COLORS[faction]}"><title>{detail}</title></rect>')
        if metric == "troop" and segment >= 58:
            parts.append(f'<text x="{x + offset + segment / 2:.3f}" y="{y + 12}" text-anchor="middle" fill="#101b27" font-size="10" font-weight="700">{faction} {fraction:.0%}</text>')
        offset += segment
    if metric == "influence":
        remaining = max(0, 100 - sum(values.values()))
        parts.append(f'<title>{remaining:.1f} unclaimed influence out of 100</title>')
    elif total <= EPS:
        parts.append('<title>No forces present; all troop shares are zero</title>')
    parts.append('</g>')
    return "".join(parts)


def render_map(game: Game, selected: str | None = None, *, interactive=False) -> str:
    def point(lon, lat):
        return ((lon + 180) * 2.7 + 12, (88 - lat) * 2.45 + 12)

    role = "group" if interactive else "img"
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 480" role="{role}" aria-label="Strategic world map: current troop shares and territorial influence" font-family="sans-serif">',
        '<title>Current strategic world</title><desc>Each theater shows its resolved status, deployed troop shares, and established influence. Troop bars divide forces present; influence bars always total 100, including gray unclaimed territory. Draft orders do not change this map.</desc>',
        '<defs><pattern id="world-grid" width="81" height="49" patternUnits="userSpaceOnUse"><path d="M81 0H0V49" fill="none" stroke="#213240" stroke-width="0.7"/></pattern></defs>',
        '<rect width="1000" height="480" rx="14" fill="#101b27"/><rect x="12" y="12" width="976" height="406" fill="url(#world-grid)"/>',
        f'<text x="28" y="35" fill="#a8bdcd" font-size="13" font-weight="600" letter-spacing="1.5">CURRENT WORLD · {game.year}</text>',
        '<g aria-hidden="true">']
    for shape in LAND:
        points = " ".join(f"{x:.1f},{y:.1f}" for x, y in (point(*p) for p in shape))
        svg.append(f'<polygon points="{points}" fill="#233544" stroke="#3d5263" stroke-width="1.2"/>')
    svg.append('</g>')
    for index, (name, (lon, lat, card_x, card_y)) in enumerate(MARKERS.items()):
        x, y = point(lon, lat)
        front = game.fronts[name]
        deployed = {f: game.nations[f].deployments[name] for f in FACTIONS}
        total = sum(deployed.values())
        unclaimed = max(0, 100 - sum(front.influence.values()))
        is_selected = name == selected
        color = "#9ff1db" if is_selected else "#a8bdcd"
        status_color = "#f5b45c" if front.status == "Contested" else "#c3d3df"
        label = name.replace("Pacific & South China Sea", "Pacific / South China Sea")
        facts = "; ".join(f"{f}: {deployed[f]:.1f} power, {deployed[f] / total:.1%} troop share, {front.influence[f]:.1f}/100 influence" if total > EPS else
            f"{f}: 0 power, 0% troop share, {front.influence[f]:.1f}/100 influence" for f in FACTIONS)
        description = f"{name}. {front.status}. {facts}. {unclaimed:.1f}/100 influence unclaimed."
        attributes = (f' data-front="{escape(name)}" role="button" tabindex="0" aria-pressed="{str(is_selected).lower()}"' if interactive else ' role="group"')
        accessible_label = f"Select {name} theater" if interactive else description
        svg.append(f'<g{attributes} aria-label="{escape(accessible_label)}" aria-describedby="world-front-{index}-description"><title>{escape(description)}</title><desc id="world-front-{index}-description">{escape(description)}</desc>')
        anchor_x = min(max(x, card_x + 16), card_x + 272)
        anchor_y = card_y if y < card_y else min(y, card_y + 128)
        svg.extend([
            f'<path d="M{x} {y}L{anchor_x} {anchor_y}" fill="none" stroke="{color}" stroke-width="1.5" opacity=".8"/>',
            f'<circle cx="{x}" cy="{y}" r="12" fill="#101b27" stroke="{color}" stroke-width="{"3" if is_selected else "1.5"}"/>',
            f'<circle cx="{x}" cy="{y}" r="4" fill="{color}"/>',
            f'<rect class="target" x="{card_x}" y="{card_y}" width="288" height="128" rx="8" fill="#142431" stroke="{color if is_selected else "#415a6c"}" stroke-width="{"2.5" if is_selected else "1"}"/>',
            f'<text x="{card_x + 12}" y="{card_y + 23}" fill="#eff5fa" font-size="15" font-weight="600">{escape(label)}</text>',
            f'<text x="{card_x + 12}" y="{card_y + 42}" fill="{status_color}" font-size="12">{escape(front.status)}</text>',
            f'<text x="{card_x + 12}" y="{card_y + 63}" fill="#c3d3df" font-size="12">Troop share</text>',
            f'<text x="{card_x + 276}" y="{card_y + 63}" text-anchor="end" fill="#c3d3df" font-size="12">{f"{total:.1f} power" if total > EPS else "No forces"}</text>',
            _bar(deployed, total, card_x + 12, card_y + 69, metric="troop", height=16),
            f'<text x="{card_x + 12}" y="{card_y + 104}" fill="#c3d3df" font-size="12">Influence / 100</text>',
            f'<text x="{card_x + 276}" y="{card_y + 104}" text-anchor="end" fill="#c3d3df" font-size="12">{unclaimed:.1f} unclaimed</text>',
            _bar(front.influence, 100, card_x + 12, card_y + 111, metric="influence", height=7),
            '</g>',
        ])
    for index, faction in enumerate((*FACTIONS, "Unclaimed")):
        x = 28 + index * 105
        svg.append(f'<rect x="{x}" y="426" width="10" height="10" rx="2" fill="{COLORS.get(faction, "#364859")}"/><text x="{x + 17}" y="435" fill="#c3d3df" font-size="12">{faction}</text>')
    svg.append('<text x="28" y="461" fill="#a8bdcd" font-size="12">Troops show forces present. Influence persists after withdrawal; gray influence is unclaimed.</text></svg>')
    return "".join(svg)
