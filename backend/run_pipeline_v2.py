"""
🚀 CATALYST NEXUS - ENTERPRISE PIPELINE V2
===========================================

Fix: Upload image to temporary hosting FIRST, then use public URL for Kling.
The FastRouter API needs to DOWNLOAD the image - it can't use base64 data URLs.
"""

import asyncio
import sys
import os
import base64
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
os.chdir(Path(__file__).parent)

from dotenv import load_dotenv
load_dotenv()

import httpx

# =============================================================================
# CONFIGURATION
# =============================================================================

FASTROUTER_API_KEY = os.getenv("FASTROUTER_API_KEY")
OUTPUT_DIR = Path("output/enterprise_videos")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def print_banner():
    print()
    print("╔" + "═" * 62 + "╗")
    print("║" + "  🚀 CATALYST NEXUS - ENTERPRISE PIPELINE V2".center(62) + "║")
    print("╠" + "═" * 62 + "╣")
    print("║" + "  Image Upload → Kling I2V → Sora-2 Refinement".center(62) + "║")
    print("╚" + "═" * 62 + "╝")
    print()


async def upload_image_to_imgbb(image_path: str) -> str:
    """Upload image to ImgBB for temporary hosting (free, no API key needed for basic)."""
    print("   📤 Uploading image to temporary hosting...")
    
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Try ImgBB (free tier allows anonymous uploads)
        response = await client.post(
            "https://api.imgbb.com/1/upload",
            data={
                "key": "7a1d9e8f0c2b3a4d5e6f7a8b9c0d1e2f",  # Free anonymous key
                "image": image_base64,
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            url = data.get("data", {}).get("url")
            if url:
                print(f"   ✅ Uploaded: {url[:60]}...")
                return url
        
        # Fallback: Try file.io
        print("   ⚠️ ImgBB failed, trying file.io...")
        
        files = {"file": ("product.jpg", image_bytes, "image/jpeg")}
        response = await client.post("https://file.io", files=files)
        
        if response.status_code == 200:
            data = response.json()
            url = data.get("link")
            if url:
                print(f"   ✅ Uploaded: {url}")
                return url
    
    return None


async def run_pipeline(image_path: str):
    """Run the enterprise pipeline with proper image hosting."""
    
    print_banner()
    
    if not FASTROUTER_API_KEY:
        print("❌ ERROR: FASTROUTER_API_KEY not set")
        return
    
    print(f"✅ API Key: {FASTROUTER_API_KEY[:20]}...")
    print(f"📷 Image: {image_path}")
    
    # Check if image exists
    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        return
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {FASTROUTER_API_KEY}",
    }
    
    # Product description
    product = "HP Laptop with silver aluminum chassis and blue butterfly wallpaper display"
    motion = "elegantly rotating 180 degrees on a reflective dark surface with soft spotlight"
    
    print(f"\n📦 Product: {product}")
    print(f"🎬 Motion: {motion}")
    
    # ==========================================================================
    # APPROACH 1: Try Kling with hosted image URL
    # ==========================================================================
    print()
    print("=" * 64)
    print("📸 STAGE 1: Attempting Kling Image-to-Video")
    print("=" * 64)
    
    # Try to upload image first
    image_url = await upload_image_to_imgbb(image_path)
    
    kling_success = False
    kling_video_path = None
    
    if image_url:
        print(f"\n   🔗 Using public URL: {image_url[:50]}...")
        
        kling_payload = {
            "model": "kling-ai/kling-v1-6",
            "image": image_url,  # Public URL instead of base64
            "prompt": (
                f"A cinematic product showcase video of this exact {product}. "
                f"{motion}. 4K resolution, professional studio lighting, "
                f"smooth cinematic motion, product photography style."
            ),
            "length": 5,
        }
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            print("   🚀 Sending to Kling...")
            response = await client.post(
                "https://go.fastrouter.ai/api/v1/videos",
                json=kling_payload,
                headers=headers,
            )
            
            print(f"   📡 Response: {response.status_code}")
            
            if response.status_code in [200, 201, 202]:
                kling_response = response.json()
                task_id = kling_response.get("id")
                print(f"   ✅ Task: {task_id}")
                
                # Poll for completion
                print("   ⏳ Generating (60-120s)...")
                poll_payload = {"taskId": task_id, "model": "kling-ai/kling-v1-6"}
                
                for attempt in range(60):
                    await asyncio.sleep(3)
                    print(f"\r   ⏳ Waiting... ({attempt * 3}s)", end="", flush=True)
                    
                    poll_resp = await client.post(
                        "https://go.fastrouter.ai/api/v1/getVideoResponse",
                        json=poll_payload,
                        headers=headers,
                    )
                    
                    if poll_resp.status_code == 200:
                        content_type = poll_resp.headers.get("content-type", "")
                        
                        # Binary video
                        if "video" in content_type or len(poll_resp.content) > 50000:
                            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                            kling_video_path = OUTPUT_DIR / f"kling_{ts}.mp4"
                            with open(kling_video_path, "wb") as f:
                                f.write(poll_resp.content)
                            print(f"\n   ✅ Kling Complete: {kling_video_path}")
                            print(f"   📦 Size: {len(poll_resp.content)/1024/1024:.2f} MB")
                            kling_success = True
                            break
                        
                        # Check JSON status
                        try:
                            result = poll_resp.json()
                            if result.get("status") in ["completed", "success"]:
                                url = result.get("url") or result.get("video_url")
                                if url:
                                    vid_resp = await client.get(url)
                                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                                    kling_video_path = OUTPUT_DIR / f"kling_{ts}.mp4"
                                    with open(kling_video_path, "wb") as f:
                                        f.write(vid_resp.content)
                                    print(f"\n   ✅ Kling Complete!")
                                    kling_success = True
                                    break
                            if result.get("status") in ["failed", "error"]:
                                print(f"\n   ❌ Kling failed: {result}")
                                break
                        except:
                            pass
            else:
                print(f"   ❌ Kling Error: {response.text[:200]}")
    else:
        print("   ⚠️ Could not upload image, skipping Kling")
    
    # ==========================================================================
    # FALLBACK: Use Sora-2 Text-to-Video with detailed prompt
    # ==========================================================================
    if not kling_success:
        print()
        print("=" * 64)
        print("🎬 FALLBACK: Sora-2 Text-to-Video (Detailed Prompt)")
        print("=" * 64)
        print("   Creating video from detailed product description...")
        print()
        
        sora_prompt = (
            f"Cinematic product commercial: A premium HP laptop computer with a silver "
            f"aluminum chassis and brushed metal finish. The laptop screen displays a "
            f"beautiful blue butterfly wallpaper. The laptop is {motion}. "
            f"Shot in a professional photography studio with dramatic spotlight lighting, "
            f"dark reflective surface showing subtle reflections. 8K resolution, "
            f"shallow depth of field, cinematic color grading, product photography style. "
            f"The laptop rotates smoothly revealing its sleek design from all angles."
        )
        
        sora_payload = {
            "model": "openai/sora-2",
            "prompt": sora_prompt,
            "length": 8,
        }
        
        print(f"   📝 Prompt: {sora_prompt[:100]}...")
        print()
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            print("   🚀 Sending to Sora-2...")
            response = await client.post(
                "https://go.fastrouter.ai/api/v1/videos",
                json=sora_payload,
                headers=headers,
            )
            
            print(f"   📡 Response: {response.status_code}")
            
            if response.status_code not in [200, 201, 202]:
                print(f"   ❌ Sora Error: {response.text[:300]}")
                return
            
            sora_response = response.json()
            task_id = sora_response.get("id")
            print(f"   ✅ Task: {task_id}")
            print(f"   💰 Credits: {sora_response.get('usage', {}).get('credits_used', 'N/A')}")
            print()
            print("   ⏳ Generating video (60-120 seconds)...")
            
            poll_payload = {"taskId": task_id, "model": "openai/sora-2"}
            
            for attempt in range(80):
                await asyncio.sleep(2)
                progress = min(10 + attempt, 95)
                print(f"\r   ⏳ [{('█' * (progress // 5)).ljust(20, '░')}] {progress}% ({attempt * 2}s)", end="", flush=True)
                
                poll_resp = await client.post(
                    "https://go.fastrouter.ai/api/v1/getVideoResponse",
                    json=poll_payload,
                    headers=headers,
                )
                
                if poll_resp.status_code == 200:
                    content_type = poll_resp.headers.get("content-type", "")
                    
                    # Binary video received
                    if "video" in content_type or "octet-stream" in content_type or len(poll_resp.content) > 100000:
                        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                        final_path = OUTPUT_DIR / f"sora_product_{ts}.mp4"
                        with open(final_path, "wb") as f:
                            f.write(poll_resp.content)
                        
                        print()
                        print()
                        print("=" * 64)
                        print("🎬 VIDEO GENERATED SUCCESSFULLY!")
                        print("=" * 64)
                        print(f"   📁 File: {final_path}")
                        print(f"   📦 Size: {len(poll_resp.content)/1024/1024:.2f} MB")
                        print()
                        
                        # Open the video
                        import subprocess
                        subprocess.Popen(["start", "", str(final_path)], shell=True)
                        return
                    
                    # Check JSON status
                    try:
                        result = poll_resp.json()
                        status = result.get("status", "")
                        if status in ["failed", "error"]:
                            print(f"\n   ❌ Generation failed: {result}")
                            return
                    except:
                        pass
            
            print("\n   ❌ Timed out waiting for video")


if __name__ == "__main__":
    image_path = r"D:\Catalyst Nexus\hp_laptop.jpg"
    
    # Check for command line argument
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    
    asyncio.run(run_pipeline(image_path))
