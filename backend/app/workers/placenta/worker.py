from io import BytesIO
from pathlib import Path
import gc

import numpy as np
import torch

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
    / "fetal_placenta_unet_best.pt"
)

WORKER_NAME = "placenta"
MODEL_NAME = "fetal_placenta_unet"

DEFAULT_IMAGE_SIZE = 256
DEFAULT_THRESHOLD = 0.5

DEVICE = torch.device("cpu")


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="FetalAI Placenta Worker",
    version="1.0.0",
)


# ============================================================
# GLOBAL MODEL STATE
# ============================================================

model = None

IMAGE_SIZE = DEFAULT_IMAGE_SIZE

BEST_VAL_DICE = None


# ============================================================
# DOUBLE CONVOLUTION
# ============================================================

class DoubleConv(torch.nn.Module):

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
    ):

        super().__init__()

        self.block = torch.nn.Sequential(

            torch.nn.Conv2d(
                in_channels,
                out_channels,
                kernel_size=3,
                padding=1,
                bias=False,
            ),

            torch.nn.BatchNorm2d(
                out_channels
            ),

            torch.nn.ReLU(
                inplace=True
            ),

            torch.nn.Conv2d(
                out_channels,
                out_channels,
                kernel_size=3,
                padding=1,
                bias=False,
            ),

            torch.nn.BatchNorm2d(
                out_channels
            ),

            torch.nn.ReLU(
                inplace=True
            ),
        )


    def forward(
        self,
        x,
    ):

        return self.block(
            x
        )


# ============================================================
# U-NET
# ============================================================

class UNet(torch.nn.Module):

    def __init__(
        self,
        in_channels: int = 3,
        out_channels: int = 1,
    ):

        super().__init__()


        # ----------------------------------------------------
        # Encoder
        # ----------------------------------------------------

        self.enc1 = DoubleConv(
            in_channels,
            32,
        )

        self.pool1 = torch.nn.MaxPool2d(
            kernel_size=2
        )


        self.enc2 = DoubleConv(
            32,
            64,
        )

        self.pool2 = torch.nn.MaxPool2d(
            kernel_size=2
        )


        self.enc3 = DoubleConv(
            64,
            128,
        )

        self.pool3 = torch.nn.MaxPool2d(
            kernel_size=2
        )


        self.enc4 = DoubleConv(
            128,
            256,
        )

        self.pool4 = torch.nn.MaxPool2d(
            kernel_size=2
        )


        # ----------------------------------------------------
        # Bottleneck
        # ----------------------------------------------------

        self.bottleneck = DoubleConv(
            256,
            512,
        )


        # ----------------------------------------------------
        # Decoder
        # ----------------------------------------------------

        self.up4 = torch.nn.ConvTranspose2d(
            512,
            256,
            kernel_size=2,
            stride=2,
        )

        self.dec4 = DoubleConv(
            512,
            256,
        )


        self.up3 = torch.nn.ConvTranspose2d(
            256,
            128,
            kernel_size=2,
            stride=2,
        )

        self.dec3 = DoubleConv(
            256,
            128,
        )


        self.up2 = torch.nn.ConvTranspose2d(
            128,
            64,
            kernel_size=2,
            stride=2,
        )

        self.dec2 = DoubleConv(
            128,
            64,
        )


        self.up1 = torch.nn.ConvTranspose2d(
            64,
            32,
            kernel_size=2,
            stride=2,
        )

        self.dec1 = DoubleConv(
            64,
            32,
        )


        # ----------------------------------------------------
        # Final layer
        # ----------------------------------------------------

        self.final = torch.nn.Conv2d(
            32,
            out_channels,
            kernel_size=1,
        )


    def forward(
        self,
        x,
    ):

        # ----------------------------------------------------
        # Encoder
        # ----------------------------------------------------

        e1 = self.enc1(
            x
        )

        e2 = self.enc2(
            self.pool1(e1)
        )

        e3 = self.enc3(
            self.pool2(e2)
        )

        e4 = self.enc4(
            self.pool3(e3)
        )

        b = self.bottleneck(
            self.pool4(e4)
        )


        # ----------------------------------------------------
        # Decoder
        # ----------------------------------------------------

        d4 = self.up4(
            b
        )

        d4 = torch.cat(
            [
                d4,
                e4,
            ],
            dim=1,
        )

        d4 = self.dec4(
            d4
        )


        d3 = self.up3(
            d4
        )

        d3 = torch.cat(
            [
                d3,
                e3,
            ],
            dim=1,
        )

        d3 = self.dec3(
            d3
        )


        d2 = self.up2(
            d3
        )

        d2 = torch.cat(
            [
                d2,
                e2,
            ],
            dim=1,
        )

        d2 = self.dec2(
            d2
        )


        d1 = self.up1(
            d2
        )

        d1 = torch.cat(
            [
                d1,
                e1,
            ],
            dim=1,
        )

        d1 = self.dec1(
            d1
        )


        output = self.final(
            d1
        )


        return torch.sigmoid(
            output
        )


# ============================================================
# PREPROCESS IMAGE
# ============================================================

def preprocess_image(
    image: Image.Image,
) -> torch.Tensor:

    image = image.convert(
        "RGB"
    )

    image = image.resize(
        (
            IMAGE_SIZE,
            IMAGE_SIZE,
        )
    )

    image_array = np.asarray(
        image,
        dtype=np.float32,
    )

    image_array = (
        image_array
        / 255.0
    )

    # HWC -> CHW

    image_array = np.transpose(
        image_array,
        (
            2,
            0,
            1,
        ),
    )

    tensor = torch.from_numpy(
        image_array
    )

    tensor = tensor.unsqueeze(
        0
    )

    return tensor.to(
        DEVICE
    )


# ============================================================
# MODEL LOADING
# ============================================================

def load_model():

    global model
    global IMAGE_SIZE
    global BEST_VAL_DICE


    print()
    print("=" * 70)
    print("STARTING PLACENTA WORKER")
    print("=" * 70)


    print(
        "Model:",
        MODEL_PATH,
    )


    if not MODEL_PATH.exists():

        raise RuntimeError(
            "Placenta model not found: "
            f"{MODEL_PATH}"
        )


    # --------------------------------------------------------
    # Load checkpoint
    # --------------------------------------------------------

    checkpoint = torch.load(
        MODEL_PATH,
        map_location=DEVICE,
        weights_only=False,
    )


    if not isinstance(
        checkpoint,
        dict,
    ):

        raise RuntimeError(
            "Placenta checkpoint must be a dictionary."
        )


    if (
        "model_state_dict"
        not in checkpoint
    ):

        raise RuntimeError(
            "Placenta checkpoint does not contain "
            "'model_state_dict'."
        )


    # --------------------------------------------------------
    # Metadata
    # --------------------------------------------------------

    IMAGE_SIZE = int(
        checkpoint.get(
            "image_size",
            DEFAULT_IMAGE_SIZE,
        )
    )


    BEST_VAL_DICE = checkpoint.get(
        "best_val_dice",
        None,
    )


    # --------------------------------------------------------
    # Build EXACT training architecture
    # --------------------------------------------------------

    loaded_model = UNet(
        in_channels=3,
        out_channels=1,
    )


    # --------------------------------------------------------
    # Load trained weights
    # --------------------------------------------------------

    loaded_model.load_state_dict(
        checkpoint[
            "model_state_dict"
        ]
    )


    loaded_model = loaded_model.to(
        DEVICE
    )


    loaded_model.eval()


    # --------------------------------------------------------
    # Disable gradients
    # --------------------------------------------------------

    for parameter in loaded_model.parameters():

        parameter.requires_grad = False


    model = loaded_model


    del checkpoint

    gc.collect()


    print(
        "Device:",
        DEVICE,
    )

    print(
        "Image size:",
        IMAGE_SIZE,
    )

    print(
        "Best validation Dice:",
        BEST_VAL_DICE,
    )

    print(
        "Architecture:",
        "U-Net 3-32-64-128-256-512-256-128-64-32-1",
    )

    print(
        "Placenta U-Net loaded successfully."
    )

    print(
        "Worker:",
        WORKER_NAME,
    )

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

        "model_loaded": (
            model is not None
        ),

        "device": str(
            DEVICE
        ),

        "image_size": IMAGE_SIZE,

        "best_val_dice": (
            BEST_VAL_DICE
        ),
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
            detail=(
                "Placenta model is not loaded."
            ),
        )


    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail=(
                "Filename is required."
            ),
        )


    content_type = (
        file.content_type
        or ""
    )

    content_type = (
        content_type
        .split(";")[0]
        .strip()
        .lower()
    )


    if not content_type.startswith(
        "image/"
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Only image files are supported."
            ),
        )


    try:

        # ----------------------------------------------------
        # Read bytes
        # ----------------------------------------------------

        raw = await file.read()


        if not raw:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Uploaded image is empty."
                ),
            )


        # ----------------------------------------------------
        # Decode image
        # ----------------------------------------------------

        image = Image.open(
            BytesIO(raw)
        ).convert(
            "RGB"
        )


        original_width = (
            image.width
        )

        original_height = (
            image.height
        )


        # ----------------------------------------------------
        # Preprocess
        # ----------------------------------------------------

        tensor = preprocess_image(
            image
        )


        # ----------------------------------------------------
        # Inference
        # ----------------------------------------------------

        with torch.inference_mode():

            prediction = model(
                tensor
            )


        # ----------------------------------------------------
        # Extract probability mask
        # ----------------------------------------------------

        probability_mask = (
            prediction[
                0,
                0,
            ]
            .cpu()
            .numpy()
        )


        # ----------------------------------------------------
        # Binary mask
        # ----------------------------------------------------

        binary_mask = (
            probability_mask
            >= DEFAULT_THRESHOLD
        )


        mask_pixels = int(
            binary_mask.sum()
        )

        total_pixels = int(
            binary_mask.size
        )


        mask_ratio = (
            mask_pixels
            / total_pixels
            if total_pixels > 0
            else 0.0
        )


        # ----------------------------------------------------
        # Probability statistics
        # ----------------------------------------------------

        mean_probability = float(
            probability_mask.mean()
        )


        max_probability = float(
            probability_mask.max()
        )


        min_probability = float(
            probability_mask.min()
        )


        # ----------------------------------------------------
        # Bounding box
        # ----------------------------------------------------

        bbox = None


        if mask_pixels > 0:

            ys, xs = np.where(
                binary_mask
            )


            x_min = int(
                xs.min()
            )

            y_min = int(
                ys.min()
            )

            x_max = int(
                xs.max()
            )

            y_max = int(
                ys.max()
            )


            bbox = {
                "x_min": x_min,
                "y_min": y_min,
                "x_max": x_max,
                "y_max": y_max,

                "width": (
                    x_max
                    - x_min
                    + 1
                ),

                "height": (
                    y_max
                    - y_min
                    + 1
                ),
            }


        # ----------------------------------------------------
        # Create resized mask
        # ----------------------------------------------------

        mask_image = Image.fromarray(
            (
                binary_mask
                .astype(
                    np.uint8
                )
                * 255
            ),
            mode="L",
        )


        mask_image = (
            mask_image.resize(
                (
                    original_width,
                    original_height,
                ),
                resample=Image.NEAREST,
            )
        )


        # ----------------------------------------------------
        # Save predicted mask
        # ----------------------------------------------------

        safe_name = (
            Path(
                file.filename
            ).stem
        )

        mask_filename = (
            f"{safe_name}_placenta_mask.png"
        )

        mask_output_dir = (
            BASE_DIR.parent.parent
            / "storage"
            / "placenta_masks"
        )

        mask_output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )


        mask_path = (
            mask_output_dir
            / mask_filename
        )


        mask_image.save(
            mask_path
        )


        # ----------------------------------------------------
        # URL
        # ----------------------------------------------------

        mask_url = (
            f"/storage/placenta_masks/"
            f"{mask_filename}"
        )


        # ----------------------------------------------------
        # Cleanup
        # ----------------------------------------------------

        del tensor
        del prediction
        del probability_mask
        del binary_mask


        return {

            "status": "success",

            "worker": WORKER_NAME,

            "model": MODEL_NAME,


            "image": {

                "filename":
                    file.filename,

                "width":
                    original_width,

                "height":
                    original_height,
            },


            "segmentation": {

                "threshold":
                    DEFAULT_THRESHOLD,

                "mask_pixels":
                    mask_pixels,

                "mask_ratio":
                    round(
                        mask_ratio,
                        6,
                    ),

                "mean_probability":
                    round(
                        mean_probability,
                        6,
                    ),

                "max_probability":
                    round(
                        max_probability,
                        6,
                    ),

                "min_probability":
                    round(
                        min_probability,
                        6,
                    ),

                "bbox":
                    bbox,

                "mask_path":
                    str(
                        mask_path
                    ),

                "mask_url":
                    mask_url,
            },


            "validation": {

                "best_val_dice":
                    BEST_VAL_DICE,
            },


            "medical_disclaimer": (
                "This segmentation result "
                "is an AI research output and "
                "is not a clinical diagnosis."
            ),
        }


    except HTTPException:

        raise


    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Placenta inference failed: "
                f"{exc}"
            ),
        ) from exc
