# RequestBeam Python SDK

[English](../README.md) | [Deutsch](README.de.md) | [Türkçe](README.tr.md) | [Italiano](README.it.md) | [Español](README.es.md) | [Français](README.fr.md) | [Português](README.pt-BR.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | [Русский](README.ru.md)

Ein synchroner und asynchroner Python-Client für die Text-, Bild-, Video-, Similarweb- und Twitter-APIs von RequestBeam. Er erhält native Antworten unverändert und bietet begrenztes Job-Polling, SSE-Ereignisse, typisierte Fehler und lokale Meldungen in allen 12 öffentlichen Projektsprachen.

## Installation

Installieren Sie dieses Repository mit Python 3.10 oder neuer. Diese Version wurde nicht auf PyPI veröffentlicht. Ein dort gleichnamiges Paket ist nicht automatisch dieses SDK.

```bash
git clone https://github.com/RequestBeamDev/python_sdk.git
cd python_sdk
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

## Authentifizierung und Sprache

Speichern Sie den API-Schlüssel in der lokalen Umgebung oder auf dem Server. Die Standard-API-Wurzel lautet `https://api.requestbeam.com`, ohne angehängtes `/v1`. `locale` ändert nur SDK-eigene Fehlermeldungen, nicht Prompts, API-Felder, Modell-IDs oder ursprüngliche Servermeldungen. Unterstützt werden `en`, `de`, `tr`, `it`, `es`, `fr`, `pt-BR` / `pt`, `ja`, `ko`, `zh-CN` / `cn` / `zh`, `zh-TW` / `tw` und `ru`. Unterstriche und Groß-/Kleinschreibung werden normalisiert; unbekannte Sprachen lösen `ValueError` aus.

Eigene `base_url`-Werte müssen HTTPS-Ursprünge ohne Zugangsdaten, Pfad, Abfrage oder Fragment sein. Job- und Twitter-Benutzer-IDs müssen nicht leere Zeichenfolgen aus ASCII-Ziffern sein.

```bash
export REQUESTBEAM_API_KEY="YOUR_API_KEY"
export REQUESTBEAM_TEXT_MODEL="YOUR_TEXT_MODEL_ID"
```

## Text und asynchrone Aufrufe

Prüfen Sie den aktuellen Modellkatalog mit `list_models()` und setzen Sie `REQUESTBEAM_TEXT_MODEL` auf eine geeignete Modell-ID. Ein Katalogeintrag garantiert keine aktuelle Anbieter-Verfügbarkeit. Antworten sind normale Dictionaries. Kontextmanager schließen SDK-eigene Verbindungen; übergebene HTTP-Clients bleiben in Ihrer Verantwortung.

```python
import os
from requestbeam import RequestBeam

with RequestBeam(locale="de") as client:
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
    async with AsyncRequestBeam(locale="de") as client:
        result = await client.chat_completions(
            model=os.environ["REQUESTBEAM_TEXT_MODEL"],
            messages=[{"role": "user", "content": "Hello"}],
        )
        print(result)

asyncio.run(main())
```

## Streaming

Verwenden Sie den Stream-Kontextmanager auch beim vorzeitigen Abbruch. Jedes `SSEEvent` bietet `event`, `data`, `id` und `json()`. Nutzdaten unterscheiden sich je nach Protokoll; nicht jedes Ereignis enthält Text. Der Iterator verarbeitet `[DONE]` intern. Stream-Fehler lösen eine SDK-Ausnahme aus.

```python
import os
from requestbeam import RequestBeam

with RequestBeam(locale="de") as client:
    with client.stream_chat_completions(
        model=os.environ["REQUESTBEAM_TEXT_MODEL"],
        messages=[{"role": "user", "content": "Hello"}],
    ) as events:
        for event in events:
            print(event.event, event.data)
```

## Bilder und Videos

Bilder liefern Ergebnisse direkt als JSON oder SSE und verwenden keine Jobs. Video-Aufträge liefern `data.jobId` als Zeichenfolge. `wait_for_job()` gibt nach `COMPLETED` die vollständige Job-Antwort zurück und löst bei `FAILED` oder `CANCELLED` einen `JobFailedError` aus. Ein Zeitlimit beendet nur das lokale Warten, nicht den Auftrag oder seine Abrechnung.

Synchrones Polling setzt die verbleibende Zeit als Limit jeder HTTP-Phase und prüft die Frist zwischen Anfragen. Eine laufende synchrone Antwort lässt sich nicht hart abbrechen; die tatsächliche Gesamtdauer kann das Budget überschreiten. Asynchrones Polling begrenzt zusätzlich die gesamte laufende Anfrage. Verwenden Sie `stream_*`; nicht-streamende Methoden lehnen `stream=True` vor dem Senden ab.

```python
from requestbeam import RequestBeam

with RequestBeam(locale="de") as client:
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

## Similarweb und Twitter

Similarweb unterstützt 27 freigegebene Operationen und erhält die nativen Antwortfelder. Es sind nur weltweite Daten (`country=999`) verfügbar. Andere gültige Länderwerte werden vom Dienst auf weltweite Daten normalisiert und liefern keine Länderdaten. Übergeben Sie bei Bedarf `from` und `to` gemeinsam über `**{"from": ..., "to": ...}`; das SDK ändert sie nicht. Leere Ergebnisse bedeuten nicht null Traffic.

```python
from requestbeam import RequestBeam

with RequestBeam(locale="de") as client:
    traffic = client.similarweb(
        "websites/visits", keys="example.com", country=999
    )
    print(traffic)
```

Twitter-Helfer unterstützen Benutzernamen, Benutzer-IDs und Benutzer-Timelines. Der Iterator liefert vollständige Seiten, folgt `meta.next_token`, begrenzt die Seitenzahl und weist wiederholte Cursor zurück. Er führt Seiten nicht zusammen und garantiert keine vollständige Timeline. Daten-GETs können kostenpflichtig sein; jede Seite ist eine eigene Anfrage.

```python
from requestbeam import RequestBeam

with RequestBeam(locale="de") as client:
    user = client.twitter_user_by_username("TwitterDev")
    user_id = user["data"]["id"]
    for page in client.iter_twitter_user_tweets(
        user_id, max_pages=3, max_results=10
    ):
        print(page)
```

## Fehler und lokale Dateien

`APIError` enthält HTTP-Status, Dienstcode, ursprüngliche Meldung, Request-ID und Antwortkörper. `TransportError`, `ProtocolError`, `PollingTimeoutError` und `JobFailedError` unterscheiden Verbindungs-, Protokoll-, Warte- und Job-Fehler. Prüfen Sie Antworten und Fehlerkörper vor Veröffentlichung auf private Daten. Schlüssel gehören nicht in Git, Browsercode, Screenshots oder Logs.

```python
from requestbeam import APIError, RequestBeam

try:
    with RequestBeam(locale="de") as client:
        client.get_job("123456789012345678")
except APIError as exc:
    print(exc.status_code, exc.code, exc.request_id)
```

Prüfen Sie die Antwortstruktur, bevor Sie Ergebnisse lokal speichern. Das SDK lädt keine entfernten Dateien automatisch herunter. Ergebnis-URLs können ablaufen; laden Sie vertrauenswürdige Dateien zeitnah mit einem separaten HTTP-Client ohne Authentifizierung, damit kein RequestBeam-Schlüssel an den Dateihost gesendet wird.

```python
import json
from pathlib import Path

# result: a response obtained from one of the calls above.
Path("result.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
)
```

## Prüfung und Grenzen

Die Tests verwenden Mock-Transporte und keine kostenpflichtigen API-Aufrufe. Stand 2026-10-29: keine Prüfung durch kostenpflichtige Live-Generierung, kein Deployment und keine PyPI-Veröffentlichung. Anfragen werden nie automatisch wiederholt, auch keine kostenpflichtigen GETs oder Generierungen. Unbekannte Parameter und Antwortstrukturen werden nicht stillschweigend geändert. Prüfen Sie die modellabhängigen Grenzen in der RequestBeam-Dokumentation.

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m build
```

Methodensignaturen und Protokollunterschiede: [API-Referenz](api-reference.md). Umfang und Prüfgrenzen: [Entwurfsnotizen](design.md).

[RequestBeam](https://requestbeam.com/de) · [API](https://requestbeam.com/de/docs/api-reference/models)
