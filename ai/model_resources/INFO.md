# 🧠 TB Chest X-Ray Model Files — Information Guide

This document explains the purpose of the three exported model files used in the TB Chest X-Ray classification system.

---

# 📁 1. `best_model.pth` (Training Checkpoint)

## 🧾 What it contains

- Model weights (`state_dict`)
- Optimizer state
- Scheduler state (if included)
- Epoch number
- Best metric (e.g., recall)

## 🎯 Purpose

Used for **resuming training** from the best-performing state.

## 🧠 When to use it

- Continue fine-tuning the model
- Restore training after Colab session resets
- Experiment with further improvements

## ❌ When NOT to use it

- Website deployment
- Production inference

## ⚠️ Notes

This file is not optimized for deployment because it includes training metadata and optimizer state.

---

# 📁 2. `deploy_model.pth` (Inference Weights)

## 🧾 What it contains

- Only `model.state_dict()` (learned weights)

## 🎯 Purpose

Used for **backend inference in the website** (Django / FastAPI).

## 🧠 When to use it

- Loading model in API server
- Running predictions on uploaded X-rays
- Production backend deployment

## ✔ Example usage

```python
model = MyModel()
model.load_state_dict(torch.load("deploy_model.pth", map_location="cpu"))
model.eval()
```

## ❌ When NOT to use it

- Resuming training (optimizer state is missing)

---

# 📁 3. `tb_model_final.pt` (TorchScript Model)

## 🧾 What it contains

- Serialized TorchScript version of the model
- Fully portable computation graph

## 🎯 Purpose

Used for **optimized or portable inference deployment**.

## 🧠 When to use it

- High-performance inference
- Deployment without full Python training code dependency
- Edge or production environments

## ✔ Example usage

```python
model = torch.jit.load("tb_model_final.pt")
model.eval()
```

## ⚠️ Notes

- Faster and more portable than standard PyTorch models
- May not support all dynamic model behaviors

---

# ⚖️ Summary Comparison

| File                | Purpose             | Use Case             | Includes Optimizer | Deployment Ready |
| ------------------- | ------------------- | -------------------- | ------------------ | ---------------- |
| `best_model.pth`    | Training checkpoint | Resume training      | ✔ Yes              | ❌ No            |
| `deploy_model.pth`  | Inference weights   | Backend API          | ❌ No              | ✔ Yes            |
| `tb_model_final.pt` | TorchScript model   | Optimized deployment | ❌ No              | ✔ Yes (advanced) |

---

# 🧭 Recommended Usage Flow

## During Training (Colab)

- Save: `best_model.pth`

## For Website Backend

- Use: `deploy_model.pth`

## For Advanced Deployment

- Optional: `tb_model_final.pt`

---

# 🧠 Key Insight

- Training files are for **learning continuation**
- Deploy files are for **real-world inference**
- TorchScript is for **optimized production deployment**

# Special thanks to Chat-GPT
