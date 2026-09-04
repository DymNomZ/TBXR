# Image Quality Assessment Contract and Logic Analysis

## Overview

This document defines and analyzes the machine-readable image quality assessment implemented in:

```text
ai/scripts/quality.py
```

The purpose of the quality assessment is to provide a stable signal that downstream components can consume to determine whether an uploaded image should be considered acceptable for normal processing or classified as low quality.

The assessment is lightweight, CPU-based, deterministic, and uses OpenCV, NumPy, and Pillow.

---

# 1. Quality Check Contract

The quality assessment returns a stable object with the following shape:

```json
{
  "status": "ACCEPTABLE",
  "score": 0.75,
  "reasons": ["blurry"]
}
```

The same object shape is returned regardless of whether the image is acceptable or low quality.

## Fields

| Field     | Type            | Description                                                      |
| --------- | --------------- | ---------------------------------------------------------------- |
| `status`  | string          | Threshold-based workflow classification                          |
| `score`   | float           | Aggregate heuristic quality score from `0.0` to `1.0`            |
| `reasons` | list of strings | Machine-readable heuristic conditions detected during assessment |

---

# 2. Status Values

The quality assessment supports two stable status values:

```text
ACCEPTABLE
LOW_QUALITY
```

## ACCEPTABLE

`ACCEPTABLE` indicates that the aggregate quality score meets or exceeds the configured threshold.

```text
score >= QUALITY_THRESHOLD
```

An acceptable image may still contain detected quality conditions.

For example:

```json
{
  "status": "ACCEPTABLE",
  "score": 0.75,
  "reasons": ["blurry"]
}
```

This means that blur was detected, but the aggregate quality score remains above the threshold.

## LOW_QUALITY

`LOW_QUALITY` indicates that the aggregate quality score is below the configured threshold.

```text
score < QUALITY_THRESHOLD
```

Example:

```json
{
  "status": "LOW_QUALITY",
  "score": 0.5,
  "reasons": ["blurry", "underexposed"]
}
```

---

# 3. Score Semantics

The quality score is a heuristic value in the range:

```text
0.0 <= score <= 1.0
```

Higher values indicate better estimated image quality.

The score begins at:

```text
1.0
```

Quality penalties are subtracted when heuristics detect quality conditions.

The final score is clamped to the valid range:

```text
0.0 - 1.0
```

The score is rounded to four decimal places.

The score is an aggregate heuristic measurement and should not be interpreted as a statistically calibrated probability.

---

# 4. Quality Threshold

The current implementation defines:

```python
QUALITY_THRESHOLD = 0.6
```

Status is determined as follows:

```text
score >= 0.6  → ACCEPTABLE
score < 0.6   → LOW_QUALITY
```

## Boundary Behavior

The threshold comparison is inclusive.

Therefore:

|  Score | Status        |
| -----: | ------------- |
| `1.00` | `ACCEPTABLE`  |
| `0.80` | `ACCEPTABLE`  |
| `0.75` | `ACCEPTABLE`  |
| `0.60` | `ACCEPTABLE`  |
| `0.59` | `LOW_QUALITY` |
| `0.55` | `LOW_QUALITY` |
| `0.00` | `LOW_QUALITY` |

The exact boundary behavior must remain stable unless the threshold contract is intentionally changed.

---

# 5. Assessment Pipeline

The assessment follows this sequence:

```text
Input PIL Image
       ↓
Convert to RGB
       ↓
Convert to grayscale
       ↓
Resolution assessment
       ↓
Exposure assessment
       ↓
Contrast assessment
       ↓
Blur assessment
       ↓
Aggregate penalties
       ↓
Calculate score
       ↓
Apply threshold
       ↓
Return stable quality_check object
```

The assessment should be performed on the original image before resizing or tensor normalization.

This is important because image properties such as original resolution and blur can be distorted by preprocessing operations such as resizing.

---

# 6. Quality Heuristics

The current implementation uses four lightweight heuristics.

## 6.1 Low Resolution

The original image resolution is calculated using:

```text
width × height
```

The image is classified as low resolution when:

```text
width × height < 512 × 512
```

Detected reason:

```text
low_resolution
```

Penalty:

```text
0.20
```

---

## 6.2 Underexposure

The mean grayscale intensity is calculated.

An image is considered underexposed when:

```text
mean_intensity < 50
```

Detected reason:

```text
underexposed
```

Penalty:

```text
0.25
```

---

## 6.3 Overexposure

The mean grayscale intensity is calculated.

An image is considered overexposed when:

```text
mean_intensity > 205
```

Detected reason:

```text
overexposed
```

Penalty:

```text
0.25
```

Underexposure and overexposure are mutually exclusive in a single assessment.

---

## 6.4 Low Contrast

The grayscale intensity distribution is measured using the first and ninety-ninth percentiles.

The image is considered low contrast when:

```text
p99 - p1 < 30
```

Detected reason:

```text
low_contrast
```

Penalty:

```text
0.20
```

---

## 6.5 Blur

Blur is estimated using the variance of the Laplacian:

```text
cv2.Laplacian(gray, cv2.CV_64F).var()
```

The image is considered blurry when:

```text
laplacian_variance < 100
```

Detected reason:

```text
blurry
```

Penalty:

```text
0.25
```

---

# 7. Quality Reasons

The current machine-readable reason values are:

```text
low_resolution
underexposed
overexposed
low_contrast
blurry
```

These values should be treated as stable contract values.

| Reason           | Meaning                                                              |
| ---------------- | -------------------------------------------------------------------- |
| `low_resolution` | Original image dimensions are below the minimum resolution threshold |
| `underexposed`   | Mean grayscale intensity is below the underexposure threshold        |
| `overexposed`    | Mean grayscale intensity is above the overexposure threshold         |
| `low_contrast`   | Grayscale intensity range is below the contrast threshold            |
| `blurry`         | Laplacian variance is below the blur threshold                       |

New reason values should only be added deliberately and documented before downstream consumers depend on them.

---

# 8. Status, Score, and Reasons Semantics

The three fields have different responsibilities.

```text
status
    ↓
Threshold-based workflow classification

score
    ↓
Aggregate heuristic quality measurement

reasons
    ↓
Individual quality conditions detected
```

This distinction is important.

A detected reason does not automatically require `LOW_QUALITY`.

For example:

```json
{
  "status": "ACCEPTABLE",
  "score": 0.75,
  "reasons": ["blurry"]
}
```

The blur heuristic detected a potential quality issue, but the aggregate score remains above the configured threshold.

Therefore:

> `ACCEPTABLE` does not imply that no quality conditions were detected.

Likewise:

> `reasons: []` indicates that no current heuristic conditions were detected.

---

# 9. Example Score Outcomes

The current penalties produce discrete score values.

## No Quality Conditions

```text
Penalty: 0.00
Score:   1.00
Status:  ACCEPTABLE
```

Output:

```json
{
  "status": "ACCEPTABLE",
  "score": 1.0,
  "reasons": []
}
```

---

## Low Resolution Only

```text
Penalty: 0.20
Score:   0.80
Status:  ACCEPTABLE
```

Output:

```json
{
  "status": "ACCEPTABLE",
  "score": 0.8,
  "reasons": ["low_resolution"]
}
```

---

## Blurry Only

```text
Penalty: 0.25
Score:   0.75
Status:  ACCEPTABLE
```

Output:

```json
{
  "status": "ACCEPTABLE",
  "score": 0.75,
  "reasons": ["blurry"]
}
```

---

## Low Resolution and Low Contrast

```text
Penalty: 0.40
Score:   0.60
Status:  ACCEPTABLE
```

Because the threshold comparison is inclusive:

```text
0.60 >= 0.60
```

Output:

```json
{
  "status": "ACCEPTABLE",
  "score": 0.6,
  "reasons": ["low_contrast", "low_resolution"]
}
```

---

## Low Resolution and Blur

```text
Penalty: 0.45
Score:   0.55
Status:  LOW_QUALITY
```

Output:

```json
{
  "status": "LOW_QUALITY",
  "score": 0.55,
  "reasons": ["blurry", "low_resolution"]
}
```

---

## Underexposed and Blurry

```text
Penalty: 0.50
Score:   0.50
Status:  LOW_QUALITY
```

Output:

```json
{
  "status": "LOW_QUALITY",
  "score": 0.5,
  "reasons": ["blurry", "underexposed"]
}
```

---

# 10. Deterministic Reason Ordering

Reasons are returned using:

```python
sorted(reasons)
```

This provides deterministic ordering.

For example:

```text
["underexposed", "blurry"]
```

is consistently returned as:

```text
["blurry", "underexposed"]
```

Deterministic ordering improves test reliability and prevents unnecessary differences between otherwise identical quality assessment results.

---

# 11. Known Heuristic Limitations

The assessment is intentionally lightweight and heuristic-based.

The score should not be interpreted as a clinical image-quality certification.

## Correlated Heuristics

Some quality conditions may be correlated.

For example:

```text
Underexposed image
       ↓
Reduced visible edge information
       ↓
Lower Laplacian variance
       ↓
Possible blurry detection
```

Similarly:

```text
Uniform image
       ↓
Low contrast
       +
Low Laplacian variance
       ↓
Possible blurry detection
```

Multiple penalties may therefore reflect related image characteristics rather than statistically independent quality failures.

This is acceptable for the current lightweight implementation, but the aggregate score should be interpreted as a heuristic score.
