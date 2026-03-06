
import asyncio
import os
import json
import httpx
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)
FASTROUTER_API_KEY = os.getenv("FASTROUTER_API_KEY")

if not FASTROUTER_API_KEY:
    print("❌ API Key not found in .env")
    exit(1)
    
FASTROUTER_STATUS_URL = "https://go.fastrouter.ai/api/v1/getVideoResponse"
OUTPUT_DIR = Path("backend/output/full_pipeline")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

async def recover_video(task_id: str):
    print(f"🔄 Attempting to recover video for Task ID: {task_id}")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {FASTROUTER_API_KEY.strip()}"
    }
    
    poll_payload = {
        "taskId": task_id,
        "model": "bytedance/seedance-pro"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Check status
        response = await client.post(FASTROUTER_STATUS_URL, json=poll_payload, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ Status check failed: {response.status_code} - {response.text}")
            return
            
        content_type = response.headers.get("content-type", "")
        print(f"   Status Response Type: {content_type}")
        
        # 1. Check for Binary Video
        if "video" in content_type or "octet-stream" in content_type or len(response.content) > 10000:
            filename = f"recovered_{task_id}.mp4"
            output_path = OUTPUT_DIR / filename
            with open(output_path, "wb") as f:
                f.write(response.content)
            print(f"\n✅ Video Recovered Successfully!")
            print(f"📂 Saved to: {output_path}")
            return

        # 2. Check for JSON URL
        try:
            result = response.json()
            print(f"   Status JSON: {result}")
            
            video_url = result.get("url") or result.get("video_url") or (result.get("data") and result["data"].get("url"))
            
            if video_url:
                print(f"   ⬇️ Downloading from URL: {video_url}")
                vid_response = await client.get(video_url)
                filename = f"recovered_{task_id}.mp4"
                output_path = OUTPUT_DIR / filename
                with open(output_path, "wb") as f:
                    f.write(vid_response.content)
                print(f"\n✅ Video Recovered Successfully!")
                print(f"📂 Saved to: {output_path}")
            else:
                status = result.get("status")
                print(f"⚠️ Video not ready yet. Status: {status}")
                if status == "success" or status == "completed":
                     print("Suggest logic update: JSON says success but no URL found?")
                     
        except Exception as e:
            print(f"❌ Error parsing response: {e}")

if __name__ == "__main__":
    # Task ID from your log
    TASK_ID = "cmlrmgxpd0ii8kdvnb33wcfjj" 
    asyncio.run(recover_video(TASK_ID))
