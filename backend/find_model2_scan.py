from pathlib import Path

from app.ml.fetal_analysis_pipeline import analyze_fetal_ultrasound

scan_dir = Path("storage/scans")

for image_path in sorted(scan_dir.iterdir()):

    if image_path.suffix.lower() not in {
        ".jpg",
        ".jpeg",
        ".png",
    }:
        continue

    try:
        result = analyze_fetal_ultrasound(image_path)

        fetal = result.get("fetal_plane", {})
        brain = result.get("brain_plane")

        fetal_class = fetal.get(
            "predicted_class",
            "Unknown",
        )

        fetal_conf = fetal.get(
            "confidence_percent",
            0,
        )

        if brain:
            brain_class = brain.get(
                "predicted_class",
                "Unknown",
            )

            brain_conf = brain.get(
                "confidence_percent",
                0,
            )
        else:
            brain_class = "-"
            brain_conf = 0

        print(
            f"{image_path.name:45} "
            f"| {fetal_class:15} "
            f"| {fetal_conf:6.2f}% "
            f"| {brain_class:18} "
            f"| {brain_conf:6.2f}%"
        )

    except Exception as exc:

        print(
            f"{image_path.name:45} | ERROR | {exc}"
        )
