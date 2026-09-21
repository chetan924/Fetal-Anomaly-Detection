from io import BytesIO
from pathlib import Path
import gc

import numpy as np
import torch
import torch.nn as nn

from fastapi import (
    FastAPI,
    File,
    HTTPException,
    UploadFile,
)

from PIL import Image


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parents[2]
    / "ml"
)

MODEL_PATH = (
    BASE_DIR
    / "models"
    / "fetal_lung_unet_v2.pth"
)

WORKER_NAME = "lung"
MODEL_NAME = "fetal_lung_unet_v2"

DEFAULT_IMAGE_SIZE = 256
DEFAULT_THRESHOLD = 0.5

DEVICE = torch.device("cpu")

NORM_MEAN = torch.tensor(
    [0.485, 0.456, 0.406],
    dtype=torch.float32,
).view(3, 1, 1)

NORM_STD = torch.tensor(
    [0.229, 0.224, 0.225],
    dtype=torch.float32,
).view(3, 1, 1)


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="FetalAI Lung Worker",
    version="1.0.0",
)


# ============================================================
# GLOBAL MODEL STATE
# ============================================================

model = None
IMAGE_SIZE = DEFAULT_IMAGE_SIZE
BEST_VAL_DICE = None
TEST_HARD_DICE = None
TEST_IOU = None


# ============================================================
# CONV BLOCK
# ============================================================

class ConvBlock(nn.Module):

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
    ):
        super().__init__()

        self.block = nn.Sequential(
            nn.Conv2d(
                in_channels,
                out_channels,
                kernel_size=3,
                padding=1,
                bias=False,
            ),
            nn.GroupNorm(
                num_groups=8,
                num_channels=out_channels,
            ),
            nn.ReLU(
                inplace=True,
            ),
            nn.Conv2d(
                out_channels,
                out_channels,
                kernel_size=3,
                padding=1,
                bias=False,
            ),
            nn.GroupNorm(
                num_groups=8,
                num_channels=out_channels,
            ),
            nn.ReLU(
                inplace=True,
            ),
        )

    def forward(
        self,
        x: torch.Tensor,
    ) -> torch.Tensor:
        return self.block(x)


# ============================================================
# U-NET V2
# ============================================================

class UNetV2(nn.Module):

    def __init__(self):
        super().__init__()

        # Encoder
        self.enc1 = ConvBlock(3, 32)
        self.enc2 = ConvBlock(32, 64)
        self.enc3 = ConvBlock(64, 128)
        self.enc4 = ConvBlock(128, 256)

        self.pool = nn.MaxPool2d(2)

        # Bottleneck
        self.bottleneck = ConvBlock(256, 384)

        # Decoder
        self.up4 = nn.ConvTranspose2d(
            384,
            256,
            kernel_size=2,
            stride=2,
        )
        self.dec4 = ConvBlock(512, 256)

        self.up3 = nn.ConvTranspose2d(
            256,
            128,
            kernel_size=2,
            stride=2,
        )
        self.dec3 = ConvBlock(256, 128)

        self.up2 = nn.ConvTranspose2d(
            128,
            64,
            kernel_size=2,
            stride=2,
        )
        self.dec2 = ConvBlock(128, 64)

        self.up1 = nn.ConvTranspose2d(
            64,
            32,
            kernel_size=2,
            stride=2,
        )
        self.dec1 = ConvBlock(64, 32)

        # Output head
        self.head = nn.Conv2d(
            32,
            1,
            kernel_size=1,
        )

    def forward(
        self,
        x: torch.Tensor,
    ) -> torch.Tensor:
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool(e1))
        e3 = self.enc3(self.pool(e2))
        e4 = self.enc4(self.pool(e3))

        b = self.bottleneck(self.pool(e4))

        d4 = self.up4(b)
        d4 = torch.cat([d4, e4], dim=1)
        d4 = self.dec4(d4)

        d3 = self.up3(d4)
        d3 = torch.cat([d3, e3], dim=1)
        d3 = self.dec3(d3)

        d2 = self.up2(d3)
        d2 = torch.cat([d2, e2], dim=1)
        d2 = self.dec2(d2)

        d1 = self.up1(d2)
        d1 = torch.cat([d1, e1], dim=1)
        d1 = self.dec1(d1)

        return self.head(d1)


# ============================================================
# PREPROCESS IMAGE
# ============================================================

def preprocess_image(
    image: Image.Image,
) -> torch.Tensor:
    image = image.convert("RGB")
    image = image.resize(
        (IMAGE_SIZE, IMAGE_SIZE),
        Image.Resampling.BILINEAR,
    )

    image_array = np.asarray(
        image,
        dtype=np.float32,
    ) / 255.0

    # HWC -> CHW
    image_array = np.transpose(
        image_array,
        (2, 0, 1),
    )

    tensor = torch.from_numpy(
        image_array
    )

    tensor = (tensor - NORM_MEAN) / NORM_STD
    tensor = tensor.unsqueeze(0)

    return tensor.to(DEVICE)


# ============================================================
# MODEL LOADING
# ============================================================

def load_model():
    global model
    global IMAGE_SIZE
    global BEST_VAL_DICE
    global TEST_HARD_DICE
    global TEST_IOU

    print()
    print("=" * 70)
    print("STARTING LUNG WORKER")
    print("=" * 70)
    print("Model path:", MODEL_PATH)

    if not MODEL_PATH.exists():
        raise RuntimeError(
            f"Lung model checkpoint not found: {MODEL_PATH}"
        )

    checkpoint = torch.load(
        MODEL_PATH,
        map_location=DEVICE,
        weights_only=False,
    )

    if not isinstance(checkpoint, dict):
        raise RuntimeError(
            "Lung checkpoint must be a dictionary."
        )

    if "model_state_dict" not in checkpoint:
        raise RuntimeError(
            "Lung checkpoint does not contain 'model_state_dict'."
        )

    IMAGE_SIZE = int(
        checkpoint.get(
            "image_size",
            DEFAULT_IMAGE_SIZE,
        )
    )

    BEST_VAL_DICE = checkpoint.get("best_val_dice", None)
    TEST_HARD_DICE = checkpoint.get("test_hard_dice", None)
    TEST_IOU = checkpoint.get("test_iou", None)

    loaded_model = UNetV2()
    loaded_model.load_state_dict(checkpoint["model_state_dict"])
    loaded_model = loaded_model.to(DEVICE)
    loaded_model.eval()

    for parameter in loaded_model.parameters():
        parameter.requires_grad = False

    model = loaded_model

    del checkpoint
    gc.collect()

    print("Device          :", DEVICE)
    print("Image size      :", IMAGE_SIZE)
    print("Architecture    :", "UNetV2 (GroupNorm)")
    print("Best Val Dice   :", BEST_VAL_DICE)
    print("Test Hard Dice  :", TEST_HARD_DICE)
    print("Test IoU        :", TEST_IOU)
    print("Lung UNetV2 loaded successfully.")
    print("Worker          :", WORKER_NAME)
    print("=" * 70)


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
def startup():
    load_model()


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "worker": WORKER_NAME,
        "model": MODEL_NAME,
        "model_loaded": (model is not None),
        "device": str(DEVICE),
        "image_size": IMAGE_SIZE,
        "best_val_dice": BEST_VAL_DICE,
        "test_hard_dice": TEST_HARD_DICE,
        "test_iou": TEST_IOU,
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
            detail="Lung model is not loaded.",
        )

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required.",
        )

    content_type = (file.content_type or "").split(";")[0].strip().lower()

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

        image = Image.open(BytesIO(raw)).convert("RGB")
        original_width = image.width
        original_height = image.height

        tensor = preprocess_image(image)

        with torch.inference_mode():
            logits = model(tensor)
            probs = torch.sigmoid(logits)

        probability_mask = probs[0, 0].cpu().numpy()
        binary_mask = probability_mask >= DEFAULT_THRESHOLD

        mask_pixels = int(binary_mask.sum())
        total_pixels = int(binary_mask.size)

        mask_ratio = (
            mask_pixels / total_pixels
            if total_pixels > 0
            else 0.0
        )

        mean_probability = float(probability_mask.mean())
        max_probability = float(probability_mask.max())
        min_probability = float(probability_mask.min())

        bbox = None
        if mask_pixels > 0:
            ys, xs = np.where(binary_mask)
            x_min = int(xs.min())
            y_min = int(ys.min())
            x_max = int(xs.max())
            y_max = int(ys.max())

            bbox = {
                "x_min": x_min,
                "y_min": y_min,
                "x_max": x_max,
                "y_max": y_max,
                "width": x_max - x_min + 1,
                "height": y_max - y_min + 1,
            }

        mask_image = Image.fromarray(
            (binary_mask.astype(np.uint8) * 255),
            mode="L",
        )

        mask_image = mask_image.resize(
            (original_width, original_height),
            resample=Image.NEAREST,
        )

        safe_name = Path(file.filename).stem
        mask_filename = f"{safe_name}_lung_mask.png"

        mask_output_dir = (
            BASE_DIR.parent.parent
            / "storage"
            / "lung_masks"
        )
        mask_output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        mask_path = mask_output_dir / mask_filename
        mask_image.save(mask_path)

        mask_url = f"/storage/lung_masks/{mask_filename}"

        del tensor
        del logits
        del probs
        del probability_mask
        del binary_mask
        gc.collect()

        return {
            "status": "success",
            "worker": WORKER_NAME,
            "model": MODEL_NAME,
            "image": {
                "filename": file.filename,
                "width": original_width,
                "height": original_height,
            },
            "segmentation": {
                "threshold": DEFAULT_THRESHOLD,
                "mask_pixels": mask_pixels,
                "mask_ratio": round(mask_ratio, 6),
                "mean_probability": round(mean_probability, 6),
                "max_probability": round(max_probability, 6),
                "min_probability": round(min_probability, 6),
                "bbox": bbox,
                "mask_path": str(mask_path),
                "mask_url": mask_url,
            },
            "validation": {
                "best_val_dice": BEST_VAL_DICE,
                "test_hard_dice": TEST_HARD_DICE,
                "test_iou": TEST_IOU,
            },
            "medical_disclaimer": (
                "This segmentation result is an AI research output "
                "and is not a clinical diagnosis."
            ),
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Lung inference failed: {exc}",
        ) from exc

