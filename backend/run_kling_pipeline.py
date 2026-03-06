"""
🚀 CATALYST NEXUS - KLING IMAGE-TO-VIDEO PIPELINE
==================================================
Uses Azure Blob Storage to host image → Kling animates YOUR product
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent))
os.chdir(Path(__file__).parent)

from dotenv import load_dotenv
# Load .env from parent directory (catalyst-nexus-core)
load_dotenv(Path(__file__).parent.parent / ".env")

import httpx
from PIL import Image


def resize_image_for_kling(image_path: str) -> str:
    """
    Resize image to meet Kling's minimum requirements.
    Kling requires minimum 720p resolution for good results.
    Returns path to resized image (temp file).
    """
    img = Image.open(image_path)
    width, height = img.size
    
    # Kling v2.1 works best with 16:9 or 9:16 aspect ratios
    # Minimum dimension should be at least 720 pixels
    MIN_DIM = 720
    TARGET_SHORT_SIDE = 1080  # Upscale to 1080p for quality
    
    print(f"   📐 Original size: {width}x{height}")
    
    # Calculate scale factor
    short_side = min(width, height)
    if short_side < MIN_DIM:
        scale = TARGET_SHORT_SIDE / short_side
        new_width = int(width * scale)
        new_height = int(height * scale)
        
        # Use LANCZOS for high-quality upscaling
        img = img.resize((new_width, new_height), Image.LANCZOS)
        print(f"   📐 Resized to: {new_width}x{new_height} (Kling requires min 720p)")
    else:
        print(f"   ✅ Size OK for Kling")
        return image_path  # No resize needed
    
    # Save to temp file
    temp_path = Path(image_path).parent / f"_kling_resized_{Path(image_path).name}"
    img.save(temp_path, "JPEG", quality=95)
    print(f"   ✅ Saved resized image: {temp_path}")
    
    return str(temp_path)

# =============================================================================
# CONFIGURATION
# =============================================================================

AZURE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")

FASTROUTER_API_KEY = os.getenv("FASTROUTER_API_KEY")
CONTAINER_NAME = "product-images"
OUTPUT_DIR = Path("output/kling_videos")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def upload_to_azure(local_path: str) -> str:
    """Upload image to Azure Blob Storage and return public URL."""
    from azure.storage.blob import BlobServiceClient, ContentSettings
    
    print("   📤 Uploading to Azure Blob Storage...")
    
    # Create blob service client
    blob_service = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
    
    # Create container if not exists (with public access)
    try:
        container_client = blob_service.create_container(
            CONTAINER_NAME, 
            public_access="blob"
        )
        print(f"   ✅ Created container: {CONTAINER_NAME}")
    except Exception as e:
        if "ContainerAlreadyExists" in str(e):
            container_client = blob_service.get_container_client(CONTAINER_NAME)
            print(f"   ✅ Using existing container: {CONTAINER_NAME}")
        else:
            raise e
    
    # Upload the file
    filename = Path(local_path).name
    blob_name = f"{uuid4().hex[:8]}_{filename}"
    
    blob_client = blob_service.get_blob_client(CONTAINER_NAME, blob_name)
    
    with open(local_path, "rb") as f:
        blob_client.upload_blob(
            f, 
            overwrite=True,
            content_settings=ContentSettings(content_type="image/jpeg")
        )
    
    # Get public URL
    public_url = f"https://rohitf.blob.core.windows.net/{CONTAINER_NAME}/{blob_name}"
    print(f"   ✅ Uploaded: {public_url}")
    
    return public_url


async def run_kling_pipeline(image_path: str):
    """Run Kling image-to-video with Azure-hosted image."""
    
    print()
    print("╔" + "═" * 62 + "╗")
    print("║" + "  🚀 CATALYST NEXUS - KLING IMAGE-TO-VIDEO".center(62) + "║")
    print("╠" + "═" * 62 + "╣")
    print("║" + "  Your ACTUAL product will be animated!".center(62) + "║")
    print("╚" + "═" * 62 + "╝")
    print()
    
    if not FASTROUTER_API_KEY:
        print("❌ FASTROUTER_API_KEY not set")
        return
    
    print(f"✅ FastRouter API Key: {FASTROUTER_API_KEY[:20]}...")
    print(f"📷 Image: {image_path}")
    
    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        return
    
    # Step 1: Resize image if needed (Kling requires min 720p)
    print()
    print("=" * 64)
    print("📐 STEP 1: Prepare Image (Resize for Kling)")
    print("=" * 64)
    
    try:
        resized_path = resize_image_for_kling(image_path)
    except Exception as e:
        print(f"   ❌ Image resize failed: {e}")
        print("   Installing Pillow...")
        os.system("pip install Pillow -q")
        resized_path = resize_image_for_kling(image_path)
    
    # Step 2: Upload to Azure
    print()
    print("=" * 64)
    print("📤 STEP 2: Upload Image to Azure Blob Storage")
    print("=" * 64)
    
    try:
        image_url = upload_to_azure(resized_path)
    except Exception as e:
        print(f"   ❌ Azure upload failed: {e}")
        print("   Installing azure-storage-blob...")
        os.system("pip install azure-storage-blob -q")
        try:
            image_url = upload_to_azure(resized_path)
        except Exception as e2:
            print(f"   ❌ Still failed: {e2}")
            return
    
    # Step 3: Send to Kling
    print()
    print("=" * 64)
    print("🎬 STEP 3: Kling Image-to-Video (Your HP Laptop)")
    print("=" * 64)
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {FASTROUTER_API_KEY}",
    }
    
    # Kling v2.1 payload with image URL
    kling_payload = {
        "model": "kling-ai/kling-v2-1",
        "image": image_url,
        "prompt": (
            "A cinematic product showcase video. The laptop elegantly rotates 180 degrees "
            "on a dark reflective surface with dramatic studio lighting. Smooth slow motion, "
            "professional product photography style, 4K quality, spotlight effect."
        ),
        "length": 5,
    }
    
    print(f"   🔗 Image URL: {image_url}")
    print(f"   📝 Prompt: {kling_payload['prompt'][:80]}...")
    print(f"   ⏱️  Duration: 5 seconds")
    print()
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        print("   🚀 Sending to Kling v2.1...")
        
        response = await client.post(
            "https://go.fastrouter.ai/api/v1/videos",
            json=kling_payload,
            headers=headers,
        )
        
        print(f"   📡 Response: {response.status_code}")
        
        if response.status_code not in [200, 201, 202]:
            print(f"   ❌ Error: {response.text[:500]}")
            return
        
        result = response.json()
        # FastRouter returns: {"data": {"taskId": "..."}, "usage": {...}}
        task_id = result.get("data", {}).get("taskId") or result.get("id") or result.get("taskId")
        
        print(f"   ✅ Task ID: {task_id}")
        print(f"   💰 Credits: {result.get('usage', {}).get('credits_used', 'N/A')}")
        print(f"   📊 Status: {result.get('data', {}).get('status', 'N/A')}")
        print()
        print("   ⏳ Generating video (60-180 seconds)...")
        print()
        
        # Poll for completion - use correct model name for Kling
        # Kling I2V can take 3-8 minutes, set timeout to 10 minutes
        poll_payload = {"taskId": task_id, "model": "kling-ai/kling-v2-1"}
        
        for attempt in range(200):  # 10 minutes max (200 * 3s = 600s)
            await asyncio.sleep(3)
            
            progress = min(10 + attempt, 95)
            bar = "█" * (progress // 5) + "░" * (20 - progress // 5)
            print(f"\r   ⏳ [{bar}] {progress}% ({attempt * 3}s)", end="", flush=True)
            
            poll_resp = await client.post(
                "https://go.fastrouter.ai/api/v1/getVideoResponse",
                json=poll_payload,
                headers=headers,
            )
            
            if poll_resp.status_code != 200:
                continue
            
            content_type = poll_resp.headers.get("content-type", "")
            
            # Binary video received
            if "video" in content_type or "octet-stream" in content_type or len(poll_resp.content) > 100000:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                video_path = OUTPUT_DIR / f"kling_hp_laptop_{ts}.mp4"
                
                with open(video_path, "wb") as f:
                    f.write(poll_resp.content)
                
                print()
                print()
                print("=" * 64)
                print("🎬 SUCCESS! Your HP Laptop Video is Ready!")
                print("=" * 64)
                print(f"   📁 File: {video_path}")
                print(f"   📦 Size: {len(poll_resp.content) / 1024 / 1024:.2f} MB")
                print()
                print("   🎯 This is YOUR actual laptop animated - not a generic one!")
                print()
                
                # Open the video
                import subprocess
                subprocess.Popen(["start", "", str(video_path)], shell=True)
                return str(video_path)
            
            # Check JSON status
            try:
                status_result = poll_resp.json()
                data = status_result.get("data", {})
                generations = data.get("generations", [])
                
                # Check for early failure
                if generations:
                    gen = generations[0]
                    gen_status = gen.get("status", "")
                    
                    if gen_status == "failed":
                        fail_msg = gen.get("failMsg", "Unknown error")
                        print(f"\n   ❌ Kling failed: {fail_msg}")
                        return None
                    
                    if gen_status == "completed" or gen_status == "success":
                        video_url = gen.get("url")
                        if video_url:
                            print(f"\n   🎬 Video URL found: {video_url[:60]}...")
                            vid_resp = await client.get(video_url)
                            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                            video_path = OUTPUT_DIR / f"kling_hp_laptop_{ts}.mp4"
                            with open(video_path, "wb") as f:
                                f.write(vid_resp.content)
                            print()
                            print("=" * 64)
                            print("🎬 SUCCESS! Your HP Laptop Video is Ready!")
                            print("=" * 64)
                            print(f"   📁 File: {video_path}")
                            print(f"   📦 Size: {len(vid_resp.content) / 1024 / 1024:.2f} MB")
                            print()
                            import subprocess
                            subprocess.Popen(["start", "", str(video_path)], shell=True)
                            return str(video_path)
                
                # Legacy status checking
                status = status_result.get("status", "")
                
                if status in ["completed", "success", "done"]:
                    video_url = status_result.get("url") or status_result.get("video_url")
                    if video_url:
                        vid_resp = await client.get(video_url)
                        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                        video_path = OUTPUT_DIR / f"kling_hp_laptop_{ts}.mp4"
                        with open(video_path, "wb") as f:
                            f.write(vid_resp.content)
                        print()
                        print(f"\n   ✅ Video saved: {video_path}")
                        import subprocess
                        subprocess.Popen(["start", "", str(video_path)], shell=True)
                        return str(video_path)
                
                if status in ["failed", "error"]:
                    print(f"\n   ❌ Kling failed: {status_result}")
                    return None
            except:
                pass
        
        print("\n   ❌ Timed out after 10 minutes")
        return None


if __name__ == "__main__":
    image_path = r"D:\Catalyst Nexus\laptop.jpg"
    
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    
    asyncio.run(run_kling_pipeline(image_path))
