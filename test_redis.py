"""Quick test to verify Redis connectivity."""
import asyncio
import sys
import redis.asyncio as aioredis

async def main():
    result_lines = []
    result_lines.append("Connecting to Upstash Redis (TLS)...")
    r = aioredis.from_url(
        "rediss://default:AdlUAAIncDFjOTBmMzNkNmUwOWI0MjFjOGMyZGJjNTI5YzY1ODc3OXAxNTU2MzY@complete-python-55636.upstash.io:6379",
        decode_responses=True,
        socket_connect_timeout=10,
    )
    try:
        pong = await r.ping()
        result_lines.append(f"PING response: {pong}")
        
        await r.set("catalyst:test", "phase2_ready", ex=60)
        val = await r.get("catalyst:test")
        result_lines.append(f"SET/GET test: {val}")
        result_lines.append("SUCCESS")
    except Exception as e:
        result_lines.append(f"ERROR: {type(e).__name__}: {e}")
    finally:
        await r.aclose()
    
    # Write to file since stdout may be buffered
    with open("test_redis_result.txt", "w") as f:
        f.write("\n".join(result_lines))

if __name__ == "__main__":
    asyncio.run(main())
