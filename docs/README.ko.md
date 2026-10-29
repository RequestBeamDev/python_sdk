# RequestBeam Python SDK

[English](../README.md) | [Deutsch](README.de.md) | [Türkçe](README.tr.md) | [Italiano](README.it.md) | [Español](README.es.md) | [Français](README.fr.md) | [Português](README.pt-BR.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | [Русский](README.ru.md)

RequestBeam 텍스트, 이미지, 동영상, Similarweb, Twitter API용 동기 및 비동기 Python 클라이언트입니다. 원래 응답 구조를 유지하며 횟수와 시간이 제한된 작업 폴링, SSE 이벤트, 유형별 오류, 프로젝트의 공개 언어 12개에 대한 로컬 메시지를 제공합니다.

## 설치

Python 3.10 이상에서 이 저장소로부터 설치하세요. 이 버전은 PyPI에 게시되지 않았으며, 같은 이름의 패키지가 이 SDK라고 가정하면 안 됩니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

## 인증과 언어

API 키는 로컬 또는 서버 환경 변수에 보관합니다. 기본 API 루트는 `https://api.requestbeam.com`이며 `/v1`을 붙이지 않습니다. `locale`은 SDK가 생성한 오류만 바꾸며 프롬프트, API 필드, 모델 ID, 서버 원문 메시지는 번역하지 않습니다. 지원 코드: `en`, `de`, `tr`, `it`, `es`, `fr`, `pt-BR` / `pt`, `ja`, `ko`, `zh-CN` / `cn` / `zh`, `zh-TW` / `tw`, `ru`. 대소문자와 밑줄은 정규화하며 미지원 언어는 `ValueError`를 발생시킵니다.

사용자 지정 `base_url`은 인증 정보, 경로, 쿼리, 프래그먼트가 없는 HTTPS 오리진이어야 합니다. 작업 및 Twitter 사용자 ID는 ASCII 숫자로만 이루어진 비어 있지 않은 문자열이어야 합니다.

```bash
export REQUESTBEAM_API_KEY="YOUR_API_KEY"
export REQUESTBEAM_TEXT_MODEL="YOUR_TEXT_MODEL_ID"
```

## 텍스트 및 비동기 호출

`list_models()`로 현재 모델 목록을 확인한 뒤 적절한 ID를 `REQUESTBEAM_TEXT_MODEL`에 설정합니다. 목록에 있다는 사실만으로 공급자의 실제 가용성이 보장되지는 않습니다. 응답은 일반 딕셔너리입니다. 컨텍스트 관리자는 SDK가 소유한 연결만 닫으며 외부에서 주입한 HTTP 클라이언트는 호출자가 관리합니다.

```python
import os
from requestbeam import RequestBeam

with RequestBeam(locale="ko") as client:
    models = client.list_models()
    result = client.chat_completions(
        model=os.environ["REQUESTBEAM_TEXT_MODEL"],
        messages=[{"role": "user", "content": "Hello"}],
    )
    print(result)
```

```python
import asyncio
import os
from requestbeam import AsyncRequestBeam

async def main():
    async with AsyncRequestBeam(locale="ko") as client:
        result = await client.chat_completions(
            model=os.environ["REQUESTBEAM_TEXT_MODEL"],
            messages=[{"role": "user", "content": "Hello"}],
        )
        print(result)

asyncio.run(main())
```

## 스트리밍

읽기를 일찍 중단하더라도 스트림 컨텍스트 관리자를 사용하세요. 각 `SSEEvent`에는 `event`, `data`, `id`, `json()`이 있습니다. 페이로드는 프로토콜마다 다르므로 모든 이벤트가 텍스트를 포함한다고 가정하지 마세요. 반복자는 `[DONE]`을 내부적으로 처리합니다. 스트림 실패 시 SDK 예외가 발생합니다.

```python
import os
from requestbeam import RequestBeam

with RequestBeam(locale="ko") as client:
    with client.stream_chat_completions(
        model=os.environ["REQUESTBEAM_TEXT_MODEL"],
        messages=[{"role": "user", "content": "Hello"}],
    ) as events:
        for event in events:
            print(event.event, event.data)
```

## 이미지와 동영상

이미지 생성은 JSON 또는 SSE로 결과를 직접 반환하며 Jobs를 사용하지 않습니다. 동영상 제출은 문자열 `data.jobId`를 반환합니다. `wait_for_job()`은 `COMPLETED` 후 작업 응답 전체를 반환하고 `FAILED` 또는 `CANCELLED`일 때 `JobFailedError`를 발생시킵니다. 제한 시간은 로컬 대기만 중지하며 원격 작업이나 요금을 취소하지 않습니다.

동기 폴링은 남은 시간을 HTTP 각 단계의 제한 시간에 적용하고 요청 사이에 기한을 확인합니다. 진행 중인 동기 응답을 강제로 중단하지 못하므로 실제 경과 시간이 예산을 넘을 수 있습니다. 비동기 폴링은 진행 중인 요청 전체에도 기한을 적용합니다. 스트림에는 `stream_*`을 사용하세요. 비스트림 메서드는 전송 전에 `stream=True`를 거부합니다.

```python
from requestbeam import RequestBeam

with RequestBeam(locale="ko") as client:
    image = client.generate_image(
        model="gpt-image-2", prompt="A red bicycle beside a white wall"
    )
    submission = client.generate_video(
        model="seedance-2.0",
        prompt="A quiet city street at dawn, slow forward camera movement.",
        duration=5,
        resolution="720p",
        aspectRatio="16:9",
        generateAudio=False,
    )
    job = client.wait_for_job(
        submission["data"]["jobId"], timeout=600, poll_interval=5
    )
    print(job["data"]["outputResult"])
```

## Similarweb 및 Twitter

Similarweb은 허용된 작업 27개를 지원하며 각 엔드포인트의 원래 응답 필드를 유지합니다. 전 세계 데이터(`country=999`)만 지원합니다. 다른 유효한 국가 값은 서비스에서 전 세계로 변환되므로 국가별 데이터가 아닙니다. 필요하면 `**{"from": ..., "to": ...}`로 두 날짜를 함께 전달하세요. SDK는 날짜를 바꾸지 않습니다. 빈 결과가 트래픽 0을 의미하지는 않습니다.

```python
from requestbeam import RequestBeam

with RequestBeam(locale="ko") as client:
    traffic = client.similarweb(
        "websites/visits", keys="example.com", country=999
    )
    print(traffic)
```

Twitter 도우미는 사용자 이름 조회, ID 조회, 사용자 타임라인을 지원합니다. 페이지 반복자는 전체 응답 페이지를 반환하고 `meta.next_token`을 따라가며 페이지 수를 제한하고 반복 커서를 거부합니다. 페이지를 합치거나 전체 타임라인 조회를 보장하지 않습니다. 데이터 GET도 과금될 수 있으며 각 페이지가 별도 요청입니다.

```python
from requestbeam import RequestBeam

with RequestBeam(locale="ko") as client:
    user = client.twitter_user_by_username("TwitterDev")
    user_id = user["data"]["id"]
    for page in client.iter_twitter_user_tweets(
        user_id, max_pages=3, max_results=10
    ):
        print(page)
```

## 오류와 로컬 파일

`APIError`는 HTTP 상태, 서비스 코드, 원문 메시지, 요청 ID, 응답 본문을 유지합니다. `TransportError`, `ProtocolError`, `PollingTimeoutError`, `JobFailedError`는 연결, 프로토콜, 대기, 작업 오류를 구분합니다. 응답 또는 예외 본문을 공개하기 전에 비공개 데이터를 확인하세요. 키를 Git, 브라우저 코드, 스크린샷, 로그에 넣지 마세요.

```python
from requestbeam import APIError, RequestBeam

try:
    with RequestBeam(locale="ko") as client:
        client.get_job("123456789012345678")
except APIError as exc:
    print(exc.status_code, exc.code, exc.request_id)
```

응답 구조를 확인한 후 결과를 로컬에 저장하세요. SDK는 원격 파일을 자동 다운로드하지 않습니다. 결과 URL은 만료될 수 있습니다. 별도의 인증 없는 HTTP 클라이언트로 신뢰할 수 있는 결과를 신속히 받아 파일 호스트에 RequestBeam 키를 보내지 않도록 하세요.

```python
import json
from pathlib import Path

# result: a response obtained from one of the calls above.
Path("result.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
)
```

## 검증과 제한

자동 테스트는 모의 전송을 사용하며 유료 API를 호출하지 않습니다. 2026-10-29 기준으로 유료 실제 생성 검증, 배포 또는 PyPI 게시는 수행되지 않았습니다. 과금 GET과 생성 제출을 포함해 자동 재시도는 없습니다. 알 수 없는 매개변수와 응답 구조를 조용히 정규화하지 않습니다. 예제를 실행하기 전에 RequestBeam 문서에서 모델별 제한을 확인하세요.

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m build
```

메서드 서명과 프로토콜 차이: [API 참조](api-reference.md). 범위 및 검증 경계: [설계 기록](design.md).

[RequestBeam](https://requestbeam.com/ko) · [API](https://requestbeam.com/ko/docs/api-reference/models)
