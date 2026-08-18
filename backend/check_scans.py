from pathlib import Path

from app.ml.predict_plane import predict_plane


SCAN_DIR = Path(
    "storage/scans"
)


VALID_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
}


print()
print("=" * 70)
print("SCANNING ALL ULTRASOUND IMAGES")
print("=" * 70)
print()


for image_path in sorted(
    SCAN_DIR.iterdir()
):

    if (
        not image_path.is_file()
        or image_path.suffix.lower()
        not in VALID_EXTENSIONS
    ):
        continue


    try:

        result = predict_plane(
            image_path
        )


        print(
            f"{image_path.name}"
        )

        print(
            f"  Class      : "
            f"{result['predicted_class']}"
        )

        print(
            f"  Confidence : "
            f"{result['confidence_percent']:.2f}%"
        )

        print()


    except Exception as exc:

        print(
            f"{image_path.name}"
        )

        print(
            f"  ERROR: {exc}"
        )

        print()


print("=" * 70)
print("SCAN COMPLETE")
print("=" * 70)