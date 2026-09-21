from pathlib import Path
import csv
import math

import numpy as np
import vtk


# ============================================================
# CONFIG
# ============================================================

MESH_ROOT = Path(
    r"D:\Fetal_Face_3D\meshes"
)

PATIENT_CSV = Path(
    r"D:\Fetal_Face_Inspect\Patient DB 2023.csv"
)

OUTPUT_DIR = Path(
    r"D:\Fetal_Face_3D\features"
)

OUTPUT_CSV = (
    OUTPUT_DIR / "fetal_face_3d_features.csv"
)


# ============================================================
# SETUP
# ============================================================

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# HELPERS
# ============================================================

def read_patient_database(path: Path):
    records = {}

    with open(
        path,
        "r",
        encoding="utf-8-sig",
        errors="replace",
        newline=""
    ) as file:

        reader = csv.DictReader(
            file
        )

        for row in reader:

            case_number = (
                row.get("Case Number", "")
                .strip()
            )

            if not case_number:
                continue

            records[
                int(case_number)
            ] = row

    return records


def read_mesh(path: Path):
    reader = vtk.vtkPolyDataReader()

    reader.SetFileName(
        str(path)
    )

    reader.Update()

    mesh = reader.GetOutput()

    if mesh is None:
        raise RuntimeError(
            f"Could not read mesh: {path}"
        )

    return mesh


def get_points(mesh):
    points = mesh.GetPoints()

    if points is None:
        return np.empty(
            (0, 3),
            dtype=np.float64
        )

    output = np.empty(
        (points.GetNumberOfPoints(), 3),
        dtype=np.float64
    )

    for idx in range(
        points.GetNumberOfPoints()
    ):
        output[idx] = points.GetPoint(
            idx
        )

    return output


def safe_mean(values):
    if len(values) == 0:
        return 0.0

    return float(
        np.mean(values)
    )


def safe_std(values):
    if len(values) == 0:
        return 0.0

    return float(
        np.std(values)
    )


def euclidean(a, b):
    return float(
        np.linalg.norm(
            np.asarray(a)
            -
            np.asarray(b)
        )
    )


def principal_axis_features(points):
    """
    PCA-based geometric descriptors.
    """

    if len(points) < 3:
        return {
            "pca1_variance": 0.0,
            "pca2_variance": 0.0,
            "pca3_variance": 0.0,
            "pca1_ratio": 0.0,
            "pca2_ratio": 0.0,
            "pca3_ratio": 0.0,
        }

    centered = (
        points
        -
        np.mean(
            points,
            axis=0
        )
    )

    covariance = np.cov(
        centered,
        rowvar=False
    )

    eigenvalues = np.linalg.eigvalsh(
        covariance
    )

    eigenvalues = np.sort(
        eigenvalues
    )[::-1]

    total = float(
        np.sum(
            eigenvalues
        )
    )

    if total <= 0:
        ratios = [
            0.0,
            0.0,
            0.0,
        ]

    else:
        ratios = (
            eigenvalues
            / total
        )

    return {
        "pca1_variance": float(
            eigenvalues[0]
        ),
        "pca2_variance": float(
            eigenvalues[1]
        ),
        "pca3_variance": float(
            eigenvalues[2]
        ),
        "pca1_ratio": float(
            ratios[0]
        ),
        "pca2_ratio": float(
            ratios[1]
        ),
        "pca3_ratio": float(
            ratios[2]
        ),
    }


def mesh_features(mesh):
    points = get_points(
        mesh
    )

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
            "surface_area": 0.0,
            "volume": 0.0,
        }

    mins = np.min(
        points,
        axis=0
    )

    maxs = np.max(
        points,
        axis=0
    )

    bbox = (
        maxs - mins
    )

    centroid = np.mean(
        points,
        axis=0
    )

    radii = np.linalg.norm(
        points - centroid,
        axis=1
    )

    distance_min_max = euclidean(
        mins,
        maxs
    )

    # Surface area
    triangle_filter = (
        vtk.vtkTriangleFilter()
    )

    triangle_filter.SetInputData(
        mesh
    )

    triangle_filter.Update()

    mass_properties = (
        vtk.vtkMassProperties()
    )

    mass_properties.SetInputConnection(
        triangle_filter.GetOutputPort()
    )

    mass_properties.Update()

    surface_area = float(
        mass_properties.GetSurfaceArea()
    )

    volume = float(
        mass_properties.GetVolume()
    )

    features = {
        "num_points": int(
            mesh.GetNumberOfPoints()
        ),
        "num_cells": int(
            mesh.GetNumberOfCells()
        ),
        "num_polygons": int(
            mesh.GetNumberOfPolys()
        ),

        "bbox_x": float(
            bbox[0]
        ),
        "bbox_y": float(
            bbox[1]
        ),
        "bbox_z": float(
            bbox[2]
        ),

        "bbox_volume": float(
            bbox[0]
            * bbox[1]
            * bbox[2]
        ),

        "centroid_x": float(
            centroid[0]
        ),
        "centroid_y": float(
            centroid[1]
        ),
        "centroid_z": float(
            centroid[2]
        ),

        "distance_min_max": (
            distance_min_max
        ),

        "point_radius_mean": (
            safe_mean(radii)
        ),

        "point_radius_std": (
            safe_std(radii)
        ),

        "point_radius_min": float(
            np.min(radii)
        ),

        "point_radius_max": float(
            np.max(radii)
        ),

        "surface_area": (
            surface_area
        ),

        "volume": volume,
    }

    features.update(
        principal_axis_features(
            points
        )
    )

    return features


# ============================================================
# LOAD PATIENT DATABASE
# ============================================================

print("=" * 70)
print("FETAL FACE 3D FEATURE EXTRACTION")
print("=" * 70)

if not MESH_ROOT.exists():
    raise FileNotFoundError(
        f"Mesh directory not found:\n{MESH_ROOT}"
    )

if not PATIENT_CSV.exists():
    raise FileNotFoundError(
        f"Patient database not found:\n{PATIENT_CSV}"
    )


patients = read_patient_database(
    PATIENT_CSV
)

print(
    f"Patient records loaded: {len(patients)}"
)


# ============================================================
# FIND MESHES
# ============================================================

mesh_files = sorted(
    MESH_ROOT.rglob(
        "*.vtk"
    )
)

print(
    f"Meshes found: {len(mesh_files)}"
)


if not mesh_files:
    raise RuntimeError(
        "No VTK meshes found."
    )


# ============================================================
# EXTRACT FEATURES
# ============================================================

rows = []

failed = 0

for index, mesh_path in enumerate(
    mesh_files,
    start=1
):

    print(
        f"\rProcessing "
        f"{index}/{len(mesh_files)}: "
        f"{mesh_path.name}",
        end=""
    )

    try:

        mesh = read_mesh(
            mesh_path
        )

        features = mesh_features(
            mesh
        )

        # m_012.vtk -> 12
        stem = mesh_path.stem

        try:
            case_number = int(
                stem.split("_")[-1]
            )

        except Exception:
            case_number = None

        patient = (
            patients.get(
                case_number,
                {}
            )
            if case_number is not None
            else {}
        )

        row = {
            "mesh_file": mesh_path.name,
            "case_number": (
                case_number
                if case_number is not None
                else ""
            ),
            "gestation": patient.get(
                "Gestation",
                ""
            ),
            "iugr": patient.get(
                "IUGR",
                ""
            ),
            "followup_category": patient.get(
                "1 year PN f/u – Category",
                ""
            ),
        }

        row.update(
            features
        )

        rows.append(
            row
        )

    except Exception as exc:

        failed += 1

        print(
            f"\nWARNING: "
            f"{mesh_path.name}: "
            f"{exc}"
        )


print()


# ============================================================
# WRITE CSV
# ============================================================

if not rows:
    raise RuntimeError(
        "No feature rows were generated."
    )


fieldnames = list(
    rows[0].keys()
)


with open(
    OUTPUT_CSV,
    "w",
    encoding="utf-8",
    newline=""
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=fieldnames
    )

    writer.writeheader()

    writer.writerows(
        rows
    )


# ============================================================
# SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("FETAL FACE 3D FEATURE EXTRACTION COMPLETE")
print("=" * 70)

print(
    f"Meshes processed : {len(rows)}"
)

print(
    f"Failed meshes    : {failed}"
)

print(
    f"Output CSV       : {OUTPUT_CSV}"
)

print(
    f"Feature columns  : {len(fieldnames)}"
)

print("\nFeatures generated include:")

for name in fieldnames:
    print(
        f"  - {name}"
    )

print("=" * 70)