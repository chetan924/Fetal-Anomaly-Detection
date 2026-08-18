from pathlib import Path
import pickle
import time

import numpy as np
import pandas as pd
import torch
from PIL import Image
from sklearn.covariance import LedoitWolf
from sklearn.decomposition import PCA
from torch.utils.data import Dataset, DataLoader
from torchvision.models import EfficientNet_B0_Weights, efficientnet_b0


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

TRAIN_CSV = BASE_DIR / "brain_anomaly_splits" / "train.csv"
VAL_CSV = BASE_DIR / "brain_anomaly_splits" / "val.csv"
TEST_CSV = BASE_DIR / "brain_anomaly_splits" / "test.csv"

MODEL_DIR = BASE_DIR.parent / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_PATH = MODEL_DIR / "brain_anomaly_detector.pkl"

BATCH_SIZE = 32
NUM_WORKERS = 0

PCA_COMPONENTS = 128

# Because we do not have abnormal ground truth, this is only
# a statistical outlier threshold, NOT a medical threshold.
THRESHOLD_PERCENTILE = 95.0

PLANES = [
    "Trans-thalamic",
    "Trans-cerebellum",
    "Trans-ventricular",
]


# ============================================================
# DEVICE
# ============================================================

device = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

print("=" * 65)
print("FETAL BRAIN OUTLIER / ANOMALY-SCORING PROTOTYPE")
print("=" * 65)

print("Device:", device)

if torch.cuda.is_available():
    print(
        "GPU:",
        torch.cuda.get_device_name(0),
    )

    print(
        "VRAM:",
        round(
            torch.cuda.get_device_properties(0).total_memory
            / 1024**3,
            2,
        ),
        "GB",
    )


# ============================================================
# MODEL + TRANSFORMS
# ============================================================

print("\nLoading pretrained EfficientNet-B0...")

weights = EfficientNet_B0_Weights.DEFAULT

transform = weights.transforms()

model = efficientnet_b0(
    weights=weights
)

# Remove classification head.
# Output becomes EfficientNet feature vector.
model.classifier = torch.nn.Identity()

model = model.to(device)

model.eval()

for parameter in model.parameters():
    parameter.requires_grad = False


# ============================================================
# DATASET
# ============================================================

class BrainDataset(Dataset):

    def __init__(self, csv_path):

        self.df = pd.read_csv(csv_path)

    def __len__(self):

        return len(self.df)

    def __getitem__(self, index):

        row = self.df.iloc[index]

        image = Image.open(
            row["image_path"]
        ).convert("RGB")

        image = transform(image)

        return (
            image,
            row["Brain_plane"],
            row["Image_name"],
        )


# ============================================================
# FEATURE EXTRACTION
# ============================================================

def extract_features(csv_path, split_name):

    dataset = BrainDataset(csv_path)

    loader = DataLoader(
        dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=NUM_WORKERS,
        pin_memory=torch.cuda.is_available(),
    )

    all_features = []
    all_planes = []
    all_names = []

    print(
        f"\nExtracting {split_name} features..."
    )

    start_time = time.time()

    with torch.inference_mode():

        for batch_index, (
            images,
            planes,
            names,
        ) in enumerate(loader, start=1):

            images = images.to(
                device,
                non_blocking=True,
            )

            features = model(images)

            features = (
                features
                .detach()
                .cpu()
                .numpy()
            )

            all_features.append(features)

            all_planes.extend(planes)
            all_names.extend(names)

            if batch_index % 20 == 0:
                print(
                    f"  Batch "
                    f"{batch_index}/{len(loader)}"
                )

    features = np.concatenate(
        all_features,
        axis=0,
    )

    elapsed = time.time() - start_time

    print(
        f"{split_name} features:",
        features.shape,
    )

    print(
        f"Time: {elapsed:.2f} sec"
    )

    return (
        features,
        np.array(all_planes),
        np.array(all_names),
    )


# ============================================================
# EXTRACT TRAIN / VALIDATION / TEST FEATURES
# ============================================================

train_features, train_planes, train_names = (
    extract_features(
        TRAIN_CSV,
        "TRAIN",
    )
)

val_features, val_planes, val_names = (
    extract_features(
        VAL_CSV,
        "VALIDATION",
    )
)

test_features, test_planes, test_names = (
    extract_features(
        TEST_CSV,
        "TEST",
    )
)


# ============================================================
# PCA
# ============================================================

print("\n" + "=" * 65)
print("PCA FEATURE REDUCTION")
print("=" * 65)

max_components = min(
    PCA_COMPONENTS,
    train_features.shape[0] - 1,
    train_features.shape[1],
)

pca = PCA(
    n_components=max_components,
    random_state=42,
)

train_pca = pca.fit_transform(
    train_features
)

val_pca = pca.transform(
    val_features
)

test_pca = pca.transform(
    test_features
)

print(
    "Original feature dimension:",
    train_features.shape[1],
)

print(
    "PCA dimension:",
    train_pca.shape[1],
)

print(
    "Explained variance:",
    f"{pca.explained_variance_ratio_.sum() * 100:.2f}%",
)


# ============================================================
# MAHALANOBIS MODELS
# ============================================================

plane_models = {}


def mahalanobis_scores(
    features,
    mean,
    precision,
):

    diff = features - mean

    squared = np.einsum(
        "ij,jk,ik->i",
        diff,
        precision,
        diff,
    )

    squared = np.maximum(
        squared,
        0,
    )

    return np.sqrt(squared)


print("\n" + "=" * 65)
print("BUILDING PLANE-SPECIFIC REFERENCE MODELS")
print("=" * 65)


for plane in PLANES:

    print(f"\nPlane: {plane}")

    train_mask = (
        train_planes == plane
    )

    val_mask = (
        val_planes == plane
    )

    test_mask = (
        test_planes == plane
    )

    plane_train = train_pca[
        train_mask
    ]

    plane_val = val_pca[
        val_mask
    ]

    plane_test = test_pca[
        test_mask
    ]

    print(
        "Train samples:",
        len(plane_train),
    )

    print(
        "Validation samples:",
        len(plane_val),
    )

    print(
        "Test samples:",
        len(plane_test),
    )

    # Robust covariance estimation
    covariance_model = LedoitWolf()

    covariance_model.fit(
        plane_train
    )

    mean = covariance_model.location_

    precision = covariance_model.precision_

    # Validation distribution is used only to create
    # a statistical outlier threshold.
    val_scores = mahalanobis_scores(
        plane_val,
        mean,
        precision,
    )

    threshold = float(
        np.percentile(
            val_scores,
            THRESHOLD_PERCENTILE,
        )
    )

    test_scores = mahalanobis_scores(
        plane_test,
        mean,
        precision,
    )

    print(
        "Validation score mean:",
        f"{val_scores.mean():.4f}",
    )

    print(
        "Validation score std:",
        f"{val_scores.std():.4f}",
    )

    print(
        f"{THRESHOLD_PERCENTILE:.0f}th "
        f"percentile threshold:",
        f"{threshold:.4f}",
    )

    test_outliers = (
        test_scores > threshold
    ).sum()

    test_outlier_percent = (
        test_outliers
        / len(test_scores)
        * 100
    )

    print(
        "Test statistical outliers:",
        f"{test_outliers}/{len(test_scores)} "
        f"({test_outlier_percent:.2f}%)",
    )

    plane_models[plane] = {
        "mean": mean,
        "precision": precision,
        "threshold": threshold,
        "validation_score_mean": float(
            val_scores.mean()
        ),
        "validation_score_std": float(
            val_scores.std()
        ),
    }


# ============================================================
# SAVE ARTIFACT
# ============================================================

artifact = {
    "model_type": (
        "EfficientNet-B0 + PCA + "
        "plane-specific Mahalanobis scoring"
    ),

    "version": 1,

    "pca": pca,

    "plane_models": plane_models,

    "planes": PLANES,

    "threshold_percentile": (
        THRESHOLD_PERCENTILE
    ),

    "feature_dimension": int(
        train_features.shape[1]
    ),

    "pca_dimension": int(
        train_pca.shape[1]
    ),

    "important_note": (
        "This model is an outlier-scoring prototype. "
        "The source dataset does not contain verified "
        "normal/abnormal ground-truth labels. "
        "Outputs must not be interpreted as a medical "
        "diagnosis of fetal anomaly."
    ),
}


with open(
    OUTPUT_PATH,
    "wb",
) as file:

    pickle.dump(
        artifact,
        file,
    )


# ============================================================
# COMPLETE
# ============================================================

print("\n" + "=" * 65)
print("TRAINING / REFERENCE BUILD COMPLETE")
print("=" * 65)

print(
    "Artifact saved to:"
)

print(
    OUTPUT_PATH
)

print(
    "\nIMPORTANT:"
)

print(
    "This artifact detects statistical outliers "
    "relative to the training distribution."
)

print(
    "It does NOT yet provide clinically validated "
    "Normal/Abnormal fetal anomaly classification."
)