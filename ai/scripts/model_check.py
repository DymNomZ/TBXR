import torch

best_model = torch.load("ai/model_resources/best_model-05-07-1537.pth", map_location="cpu")
deploy_model = torch.load("ai/model_resources/deploy_model-05-07-1537.pth", map_location="cpu")

print(type(best_model))
print(type(deploy_model))