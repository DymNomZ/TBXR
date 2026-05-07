# Preprocessing Specification

This document defines the exact preprocessing pipeline used during training and validation.  
It must be replicated exactly in the backend inference pipeline.

---

## Input Image Size

- Target size: **224 × 224**

Used in:

- `transforms.Resize((224, 224))`
- `transforms.RandomResizedCrop(224, ...)`

---

## Color / Channel Format

- Input images are converted to **grayscale**
- Then expanded to **3 channels**

Transformation:

- `transforms.Grayscale(num_output_channels=3)`

Result:

- Single-channel grayscale images duplicated into RGB-like 3-channel format
- Final channel format: **RGB-compatible (3 channels)**

---

## Training Data Augmentation (TRAIN ONLY)

Applied only during training:

- Random rotation: ±10 degrees  
  (`transforms.RandomRotation(10)`)

- Random resized crop:
  - Output size: 224 × 224
  - Scale range: 0.8 to 1.0  
    (`transforms.RandomResizedCrop(224, scale=(0.8, 1.0))`)

- Color jitter:
  - Brightness: 0.2
  - Contrast: 0.2  
    (`transforms.ColorJitter(brightness=0.2, contrast=0.2)`)

---

## Tensor Conversion

- Image is converted to PyTorch tensor using:
  - `transforms.ToTensor()`

Output format:

- Float tensor in range **[0, 1]**
- Shape: **[C, H, W]**

---

## Normalization

Applied to both training and validation:

### Mean

[0.485, 0.456, 0.406]

### Standard Deviation

[0.229, 0.224, 0.225]

This corresponds to ImageNet normalization values.

---

## Validation Pipeline

Validation preprocessing is deterministic (no augmentation):

- Resize: 224 × 224
- Grayscale → 3 channels
- ToTensor
- Normalize (same as training)

No random transformations are applied.

---

## Critical Consistency Requirement

The backend inference pipeline MUST:

- Resize images to 224 × 224
- Convert grayscale images to 3-channel format
- Apply identical normalization:
  - mean = [0.485, 0.456, 0.406]
  - std = [0.229, 0.224, 0.225]
- Use **no augmentation during inference**

Mismatch in any of these steps will result in degraded model performance.
