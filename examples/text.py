"""Run with REQUESTBEAM_API_KEY and REQUESTBEAM_TEXT_MODEL; makes a billable call."""

import os

from requestbeam import RequestBeam

with RequestBeam() as client:
    result = client.chat_completions(
        model=os.environ["REQUESTBEAM_TEXT_MODEL"],
        messages=[{"role": "user", "content": "Hello"}],
    )
    print(result)
