from pathlib import Path
from typing import Dict

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from torchvision import transforms
from torchvision.models import mobilenet_v3_large


# CHANGE THIS FOR FUTURE VERSIONS OF THE MODEL
MODEL_VERSION = "v1.0.0"
MODEL_NAME = "best_model.pth"

BASE_DIR = Path(__file__).parent.parents[1]
MODEL_PATH = BASE_DIR/"ai"/"model_resources"/MODEL_VERSION/MODEL_NAME
HEATMAP_DIR = BASE_DIR/"ai"/"media"/"heatmaps"

HEATMAP_DIR.mkdir(parents=True, exist_ok=True)
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

CLASS_NAMES = {
    0: "Low Risk",
    1: "High Risk"
}

IMAGE_SIZE = 224

# ============================================================
# PREPROCESSING
# ============================================================

transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.Grayscale(num_output_channels=3),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

def preprocess_image(image_path: str):
    image = Image.open(image_path).convert("RGB")

    tensor = transform(image).unsqueeze(0).to(DEVICE)

    return image, tensor


def load_model():
    model = mobilenet_v3_large(weights=None)

    # Binary classification head
    in_features = model.classifier[3].in_features
    model.classifier[3] = torch.nn.Linear(in_features, 1)

    checkpoint = torch.load(MODEL_PATH, map_location=DEVICE)

    # EXPECTED FORMAT:
    # checkpoint["model_state_dict"]
    model.load_state_dict(checkpoint["model_state_dict"])


    model.to(DEVICE)
    model.eval()

    return model

MODEL = load_model()

# ============================================================
# PREPROCESS IMAGE
# ============================================================

def preprocess_image(image_path: str):
    image = Image.open(image_path)

    tensor = transform(image).unsqueeze(0).to(DEVICE)

    return image, tensor

# ============================================================
# PREDICTION
# ============================================================

def predict(image_path: str) -> Dict:
    _, input_tensor = preprocess_image(image_path)

    with torch.no_grad():
        logit = MODEL(input_tensor)
        prob = torch.sigmoid(logit).item()

    risk_score = prob
    risk_label = "High Risk" if prob >= 0.5 else "Low Risk"

    return {
        "risk_score": round(risk_score, 4),
        "risk_label": risk_label
    }


# ============================================================
# GRAD-CAM
# ============================================================

class GradCAM:
    def __init__(self, model, target_layer):
        self.model = model
        self.target_layer = target_layer
        self.gradients = None
        self.activations = None
        self._register_hooks()

    def _register_hooks(self):
        def forward_hook(module, input, output):
            self.activations = output.detach()

        def backward_hook(module, grad_input, grad_output):
            self.gradients = grad_output[0].detach()

        self.target_layer.register_forward_hook(forward_hook)
        self.target_layer.register_full_backward_hook(backward_hook)

    def generate(self, input_tensor, class_idx=None):
        outputs = self.model(input_tensor)

        if class_idx is None:
            class_idx = torch.argmax(outputs, dim=1).item()

        self.model.zero_grad()

        loss = outputs[:, class_idx]
        loss.backward()

        gradients = self.gradients[0]
        activations = self.activations[0]

        pooled_gradients = torch.mean(gradients, dim=[1, 2])

        for i in range(activations.shape[0]):
            activations[i, :, :] *= pooled_gradients[i]

        heatmap = torch.mean(activations, dim=0).cpu().numpy()

        heatmap = np.maximum(heatmap, 0)

        if np.max(heatmap) != 0:
            heatmap /= np.max(heatmap)

        return heatmap


# ============================================================
# HEATMAP GENERATION
# ============================================================

def generate_heatmap(image_path: str) -> str:
    original_image, input_tensor = preprocess_image(image_path)

    target_layer = MODEL.features[-1]

    grad_cam = GradCAM(MODEL, target_layer)

    heatmap = grad_cam.generate(input_tensor)

    original_np = np.array(original_image.convert("RGB"))
    original_np = cv2.cvtColor(original_np, cv2.COLOR_RGB2BGR)

    heatmap = cv2.resize(
        heatmap,
        (original_np.shape[1], original_np.shape[0])
    )

    heatmap = np.uint8(255 * heatmap)

    colored_heatmap = cv2.applyColorMap(
        heatmap,
        cv2.COLORMAP_JET
    )

    overlay = cv2.addWeighted(
        original_np,
        0.6,
        colored_heatmap,
        0.4,
        0
    )

    filename = f"{Path(image_path).stem}_heatmap.jpg"
    save_path = HEATMAP_DIR / filename

    cv2.imwrite(str(save_path), overlay)

    return str(save_path)