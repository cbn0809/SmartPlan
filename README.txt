AI-Based Smart House Planner — VS Code setup

CURRENT DEVELOPMENT BUILD
This update builds on the original Flask + CSV + scikit-learn project. It adds
a metric geometry engine, adjacency-aware zoning and architectural SVG output.

METRIC SYSTEM
- Plot width and length are entered in metres.
- Room dimensions and areas are shown in metres and square metres.
- The existing ML model still receives square-foot feature values internally
  for compatibility with the original synthetic dataset.
- Construction rate remains ₹ per sq. ft.; it is converted internally.

SETUP
1. Extract this folder and open it in Visual Studio Code.
2. Open Terminal > New Terminal.
3. Create a virtual environment (recommended): python -m venv .venv
4. Activate it:
   Windows PowerShell: .venv\\Scripts\\Activate.ps1
   macOS/Linux: source .venv/bin/activate
5. Install: pip install -r requirements.txt
6. Train the optional ML classifier: python train_model.py
7. Start the app: python app.py
8. Open http://127.0.0.1:5000

TESTS
Run the geometry-engine tests:
   python -m unittest discover -s tests -v

WHAT THIS BUILD ADDS
- Metric plot input, room dimensions and room-wise area calculations.
- Fixed 3 x 4 planning grid with public, service and private room zones.
- Adjacency priorities: living/dining, kitchen/dining and bedrooms/bathrooms.
- Open-plan front-zone partition handling based on kitchen and living/dining
  selections.
- A staircase reserved at the same grid coordinates on every multi-storey floor.
- Single-storey plans do not show an unnecessary staircase.
- Conceptual 300 mm external wall band and 150 mm internal partition strips.
- Main entrance opening, door leaves and swing arcs, external window symbols,
  furniture and bathroom fixtures.
- Separate SVG plan for each floor, floor switching and SVG downloads.
- A heuristic arrangement score to explain the rule-based layout evaluation.
- Original CSV, Flask frontend/backend and ML classifier retained.

IMPORTANT LIMITATIONS
This is still an educational concept generator. The zoning engine currently
uses a fixed 3 x 4 grid with room-type placement priorities. It is more structured
than the earlier equal-box diagram, but it is not yet a free-form architectural
optimiser. It does not verify statutory setbacks, local Kerala building rules,
ventilation/lighting requirements, structural grids, plumbing stacks, fire
egress, accessibility, exact stair risers/treads or construction clearances.
The heuristic score is not a compliance or professional design rating.
Synthetic CSV labels are not architectural ground truth. A licensed local
architect and structural engineer must verify any real project.

SAMPLE OUTPUTS
Open sample_outputs/sample_floor_1.svg and sample_floor_2.svg in a browser
or vector editor to inspect a generated 9 m x 12 m, 3-bedroom, 2-floor plan.

Latest drawing refinements
- Room names and clear dimensions now use a larger, high-contrast label style,
  with net room area shown directly in each room.
- Furniture and fixture outlines use non-scaling strokes so they remain
  proportional when the SVG is resized in the browser.
- Door openings use a wall-sized erase gap and slim door/swing strokes rather
  than oversized symbols.
- The U-return staircase graphic is compact and centred within its room cell.
- Updated SVG examples are included in sample_outputs.


STUDENT-PROJECT INPUT LIMITS (v3.2)
- Plot width: 6–20 m
- Plot length: 8–25 m
- Maximum plot area: 400 m²
- Maximum side ratio: 2.5:1
- Bedrooms: 1–5; bathrooms: 1–4; floors: 1–2
These limits prevent extreme plot values that the simple concept layout engine cannot handle.
The floor plan is now the first and largest result section, with larger room labels and no artificial SVG height cap.
