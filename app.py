from flask import Flask, render_template, request
import pandas as pd
import joblib
import io
from floorplan import build_floors, render_svg, FT2_PER_M2

app = Flask(__name__)
try:
    model = joblib.load("house_model.joblib")
except (FileNotFoundError, EOFError):
    model = None

FEATURES = ["plot_area_sqft","bedrooms","bathrooms","floors","parking_spaces",
            "balconies","study_room","kitchen_type","living_dining",
            "estimated_builtup_area_sqft"]

def predict_layout(plot_area_m2, bedrooms, bathrooms, floors, parking,
                   balconies, study, kitchen, living, builtup_m2):
    if model is None:
        return "Standard"
    row = pd.DataFrame([{
        "plot_area_sqft": plot_area_m2 * FT2_PER_M2,
        "bedrooms": bedrooms, "bathrooms": bathrooms, "floors": floors,
        "parking_spaces": parking, "balconies": balconies, "study_room": study,
        "kitchen_type": kitchen, "living_dining": living,
        "estimated_builtup_area_sqft": builtup_m2 * FT2_PER_M2
    }], columns=FEATURES)
    return str(model.predict(row)[0])

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    try:
        length = float(request.form["plot_length"])
        width = float(request.form["plot_width"])
        beds = int(request.form["bedrooms"])
        baths = int(request.form["bathrooms"])
        ensuites = int(request.form.get("ensuite_bathrooms", 0))
        floors = int(request.form["floors"])
        parking = int(request.form.get("parking_spaces", 0))
        balconies = int(request.form.get("balconies", 0))
        study = int(request.form.get("study_room", 0))
        utility = int(request.form.get("utility_room", 0))
        garden_type = request.form.get("garden_type", "none")
        terrace_garden = int(request.form.get("terrace_garden", 0))
        kitchen = request.form.get("kitchen_type", "Open")
        living = request.form.get("living_dining", "Combined")
        rate = float(request.form.get("rate", 2200))
        if min(length, width, rate) <= 0:
            raise ValueError("Plot dimensions and construction rate must be greater than zero.")
        # Keep this school-project planner within a realistic residential plot range.
        if not (8.0 <= length <= 25.0):
            raise ValueError("Plot length must be between 8 m and 25 m.")
        if not (6.0 <= width <= 20.0):
            raise ValueError("Plot width must be between 6 m and 20 m.")
        if length * width > 400:
            raise ValueError("Maximum supported plot area is 400 m². Please enter a smaller residential plot.")
        if max(length, width) / min(length, width) > 2.5:
            raise ValueError("Please use a more practical plot proportion (maximum side ratio 2.5:1).")
        if not (1 <= beds <= 5 and 1 <= baths <= 4 and 1 <= floors <= 2):
            raise ValueError("Choose 1–5 bedrooms, 1–4 bathrooms and 1–2 floors.")
        if not (0 <= parking <= 2 and 0 <= balconies <= 2 and study in (0,1)
                and utility in (0,1)
                and 0 <= ensuites <= min(beds, baths - 1)):
            raise ValueError("Please check parking, balcony and study-room selections.")
        if garden_type not in ("none", "rear", "courtyard"):
            raise ValueError("Choose no garden, a rear garden, or an L-shaped courtyard garden.")
        plot_area = length * width
        floor_plans = build_floors(width, length, beds, baths, floors, parking,
                                   balconies, bool(study), kitchen, living, ensuites,
                                   bool(utility), garden_type, bool(terrace_garden))
        total_builtup = sum(f["builtup"] for f in floor_plans)
        # Rate remains a familiar ₹/sq ft input; all geometry and displayed areas use metric.
        rate_m2 = rate * FT2_PER_M2
        cost = total_builtup * rate_m2
        prediction = predict_layout(plot_area, beds, baths, floors, parking,
                                    balconies, study, kitchen, living, total_builtup)
        plans = []
        for f in floor_plans:
            plans.append({
                "level": f["level"],
                "svg": render_svg(f, width, length),
                "rooms": [{
                    "name": r.name, "width": r.clear_w, "length": r.clear_h, "area": r.area
                } for r in f["rooms"] if r.kind != "open" and r.name],
                "area": sum(r.area for r in f["rooms"] if r.kind != "terrace"),
                "layout_score": f["layout_score"]
            })
        return render_template("result.html", prediction=prediction,
            plot_area=plot_area, builtup=total_builtup, cost=cost,
            cost_lakh=cost/100000, rate=rate, bedrooms=beds,
            bathrooms=baths, floors=floors, plans=plans,
            remaining= max(0.0, plot_area - floor_plans[0]["builtup"]),
            plot_width=width, plot_length=length,
            layout_score=round(sum(f["layout_score"] for f in floor_plans)/len(floor_plans)),
            model_available=model is not None)
    except (ValueError, KeyError, TypeError) as e:
        return render_template("index.html", error=str(e) or "Please check your inputs."), 400

if __name__ == "__main__":
    app.run(debug=True)
