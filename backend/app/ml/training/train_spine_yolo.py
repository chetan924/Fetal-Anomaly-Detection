from pathlib import Path
import shutil

from ultralytics import YOLO


# ============================================================
# CONFIG
# ============================================================

DATA_YAML = Path(
    r"D:\Fetal_Spine_YOLO\data.yaml"
)

MODEL_DIR = Path(
    r"D:\Fetal Anomaly Detection\backend\app\ml\models"
)

FINAL_MODEL = (
    MODEL_DIR / "fetal_spine_yolo.pt"
)

RUNS_DIR = Path(
    r"D:\Fetal_Spine_YOLO\runs"
)

MODEL_NAME = "yolov8n.pt"

EPOCHS = 30
IMAGE_SIZE = 640
BATCH_SIZE = 4
WORKERS = 0
PATIENCE = 8

DEVICE = "cpu"


# ============================================================
# VALIDATION
# ============================================================

if not DATA_YAML.exists():
    raise FileNotFoundError(
        f"data.yaml not found:\n{DATA_YAML}"
    )


MODEL_DIR.mkdir(
    parents=True,
    exist_ok=True
)

RUNS_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# CONFIG PRINT
# ============================================================

print("=" * 70)
print("FETAL SPINE YOLO TRAINING")
print("=" * 70)

print(f"Dataset     : {DATA_YAML}")
print(f"Base model  : {MODEL_NAME}")
print(f"Device      : {DEVICE}")
print(f"Image size  : {IMAGE_SIZE}")
print(f"Batch size  : {BATCH_SIZE}")
print(f"Epochs      : {EPOCHS}")
print(f"Workers     : {WORKERS}")
print(f"Patience    : {PATIENCE}")

print("=" * 70)


# ============================================================
# LOAD MODEL
# ============================================================

print("\nLoading YOLO model...")

model = YOLO(
    MODEL_NAME
)


# ============================================================
# TRAIN
# ============================================================

print("\nStarting training...\n")

results = model.train(

    data=str(
        DATA_YAML
    ),

    epochs=EPOCHS,

    imgsz=IMAGE_SIZE,

    batch=BATCH_SIZE,

    workers=WORKERS,

    device=DEVICE,

    patience=PATIENCE,

    project=str(
        RUNS_DIR
    ),

    name="fetal_spine_yolo",

    exist_ok=True,

    pretrained=True,

    optimizer="AdamW",

    lr0=0.001,

    weight_decay=0.0005,

    cos_lr=True,

    close_mosaic=5,

    cache=False,

    amp=False,

    verbose=True,

    plots=True,

    save=True,

    save_period=5,

    val=True,

    deterministic=True,
)


# ============================================================
# BEST MODEL
# ============================================================

best_model = (
    RUNS_DIR
    / "fetal_spine_yolo"
    / "weights"
    / "best.pt"
)

last_model = (
    RUNS_DIR
    / "fetal_spine_yolo"
    / "weights"
    / "last.pt"
)


print("\n" + "=" * 70)
print("TRAINING FINISHED")
print("=" * 70)

print(
    f"Best checkpoint:\n{best_model}"
)

print(
    f"Last checkpoint:\n{last_model}"
)


# ============================================================
# COPY BEST MODEL
# ============================================================

if best_model.exists():

    shutil.copy2(
        best_model,
        FINAL_MODEL
    )

    print(
        f"\nBest model copied to:\n{FINAL_MODEL}"
    )

else:

    raise FileNotFoundError(
        "Best YOLO checkpoint was not created."
    )


# ============================================================
# FINAL VALIDATION
# ============================================================

print("\nRunning final validation...")

best = YOLO(
    str(FINAL_MODEL)
)

metrics = best.val(
    data=str(DATA_YAML),
    imgsz=IMAGE_SIZE,
    batch=BATCH_SIZE,
    device=DEVICE,
    workers=WORKERS,
    verbose=True,
    plots=True,
)


# ============================================================
# METRICS
# ============================================================

try:

    print("\n" + "=" * 70)
    print("FINAL SPINE MODEL METRICS")
    print("=" * 70)

    print(
        f"mAP50     : {metrics.box.map50:.4f}"
    )

    print(
        f"mAP50-95  : {metrics.box.map:.4f}"
    )

    print(
        f"Precision : {metrics.box.mp:.4f}"
    )

    print(
        f"Recall    : {metrics.box.mr:.4f}"
    )

except Exception:

    print(
        "\nValidation completed, "
        "but metric fields could not be read."
    )


# ============================================================
# COMPLETE
# ============================================================

print("\n" + "=" * 70)

print(
    "FETAL SPINE YOLO TRAINING COMPLETE"
)

print(
    f"Model:\n{FINAL_MODEL}"
)

print("=" * 70)