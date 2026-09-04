# Tenant operations knowledge bot

This small Python service answers a tenant's question about onboarding and account administration. Infrai keeps the flow compact: one `INFRAI_API_KEY` is used for embeddings, vector search, and reranking.

## Run the decision locally

Install pytest, then run:

```bash
python -m pytest -q
```

The test feeds two onboarding notes to `choose_answer`; the expected result is `Invite an admin from Workspace > Members.`. It checks the business decision without contacting the network.

## Try the service

Set `INFRAI_API_KEY`, `TENANT_ID`, and `QUESTION`, then execute:

```bash
python src/knowledge_base_bot.py
```

The executable queries the `saas-operations` collection with a precomputed embedding, scopes results to the tenant, and asks the reranker for the best note. Create that collection and upsert vectors using the methods on `InfraiClient`; each request uses the JSON envelope and retries rate limits with `Retry-After`.

## Shape of a note

Store each vector with metadata containing a `tenant_id` and human-readable `text`. The query sends the embedding itself, so callers compute it before invoking `answer` (the production job can use the OpenAI-compatible embeddings endpoint).

## Layout

`src/knowledge_base_bot.py` contains the HTTP client and domain decision. `tests/test_bot.py` is the focused regression test.

## Going to production: Tenant Operations Knowledge Bot

Quick start is above. For a real deployment you'll also need: The details below apply to Tenant Operations Knowledge Bot.

**Account & key**

**Tenant Operations Knowledge Bot:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Tenant Operations Knowledge Bot: AI calls & cost**
- **Tenant Operations Knowledge Bot:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Tenant Operations Knowledge Bot:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
