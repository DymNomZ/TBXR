from pathlib import Path
from inference import predict, generate_heatmap

BASE_DIR = Path(__file__).parent.parents[1]
image_path = BASE_DIR / "ai"/ "scripts" / "media_inference_check" / "Tuberculosis-19.png"

# 1. Test prediction
result = predict(image_path)
print("PREDICTION:", result)

# 2. Test heatmap generation
heatmap_path = generate_heatmap(image_path)
print("HEATMAP SAVED AT:", heatmap_path)
