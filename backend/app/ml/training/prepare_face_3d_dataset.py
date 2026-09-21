from pathlib import Path
import csv
import re


ROOT = Path(
    r"D:\Fetal_Face_Inspect"
)

DATA_ZIP = (
    ROOT / "data_age_rescaled.zip"
)

OUTPUT_ROOT = Path(
    r"D:\Fetal_Face_3D"
)


print("=" * 70)
print("FETAL FACE 3D DATASET INSPECTION")
print("=" * 70)


# ============================================================
# BASIC CHECK
# ============================================================

if not DATA_ZIP.exists():
    raise FileNotFoundError(
        f"Nested dataset ZIP not found:\n{DATA_ZIP}"
    )


print(
    f"Dataset ZIP:\n{DATA_ZIP}"
)

print(
    f"Size MB: {DATA_ZIP.stat().st_size / (1024 * 1024):.2f}"
)


# ============================================================
# LIST VTK FILES INSIDE ZIP
# ============================================================

import zipfile


with zipfile.ZipFile(
    DATA_ZIP,
    "r"
) as archive:

    names = archive.namelist()


vtk_files = [
    name
    for name in names
    if name.lower().endswith(".vtk")
]


print(
    f"\nVTK files found: {len(vtk_files)}"
)


print("\nFirst 30 VTK files:")

for name in vtk_files[:30]:
    print(name)


# ============================================================
# EXTRACT VTK FILES
# ============================================================

OUTPUT_ROOT.mkdir(
    parents=True,
    exist_ok=True
)

EXTRACT_ROOT = (
    OUTPUT_ROOT / "meshes"
)

EXTRACT_ROOT.mkdir(
    parents=True,
    exist_ok=True
)


print(
    "\nExtracting VTK meshes..."
)


with zipfile.ZipFile(
    DATA_ZIP,
    "r"
) as archive:

    for name in vtk_files:

        archive.extract(
            name,
            EXTRACT_ROOT
        )


print(
    "VTK extraction complete."
)


# ============================================================
# FIND EXTRACTED FILES
# ============================================================

extracted = list(
    EXTRACT_ROOT.rglob("*.vtk")
)

print(
    f"\nExtracted VTK files: {len(extracted)}"
)


# ============================================================
# FILE ID PATTERN
# ============================================================

pattern = re.compile(
    r"m_(\d+)\.vtk",
    re.IGNORECASE
)

ids = []

for file in extracted:

    match = pattern.fullmatch(
        file.name
    )

    if match:
        ids.append(
            int(match.group(1))
        )


print(
    f"Numeric mesh IDs: {len(ids)}"
)

if ids:

    print(
        f"Minimum ID: {min(ids)}"
    )

    print(
        f"Maximum ID: {max(ids)}"
    )


# ============================================================
# OPTIONAL VTK LIBRARY CHECK
# ============================================================

try:

    import vtk

    print(
        "\nVTK Python package: AVAILABLE"
    )

    test_file = (
        extracted[0]
        if extracted
        else None
    )

    if test_file:

        print(
            f"\nInspecting:\n{test_file.name}"
        )

        reader = (
            vtk.vtkPolyDataReader()
        )

        reader.SetFileName(
            str(test_file)
        )

        reader.Update()

        mesh = (
            reader.GetOutput()
        )

        print(
            f"Points   : {mesh.GetNumberOfPoints()}"
        )

        print(
            f"Cells    : {mesh.GetNumberOfCells()}"
        )

        print(
            f"Polygons : {mesh.GetNumberOfPolys()}"
        )

        bounds = [
            0.0
        ] * 6

        mesh.GetBounds(
            bounds
        )

        print(
            f"Bounds   : {bounds}"
        )

except ImportError:

    print(
        "\nVTK Python package: NOT INSTALLED"
    )

    print(
        "Mesh structure inspection skipped."
    )


# ============================================================
# PATIENT DATABASE
# ============================================================

patient_csv = (
    ROOT / "Patient DB 2023.csv"
)

if patient_csv.exists():

    print(
        "\nPatient database found:"
    )

    print(
        patient_csv
    )

    with open(
        patient_csv,
        "r",
        encoding="utf-8-sig",
        errors="replace",
        newline=""
    ) as f:

        reader = csv.reader(
            f
        )

        rows = list(
            reader
        )

    print(
        f"Rows including header: {len(rows)}"
    )

    if rows:

        print(
            "Columns:"
        )

        print(
            rows[0]
        )

        print(
            "\nFirst 10 records:"
        )

        for row in rows[1:11]:

            print(
                row
            )

else:

    print(
        "\nPatient DB not found."
    )


# ============================================================
# COMPLETE
# ============================================================

print("\n" + "=" * 70)

print(
    "FETAL FACE 3D INSPECTION COMPLETE"
)

print(
    f"Output:\n{OUTPUT_ROOT}"
)

print("=" * 70)