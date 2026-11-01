"""Metric residential layout engine and SVG architectural renderer.

This is an educational concept generator. It uses a fixed shared planning grid
with room-zone priorities and a vertically aligned stair core. It is not a
building-code, structural, or construction-documentation engine.
"""
from dataclasses import dataclass
from html import escape
from math import ceil

FT2_PER_M2 = 10.7639104167
OUTER_WALL = 0.30
GRID_COLS = 3
GRID_ROWS = 4
STAIR_CELL = 5  # fixed cell on every level, so stair core aligns floor-to-floor

@dataclass
class Room:
    name: str
    x: float
    y: float
    w: float
    h: float
    kind: str
    cell: int = -1
    clear_x: float = None
    clear_y: float = None
    clear_w: float = None
    clear_h: float = None

    @property
    def area(self):
        return (self.clear_w if self.clear_w is not None else self.w) * (self.clear_h if self.clear_h is not None else self.h)

def _cell_geometry(width, length):
    """Three unequal bays by four bands: public, service, private, private."""
    col_widths = [width * .40, width * .34, width * .26]
    row_heights = [length * .25, length * .25, length * .25, length * .25]
    xs = [0.0]
    ys = [0.0]
    for v in col_widths[:-1]:
        xs.append(xs[-1] + v)
    for v in row_heights[:-1]:
        ys.append(ys[-1] + v)
    cells = {}
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            idx = row * GRID_COLS + col
            cells[idx] = (xs[col], ys[row], col_widths[col], row_heights[row])
    return cells

def _assign_floor(level, bedrooms, bathrooms, floors, parking_spaces,
                  balconies, study, living_dining, utility_room=False):
    """Place rooms in public-to-private order around a stable stair core."""
    assigned = {}
    def put(cell, name, kind):
        if cell in assigned:
            return False
        assigned[cell] = (name, kind)
        return True

    if level == 0:
        # Front edge is the street. Parking sits beside the entry foyer; the
        # foyer opens into living, then dining/kitchen and the private zone.
        if parking_spaces:
            put(0, f"Parking ({parking_spaces} space{'s' if parking_spaces != 1 else ''})", "parking")
            put(1, "Entry / Foyer", "foyer")
            put(2, "Living / Dining" if living_dining == "Combined" else "Living", "living")
        else:
            put(0, "Entry / Foyer", "foyer")
            put(1, "Living / Dining" if living_dining == "Combined" else "Living", "living")
            put(2, "Dining" if living_dining == "Separate" else "Open Dining", "dining")
        if parking_spaces:
            put(3, "Dining" if living_dining == "Separate" else "Open Dining", "dining")
            put(4, "Kitchen", "kitchen")
            if utility_room:
                put(7, "Utility / Laundry", "utility")
        else:
            put(3, "Kitchen", "kitchen")
            if utility_room:
                put(4, "Utility / Laundry", "utility")
        if floors > 1:
            put(STAIR_CELL, "Staircase", "stair")
        bath_cell = 6 if parking_spaces and utility_room else 7
        put(bath_cell, "Bathroom 1", "bath")
        bed_cells = [c for c in [6, 8, 9, 10, 11] if c not in assigned]
        bath_cells = [8, 9, 10, 11, 6, 7]
        study_cells = [6, 8, 9, 10, 11]
        balcony_cells = [2, 6, 8, 9, 10, 11] if floors == 1 else []
    else:
        put(STAIR_CELL, "Staircase", "stair")
        # Upper floor is predominantly private; rooms near the service core
        # are reserved for bathrooms and family/study spaces.
        bed_cells = [0, 1, 3, 4, 6, 7, 8, 9, 10, 11]
        bath_cells = [4, 7, 8, 9, 10, 11, 2]
        study_cells = [2, 6, 9, 10, 11]
        balcony_cells = [2, 0, 1, 3, 6, 7, 8, 9, 10, 11]

    return assigned, bed_cells, bath_cells, study_cells, balcony_cells

def build_floors(plot_width, plot_length, bedrooms, bathrooms, floors,
                 parking_spaces=0, balconies=0, study=False, kitchen_type="Open",
                 living_dining="Combined", ensuite_bathrooms=0,
                 utility_room=False, garden_type="none", terrace_garden=False):
    """Create metric floor geometry with shared stair-core coordinates.

    A nominal 0.30 m outer wall is reserved. Room areas sum to the internal
    footprint because all 12 planning cells are represented, including passage.
    """
    if garden_type not in ("none", "rear", "courtyard"):
        raise ValueError("Choose no garden, a rear garden, or an L-shaped courtyard garden.")
    if terrace_garden and floors < 2:
        raise ValueError("A second-floor terrace garden requires a two-floor house.")
    garden_depth = max(1.5, min(3.0, plot_length * .20)) if garden_type == "rear" else 0.0
    building_length = plot_length - garden_depth
    # Larger two-level homes can spare a two-cell corner court; single-storey
    # plans keep the garden to one rear corner cell to preserve room capacity.
    garden_cells = ({11} if floors == 1 else {8, 11}) if garden_type == "courtyard" else set()
    inner_w = plot_width - 2 * OUTER_WALL
    inner_l = building_length - 2 * OUTER_WALL
    if inner_w < 4.0 or inner_l < 4.0:
        raise ValueError("The plot must be at least 4.6 m wide and 4.6 m long for this conceptual layout.")
    if not 0 <= ensuite_bathrooms <= min(bedrooms, bathrooms):
        raise ValueError("Ensuite bathrooms cannot exceed the bedroom or total bathroom count.")
    shared_bathroom_count = bathrooms - ensuite_bathrooms
    if shared_bathroom_count < 1:
        raise ValueError("At least one shared bathroom is required.")
    cells = _cell_geometry(inner_w, inner_l)
    available_cells = set(cells) - garden_cells

    bed_alloc = [0] * floors
    bath_alloc = [0] * floors
    bed_alloc[0] = bedrooms if floors == 1 else max(1, ceil(bedrooms / 2))
    bath_alloc[0] = shared_bathroom_count if floors == 1 else max(1, ceil(shared_bathroom_count / 2))
    for i in range(bedrooms - bed_alloc[0]):
        bed_alloc[1 + (i % (floors - 1))] += 1
    for i in range(shared_bathroom_count - bath_alloc[0]):
        bath_alloc[1 + (i % (floors - 1))] += 1

    result = []
    next_bed = 1
    next_bath = 1
    ensuites_left = ensuite_bathrooms
    for level in range(floors):
        assigned, bed_cells, bath_cells, study_cells, balcony_cells = _assign_floor(
            level, bed_alloc[level], bath_alloc[level], floors, parking_spaces,
            balconies, study, living_dining, utility_room and level == 0
        )
        bed_cells = [c for c in bed_cells if c in available_cells]
        bath_cells = [c for c in bath_cells if c in available_cells]
        study_cells = [c for c in study_cells if c in available_cells]
        balcony_cells = [c for c in balcony_cells if c in available_cells]
        for cell in garden_cells:
            assigned.pop(cell, None)
        # Ground-floor Bathroom 1 is pre-positioned by the stair/service core.
        if level == 0:
            next_bath = 2
        # Allocate remaining baths
        # to cells adjacent to the bedroom band where possible.
        remaining_baths = bath_alloc[level] - (1 if level == 0 else 0)
        for cell in bath_cells:
            if remaining_baths <= 0:
                break
            if cell not in assigned:
                assigned[cell] = (f"Bathroom {next_bath}", "bath")
                next_bath += 1
                remaining_baths -= 1
        if remaining_baths > 0:
            raise ValueError(f"Too many bathrooms to fit on floor {level+1}. Increase plot size or reduce bathroom count.")
        # Allocate bedrooms into rear/private cells.
        for _ in range(bed_alloc[level]):
            cell = next((c for c in bed_cells if c not in assigned), None)
            if cell is None:
                raise ValueError("The selected bedroom count exceeds this prototype's room capacity.")
            assigned[cell] = (f"Bedroom {next_bed}", "bedroom")
            next_bed += 1
        # Optional study and balcony use leftover cells, without displacing core rooms.
        if study and (level > 0 or floors == 1):
            cell = next((c for c in study_cells if c not in assigned), None)
            if cell is None:
                raise ValueError(f"There is no suitable space for the study on floor {level+1}. Reduce optional spaces or increase plot size.")
            assigned[cell] = ("Study", "study")
        if (level > 0 or floors == 1):
            for i in range(balconies):
                cell = next((c for c in balcony_cells if c not in assigned), None)
                if cell is None:
                    raise ValueError(f"There is no suitable space for balcony {i+1}. Reduce optional spaces or increase plot size.")
                assigned[cell] = (f"Balcony {i+1}", "balcony")
        if terrace_garden and level == 1:
            cell = next((c for c in reversed(balcony_cells) if c not in assigned), None)
            if cell is None:
                raise ValueError("There is no suitable space for the second-floor terrace garden. Reduce optional spaces or increase plot size.")
            assigned[cell] = ("Terrace Garden", "terrace")
        # Keep cell geometry for area accounting, but don't invent a "Family
        # Area" label for every leftover cell. Unassigned cells stay open/blank.
        for cell in available_cells:
            if cell not in assigned:
                assigned[cell] = ("", "open")

        rooms = []
        for cell, (name, kind) in assigned.items():
            x, y, w, h = cells[cell]
            col, row = cell % GRID_COLS, cell // GRID_COLS
            clear_x = x + (.075 if col > 0 else 0)
            clear_y = y + (.075 if row > 0 else 0)
            clear_w = w - (.075 if col > 0 else 0) - (.075 if col < GRID_COLS-1 else 0)
            clear_h = h - (.075 if row > 0 else 0) - (.075 if row < GRID_ROWS-1 else 0)
            if kind == "bedroom" and ensuites_left:
                bath_w, bath_h = min(1.20, clear_w * .38), min(1.60, clear_h * .72)
                bedroom_w = clear_w - bath_w - .15
                if bath_w >= 1.0 and bath_h >= 1.45 and bedroom_w >= 1.8:
                    rooms.append(Room(name + " (ensuite)", x, y, w, h, kind, cell,
                                      clear_x, clear_y, bedroom_w, clear_h))
                    bx, by = clear_x + bedroom_w + .15, clear_y + clear_h - bath_h
                    rooms.append(Room(name.replace("Bedroom", "Ensuite"), bx, by,
                                      bath_w, bath_h, "ensuite", cell, bx, by, bath_w, bath_h))
                    ensuites_left -= 1
                    continue
            rooms.append(Room(name, x, y, w, h, kind, cell, clear_x, clear_y, clear_w, clear_h))
        if ensuites_left:
            raise ValueError("There is no bedroom large enough for the requested ensuite. Reduce ensuite count or change the room requirements.")
        # Ensure requested counts fit the grid with useful minimum clear dimensions.
        for r in rooms:
            if r.kind in ("bedroom", "bath", "kitchen") and min(r.clear_w, r.clear_h) < 1.8:
                raise ValueError(f"{r.name} is too narrow for this conceptual layout. Increase plot width or reduce the number of spaces.")
        result.append({
            "level": level + 1, "rooms": rooms, "width": plot_width,
            "length": building_length, "site_length": plot_length,
            "building_length": building_length,
            "builtup": plot_width * building_length - sum(cells[c][2] * cells[c][3] for c in garden_cells),
            "garden_type": garden_type, "garden_depth": garden_depth,
            "garden_cells": sorted(garden_cells),
            "terrace_garden": bool(terrace_garden and level == 1),
            "stair_cell": STAIR_CELL, "stair_bounds": cells[STAIR_CELL],
            "has_front_parking": bool(parking_spaces and level == 0),
            "kitchen_type": kitchen_type, "living_dining": living_dining,
            "layout_score": evaluate_layout({"rooms": rooms})
        })
    return result

def evaluate_layout(floor):
    """Heuristic quality score based on adjacency, usable room sizes and stair core."""
    by_cell = {r.cell: r for r in floor["rooms"]}
    def adjacent(kind_a, kind_b):
        a = [r for r in floor["rooms"] if r.kind == kind_a]
        b = [r for r in floor["rooms"] if r.kind == kind_b]
        best = 0
        for ra in a:
            for rb in b:
                ar, ac = divmod(ra.cell, GRID_COLS)
                br, bc = divmod(rb.cell, GRID_COLS)
                distance = abs(ar-br) + abs(ac-bc)
                if distance == 1:
                    best = 1
        return best
    score = 60
    score += 12 * adjacent("living", "dining")
    score += 10 * adjacent("kitchen", "dining")
    score += 8 * adjacent("bedroom", "bath")
    score += 5 if by_cell.get(STAIR_CELL) and by_cell[STAIR_CELL].kind == "stair" else 0
    small_penalty = sum(3 for r in floor["rooms"] if r.kind in ("bedroom","bath","kitchen") and min(r.clear_w,r.clear_h) < 2.0)
    return max(0, min(100, score-small_penalty))

def _furniture(room):
    x = room.clear_x if room.clear_x is not None else room.x
    y = room.clear_y if room.clear_y is not None else room.y
    w = room.clear_w if room.clear_w is not None else room.w
    h = room.clear_h if room.clear_h is not None else room.h
    cx, cy = x + w / 2, y + h / 2
    k = room.kind
    if k == "bedroom":
        bw, bh = min(1.25, w * .36), min(1.55, h * .34)
        return (f'<rect class="sp-furn" x="{cx-bw/2:.3f}" y="{cy-bh/2:.3f}" width="{bw:.3f}" height="{bh:.3f}" rx=".05"/>'
                f'<path class="sp-detail-m" d="M {cx-bw/2:.3f} {cy-bh/2+.28:.3f} h {bw:.3f}"/>')
    if k == "living":
        sw, sh = min(1.55, w * .38), min(.62, h * .18)
        return (f'<rect class="sp-furn" x="{cx-sw/2:.3f}" y="{y+h*.34:.3f}" width="{sw:.3f}" height="{sh:.3f}" rx=".08"/>'
                f'<rect class="sp-furn" x="{cx-.34:.3f}" y="{y+h*.68:.3f}" width=".68" height=".42" rx=".04"/>')
    if k == "kitchen":
        kw = min(w * .70, 2.3)
        return (f'<path class="sp-furn" d="M {x+w*.12:.3f} {y+h*.30:.3f} h {kw:.3f} v .55 h -{kw:.3f} z"/>'
                f'<circle class="sp-fixture" cx="{x+w*.25:.3f}" cy="{y+h*.36:.3f}" r=".12"/>'
                f'<circle class="sp-fixture" cx="{x+w*.40:.3f}" cy="{y+h*.36:.3f}" r=".12"/>')
    if k == "utility":
        unit = min(.62, w * .28, h * .28)
        return (f'<rect class="sp-furn" x="{x+w*.12:.3f}" y="{y+h*.38:.3f}" width="{unit:.3f}" height="{unit:.3f}" rx=".04"/>'
                f'<circle class="sp-detail-m" cx="{x+w*.12+unit/2:.3f}" cy="{y+h*.38+unit/2:.3f}" r="{unit*.30:.3f}"/>'
                f'<path class="sp-furn" d="M {x+w*.22:.3f} {y+h*.24:.3f} h {min(w*.62,1.25):.3f} v .35 h -{min(w*.62,1.25):.3f} z"/>')
    if k == "dining":
        tw, th = min(1.15, w * .34), min(.72, h * .25)
        return f'<rect class="sp-furn" x="{cx-tw/2:.3f}" y="{cy-th/2:.3f}" width="{tw:.3f}" height="{th:.3f}" rx=".05"/>'
    if k == "bath":
        return (f'<rect class="sp-fixture" x="{x+w*.10:.3f}" y="{y+h*.34:.3f}" width=".48" height=".36" rx=".12"/>'
                f'<circle class="sp-fixture" cx="{x+w*.74:.3f}" cy="{y+h*.40:.3f}" r=".13"/>'
                f'<rect class="sp-fixture" x="{x+w*.14:.3f}" y="{y+h*.68:.3f}" width=".34" height=".24" rx=".08"/>')
    if k == "ensuite":
        return (f'<rect class="sp-fixture" x="{x+w*.08:.3f}" y="{y+h*.54:.3f}" width="{min(.55,w*.40):.3f}" height="{min(.42,h*.22):.3f}" rx=".10"/>'
                f'<circle class="sp-fixture" cx="{x+w*.76:.3f}" cy="{y+h*.60:.3f}" r=".12"/>'
                f'<rect class="sp-fixture" x="{x+w*.12:.3f}" y="{y+h*.78:.3f}" width="{min(.38,w*.30):.3f}" height="{min(.28,h*.18):.3f}" rx=".06"/>')
    if k == "parking":
        cw, ch = min(1.45, w * .44), min(3.0, h * .55)
        return (f'<rect class="sp-furn" x="{cx-cw/2:.3f}" y="{cy-ch/2:.3f}" width="{cw:.3f}" height="{ch:.3f}" rx=".20"/>'
                f'<path class="sp-detail-m" d="M {cx-cw/2:.3f} {cy-ch/2+.48:.3f} h {cw:.3f} M {cx-cw/2:.3f} {cy+ch/2-.48:.3f} h {cw:.3f}"/>')
    if k == "stair":
        # Compact U-return stair core, centred within its allocated room cell.
        sw, sh = min(1.65, w * .52), min(2.05, h * .56)
        sx, sy = cx - sw / 2, cy - sh / 2
        flight = sw * .39
        gap = sw * .12
        lines = []
        for j in range(1, 8):
            yy = sy + sh * .10 + j * sh * .095
            lines.append(f'M {sx+.06:.3f} {yy:.3f} h {flight-.06:.3f}')
            lines.append(f'M {sx+flight+gap:.3f} {yy:.3f} h {flight-.06:.3f}')
        landing_y = sy + sh * .43
        return (f'<rect class="sp-fixture" x="{sx:.3f}" y="{sy:.3f}" width="{sw:.3f}" height="{sh:.3f}" rx=".025"/>'
                + f'<rect class="sp-furn" x="{sx+flight:.3f}" y="{landing_y:.3f}" width="{gap:.3f}" height="{sh*.18:.3f}"/>'
                + '<path class="sp-detail-m" d="' + ' '.join(lines) + '"/>'
                + f'<path class="sp-arrow" d="M {cx:.3f} {sy+sh*.86:.3f} v -{sh*.25:.3f} m -.10 .10 l .10 -.10 .10 .10"/>')
    if k == "study":
        return (f'<rect class="sp-furn" x="{x+w*.18:.3f}" y="{y+h*.34:.3f}" width="{w*.62:.3f}" height=".55" rx=".04"/>'
                f'<rect class="sp-fixture" x="{x+w*.38:.3f}" y="{y+h*.62:.3f}" width=".42" height=".42" rx=".04"/>')
    if k in ("balcony", "terrace"):
        return f'<path class="sp-detail-m" d="M {x+w*.12:.3f} {y+h*.34:.3f} h {w*.76:.3f} M {x+w*.12:.3f} {y+h*.34:.3f} v {h*.55:.3f} M {x+w*.88:.3f} {y+h*.34:.3f} v {h*.55:.3f}"/>'
    return ""

def _door_on_horizontal(room, opening=.75):
    opening = min(opening, room.w * .32)
    if room.w < 1.8 or room.h < 1.8:
        return ""
    x = room.x + room.w * .5 - opening / 2
    y = room.y + room.h
    return (f'<path class="sp-erase" d="M {x:.3f} {y:.3f} h {opening:.3f}"/>'
            f'<path class="sp-door" d="M {x:.3f} {y:.3f} v -{opening:.3f}"/>'
            f'<path class="sp-swing" d="M {x+opening:.3f} {y:.3f} A {opening:.3f} {opening:.3f} 0 0 0 {x:.3f} {y-opening:.3f}"/>')

def _entry_door(room, opening=1.0):
    opening = min(opening, room.w * .30)
    x = room.x + room.w * .5 - opening / 2
    y = room.y
    return (f'<path class="sp-erase" d="M {x:.3f} {y:.3f} h {opening:.3f}"/>'
            f'<path class="sp-door" d="M {x:.3f} {y:.3f} v {opening:.3f}"/>'
            f'<path class="sp-swing" d="M {x+opening:.3f} {y:.3f} A {opening:.3f} {opening:.3f} 0 0 1 {x:.3f} {y+opening:.3f}"/>')

def _window(room):
    if room.w < 1.8:
        return ""
    x = room.x + room.w * .25
    y = room.y
    ww = min(1.35, room.w * .45)
    return (f'<path class="sp-erase" d="M {x:.3f} {y:.3f} h {ww:.3f}"/>'
            f'<path class="sp-window" d="M {x:.3f} {y-.035:.3f} h {ww:.3f} M {x:.3f} {y+.035:.3f} h {ww:.3f}"/>')

def render_svg(floor, plot_width, plot_length):
    scale = 90
    pad = 1.35
    W = (plot_width + 2 * pad) * scale
    H = (plot_length + 2 * pad) * scale + 1.0 * scale
    px = lambda v: v * scale
    ox, oy = pad * scale, pad * scale
    inner_x, inner_y = ox + px(OUTER_WALL), oy + px(OUTER_WALL)
    building_length = floor.get("building_length", plot_length)
    garden_type = floor.get("garden_type", "none")
    garden_cells = set(floor.get("garden_cells", []))
    inner_w, inner_h = plot_width - 2 * OUTER_WALL, building_length - 2 * OUTER_WALL
    rooms = floor["rooms"]
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" role="img" aria-label="Floor {floor["level"]} architectural plan">',
        '<defs><pattern id="grid" width="9" height="9" patternUnits="userSpaceOnUse"><path d="M 9 0 L 0 0 0 9" fill="none" stroke="#edf0f4" stroke-width=".55"/></pattern></defs>',
        '<style>.sp-outer{fill:#263344;stroke:#172333;stroke-width:1}.sp-inner{fill:#fff;stroke:#263344;stroke-width:1}.sp-part{fill:#263344;stroke:none}.sp-furn{fill:#eef2f5;stroke:#526273;stroke-width:.018}.sp-fixture{fill:#fff;stroke:#526273;stroke-width:.018}.sp-detail{fill:none;stroke:#657487;stroke-width:1.2}.sp-detail-m{fill:none;stroke:#657487;stroke-width:.014}.sp-door{fill:none;stroke:#26364a;stroke-width:.016}.sp-door-px{fill:none;stroke:#26364a;stroke-width:1.6}.sp-swing{fill:none;stroke:#8391a1;stroke-width:.010;stroke-dasharray:.035 .03}.sp-swing-px{fill:none;stroke:#8391a1;stroke-width:1.1;stroke-dasharray:3 2}.sp-window{stroke:#287c9f;stroke-width:3;stroke-linecap:butt}.sp-erase{fill:none;stroke:#fff;stroke-width:.12}.sp-label{font:700 18px Arial,sans-serif;fill:#182333;text-anchor:middle}.sp-dim{font:13px Arial,sans-serif;fill:#536274;text-anchor:middle}.sp-small{font:12px Arial;fill:#718093}.sp-arrow{fill:none;stroke:#3559a8;stroke-width:.020}</style>',
        '<style>.sp-label-small{font:700 10px Arial,sans-serif;fill:#182333;text-anchor:middle}.sp-dim-small{font:9px Arial,sans-serif;fill:#536274;text-anchor:middle}.sp-garden-label{font:700 14px Arial,sans-serif;fill:#55734f;text-anchor:middle;letter-spacing:1px}.sp-plant circle{fill:#69a55f;stroke:#467843;stroke-width:1}.sp-plant circle:nth-child(2){fill:#8bbd70}.sp-plant circle:nth-child(3){fill:#4d8d51}</style>',
        f'<rect width="{W:.0f}" height="{H:.0f}" fill="#fff"/>',
        f'<text x="{W/2:.1f}" y="28" text-anchor="middle" font-family="Arial" font-size="17" font-weight="bold" fill="#182333">FLOOR {floor["level"]} · ARCHITECTURAL CONCEPT</text>',
    ]
    geom = _cell_geometry(inner_w, inner_h)
    if garden_type == "courtyard":
        # The rear-right two cells are left open to form an L-shaped footprint
        # around a planted side/rear courtyard.
        garden_start = min(garden_cells)
        outer_notch_x = inner_x + px(geom[garden_start][0] - .075)
        outer_notch_y = inner_y + px(geom[garden_start][1] - .075)
        inner_notch_x = inner_x + px(geom[garden_start][0] + .075)
        inner_notch_y = inner_y + px(geom[garden_start][1] + .075)
        outer_d = (f"M {ox:.2f} {oy:.2f} H {ox+px(plot_width):.2f} "
                   f"V {outer_notch_y:.2f} H {outer_notch_x:.2f} "
                   f"V {oy+px(building_length):.2f} H {ox:.2f} Z")
        inner_d = (f"M {inner_x:.2f} {inner_y:.2f} H {inner_x+px(inner_w):.2f} "
                   f"V {inner_notch_y:.2f} H {inner_notch_x:.2f} "
                   f"V {inner_y+px(inner_h):.2f} H {inner_x:.2f} Z")
        svg.append(f'<path class="sp-outer" d="{outer_d}"/>')
        svg.append(f'<path class="sp-inner" d="{inner_d}"/>')
    else:
        svg.append(f'<rect class="sp-outer" x="{ox:.2f}" y="{oy:.2f}" width="{px(plot_width):.2f}" height="{px(building_length):.2f}"/>')
        svg.append(f'<rect class="sp-inner" x="{inner_x:.2f}" y="{inner_y:.2f}" width="{px(inner_w):.2f}" height="{px(inner_h):.2f}"/>')
        svg.append(f'<rect x="{inner_x:.2f}" y="{inner_y:.2f}" width="{px(inner_w):.2f}" height="{px(inner_h):.2f}" fill="url(#grid)"/>')
    if garden_type == "rear":
        garden_y = oy + px(building_length)
        garden_h = px(plot_length - building_length)
        svg.append(f'<rect x="{ox:.2f}" y="{garden_y:.2f}" width="{px(plot_width):.2f}" height="{garden_h:.2f}" fill="#e5f0df" stroke="#78966e" stroke-width="1.2"/>')
        svg.append(f'<text x="{W/2:.2f}" y="{garden_y+garden_h*.48:.2f}" class="sp-garden-label">REAR GARDEN · {floor["garden_depth"]:.2f} m deep</text>')
        for i in range(5):
            gx = ox + px(plot_width * (i + .5) / 5)
            gy = garden_y + garden_h * .74
            svg.append(f'<g class="sp-plant"><circle cx="{gx:.2f}" cy="{gy:.2f}" r="12"/><circle cx="{gx-7:.2f}" cy="{gy+3:.2f}" r="7"/><circle cx="{gx+7:.2f}" cy="{gy+3:.2f}" r="7"/></g>')
    elif garden_type == "courtyard":
        for cell in sorted(garden_cells):
            gx, gy, gw, gh = geom[cell]
            svg.append(f'<rect x="{inner_x+px(gx):.2f}" y="{inner_y+px(gy):.2f}" width="{px(gw):.2f}" height="{px(gh):.2f}" fill="#e5f0df"/>')
            svg.append(f'<text x="{inner_x+px(gx+gw/2):.2f}" y="{inner_y+px(gy+gh*.46):.2f}" class="sp-garden-label">GARDEN</text>')
            svg.append(f'<text x="{inner_x+px(gx+gw/2):.2f}" y="{inner_y+px(gy+gh*.46)+16:.2f}" class="sp-dim-small">{gw:.2f} × {gh:.2f} m</text>')
            for fx, fy, radius in ((.28,.30,10),(.72,.68,12),(.30,.76,7)):
                cx, cy = inner_x+px(gx+gw*fx), inner_y+px(gy+gh*fy)
                svg.append(f'<g class="sp-plant"><circle cx="{cx:.2f}" cy="{cy:.2f}" r="{radius}"/><circle cx="{cx-radius*.55:.2f}" cy="{cy+radius*.25:.2f}" r="{radius*.62:.2f}"/><circle cx="{cx+radius*.55:.2f}" cy="{cy+radius*.25:.2f}" r="{radius*.62:.2f}"/></g>')
    if garden_type != "none":
        svg.append(f'<rect x="{ox:.2f}" y="{oy:.2f}" width="{px(plot_width):.2f}" height="{px(plot_length):.2f}" fill="none" stroke="#688260" stroke-width="1.5" stroke-dasharray="8 6"/>')
    # Internal partition lines follow the grid, stopping at the garden cells.
    for boundary_index in range(GRID_COLS-1):
        wall_x = inner_x + px(geom[boundary_index+1][0]-.075)
        for row in range(GRID_ROWS):
            left_cell = row * GRID_COLS + boundary_index
            right_cell = left_cell + 1
            if left_cell in garden_cells or right_cell in garden_cells:
                continue
            omit_front = row == 0 and (
                (boundary_index == 0 and not floor.get("has_front_parking") and floor.get("living_dining") == "Combined") or
                (boundary_index == 1 and floor.get("kitchen_type") == "Open"))
            if not omit_front:
                y, _, _, h = geom[left_cell]
                svg.append(f'<rect class="sp-part" x="{wall_x:.2f}" y="{inner_y+px(y):.2f}" width="{px(.15):.2f}" height="{px(h):.2f}"/>')
    for row in range(1, GRID_ROWS):
        for col in range(GRID_COLS):
            upper_cell = (row-1) * GRID_COLS + col
            lower_cell = row * GRID_COLS + col
            if upper_cell in garden_cells or lower_cell in garden_cells:
                continue
            x, y, w, _ = geom[lower_cell]
            svg.append(f'<rect class="sp-part" x="{inner_x+px(x):.2f}" y="{inner_y+px(y-.075):.2f}" width="{px(w):.2f}" height="{px(.15):.2f}"/>')
    if floor.get("has_front_parking"):
        # A door links the street-side parking bay to the adjoining foyer.
        wall_x = inner_x + px(geom[1][0] - .075)
        door_y = inner_y + px(geom[0][1] + geom[0][3] * .52)
        opening = px(.78)
        svg.append(f'<rect x="{wall_x-px(.10):.2f}" y="{door_y-opening/2:.2f}" width="{px(.20):.2f}" height="{opening:.2f}" fill="#fff"/>')
        svg.append(f'<path class="sp-door-px" d="M {wall_x:.2f} {door_y-opening/2:.2f} h {opening:.2f}"/>')
        svg.append(f'<path class="sp-swing-px" d="M {wall_x+opening:.2f} {door_y-opening/2:.2f} A {opening:.2f} {opening:.2f} 0 0 1 {wall_x:.2f} {door_y+opening/2:.2f}"/>')
    kitchen_room = next((r for r in rooms if r.kind == "kitchen"), None)
    utility = next((r for r in rooms if r.kind == "utility"), None)
    if kitchen_room and utility:
        kr, kc = divmod(kitchen_room.cell, GRID_COLS)
        ur, uc = divmod(utility.cell, GRID_COLS)
        opening = px(.72)
        if kr == ur and abs(kc - uc) == 1:
            boundary = geom[max(kitchen_room.cell, utility.cell)][0]
            wall_x = inner_x + px(boundary - .075)
            door_y = inner_y + px(geom[kitchen_room.cell][1] + geom[kitchen_room.cell][3] * .52)
            svg.append(f'<rect x="{wall_x-px(.10):.2f}" y="{door_y-opening/2:.2f}" width="{px(.20):.2f}" height="{opening:.2f}" fill="#fff"/>')
            svg.append(f'<path class="sp-door-px" d="M {wall_x:.2f} {door_y-opening/2:.2f} h {opening:.2f}"/>')
            svg.append(f'<path class="sp-swing-px" d="M {wall_x+opening:.2f} {door_y-opening/2:.2f} A {opening:.2f} {opening:.2f} 0 0 1 {wall_x:.2f} {door_y+opening/2:.2f}"/>')
        elif kc == uc and abs(kr - ur) == 1:
            boundary = geom[max(kitchen_room.cell, utility.cell)][1]
            wall_y = inner_y + px(boundary - .075)
            door_x = inner_x + px(geom[kitchen_room.cell][0] + geom[kitchen_room.cell][2] * .52)
            svg.append(f'<rect x="{door_x-opening/2:.2f}" y="{wall_y-px(.10):.2f}" width="{opening:.2f}" height="{px(.20):.2f}" fill="#fff"/>')
            svg.append(f'<path class="sp-door-px" d="M {door_x-opening/2:.2f} {wall_y:.2f} v {opening:.2f}"/>')
            svg.append(f'<path class="sp-swing-px" d="M {door_x-opening/2:.2f} {wall_y+opening:.2f} A {opening:.2f} {opening:.2f} 0 0 0 {door_x+opening/2:.2f} {wall_y:.2f}"/>')

    # Render room fixtures, labels, windows, doors and dimensions.
    for room in rooms:
        if room.kind == "open" or not room.name:
            continue
        if room.kind == "ensuite":
            # Lightweight cubicle partition and inward doorway, in SVG pixels.
            bx, by, bw, bh = room.clear_x, room.clear_y, room.clear_w, room.clear_h
            svg.append(f'<rect x="{inner_x+px(bx):.2f}" y="{inner_y+px(by):.2f}" width="{px(bw):.2f}" height="{px(bh):.2f}" fill="none" stroke="#263344" stroke-width="1.4"/>')
            door_y = by + bh * .52
            svg.append(f'<rect x="{inner_x+px(bx)-px(.08):.2f}" y="{inner_y+px(door_y):.2f}" width="{px(.16):.2f}" height="{px(.62):.2f}" fill="#fff"/>')
            svg.append(f'<path class="sp-door" d="M {inner_x+px(bx):.2f} {inner_y+px(door_y):.2f} h {px(.62):.2f}"/>')
            svg.append(f'<path class="sp-swing" d="M {inner_x+px(bx):.2f} {inner_y+px(door_y+.62):.2f} A {px(.62):.2f} {px(.62):.2f} 0 0 0 {inner_x+px(bx+.62):.2f} {inner_y+px(door_y):.2f}"/>')
        furn = _furniture(room)
        if furn:
            svg.append(f'<g transform="translate({inner_x:.2f} {inner_y:.2f}) scale({scale})">{furn}</g>')
        rx = inner_x + px(room.clear_x)
        ry = inner_y + px(room.clear_y)
        rw, rh = px(room.clear_w), px(room.clear_h)
        # Keep room titles in a consistent top label zone so they remain
        # legible and do not sit directly on top of the furniture symbols.
        label_x = rx + rw / 2
        label_y = ry + min(30, max(23, rh * .12))
        if room.kind == "ensuite":
            label_y = ry + min(20, max(14, rh * .10))
            svg.append(f'<text class="sp-label-small" x="{label_x:.2f}" y="{label_y:.2f}">ENSUITE</text>')
            svg.append(f'<text class="sp-dim-small" x="{label_x:.2f}" y="{label_y+12:.2f}">{room.clear_w:.2f} × {room.clear_h:.2f} m</text>')
            svg.append(f'<text class="sp-dim-small" x="{label_x:.2f}" y="{label_y+23:.2f}">{room.area:.2f} m²</text>')
            continue
        if room.kind == "terrace":
            svg.append(f'<rect x="{rx:.2f}" y="{ry:.2f}" width="{rw:.2f}" height="{rh:.2f}" fill="#e5f0df" stroke="#78966e" stroke-width="1.2"/>')
            for fx, fy in ((.18,.30),(.82,.68)):
                cx, cy = rx+rw*fx, ry+rh*fy
                svg.append(f'<g class="sp-plant"><circle cx="{cx:.2f}" cy="{cy:.2f}" r="10"/><circle cx="{cx-6:.2f}" cy="{cy+3:.2f}" r="7"/><circle cx="{cx+6:.2f}" cy="{cy+3:.2f}" r="7"/></g>')
            svg.append(f'<text class="sp-label-small" x="{label_x:.2f}" y="{label_y:.2f}">TERRACE GARDEN</text>')
            svg.append(f'<text class="sp-dim-small" x="{label_x:.2f}" y="{label_y+12:.2f}">{room.clear_w:.2f} × {room.clear_h:.2f} m · OUTDOOR</text>')
            continue
        svg.append(f'<text class="sp-label" x="{label_x:.2f}" y="{label_y:.2f}">{escape(room.name)}</text>')
        svg.append(f'<text class="sp-dim" x="{label_x:.2f}" y="{label_y+20:.2f}">{room.clear_w:.2f} × {room.clear_h:.2f} m  ·  {room.area:.2f} m²</text>')
        # Window symbols on the front/top external edge.
        if room.y < 1e-6 and room.kind not in ("parking", "balcony", "living", "foyer"):
            win_x = inner_x + px(room.x + room.w*.25)
            win_w = px(min(1.35, room.w*.45))
            svg.append(f'<rect x="{win_x:.2f}" y="{oy:.2f}" width="{win_w:.2f}" height="{px(OUTER_WALL):.2f}" fill="#fff"/>')
            svg.append(f'<path class="sp-window" d="M {win_x:.2f} {oy+px(.10):.2f} h {win_w:.2f} M {win_x:.2f} {oy+px(.20):.2f} h {win_w:.2f}"/>')
        if room.x < 1e-6 and room.kind not in ("parking", "balcony"):
            win_y = inner_y + px(room.y + room.h*.25)
            win_h = px(min(1.25, room.h*.42))
            svg.append(f'<rect x="{ox:.2f}" y="{win_y:.2f}" width="{px(OUTER_WALL):.2f}" height="{win_h:.2f}" fill="#fff"/>')
            svg.append(f'<path class="sp-window" d="M {ox+px(.10):.2f} {win_y:.2f} v {win_h:.2f} M {ox+px(.20):.2f} {win_y:.2f} v {win_h:.2f}"/>')
        if garden_type == "courtyard" and room.cell in (7, 10) and room.kind not in ("parking", "balcony"):
            garden_edge = inner_x + px(geom[8][0] - .075)
            win_y = inner_y + px(room.y + room.h*.25)
            win_h = px(min(1.25, room.h*.42))
            svg.append(f'<rect x="{garden_edge-px(.075):.2f}" y="{win_y:.2f}" width="{px(.15):.2f}" height="{win_h:.2f}" fill="#fff"/>')
            svg.append(f'<path class="sp-window" d="M {garden_edge-px(.10):.2f} {win_y:.2f} v {win_h:.2f} M {garden_edge:.2f} {win_y:.2f} v {win_h:.2f}"/>')
        if room.x + room.w >= inner_w-1e-6 and room.kind not in ("parking", "balcony"):
            win_y = inner_y + px(room.y + room.h*.25)
            win_h = px(min(1.25, room.h*.42))
            right_wall_x = ox + px(plot_width)
            svg.append(f'<rect x="{right_wall_x-px(OUTER_WALL):.2f}" y="{win_y:.2f}" width="{px(OUTER_WALL):.2f}" height="{win_h:.2f}" fill="#fff"/>')
            svg.append(f'<path class="sp-window" d="M {right_wall_x-px(.20):.2f} {win_y:.2f} v {win_h:.2f} M {right_wall_x-px(.10):.2f} {win_y:.2f} v {win_h:.2f}"/>')
        if room.y + room.h >= inner_h-1e-6 and room.kind not in ("parking", "balcony"):
            win_x = inner_x + px(room.x + room.w*.25)
            win_w = px(min(1.35, room.w*.45))
            rear_y = oy + px(plot_length)
            svg.append(f'<rect x="{win_x:.2f}" y="{rear_y-px(OUTER_WALL):.2f}" width="{win_w:.2f}" height="{px(OUTER_WALL):.2f}" fill="#fff"/>')
            svg.append(f'<path class="sp-window" d="M {win_x:.2f} {rear_y-px(.20):.2f} h {win_w:.2f} M {win_x:.2f} {rear_y-px(.10):.2f} h {win_w:.2f}"/>')
        # The main entrance belongs to the foyer, not directly to the living room.
        if room.kind == "foyer" and room.y < 1e-6:
            opening = min(.90, room.w * .30)
            entry_x = inner_x + px(room.x + room.w*.5 - opening/2)
            # Cut a matching gap through the 300 mm external wall band.
            svg.append(f'<rect x="{entry_x:.2f}" y="{oy:.2f}" width="{px(opening):.2f}" height="{px(OUTER_WALL):.2f}" fill="#fff"/>')
            svg.append(f'<path class="sp-door-px" d="M {entry_x:.2f} {inner_y:.2f} v {px(opening):.2f}"/>')
            svg.append(f'<path class="sp-swing-px" d="M {entry_x+px(opening):.2f} {inner_y:.2f} A {px(opening):.2f} {px(opening):.2f} 0 0 1 {entry_x:.2f} {inner_y+px(opening):.2f}"/>')
        # Door opening arcs on lower internal partition edges only.
        if room.y + room.h < inner_h - 1e-6 and room.kind not in ("corridor", "balcony"):
            svg.append(f'<g transform="translate({inner_x:.2f} {inner_y:.2f}) scale({scale})">{_door_on_horizontal(room)}</g>')

    # Overall dimension strings and extension lines.
    top_y = oy - 18
    left_x = ox - 22
    svg.append(f'<path class="sp-detail" d="M {ox:.2f} {top_y+6:.2f} V {oy:.2f} M {ox+px(plot_width):.2f} {top_y+6:.2f} V {oy:.2f} M {ox:.2f} {top_y:.2f} H {ox+px(plot_width):.2f}"/>')
    svg.append(f'<text class="sp-dim" x="{ox+px(plot_width)/2:.2f}" y="{top_y-4:.2f}">{plot_width:.2f} m</text>')
    svg.append(f'<path class="sp-detail" d="M {left_x+6:.2f} {oy:.2f} H {ox:.2f} M {left_x+6:.2f} {oy+px(plot_length):.2f} H {ox:.2f} M {left_x:.2f} {oy:.2f} V {oy+px(plot_length):.2f}"/>')
    svg.append(f'<text class="sp-dim" x="{left_x-5:.2f}" y="{oy+px(plot_length)/2:.2f}" transform="rotate(-90 {left_x-5:.2f} {oy+px(plot_length)/2:.2f})">{plot_length:.2f} m</text>')
    svg.append(f'<text class="sp-small" x="{ox:.2f}" y="{H-22:.2f}">All dimensions in metres · nominal 300 mm external wall</text>')
    svg.append('</svg>')
    return ''.join(svg)
