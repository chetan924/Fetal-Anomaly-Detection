from pathlib import Path

from app.ml.predict_plane import predict_plane
from app.ml.gradcam import (
    generate_gradcam,
    remove_hooks,
)


# =========================================================
# CONFIG
# =========================================================

BACKEND_ROOT = (
    Path(__file__).resolve().parent
)


SCAN_DIR = (
    BACKEND_ROOT
    / "storage"
    / "scans"
)


ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}


# =========================================================
# HELPERS
# =========================================================

def get_image_files():
    """
    Return all supported ultrasound images
    from backend/storage/scans.
    """

    if not SCAN_DIR.exists():

        raise FileNotFoundError(
            f"Scan directory not found: {SCAN_DIR}"
        )


    return sorted(
        [
            file
            for file in SCAN_DIR.iterdir()
            if (
                file.is_file()
                and file.suffix.lower()
                in ALLOWED_EXTENSIONS
            )
        ],
        key=lambda file: file.name.lower(),
    )


# =========================================================
# MAIN VALIDATION
# =========================================================

def main():

    print()
    print("=" * 100)
    print(
        "FETALAI — GRAD-CAM ATTENTION VALIDATION"
    )
    print("=" * 100)


    print()
    print(
        f"Scan directory: {SCAN_DIR}"
    )


    # =====================================================
    # FIND IMAGES
    # =====================================================

    try:

        images = get_image_files()

    except Exception as exc:

        print()
        print(
            "Failed to find scan images:"
        )

        print(
            f"{type(exc).__name__}: {exc}"
        )

        return


    print()
    print(
        f"Images found: {len(images)}"
    )


    if not images:

        print()
        print(
            "No ultrasound images found."
        )

        return


    # =====================================================
    # RESULTS
    # =====================================================

    results = []

    errors = []


    # =====================================================
    # PROCESS ALL IMAGES
    # =====================================================

    for index, image_path in enumerate(
        images,
        start=1,
    ):

        print()
        print(
            f"[{index}/{len(images)}] "
            f"{image_path.name}"
        )


        try:

            # =================================================
            # MODEL 1 — FETAL PLANE
            # =================================================

            plane_result = predict_plane(
                image_path
            )


            predicted_class = (
                plane_result[
                    "predicted_class"
                ]
            )


            confidence_percent = float(
                plane_result[
                    "confidence_percent"
                ]
            )


            # =================================================
            # GRAD-CAM
            # =================================================

            gradcam_result = (
                generate_gradcam(
                    image_path,
                    output_prefix=(
                        f"validation_{index}"
                    ),
                )
            )


            # =================================================
            # ATTENTION QUALITY
            # =================================================

            attention = (
                gradcam_result[
                    "attention_quality"
                ]
            )


            attention_score = float(
                attention[
                    "score"
                ]
            )


            attention_status = (
                attention[
                    "status"
                ]
            )


            attention_label = (
                attention[
                    "label"
                ]
            )


            attention_entropy = float(
                attention[
                    "entropy"
                ]
            )


            # =================================================
            # SAVE RESULT
            # =================================================

            result = {

                "file":
                    image_path.name,

                "class":
                    predicted_class,

                "confidence":
                    confidence_percent,

                "score":
                    attention_score,

                "status":
                    attention_status,

                "label":
                    attention_label,

                "entropy":
                    attention_entropy,

            }


            results.append(
                result
            )


            # =================================================
            # DISPLAY
            # =================================================

            print(
                f"  Class      : "
                f"{predicted_class}"
            )


            print(
                f"  Confidence : "
                f"{confidence_percent:.2f}%"
            )


            print(
                f"  Attention  : "
                f"{attention_score:.4f}"
            )


            print(
                f"  Status     : "
                f"{attention_status}"
            )


            print(
                f"  Entropy    : "
                f"{attention_entropy:.4f}"
            )


        except Exception as exc:

            error_message = (
                f"{type(exc).__name__}: {exc}"
            )


            errors.append(
                {
                    "file":
                        image_path.name,

                    "error":
                        error_message,
                }
            )


            print(
                f"  ERROR      : "
                f"{error_message}"
            )


    # =====================================================
    # NO RESULTS
    # =====================================================

    if not results:

        print()
        print("=" * 100)
        print(
            "VALIDATION FAILED"
        )
        print("=" * 100)

        print()
        print(
            "No images were processed successfully."
        )

        return


    # =====================================================
    # OVERALL SCORE SUMMARY
    # =====================================================

    scores = [
        item["score"]
        for item in results
    ]


    average_score = (
        sum(scores)
        / len(scores)
    )


    minimum_score = min(
        scores
    )


    maximum_score = max(
        scores
    )


    print()
    print("=" * 100)
    print(
        "ATTENTION SCORE SUMMARY"
    )
    print("=" * 100)


    print()
    print(
        f"Images found       : "
        f"{len(images)}"
    )


    print(
        f"Successful images  : "
        f"{len(results)}"
    )


    print(
        f"Failed images      : "
        f"{len(errors)}"
    )


    print(
        f"Average score      : "
        f"{average_score:.4f}"
    )


    print(
        f"Minimum score      : "
        f"{minimum_score:.4f}"
    )


    print(
        f"Maximum score      : "
        f"{maximum_score:.4f}"
    )


    # =====================================================
    # STATUS DISTRIBUTION
    # =====================================================

    focused_count = sum(
        1
        for item in results
        if item["status"]
        == "focused"
    )


    moderate_count = sum(
        1
        for item in results
        if item["status"]
        == "moderate"
    )


    uncertain_count = sum(
        1
        for item in results
        if item["status"]
        == "uncertain"
    )


    print()
    print(
        "STATUS DISTRIBUTION"
    )


    print(
        f"Focused    : "
        f"{focused_count}"
    )


    print(
        f"Moderate   : "
        f"{moderate_count}"
    )


    print(
        f"Uncertain  : "
        f"{uncertain_count}"
    )


    # =====================================================
    # CLASS-WISE DISTRIBUTION
    # =====================================================

    classes = sorted(
        {
            item["class"]
            for item in results
        }
    )


    print()
    print("=" * 100)
    print(
        "CLASS-WISE ATTENTION"
    )
    print("=" * 100)


    print()


    print(
        f"{'Class':25}"
        f"{'Count':>8}"
        f"{'Average':>12}"
        f"{'Min':>12}"
        f"{'Max':>12}"
    )


    print(
        "-" * 70
    )


    for class_name in classes:

        class_scores = [
            item["score"]
            for item in results
            if item["class"]
            == class_name
        ]


        class_average = (
            sum(class_scores)
            / len(class_scores)
        )


        class_min = min(
            class_scores
        )


        class_max = max(
            class_scores
        )


        print(
            f"{class_name:25}"
            f"{len(class_scores):8d}"
            f"{class_average:12.4f}"
            f"{class_min:12.4f}"
            f"{class_max:12.4f}"
        )


    # =====================================================
    # FULL RESULTS
    # =====================================================

    print()
    print("=" * 100)
    print(
        "ALL RESULTS"
    )
    print("=" * 100)


    print()


    print(
        f"{'File':38}"
        f"{'Class':18}"
        f"{'Conf.':>9}"
        f"{'Score':>9}"
        f"{'Status':>12}"
    )


    print(
        "-" * 100
    )


    for item in results:

        file_name = (
            item["file"][:38]
        )


        class_name = (
            item["class"][:18]
        )


        print(
            f"{file_name:38}"
            f"{class_name:18}"
            f"{item['confidence']:8.2f}%"
            f"{item['score']:9.4f}"
            f"{item['status']:>12}"
        )


    # =====================================================
    # FAILED IMAGES
    # =====================================================

    if errors:

        print()
        print("=" * 100)
        print(
            "FAILED IMAGES"
        )
        print("=" * 100)


        for error in errors:

            print()
            print(
                f"File : {error['file']}"
            )


            print(
                f"Error: {error['error']}"
            )


    # =====================================================
    # FINAL STATUS
    # =====================================================

    print()
    print("=" * 100)
    print(
        "VALIDATION COMPLETE"
    )
    print("=" * 100)


    print()
    print(
        "Attention score measures Grad-CAM "
        "activation concentration only."
    )


    print(
        "It is NOT a clinical reliability "
        "score or medical diagnosis."
    )


    print()
    print(
        "Do NOT change attention thresholds "
        "until the validation results are reviewed."
    )


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":

    try:

        main()

    finally:

        # -------------------------------------------------
        # Remove Grad-CAM hooks
        # -------------------------------------------------

        try:

            remove_hooks()

        except Exception:

            pass