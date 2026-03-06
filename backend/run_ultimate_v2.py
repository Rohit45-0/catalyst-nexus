"""
🚀 CATALYST NEXUS - ULTIMATE PIPELINE v2
==========================================
Now with DISCOVERED undocumented parameters:
- image_tail: End frame lock (same image = identity preservation)
- negative_prompt: Avoid hallucination
- cfg_scale: Prompt adherence
- camera_control: Motion guidance

This is the BEST we can achieve with FastRouter!
"""

import os
import sys
import json
import time
import base64
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent))
os.chdir(Path(__file__).parent)

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

FASTROUTER_API_KEY = os.getenv("FASTROUTER_API_KEY")
FASTROUTER_BASE_URL = "https://go.fastrouter.ai/api/v1"

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_DEPLOYMENT = os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4o")
AZURE_API_VERSION = os.getenv("AZURE_API_VERSION", "2024-02-15-preview")

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")

OUTPUT_DIR = Path("output/ultimate_v2")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def print_banner():
    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║       🎬 CATALYST NEXUS - ULTIMATE PIPELINE v2 🎬                        ║
╠══════════════════════════════════════════════════════════════════════════╣
║  🔓 UNLOCKED: image_tail + negative_prompt + cfg_scale + camera_control  ║
║  ─────────────────────────────────────────────────────────────────────── ║
║  Maximum quality with ALL discovered parameters                          ║
╚══════════════════════════════════════════════════════════════════════════╝
""")


def upload_to_azure(image_path: str) -> str:
    """Upload image to Azure Blob Storage."""
    from azure.storage.blob import BlobServiceClient, ContentSettings
    
    blob_service = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    container_client = blob_service.get_container_client("product-images")
    
    try:
        container_client.create_container()
    except:
        pass
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    blob_name = f"ultimate_v2_{timestamp}_{Path(image_path).name}"
    
    blob_client = container_client.get_blob_client(blob_name)
    with open(image_path, "rb") as f:
        blob_client.upload_blob(f, overwrite=True, 
            content_settings=ContentSettings(content_type="image/jpeg"))
    
    return f"https://rohitf.blob.core.windows.net/product-images/{blob_name}"


def analyze_vision_dna(image_path: str) -> Dict[str, Any]:
    """Deep VisionDNA analysis for optimal prompt + camera motion."""
    
    print("\n" + "═" * 70)
    print("🧬 STEP 1: VISION DNA ANALYSIS")
    print("═" * 70)
    
    with open(image_path, "rb") as f:
        image_base64 = base64.b64encode(f.read()).decode("utf-8")
    
    ext = Path(image_path).suffix.lower()
    mime_type = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png"
    
    system_prompt = """Analyze this product for VIDEO generation. Return JSON:

{
    "product": {
        "category": "laptop/phone/watch/etc",
        "material": "metal/plastic/glass",
        "finish": "matte/glossy/brushed"
    },
    "camera_recommendation": {
        "motion_type": "pan/orbit/zoom/dolly",
        "direction": "left/right/clockwise/in/out",
        "speed": "slow/medium",
        "focus_on": "what to highlight"
    },
    "prompt_keywords": ["keyword1", "keyword2", "keyword3"],
    "avoid_keywords": ["things that would look bad"]
}"""

    headers = {"Content-Type": "application/json", "api-key": AZURE_OPENAI_KEY}
    
    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [
                {"type": "text", "text": "Analyze for video:"},
                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_base64}"}}
            ]}
        ],
        "max_tokens": 1000,
        "response_format": {"type": "json_object"}
    }
    
    print("   📷 Analyzing with GPT-4o Vision...")
    url = f"{AZURE_OPENAI_ENDPOINT}openai/deployments/{AZURE_DEPLOYMENT}/chat/completions?api-version={AZURE_API_VERSION}"
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    
    dna = json.loads(response.json()["choices"][0]["message"]["content"])
    
    print(f"   ✅ Product: {dna.get('product', {}).get('category', 'unknown')}")
    print(f"   ✅ Material: {dna.get('product', {}).get('material', 'unknown')}")
    print(f"   ✅ Camera: {dna.get('camera_recommendation', {}).get('motion_type', 'orbit')}")
    
    return dna


def build_ultimate_payload(image_url: str, dna: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build the ULTIMATE payload with ALL discovered parameters.
    """
    print("\n" + "═" * 70)
    print("📝 STEP 2: BUILD ULTIMATE PAYLOAD")
    print("═" * 70)
    
    product = dna.get("product", {})
    camera = dna.get("camera_recommendation", {})
    keywords = dna.get("prompt_keywords", [])
    avoid = dna.get("avoid_keywords", [])
    
    # Build smart prompt
    category = product.get("category", "product")
    material = product.get("material", "")
    finish = product.get("finish", "")
    motion = camera.get("motion_type", "orbit")
    direction = camera.get("direction", "clockwise")
    focus = camera.get("focus_on", "details")
    
    prompt = f"""Cinematic product video of this {material} {finish} {category}. 
Smooth {motion} camera movement {direction}. 
Focus on {focus}. Premium commercial quality, sharp details, professional lighting.
{' '.join(keywords[:5])}"""
    
    # Build negative prompt
    negative = "blurry, distorted, morphing, low quality, changing shape, incorrect proportions"
    if avoid:
        negative += ", " + ", ".join(avoid[:5])
    
    # Build camera control
    camera_control = {
        "type": camera.get("motion_type", "orbit"),
        "horizontal": 5 if direction in ["left", "clockwise"] else -5,
        "vertical": 0
    }
    
    payload = {
        "model": "kling-ai/kling-v2-1",
        "image": image_url,                    # Start frame
        "image_tail": image_url,               # 🔥 END FRAME = SAME (identity lock!)
        "prompt": prompt[:500],
        "negative_prompt": negative[:200],     # 🔥 Avoid hallucination
        "length": 5,
        "cfg_scale": 0.5,                      # 🔥 Prompt adherence
        "camera_control": camera_control       # 🔥 Motion guidance!
    }
    
    print(f"   ✅ Start Frame: {image_url[:50]}...")
    print(f"   ✅ End Frame: SAME AS START (identity lock)")
    print(f"   ✅ Prompt: {prompt[:80]}...")
    print(f"   ✅ Negative: {negative[:60]}...")
    print(f"   ✅ CFG Scale: 0.5")
    print(f"   ✅ Camera: {camera_control}")
    
    return payload


def render_ultimate(payload: Dict[str, Any]) -> Dict:
    """Submit and poll for ultimate render."""
    
    print("\n" + "═" * 70)
    print("🎬 STEP 3: KLING ULTIMATE RENDER")
    print("═" * 70)
    
    headers = {
        "Authorization": f"Bearer {FASTROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    print("   📤 Submitting with ALL optimizations...")
    print(f"   📦 Payload keys: {list(payload.keys())}")
    
    response = requests.post(
        f"{FASTROUTER_BASE_URL}/videos",
        headers=headers,
        json=payload,
        timeout=60
    )
    
    print(f"   📥 Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"   ❌ Error: {response.text[:500]}")
        raise Exception(f"API Error: {response.text}")
    
    result = response.json()
    task_id = result.get("data", {}).get("taskId") or result.get("data", {}).get("task_id")
    credits = result.get("usage", {}).get("credits_used", 0.21)
    
    print(f"   ✅ Task ID: {task_id}")
    print(f"   💰 Credits: {credits}")
    
    # Poll
    print(f"\n   ⏳ Rendering with identity lock + camera control...")
    start_time = time.time()
    
    while True:
        elapsed = time.time() - start_time
        if elapsed > 300:
            raise TimeoutError("Timeout after 5 minutes")
        
        time.sleep(5)
        
        status_response = requests.get(
            f"{FASTROUTER_BASE_URL}/videos/{task_id}",
            headers=headers,
            timeout=30
        )
        data = status_response.json()
        
        status = None
        video_url = None
        
        if "data" in data:
            d = data["data"]
            if "generations" in d and len(d["generations"]) > 0:
                gen = d["generations"][0]
                status = gen.get("status")
                video_url = gen.get("url")
        
        progress = min(95, int((elapsed / 180) * 100))
        bar = "█" * (progress // 5) + "░" * (20 - progress // 5)
        print(f"\r   ⏳ [{bar}] {progress}% ({int(elapsed)}s)", end="", flush=True)
        
        if status == "succeed" and video_url:
            print(f"\n   ✅ Video ready!")
            return {"task_id": task_id, "video_url": video_url, "render_time": elapsed}
        elif status == "failed":
            raise Exception(f"Render failed: {data}")


def download_video(video_url: str, output_path: str) -> str:
    """Download video file."""
    response = requests.get(video_url, timeout=120, stream=True)
    response.raise_for_status()
    
    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"   ✅ Saved: {output_path} ({size_mb:.2f} MB)")
    return output_path


def main(image_path: str):
    """Run the ULTIMATE v2 pipeline."""
    print_banner()
    
    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        sys.exit(1)
    
    print(f"📷 Input: {image_path}")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Step 1: VisionDNA
    dna = analyze_vision_dna(image_path)
    
    # Save DNA
    dna_path = OUTPUT_DIR / f"dna_{timestamp}.json"
    with open(dna_path, "w") as f:
        json.dump(dna, f, indent=2)
    
    # Step 2: Upload
    print("\n" + "═" * 70)
    print("📤 UPLOADING TO AZURE")
    print("═" * 70)
    image_url = upload_to_azure(image_path)
    print(f"   ✅ URL: {image_url[:60]}...")
    
    # Step 3: Build ultimate payload
    payload = build_ultimate_payload(image_url, dna)
    
    # Save payload for debugging
    payload_path = OUTPUT_DIR / f"payload_{timestamp}.json"
    with open(payload_path, "w") as f:
        json.dump(payload, f, indent=2)
    
    # Step 4: Render
    result = render_ultimate(payload)
    
    # Step 5: Download
    video_path = OUTPUT_DIR / f"ultimate_v2_{timestamp}.mp4"
    download_video(result["video_url"], str(video_path))
    
    # Summary
    print("\n" + "═" * 70)
    print("🎉 ULTIMATE v2 PIPELINE COMPLETE")
    print("═" * 70)
    print(f"   📹 Video: {video_path}")
    print(f"   🧬 DNA: {dna_path}")
    print(f"   ⏱️  Render: {result['render_time']:.1f}s")
    print()
    print("   🔓 UNLOCKED FEATURES USED:")
    print("      ✓ image_tail: End frame = Start frame (identity lock)")
    print("      ✓ negative_prompt: Anti-hallucination")
    print("      ✓ cfg_scale: Prompt adherence")
    print("      ✓ camera_control: Motion guidance")
    print("═" * 70)
    
    # Open video
    os.startfile(str(video_path))
    
    return str(video_path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_ultimate_v2.py <image_path>")
        sys.exit(1)
    
    main(sys.argv[1])
