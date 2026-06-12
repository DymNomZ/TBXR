"""
Hey gangs this is what I made based sa PREPORCESS_SPEC.md wherein naay 224x224 resize,
grayscale to 3-channel, ImageNet normalization, no augmentation. preprocess_xray() loads image inputs (including DICOM),
applies the exact deterministic transforms, and saves a normalized CHW tensor as a .npy file to be used for inference.
"""

from pathlib import Path

import numpy as np
from PIL import Image
from PIL.Image import Resampling
import pydicom
from pydicom.multival import MultiValue


def preprocess_xray(input_path: str) -> str:
    """
    Run all preprocessing steps for a raw X-ray file.

    Returns the output path of the processed image tensor (.npy).
    """
    input_path_obj = Path(input_path)
    if not input_path_obj.exists():
        raise FileNotFoundError(f"Input file not found: {input_path_obj}")
    if not input_path_obj.is_file():
        raise ValueError(f"Input path is not a file: {input_path_obj}")

    image = _load_image(input_path_obj)
    image = _prepare_image(image)

    # Convert to normalized CHW tensor and persist for inference.
    tensor = _to_normalized_chw_tensor(image)
    output_path = input_path_obj.with_name(f"{input_path_obj.stem}_processed.npy")
    np.save(output_path, tensor)
    return str(output_path)


def _load_image(input_path: Path) -> Image.Image:
    if input_path.suffix.lower() == ".dcm":
        dicom_data = pydicom.dcmread(str(input_path))
        if not hasattr(dicom_data, "pixel_array"):
            raise ValueError("DICOM file does not contain image data.")

        pixel_array = dicom_data.pixel_array.astype(float)

        if "RescaleSlope" in dicom_data and "RescaleIntercept" in dicom_data:
            slope = float(dicom_data.RescaleSlope)
            intercept = float(dicom_data.RescaleIntercept)
            pixel_array = pixel_array * slope + intercept

        if "WindowCenter" in dicom_data and "WindowWidth" in dicom_data:
            window_center = dicom_data.WindowCenter
            window_width = dicom_data.WindowWidth

            if isinstance(window_center, MultiValue):
                window_center = float(window_center[0])
            else:
                window_center = float(window_center)

            if isinstance(window_width, MultiValue):
                window_width = float(window_width[0])
            else:
                window_width = float(window_width)

            vmin = window_center - (window_width / 2.0)
            vmax = window_center + (window_width / 2.0)

            pixel_array = np.clip(pixel_array, vmin, vmax)
            image_scaled = ((pixel_array - vmin) / (vmax - vmin)) * 255.0
        else:
            p1 = np.percentile(pixel_array, 1)
            p99 = np.percentile(pixel_array, 99)
            pixel_array = np.clip(pixel_array, p1, p99)
            image_scaled = ((pixel_array - p1) / (p99 - p1)) * 255.0

        if (
            hasattr(dicom_data, "PhotometricInterpretation")
            and dicom_data.PhotometricInterpretation == "MONOCHROME1"
        ):
            image_scaled = 255.0 - image_scaled

        image_uint8 = np.uint8(image_scaled)
        if image_uint8.ndim == 3:
            if image_uint8.shape[0] == 1:
                image_uint8 = image_uint8.squeeze(0)
            else:
                raise ValueError("Multi-frame DICOMs are not supported.")

        return Image.fromarray(image_uint8)

    return Image.open(input_path)


def _prepare_image(image: Image.Image) -> Image.Image:
    image = image.convert("L").convert("RGB")
    return image.resize((224, 224), resample=Resampling.BILINEAR)


def _to_normalized_chw_tensor(image: Image.Image) -> np.ndarray:
    image_array = np.asarray(image, dtype=np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    normalized = (image_array - mean) / std
    return np.transpose(normalized, (2, 0, 1))
