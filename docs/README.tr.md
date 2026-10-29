# RequestBeam Python SDK

[English](../README.md) | [Deutsch](README.de.md) | [Türkçe](README.tr.md) | [Italiano](README.it.md) | [Español](README.es.md) | [Français](README.fr.md) | [Português](README.pt-BR.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | [Русский](README.ru.md)

RequestBeam metin, görsel, video, Similarweb ve Twitter API'leri için senkron ve asenkron Python istemcisi. Yerel yanıt yapılarını korur; sınırlı iş sorgulama, SSE olayları, türlenmiş hatalar ve projenin 12 genel dilinde yerel mesajlar sunar.

## Kurulum

Bu depodan Python 3.10 veya üzeriyle yükleyin. Bu sürüm PyPI'da yayımlanmamıştır; oradaki aynı adlı bir paketin bu SDK olduğunu varsaymayın.

```bash
git clone https://github.com/RequestBeamDev/python_sdk.git
cd python_sdk
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

## Kimlik doğrulama ve dil

API anahtarını yerel ortamda veya sunucu ortamında tutun. Varsayılan API kökü `https://api.requestbeam.com` adresidir; `/v1` eklemeyin. `locale` yalnızca SDK'nın oluşturduğu hata mesajlarını değiştirir; istemleri, API alanlarını, model kimliklerini veya sunucunun özgün mesajını çevirmez. Desteklenen kodlar: `en`, `de`, `tr`, `it`, `es`, `fr`, `pt-BR` / `pt`, `ja`, `ko`, `zh-CN` / `cn` / `zh`, `zh-TW` / `tw`, `ru`. Alt çizgi ve harf boyutu normalleştirilir. Desteklenmeyen diller `ValueError` üretir.

Özel `base_url` değerleri kimlik bilgisi, yol, sorgu veya parça içermeyen HTTPS kökenleri olmalıdır. İş ve Twitter kullanıcı kimlikleri yalnızca ASCII rakamlarından oluşan boş olmayan metinler olmalıdır.

```bash
export REQUESTBEAM_API_KEY="YOUR_API_KEY"
export REQUESTBEAM_TEXT_MODEL="YOUR_TEXT_MODEL_ID"
```

## Metin ve asenkron kullanım

Güncel model kataloğunu `list_models()` ile inceleyip `REQUESTBEAM_TEXT_MODEL` değişkenine uygun bir model kimliği atayın. Katalogda bulunmak sağlayıcının o anda kullanılabilir olduğunu garanti etmez. Yanıtlar normal sözlüklerdir. Bağlam yöneticileri SDK'ya ait bağlantıları kapatır; dışarıdan verilen HTTP istemcilerinin sorumluluğu çağırandadır.

```python
import os
from requestbeam import RequestBeam

with RequestBeam(locale="tr") as client:
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
    async with AsyncRequestBeam(locale="tr") as client:
        result = await client.chat_completions(
            model=os.environ["REQUESTBEAM_TEXT_MODEL"],
            messages=[{"role": "user", "content": "Hello"}],
        )
        print(result)

asyncio.run(main())
```

## Akış

Okumayı erken bıraksanız bile akış bağlam yöneticisini kullanın. Her `SSEEvent`, `event`, `data`, `id` ve `json()` sunar. Olay verileri protokole göre değişir; her olayın metin içerdiğini varsaymayın. Yineleyici `[DONE]` işaretini tüketir. Akış hataları SDK istisnası üretir.

```python
import os
from requestbeam import RequestBeam

with RequestBeam(locale="tr") as client:
    with client.stream_chat_completions(
        model=os.environ["REQUESTBEAM_TEXT_MODEL"],
        messages=[{"role": "user", "content": "Hello"}],
    ) as events:
        for event in events:
            print(event.event, event.data)
```

## Görseller ve video

Görsel üretimi doğrudan JSON veya SSE döndürür ve Jobs kullanmaz. Video gönderimi metin türünde `data.jobId` döndürür. `wait_for_job()`, `COMPLETED` sonrasında tam iş yanıtını döndürür; `FAILED` veya `CANCELLED` için `JobFailedError` üretir. Zaman aşımı yalnızca yerel beklemeyi durdurur; uzaktaki işi veya ücretlendirmeyi iptal etmez.

Senkron sorgulama kalan bütçeyi her HTTP zaman aşımı aşamasına uygular ve istekler arasında süreyi kontrol eder. Devam eden senkron yanıtı zorla kesemez; toplam süre bütçeyi aşabilir. Asenkron sorgulama ayrıca devam eden isteğe genel bir süre sınırı uygular. Akış için `stream_*` kullanın; diğer yöntemler göndermeden önce `stream=True` değerini reddeder.

```python
from requestbeam import RequestBeam

with RequestBeam(locale="tr") as client:
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

## Similarweb ve Twitter

Similarweb 27 izinli işlemi destekler ve uç noktaların özgün yanıt alanlarını korur. Yalnızca dünya geneli veri (`country=999`) desteklenir. Diğer geçerli ülke değerleri hizmet tarafından dünya geneline dönüştürülür, ülkeye özel veri vermez. Gerektiğinde `from` ve `to` değerlerini birlikte `**{"from": ..., "to": ...}` ile iletin; SDK bunları değiştirmez. Boş sonuç sıfır trafik anlamına gelmez.

```python
from requestbeam import RequestBeam

with RequestBeam(locale="tr") as client:
    traffic = client.similarweb(
        "websites/visits", keys="example.com", country=999
    )
    print(traffic)
```

Twitter yardımcıları kullanıcı adı, kullanıcı kimliği ve kullanıcı zaman akışını kapsar. Sayfa yineleyici tam sayfalar döndürür, `meta.next_token` değerini izler, sayfa sınırı uygular ve tekrarlanan imleçleri reddeder. Sayfaları birleştirmez ve tüm zaman akışını getirmeyi garanti etmez. Veri GET istekleri ücretli olabilir; her sayfa ayrı istektir.

```python
from requestbeam import RequestBeam

with RequestBeam(locale="tr") as client:
    user = client.twitter_user_by_username("TwitterDev")
    user_id = user["data"]["id"]
    for page in client.iter_twitter_user_tweets(
        user_id, max_pages=3, max_results=10
    ):
        print(page)
```

## Hatalar ve yerel dosyalar

`APIError`, HTTP durumunu, hizmet kodunu, özgün mesajı, istek kimliğini ve yanıt gövdesini korur. `TransportError`, `ProtocolError`, `PollingTimeoutError` ve `JobFailedError` bağlantı, protokol, bekleme ve iş hatalarını ayırır. Yanıtları ve hata gövdelerini yayımlamadan önce özel veri açısından kontrol edin. Anahtarları kaynak koduna, tarayıcıya, ekran görüntülerine veya günlüklere koymayın.

```python
from requestbeam import APIError, RequestBeam

try:
    with RequestBeam(locale="tr") as client:
        client.get_job("123456789012345678")
except APIError as exc:
    print(exc.status_code, exc.code, exc.request_id)
```

Yerel kayıttan önce yanıt yapısını kontrol edin. SDK uzak dosyaları otomatik indirmez. Sonuç URL'lerinin süresi dolabilir; güvenilir sonuçları ayrı ve kimlik doğrulamasız bir HTTP istemcisiyle zamanında indirin, böylece RequestBeam anahtarı dosya sunucusuna gönderilmez.

```python
import json
from pathlib import Path

# result: a response obtained from one of the calls above.
Path("result.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
)
```

## Doğrulama ve sınırlar

Testler sahte taşıma katmanları kullanır ve ücretli API çağrısı yapmaz. 2026-10-29 itibarıyla ücretli canlı üretim doğrulaması, dağıtım veya PyPI yayını yapılmamıştır. Ücretli GET ve üretim gönderimleri dahil hiçbir istek otomatik tekrarlanmaz. Bilinmeyen parametreler ve yanıt yapıları sessizce değiştirilmez. Örnekleri çalıştırmadan önce RequestBeam belgelerindeki model sınırlarını kontrol edin.

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m build
```

İmzalar ve protokol farkları: [API başvurusu](api-reference.md). Kapsam ve doğrulama sınırları: [tasarım notları](design.md).

[RequestBeam](https://requestbeam.com/tr) · [API](https://requestbeam.com/tr/docs/api-reference/models)
