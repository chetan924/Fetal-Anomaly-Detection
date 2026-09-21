from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
)

from sklearn.linear_model import LogisticRegression


# ============================================================
# CONFIG
# ============================================================

INPUT_CSV = Path(
    r"D:\Fetal_Face_3D\features\fetal_face_3d_labeled.csv"
)

OUTPUT_DIR = Path(
    r"D:\Fetal_Face_3D\models"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

RANDOM_STATE = 42
N_SPLITS = 5


# ============================================================
# LOAD DATA
# ============================================================

print("=" * 70)
print("FETAL FACE 3D CLASSIFIER TRAINING")
print("=" * 70)

if not INPUT_CSV.exists():
    raise FileNotFoundError(
        f"Input CSV not found:\n{INPUT_CSV}"
    )

df = pd.read_csv(
    INPUT_CSV
)

print(
    f"Dataset shape: {df.shape}"
)


# ============================================================
# TARGET CHECK
# ============================================================

if "face_label" not in df.columns:
    raise ValueError(
        "face_label column not found."
    )

print("\nClass distribution:")

print(
    df["face_label_name"]
    .value_counts()
)


# ============================================================
# FEATURE COLUMNS
# ============================================================

NON_FEATURE_COLUMNS = {
    "mesh_file",
    "case_number",
    "gestation",
    "iugr",
    "followup_category",
    "face_label",
    "face_label_name",
}

feature_columns = [
    col
    for col in df.columns
    if col not in NON_FEATURE_COLUMNS
]


print(
    f"\nFeature count: {len(feature_columns)}"
)

print(
    "Features:"
)

for col in feature_columns:
    print(
        f"  - {col}"
    )


# ============================================================
# NUMERIC FEATURES ONLY
# ============================================================

X = df[
    feature_columns
].apply(
    pd.to_numeric,
    errors="coerce"
)

y = df[
    "face_label"
].astype(int)


# ============================================================
# SANITY CHECK
# ============================================================

if y.nunique() < 2:
    raise ValueError(
        "Need at least two classes."
    )

class_counts = (
    y.value_counts()
)

print(
    "\nNumeric feature matrix:",
    X.shape
)

print(
    "Target distribution:",
    class_counts.to_dict()
)


minority_count = int(
    class_counts.min()
)

if minority_count < N_SPLITS:
    print(
        f"\nWARNING: minority class has only "
        f"{minority_count} samples."
    )

    print(
        "Reducing CV folds to match minority class."
    )

    cv_splits = minority_count

else:
    cv_splits = N_SPLITS


# ============================================================
# MODELS
# ============================================================

logistic_pipeline = Pipeline(
    steps=[
        (
            "imputer",
            SimpleImputer(
                strategy="median"
            ),
        ),

        (
            "scaler",
            StandardScaler()
        ),

        (
            "classifier",
            LogisticRegression(
                max_iter=3000,
                class_weight="balanced",
                random_state=RANDOM_STATE,
            ),
        ),
    ]
)


rf_pipeline = Pipeline(
    steps=[
        (
            "imputer",
            SimpleImputer(
                strategy="median"
            ),
        ),

        (
            "classifier",
            RandomForestClassifier(
                n_estimators=500,
                max_depth=5,
                min_samples_leaf=3,
                class_weight="balanced",
                random_state=RANDOM_STATE,
                n_jobs=-1,
            ),
        ),
    ]
)


models = {
    "LogisticRegression": logistic_pipeline,
    "RandomForest": rf_pipeline,
}


# ============================================================
# CROSS VALIDATION
# ============================================================

cv = StratifiedKFold(
    n_splits=cv_splits,
    shuffle=True,
    random_state=RANDOM_STATE,
)


scoring = {
    "accuracy": "accuracy",
    "precision": "precision",
    "recall": "recall",
    "f1": "f1",
    "roc_auc": "roc_auc",
}


results = []


print("\n" + "=" * 70)
print("STRATIFIED CROSS-VALIDATION")
print("=" * 70)


for name, model in models.items():

    print(
        f"\nEvaluating: {name}"
    )

    cv_result = cross_validate(
        model,
        X,
        y,
        cv=cv,
        scoring=scoring,
        return_train_score=False,
        n_jobs=-1,
    )

    row = {
        "model": name,
    }

    for metric in scoring:

        values = cv_result[
            f"test_{metric}"
        ]

        row[
            f"{metric}_mean"
        ] = float(
            np.mean(values)
        )

        row[
            f"{metric}_std"
        ] = float(
            np.std(values)
        )

    results.append(
        row
    )

    print(
        f"Accuracy : "
        f"{row['accuracy_mean']:.4f} "
        f"+/- {row['accuracy_std']:.4f}"
    )

    print(
        f"Precision: "
        f"{row['precision_mean']:.4f} "
        f"+/- {row['precision_std']:.4f}"
    )

    print(
        f"Recall   : "
        f"{row['recall_mean']:.4f} "
        f"+/- {row['recall_std']:.4f}"
    )

    print(
        f"F1       : "
        f"{row['f1_mean']:.4f} "
        f"+/- {row['f1_std']:.4f}"
    )

    print(
        f"ROC-AUC  : "
        f"{row['roc_auc_mean']:.4f} "
        f"+/- {row['roc_auc_std']:.4f}"
    )


# ============================================================
# SAVE CV RESULTS
# ============================================================

results_df = pd.DataFrame(
    results
)

results_path = (
    OUTPUT_DIR
    / "face_3d_cv_results.csv"
)

results_df.to_csv(
    results_path,
    index=False
)


# ============================================================
# SELECT BEST MODEL
# ============================================================

best_index = (
    results_df[
        "roc_auc_mean"
    ].idxmax()
)

best_name = results_df.loc[
    best_index,
    "model"
]

best_model = models[
    best_name
]


print("\n" + "=" * 70)

print(
    f"BEST MODEL: {best_name}"
)

print("=" * 70)


# ============================================================
# FIT FINAL MODEL
# ============================================================

best_model.fit(
    X,
    y
)


# ============================================================
# TRAINING DATA PREDICTION
# ============================================================
# This is NOT a generalization metric.
# It is only a sanity check after fitting.

pred = best_model.predict(
    X
)

if hasattr(
    best_model,
    "predict_proba"
):

    probabilities = (
        best_model
        .predict_proba(X)[:, 1]
    )

else:

    probabilities = None


print("\nTraining-set sanity check:")

print(
    classification_report(
        y,
        pred,
        target_names=[
            "normal",
            "facial_abnormality",
        ],
        digits=4,
        zero_division=0,
    )
)


print(
    "Confusion matrix:"
)

print(
    confusion_matrix(
        y,
        pred
    )
)


if probabilities is not None:

    train_auc = roc_auc_score(
        y,
        probabilities
    )

    print(
        f"\nTraining ROC-AUC: "
        f"{train_auc:.4f}"
    )


# ============================================================
# SAVE MODEL
# ============================================================

import joblib


MODEL_PATH = (
    OUTPUT_DIR
    / "fetal_face_3d_classifier.joblib"
)

joblib.dump(
    best_model,
    MODEL_PATH
)


# ============================================================
# FEATURE LIST
# ============================================================

FEATURES_PATH = (
    OUTPUT_DIR
    / "feature_columns.txt"
)

with open(
    FEATURES_PATH,
    "w",
    encoding="utf-8"
) as file:

    for column in feature_columns:
        file.write(
            column + "\n"
        )


# ============================================================
# COMPLETE
# ============================================================

print("\n" + "=" * 70)
print("FETAL FACE 3D CLASSIFIER TRAINING COMPLETE")
print("=" * 70)

print(
    f"Best model          : {best_name}"
)

print(
    f"Cross-validation    : "
    f"{cv_splits}-fold stratified"
)

print(
    f"CV results          : {results_path}"
)

print(
    f"Model saved         : {MODEL_PATH}"
)

print(
    f"Feature list        : {FEATURES_PATH}"
)

print("=" * 70)