from typing import List, Literal, TypedDict

import cv2
import numpy as np
from PIL import Image


QUALITY_THRESHOLD = 0.6
QUALITY_REASONS = frozenset({
    "underexposed",
    "overexposed",
    "low_contrast",
    "blurry",
    "low_resolution",
})


class QualityCheck(TypedDict):
    status: Literal["ACCEPTABLE", "LOW_QUALITY"]
    score: float
    reasons: List[str]


def assess_quality(image: Image.Image) -> QualityCheck:
    image_rgb = image.convert("RGB")
    gray = np.array(image_rgb.convert("L"))

    height, width = gray.shape

    reasons = []
    penalty = 0.0

    # Resolution
    if width * height < 512 * 512:
        reasons.append("low_resolution")
        penalty += 0.20

    # Exposure
    mean_intensity = float(np.mean(gray))

    if mean_intensity < 50:
        reasons.append("underexposed")
        penalty += 0.25

    elif mean_intensity > 205:
        reasons.append("overexposed")
        penalty += 0.25

    # Contrast
    p1, p99 = np.percentile(gray, [1, 99])

    if (p99 - p1) < 30:
        reasons.append("low_contrast")
        penalty += 0.20

    # Blur
    laplacian_variance = cv2.Laplacian(
        gray,
        cv2.CV_64F
    ).var()

    if laplacian_variance < 100:
        reasons.append("blurry")
        penalty += 0.25

    score = max(0.0, min(1.0, 1.0 - penalty))
    score = round(float(score), 4)

    status = (
        "ACCEPTABLE"
        if score >= QUALITY_THRESHOLD
        else "LOW_QUALITY"
    )

    return {
        "status": status,
        "score": score,
        "reasons": sorted(reasons),
    }