# RequestBeam Python SDK

[English](../README.md) | [Deutsch](README.de.md) | [Türkçe](README.tr.md) | [Italiano](README.it.md) | [Español](README.es.md) | [Français](README.fr.md) | [Português](README.pt-BR.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | [Русский](README.ru.md)

Client Python sincrono e asincrono per le API RequestBeam di testo, immagini, video, Similarweb e Twitter. Conserva le risposte native e offre polling limitato dei processi, eventi SSE, errori tipizzati e messaggi locali nelle 12 lingue pubbliche del progetto.

## Installazione

Installa da questo repository con Python 3.10 o successivo. Questa versione non è pubblicata su PyPI: un pacchetto omonimo non è necessariamente questo SDK.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

## Autenticazione e lingua

Conserva la chiave API nell'ambiente locale o del server. La radice predefinita è `https://api.requestbeam.com`; non aggiungere `/v1`. `locale` modifica solo gli errori generati dall'SDK, senza tradurre prompt, campi API, ID dei modelli o messaggi originali del server. Codici supportati: `en`, `de`, `tr`, `it`, `es`, `fr`, `pt-BR` / `pt`, `ja`, `ko`, `zh-CN` / `cn` / `zh`, `zh-TW` / `tw`, `ru`. Maiuscole e trattini bassi vengono normalizzati. Le lingue sconosciute generano `ValueError`.

I valori personalizzati di `base_url` devono essere origini HTTPS senza credenziali, percorso, query o frammento. Gli ID dei processi e degli utenti Twitter devono essere stringhe non vuote di cifre ASCII.

```bash
export REQUESTBEAM_API_KEY="YOUR_API_KEY"
export REQUESTBEAM_TEXT_MODEL="YOUR_TEXT_MODEL_ID"
```

## Testo e chiamate asincrone

Consulta il catalogo corrente con `list_models()` e imposta `REQUESTBEAM_TEXT_MODEL` su un ID appropriato. La presenza nel catalogo non garantisce la disponibilità effettiva del fornitore. Le risposte sono normali dizionari. I gestori di contesto chiudono le connessioni dell'SDK; i client HTTP forniti dall'esterno restano sotto la responsabilità del chiamante.

```python
import os
from requestbeam import RequestBeam

with RequestBeam(locale="it") as client:
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
    async with AsyncRequestBeam(locale="it") as client:
        result = await client.chat_completions(
            model=os.environ["REQUESTBEAM_TEXT_MODEL"],
            messages=[{"role": "user", "content": "Hello"}],
        )
        print(result)

asyncio.run(main())
```

## Streaming

Usa il gestore di contesto anche quando interrompi la lettura in anticipo. Ogni `SSEEvent` espone `event`, `data`, `id` e `json()`. I dati dipendono dal protocollo: non tutti gli eventi contengono testo. L'iteratore consuma il marcatore `[DONE]`. Gli errori di streaming generano un'eccezione dell'SDK.

```python
import os
from requestbeam import RequestBeam

with RequestBeam(locale="it") as client:
    with client.stream_chat_completions(
        model=os.environ["REQUESTBEAM_TEXT_MODEL"],
        messages=[{"role": "user", "content": "Hello"}],
    ) as events:
        for event in events:
            print(event.event, event.data)
```

## Immagini e video

Le immagini restituiscono direttamente JSON o SSE e non usano Jobs. L'invio di un video restituisce `data.jobId` come stringa. `wait_for_job()` restituisce la risposta completa dopo `COMPLETED` e genera `JobFailedError` per `FAILED` o `CANCELLED`. Il timeout interrompe solo l'attesa locale, senza annullare il processo remoto o i relativi addebiti.

Il polling sincrono applica il tempo residuo a ogni fase HTTP e controlla la scadenza tra le richieste. Non può interrompere forzatamente una risposta sincrona in corso, quindi il tempo totale può superare il budget. Il polling asincrono impone anche una scadenza alla richiesta in corso. Usa `stream_*` per lo streaming; gli altri metodi rifiutano `stream=True` prima dell'invio.

```python
from requestbeam import RequestBeam

with RequestBeam(locale="it") as client:
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

## Similarweb e Twitter

Similarweb supporta 27 operazioni consentite e conserva i campi nativi delle risposte. Sono disponibili solo dati mondiali (`country=999`). Altri valori di paese validi vengono normalizzati dal servizio su dati mondiali, non su dati nazionali. Se necessario, passa insieme `from` e `to` tramite `**{"from": ..., "to": ...}`; l'SDK non li riscrive. Un risultato vuoto non significa traffico zero.

```python
from requestbeam import RequestBeam

with RequestBeam(locale="it") as client:
    traffic = client.similarweb(
        "websites/visits", keys="example.com", country=999
    )
    print(traffic)
```

Gli helper Twitter coprono ricerca per nome utente, ID utente e timeline. L'iteratore restituisce pagine complete, segue `meta.next_token`, limita il numero di pagine e rifiuta cursori ripetuti. Non unisce le pagine né garantisce l'intera timeline. Le richieste GET di dati possono essere a pagamento; ogni pagina è una richiesta distinta.

```python
from requestbeam import RequestBeam

with RequestBeam(locale="it") as client:
    user = client.twitter_user_by_username("TwitterDev")
    user_id = user["data"]["id"]
    for page in client.iter_twitter_user_tweets(
        user_id, max_pages=3, max_results=10
    ):
        print(page)
```

## Errori e file locali

`APIError` conserva stato HTTP, codice del servizio, messaggio originale, ID richiesta e corpo della risposta. `TransportError`, `ProtocolError`, `PollingTimeoutError` e `JobFailedError` distinguono errori di connessione, protocollo, attesa e processo. Verifica che risposte e corpi degli errori non contengano dati privati prima di pubblicarli. Non inserire chiavi nel codice, nel browser, negli screenshot o nei log.

```python
from requestbeam import APIError, RequestBeam

try:
    with RequestBeam(locale="it") as client:
        client.get_job("123456789012345678")
except APIError as exc:
    print(exc.status_code, exc.code, exc.request_id)
```

Controlla la struttura restituita prima di salvare i risultati. L'SDK non scarica automaticamente file remoti. Gli URL dei risultati possono scadere: scarica tempestivamente i file attendibili con un client HTTP separato senza autenticazione, per non inviare la chiave RequestBeam al server dei file.

```python
import json
from pathlib import Path

# result: a response obtained from one of the calls above.
Path("result.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
)
```

## Verifica e limiti

I test usano trasporti simulati e non effettuano chiamate API a pagamento. Al 2026-10-29 non sono state eseguite generazioni reali a pagamento, distribuzioni o pubblicazioni su PyPI. Nessuna richiesta viene ripetuta automaticamente, incluse GET a pagamento e generazioni. Parametri sconosciuti e strutture di risposta non vengono normalizzati silenziosamente. Consulta i limiti del modello nella documentazione RequestBeam prima di eseguire gli esempi.

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m build
```

Firme e differenze di protocollo: [riferimento API](api-reference.md). Ambito e limiti di verifica: [note di progettazione](design.md).

[RequestBeam](https://requestbeam.com/it) · [API](https://requestbeam.com/it/docs/api-reference/models)
