import unittest
from floorplan import build_floors, render_svg, OUTER_WALL

class FloorPlanEngineTests(unittest.TestCase):
    def test_net_room_area_excludes_internal_walls(self):
        width, length = 9.0, 12.0
        floors = build_floors(width, length, 3, 2, 2, 1, 1, True)
        inner_w = width - 2*OUTER_WALL
        inner_l = length - 2*OUTER_WALL
        # Net room area excludes two 150 mm vertical and three horizontal
        # partition bands, subtracting their six intersections once.
        expected = (inner_w * inner_l
                    - 2*.15*inner_l - 3*.15*inner_w
                    + 6*.15*.15)
        for floor in floors:
            self.assertAlmostEqual(sum(r.area for r in floor["rooms"]), expected, places=6)
            self.assertLess(sum(r.area for r in floor["rooms"]), floor["builtup"])

    def test_stair_core_aligns_across_floors(self):
        floors = build_floors(10, 15, 4, 3, 2)
        stairs = [next(r for r in floor["rooms"] if r.kind == "stair") for floor in floors]
        self.assertEqual((stairs[0].x, stairs[0].y, stairs[0].w, stairs[0].h),
                         (stairs[1].x, stairs[1].y, stairs[1].w, stairs[1].h))

    def test_room_cells_do_not_overlap(self):
        floor = build_floors(9, 12, 3, 2, 2)[0]
        cells = [r.cell for r in floor["rooms"]]
        self.assertEqual(len(cells), len(set(cells)))
        self.assertEqual(len(cells), 12)

    def test_single_storey_has_no_staircase(self):
        floor = build_floors(9, 12, 3, 2, 1)[0]
        self.assertFalse(any(r.kind == "stair" for r in floor["rooms"]))

    def test_svg_contains_architectural_symbols(self):
        floor = build_floors(9, 12, 3, 2, 2)[0]
        svg = render_svg(floor, 9, 12)
        self.assertIn("<svg", svg)
        self.assertIn("class=\"sp-door\"", svg)
        self.assertIn("class=\"sp-window\"", svg)
        self.assertIn("class=\"sp-furn\"", svg)
        self.assertIn("font:700 18px Arial,sans-serif", svg)
        self.assertIn("m  ·  ", svg)
        self.assertIn("</svg>", svg)

    def test_staircase_symbol_is_compact(self):
        floor = build_floors(9, 12, 3, 2, 2)[0]
        stair = next(r for r in floor["rooms"] if r.kind == "stair")
        svg = render_svg(floor, 9, 12)
        self.assertIn('width="1.097"', svg)
        self.assertLessEqual(stair.w, 9.0)

    def test_combined_living_dining_is_labelled_consistently(self):
        floor = build_floors(9, 12, 3, 2, 1, living_dining="Combined")[0]
        labels = {r.name for r in floor["rooms"]}
        self.assertIn("Living / Dining", labels)
        self.assertIn("Open Dining", labels)
        self.assertNotIn("Dining", labels)

    def test_separate_living_dining_is_labelled_consistently(self):
        floor = build_floors(9, 12, 3, 2, 1, living_dining="Separate")[0]
        labels = {r.name for r in floor["rooms"]}
        self.assertIn("Living", labels)
        self.assertIn("Dining", labels)

    def test_open_plan_selection_changes_partition_geometry(self):
        open_floor = build_floors(9, 12, 3, 2, 2,
                                  kitchen_type="Open", living_dining="Combined")[0]
        closed_floor = build_floors(9, 12, 3, 2, 2,
                                    kitchen_type="Closed", living_dining="Separate")[0]
        self.assertNotEqual(render_svg(open_floor, 9, 12),
                            render_svg(closed_floor, 9, 12))

    def test_too_small_plot_is_rejected(self):
        with self.assertRaises(ValueError):
            build_floors(4, 5, 2, 1, 1)

if __name__ == "__main__":
    unittest.main()