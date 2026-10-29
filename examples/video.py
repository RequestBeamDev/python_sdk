"""Explicitly run to submit a billable video job and wait for its result."""

import os

from requestbeam import RequestBeam

with RequestBeam() as client:
    created = client.generate_video(
        model=os.environ["REQUESTBEAM_VIDEO_MODEL"], prompt="A calm ocean at sunrise"
    )
    print(client.wait_for_job(created["data"]["jobId"]))
