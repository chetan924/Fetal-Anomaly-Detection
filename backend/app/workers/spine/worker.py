from io import BytesIO
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from PIL import Image
from ultralytics import YOLO


# ============================================================
# CONFIGURATION
# ============================================================

MODEL_PATH = Path(
    r"D:\Fetal Anomaly Detection\backend\app\ml\models\fetal_spine_yolo.pt"
)

WORKER_NAME = "spine"
MODEL_NAME = "fetal_spine_yolo"

CONFIDENCE_THRESHOLD = 0.25


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="FetalAI Spine Worker",
    version="1.0.0",
)


# ============================================================
# MODEL
# ============================================================

model = None


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
def load_model():

    global model

    print("=" * 70)
    print("STARTING SPINE WORKER")
    print("=" * 70)

    print(
        "Model:",
        MODEL_PATH,
    )

    if not MODEL_PATH.exists():

        raise RuntimeError(
            f"Spine model not found: {MODEL_PATH}"
        )

    model = YOLO(
        str(MODEL_PATH)
    )

    print(
        "Spine model loaded successfully."
    )

    print(
        "Worker:",
        WORKER_NAME,
    )

    print("=" * 70)


# ============================================================
# HEALTH
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
# PREDICT
# ============================================================

@app.post("/predict")
async def predict(
    file: UploadFile = File(...),
):

    if model is None:

        raise HTTPException(
            status_code=503,
            detail="Spine model is not loaded.",
        )

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="Filename is required.",
        )

    content_type = (
        file.content_type or ""
    ).split(";")[0].strip().lower()

    if not content_type.startswith("image/"):

        raise HTTPException(
            status_code=400,
            detail="Only image files are supported.",
        )

    try:

        raw = await file.read()

        if not raw:

            raise HTTPException(
                status_code=400,
                detail="Uploaded image is empty.",
            )

        image = Image.open(
            BytesIO(raw)
        ).convert("RGB")

        results = model.predict(
            source=image,
            conf=CONFIDENCE_THRESHOLD,
            device="cpu",
            verbose=False,
        )

        result = results[0]

        detections = []

        if result.boxes is not None:

            names = result.names

            for box in result.boxes:

                class_id = int(
                    box.cls[0]
                    .cpu()
                    .item()
                )

                confidence = float(
                    box.conf[0]
                    .cpu()
                    .item()
                )

                xyxy = (
                    box.xyxy[0]
                    .cpu()
                    .numpy()
                    .tolist()
                )

                if hasattr(names, "get"):

                    class_name = names.get(
                        class_id,
                        str(class_id),
                    )

                else:

                    class_name = str(
                        names[class_id]
                    )

                detections.append(
                    {
                        "class_id": class_id,
                        "class_name": class_name,
                        "confidence": round(
                            confidence,
                            6,
                        ),
                        "bbox": [
                            round(
                                float(value),
                                2,
                            )
                            for value in xyxy
                        ],
                    }
                )

        return {
            "status": "success",
            "worker": WORKER_NAME,
            "model": MODEL_NAME,
            "image": {
                "filename": file.filename,
                "width": image.width,
                "height": image.height,
            },
            "detections": detections,
            "detection_count": len(
                detections
            ),
        }

    except HTTPException:
        raise

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Spine inference failed: {exc}"
            ),
        ) from exc
