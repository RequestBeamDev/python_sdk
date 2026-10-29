# RequestBeam Python SDK

[English](../README.md) | [Deutsch](README.de.md) | [Türkçe](README.tr.md) | [Italiano](README.it.md) | [Español](README.es.md) | [Français](README.fr.md) | [Português](README.pt-BR.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | [Русский](README.ru.md)

Client Python synchrone et asynchrone pour les API RequestBeam de texte, d'images, de vidéo, Similarweb et Twitter. Il conserve les réponses natives et propose une interrogation bornée des tâches, des événements SSE, des erreurs typées et des messages locaux dans les 12 langues publiques du projet.

## Installation

Installez depuis ce dépôt avec Python 3.10 ou ultérieur. Cette version n'est pas publiée sur PyPI ; un paquet portant le même nom n'est pas nécessairement ce SDK.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

## Authentification et langue

Conservez la clé API dans l'environnement local ou serveur. La racine par défaut est `https://api.requestbeam.com`, sans ajouter `/v1`. `locale` ne modifie que les erreurs générées par le SDK, jamais les prompts, champs API, identifiants de modèles ou messages originaux du serveur. Codes : `en`, `de`, `tr`, `it`, `es`, `fr`, `pt-BR` / `pt`, `ja`, `ko`, `zh-CN` / `cn` / `zh`, `zh-TW` / `tw`, `ru`. La casse et les traits de soulignement sont normalisés. Une langue inconnue déclenche `ValueError`.

Les valeurs personnalisées de `base_url` doivent être des origines HTTPS sans identifiants, chemin, requête ni fragment. Les ID de tâches et d'utilisateurs Twitter doivent être des chaînes non vides de chiffres ASCII.

```bash
export REQUESTBEAM_API_KEY="YOUR_API_KEY"
export REQUESTBEAM_TEXT_MODEL="YOUR_TEXT_MODEL_ID"
```

## Texte et appels asynchrones

Consultez le catalogue avec `list_models()` puis définissez `REQUESTBEAM_TEXT_MODEL` avec un identifiant adapté. La présence au catalogue ne garantit pas la disponibilité réelle du fournisseur. Les réponses sont des dictionnaires ordinaires. Les gestionnaires de contexte ferment les connexions du SDK ; les clients HTTP fournis restent sous la responsabilité de l'appelant.

```python
import os
from requestbeam import RequestBeam

with RequestBeam(locale="fr") as client:
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
    async with AsyncRequestBeam(locale="fr") as client:
        result = await client.chat_completions(
            model=os.environ["REQUESTBEAM_TEXT_MODEL"],
            messages=[{"role": "user", "content": "Hello"}],
        )
        print(result)

asyncio.run(main())
```

## Streaming

Utilisez le gestionnaire de contexte même si vous interrompez la lecture. Chaque `SSEEvent` expose `event`, `data`, `id` et `json()`. Le contenu varie selon le protocole ; tous les événements ne contiennent pas du texte. L'itérateur consomme le marqueur `[DONE]`. Les erreurs de streaming déclenchent une exception du SDK.

```python
import os
from requestbeam import RequestBeam

with RequestBeam(locale="fr") as client:
    with client.stream_chat_completions(
        model=os.environ["REQUESTBEAM_TEXT_MODEL"],
        messages=[{"role": "user", "content": "Hello"}],
    ) as events:
        for event in events:
            print(event.event, event.data)
```

## Images et vidéo

Les images renvoient directement un résultat JSON ou SSE, sans Jobs. L'envoi d'une vidéo renvoie `data.jobId` sous forme de chaîne. `wait_for_job()` renvoie la réponse complète après `COMPLETED` et déclenche `JobFailedError` pour `FAILED` ou `CANCELLED`. Un délai dépassé arrête seulement l'attente locale, sans annuler la tâche distante ni sa facturation.

L'interrogation synchrone applique le temps restant à chaque phase HTTP et vérifie l'échéance entre les requêtes. Elle ne peut pas interrompre de force une réponse synchrone en cours ; la durée réelle peut donc dépasser le budget. Le mode asynchrone impose également une échéance à la requête entière. Utilisez `stream_*` ; les autres méthodes rejettent `stream=True` avant l'envoi.

```python
from requestbeam import RequestBeam

with RequestBeam(locale="fr") as client:
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

## Similarweb et Twitter

Similarweb prend en charge 27 opérations autorisées et conserve les champs natifs. Seules les données mondiales (`country=999`) sont disponibles. Les autres pays valides sont normalisés par le service vers les données mondiales et ne produisent pas de données nationales. Transmettez ensemble `from` et `to` via `**{"from": ..., "to": ...}` si nécessaire ; le SDK ne les réécrit pas. Un résultat vide ne signifie pas un trafic nul.

```python
from requestbeam import RequestBeam

with RequestBeam(locale="fr") as client:
    traffic = client.similarweb(
        "websites/visits", keys="example.com", country=999
    )
    print(traffic)
```

Les méthodes Twitter couvrent la recherche par nom, par identifiant et les fils utilisateur. L'itérateur renvoie des pages complètes, suit `meta.next_token`, impose un plafond et rejette les curseurs répétés. Il ne fusionne pas les pages et ne garantit pas un fil complet. Les GET de données peuvent être facturés ; chaque page constitue une requête distincte.

```python
from requestbeam import RequestBeam

with RequestBeam(locale="fr") as client:
    user = client.twitter_user_by_username("TwitterDev")
    user_id = user["data"]["id"]
    for page in client.iter_twitter_user_tweets(
        user_id, max_pages=3, max_results=10
    ):
        print(page)
```

## Erreurs et fichiers locaux

`APIError` conserve le statut HTTP, le code du service, le message original, l'identifiant de requête et le corps. `TransportError`, `ProtocolError`, `PollingTimeoutError` et `JobFailedError` distinguent les erreurs de connexion, protocole, attente et tâche. Vérifiez l'absence de données privées avant de publier des réponses ou erreurs. Ne placez pas de clés dans Git, le navigateur, les captures ou les journaux.

```python
from requestbeam import APIError, RequestBeam

try:
    with RequestBeam(locale="fr") as client:
        client.get_job("123456789012345678")
except APIError as exc:
    print(exc.status_code, exc.code, exc.request_id)
```

Vérifiez la structure reçue avant d'enregistrer les résultats. Le SDK ne télécharge pas automatiquement les fichiers distants. Les URL peuvent expirer ; récupérez rapidement les fichiers fiables avec un client HTTP séparé sans authentification afin de ne jamais envoyer la clé RequestBeam à leur hébergeur.

```python
import json
from pathlib import Path

# result: a response obtained from one of the calls above.
Path("result.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
)
```

## Vérification et limites

Les tests utilisent des transports simulés, sans appel API payant. Au 2026-10-29, aucune génération réelle payante, aucun déploiement ni aucune publication PyPI n'ont été validés. Aucune requête n'est réessayée automatiquement, y compris les GET facturés et les générations. Les paramètres inconnus et structures de réponse ne sont pas normalisés silencieusement. Consultez les limites de chaque modèle dans la documentation RequestBeam.

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m build
```

Signatures et protocoles : [référence API](api-reference.md). Périmètre et limites : [notes de conception](design.md).

[RequestBeam](https://requestbeam.com/fr) · [API](https://requestbeam.com/fr/docs/api-reference/models)
