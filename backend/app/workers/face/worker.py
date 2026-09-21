import io
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, File, HTTPException, UploadFile
import joblib
import numpy as np
import pandas as pd
import vtk


# ============================================================
# CONFIGURATION
# ============================================================

_DEFAULT_MODEL = Path(__file__).resolve().parents[2] / "ml" / "models" / "fetal_face_3d_classifier.joblib"
_DEFAULT_FEATURES = Path(__file__).resolve().parents[2] / "ml" / "models" / "feature_columns.txt"
_LEGACY_MODEL = Path(r"D:\Fetal_Face_3D\models\fetal_face_3d_classifier.joblib")
_LEGACY_FEATURES = Path(r"D:\Fetal_Face_3D\models\feature_columns.txt")

MODEL_PATH = Path(os.getenv("FACE_MODEL_PATH", str(_DEFAULT_MODEL if _DEFAULT_MODEL.exists() else _LEGACY_MODEL)))
FEATURES_PATH = Path(os.getenv("FACE_FEATURES_PATH", str(_DEFAULT_FEATURES if _DEFAULT_FEATURES.exists() else _LEGACY_FEATURES)))

WORKER_NAME = "face"
MODEL_NAME = "fetal_face_3d_classifier"


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="FetalAI Face 3D Worker",
    version="1.0.0",
)

model = None
feature_columns: List[str] = []


# ============================================================
# FEATURE EXTRACTION HELPERS
# ============================================================

def safe_mean(values):
    if len(values) == 0:
        return 0.0
    return float(np.mean(values))


def safe_std(values):
    if len(values) == 0:
        return 0.0
    return float(np.std(values))


def euclidean(a, b):
    return float(np.linalg.norm(np.asarray(a) - np.asarray(b)))


def get_points(mesh):
    points = mesh.GetPoints()
    if points is None:
        return np.empty((0, 3), dtype=np.float64)

    n_pts = points.GetNumberOfPoints()
    output = np.empty((n_pts, 3), dtype=np.float64)
    for idx in range(n_pts):
        output[idx] = points.GetPoint(idx)
    return output


def principal_axis_features(points):
    if len(points) < 3:
        return {
            "pca1_variance": 0.0,
            "pca2_variance": 0.0,
            "pca3_variance": 0.0,
            "pca1_ratio": 0.0,
            "pca2_ratio": 0.0,
            "pca3_ratio": 0.0,
        }

    centered = points - np.mean(points, axis=0)
    covariance = np.cov(centered, rowvar=False)
    eigenvalues = np.linalg.eigvalsh(covariance)
    eigenvalues = np.sort(eigenvalues)[::-1]
    total = float(np.sum(eigenvalues))

    if total <= 0:
        ratios = [0.0, 0.0, 0.0]
    else:
        ratios = eigenvalues / total

    return {
        "pca1_variance": float(eigenvalues[0]),
        "pca2_variance": float(eigenvalues[1]),
        "pca3_variance": float(eigenvalues[2]),
        "pca1_ratio": float(ratios[0]),
        "pca2_ratio": float(ratios[1]),
        "pca3_ratio": float(ratios[2]),
    }


def extract_mesh_features(mesh) -> Dict[str, Any]:
    points = get_points(mesh)
    if len(points) == 0:
        return {
            "num_points": 0,
            "num_cells": 0,
            "num_polygons": 0,
            "bbox_x": 0.0,
            "bbox_y": 0.0,
            "bbox_z": 0.0,
            "bbox_volume": 0.0,
            "centroid_x": 0.0,
            "centroid_y": 0.0,
            "centroid_z": 0.0,
            "distance_min_max": 0.0,
            "point_radius_mean": 0.0,
            "point_radius_std": 0.0,
            "point_radius_min": 0.0,
            "point_radius_max": 0.0,
            "surface_area": 0.0,
            "volume": 0.0,
            "pca1_variance": 0.0,
            "pca2_variance": 0.0,
            "pca3_variance": 0.0,
            "pca1_ratio": 0.0,
            "pca2_ratio": 0.0,
            "pca3_ratio": 0.0,
        }

    mins = np.min(points, axis=0)
    maxs = np.max(points, axis=0)
    bbox = maxs - mins
    centroid = np.mean(points, axis=0)
    radii = np.linalg.norm(points - centroid, axis=1)
    distance_min_max = euclidean(mins, maxs)

    # Surface area & Volume via vtkMassProperties
    surface_area = 0.0
    volume = 0.0
    try:
        triangle_filter = vtk.vtkTriangleFilter()
        triangle_filter.SetInputData(mesh)
        triangle_filter.Update()

        mass_properties = vtk.vtkMassProperties()
        mass_properties.SetInputConnection(triangle_filter.GetOutputPort())
        mass_properties.Update()

        surface_area = float(mass_properties.GetSurfaceArea())
        volume = float(mass_properties.GetVolume())
    except Exception:
        pass

    features = {
        "num_points": int(mesh.GetNumberOfPoints()),
        "num_cells": int(mesh.GetNumberOfCells()),
        "num_polygons": int(mesh.GetNumberOfPolys()),
        "bbox_x": float(bbox[0]),
        "bbox_y": float(bbox[1]),
        "bbox_z": float(bbox[2]),
        "bbox_volume": float(bbox[0] * bbox[1] * bbox[2]),
        "centroid_x": float(centroid[0]),
        "centroid_y": float(centroid[1]),
        "centroid_z": float(centroid[2]),
        "distance_min_max": distance_min_max,
        "point_radius_mean": safe_mean(radii),
        "point_radius_std": safe_std(radii),
        "point_radius_min": float(np.min(radii)) if len(radii) > 0 else 0.0,
        "point_radius_max": float(np.max(radii)) if len(radii) > 0 else 0.0,
        "surface_area": surface_area,
        "volume": volume,
    }

    features.update(principal_axis_features(points))
    return features


# ============================================================
# LIFECYCLE & STARTUP
# ============================================================

@app.on_event("startup")
def startup():
    global model, feature_columns
    print("=" * 70)
    print("STARTING FETAL FACE 3D WORKER (Python 3.11 + VTK)")
    print("=" * 70)

    if not MODEL_PATH.exists():
        raise RuntimeError(f"Face model not found at: {MODEL_PATH}")

    model = joblib.load(MODEL_PATH)
    print(f"Face 3D model loaded from: {MODEL_PATH}")

    if FEATURES_PATH.exists():
        with open(FEATURES_PATH, "r", encoding="utf-8") as f:
            feature_columns = [line.strip() for line in f if line.strip()]
        print(f"Loaded {len(feature_columns)} feature columns from: {FEATURES_PATH}")
    else:
        print("Warning: feature_columns.txt not found. Using default extracted feature keys.")
        feature_columns = []


# ============================================================
# HEALTH ENDPOINT
# ============================================================

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "worker": WORKER_NAME,
        "model": MODEL_NAME,
        "model_loaded": model is not None,
    }


# ============================================================
# PREDICT ENDPOINT
# ============================================================

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    if model is None:
        raise HTTPException(status_code=503, detail="Face 3D model is not loaded.")

    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Uploaded VTK file is empty.")

    # Write temporarily to load via VTK polydata reader
    with tempfile.NamedTemporaryFile(suffix=".vtk", delete=False) as tmp:
        tmp.write(raw_bytes)
        tmp_path = tmp.name

    try:
        reader = vtk.vtkPolyDataReader()
        reader.SetFileName(tmp_path)
        reader.Update()
        mesh = reader.GetOutput()

        if mesh is None or mesh.GetNumberOfPoints() == 0:
            raise HTTPException(
                status_code=400,
                detail="Invalid or empty VTK mesh polydata structure."
            )

        features = extract_mesh_features(mesh)

        cols = feature_columns if feature_columns else list(features.keys())
        data_dict = {c: [features.get(c, 0.0)] for c in cols}
        df_x = pd.DataFrame(data_dict)

        pred_class_idx = int(model.predict(df_x)[0])
        if hasattr(model, "predict_proba"):
            probs = model.predict_proba(df_x)[0]
            prob_dict = {
                "normal": round(float(probs[0]), 4),
                "facial_abnormality": round(float(probs[1]), 4) if len(probs) > 1 else 0.0,
            }
            conf = round(float(probs[pred_class_idx]), 4)
        else:
            prob_dict = {"normal": 0.5, "facial_abnormality": 0.5}
            conf = 0.90

        label_name = "facial_abnormality" if pred_class_idx == 1 else "normal"

        return {
            "status": "success",
            "worker": WORKER_NAME,
            "model": MODEL_NAME,
            "predicted_class": label_name,
            "confidence": conf,
            "probabilities": prob_dict,
            "mesh_statistics": {
                "num_points": int(mesh.GetNumberOfPoints()),
                "num_cells": int(mesh.GetNumberOfCells()),
                "bbox_x": round(float(features.get("bbox_x", 0.0)), 2),
                "bbox_y": round(float(features.get("bbox_y", 0.0)), 2),
                "bbox_z": round(float(features.get("bbox_z", 0.0)), 2),
                "surface_area": round(float(features.get("surface_area", 0.0)), 2),
                "volume": round(float(features.get("volume", 0.0)), 2),
            },
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Face 3D inference failed: {exc}"
        ) from exc
    finally:
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
