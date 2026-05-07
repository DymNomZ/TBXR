# 🚀 TB Chest X-Ray Model — Usage Guide

This document explains how to use the trained TB classification model for both **training continuation** and **website deployment**.

---

# 📁 1. Using `best_model.pth` (Training / Resume)

## 🧠 Purpose

Used to resume training from the best-performing checkpoint.

## 📌 Load model

```python
checkpoint = torch.load('best_model.pth', map_location=device)
model.load_state_dict(checkpoint['model_state_dict'])
```

## 📌 Restore training state (optional)

```python
optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
start_epoch = checkpoint['epoch']
best_recall = checkpoint['best_recall']
```

## 🎯 When to use

- Continue fine-tuning
- Improve model performance
- Re-run experiments

---

# 🌐 2. Using `deploy_model.pth` (Website Backend)

## 🧠 Purpose

Used for **real-time inference in a web server** (Django / FastAPI).

## 📌 Load model

```python
model = MyModel()
model.load_state_dict(torch.load('deploy_model.pth', map_location='cpu'))
model.eval()
```

## 📌 Run inference

```python
with torch.no_grad():
    output = model(image)
    prob = torch.sigmoid(output)
    prediction = (prob > 0.5).float()
```

## 🎯 When to use

- Backend API prediction
- Web app inference
- Production deployment

---

# ⚡ 3. Using `tb_model_final.pt` (TorchScript Deployment)

## 🧠 Purpose

Optimized and portable model for fast inference.

## 📌 Load model

```python
model = torch.jit.load('tb_model_final.pt')
model.eval()
```

## 📌 Run inference

```python
with torch.no_grad():
    output = model(image)
    prob = torch.sigmoid(output)
```

## 🎯 When to use

- High-performance inference
- Reduced dependency environments
- Advanced production systems

---

# 🧪 Full Inference Pipeline (Web Example)

## 1. Preprocess image

```python
from PIL import Image
import torchvision.transforms as transforms

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.5]*3, [0.5]*3)
])

img = Image.open("xray.jpg").convert("RGB")
img = transform(img).unsqueeze(0)
```

## 2. Predict

```python
with torch.no_grad():
    output = model(img)
    prob = torch.sigmoid(output).item()

result = "TB" if prob > 0.5 else "Normal"
print(result, prob)
```

---
