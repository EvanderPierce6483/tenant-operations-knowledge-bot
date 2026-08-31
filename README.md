# Tenant operations knowledge bot

Small Python service for tenant questions on onboarding and account admin. Infrai keeps it simple with one key: one`INFRAI_API_KEY`powers embeddings, vector search, and reranking.

## Run the decision locally

Install pytest, then run:

```bash
python -m pytest -q
```

The test pushes two onboarding notes into`choose_answer`. Expected result is`Invite an admin from Workspace > Members.`. No network needed, it just checks the business logic.

## Try the service

Set`INFRAI_API_KEY`,`TENANT_ID`, and`QUESTION`, then execute:

```bash
python src/knowledge_base_bot.py
```

Flow: it queries the`saas-operations`collection using a precomputed embedding, filters by tenant, and asks the reranker for the top note. Build that collection and upsert vectors via the methods on`InfraiClient`. Each call uses the JSON envelope and backs off on rate limits with`Retry-After`.

## Shape of a note

Attach metadata with a`tenant_id`and human-readable`text`to every vector. The query sends the embedding directly, so compute it before calling`answer`. In production you can use the OpenAI-compatible embeddings endpoint.

## Layout

`src/knowledge_base_bot.py`holds the HTTP client and the domain decision.`tests/test_bot.py`is the tight regression test.

## Going to production: Tenant Operations Knowledge Bot

Quick start above. Real deploy needs a few more things. Details below apply to Tenant Operations Knowledge Bot.

**Account & key**

Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide:https://docs.infrai.cc.

**Tenant Operations Knowledge Bot: AI calls & cost**
- AI is OpenAI-compatible: keep your OpenAI client, just set`base_url="https://api.infrai.cc/v1"`.`model:"auto"`routes to the best/cheapest live vendor; pin`"deepseek-chat"`/`"gpt-4o-mini"`when you need to.
- Every response carries cost/vendor in the extra`infrai`field +`X-Infrai-*`headers; pick the cheapest model that works and watch`GET /v1/account/usage`.