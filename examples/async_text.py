"""An async streaming example; running this makes a billable call."""

import asyncio
import os

from requestbeam import AsyncRequestBeam


async def main():
    async with AsyncRequestBeam() as client:
        async with client.stream_chat_completions(
            model=os.environ["REQUESTBEAM_TEXT_MODEL"],
            messages=[{"role": "user", "content": "Hello"}],
        ) as events:
            async for event in events:
                print(event.json())


if __name__ == "__main__":
    asyncio.run(main())
