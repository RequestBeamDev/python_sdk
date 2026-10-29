# RequestBeam Python SDK

[English](../README.md) | [Deutsch](README.de.md) | [Türkçe](README.tr.md) | [Italiano](README.it.md) | [Español](README.es.md) | [Français](README.fr.md) | [Português](README.pt-BR.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | [Русский](README.ru.md)

RequestBeam のテキスト、画像、動画、Similarweb、Twitter API 用の同期・非同期 Python クライアントです。元の応答構造を保持し、上限付きジョブポーリング、SSE イベント、型別の例外、プロジェクトの公開言語全 12 種のローカルメッセージを提供します。

## インストール

Python 3.10 以降で、このリポジトリからインストールしてください。このバージョンは PyPI 未公開です。PyPI の同名パッケージをこの SDK と見なさないでください。

```bash
git clone https://github.com/RequestBeamDev/python_sdk.git
cd python_sdk
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

## 認証と言語

API キーはローカルまたはサーバーの環境変数で管理します。既定の API ルートは `https://api.requestbeam.com` で、`/v1` は付けません。`locale` は SDK が生成するエラーのみを変更し、プロンプト、API フィールド、モデル ID、サーバーの元のメッセージは翻訳しません。対応コードは `en`、`de`、`tr`、`it`、`es`、`fr`、`pt-BR` / `pt`、`ja`、`ko`、`zh-CN` / `cn` / `zh`、`zh-TW` / `tw`、`ru` です。大文字小文字とアンダースコアは正規化され、未対応言語は `ValueError` になります。

独自の `base_url` は認証情報、パス、クエリ、フラグメントを含まない HTTPS オリジンにしてください。ジョブ ID と Twitter ユーザー ID は ASCII 数字のみの空でない文字列です。

```bash
export REQUESTBEAM_API_KEY="YOUR_API_KEY"
export REQUESTBEAM_TEXT_MODEL="YOUR_TEXT_MODEL_ID"
```

## テキストと非同期呼び出し

`list_models()` で現在のモデルカタログを確認し、適切なモデル ID を `REQUESTBEAM_TEXT_MODEL` に設定してください。カタログへの掲載はプロバイダーの実際の稼働を保証しません。応答は通常の辞書です。コンテキストマネージャーは SDK 所有の接続を閉じますが、外部から渡した HTTP クライアントは呼び出し側で管理します。

```python
import os
from requestbeam import RequestBeam

with RequestBeam(locale="ja") as client:
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
    async with AsyncRequestBeam(locale="ja") as client:
        result = await client.chat_completions(
            model=os.environ["REQUESTBEAM_TEXT_MODEL"],
            messages=[{"role": "user", "content": "Hello"}],
        )
        print(result)

asyncio.run(main())
```

## ストリーミング

途中で読み取りをやめる場合もストリームのコンテキストマネージャーを使います。各 `SSEEvent` は `event`、`data`、`id`、`json()` を提供します。データ形式はプロトコルごとに異なり、すべてのイベントにテキストがあるとは限りません。`[DONE]` はイテレーターが内部処理します。ストリームの失敗は SDK 例外になります。

```python
import os
from requestbeam import RequestBeam

with RequestBeam(locale="ja") as client:
    with client.stream_chat_completions(
        model=os.environ["REQUESTBEAM_TEXT_MODEL"],
        messages=[{"role": "user", "content": "Hello"}],
    ) as events:
        for event in events:
            print(event.event, event.data)
```

## 画像と動画

画像生成は JSON または SSE で直接結果を返し、Jobs は使いません。動画の送信は文字列の `data.jobId` を返します。`wait_for_job()` は `COMPLETED` 後にジョブ応答全体を返し、`FAILED` または `CANCELLED` では `JobFailedError` を送出します。タイムアウトはローカルの待機だけを停止し、上流のジョブや課金は取り消しません。

同期ポーリングでは残り時間を HTTP の各フェーズのタイムアウトに設定し、リクエストの間で期限を確認します。進行中の同期応答を強制中断できないため、実際の経過時間は予算を超える場合があります。非同期版は進行中のリクエスト全体にも期限を適用します。ストリームには `stream_*` を使ってください。非ストリームメソッドは送信前に `stream=True` を拒否します。

```python
from requestbeam import RequestBeam

with RequestBeam(locale="ja") as client:
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

## Similarweb と Twitter

Similarweb は許可された 27 操作に対応し、各 API の元の応答フィールドを保持します。対応するのは世界全体のデータ (`country=999`) のみです。他の有効な国コードはサービス側で世界全体に変換され、国別データにはなりません。必要なら `**{"from": ..., "to": ...}` で日付範囲をペアで渡します。SDK はこれらを書き換えません。空の結果はトラフィックがゼロという意味ではありません。

```python
from requestbeam import RequestBeam

with RequestBeam(locale="ja") as client:
    traffic = client.similarweb(
        "websites/visits", keys="example.com", country=999
    )
    print(traffic)
```

Twitter のヘルパーはユーザー名検索、ID 検索、ユーザータイムラインに対応します。ページイテレーターは応答ページ全体を返し、`meta.next_token` をたどり、ページ上限を設け、重複カーソルを拒否します。ページの結合やタイムライン全件取得は保証しません。データ GET は課金される場合があり、各ページが別のリクエストです。

```python
from requestbeam import RequestBeam

with RequestBeam(locale="ja") as client:
    user = client.twitter_user_by_username("TwitterDev")
    user_id = user["data"]["id"]
    for page in client.iter_twitter_user_tweets(
        user_id, max_pages=3, max_results=10
    ):
        print(page)
```

## エラーとローカル保存

`APIError` は HTTP ステータス、サービスコード、元のメッセージ、リクエスト ID、応答本文を保持します。`TransportError`、`ProtocolError`、`PollingTimeoutError`、`JobFailedError` は接続、プロトコル、待機、ジョブの失敗を区別します。応答や例外本文を公開する前に個人・機密情報を確認してください。キーを Git、ブラウザーコード、スクリーンショット、ログに含めないでください。

```python
from requestbeam import APIError, RequestBeam

try:
    with RequestBeam(locale="ja") as client:
        client.get_job("123456789012345678")
except APIError as exc:
    print(exc.status_code, exc.code, exc.request_id)
```

結果の構造を確認してからローカル保存します。SDK はリモートファイルを自動取得しません。結果 URL は期限切れになる場合があります。信頼できる結果は別の認証なし HTTP クライアントで早めに取得し、ファイルホストに RequestBeam キーを送信しないでください。

```python
import json
from pathlib import Path

# result: a response obtained from one of the calls above.
Path("result.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
)
```

## 検証と制限

自動テストはモック通信を使い、有料 API を呼び出しません。2026-10-29 時点では有料の実生成による確認、デプロイ、PyPI 公開は未実施です。課金 GET や生成の送信も含め、自動再試行は行いません。未知のパラメーターや応答構造を黙って変換しません。例を実行する前に RequestBeam ドキュメントでモデル別の制約を確認してください。

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m build
```

シグネチャとプロトコルの違いは [API リファレンス](api-reference.md)、範囲と検証の境界は [設計メモ](design.md) を参照してください。

[RequestBeam](https://requestbeam.com/ja) · [API](https://requestbeam.com/ja/docs/api-reference/models)
