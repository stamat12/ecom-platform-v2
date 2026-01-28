"""
Image operations - Pure business logic without UI dependencies.
All functions return results; UI layer handles notifications and state updates.

Extracted from gui_nicegui.py during Phase 3 refactoring.
"""

import json
import subprocess
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple
import sys

# Ensure project root is on path for local imports
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config
from agents.image_classification import (
    classify_images_core,
    remove_image_refs_from_json,
    mark_contains_ean,
    unmark_contains_ean,
)
from agents.image_selector import select_main_images_core
from agents.image_generator import generate_and_save
from agents.image_upscaler import upscale_image


# ============================================================================
# CLASSIFICATION OPERATIONS
# ============================================================================

def classify_images_operation(
    image_paths: List[str], classification_type: str
) -> Tuple[int, List[str], List[str]]:
    """
    Classify selected images using agent core logic.
    
    Args:
        image_paths: List of image file paths
        classification_type: Type to classify as ('phone', 'stock', 'enhanced')
    
    Returns:
        Tuple of (processed_count, updated_skus, errors)
    """
    processed, updated_skus, errors = classify_images_core(image_paths, classification_type)
    return processed, updated_skus, errors


def select_main_images_operation(
    image_paths: List[str]
) -> Tuple[int, List[str], List[str]]:
    """
    Mark selected images as main images.
    
    Args:
        image_paths: List of image file paths
    
    Returns:
        Tuple of (processed_count, updated_skus, errors)
    """
    processed, updated_skus, errors = select_main_images_core(image_paths)
    return processed, updated_skus, errors


def unmark_main_images_operation(
    image_paths: List[str]
) -> Tuple[int, List[str], List[str]]:
    """
    Remove selected images from main_images in JSON.
    
    Args:
        image_paths: List of image file paths
    
    Returns:
        Tuple of (removed_count, updated_skus, errors)
    """
    if not image_paths:
        return 0, [], []

    # Group by SKU -> filenames to remove
    sku_to_filenames: Dict[str, Set[str]] = defaultdict(set)
    for p in image_paths:
        try:
            path_obj = Path(p)
            sku = path_obj.parent.name
            sku_to_filenames[sku].add(path_obj.name)
        except Exception:
            continue

    updated_skus: List[str] = []
    errors: List[str] = []
    removed_count = 0

    for sku, filenames in sku_to_filenames.items():
        product_path = config.PRODUCTS_FOLDER_PATH / f"{sku}.json"
        if not product_path.exists():
            errors.append(f"{sku}: JSON not found")
            continue
        
        try:
            with product_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            
            product_detail = data.get(sku, {}) or {}
            images_section = product_detail.get("Images", {}) or {}
            main_images = images_section.get("main_images", []) or []

            # Filter out entries whose filename is in filenames
            new_main = []
            for entry in main_images:
                fname = entry.get("filename") if isinstance(entry, dict) else None
                if not fname or fname not in filenames:
                    new_main.append(entry)
                else:
                    removed_count += 1

            images_section["main_images"] = new_main
            product_detail["Images"] = images_section
            data[sku] = product_detail

            with product_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            updated_skus.append(sku)
        except Exception as ex:
            errors.append(f"{sku}: {ex}")

    return removed_count, updated_skus, errors


# ============================================================================
# IMAGE GENERATION OPERATIONS
# ============================================================================

def generate_images_operation(
    image_paths: List[str], prompt_name: str, prompt_text: str
) -> Tuple[int, Dict[str, List[Path]], List[str]]:
    """
    Generate enhanced images for selected images using the chosen prompt.
    
    Args:
        image_paths: List of image file paths
        prompt_name: Name of the prompt
        prompt_text: Full prompt text
    
    Returns:
        Tuple of (generated_count, sku_images_dict, errors)
    """
    generated_count = 0
    errors = []
    
    # Group images by SKU
    sku_images = {}
    for img_path_str in image_paths:
        img_path = Path(img_path_str)
        sku = img_path.parent.name
        if sku not in sku_images:
            sku_images[sku] = []
        sku_images[sku].append(img_path)
    
    # Generate for each image
    generated_images = []
    for sku, images in sku_images.items():
        for img_path in images:
            try:
                output_path, error = generate_and_save(
                    sku, img_path, prompt_name, prompt_text
                )
                if error:
                    errors.append(f"{img_path.name}: {error}")
                else:
                    generated_count += 1
                    generated_images.append(output_path.name if output_path else "unknown")
            except Exception as ex:
                errors.append(f"{img_path.name}: {str(ex)}")
    
    return generated_count, sku_images, errors


# ============================================================================
# IMAGE UPSCALING OPERATIONS
# ============================================================================

def upscale_images_operation(
    image_paths: List[str]
) -> Tuple[int, Dict[str, List[Path]], List[str], List[Tuple[Path, str]]]:
    """
    Upscale selected enhanced images and update JSON metadata.
    
    Args:
        image_paths: List of image file paths
    
    Returns:
        Tuple of (upscaled_count, sku_images_dict, errors, upscaled_files)
        upscaled_files is a list of (original_path, upscaled_filename) tuples
    """
    upscaled_count = 0
    errors = []
    upscaled_files = []
    
    # Group images by SKU
    sku_images = {}
    for img_path_str in image_paths:
        try:
            img_path = Path(img_path_str) if not isinstance(img_path_str, Path) else img_path_str
            
            if not img_path.exists():
                errors.append(f"{img_path_str}: File not found")
                continue
                
            sku = img_path.parent.name
            if sku not in sku_images:
                sku_images[sku] = []
            sku_images[sku].append(img_path)
        except Exception as ex:
            errors.append(f"{img_path_str}: Failed to process path - {str(ex)}")
            continue
    
    # Upscale each image and update JSON
    for sku, images in sku_images.items():
        for original_path in images:
            try:
                # 1. Upscale via Replicate API
                output_dir = original_path.parent
                upscaled_path, error = upscale_image(
                    image_path=original_path,
                    output_dir=output_dir,
                    scale=4
                )
                
                if error:
                    errors.append(f"{original_path.name}: {error}")
                    continue
                
                if not upscaled_path or not Path(upscaled_path).exists():
                    errors.append(f"{original_path.name}: Upscaling failed (no output)")
                    continue
                
                upscaled_filename = Path(upscaled_path).name

                # 2. Replace original enhanced with upscaled version in JSON
                product_path = config.PRODUCTS_FOLDER_PATH / f"{sku}.json"
                if not product_path.exists():
                    errors.append(f"{sku}: JSON not found")
                    continue
                
                with product_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                
                product_detail = data.get(sku, {})
                images_section = product_detail.get("Images", {})
                enhanced = images_section.get("enhanced", []) or []
                
                # Find entry and replace filename with upscaled; mark upscaled: true
                found = False
                for i, entry in enumerate(enhanced):
                    if entry.get("filename") == original_path.name:
                        enhanced[i]["filename"] = upscaled_filename
                        enhanced[i]["upscaled"] = True
                        found = True
                        break
                
                if not found:
                    errors.append(f"{original_path.name}: Not found in enhanced array")
                    continue
                
                # Save updated JSON
                images_section["enhanced"] = enhanced
                product_detail["Images"] = images_section
                data[sku] = product_detail
                
                with product_path.open("w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                upscaled_count += 1
                upscaled_files.append((original_path, upscaled_filename))
                
                # 3. Delete the original enhanced image
                time.sleep(0.2)
                try:
                    if original_path.exists():
                        original_path.unlink()
                except (PermissionError, OSError):
                    # File still locked, will try again later
                    pass
                
            except Exception as ex:
                errors.append(f"{original_path.name}: {str(ex)}")
    
    return upscaled_count, sku_images, errors, upscaled_files


def cleanup_original_files(sku_images: Dict[str, List[Path]]) -> List[str]:
    """
    Force delete remaining original files after upscale.
    Uses Windows command for force deletion.
    
    Args:
        sku_images: Dictionary mapping SKU to list of original image paths
    
    Returns:
        List of cleanup errors (empty if all successful)
    """
    cleanup_errors = []
    time.sleep(1.5)
    
    deleted_files = []
    for sku, images in sku_images.items():
        for original_path in images:
            try:
                if original_path.exists():
                    subprocess.run(
                        ['cmd', '/c', f'del /F /Q "{original_path}"'],
                        shell=False,
                        capture_output=True,
                        timeout=5
                    )
                    deleted_files.append(original_path.name)
            except Exception as ex:
                cleanup_errors.append(f"{original_path.name}: {str(ex)}")
    
    return cleanup_errors


# ============================================================================
# DELETE OPERATIONS
# ============================================================================

def delete_from_folder_operation(image_paths: List[str]) -> Tuple[int, int, List[str]]:
    """
    Delete files from disk.
    
    Args:
        image_paths: List of image file paths
    
    Returns:
        Tuple of (deleted_count, failed_count, error_messages)
    """
    deleted, failed = 0, 0
    errors = []
    
    for path_str in image_paths:
        p = Path(path_str)
        try:
            if p.exists():
                p.unlink()
            deleted += 1
        except Exception as ex:
            failed += 1
            errors.append(f"Failed to delete {p.name}: {ex}")
    
    return deleted, failed, errors


def delete_from_json_operation(image_paths: List[str]) -> Tuple[int, int, List[str]]:
    """
    Remove image references from JSON files.
    Files remain on disk.
    
    Args:
        image_paths: List of image file paths
    
    Returns:
        Tuple of (removed_total, updated_count, errors)
    """
    filenames = [Path(p).name for p in image_paths]
    removed_total, updated_count, errors = remove_image_refs_from_json(filenames)
    return removed_total, updated_count, errors


# ============================================================================
# EAN FLAG OPERATIONS
# ============================================================================

def mark_contains_ean_operation(image_paths: List[str]) -> Tuple[int, List[str], List[str]]:
    """Mark images with contains_ean flag."""
    return mark_contains_ean(image_paths)


def unmark_contains_ean_operation(image_paths: List[str]) -> Tuple[int, List[str], List[str]]:
    """Remove contains_ean flag from images."""
    return unmark_contains_ean(image_paths)


# ============================================================================
# EBAY IMAGE ORDER OPERATIONS
# ============================================================================

def extract_sku_from_image_path(image_path: Path) -> str:
    """Extract SKU from image path by looking for parent directories."""
    try:
        # Convert to Path if string
        if isinstance(image_path, str):
            image_path = Path(image_path)
        
        # Strategy 1: Look for 'products' directory and take next folder as SKU
        parts = image_path.parts
        if 'products' in parts:
            idx = parts.index('products')
            if idx + 1 < len(parts):
                candidate = parts[idx + 1]
                # Make sure it's not a common folder name
                if candidate.lower() not in ('images', 'photos', 'img', 'pics'):
                    return candidate
        
        # Strategy 2: If no 'products' folder, try parent directories
        # Typical structure: .../products/SKUXXXXX/images/filename.jpg
        # So parent's parent might be the SKU
        try:
            # Get the grandparent directory name
            grandparent = image_path.parent.parent.name
            if grandparent and grandparent.lower() not in ('products', 'images', 'photos', 'img', 'pics'):
                if len(grandparent) > 0:
                    return grandparent
        except Exception:
            pass
        
        # Strategy 3: Check parent directory - but exclude common folder names
        try:
            parent = image_path.parent.name
            # Exclude common directory names (case-insensitive)
            excluded = {'images', 'photos', 'img', 'pics', 'media', 'assets', 'uploads', 'files', 'data'}
            if parent and parent.lower() not in excluded and len(parent) >= 2:
                return parent
        except Exception:
            pass
            
    except Exception as e:
        print(f"Error extracting SKU from {image_path}: {e}")
    
    return ""


def set_ebay_image_order_operation(image_paths: List[str], order_num: int) -> Tuple[int, List[str], List[str]]:
    """
    Set eBay image order for selected images (1-12).
    Stores in JSON under Images -> eBay Images as {filename, order}.
    
    Args:
        image_paths: List of image file paths
        order_num: Order number 1-12
    
    Returns:
        (changed_count, updated_skus_list, errors_list)
    """
    if not image_paths or not (1 <= order_num <= 12):
        return 0, [], ["Invalid order number; must be 1-12"]
    
    changed = 0
    updated_skus = set()
    errors = []
    
    for image_path_str in image_paths:
        try:
            image_path = Path(image_path_str)
            if not image_path.exists():
                errors.append(f"Image not found: {image_path.name}")
                continue
            
            # Extract SKU from path
            sku = extract_sku_from_image_path(image_path)
            if not sku:
                errors.append(f"Could not determine SKU for {image_path.name} (path: {str(image_path)[:100]})")
                continue
            
            # Load product JSON
            json_path = config.PRODUCTS_FOLDER_PATH / f"{sku}.json"
            if not json_path.exists():
                errors.append(f"No JSON found for SKU {sku}")
                continue
            
            with json_path.open("r", encoding="utf-8") as f:
                product_data = json.load(f)
            
            if sku not in product_data:
                product_data[sku] = {}
            
            # Initialize Images section if needed
            if "Images" not in product_data[sku]:
                product_data[sku]["Images"] = {}
            
            # Initialize eBay Images array if needed
            if "eBay Images" not in product_data[sku]["Images"]:
                product_data[sku]["Images"]["eBay Images"] = []
            
            # Get filename
            filename = image_path.name
            
            # Check if this filename already exists in eBay Images
            ebay_images = product_data[sku]["Images"]["eBay Images"]
            existing_idx = next((i for i, img in enumerate(ebay_images) if img.get("filename") == filename), None)
            
            # Create or update the image record
            image_record = {"filename": filename, "order": order_num}
            
            if existing_idx is not None:
                # Update existing record
                ebay_images[existing_idx] = image_record
            else:
                # Add new record
                ebay_images.append(image_record)
            
            # Save back
            with json_path.open("w", encoding="utf-8") as f:
                json.dump(product_data, f, ensure_ascii=False, indent=2)
            
            changed += 1
            updated_skus.add(sku)
        except Exception as e:
            errors.append(f"Error processing {Path(image_path_str).name}: {str(e)[:80]}")
    
    return changed, list(updated_skus), errors
