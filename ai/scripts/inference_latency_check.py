from pathlib import Path
import time
import statistics

from inference import predict

BASE_DIR = Path(__file__).parent.parents[1]

image_path = (
    BASE_DIR
    / "ai"
    / "scripts"
    / "media_inference_check"
    / "Tuberculosis-19.png"
)

# ----------------------------------------
# Warm-up
# ----------------------------------------

for _ in range(5):
    predict(image_path)


# ----------------------------------------
# Measure prediction latency
# ----------------------------------------

latencies = []
NUM_RUNS = 100

for _ in range(NUM_RUNS):

    start = time.perf_counter()

    result = predict(image_path)

    end = time.perf_counter()

    latencies.append((end - start) * 1000)


# ----------------------------------------
# Results
# ----------------------------------------

print("Inference Latency")
print("-" * 40)
print(f"Runs: {NUM_RUNS}")
print()

print(f"Mean:   {statistics.mean(latencies):.3f} ms")
print(f"Median: {statistics.median(latencies):.3f} ms")
print(f"Minimum: {min(latencies):.3f} ms")
print(f"Maximum: {max(latencies):.3f} ms")

print("\nSample prediction:")
print(result)