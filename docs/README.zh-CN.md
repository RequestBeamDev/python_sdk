# RequestBeam Python SDK

[English](../README.md) | [Deutsch](README.de.md) | [Türkçe](README.tr.md) | [Italiano](README.it.md) | [Español](README.es.md) | [Français](README.fr.md) | [Português](README.pt-BR.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | [Русский](README.ru.md)

用于 RequestBeam 文本、图片、视频、Similarweb 和 Twitter API 的同步与异步 Python 客户端。保留原始响应结构，提供有上限的任务轮询、SSE 事件、类型化异常，以及项目全部 12 种公共语言的本地提示。

## 安装

使用 Python 3.10 或更高版本，从本仓库安装。本版本尚未发布到 PyPI；不要将 PyPI 上的同名包视为本 SDK。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

## 认证与语言

API Key 保存在本地或服务端环境变量中。默认 API 根地址为 `https://api.requestbeam.com`，不要追加 `/v1`。`locale` 只改变 SDK 自身产生的错误提示，不翻译提示词、API 字段、模型 ID 或服务端原始错误消息。支持 `en`、`de`、`tr`、`it`、`es`、`fr`、`pt-BR` / `pt`、`ja`、`ko`、`zh-CN` / `cn` / `zh`、`zh-TW` / `tw`、`ru`，兼容下划线与大小写。不支持的语言会抛出 `ValueError`。

自定义 `base_url` 必须是无凭证、路径、查询或片段的 HTTPS 源地址。任务 ID 和 Twitter 用户 ID 必须是仅含 ASCII 数字的非空字符串。

```bash
export REQUESTBEAM_API_KEY="YOUR_API_KEY"
export REQUESTBEAM_TEXT_MODEL="YOUR_TEXT_MODEL_ID"
```

## 文本与异步调用

通过 `list_models()` 查看当前模型目录，再将适用的模型 ID 设置到 `REQUESTBEAM_TEXT_MODEL`。目录中存在不等于上游此时一定可用。响应为普通字典。上下文管理器会关闭 SDK 自己创建的连接；外部传入的 HTTP 客户端由调用方管理。

```python
import os
from requestbeam import RequestBeam

with RequestBeam(locale="zh-CN") as client:
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
    async with AsyncRequestBeam(locale="zh-CN") as client:
        result = await client.chat_completions(
            model=os.environ["REQUESTBEAM_TEXT_MODEL"],
            messages=[{"role": "user", "content": "Hello"}],
        )
        print(result)

asyncio.run(main())
```

## 流式调用

即使提前停止读取，也应使用流式上下文管理器。每个 `SSEEvent` 提供 `event`、`data`、`id` 和 `json()`。不同协议的事件数据不同，不要假定每个事件都有文本。迭代器内部处理 `[DONE]` 标记。流式失败会抛出 SDK 异常。

```python
import os
from requestbeam import RequestBeam

with RequestBeam(locale="zh-CN") as client:
    with client.stream_chat_completions(
        model=os.environ["REQUESTBEAM_TEXT_MODEL"],
        messages=[{"role": "user", "content": "Hello"}],
    ) as events:
        for event in events:
            print(event.event, event.data)
```

## 图片与视频

图片生成通过 JSON 或 SSE 直接返回结果，不走 Jobs。视频提交返回字符串 `data.jobId`。`wait_for_job()` 在 `COMPLETED` 后返回完整任务响应，在 `FAILED` 或 `CANCELLED` 时抛出 `JobFailedError`。等待超时只停止本地等待，不会取消上游任务或计费。

同步轮询将剩余时间设置为 HTTP 各阶段的超时，并在请求之间检查截止时间。它无法硬中断正在传输的同步响应，因此实际总等待可能超过轮询预算。异步轮询还会对进行中的整次请求施加剩余时间限制。流式请求请使用 `stream_*`；非流式方法会在发送前拒绝 `stream=True`。

```python
from requestbeam import RequestBeam

with RequestBeam(locale="zh-CN") as client:
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

## Similarweb 与 Twitter

Similarweb 支持 27 个白名单操作，保留各接口的原生响应字段。目前只支持全球数据（`country=999`）。其他合法国家值由服务端转换为全球口径，并非国家维度结果。需要日期区间时，通过 `**{"from": ..., "to": ...}` 成对传入；SDK 不改写日期。空结果不代表流量为零。

```python
from requestbeam import RequestBeam

with RequestBeam(locale="zh-CN") as client:
    traffic = client.similarweb(
        "websites/visits", keys="example.com", country=999
    )
    print(traffic)
```

Twitter 辅助方法支持用户名查询、用户 ID 查询和用户时间线。分页迭代器返回完整原生分页响应，跟随 `meta.next_token`，设置页数上限并拒绝重复游标。它不会合并页面，也不承诺获取全部时间线。数据 GET 也可能计费，每页都是一次独立请求。

```python
from requestbeam import RequestBeam

with RequestBeam(locale="zh-CN") as client:
    user = client.twitter_user_by_username("TwitterDev")
    user_id = user["data"]["id"]
    for page in client.iter_twitter_user_tweets(
        user_id, max_pages=3, max_results=10
    ):
        print(page)
```

## 错误与本地保存

`APIError` 保留 HTTP 状态、服务端错误码、原始消息、请求 ID 和响应体。`TransportError`、`ProtocolError`、`PollingTimeoutError`、`JobFailedError` 分别区分连接、协议、等待和任务失败。公开原始响应或异常正文前，请检查私密数据。不要将密钥放进 Git、浏览器代码、截图或日志。

```python
from requestbeam import APIError, RequestBeam

try:
    with RequestBeam(locale="zh-CN") as client:
        client.get_job("123456789012345678")
except APIError as exc:
    print(exc.status_code, exc.code, exc.request_id)
```

检查响应结构后再保存本地结果。SDK 不会自动下载远程文件。结果 URL 可能过期；应及时用独立、无认证的 HTTP 客户端获取可信结果，避免向资源主机发送 RequestBeam API Key。

```python
import json
from pathlib import Path

# result: a response obtained from one of the calls above.
Path("result.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
)
```

## 验证与限制

自动测试使用 mock transport，不调用收费 API。截至 2026-10-29，尚未进行付费线上生成验证、部署或 PyPI 发布。所有请求都不自动重试，包括收费 GET 与生成提交。未知参数和服务端响应结构不会被静默改写。运行示例前，请查看 RequestBeam 文档中的具体模型限制。

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m build
```

方法签名与协议差异见 [API 参考](api-reference.md)，范围与验证边界见 [设计记录](design.md)。

[RequestBeam](https://requestbeam.com/cn) · [API](https://requestbeam.com/cn/docs/api-reference/models)
