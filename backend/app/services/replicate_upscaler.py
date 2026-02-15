"""Upscaling service using Replicate API"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional, Tuple

import requests

logger = logging.getLogger(__name__)


def _setup_file_logging() -> None:
    log_dir = Path(__file__).resolve().parents[2] / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "replicate_upscaler.log"

    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler) and getattr(handler, "baseFilename", "") == str(log_path):
            return

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)


_setup_file_logging()

# Replicate models for upscaling
REPLICATE_UPSCALE_MODELS = {
    "2x": "nightmareai/real-esrgan:42fed1c4974146d4d2414e2be2c5277c7fcf05fcc3a73abf41610695738c1d7b",
    "4x": "nightmareai/real-esrgan:42fed1c4974146d4d2414e2be2c5277c7fcf05fcc3a73abf41610695738c1d7b",
}


def _get_replicate_token() -> Optional[str]:
    """Get Replicate API token from environment"""
    token = os.getenv("REPLICATE_API_TOKEN")
    if not token:
        logger.error("❌ REPLICATE_API_TOKEN not set in environment!")
    else:
        logger.info(f"✓ REPLICATE_API_TOKEN found (first 15 chars: {token[:15]}...)")
    return token


def _get_file_size_mb(path: Path) -> float:
    """Get file size in MB"""
    if not path.exists():
        return 0
    return path.stat().st_size / (1024 * 1024)


def upscale_image_via_replicate(
    image_path: Path,
    output_dir: Path,
    scale: int = 4,
    target_size_mb: float = 8.0,
) -> Tuple[Optional[Path], Optional[str]]:
    """
    Upscale an image using Replicate API
    
    Args:
        image_path: Path to input image
        output_dir: Directory to save output
        scale: Upscaling factor (2 or 4)
        target_size_mb: Target file size in MB
        
    Returns:
        Tuple of (output_path, error_message)
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"🚀 UPSCALE START: {image_path.name}")
    logger.info(f"{'='*60}")
    
    if not image_path.exists():
        error = f"❌ Image not found: {image_path}"
        logger.error(error)
        return None, error
    
    input_size_mb = _get_file_size_mb(image_path)
    logger.info(f"📁 Input file: {input_size_mb:.2f} MB")
    
    token = _get_replicate_token()
    if not token:
        error = "❌ REPLICATE_API_TOKEN not configured"
        logger.error(error)
        return None, error
    
    # Read image file
    try:
        logger.info(f"📖 Reading image file...")
        with open(image_path, "rb") as f:
            image_data = f.read()
        logger.info(f"✓ Image read: {len(image_data)} bytes")
    except Exception as e:
        error = f"❌ Failed to read image: {str(e)}"
        logger.error(error)
        return None, error
    
    # Convert to base64
    import base64
    logger.info(f"🔄 Encoding to base64...")
    image_b64 = base64.b64encode(image_data).decode("utf-8")
    image_mime = "image/jpeg" if image_path.suffix.lower() in [".jpg", ".jpeg"] else "image/png"
    logger.info(f"✓ Base64 encoded ({len(image_b64)} chars), MIME: {image_mime}")
    
    # Use direct Replicate API call
    try:
        upscale_url = f"https://api.replicate.com/v1/predictions"
        headers = {
            "Authorization": f"Token {token}",
            "Content-Type": "application/json",
        }
        
        # Use Real-ESRGAN model via Replicate
        model_version = REPLICATE_UPSCALE_MODELS.get(f"{scale}x", REPLICATE_UPSCALE_MODELS["4x"])
        payload = {
            "version": model_version,
            "input": {
                "image": f"data:{image_mime};base64,{image_b64}",
                "scale": scale,
                "face_enhance": False,  # Disable to preserve original colors
            },
        }
        
        logger.info(f"\n📡 Submitting to Replicate API:")
        logger.info(f"   URL: {upscale_url}")
        logger.info(f"   Scale: {scale}x")
        logger.info(f"   Model: {model_version[:70]}...")
        
        # Submit job
        response = requests.post(upscale_url, json=payload, headers=headers, timeout=30)
        
        logger.info(f"📥 API Response status: {response.status_code}")
        if response.status_code not in [200, 201]:
            error_text = response.text[:500]
            error = f"❌ Replicate API error {response.status_code}: {error_text}"
            logger.error(error)
            return None, error
        
        job_data = response.json()
        job_id = job_data.get("id")
        logger.info(f"   Job ID: {job_id}")
        logger.info(f"   Status: {job_data.get('status')}")
        
        if not job_id:
            error = "❌ Failed to get job ID from Replicate"
            logger.error(error)
            return None, error
        
        # Poll for completion
        import time
        max_attempts = 120  # 2 minutes with 1-second intervals
        logger.info(f"\n⏳ Polling for job completion (max {max_attempts}s)...")
        
        for attempt in range(max_attempts):
            try:
                status_response = requests.get(
                    f"{upscale_url}/{job_id}",
                    headers=headers,
                    timeout=10
                )
                
                if status_response.status_code != 200:
                    error = f"❌ Failed to check job status: {status_response.status_code}"
                    logger.error(error)
                    return None, error
                
                status_data = status_response.json()
                status = status_data.get("status")
                
                # Log every 10 seconds or on status change
                if attempt % 10 == 0 or status in ["succeeded", "failed"]:
                    logger.info(f"   [{attempt}s] Status: {status}")
                
                if status == "succeeded":
                    output_url = status_data.get("output")
                    if not output_url:
                        error = "❌ Replicate returned success but no output URL"
                        logger.error(error)
                        logger.error(f"   Response: {status_data}")
                        return None, error
                    
                    logger.info(f"\n✅ Job succeeded!")
                    logger.info(f"   Output URL: {output_url[:100]}...")
                    
                    logger.info(f"📥 Downloading upscaled image...")
                    # Download upscaled image
                    output_response = requests.get(output_url, timeout=30)
                    if output_response.status_code != 200:
                        error = f"❌ Failed to download upscaled image: {output_response.status_code}"
                        logger.error(error)
                        return None, error
                    
                    downloaded_size = len(output_response.content)
                    logger.info(f"✓ Downloaded: {downloaded_size} bytes ({downloaded_size / (1024*1024):.2f} MB)")
                    
                    # Save Replicate output as PNG to avoid any color conversion
                    # Real-ESRGAN returns PNG format - keep it as-is for perfect color preservation
                    output_path = output_dir / f"{image_path.stem}_upscaled_{scale}x.png"
                    
                    logger.info(f"💾 Saving to: {output_path.name}")
                    with open(output_path, "wb") as f:
                        f.write(output_response.content)
                    
                    output_size_mb = _get_file_size_mb(output_path)
                    logger.info(f"✓ Saved successfully: {output_size_mb:.2f} MB")
                    logger.info(f"\n🎉 UPSCALING COMPLETE")
                    logger.info(f"   Input:  {input_size_mb:.2f} MB → Output: {output_size_mb:.2f} MB (scale {scale}x)")
                    logger.info(f"{'='*60}\n")
                    
                    return output_path, None
                
                elif status == "failed":
                    error_msg = status_data.get("error", "Unknown error")
                    error = f"❌ Replicate upscaling failed: {error_msg}"
                    logger.error(error)
                    logger.error(f"   Full response: {status_data}")
                    return None, error
                
                # Still processing
                time.sleep(1)
            
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ Request error while polling (attempt {attempt}): {e}")
                if attempt < max_attempts - 1:
                    time.sleep(1)
                    continue
                return None, f"Polling error: {str(e)}"
        
        error = f"❌ Upscaling timed out after {max_attempts} seconds"
        logger.error(error)
        logger.error(f"{'='*60}\n")
        return None, error
    
    except Exception as e:
        logger.error(f"\n❌ UNEXPECTED ERROR: {str(e)}", exc_info=True)
        logger.error(f"{'='*60}\n")
        return None, f"Upscaling error: {str(e)}"


def upscale_to_target_size(
    image_path: Path,
    output_dir: Path,
    target_size_mb: float = 8.0,
) -> Tuple[Optional[Path], Optional[str]]:
    """
    Upscale image until it reaches target size (up to 8 MB)
    
    Args:
        image_path: Path to input image
        output_dir: Directory to save output
        target_size_mb: Target file size in MB
        
    Returns:
        Tuple of (output_path, error_message)
    """
    current_size_mb = _get_file_size_mb(image_path)
    logger.info(f"\n>>> UPSCALE_TO_TARGET_SIZE wrapper called")
    logger.info(f"    Current size: {current_size_mb:.2f} MB, Target: {target_size_mb:.2f} MB")
    
    # If already above target, just return the original
    if current_size_mb >= target_size_mb:
        logger.info(f"    ✓ Image already above target size ({current_size_mb:.2f} >= {target_size_mb:.2f}), skipping")
        return image_path, None
    
    # Use 2x upscaling (safer, less likely to exceed GPU memory)
    logger.info(f"\n>>> Attempting 2x upscaling...")
    upscaled_path, error = upscale_image_via_replicate(
        image_path,
        output_dir,
        scale=2,
        target_size_mb=target_size_mb,
    )
    
    if error:
        logger.error(f"    ❌ All upscaling attempts failed: {error}")
        return None, error
    
    if not upscaled_path:
        error = "❌ Upscaling returned no output path"
        logger.error(error)
        return None, error
    
    upscaled_size_mb = _get_file_size_mb(upscaled_path)
    logger.info(f"\n>>> Upscaled result: {upscaled_size_mb:.2f} MB (target: {target_size_mb:.2f} MB)")
    
    # If still below target and upscaled size is reasonable, try another round
    if upscaled_size_mb < target_size_mb and upscaled_size_mb > 0.5:
        logger.info(f"    ℹ️  Still below target, attempting second upscaling round...")
        second_upscale, error2 = upscale_image_via_replicate(
            upscaled_path,
            output_dir,
            scale=2,
            target_size_mb=target_size_mb,
        )
        if not error2 and second_upscale:
            second_size_mb = _get_file_size_mb(second_upscale)
            if second_size_mb > upscaled_size_mb:
                upscaled_path = second_upscale
                logger.info(f"    ✓ Second upscaling improved to {second_size_mb:.2f} MB")
        else:
            logger.info(f"    ℹ️  Second upscaling failed or did not improve, using first result")
    
    logger.info(f"\n>>> UPSCALE_TO_TARGET_SIZE complete: {upscaled_path.name} ({upscaled_size_mb:.2f} MB)")
    return upscaled_path, None
