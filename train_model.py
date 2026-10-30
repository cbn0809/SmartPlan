import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score, classification_report

df = pd.read_csv("house_planner_synthetic_dataset.csv")
features = ["plot_area_sqft","bedrooms","bathrooms","floors","parking_spaces",
            "balconies","study_room","kitchen_type","living_dining",
            "estimated_builtup_area_sqft"]
X, y = df[features], df["layout_category"]
cat = ["kitchen_type","living_dining"]
num = [c for c in features if c not in cat]
prep = ColumnTransformer([
    ("categorical", OneHotEncoder(handle_unknown="ignore"), cat),
    ("numeric", "passthrough", num)
])
model = Pipeline([
    ("prep", prep),
    ("tree", DecisionTreeClassifier(max_depth=6, random_state=42))
])
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=.2, random_state=42, stratify=y
)
model.fit(X_train, y_train)
pred = model.predict(X_test)
print("Rows and columns:", df.shape)
print("Category counts:\n", y.value_counts())
print("Test accuracy:", round(accuracy_score(y_test, pred), 3))
print(classification_report(y_test, pred, zero_division=0))
joblib.dump(model, "house_model.joblib")
print("Saved house_model.joblib")
