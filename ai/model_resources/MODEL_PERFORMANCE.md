# Model Performance

## Dataset

The model was evaluated using the **Tuberculosis (TB) Chest X-ray Database** from Kaggle.

The dataset used in this repository contains:

- **Normal:** 3,500 images
- **Tuberculosis:** 697 images
- **Total:** 4,197 images

Class mapping:

| Class        | Label |
| ------------ | ----: |
| Normal       |     0 |
| Tuberculosis |     1 |

### Dataset Split

The dataset was split into training and validation sets.

| Split      |    Normal | Tuberculosis |     Total |
| ---------- | --------: | -----------: | --------: |
| Training   |     2,800 |          560 |     3,360 |
| Validation |       700 |          137 |       837 |
| **Total**  | **3,500** |      **697** | **4,197** |

This corresponds to an approximately 80/20 training-validation split.

## Evaluation

The following metrics were calculated:

- Accuracy
- Sensitivity (Recall)
- Specificity
- Precision
- F1 Score
- AUC-ROC

A classification threshold of `0.5` was used for binary predictions. AUC-ROC was calculated using model output probabilities.

## Validation Results

| Metric               |      Result |
| -------------------- | ----------: |
| Accuracy             |  **99.88%** |
| Sensitivity (Recall) |  **99.27%** |
| Specificity          | **100.00%** |
| Precision            | **100.00%** |
| F1 Score             |  **99.63%** |
| AUC-ROC              |  **1.0000** |

It is of note that the current data set trained on is considered to be an easy dataset

## Proposal Target Comparison

The model performance was compared against the project targets.

| Metric      | Target |  Result | Status |
| ----------- | -----: | ------: | ------ |
| Sensitivity |   ≥90% |  99.27% | PASS   |
| Specificity |   >70% | 100.00% | PASS   |

The evaluated model exceeded both specified performance targets on the validation split.

## Inference Latency

Inference latency was measured using the repository's `predict()` function with a single chest X-ray image.

The measurement represents end-to-end prediction execution for the `predict()` function.

### Measurement Configuration

- **Input:** Single chest X-ray image
- **Warm-up runs:** 5
- **Measured runs:** 100

### Results

| Metric  |        Latency |
| ------- | -------------: |
| Mean    |  **73.335 ms** |
| Median  |  **65.557 ms** |
| Minimum |  **46.076 ms** |
| Maximum | **467.838 ms** |

The median latency was lower than the mean, indicating occasional higher-latency outliers during measurement.

## Dataset Attribution

The Tuberculosis Chest X-ray Database was created by researchers from Qatar University, the University of Dhaka, and collaborating institutions.

If this dataset is used for scientific or academic purposes, please cite:

> T. Rahman, A. Khandakar, M. A. Kadir, K. R. Islam, K. F. Islam, Z. B. Mahbub, M. A. Ayari, and M. E. H. Chowdhury, "Reliable Tuberculosis Detection using Chest X-ray with Deep Learning, Segmentation and Visualization," _IEEE Access_, vol. 8, pp. 191586–191601, 2020. DOI: 10.1109/ACCESS.2020.3031384.
