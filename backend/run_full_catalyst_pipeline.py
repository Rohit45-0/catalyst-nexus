"""
🚀 CATALYST NEXUS - FULL INTELLIGENT PIPELINE
==============================================
Complete workflow:
1. VisionDNA Analysis → Extract product identity
2. Generate Dynamic Prompt → Based on extracted features
3. Kling I2V → Render video with intelligent prompt
"""

import asyncio
import os
import sys
import json
from pathlib import Path
from datetime import datetime
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent))
os.chdir(Path(__file__).parent)

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import httpx
from PIL import Image
import base64

# Azure connection for blob storage
AZURE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")

FASTROUTER_API_KEY = os.getenv("FASTROUTER_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_DEPLOYMENT = os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4o")

OUTPUT_DIR = Path("output/catalyst_videos")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def print_banner():
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║         🧬 CATALYST NEXUS - FULL INTELLIGENT PIPELINE 🧬             ║
╠══════════════════════════════════════════════════════════════════════╣
║  VisionDNA Analysis → Dynamic Prompt → Kling I2V → Final Video       ║
╚══════════════════════════════════════════════════════════════════════╝
""")


def image_to_base64(image_path: str) -> str:
    """Convert image to base64 for GPT-4o Vision."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


async def step1_vision_dna_analysis(image_path: str) -> dict:
    """
    STEP 1: VisionDNA Analysis
    Extract product identity using GPT-4o Vision
    """
    print("\n" + "="*70)
    print("🧬 STEP 1: VISION DNA ANALYSIS")
    print("="*70)
    print(f"   📷 Analyzing: {image_path}")
    
    # Convert image to base64
    img_base64 = image_to_base64(image_path)
    
    # Get image extension
    ext = Path(image_path).suffix.lower()
    media_type = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png"
    
    analysis_prompt = """Analyze this product image and extract detailed information for AI video generation.

Return a JSON object with:
{
    "product_category": "category (e.g., laptop, headphones, watch)",
    "product_description": "detailed one-paragraph description",
    "brand_detected": "brand name if visible, else 'unknown'",
    "materials": {
        "primary": "main material",
        "surface_finish": "matte|glossy|metallic|brushed",
        "colors": ["list of colors"],
        "reflectivity": "low|medium|high"
    },
    "lighting": {
        "type": "studio|natural|dramatic|ambient",
        "direction": "top|side|front|backlit",
        "mood": "professional|warm|cool|cinematic"
    },
    "structure": {
        "shape": "describe overall shape",
        "key_features": ["list distinctive features"],
        "orientation": "how product is positioned"
    },
    "video_recommendations": {
        "camera_movements": ["suggested camera moves"],
        "focus_points": ["what to highlight"],
        "mood_keywords": ["words describing ideal video mood"]
    }
}"""

    url = f"{AZURE_OPENAI_ENDPOINT.rstrip('/')}/openai/deployments/{AZURE_DEPLOYMENT}/chat/completions?api-version=2024-02-15-preview"
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            url,
            json={
                "messages": [
                    {
                        "role": "system", 
                        "content": "You are an expert product analyst. Always return valid JSON."
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": analysis_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{img_base64}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 1500,
                "temperature": 0.3,
            },
            headers={
                "Content-Type": "application/json",
                "api-key": AZURE_OPENAI_KEY,
            }
        )
        
        if response.status_code != 200:
            print(f"   ❌ GPT-4o Vision failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        
        # Parse JSON from response
        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            vision_dna = json.loads(content.strip())
            
            print(f"   ✅ Product: {vision_dna.get('product_category', 'Unknown')}")
            print(f"   ✅ Brand: {vision_dna.get('brand_detected', 'Unknown')}")
            print(f"   ✅ Materials: {vision_dna.get('materials', {}).get('primary', 'Unknown')}")
            print(f"   ✅ Surface: {vision_dna.get('materials', {}).get('surface_finish', 'Unknown')}")
            print(f"   ✅ Lighting: {vision_dna.get('lighting', {}).get('type', 'Unknown')}")
            
            return vision_dna
            
        except json.JSONDecodeError as e:
            print(f"   ⚠️ JSON parse error, using raw content")
            return {"raw_analysis": content}


async def step2_generate_dynamic_prompt(vision_dna: dict, style: str = "cinematic") -> str:
    """
    STEP 2: Generate Dynamic Video Prompt
    Create intelligent prompt based on VisionDNA analysis
    """
    print("\n" + "="*70)
    print("📝 STEP 2: GENERATE DYNAMIC PROMPT")
    print("="*70)
    
    # Extract key info from VisionDNA
    category = vision_dna.get("product_category", "product")
    description = vision_dna.get("product_description", "")
    materials = vision_dna.get("materials", {})
    lighting = vision_dna.get("lighting", {})
    structure = vision_dna.get("structure", {})
    recommendations = vision_dna.get("video_recommendations", {})
    
    colors = materials.get("colors", ["neutral"])
    surface = materials.get("surface_finish", "sleek")
    reflectivity = materials.get("reflectivity", "medium")
    light_type = lighting.get("type", "studio")
    light_mood = lighting.get("mood", "professional")
    key_features = structure.get("key_features", [])
    camera_moves = recommendations.get("camera_movements", ["slow rotation"])
    mood_keywords = recommendations.get("mood_keywords", ["premium", "elegant"])
    
    # Build intelligent prompt
    prompt_parts = [
        f"A {style} product showcase video of this {category}.",
    ]
    
    # Add camera movement
    if camera_moves:
        prompt_parts.append(f"The camera {camera_moves[0]}.")
    else:
        prompt_parts.append("The product elegantly rotates to showcase all angles.")
    
    # Add material/surface description
    if surface and reflectivity:
        if reflectivity == "high":
            prompt_parts.append(f"Light reflects beautifully off the {surface} surface, creating premium highlights.")
        else:
            prompt_parts.append(f"The {surface} finish gives a {mood_keywords[0] if mood_keywords else 'premium'} appearance.")
    
    # Add lighting description
    if light_type and light_mood:
        prompt_parts.append(f"{light_type.capitalize()} lighting with a {light_mood} atmosphere.")
    
    # Add key features focus
    if key_features:
        prompt_parts.append(f"Highlighting the {key_features[0]}.")
    
    # Add mood
    prompt_parts.append(f"The overall mood is {', '.join(mood_keywords[:2]) if mood_keywords else 'sophisticated and modern'}.")
    
    # Final polish
    prompt_parts.append("Smooth motion, high-end commercial quality, 4K cinematic look.")
    
    final_prompt = " ".join(prompt_parts)
    
    print(f"   📝 Generated Prompt:")
    print(f"   {final_prompt[:100]}...")
    print(f"   [Full length: {len(final_prompt)} chars]")
    
    return final_prompt


async def step3_upload_to_azure(image_path: str) -> str:
    """
    STEP 3: Upload Image to Azure Blob Storage
    """
    print("\n" + "="*70)
    print("📤 STEP 3: UPLOAD TO AZURE BLOB STORAGE")
    print("="*70)
    
    from azure.storage.blob import BlobServiceClient, ContentSettings
    
    blob_service = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
    
    try:
        container_client = blob_service.create_container("product-images", public_access="blob")
        print(f"   ✅ Created container: product-images")
    except Exception as e:
        if "ContainerAlreadyExists" in str(e):
            container_client = blob_service.get_container_client("product-images")
            print(f"   ✅ Using existing container: product-images")
        else:
            raise e
    
    filename = Path(image_path).name
    blob_name = f"{uuid4().hex[:8]}_{filename}"
    
    # Upload with proper content type
    ext = Path(image_path).suffix.lower()
    content_type = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png"
    
    blob_client = container_client.get_blob_client(blob_name)
    with open(image_path, "rb") as f:
        blob_client.upload_blob(
            f,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type)
        )
    
    url = f"https://rohitf.blob.core.windows.net/product-images/{blob_name}"
    print(f"   ✅ Uploaded: {url}")
    
    return url


async def step4_kling_render(image_url: str, prompt: str, duration: int = 5) -> dict:
    """
    STEP 4: Kling Image-to-Video Render
    """
    print("\n" + "="*70)
    print("🎬 STEP 4: KLING IMAGE-TO-VIDEO RENDER")
    print("="*70)
    print(f"   🔗 Image: {image_url[:60]}...")
    print(f"   📝 Prompt: {prompt[:80]}...")
    print(f"   ⏱️  Duration: {duration}s")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Submit render request
        response = await client.post(
            "https://go.fastrouter.ai/api/v1/videos",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {FASTROUTER_API_KEY}"
            },
            json={
                "model": "kling-ai/kling-v2-1",
                "image": image_url,
                "prompt": prompt,
                "length": duration
            }
        )
        
        if response.status_code != 200:
            print(f"   ❌ Kling request failed: {response.status_code}")
            print(f"   {response.text}")
            return None
        
        result = response.json()
        task_id = result.get("data", {}).get("taskId")
        credits = result.get("usage", {}).get("credits_used", 0)
        
        if not task_id:
            print(f"   ❌ No task ID received: {result}")
            return None
        
        print(f"   ✅ Task ID: {task_id}")
        print(f"   💰 Credits: {credits}")
        print(f"\n   ⏳ Generating video (typically 60-180 seconds)...")
        
        # Poll for completion
        start_time = asyncio.get_event_loop().time()
        max_wait = 300  # 5 minutes max
        poll_interval = 3
        
        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > max_wait:
                print(f"\n   ❌ Timeout after {max_wait}s")
                return {"task_id": task_id, "status": "timeout"}
            
            # Poll status
            poll_response = await client.post(
                "https://go.fastrouter.ai/api/v1/getVideoResponse",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {FASTROUTER_API_KEY}"
                },
                json={
                    "taskId": task_id,
                    "model": "kling-ai/kling-v2-1"
                }
            )
            
            content_type = poll_response.headers.get("content-type", "")
            content_length = len(poll_response.content)
            
            # Check if we got video data
            if "video" in content_type or content_length > 100000:
                # Save video
                video_path = OUTPUT_DIR / f"catalyst_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
                with open(video_path, "wb") as f:
                    f.write(poll_response.content)
                
                print(f"\n   ✅ Video generated in {elapsed:.1f}s!")
                print(f"   ✅ Saved: {video_path}")
                print(f"   ✅ Size: {content_length / 1024 / 1024:.2f} MB")
                
                return {
                    "task_id": task_id,
                    "status": "completed",
                    "video_path": str(video_path),
                    "size_bytes": content_length,
                    "generation_time": elapsed
                }
            
            # Check JSON response for status
            try:
                data = poll_response.json()
                generations = data.get("data", {}).get("generations", [])
                
                if generations:
                    gen = generations[0]
                    status = gen.get("status", "")
                    
                    if status == "succeed":
                        video_url = gen.get("url", "")
                        if video_url:
                            print(f"\n   ✅ Video ready! Downloading...")
                            # Download video
                            vid_response = await client.get(video_url, timeout=120.0)
                            video_path = OUTPUT_DIR / f"catalyst_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
                            with open(video_path, "wb") as f:
                                f.write(vid_response.content)
                            
                            print(f"   ✅ Saved: {video_path}")
                            return {
                                "task_id": task_id,
                                "status": "completed",
                                "video_path": str(video_path),
                                "video_url": video_url,
                                "generation_time": elapsed
                            }
                    
                    elif status == "failed":
                        fail_msg = gen.get("failMsg", "Unknown error")
                        print(f"\n   ❌ Generation failed: {fail_msg}")
                        return {"task_id": task_id, "status": "failed", "error": fail_msg}
                    
            except:
                pass
            
            # Progress indicator
            progress = min(95, int(elapsed / max_wait * 100))
            bars = "█" * (progress // 5) + "░" * (20 - progress // 5)
            print(f"\r   ⏳ [{bars}] {progress}% ({int(elapsed)}s)", end="", flush=True)
            
            await asyncio.sleep(poll_interval)


async def run_full_pipeline(image_path: str):
    """
    Run the complete Catalyst Nexus pipeline
    """
    print_banner()
    
    # Validate inputs
    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        return
    
    if not FASTROUTER_API_KEY:
        print("❌ FASTROUTER_API_KEY not set")
        return
    
    if not AZURE_OPENAI_KEY:
        print("❌ AZURE_OPENAI_API_KEY not set")
        return
    
    print(f"✅ FastRouter API Key: {FASTROUTER_API_KEY[:20]}...")
    print(f"✅ Azure OpenAI: {AZURE_OPENAI_ENDPOINT[:40]}...")
    print(f"📷 Input Image: {image_path}")
    
    start_time = asyncio.get_event_loop().time()
    
    # STEP 1: VisionDNA Analysis
    vision_dna = await step1_vision_dna_analysis(image_path)
    if not vision_dna:
        print("\n❌ VisionDNA analysis failed")
        return
    
    # Save VisionDNA to file
    dna_path = OUTPUT_DIR / f"vision_dna_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(dna_path, "w") as f:
        json.dump(vision_dna, f, indent=2)
    print(f"\n   💾 VisionDNA saved: {dna_path}")
    
    # STEP 2: Generate Dynamic Prompt
    prompt = await step2_generate_dynamic_prompt(vision_dna, style="cinematic")
    
    # STEP 3: Upload to Azure
    image_url = await step3_upload_to_azure(image_path)
    
    # STEP 4: Kling Render
    result = await step4_kling_render(image_url, prompt, duration=5)
    
    # Summary
    total_time = asyncio.get_event_loop().time() - start_time
    print("\n" + "="*70)
    print("🎉 PIPELINE COMPLETE")
    print("="*70)
    print(f"   ⏱️  Total Time: {total_time:.1f}s")
    if result and result.get("status") == "completed":
        print(f"   🎬 Output: {result.get('video_path')}")
    print("="*70)
    
    return result


if __name__ == "__main__":
    # Default image path
    image_path = r"D:\Catalyst Nexus\896332-2560x1440-desktop-hd-laptop-background-image.jpg"
    
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    
    asyncio.run(run_full_pipeline(image_path))
