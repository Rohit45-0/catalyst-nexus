import sys
import os
import traceback

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))

import asyncio
import logging

logging.basicConfig(level=logging.INFO)

from app.agents.neural_render import NeuralRenderAgent, RenderRequest
from app.agents.neural_render import RenderBackend, RenderQuality

async def test():
    try:
        agent = NeuralRenderAgent()
        req = RenderRequest(
            prompt="A minimalistic product poster for a futuristic air fryer on a kitchen counter.", 
            backend=RenderBackend.DALLE_3, 
            width=1024, 
            height=1024, 
            quality=RenderQuality.DRAFT
        )
        res = await agent.render_image(req)
        with open('dalle_test_result.txt', 'w') as f:
            f.write(f"Result path: {res.output_path}\n")
            f.write(f"Result URL: {res.output_url}\n")
            f.write(f"Status: {res.status}\n")
    except Exception as e:
        with open('dalle_test_result.txt', 'w') as f:
            f.write(f"Exception: {e}\n")
            f.write(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(test())
