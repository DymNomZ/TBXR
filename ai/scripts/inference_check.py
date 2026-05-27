from pathlib import Path
from inference import predict, generate_heatmap, shutdown_model

BASE_DIR = Path(__file__).parent.parents[1]
image_path = BASE_DIR / "ai"/ "scripts" / "media_inference_check" / "others (109).jpg"

# 1. Test prediction
try:
	result = predict(image_path)
	print("PREDICTION:", result)

	# 2. Test heatmap generation
	heatmap_path = generate_heatmap(image_path)
	print("HEATMAP SAVED AT:", heatmap_path)
finally:
	shutdown_model()
