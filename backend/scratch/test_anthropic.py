import asyncio
import os
import anthropic
from anthropic import AsyncAnthropic
from anthropic import NotFoundError, APIStatusError

async def main():
    api_key = os.getenv("ANTHROPIC_API_KEY", "sk-ant-api03-dummykey123")
    client = AsyncAnthropic(api_key=api_key)
    try:
        res = await client.messages.create(
            model="claude-3-5-sonnet-latest",
            max_tokens=100,
            messages=[{"role": "user", "content": "Hi"}]
        )
        print("Success:", res)
    except Exception as e:
        print(f"Exception type: {type(e).__name__}")
        print(f"Exception message: {str(e)}")

asyncio.run(main())
