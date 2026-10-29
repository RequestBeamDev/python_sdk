# RequestBeam Python SDK

[English](../README.md) | [Deutsch](README.de.md) | [Türkçe](README.tr.md) | [Italiano](README.it.md) | [Español](README.es.md) | [Français](README.fr.md) | [Português](README.pt-BR.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | [Русский](README.ru.md)

用於 RequestBeam 文字、圖片、影片、Similarweb 與 Twitter API 的同步及非同步 Python 用戶端。保留原始回應結構，提供有上限的工作輪詢、SSE 事件、類型化例外，以及專案全部 12 種公開語言的本地提示。

## 安裝

使用 Python 3.10 或更新版本，從本儲存庫安裝。本版本尚未發布至 PyPI；請勿將 PyPI 上的同名套件視為本 SDK。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

## 認證與語言

API Key 儲存在本機或伺服器環境變數中。預設 API 根位址為 `https://api.requestbeam.com`，請勿附加 `/v1`。`locale` 只改變 SDK 本身產生的錯誤提示，不翻譯提示詞、API 欄位、模型 ID 或伺服器原始錯誤訊息。支援 `en`、`de`、`tr`、`it`、`es`、`fr`、`pt-BR` / `pt`、`ja`、`ko`、`zh-CN` / `cn` / `zh`、`zh-TW` / `tw`、`ru`，相容底線與大小寫。不支援的語言會引發 `ValueError`。

自訂 `base_url` 必須是不含憑證、路徑、查詢或片段的 HTTPS 來源位址。工作 ID 與 Twitter 使用者 ID 必須是僅含 ASCII 數字的非空字串。

```bash
export REQUESTBEAM_API_KEY="YOUR_API_KEY"
export REQUESTBEAM_TEXT_MODEL="YOUR_TEXT_MODEL_ID"
```

## 文字與非同步呼叫

透過 `list_models()` 查看目前模型目錄，再將適用的模型 ID 設定至 `REQUESTBEAM_TEXT_MODEL`。目錄中存在不代表上游此時一定可用。回應為一般字典。情境管理器會關閉 SDK 自行建立的連線；外部傳入的 HTTP 用戶端由呼叫方管理。

```python
import os
from requestbeam import RequestBeam

with RequestBeam(locale="zh-TW") as client:
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
    async with AsyncRequestBeam(locale="zh-TW") as client:
        result = await client.chat_completions(
            model=os.environ["REQUESTBEAM_TEXT_MODEL"],
            messages=[{"role": "user", "content": "Hello"}],
        )
        print(result)

asyncio.run(main())
```

## 串流呼叫

即使提早停止讀取，也應使用串流情境管理器。每個 `SSEEvent` 提供 `event`、`data`、`id` 與 `json()`。不同協定的事件資料不同，請勿假定每個事件都有文字。迭代器內部處理 `[DONE]` 標記。串流失敗會引發 SDK 例外。

```python
import os
from requestbeam import RequestBeam

with RequestBeam(locale="zh-TW") as client:
    with client.stream_chat_completions(
        model=os.environ["REQUESTBEAM_TEXT_MODEL"],
        messages=[{"role": "user", "content": "Hello"}],
    ) as events:
        for event in events:
            print(event.event, event.data)
```

## 圖片與影片

圖片生成透過 JSON 或 SSE 直接回傳結果，不使用 Jobs。影片提交回傳字串 `data.jobId`。`wait_for_job()` 在 `COMPLETED` 後回傳完整工作回應，在 `FAILED` 或 `CANCELLED` 時引發 `JobFailedError`。等待逾時只停止本機等待，不會取消上游工作或計費。

同步輪詢將剩餘時間設定為 HTTP 各階段的逾時，並在請求之間檢查截止時間。它無法強制中斷正在傳輸的同步回應，因此實際總等待可能超過輪詢預算。非同步輪詢還會對進行中的整次請求施加剩餘時間限制。串流請求請使用 `stream_*`；非串流方法會在傳送前拒絕 `stream=True`。

```python
from requestbeam import RequestBeam

with RequestBeam(locale="zh-TW") as client:
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

## Similarweb 與 Twitter

Similarweb 支援 27 個允許清單操作，保留各端點的原生回應欄位。目前只支援全球資料（`country=999`）。其他合法國家值由服務端轉為全球範圍，並非國家維度結果。需要日期範圍時，透過 `**{"from": ..., "to": ...}` 成對傳入；SDK 不改寫日期。空結果不代表流量為零。

```python
from requestbeam import RequestBeam

with RequestBeam(locale="zh-TW") as client:
    traffic = client.similarweb(
        "websites/visits", keys="example.com", country=999
    )
    print(traffic)
```

Twitter 輔助方法支援使用者名稱查詢、使用者 ID 查詢及使用者時間軸。分頁迭代器回傳完整原生分頁回應，跟隨 `meta.next_token`，設定頁數上限並拒絕重複游標。它不會合併頁面，也不保證取得全部時間軸。資料 GET 也可能計費，每頁都是獨立請求。

```python
from requestbeam import RequestBeam

with RequestBeam(locale="zh-TW") as client:
    user = client.twitter_user_by_username("TwitterDev")
    user_id = user["data"]["id"]
    for page in client.iter_twitter_user_tweets(
        user_id, max_pages=3, max_results=10
    ):
        print(page)
```

## 錯誤與本地儲存

`APIError` 保留 HTTP 狀態、服務端錯誤碼、原始訊息、請求 ID 與回應本文。`TransportError`、`ProtocolError`、`PollingTimeoutError`、`JobFailedError` 分別區分連線、協定、等待與工作失敗。公開原始回應或例外本文前，請檢查私人資料。請勿將金鑰放進 Git、瀏覽器程式碼、螢幕截圖或日誌。

```python
from requestbeam import APIError, RequestBeam

try:
    with RequestBeam(locale="zh-TW") as client:
        client.get_job("123456789012345678")
except APIError as exc:
    print(exc.status_code, exc.code, exc.request_id)
```

檢查回應結構後再儲存本機結果。SDK 不會自動下載遠端檔案。結果 URL 可能過期；應及時使用獨立、無認證的 HTTP 用戶端取得可信結果，避免將 RequestBeam API Key 傳給資源主機。

```python
import json
from pathlib import Path

# result: a response obtained from one of the calls above.
Path("result.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
)
```

## 驗證與限制

自動測試使用模擬傳輸，不呼叫付費 API。截至 2026-10-29，尚未進行付費線上生成驗證、部署或 PyPI 發布。所有請求都不會自動重試，包括付費 GET 與生成提交。未知參數及伺服器回應結構不會被默默改寫。執行範例前，請查看 RequestBeam 文件中的個別模型限制。

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m build
```

方法簽章與協定差異見 [API 參考](api-reference.md)，範圍與驗證界線見 [設計記錄](design.md)。

[RequestBeam](https://requestbeam.com/tw) · [API](https://requestbeam.com/tw/docs/api-reference/models)
