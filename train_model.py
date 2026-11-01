import pandas as pd
import joblib
from sklearn.model_selection import RepeatedStratifiedKFold, cross_val_score
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier

df = pd.read_csv("house_planner_synthetic_dataset.csv")
features = ["plot_area_sqft", "bedrooms", "bathrooms", "floors", "parking_spaces",
            "balconies", "study_room", "kitchen_type", "living_dining",
            "estimated_builtup_area_sqft"]
X, y = df[features], df["layout_category"]
cat = ["kitchen_type", "living_dining"]
num = [column for column in features if column not in cat]
prep = ColumnTransformer([
    ("categorical", OneHotEncoder(handle_unknown="ignore"), cat),
    ("numeric", "passthrough", num)
])

# Compare tree complexity over 100 stratified train/validation splits. Re-fitting
# the same tree 100 times would not improve it; these folds test which depth
# generalizes better before the final model is fitted on all available rows.
cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=20, random_state=42)
depths = [6, 8, 10]
cv_results = {}
for depth in depths:
    candidate = Pipeline([
        ("prep", prep),
        ("tree", DecisionTreeClassifier(max_depth=depth, random_state=42))
    ])
    scores = cross_val_score(candidate, X, y, cv=cv, scoring="accuracy", n_jobs=1)
    cv_results[depth] = scores
    print(f"Depth {depth}: 100-fold accuracy "
          f"{scores.mean():.3f} +/- {scores.std():.3f}")

best_depth = max(depths, key=lambda depth: cv_results[depth].mean())
model = Pipeline([
    ("prep", prep),
    ("tree", DecisionTreeClassifier(max_depth=best_depth, random_state=42))
])
model.fit(X, y)
joblib.dump(model, "house_model.joblib")
print(f"Selected depth: {best_depth}")
print(f"Saved house_model.joblib trained on all {len(df)} rows.")
