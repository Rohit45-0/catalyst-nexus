"""
Catalyst Nexus - ENHANCED Quality Pipeline
Uses Kling v2.1 with:
- Image as BOTH start and end frame (preserves product identity)
- Professional mode for higher quality
- Optimized prompts for product videos
"""

import os
import sys
import json
import time
import base64
import requests
from datetime import datetime
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

FASTROUTER_API_KEY = os.getenv("FASTROUTER_API_KEY", "")
FASTROUTER_BASE_URL = "https://go.fastrouter.ai/api/v1"

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
AZURE_CONTAINER_NAME = "product-images"

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_DEPLOYMENT = "gpt-4o"
AZURE_OPENAI_API_VERSION = "2024-02-15-preview"

OUTPUT_DIR = Path("output/catalyst_videos_hq")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def print_banner():
    print("\n" + "╔" + "═" * 70 + "╗")
    print("║" + "  🎬 CATALYST NEXUS - ENHANCED QUALITY PIPELINE 🎬  ".center(70) + "║")
    print("╠" + "═" * 70 + "╣")
    print("║" + "  Start+End Frame Mode | Professional Quality | Product Preservation  ".center(70) + "║")
    print("╚" + "═" * 70 + "╝\n")


def upload_to_azure(image_path: str) -> str:
    """Upload image to Azure Blob Storage and return public URL."""
    from azure.storage.blob import BlobServiceClient, ContentSettings
    
    blob_service = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    container_client = blob_service.get_container_client(AZURE_CONTAINER_NAME)
    
    # Generate unique blob name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    blob_name = f"hq_{timestamp}_{Path(image_path).name}"
    
    # Upload with proper content type
    blob_client = container_client.get_blob_client(blob_name)
    with open(image_path, "rb") as f:
        blob_client.upload_blob(
            f, 
            overwrite=True,
            content_settings=ContentSettings(content_type="image/jpeg")
        )
    
    return f"https://rohitf.blob.core.windows.net/{AZURE_CONTAINER_NAME}/{blob_name}"


def analyze_image_with_vision(image_path: str) -> dict:
    """Use GPT-4o Vision to analyze product image."""
    print("   📷 Analyzing image with GPT-4o Vision...")
    
    # Encode image to base64
    with open(image_path, "rb") as f:
        image_base64 = base64.b64encode(f.read()).decode("utf-8")
    
    # Determine mime type
    ext = Path(image_path).suffix.lower()
    mime_type = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png"
    
    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_OPENAI_KEY
    }
    
    payload = {
        "messages": [
            {
                "role": "system",
                "content": """You are a product video director. Analyze the product image and provide:
1. Product type and description
2. Key visual features to highlight
3. Best camera movements for this specific product
4. Mood and style recommendations

Return as JSON with keys: product_type, description, key_features (array), camera_moves (array), mood"""
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Analyze this product image for creating a premium showcase video:"},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_base64}"}}
                ]
            }
        ],
        "max_tokens": 1000,
        "response_format": {"type": "json_object"}
    }
    
    url = f"{AZURE_OPENAI_ENDPOINT}openai/deployments/{AZURE_OPENAI_DEPLOYMENT}/chat/completions?api-version={AZURE_OPENAI_API_VERSION}"
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    
    result = response.json()
    analysis = json.loads(result["choices"][0]["message"]["content"])
    return analysis


def generate_quality_prompt(analysis: dict) -> str:
    """Generate an optimized prompt for high-quality video."""
    
    product = analysis.get("product_type", "product")
    features = analysis.get("key_features", [])
    camera_moves = analysis.get("camera_moves", ["slow pan"])
    mood = analysis.get("mood", "professional")
    
    # Build detailed prompt
    features_text = ", ".join(features[:3]) if features else "premium details"
    camera_text = camera_moves[0] if camera_moves else "slow cinematic pan"
    
    prompt = f"""Cinematic product video of this {product}. 
The camera performs a {camera_text}, highlighting {features_text}. 
Smooth, professional motion. {mood} lighting. 
High-end commercial quality. The product remains sharp and in focus throughout.
Subtle ambient movement. Premium showcase aesthetic."""
    
    return prompt[:500]  # Kling has prompt length limits


def render_kling_enhanced(image_url: str, prompt: str, use_end_frame: bool = True, duration: int = 5) -> dict:
    """
    Render video with Kling v2.1 using enhanced settings.
    
    If use_end_frame=True, uses the same image as start AND end frame
    to ensure the product appearance is preserved throughout.
    """
    print("\n" + "=" * 70)
    print("🎬 KLING ENHANCED RENDER")
    print("=" * 70)
    
    headers = {
        "Authorization": f"Bearer {FASTROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Build payload with enhanced settings
    payload = {
        "model": "kling-ai/kling-v2-1",
        "image_url": image_url,
        "prompt": prompt,
        "duration": duration,
        "aspect_ratio": "16:9",  # Widescreen for professional look
    }
    
    # Use same image as end frame to preserve product identity
    if use_end_frame:
        payload["image_end_url"] = image_url
        print("   ✅ Using START + END frame mode (product preservation)")
    
    print(f"   📝 Prompt: {prompt[:80]}...")
    print(f"   ⏱️  Duration: {duration}s")
    print(f"   📐 Aspect: 16:9 (widescreen)")
    
    # Submit task
    response = requests.post(
        f"{FASTROUTER_BASE_URL}/videos",
        headers=headers,
        json=payload,
        timeout=60
    )
    response.raise_for_status()
    result = response.json()
    
    task_id = result.get("data", {}).get("task_id") or result.get("task_id")
    print(f"   ✅ Task ID: {task_id}")
    print(f"   💰 Credits: ~0.21-0.42 (depending on mode)")
    
    # Poll for completion
    print("\n   ⏳ Rendering (enhanced mode may take 2-4 minutes)...")
    start_time = time.time()
    max_wait = 300  # 5 minutes max
    
    while True:
        elapsed = time.time() - start_time
        if elapsed > max_wait:
            raise TimeoutError("Render timeout exceeded")
        
        time.sleep(5)
        
        # Check status
        status_response = requests.get(
            f"{FASTROUTER_BASE_URL}/videos/{task_id}",
            headers=headers,
            timeout=30
        )
        status_data = status_response.json()
        
        # Parse status
        status = None
        video_url = None
        
        if "data" in status_data:
            data = status_data["data"]
            if "generations" in data and len(data["generations"]) > 0:
                gen = data["generations"][0]
                status = gen.get("status")
                video_url = gen.get("url")
            elif "status" in data:
                status = data["status"]
                video_url = data.get("url")
        
        # Progress indicator
        progress = min(95, int((elapsed / 180) * 100))
        bar = "█" * (progress // 5) + "░" * (20 - progress // 5)
        print(f"\r   ⏳ [{bar}] {progress}% ({int(elapsed)}s)", end="", flush=True)
        
        if status == "succeed" and video_url:
            print(f"\n   ✅ Video ready!")
            return {
                "task_id": task_id,
                "video_url": video_url,
                "duration": duration,
                "render_time": elapsed
            }
        elif status == "failed":
            raise Exception(f"Render failed: {status_data}")


def download_video(video_url: str, output_path: str) -> str:
    """Download video file."""
    print(f"   📥 Downloading video...")
    
    response = requests.get(video_url, timeout=120, stream=True)
    response.raise_for_status()
    
    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"   ✅ Saved: {output_path} ({size_mb:.2f} MB)")
    return output_path


def main(image_path: str):
    print_banner()
    
    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        sys.exit(1)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Step 1: Analyze image
    print("=" * 70)
    print("🧬 STEP 1: VISION ANALYSIS")
    print("=" * 70)
    
    try:
        analysis = analyze_image_with_vision(image_path)
        print(f"   ✅ Product: {analysis.get('product_type', 'unknown')}")
        print(f"   ✅ Features: {', '.join(analysis.get('key_features', [])[:3])}")
        print(f"   ✅ Mood: {analysis.get('mood', 'professional')}")
        
        # Save analysis
        analysis_path = OUTPUT_DIR / f"analysis_{timestamp}.json"
        with open(analysis_path, "w") as f:
            json.dump(analysis, f, indent=2)
        print(f"   💾 Saved: {analysis_path}")
        
    except Exception as e:
        print(f"   ⚠️ Vision analysis failed: {e}")
        analysis = {"product_type": "product", "key_features": [], "mood": "professional"}
    
    # Step 2: Generate optimized prompt
    print("\n" + "=" * 70)
    print("📝 STEP 2: GENERATE QUALITY PROMPT")
    print("=" * 70)
    
    prompt = generate_quality_prompt(analysis)
    print(f"   📝 Prompt ({len(prompt)} chars):")
    print(f"   {prompt[:150]}...")
    
    # Step 3: Upload to Azure
    print("\n" + "=" * 70)
    print("📤 STEP 3: UPLOAD TO AZURE")
    print("=" * 70)
    
    image_url = upload_to_azure(image_path)
    print(f"   ✅ URL: {image_url[:60]}...")
    
    # Step 4: Render with enhanced settings
    print("\n" + "=" * 70)
    print("🎬 STEP 4: ENHANCED KLING RENDER")
    print("=" * 70)
    
    print("\n   🔧 Enhanced Settings:")
    print("      • Start frame: Your image")
    print("      • End frame: Your image (preserves product)")
    print("      • Aspect: 16:9 widescreen")
    print("      • Duration: 5 seconds")
    
    result = render_kling_enhanced(
        image_url=image_url,
        prompt=prompt,
        use_end_frame=True,  # KEY: Uses image as both start AND end
        duration=5
    )
    
    # Step 5: Download
    video_path = OUTPUT_DIR / f"enhanced_{timestamp}.mp4"
    download_video(result["video_url"], str(video_path))
    
    # Summary
    print("\n" + "=" * 70)
    print("✅ ENHANCED PIPELINE COMPLETE")
    print("=" * 70)
    print(f"   📹 Video: {video_path}")
    print(f"   ⏱️  Render time: {result['render_time']:.1f}s")
    print(f"   🎯 Mode: Start+End frame (product preserved)")
    print("=" * 70)
    
    # Open video
    os.startfile(str(video_path))
    
    return str(video_path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_enhanced_pipeline.py <image_path>")
        sys.exit(1)
    
    main(sys.argv[1])
