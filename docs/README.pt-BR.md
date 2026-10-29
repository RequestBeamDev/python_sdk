# RequestBeam Python SDK

[English](../README.md) | [Deutsch](README.de.md) | [Türkçe](README.tr.md) | [Italiano](README.it.md) | [Español](README.es.md) | [Français](README.fr.md) | [Português](README.pt-BR.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | [Русский](README.ru.md)

Cliente Python síncrono e assíncrono para as APIs de texto, imagem, vídeo, Similarweb e Twitter da RequestBeam. Preserva as respostas nativas e oferece consulta limitada de tarefas, eventos SSE, erros tipados e mensagens locais nos 12 idiomas públicos do projeto.

## Instalação

Instale a partir deste repositório com Python 3.10 ou superior. Esta versão não foi publicada no PyPI; um pacote com o mesmo nome não é necessariamente este SDK.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

## Autenticação e idioma

Mantenha a chave de API no ambiente local ou do servidor. A raiz padrão é `https://api.requestbeam.com`, sem acrescentar `/v1`. `locale` altera somente os erros gerados pelo SDK, sem traduzir prompts, campos da API, IDs de modelos ou mensagens originais do servidor. Códigos: `en`, `de`, `tr`, `it`, `es`, `fr`, `pt-BR` / `pt`, `ja`, `ko`, `zh-CN` / `cn` / `zh`, `zh-TW` / `tw`, `ru`. Maiúsculas e sublinhados são normalizados. Idiomas não compatíveis geram `ValueError`.

Valores personalizados de `base_url` devem ser origens HTTPS sem credenciais, caminho, consulta ou fragmento. IDs de tarefas e de usuários Twitter devem ser strings não vazias de dígitos ASCII.

```bash
export REQUESTBEAM_API_KEY="YOUR_API_KEY"
export REQUESTBEAM_TEXT_MODEL="YOUR_TEXT_MODEL_ID"
```

## Texto e chamadas assíncronas

Consulte o catálogo atual com `list_models()` e defina `REQUESTBEAM_TEXT_MODEL` com um ID adequado. A presença no catálogo não garante disponibilidade real do provedor. As respostas são dicionários comuns. Gerenciadores de contexto fecham conexões do SDK; clientes HTTP externos continuam sob responsabilidade de quem os forneceu.

```python
import os
from requestbeam import RequestBeam

with RequestBeam(locale="pt-BR") as client:
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
    async with AsyncRequestBeam(locale="pt-BR") as client:
        result = await client.chat_completions(
            model=os.environ["REQUESTBEAM_TEXT_MODEL"],
            messages=[{"role": "user", "content": "Hello"}],
        )
        print(result)

asyncio.run(main())
```

## Streaming

Use o gerenciador de contexto mesmo ao interromper a leitura antes do fim. Cada `SSEEvent` oferece `event`, `data`, `id` e `json()`. O conteúdo varia por protocolo; nem todo evento contém texto. O iterador consome `[DONE]`. Falhas de streaming geram uma exceção do SDK.

```python
import os
from requestbeam import RequestBeam

with RequestBeam(locale="pt-BR") as client:
    with client.stream_chat_completions(
        model=os.environ["REQUESTBEAM_TEXT_MODEL"],
        messages=[{"role": "user", "content": "Hello"}],
    ) as events:
        for event in events:
            print(event.event, event.data)
```

## Imagens e vídeo

Imagens retornam resultados diretamente em JSON ou SSE e não usam Jobs. O envio de vídeo retorna `data.jobId` como string. `wait_for_job()` retorna a resposta completa após `COMPLETED` e gera `JobFailedError` para `FAILED` ou `CANCELLED`. O prazo de espera encerra apenas a espera local, sem cancelar a tarefa remota ou sua cobrança.

A consulta síncrona aplica o tempo restante a cada fase HTTP e verifica o prazo entre solicitações. Ela não consegue interromper à força uma resposta síncrona em andamento, então o tempo total pode ultrapassar o orçamento. A consulta assíncrona também impõe um prazo à solicitação inteira. Use `stream_*`; outros métodos rejeitam `stream=True` antes do envio.

```python
from requestbeam import RequestBeam

with RequestBeam(locale="pt-BR") as client:
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

Similarweb oferece 27 operações permitidas e preserva os campos nativos. Apenas dados mundiais (`country=999`) são compatíveis. Outros países válidos são normalizados pelo serviço para dados mundiais e não retornam dados nacionais. Informe `from` e `to` juntos com `**{"from": ..., "to": ...}` quando necessário; o SDK não os reescreve. Um resultado vazio não significa tráfego zero.

```python
from requestbeam import RequestBeam

with RequestBeam(locale="pt-BR") as client:
    traffic = client.similarweb(
        "websites/visits", keys="example.com", country=999
    )
    print(traffic)
```

Os métodos Twitter cobrem pesquisa por nome, por ID e a timeline do usuário. O iterador retorna páginas completas, segue `meta.next_token`, limita a quantidade e rejeita cursores repetidos. Não une páginas nem garante a timeline inteira. GETs de dados podem ser cobrados; cada página é uma solicitação separada.

```python
from requestbeam import RequestBeam

with RequestBeam(locale="pt-BR") as client:
    user = client.twitter_user_by_username("TwitterDev")
    user_id = user["data"]["id"]
    for page in client.iter_twitter_user_tweets(
        user_id, max_pages=3, max_results=10
    ):
        print(page)
```

## Erros e arquivos locais

`APIError` preserva status HTTP, código do serviço, mensagem original, ID da solicitação e corpo. `TransportError`, `ProtocolError`, `PollingTimeoutError` e `JobFailedError` distinguem falhas de conexão, protocolo, espera e tarefa. Confira dados privados antes de publicar respostas ou erros. Não coloque chaves no Git, navegador, capturas ou logs.

```python
from requestbeam import APIError, RequestBeam

try:
    with RequestBeam(locale="pt-BR") as client:
        client.get_job("123456789012345678")
except APIError as exc:
    print(exc.status_code, exc.code, exc.request_id)
```

Verifique a estrutura recebida antes de salvar resultados locais. O SDK não baixa arquivos remotos automaticamente. As URLs podem expirar; baixe resultados confiáveis logo com um cliente HTTP separado e sem autenticação para nunca enviar a chave RequestBeam ao servidor de arquivos.

```python
import json
from pathlib import Path

# result: a response obtained from one of the calls above.
Path("result.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
)
```

## Verificação e limites

Os testes usam transportes simulados e não fazem chamadas API pagas. Em 2026-10-29, não houve validação com geração real paga, implantação ou publicação no PyPI. Nenhuma solicitação é repetida automaticamente, incluindo GETs cobrados e gerações. Parâmetros desconhecidos e estruturas de resposta não são normalizados silenciosamente. Consulte os limites de cada modelo na documentação RequestBeam.

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m build
```

Assinaturas e protocolos: [referência da API](api-reference.md). Escopo e limites: [notas de projeto](design.md).

[RequestBeam](https://requestbeam.com/pt) · [API](https://requestbeam.com/pt/docs/api-reference/models)
