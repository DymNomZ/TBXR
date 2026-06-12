# AI Model Setup

The AI model weights are not included in the repository to keep the project lightweight.

## Download Model Files

Download the required model resources from:

https://drive.google.com/drive/folders/1gPpxL2HiJjQnmj-u9HNOk8cbbSZbdh8o?usp=sharing

---

## Folder Placement

Place the downloaded model files inside:

```txt
ai/model_resources/<MODEL_VERSION>/
```

The final structure should look like:

```txt
project_root/
├── ai/
│   ├── model_resources/
│   │   └── <MODEL_VERSION>/
│   │       └── <MODEL_NAME>
│   └── media/
│       └── heatmaps/
```

---

## Script Paths

The application resolves model paths using:

```python
BASE_DIR = Path(__file__).parent.parents[1]

MODEL_PATH = (
    BASE_DIR / "ai" / "model_resources" / MODEL_VERSION / MODEL_NAME
)

HEATMAP_DIR = (
    BASE_DIR / "ai" / "media" / "heatmaps"
)
```

---

## Notes

- Ensure the correct model version folder is used.
- Ensure the model filename matches `MODEL_NAME`.
- The `heatmaps` directory is used for generated Grad-CAM visualizations.
- If the `heatmaps` folder does not exist, create it manually:

```bash
mkdir -p ai/media/heatmaps
```
