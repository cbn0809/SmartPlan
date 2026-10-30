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
                  balconies, study, living_dining):
    """Place rooms by functional zone while reserving the same stair cell."""
    assigned = {}
    def put(cell, name, kind):
        if cell in assigned:
            return False
        assigned[cell] = (name, kind)
        return True

    if level == 0:
        # Public zone at the front: living and dining touch; kitchen is one
        # band behind dining. Service and stair core share the middle band.
        put(0, "Living / Dining" if living_dining == "Combined" else "Living", "living")
        put(1, "Dining" if living_dining == "Separate" else "Open Dining", "dining")
        put(2, "Kitchen", "kitchen")
        if floors > 1:
            put(STAIR_CELL, "Staircase", "stair")
        put(4, "Bathroom 1", "bath")
        if parking_spaces:
            put(6, f"Parking ({parking_spaces} space{'s' if parking_spaces != 1 else ''})", "parking")
        bed_cells = [7, 8, 9, 10, 11]
        bath_cells = [8, 9, 10, 11, 2]
        study_cells = [2, 6, 9, 10, 11]
        balcony_cells = [2, 6, 9, 10, 11] if floors == 1 else []
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
                 living_dining="Combined"):
    """Create metric floor geometry with shared stair-core coordinates.

    A nominal 0.30 m outer wall is reserved. Room areas sum to the internal
    footprint because all 12 planning cells are represented, including passage.
    """
    inner_w = plot_width - 2 * OUTER_WALL
    inner_l = plot_length - 2 * OUTER_WALL
    if inner_w < 4.0 or inner_l < 4.0:
        raise ValueError("The plot must be at least 4.6 m wide and 4.6 m long for this conceptual layout.")
    cells = _cell_geometry(inner_w, inner_l)

    bed_alloc = [0] * floors
    bath_alloc = [0] * floors
    bed_alloc[0] = bedrooms if floors == 1 else max(1, ceil(bedrooms / 2))
    bath_alloc[0] = bathrooms if floors == 1 else max(1, ceil(bathrooms / 2))
    for i in range(bedrooms - bed_alloc[0]):
        bed_alloc[1 + (i % (floors - 1))] += 1
    for i in range(bathrooms - bath_alloc[0]):
        bath_alloc[1 + (i % (floors - 1))] += 1

    result = []
    next_bed = 1
    next_bath = 1
    for level in range(floors):
        assigned, bed_cells, bath_cells, study_cells, balcony_cells = _assign_floor(
            level, bed_alloc[level], bath_alloc[level], floors, parking_spaces,
            balconies, study, living_dining
        )
        # Ground-floor Bathroom 1 is pre-positioned beside the stair/service core.
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
        # Keep all 12 cells accounted for: remaining cells become circulation or
        # a flexible family/utility space, never unlabelled blank rectangles.
        for cell in cells:
            if cell not in assigned:
                assigned[cell] = ("Passage" if cell in (2, 8, 10, 11) else "Family Area", "corridor")

        rooms = []
        for cell, (name, kind) in assigned.items():
            x, y, w, h = cells[cell]
            col, row = cell % GRID_COLS, cell // GRID_COLS
            clear_x = x + (.075 if col > 0 else 0)
            clear_y = y + (.075 if row > 0 else 0)
            clear_w = w - (.075 if col > 0 else 0) - (.075 if col < GRID_COLS-1 else 0)
            clear_h = h - (.075 if row > 0 else 0) - (.075 if row < GRID_ROWS-1 else 0)
            rooms.append(Room(name, x, y, w, h, kind, cell, clear_x, clear_y, clear_w, clear_h))
        # Ensure requested counts fit the grid with useful minimum clear dimensions.
        for r in rooms:
            if r.kind in ("bedroom", "bath", "kitchen") and min(r.clear_w, r.clear_h) < 1.8:
                raise ValueError(f"{r.name} is too narrow for this conceptual layout. Increase plot width or reduce the number of spaces.")
        result.append({
            "level": level + 1, "rooms": rooms, "width": plot_width,
            "length": plot_length, "builtup": plot_width * plot_length,
            "stair_cell": STAIR_CELL, "stair_bounds": cells[STAIR_CELL],
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
    if k == "dining":
        tw, th = min(1.15, w * .34), min(.72, h * .25)
        return f'<rect class="sp-furn" x="{cx-tw/2:.3f}" y="{cy-th/2:.3f}" width="{tw:.3f}" height="{th:.3f}" rx=".05"/>'
    if k == "bath":
        return (f'<rect class="sp-fixture" x="{x+w*.10:.3f}" y="{y+h*.34:.3f}" width=".48" height=".36" rx=".12"/>'
                f'<circle class="sp-fixture" cx="{x+w*.74:.3f}" cy="{y+h*.40:.3f}" r=".13"/>'
                f'<rect class="sp-fixture" x="{x+w*.14:.3f}" y="{y+h*.68:.3f}" width=".34" height=".24" rx=".08"/>')
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
    if k == "balcony":
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
    inner_w, inner_h = plot_width - 2 * OUTER_WALL, plot_length - 2 * OUTER_WALL
    rooms = floor["rooms"]
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" role="img" aria-label="Floor {floor["level"]} architectural plan">',
        '<defs><pattern id="grid" width="9" height="9" patternUnits="userSpaceOnUse"><path d="M 9 0 L 0 0 0 9" fill="none" stroke="#edf0f4" stroke-width=".55"/></pattern></defs>',
        '<style>.sp-outer{fill:#263344;stroke:#172333;stroke-width:1}.sp-inner{fill:#fff;stroke:#263344;stroke-width:1}.sp-part{fill:#263344;stroke:none}.sp-furn{fill:#eef2f5;stroke:#526273;stroke-width:.018}.sp-fixture{fill:#fff;stroke:#526273;stroke-width:.018}.sp-detail{fill:none;stroke:#657487;stroke-width:1.2}.sp-detail-m{fill:none;stroke:#657487;stroke-width:.014}.sp-door{fill:none;stroke:#26364a;stroke-width:.016}.sp-door-px{fill:none;stroke:#26364a;stroke-width:1.6}.sp-swing{fill:none;stroke:#8391a1;stroke-width:.010;stroke-dasharray:.035 .03}.sp-swing-px{fill:none;stroke:#8391a1;stroke-width:1.1;stroke-dasharray:3 2}.sp-window{stroke:#287c9f;stroke-width:3;stroke-linecap:butt}.sp-erase{fill:none;stroke:#fff;stroke-width:.12}.sp-label{font:700 18px Arial,sans-serif;fill:#182333;text-anchor:middle}.sp-dim{font:13px Arial,sans-serif;fill:#536274;text-anchor:middle}.sp-small{font:12px Arial;fill:#718093}.sp-arrow{fill:none;stroke:#3559a8;stroke-width:.020}</style>',
        f'<rect width="{W:.0f}" height="{H:.0f}" fill="#fff"/>',
        f'<text x="{W/2:.1f}" y="28" text-anchor="middle" font-family="Arial" font-size="17" font-weight="bold" fill="#182333">FLOOR {floor["level"]} · ARCHITECTURAL CONCEPT</text>',
        # Filled perimeter band represents the nominal 300 mm external wall.
        f'<rect class="sp-outer" x="{ox:.2f}" y="{oy:.2f}" width="{px(plot_width):.2f}" height="{px(plot_length):.2f}"/>',
        f'<rect class="sp-inner" x="{inner_x:.2f}" y="{inner_y:.2f}" width="{px(inner_w):.2f}" height="{px(inner_h):.2f}"/>',
        f'<rect x="{inner_x:.2f}" y="{inner_y:.2f}" width="{px(inner_w):.2f}" height="{px(inner_h):.2f}" fill="url(#grid)"/>'
    ]
    # Internal partition lines follow the fixed 3 x 4 planning grid.
    geom = _cell_geometry(inner_w, inner_h)
    col_x = [geom[i][0] for i in (1, 2)]
    row_y = [geom[i*GRID_COLS][1] for i in (1, 2, 3)]
    for boundary_index, x in enumerate(col_x):
        wall_x = inner_x + px(x-.075)
        # Open-plan front zones omit only the corresponding front-band partition.
        omit_front_wall = ((boundary_index == 0 and floor.get("living_dining") == "Combined") or
                           (boundary_index == 1 and floor.get("kitchen_type") == "Open"))
        if omit_front_wall:
            front_h = px(inner_h * .25)
            svg.append(f'<rect class="sp-part" x="{wall_x:.2f}" y="{inner_y+front_h:.2f}" width="{px(.15):.2f}" height="{px(inner_h)-front_h:.2f}"/>')
        else:
            svg.append(f'<rect class="sp-part" x="{wall_x:.2f}" y="{inner_y:.2f}" width="{px(.15):.2f}" height="{px(inner_h):.2f}"/>')
    for y in row_y:
        svg.append(f'<rect class="sp-part" x="{inner_x:.2f}" y="{inner_y+px(y-.075):.2f}" width="{px(inner_w):.2f}" height="{px(.15):.2f}"/>')

    # Render room fixtures, labels, windows, doors and dimensions.
    for room in rooms:
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
        svg.append(f'<text class="sp-label" x="{label_x:.2f}" y="{label_y:.2f}">{escape(room.name)}</text>')
        svg.append(f'<text class="sp-dim" x="{label_x:.2f}" y="{label_y+20:.2f}">{room.clear_w:.2f} × {room.clear_h:.2f} m  ·  {room.area:.2f} m²</text>')
        # Window symbols on the front/top external edge.
        if room.y < 1e-6 and room.kind not in ("parking", "balcony", "living"):
            win_x = inner_x + px(room.x + room.w*.25)
            win_w = px(min(1.35, room.w*.45))
            svg.append(f'<rect x="{win_x:.2f}" y="{oy:.2f}" width="{win_w:.2f}" height="{px(OUTER_WALL):.2f}" fill="#fff"/>')
            svg.append(f'<path class="sp-window" d="M {win_x:.2f} {oy+px(.10):.2f} h {win_w:.2f} M {win_x:.2f} {oy+px(.20):.2f} h {win_w:.2f}"/>')
        if room.x < 1e-6 and room.kind not in ("parking", "balcony"):
            win_y = inner_y + px(room.y + room.h*.25)
            win_h = px(min(1.25, room.h*.42))
            svg.append(f'<rect x="{ox:.2f}" y="{win_y:.2f}" width="{px(OUTER_WALL):.2f}" height="{win_h:.2f}" fill="#fff"/>')
            svg.append(f'<path class="sp-window" d="M {ox+px(.10):.2f} {win_y:.2f} v {win_h:.2f} M {ox+px(.20):.2f} {win_y:.2f} v {win_h:.2f}"/>')
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
        # Main entrance is placed in the front wall at the living-room bay.
        if room.kind == "living" and room.y < 1e-6:
            opening = min(.85, room.w * .26)
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
    svg.append(f'<text class="sp-small" x="{ox:.2f}" y="{H-22:.2f}">All dimensions in metres · nominal 300 mm external wall · conceptual layout, not for construction</text>')
    svg.append('</svg>')
    return ''.join(svg)
