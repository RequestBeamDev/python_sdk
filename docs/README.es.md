# RequestBeam Python SDK

[English](../README.md) | [Deutsch](README.de.md) | [Türkçe](README.tr.md) | [Italiano](README.it.md) | [Español](README.es.md) | [Français](README.fr.md) | [Português](README.pt-BR.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | [Русский](README.ru.md)

Cliente Python síncrono y asíncrono para las API de texto, imágenes, vídeo, Similarweb y Twitter de RequestBeam. Conserva las respuestas nativas y ofrece consultas de trabajos limitadas, eventos SSE, errores tipados y mensajes locales en los 12 idiomas públicos del proyecto.

## Instalación

Instala desde este repositorio con Python 3.10 o posterior. Esta versión no se ha publicado en PyPI; no supongas que un paquete con el mismo nombre sea este SDK.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

## Autenticación e idioma

Guarda la clave API en el entorno local o del servidor. La raíz predeterminada es `https://api.requestbeam.com`, sin añadir `/v1`. `locale` solo cambia los errores generados por el SDK; no traduce prompts, campos API, ID de modelos ni mensajes originales del servidor. Códigos: `en`, `de`, `tr`, `it`, `es`, `fr`, `pt-BR` / `pt`, `ja`, `ko`, `zh-CN` / `cn` / `zh`, `zh-TW` / `tw`, `ru`. Se normalizan las mayúsculas y los guiones bajos. Un idioma no compatible genera `ValueError`.

Los valores personalizados de `base_url` deben ser orígenes HTTPS sin credenciales, ruta, consulta ni fragmento. Los ID de trabajos y usuarios Twitter deben ser cadenas no vacías de dígitos ASCII.

```bash
export REQUESTBEAM_API_KEY="YOUR_API_KEY"
export REQUESTBEAM_TEXT_MODEL="YOUR_TEXT_MODEL_ID"
```

## Texto y llamadas asíncronas

Consulta el catálogo con `list_models()` y asigna un ID adecuado a `REQUESTBEAM_TEXT_MODEL`. Estar en el catálogo no garantiza disponibilidad real del proveedor. Las respuestas son diccionarios normales. Los gestores de contexto cierran las conexiones del SDK; los clientes HTTP externos siguen siendo responsabilidad de quien los proporciona.

```python
import os
from requestbeam import RequestBeam

with RequestBeam(locale="es") as client:
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
    async with AsyncRequestBeam(locale="es") as client:
        result = await client.chat_completions(
            model=os.environ["REQUESTBEAM_TEXT_MODEL"],
            messages=[{"role": "user", "content": "Hello"}],
        )
        print(result)

asyncio.run(main())
```

## Streaming

Usa el gestor de contexto del stream incluso si dejas de leer antes. Cada `SSEEvent` ofrece `event`, `data`, `id` y `json()`. El contenido varía por protocolo; no todos los eventos contienen texto. El iterador consume `[DONE]`. Los errores de streaming generan una excepción del SDK.

```python
import os
from requestbeam import RequestBeam

with RequestBeam(locale="es") as client:
    with client.stream_chat_completions(
        model=os.environ["REQUESTBEAM_TEXT_MODEL"],
        messages=[{"role": "user", "content": "Hello"}],
    ) as events:
        for event in events:
            print(event.event, event.data)
```

## Imágenes y vídeo

Las imágenes devuelven el resultado directamente como JSON o SSE y no utilizan Jobs. El envío de vídeo devuelve `data.jobId` como cadena. `wait_for_job()` devuelve la respuesta completa tras `COMPLETED` y genera `JobFailedError` para `FAILED` o `CANCELLED`. Agotar el tiempo de espera solo detiene la espera local, no cancela el trabajo remoto ni sus cargos.

El sondeo síncrono aplica el tiempo restante a cada fase HTTP y comprueba el plazo entre solicitudes. No puede interrumpir por la fuerza una respuesta síncrona en curso, por lo que la duración total puede superar el presupuesto. El sondeo asíncrono también impone un plazo a toda la solicitud en curso. Usa `stream_*`; los demás métodos rechazan `stream=True` antes de enviar.

```python
from requestbeam import RequestBeam

with RequestBeam(locale="es") as client:
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

## Similarweb y Twitter

Similarweb admite 27 operaciones autorizadas y conserva los campos nativos de cada respuesta. Solo se admiten datos mundiales (`country=999`). Otros países válidos se convierten en datos mundiales en el servicio; no producen datos por país. Pasa `from` y `to` juntos mediante `**{"from": ..., "to": ...}` cuando sea necesario; el SDK no los modifica. Un resultado vacío no equivale a tráfico cero.

```python
from requestbeam import RequestBeam

with RequestBeam(locale="es") as client:
    traffic = client.similarweb(
        "websites/visits", keys="example.com", country=999
    )
    print(traffic)
```

Los métodos Twitter cubren búsquedas por nombre, ID de usuario y cronologías. El iterador entrega páginas nativas completas, sigue `meta.next_token`, limita las páginas y rechaza cursores repetidos. No combina páginas ni garantiza obtener toda la cronología. Los GET de datos pueden tener coste; cada página es una solicitud independiente.

```python
from requestbeam import RequestBeam

with RequestBeam(locale="es") as client:
    user = client.twitter_user_by_username("TwitterDev")
    user_id = user["data"]["id"]
    for page in client.iter_twitter_user_tweets(
        user_id, max_pages=3, max_results=10
    ):
        print(page)
```

## Errores y archivos locales

`APIError` conserva estado HTTP, código del servicio, mensaje original, ID de solicitud y cuerpo. `TransportError`, `ProtocolError`, `PollingTimeoutError` y `JobFailedError` separan fallos de conexión, protocolo, espera y trabajo. Revisa los datos privados antes de publicar respuestas o cuerpos de error. No incluyas claves en Git, código del navegador, capturas o registros.

```python
from requestbeam import APIError, RequestBeam

try:
    with RequestBeam(locale="es") as client:
        client.get_job("123456789012345678")
except APIError as exc:
    print(exc.status_code, exc.code, exc.request_id)
```

Comprueba la estructura antes de guardar los resultados localmente. El SDK no descarga archivos remotos automáticamente. Las URL pueden caducar: descarga resultados de confianza pronto con un cliente HTTP separado y sin autenticación para no enviar la clave RequestBeam al servidor de archivos.

```python
import json
from pathlib import Path

# result: a response obtained from one of the calls above.
Path("result.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
)
```

## Verificación y límites

Las pruebas usan transportes simulados y no hacen llamadas API de pago. A fecha 2026-10-29 no hay validación con generación real de pago, despliegue ni publicación en PyPI. Ninguna solicitud se reintenta automáticamente, incluidos GET facturables y envíos de generación. No se normalizan silenciosamente parámetros desconocidos ni estructuras de respuesta. Consulta los límites de cada modelo en la documentación de RequestBeam.

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m build
```

Firmas y protocolos: [referencia API](api-reference.md). Alcance y límites de verificación: [notas de diseño](design.md).

[RequestBeam](https://requestbeam.com/es) · [API](https://requestbeam.com/es/docs/api-reference/models)
