from io import BytesIO

from fastapi import FastAPI, File, HTTPException, UploadFile
from PIL import Image

from app.ml.predict_plane import predict_plane


app = FastAPI(
    title="FetalAI Plane Worker",
    version="1.0.0",
)


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "worker": "plane",
        "model": "fetal_plane_efficientnet_b0",
        "model_loaded": True,
    }


@app.post("/predict")
async def predict(
    file: UploadFile = File(...)
):
    try:
        raw = await file.read()

        if not raw:
            raise HTTPException(
                status_code=400,
                detail="Empty image.",
            )

        image = Image.open(
            BytesIO(raw)
        ).convert("RGB")

        result = predict_plane(
            image
        )

        return {
            "status": "success",
            "worker": "plane",
            "model": "fetal_plane_efficientnet_b0",
            "result": result,
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Plane inference failed: {exc}",
        )
