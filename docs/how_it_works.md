# EGRS AI — Complete Course: How Everything Works

> **Author**: EGRS Engineering Team  
> **Updated**: May 2026  
> **System**: AI layer for the EGRS application (Energy Management, Orange Tunisie)

---

## Table of Contents

1. [Big Picture](#1-big-picture)
2. [What is an LLM?](#2-what-is-an-llm)
3. [What is RAG? (Retrieval-Augmented Generation)](#3-what-is-rag-retrieval-augmented-generation)
4. [System Components](#4-system-components)
5. [The Complete Pipeline — Step by Step](#5-the-complete-pipeline--step-by-step)
6. [Deep Dive: Data Layer](#6-deep-dive-data-layer)
7. [Deep Dive: ML Layer (XGBoost)](#7-deep-dive-ml-layer-xgboost)
8. [Deep Dive: RAG Layer (pgvector)](#8-deep-dive-rag-layer-pgvector)
9. [Deep Dive: LLM Layer (Ollama + Qwen)](#9-deep-dive-llm-layer-ollama--qwen)
10. [Deep Dive: Report Generation](#10-deep-dive-report-generation)
11. [Deep Dive: API Layer (FastAPI)](#11-deep-dive-api-layer-fastapi)
12. [Walkthrough — Real Scenario](#12-walkthrough--real-scenario)
13. [Key Architecture Decisions](#13-key-architecture-decisions)
14. [How to Run / Test / Modify](#14-how-to-run--test--modify)
15. [Glossary](#15-glossary)
16. [Appendix: File Index](#16-appendix-file-index)

---

# 1. Big Picture

## What does this system do?

EGRS (Energy Management System) tracks electricity consumption for Orange Tunisie's cell tower sites (4G/5G). The **AI layer** adds three capabilities:

1. **Predict next year's budget** — given historical invoices, forecast consumption and cost
2. **Analyze current year** — show billing, site visit compliance, technician performance
3. **Evaluate new site investments** — if Orange wants to build 50 new 4G towers, estimate their energy cost

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js / Flutter)             │
│                         Port 3001 / mobile                      │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    NESTJS BACKEND (proxy)                        │
│  Port 3000  ───  /ai/*  ───  proxies to FastAPI                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                    FASTAPI AI SERVICE                             │
│  Port 5000                                                       │
│                                                                   │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────────┐ │
│  │ API Routers │──│ LLM Chain    │──│ Report Generator         │ │
│  │ (reports,   │  │ (orchestrator)│  │ (PDF / JSON / Excel)    │ │
│  │  analytics, │  └──────┬───────┘  └──────────────────────────┘ │
│  │  ingestion) │         │                                        │
│  └─────────────┘         │                                        │
│                          ▼                                        │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                AI Engine Layers                             │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────────────┐  │  │
│  │  │ Data     │  │ ML       │  │ LLM / RAG                │  │  │
│  │  │Extractors│──│(XGBoost) │──│(Ollama + pgvector)        │  │  │
│  │  │ (SQL)    │  │          │  │                            │  │  │
│  │  └────┬─────┘  └──────────┘  └──────────────────────────┘  │  │
│  └───────┼────────────────────────────────────────────────────┘  │
└──────────┼───────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────┐
│                    POSTGRESQL (pgvector)                          │
│  Port 5432                                                       │
│  ┌──────────────┐  ┌──────────────────┐  ┌───────────────────┐  │
│  │ invoice_items│  │ consumption_vectors│  │ tariff_config     │  │
│  │ (149K rows)  │  │ (vector(12) + HNSW) │  │ (pricing rules)  │  │
│  └──────────────┘  └──────────────────┘  └───────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────┐
│                    OLLAMA (local LLM)                             │
│  Port 11434                                                      │
│  Model: qwen2.5:3b                                                │
└──────────────────────────────────────────────────────────────────┘
```

## The Key Insight

**Three different AI techniques work together:**

| Technique | What it does | Analogy |
|-----------|-------------|---------|
| **XGBoost** (ML) | Predicts numbers (kWh, cost) | A calculator with a memory of past patterns |
| **pgvector** (RAG) | Finds similar historical sites | A librarian who finds the most relevant books |
| **Qwen/LLM** | Generates natural language reports | A human analyst who reads data and writes a report |

---

# 2. What is an LLM?

## The One-Sentence Answer

A **Large Language Model (LLM)** is a neural network trained on massive amounts of text that predicts the next word in a sequence — and by doing this billions of times, it can write coherent paragraphs, answer questions, and follow instructions.

## How it Works (Simplified)

```
Input:  "The capital of France is"
        ↓
[Neural Network with billions of parameters]
        ↓
Output: "Paris" (with 92% probability)
        "Lyon"  (with 3% probability)
        ...
```

Training: The model read billions of sentences from the internet and learned patterns:
- "capital of France" → "Paris"
- "forecast for next year" → growth-related words
- Numbers and percentages → financial analysis language

The "7 billion parameters" in `qwen2.5:3b` refers to the number of mathematical weights the model uses — roughly analogous to the number of "connections" in its brain.

## Key Concepts

### Tokens
LLMs don't read characters, they read **tokens** — chunks of text:
- "hello" = 1 token
- "unbelievable" = 3 tokens ("un", "believe", "able")
- This sentence ≈ 15 tokens

Qwen2.5:3b has a context window of ~32K tokens (about 24,000 words).

### Temperature
Controls randomness in the output:
- **0.1** (what we use) — very deterministic, almost always picks the most likely word
- **0.5** — some creativity
- **1.0** — full creativity (can be incoherent)

We use **0.1** because we want factual, reproducible budget reports — not creative fiction.

### System Prompt vs User Prompt
```
SYSTEM PROMPT:  "You are a budget analyst. Be precise."
                ↓ (sets the role and rules, not visible to user)
USER PROMPT:    "Forecast 2027 budget given this data: ..."
                ↓ (the actual task)
LLM RESPONSE:   "{executive_summary: '...', consumption_forecast: {...}}"
```

### Structured Output (JSON Schema)
Normally LLMs output free text. We want **structured JSON** that our code can parse. Ollama supports **constrained decoding** — we tell it the JSON schema and it only outputs valid JSON matching that schema:

```json
{
  "type": "object",
  "properties": {
    "executive_summary": {"type": "string"},
    "consumption_forecast": {
      "type": "object",
      "properties": {
        "total_predicted_kwh": {"type": "number"},
        "monthly_breakdown": {"type": "array", ...}
      }
    }
  }
}
```

## Why Local LLMs? (Why not ChatGPT?)

| Factor | ChatGPT / Claude | Local Qwen (our choice) |
|--------|-----------------|------------------------|
| **Data privacy** | Your data leaves your server | Stays 100% on-premise |
| **Cost** | Pay per token ($$\$) | Free (just electricity) |
| **Latency** | Internet RTT + queue | Direct, predictable |
| **Offline** | Requires internet | Works fully offline |
| **Customization** | Limited | Full control |
| **Quality** | Better (GPT-4, Claude 3.5) | Good enough for structured tasks |

**Trade-off**: Qwen2.5:3b is smaller and less "smart" than GPT-4. But for structured data → structured JSON tasks, it performs well. If we needed poetic marketing copy, we'd use GPT-4.

---

# 3. What is RAG? (Retrieval-Augmented Generation)

## The Core Problem

An LLM knows about "electricity consumption" in general, but it doesn't know:
- How much Site #1234 consumed last year
- Which sites are similar to a new proposed site
- What the tariff rates are for BT vs MT customers

**RAG solves this**: Before asking the LLM a question, we retrieve relevant data from our database and inject it into the prompt.

## How RAG Works in This Project

```
Step 1: USER asks "Forecast budget for 5 new 4G sites"
         ↓
Step 2: RETRIEVAL: Find historical sites similar to the proposed new sites
         ↓                   ↓
         Query vector        Vector database (pgvector)
         [site config,       ┌──────────────────────┐
          network type,  →   │ consumption_vectors  │
          est. kWh/month]    │ vector | year | site │
                              │ ...                  │
                              └──────────────────────┘
         ↓
Step 3: AUGMENT: Inject similar sites' data into the prompt
         "These are consumption patterns of 10 similar sites: ..."
         ↓
Step 4: GENERATE: LLM uses this context to produce the report
```

## What is a Vector Embedding?

A **vector** is just a list of numbers. In our case, a 12-dimensional vector representing a site's monthly consumption pattern:

```
Site A: [4500, 4200, 4800, 5100, 5300, 5500, 5800, 5600, 5200, 4900, 4600, 4400]
         Jan   Feb   Mar   Apr   May   Jun   Jul   Aug   Sep   Oct   Nov   Dec
```

Each position = consumption for that month. This captures the **seasonal pattern** of the site.

## Cosine Similarity — How We Compare Vectors

Imagine two arrows pointing from the center of a circle:

```
         Site A (summer peak)
              ↑
              │
    Site B ───┼──→ (stable year-round)
              │
```

- **Similar direction** → similar consumption pattern (both peak in summer)
- **Opposite direction** → opposite patterns
- **Formula**: `cosine_similarity(A, B) = (A·B) / (|A|×|B|)`

Result is always between -1 and 1:
- **1.0** → identical patterns (same monthly proportions)
- **0.0** → no relationship
- **-1.0** → opposite patterns (peak when the other troughs)

## Why 12 Dimensions?

Each month is one dimension. We could use:
- **1 dimension** — total annual kWh (loses all pattern info)
- **4 dimensions** — quarterly consumption (rough pattern)
- **12 dimensions** — monthly consumption (good balance of detail and performance)
- **365 dimensions** — daily consumption (too sparse, slow)

**12 is the sweet spot**: captures seasonal patterns without being too sparse for similarity search.

## The pgvector Extension

pgvector adds vector operations directly inside PostgreSQL:

```sql
-- Store a vector
INSERT INTO consumption_vectors (site_id, year, vector)
VALUES (1234, 2025, '[4500,4200,4800,5100,5300,5500,5800,5600,5200,4900,4600,4400]'::vector);

-- Find the 10 most similar sites to a query pattern
SELECT site_id, total_consumption, 
       1 - (vector <=> '[5000,4800,5000,...]'::vector) AS similarity
FROM consumption_vectors
WHERE year = 2025
ORDER BY vector <=> '[5000,4800,5000,...]'::vector
LIMIT 10;
```

`<=>` is the **cosine distance operator**. `1 - distance` gives us similarity.

The **HNSW index** (Hierarchical Navigable Small World) makes this fast — instead of scanning all 19,000+ vectors, it navigates a graph structure to find nearest neighbors in milliseconds.

---

# 4. System Components

## Component Map

```
┌─────────────────────────────────────────────────────────────────────┐
│  FastAPI (port 5000)                                                │
│  ├── api/main.py            ← App creation, CORS, lifespan          │
│  ├── api/routers/                                                    │
│  │   ├── health.py          ← GET /health                           │
│  │   ├── reports.py         ← POST/GET budget forecast (async jobs) │
│  │   ├── analytics.py       ← GET current-year, yoy, clusters       │
│  │   └── ingestion.py       ← POST upload XLS for new sites         │
│  ├── llm/                                                           │
│  │   ├── chain.py            ← Main orchestrator                    │
│  │   ├── ollama_client.py    ← HTTP calls to Ollama                 │
│  │   └── parsers.py          ← Parse + validate LLM output          │
│  ├── rag/                                                            │
│  │   ├── embeddings.py       ← Build 12-dim vectors from DB         │
│  │   ├── retriever.py        ← Find similar sites (RAG)             │
│  │   ├── indexer.py          ← Rebuild vector index                 │
│  │   └── prompt_templates.py ← Construct system/user prompts        │
│  ├── ml/                                                             │
│  │   ├── features.py         ← Feature engineering (lags, rolling)  │
│  │   ├── config.py           ← XGBoost hyperparams                  │
│  │   └── forecasting/                                                │
│  │       ├── xgboost_model.py ← Train, load, predict                │
│  │       ├── prophet_model.py ← Alternative Prophet model           │
│  │       └── trainer.py       ← Training pipeline                   │
│  ├── data/                                                           │
│  │   ├── db.py               ← Async SQLAlchemy engine              │
│  │   ├── vector_store.py     ← pgvector CRUD operations             │
│  │   └── extractors/                                                 │
│  │       ├── consumption.py   ← Invoice-based consumption queries   │
│  │       ├── invoices.py      ← Billing summaries                   │
│  │       ├── visits.py        ← Visit compliance queries            │
│  │       ├── sites.py         ← Site metadata queries               │
│  │       └── billing.py       ← Tariff + budget calculation         │
│  ├── report/                                                         │
│  │   ├── generator.py         ← JSON + PDF + Excel orchestration    │
│  │   ├── puppeteer_renderer.py ← HTML → PDF via Pyppeteer           │
│  │   ├── excel_exporter.py     ← openpyxl Excel builder             │
│  │   └── templates/            ← Jinja2 HTML templates              │
│  └── config/                                                         │
│      └── settings.py           ← All env vars, DB URLs, etc.        │
├──────────────────────────────────────────────────────────────────────┤
│  NestJS Proxy (port 3000)                                            │
│  └── src/ai/                                                         │
│      ├── ai.module.ts         ← Module registration                 │
│      ├── ai.controller.ts     ← POST/GET proxy routes               │
│      ├── ai.service.ts        ← HTTP proxy to FastAPI               │
│      └── dto/                  ← TypeScript DTOs                    │
├──────────────────────────────────────────────────────────────────────┤
│  Ollama (port 11434)                                                 │
│  └── Model: qwen2.5:3b                                               │
├──────────────────────────────────────────────────────────────────────┤
│  PostgreSQL 17 + pgvector 0.7.4 (port 5432, Docker)                 │
│  └── Tables: invoice_items, sites, tariff_config, consumption_vectors, ... │
└──────────────────────────────────────────────────────────────────────┘
```

## Tech Stack Summary

| Component | Technology | Why? |
|-----------|-----------|------|
| **Backend framework** | FastAPI (Python) | Async, Pydantic validation, auto-docs |
| **API proxy** | NestJS (TypeScript) | Already existing backend ecosystem |
| **Database** | PostgreSQL 17 | Already in use for EGRS |
| **Vector search** | pgvector 0.7.4 | Extension inside PG, no separate DB |
| **ML** | XGBoost | Best for tabular/time-series forecasting |
| **LLM** | Qwen2.5:3b via Ollama | Local, free, private |
| **PDF** | Pyppeteer (headless Chromium) | Pixel-perfect HTML→PDF |
| **Excel** | openpyxl | Read/write .xlsx files |
| **Templates** | Jinja2 | Python native, loops/filters |

---

# 5. The Complete Pipeline — Step by Step

When a user submits a budget forecast request, this is the full journey:

## Step 1: Submit Request

```
POST /api/v1/reports/budget-forecast
```

```json
{
  "target_year": 2027,
  "new_sites": [
    {
      "configuration": "Terminal",
      "network_type": "4G",
      "electrical_type": "BT",
      "direction_id": 1,
      "estimated_consumption": 50000,
      "site_count": 5
    }
  ],
  "user_prompt": "Focus on the Southern region impact"
}
```

File: `api/routers/reports.py`

## Step 2: Create Async Job

```python
job_id = str(uuid.uuid4())
_jobs[job_id] = {"status": "pending", "progress": 0}
asyncio.create_task(_run_forecast_job(job_id, request, session))
return {"job_id": job_id, "status": "pending", "message": "..."}
```

The request is **async** because:
- XGBoost prediction takes ~5 seconds
- LLM call takes ~30-120 seconds
- PDF rendering takes ~3 seconds
- Total: up to 2 minutes

Instead of blocking the HTTP request, we:
1. Create a job ID
2. Start processing in background
3. Return immediately
4. User polls `GET /reports/{job_id}` until status = "completed"

## Step 3: Extract Historical Data

```python
historical_data = await get_monthly_consumption_from_invoices(
    session, end_year=target_year - 1
)
```

File: `data/extractors/consumption.py`

**The SQL query** runs:

```sql
SELECT
    ii.site_id,
    s."SiteCode", s."SiteName", s."Configuration",
    s."ElecType", s."NetworkTypeId", s."DirectionId",
    EXTRACT(YEAR FROM ii.item_date)::int AS year,
    EXTRACT(MONTH FROM ii.item_date)::int AS month,
    -- THE KEY COMPUTATION:
    ((ii.final_sale - COALESCE(ii.tva, 0)) / 1000.0) /
      CASE WHEN s."ElecType" = 'BT' THEN tc.kwh_price_bt
           ELSE tc.kwh_price_mt END AS total_consumption_kwh,
    ii.final_sale,
    tc.kwh_price_bt, tc.kwh_price_mt, tc.tax_rate
FROM invoice_items ii
JOIN sites s ON s."SiteId" = ii.site_id
LEFT JOIN tariff_config tc ON tc.id = 1
WHERE EXTRACT(YEAR FROM ii.item_date) <= 2026
ORDER BY ii.site_id, ii.item_date
```

**What the formula does**:

```
final_sale = total invoice amount in millimes (1/1000 TND)
tva        = VAT amount in millimes
           ↓
HT = final_sale - tva    ← amount before tax, in millimes
HT_TND = HT / 1000       ← convert to Tunisian Dinars
           ↓
kWh = HT_TND / kwh_price ← divide by tariff rate
     = ((final_sale - tva) / 1000) / 0.396 (for BT)
                                   / 0.414 (for MT)
```

**Result**: ~149,000 rows of monthly per-site consumption data.

## Step 4: Feature Engineering

```python
df = engineer_features(df)
```

File: `ml/features.py`

Raw data becomes ML-ready features:

```
Original: site_id | year | month | total_consumption_kwh
                                                    ↓
Engineered: site_id | year | month | total_consumption_kwh |
            quarter | month_sin | month_cos |           ← cyclical encoding
            lag_1 | lag_2 | lag_3 | lag_12 |             ← previous months
            rolling_mean_3 | rolling_std_3 |              ← moving averages
            rolling_max_6 | is_bt | yoy_change            ← trend indicators
```

### Why these features?

| Feature | Purpose | Example |
|---------|---------|---------|
| `lag_1` | Last month's consumption (autoregressive) | If June was 5000 kWh, July is likely similar |
| `lag_12` | Same month last year (seasonal) | July last year was 5500 kWh, so this July ≈ 5500 |
| `month_sin/cos` | Time of year (cyclical) | Jan=0°, Dec=330° — model learns summer peaks |
| `rolling_mean_3` | Short-term trend | Last 3 months average |
| `yoy_change` | Year-over-year growth rate | Is consumption rising or falling? |

### Cyclical Encoding Explained

Months are circular (Dec → Jan is a small step, not a big one):
```
Bad: month = 12  →  month = 1   (model thinks "big jump")
Good: month_sin(Dec) ≈ 0  →  month_sin(Jan) ≈ 0.5
      month_cos(Dec) ≈ 1  →  month_cos(Jan) ≈ 0.87
```
The model can now understand that December and January are close together.

## Step 5: RAG — Find Similar Sites (if new sites provided)

```python
for site_input in new_sites:
    query_vec = build_query_vector_from_input(site_input)     # Step 5a
    similar = await retrieve_similar_sites(session, query_vec) # Step 5b
    site_input["similar_sites"] = similar
```

File: `rag/retriever.py` → `data/vector_store.py`

### Step 5a: Build Query Vector

```python
def build_query_vector_from_input(site_input):
    estimated = site_input.get("estimated_consumption", 5000)  # annual kWh
    # Simple: divide equally across 12 months
    monthly = estimated / 12
    return [monthly] * 12
```

If the user says "estimated 50,000 kWh/year", we get:
```
[4167, 4167, 4167, 4167, 4167, 4167, 4167, 4167, 4167, 4167, 4167, 4167]
```

### Step 5b: Vector Similarity Search

```sql
SELECT cv.site_id, cv.total_consumption,
       s."SiteName", s."Configuration", s."ElecType",
       1 - (cv.vector <=> :query_vec::vector) AS similarity
FROM consumption_vectors cv
JOIN sites s ON s."SiteId" = cv.site_id
WHERE cv.vector IS NOT NULL
  AND cv.year IN (2024, 2025, 2026)
ORDER BY cv.vector <=> :query_vec::vector
LIMIT 10
```

The cosine distance `<=>` finds the 10 historical sites with the most similar consumption patterns. Their data is used as "real-world examples" for the LLM.

**Why not just use XGBoost for new sites?**  
XGBoost needs historical data for each site. New sites have zero history. RAG finds similar historical sites and says, "these 10 sites were built similarly — their consumption pattern was X, so expect something similar."

## Step 6: XGBoost Prediction

```python
model, features = load_model()  # Load from pickle file
forecast_df = df[df["year"] == target_year - 1].copy()
forecast_df["year"] = target_year  # Shift year forward
predictions = predict_consumption(model, features, forecast_df)
```

File: `ml/forecasting/xgboost_model.py`

### What is XGBoost?

**XGBoost** (eXtreme Gradient Boosting) is a decision-tree ensemble algorithm. It builds hundreds of small decision trees, each one correcting the errors of the previous ones.

```
Tree 1: "If month=Jul and lag_1 > 5000 → predict 5500"
         Error: predicted 5500, actual was 5700 (error = +200)
                        ↓
Tree 2: "If month=Jul and lag_1 > 5000 → adjust +200"
         Tree 1 predicted 5500, Tree 2 adds +200 → 5700 ✓
                        ↓
Tree 3: ... (refines further)
```

**300 trees** are combined for the final prediction.

### How Prediction Works for Next Year

We take the **last year's data** (2026), shift the year to 2027, and run the model:

```
site_id=1234, month=7, lag_1=5200 (June 2026), lag_12=5000 (July 2025)
                            ↓
Model predicts: July 2027 consumption = 5,423 kWh
```

The features (`lag_1`, `lag_12`, etc.) are computed from 2026 data, but the prediction is for 2027. This works because:
- `lag_1` (June 2026) is known → predicts July 2027 using June 2026
- `lag_12` (July 2025) is known → captures seasonal pattern

### Model Training

The model was trained on **149,000 invoice rows** from 2012-2026:

```python
raw_data = await get_monthly_consumption_from_invoices(session)
df = pd.DataFrame(raw_data)
df = engineer_features(df, target_col="total_consumption_kwh")
df["target"] = df["total_consumption_kwh"]

model = xgb.XGBRegressor(
    n_estimators=300,     # 300 trees
    max_depth=6,           # Each tree max 6 levels deep
    learning_rate=0.05,    # How much each tree contributes
    subsample=0.8,         # Use 80% of data per tree (prevents overfitting)
    colsample_bytree=0.8,  # Use 80% of features per tree
)
model.fit(X, y)
```

After training, the model is saved to `ml/forecasting/models/consumption_xgboost.pkl` (a pickle file containing the trained model + feature list).

## Step 7: Get Current Year Billing

```python
current_year_billing = await get_yearly_billing_summary(session, target_year - 1)
```

File: `data/extractors/invoices.py`

This returns aggregated billing data:

```json
[
  {
    "direction_id": 1, "direction_name": "Nord",
    "elec_type": "BT", "site_count": 150,
    "total_final_sale_tnd": 1250000.00,
    "total_consumption_kwh": 3150000,
    "avg_cost_per_site": 8333.33
  },
  ...
]
```

## Step 8: Assemble the Prompt

```python
system_prompt, user_content = get_report_prompt(
    report_type="budget_forecast",
    historical_summary={...},
    predictions={"total_predicted_kwh": 42500000, "new_sites_contribution": [...]},
    billing_summary=[...],
    new_sites_input=[...],
    user_prompt="Focus on the Southern region impact",
)
```

File: `rag/prompt_templates.py`

### What the LLM Actually Sees

**System Prompt** (invisible to user, sets the role):

```
You are an AI budget analyst for Orange Tunisie's Energy Management System (EGRS).
Your role is to analyze energy consumption data, forecast budgets, and provide
actionable recommendations.

You MUST:
- Only use the numerical data provided
- Never invent numbers or make unsupported claims
- Output ONLY valid JSON matching the specified schema
- All monetary values in Tunisian Dinar (TND)
- All energy values in kilowatt-hours (kWh)
```

**User Prompt** (contains the actual data):

```
## Report Type: Budget Forecast

## Historical Data Summary
- Total sites in database: 850
- Total historical consumption: 45,200,000 kWh
- Years of data available: 2012, 2013, ..., 2026

## Forecast Predictions (from XGBoost)
- Predicted consumption for next year: 42,500,000 kWh

## Current Year Billing by Direction
- Direction Nord (BT): 1,250,000.00 TND for 3,150,000 kWh
- Direction Centre (BT): 987,000.00 TND for 2,100,000 kWh
...

## New Site Specifications
  1. Configuration: Terminal, Network: 4G, ElecType: BT,
     Direction: 1, Est. Consumption: 50,000 kWh
     Similar sites found: 10 (avg consumption: 48,200 kWh)

## User's Specific Request
Focus on the Southern region impact
```

## Step 9: Call the LLM

```python
llm_output = await generate_structured_report(
    system_prompt=system_prompt,
    user_prompt=user_content,
    json_schema=schema,
)
```

File: `llm/ollama_client.py`

This sends an HTTP POST to `http://localhost:11434/api/generate`:

```json
{
  "model": "qwen2.5:3b",
  "system": "You are an AI budget analyst...",
  "prompt": "## Report Type: Budget Forecast...",
  "stream": false,
  "format": {  ← JSON Schema for constrained decoding
    "type": "object",
    "properties": {
      "executive_summary": {"type": "string"},
      "consumption_forecast": {
        "type": "object",
        "properties": {
          "total_predicted_kwh": {"type": "number"},
          "monthly_breakdown": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "month": {"type": "integer"},
                "predicted_kwh": {"type": "number"},
                "predicted_cost_tnd": {"type": "number"}
              }
            }
          },
          "confidence_level": {"type": "string"}
        }
      },
      "budget_breakdown": {...},
      "investment_impact": {...},
      "recommendations": {"type": "array", "items": {"type": "string"}}
    }
  },
  "options": {
    "temperature": 0.1,
    "top_p": 0.9,
    "num_predict": 4096
  }
}
```

The LLM processes ~30 seconds and returns:

```json
{
  "executive_summary": "Based on historical data from 850 sites...",
  "consumption_forecast": {
    "total_predicted_kwh": 42500000,
    "monthly_breakdown": [
      {"month": 1, "predicted_kwh": 3200000, "predicted_cost_tnd": 1267200},
      ...
    ],
    "confidence_level": "Moderate (based on 3 years of similar growth pattern)"
  },
  "budget_breakdown": {
    "total_budget_tnd": 16830000,
    "by_direction": [...],
    "by_elec_type": {"BT": 0.65, "MT": 0.35}
  },
  "investment_impact": {
    "new_sites_count": 5,
    "additional_consumption_kwh": 241000,
    "additional_cost_tnd": 95436
  },
  "recommendations": [
    "Consider seasonal variation monitoring for new sites...",
    "The Southern region may require additional budget allocation..."
  ]
}
```

## Step 10: Parse & Validate Output

```python
result = parse_report_output(llm_output)
```

File: `llm/parsers.py`

Checks:
1. LLM returned valid JSON → `status: "success"`
2. Has all required fields → `executive_summary`, `consumption_forecast`, `recommendations`
3. Numbers make sense → `total_predicted_kwh > 0`

If the LLM hallucinates or returns bad JSON, it's caught here and returned as `status: "error"` rather than crashing.

## Step 11: Generate Report Files

```python
report_files = await generate_report_files(
    report_type="budget_forecast",
    data=chain_result,
)
```

File: `report/generator.py`

Three files are created:

### 11a. JSON file
Raw data saved to `reports/storage/{uuid}.json` — for API consumption.

### 11b. PDF file
1. Jinja2 renders `budget_forecast.html` with the data → HTML string
2. Pyppeteer launches headless Chromium
3. Loads HTML, waits for fonts/images to load
4. Generates A4 PDF with margins
5. Saves to `reports/storage/{uuid}.pdf`

### 11c. Excel file
openpyxl creates a workbook with 3 sheets:
- **Executive Summary** — key metrics row
- **Monthly Forecast** — month-by-month breakdown
- **Recommendations** — LLM-generated text list

## Step 12: Return Response

```python
_jobs[job_id] = {
    "status": "completed",
    "progress": 100,
    "result": {
        "data": chain_result,       # The LLM output
        "report_id": "...",
        "json_url": "/reports/storage/....json",
        "pdf_url": "/reports/storage/....pdf",
        "excel_url": "/reports/storage/....xlsx",
        "expires_at": "2026-06-01T..."
    }
}
```

The frontend polls `GET /reports/{job_id}` and renders the data.

---

# 6. Deep Dive: Data Layer

## Database: PostgreSQL 17 + pgvector 0.7.4

**Location**: Docker container `postgres_db:5432`  
**Database name**: `E-GRS_DB`  
**User**: `orange_user`  
**pgvector version**: 0.7.4 (built from source for PostgreSQL 17 compatibility)

### Why Docker?

- Isolates PostgreSQL from Windows services
- Consistent environment across machines
- Easy to restart/reset: `docker compose down && docker compose up`

### Why pgvector built from source?

On Alpine Linux in Docker, `apk add postgresql-pgvector` installs a package targeting PostgreSQL 18. Our container runs PostgreSQL 17, which causes an ABI mismatch. Building from source (`make && make install`) inside the container ensures the correct version.

## Tables Used

### 1. `invoice_items` — Primary Data Source

| Column | Type | Description | Used For |
|--------|------|-------------|----------|
| `site_id` | bigint | FK to sites | Grouping |
| `item_date` | timestamp | Invoice date | Year/month extraction |
| `final_sale` | numeric | Total amount (millimes) | **Derived kWh** |
| `tva` | numeric | VAT amount (millimes) | **Derived kWh** (subtracted) |
| `consumption_amount` | numeric | Raw meter value | **NOT USED anymore** |
| `consumption_kwh` | numeric | Direct meter reading | **NOT USED** |
| `item_id` | bigint | PK | Unused |
| `description` | text | Invoice description | Unused |

**Rows**: ~149,000  
**Years**: 2012–2026

### 2. `sites` — Site Metadata

| Column | Type | Description |
|--------|------|-------------|
| `"SiteId"` | integer | PK |
| `"SiteCode"` | text | E.g., "TUN-001" |
| `"SiteName"` | text | Human-readable name |
| `"Configuration"` | text | "Terminal", "Nodal", "Agreg" |
| `"ElecType"` | text | "BT" (Basse Tension) or "MT" (Moyenne Tension) |
| `"NetworkTypeId"` | integer | 2G/3G/4G/5G identifier |
| `"DirectionId"` | integer | Region ID (1=Nord, 2=Centre, 3=Sud) |
| `"IsSharing"` | boolean | Site shared with other operators |
| `"deletedAt"` | timestamp | Soft delete |

### 3. `tariff_config` — Pricing Rules

| Column | Value | Description |
|--------|-------|-------------|
| `kwh_price_bt` | **0.396 TND** | Price per kWh for BT sites |
| `kwh_price_mt` | **0.414 TND** | Price per kWh for MT sites |
| `tax_rate` | **0.19** (19%) | VAT rate |
| `fixed_service_fee` | 0.000 TND | Fixed monthly fee |

**Only 1 row** — the tariff is the same for all sites.

### 4. `consumption_vectors` — Vector Index

| Column | Type | Description |
|--------|------|-------------|
| `site_id` | integer | FK to sites |
| `year` | integer | Year |
| `vector` | vector(12) | 12-dim monthly consumption |
| `total_consumption` | float | Annual total |
| `site_configuration` | text | Denormalized from sites |
| `network_type_id` | integer | Denormalized from sites |
| `electrical_type` | text | Denormalized from sites |
| `direction_id` | integer | Denormalized from sites |

**Index**: HNSW on `vector` using cosine distance (`vector_cosine_ops`)  
**Rows**: ~19,500 (one per site per year)

The denormalized columns (`site_configuration`, `network_type_id`, etc.) are stored alongside the vector so that RAG results don't need extra joins — they're ready to inject into the prompt immediately.

### 5. `visits` — Site Visit Tracking

| Column | Description |
|--------|-------------|
| `"siteId"` | Site visited |
| `"visitDate"` | When the visit happened |
| `status` | 'COMPLETED' or other |
| `"technicianId"` | FK to users |

### 6. `visit_measurements` — Meter Readings

| Column | Description |
|--------|-------------|
| `"visitId"` | FK to visits |
| `consumption` | kWh reading from meter |
| `"meterIndex"`, `"previousIndex"` | Meter indices |

### 7–10. Auxiliary Tables

| Table | Purpose |
|-------|---------|
| `users` | Technician names (first_name + last_name) |
| `shared_operators` | Bridge: shared sites → operators |
| `operators` | Operator company names |
| `directions` | Region names (Nord, Centre, Sud) |

## The Key Connection

```
invoice_items.final_sale - tva ──→ kWh (derived)
                                           │
                              ↓            ↓
                         XGBoost      pgvector (RAG)
                         (predict     (find similar
                          numbers)     patterns)
                              │            │
                              └─────┬──────┘
                                    ↓
                               LLM prompt
                                    │
                                    ↓
                              JSON Report
                              + PDF + Excel
```

---

# 7. Deep Dive: ML Layer (XGBoost)

## What is XGBoost?

XGBoost stands for **eXtreme Gradient Boosting**. It's a machine learning algorithm that:

1. Starts with a simple prediction (e.g., "all months: 5000 kWh")
2. Measures errors (actual - predicted = residual)
3. Builds a decision tree to predict the errors
4. Adds the tree's predictions to correct the original
5. Repeats steps 2-4 for 300 iterations
6. Final result = sum of all trees

```
Iteration 1:  prediction = 5000      error = +200
Iteration 2:  correction = +180      remaining error = +20
Iteration 3:  correction = +15       remaining error = +5
...
Iteration 300: prediction = 5000 + 180 + 15 + ... = 5423 ✓
```

## Why XGBoost Over Deep Learning?

| Factor | XGBoost | Neural Network |
|--------|---------|---------------|
| **Data size** | Works with 100K rows | Needs millions |
| **Training time** | Minutes | Hours/days |
| **Interpretability** | Feature importance scores | Black box |
| **Tabular data** | Best in class | Worse than XGBoost |
| **Time series** | Good with lag features | Better with sequences |

**Winner for our use case**: XGBoost. Our data is tabular (site_id, month, features), not sequential text/images.

## Feature Importance

After training, XGBoost can tell us which features matter most:

```
Feature Importance (fictional example):
lag_12           : 35%  ← same month last year is most important
lag_1            : 20%  ← last month
month_sin/cos    : 15%  ← time of year
rolling_mean_3   : 12%  ← short-term trend
yoy_change       : 10%  ← growth rate
is_bt            :  5%  ← BT vs MT
quarter          :  3%  ← quarter of year
```

This tells us: **seasonal patterns (lag_12 + month) dominate**. The model primarily learns "same time last year" + "recent trend".

## Model File

The trained model is saved to `ml/forecasting/models/consumption_xgboost.pkl`:

```
consumption_xgboost.pkl
├── "model"    → xgb.XGBRegressor (300 trees, max_depth=6)
└── "features" → ["month", "quarter", "month_sin", "month_cos",
                   "lag_1", "lag_2", "lag_3", "lag_12",
                   "rolling_mean_3", "rolling_std_3", "rolling_max_6",
                   "is_bt", "yoy_change"]
```

The `features` list is critical — it ensures that when we predict, we use exactly the same columns in exactly the same order as training.

---

# 8. Deep Dive: RAG Layer (pgvector)

## The Two-Stage Embedding Process

### Stage 1: Build Embeddings (One-time, via seed script)

```
python -m scripts.seed_vector_index
```

For each site + year combination:
1. Fetch 12 monthly consumption values from `invoice_items`
2. Package them as `[jan, feb, mar, ..., dec]` — a 12-dim vector
3. Store in `consumption_vectors` table

```python
# rag/embeddings.py
month_map = {
    row["month"]: row["total_consumption_kwh"] or 0
    for row in monthly_data
    if row["site_id"] == site_id and row["year"] == year
}
vector = [float(month_map.get(m, 0)) for m in range(1, 13)]
```

### Stage 2: Search (Every query)

When a user submits new sites:
1. Build a query vector from the estimated consumption
2. `SELECT ... ORDER BY vector <=> query_vector LIMIT 10`
3. Return the 10 most similar sites with their metadata

## Why RAG Instead of Just Asking the LLM?

Without RAG:
```
USER: "Forecast for a new Terminal site in the North region"
LLM: "I think it will consume about 50,000 kWh per year" ← GUESSING
```

With RAG:
```
RETRIEVED: "Site 1234 (Terminal, Nord): 47,200 kWh/year"
           "Site 5678 (Terminal, Nord): 51,300 kWh/year"
           "Site 9012 (Terminal, Nord): 49,100 kWh/year"
USER: "Forecast for a new Terminal site in the North region"
LLM: "Based on similar sites (47K-51K kWh/year), expect ~49,000 kWh" ← EVIDENCE-BASED
```

## The HNSW Index

Without an index, searching 19,500 vectors requires computing cosine distance 19,500×. This is fast in memory (milliseconds) but slow on disk.

**HNSW** (Hierarchical Navigable Small World) creates a multi-level graph:

```
Level 3:   A ─── B ─── C      (few nodes, long jumps)
              ↙   ↓   ↘
Level 2:   A ─── B ─── C ─── D  (medium granularity)
               ↙   ↓   ↓    ↘
Level 1:   A ─ B ─ C ─ D ─ E ─ F  (full dataset)
```

Search starts at the top level (coarse) and descends to finer levels, touching only ~200 vectors out of 19,500 — **100× faster**.

---

# 9. Deep Dive: LLM Layer (Ollama + Qwen)

## Ollama — The LLM Server

Ollama is a lightweight server that:
- Manages model downloads: `ollama pull qwen2.5:3b`
- Runs the model with efficient inference (quantized 4-bit)
- Exposes a REST API at `http://localhost:11434`
- Supports OpenAI-compatible endpoints

**API calls we use**:
```
POST /api/generate       ← Generate text (main endpoint)
GET  /api/tags           ← List available models (health check)
```

## Qwen2.5:3b — The Model

Qwen2.5 is a family of models by Alibaba Cloud:
- **3b** = 3 billion parameters (our choice)
- **7b** = 7 billion parameters (better quality, slower)
- **14b** = 14 billion parameters
- **72b** = 72 billion parameters

### Why 3b?

| Size | RAM Needed | Quality | Speed | Use Case |
|------|-----------|---------|-------|----------|
| 3b | 4 GB | Good enough | Fast | Dev + structured tasks |
| 7b | 8 GB | Better | Moderate | Production |
| 14b+ | 16+ GB | Best | Slow | Overkill for this |

For development, 3b is sufficient. For production with more complex reports, upgrade to 7b.

## How Ollama Generates Text

```
Input prompt → Tokenize → Neural Network Inference → Detokenize → Output

1. "Forecast budget..." → [4512, 8901, 3321, ...]  (text → token IDs)
2. Run through 3 billion parameters (matrix multiplications)
3. Get probability for every possible next token (vocabulary of ~150K tokens)
4. Pick the most likely one (temperature 0.1 = very greedy)
5. Append to input, repeat until max tokens or stop sequence
```

## The Format Parameter (Constrained Decoding)

Ollama supports **grammar-based sampling** via the `format` parameter:

```python
payload["format"] = json_schema
```

Ollama converts the JSON schema to a grammar that constrains which tokens can be generated at each position:
- If the schema says `"total_predicted_kwh": {"type": "number"}`, Ollama only generates numeric characters at that position
- If the schema says `"status": {"enum": ["success", "error"]}`, Ollama only generates `"success"` or `"error"`

This guarantees valid JSON output — no parsing errors from malformed LLM responses.

---

# 10. Deep Dive: Report Generation

## The Three Outputs

### 10a. JSON (`{report_id}.json`)
Raw structured data, same format as the LLM output. Used by the NestJS backend and frontend for programmatic access.

### 10b. PDF (`{report_id}.pdf`)

Generation pipeline:
```
LLM JSON output
       ↓
Jinja2 Template ← renders HTML with the data
       ↓
HTML String
       ↓
Pyppeteer ← launches headless Chromium
       ↓
page.setContent(html) ← loads HTML
       ↓
page.pdf() ← generates A4 PDF
       ↓
PDF file saved to disk
```

**Why Pyppeteer instead of wkhtmltopdf or ReportLab?**
- Pyppeteer uses real Chromium → 100% CSS fidelity
- Jinja2 templates are easy to maintain
- Same HTML can be previewed in a browser
- Supports modern CSS (flexbox, grid, @media print)

**Chromium path** is configured in `.env`:
```
CHROMIUM_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe
```

Pyppeteer can auto-download its own Chromium, but using the existing system Chrome saves space and avoids download issues.

### 10c. Excel (`{report_id}.xlsx`)

openpyxl creates a workbook with styled sheets:

```
┌──────────────────────────────────────┐
│ EGRS AI Budget Report                │
├──────────────────────────────────────┤
│ Metric                │ Value        │
├───────────────────────┼──────────────┤
│ Total Predicted (kWh) │ 42,500,000   │
│ Total Budget (TND)    │ 16,830,000   │
│ New Sites             │ 5            │
│ Additional Cost (TND) │ 95,436       │
└──────────────────────────────────────┘

Sheet 2: Monthly Forecast
┌───────┬─────────────┬────────────────┐
│ Month │ Pred kWh    │ Pred Cost TND  │
├───────┼─────────────┼────────────────┤
│ Jan   │ 3,200,000   │ 1,267,200      │
│ Feb   │ 3,100,000   │ 1,227,600      │
│ ...   │ ...         │ ...            │
└───────┴─────────────┴────────────────┘

Sheet 3: Recommendations
┌──────────────────────────────────────┐
│ Recommendations                      │
├──────────────────────────────────────┤
│ Consider seasonal variation...       │
│ Southern region may need...          │
└──────────────────────────────────────┘
```

## Report Storage

All reports (JSON, PDF, Excel) are stored at `reports/storage/` with a 7-day TTL (`report_ttl_days = 7`). The `expires_at` field in the response tells the frontend when to delete cached links.

---

# 11. Deep Dive: API Layer (FastAPI)

## Application Structure

```python
# api/main.py
app = FastAPI(title="EGRS AI Service", version="1.0.0")

@app.on_event("startup")
async def startup():
    await init_db(settings)     # Connect to PostgreSQL

app.include_router(health_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(ingestion_router, prefix="/api/v1")
```

## Endpoints Reference

### Health
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | DB + Ollama status |

### Reports (async job pattern)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/reports/budget-forecast` | Start report generation |
| GET | `/api/v1/reports/{job_id}` | Poll job status |

### Analytics (synchronous)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/analytics/current-year?year=2026` | Billing + compliance + tech perf |
| GET | `/api/v1/analytics/year-over-year?years=2025,2026` | Multi-year billing comparison |
| GET | `/api/v1/analytics/site-clusters?year=2026` | Vector similarity clusters |

### Ingestion
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/ingest/new-sites` | Upload XLS/CSV of new site specs |

## Async Job Pattern Explained

```
Client                    FastAPI                    LLM Chain
  │                         │                          │
  │ POST /reports           │                          │
  │────────────────────────>│                          │
  │                         │  Create job_id            │
  │                         │  Spawn background task    │
  │ {job_id, "pending"}     │                          │
  │<────────────────────────│                          │
  │                         │                          │
  │ GET /reports/{id}       │     [LLM running...]      │
  │────────────────────────>│                          │
  │ {"status":"running",    │                          │
  │  "progress":10}         │                          │
  │<────────────────────────│                          │
  │                         │                          │
  │ GET /reports/{id}       │     [LLM done,           │
  │────────────────────────>│      generating PDF...]   │
  │ {"status":"running",    │                          │
  │  "progress":60}         │                          │
  │<────────────────────────│                          │
  │                         │                          │
  │ GET /reports/{id}       │     [Done]                │
  │────────────────────────>│                          │
  │ {"status":"completed",  │                          │
  │  "progress":100,        │                          │
  │  "result":{...}}        │                          │
  │<────────────────────────│                          │
```

**Why not WebSockets?** WebSockets add complexity (connection management, reconnection logic). Polling is simpler and reliable enough for reports that take 1-2 minutes.

## NestJS Proxy

The NestJS backend (`src/ai/`) proxies requests from the frontend:

```
Frontend → /ai/reports/budget-forecast
    ↓
NestJS → http://localhost:5000/api/v1/reports/budget-forecast
    ↓
FastAPI → processes request
    ↓
Response → NestJS → Frontend
```

This keeps the frontend URL consistent (`/ai/*`) while the AI service can move to a different port or server without frontend changes.

---

# 12. Walkthrough — Real Scenario

## Scenario: "Forecast 2027 Budget for 5 New 4G Sites in the South"

### Step 1: Upload Site Specs

The user uploads an Excel file with:

| Configuration | Network | ElecType | Direction | Est. kWh | Count |
|--------------|---------|----------|-----------|----------|-------|
| Terminal | 4G | BT | 3 (Sud) | 50,000 | 5 |

```
POST /api/v1/ingest/new-sites
```

Returns:
```json
{
  "status": "parsed",
  "total_rows": 1,
  "sites": [{"configuration": "Terminal", "network_type": "4G", ...}],
  "message": "Use POST /reports/budget-forecast with this data"
}
```

### Step 2: Generate Report

```json
POST /api/v1/reports/budget-forecast
{
  "target_year": 2027,
  "new_sites": [
    {
      "configuration": "Terminal",
      "network_type": "4G", 
      "electrical_type": "BT",
      "direction_id": 3,
      "estimated_consumption": 50000,
      "site_count": 5
    }
  ]
}
```

Returns: `{"job_id": "abc-123", "status": "pending"}`

### Step 3: What Happens Internally

**Data Extraction** (~2 seconds):
- SQL reads 149K invoice rows
- Computes kWh per row: `((final_sale - tva) / 1000) / kwh_price`
- Returns DataFrame with 149K rows

**Feature Engineering** (~1 second):
- Creates lags, rolling averages, cyclical month encoding
- DataFrame now has 15+ columns

**RAG Search** (~500ms):
- Builds query vector for `[4167] * 12` (50,000 / 12)
- pgvector finds 10 most similar sites from Direction 3 (Sud)
- Result: similar sites consume 42,000–55,000 kWh/year

**XGBoost Prediction** (~5 seconds):
- Loads model from pickle
- Takes 2026 data, shifts to 2027
- Predicts per-site per-month consumption
- Aggregates to: total_predicted_kwh = 42,500,000 (all existing sites) + 241,000 (5 new sites)

**Billing Summary** (~1 second):
- Groups current year billing by direction and BT/MT
- Direction 3 (Sud) BT: 2,500,000 TND for 6,200,000 kWh

**LLM Call** (~30–60 seconds):
- Assembled prompt: ~2000 tokens (system + user data)
- Ollama processes Qwen2.5:3b
- Returns structured JSON

**Report Generation** (~3 seconds):
- JSON file saved
- Jinja2 renders HTML → Pyppeteer generates PDF
- openpyxl creates Excel

**Total**: ~45–75 seconds

### Step 4: Poll for Result

```json
GET /reports/abc-123

{
  "status": "completed",
  "progress": 100,
  "result": {
    "data": {
      "executive_summary": "For 2027, EGRS is projected to consume 42,741,000 kWh at a cost of 16,925,436 TND, including 241,000 kWh from 5 new sites.",
      "consumption_forecast": {
        "total_predicted_kwh": 42741000,
        "monthly_breakdown": [
          {"month": 1, "predicted_kwh": 3350000},
          {"month": 2, "predicted_kwh": 3100000},
          ...
        ]
      },
      "budget_breakdown": {
        "total_budget_tnd": 16925436,
        "by_direction": [
          {"direction": "Nord", "total_tnd": 8250000},
          {"direction": "Centre", "total_tnd": 5200000},
          {"direction": "Sud", "total_tnd": 3475436}
        ]
      },
      "investment_impact": {
        "new_sites_count": 5,
        "additional_consumption_kwh": 241000,
        "additional_cost_tnd": 95436
      },
      "recommendations": [
        "The 5 new Terminal sites in the Southern region are expected to add 241,000 kWh/year at 95,436 TND.",
        "Recommend installing smart meters for real-time monitoring of new sites.",
        "Consider solar panels for Southern sites given high solar irradiance in the region."
      ]
    },
    "report_id": "abc-123",
    "json_url": "/reports/storage/abc-123.json",
    "pdf_url": "/reports/storage/abc-123.pdf",
    "excel_url": "/reports/storage/abc-123.xlsx",
    "expires_at": "2026-06-01T..."
  }
}
```

---

# 13. Key Architecture Decisions

## Decision 1: psycopg instead of asyncpg

**Problem**: asyncpg (async PostgreSQL driver) is incompatible with Windows' ProactorEventLoop used by `asyncio`. It throws `ConnectionResetError` when the event loop tries to manage connections.

**Solution**: Use `psycopg` (psycopg 3) with `postgresql+psycopg://` connection string. It fully supports async and works on Windows.

**Trade-off**: psycopg is slightly slower than asyncpg (benchmarks: ~10% slower). But correctness > speed.

## Decision 2: Derived kWh from final_sale

**Problem**: The `consumption_amount` column in `invoice_items` was sometimes empty or unreliable. Financial data (`final_sale`, `tva`) is always populated because it's the actual billing amount.

**Solution**: Compute kWh from the invoice amount:
```
kWh = ((final_sale - tva) / 1000) / kwh_price
```

**Why this works**: Invoices are generated by the utility company (STEG). The `final_sale` is always correct (it's what they charge). The `consumption_amount` meter reading was sometimes manually entered and had errors.

## Decision 3: pgvector over a separate vector database

Options considered:
- **Pinecone/Milvus/Weaviate** — SaaS or separate service, adds operational complexity
- **pgvector** — extension inside existing PostgreSQL

**Winner**: pgvector. One less thing to deploy, manage, and monitor. Performance is excellent for <100K vectors with HNSW index.

## Decision 4: Local LLM over cloud API

Options considered:
- **OpenAI / Anthropic** — pay per token, data leaves premises
- **Ollama + Qwen** — free, local, private

**Winner**: Ollama + Qwen2.5. Orange Tunisie's energy consumption data is business-sensitive. Sending it to OpenAI's servers is not acceptable.

## Decision 5: Async job polling over synchronous request

**Why**: LLM inference takes 30–120 seconds. A synchronous HTTP request would:
- Time out (most proxies timeout at 30s)
- Block the server thread (waste resources)
- Provide no progress feedback

**Async job pattern**: Submit → get job_id → poll for results. The frontend shows a loading spinner with progress percentage.

## Decision 6: RAG + XGBoost + LLM (Three-Layer Architecture)

**Why not just LLM?**
LLMs can't predict precise kWh numbers. They're language models, not regression models.

**Why not just XGBoost?**
XGBoost predicts numbers but can't write a report, provide recommendations, or explain reasoning in natural language.

**Why not just RAG?**
RAG finds similar sites but can't forecast or generate narratives.

**The combination** is more powerful than any single approach:
- XGBoost → precise numerical forecast
- RAG → evidence-based analogy for new sites
- LLM → human-readable report with reasoning

```
XGBoost → "42,500,000 kWh"
RAG     → "10 similar sites consumed 48-52K kWh"
LLM     → "Budget will increase 3.2% due to new sites..."
```

---

# 14. How to Run / Test / Modify

## Quick Start

```bash
# 1. Start the AI service
cd Orange/AI
.\venv\Scripts\Activate.ps1
python run.py

# 2. Verify health (in another terminal)
curl.exe http://localhost:5000/api/v1/health
# → {"status":"ok","database":"connected","ollama":"available"}

# 3. Test analytics (no Ollama needed)
curl.exe http://localhost:5000/api/v1/analytics/current-year?year=2026

# 4. Test report (needs Ollama)
curl.exe -X POST http://localhost:5000/api/v1/reports/budget-forecast \
  -H "Content-Type: application/json" \
  -d '{"target_year": 2027}'
# → {"job_id": "xxx", "status": "pending"}

# 5. Poll for result
curl.exe http://localhost:5000/api/v1/reports/xxx
```

## Common Tasks

### Retrain the model (after data changes)
```bash
cd Orange/AI
.\venv\Scripts\Activate.ps1
python -m scripts.train_models
```

### Rebuild vector index (after data changes)
```bash
cd Orange/AI
.\venv\Scripts\Activate.ps1
python -m scripts.seed_vector_index
```

### Add a new report type
1. Create a template in `report/templates/`
2. Add prompt logic in `rag/prompt_templates.py`
3. Add schema in `api/schemas/reports.py`
4. Add endpoint in `api/routers/reports.py`
5. Add template mapping in `report/generator.py`

### Switch to a different LLM model
1. Pull the model: `ollama pull qwen2.5:7b`
2. Update `.env`: `OLLAMA_MODEL=qwen2.5:7b`
3. Restart FastAPI

### Add a new data source
1. Create extractor in `data/extractors/`
2. Add SQL query function
3. Call it from `llm/chain.py` or `api/routers/`

---

# 15. Glossary

| Term | Definition |
|------|-----------|
| **LLM** | Large Language Model — neural network that generates text |
| **RAG** | Retrieval-Augmented Generation — fetch relevant data before asking LLM |
| **pgvector** | PostgreSQL extension for vector similarity search |
| **Vector** | List of numbers representing data (e.g., 12 monthly kWh values) |
| **Cosine similarity** | Measure of how similar two vectors are (0 to 1) |
| **HNSW** | Hierarchical Navigable Small World — fast nearest-neighbor search index |
| **XGBoost** | Gradient boosted trees ML algorithm |
| **Feature engineering** | Creating ML-ready columns from raw data (lags, rolling averages) |
| **Lag feature** | Previous time period's value (e.g., lag_1 = last month) |
| **Cyclical encoding** | Converting month numbers to sin/cos so model understands circularity |
| **Token** | Chunk of text that an LLM processes (word piece) |
| **Temperature** | Controls randomness in LLM output (0=deterministic, 1=random) |
| **Constrained decoding** | Forcing LLM to output valid JSON matching a schema |
| **Streaming** | LLM output token-by-token vs all at once |
| **Ollama** | Local LLM server (runs models on your machine) |
| **Qwen2.5** | Open-source LLM family by Alibaba (3b, 7b, 14b, 72b) |
| **Pyppeteer** | Python port of Puppeteer — controls headless Chrome |
| **openpyxl** | Python library for reading/writing Excel files |
| **Jinja2** | Python template engine (like Nunjucks/Handlebars) |
| **Pydantic** | Python library for data validation using type hints |
| **Asyncio** | Python async/await framework for concurrent operations |
| **Millime** | 1/1000 of a Tunisian Dinar (TND). Invoice amounts are in millimes |
| **BT / MT** | Basse Tension / Moyenne Tension (Low/Medium Voltage) — electrical classification |
| **Terminal / Nodal / Agreg** | Site configuration types (end tower, aggregation node, aggregate) |
| **Direction** | Geographic region: 1=Nord, 2=Centre, 3=Sud |

---

# 16. Appendix: File Index

| Absolute Path | Role |
|--------------|------|
| `Orange/AI/run.py` | Entry point, starts uvicorn |
| `Orange/AI/api/main.py` | FastAPI app, CORS, lifespan, router mounting |
| `Orange/AI/api/dependencies.py` | get_db() dependency injector |
| `Orange/AI/api/routers/health.py` | GET /health endpoint |
| `Orange/AI/api/routers/reports.py` | POST/GET budget forecast (async jobs) |
| `Orange/AI/api/routers/analytics.py` | GET current-year, yoy, clusters |
| `Orange/AI/api/routers/ingestion.py` | POST upload XLS for new sites |
| `Orange/AI/api/schemas/reports.py` | Pydantic models: NewSiteInput, ReportRequest, etc. |
| `Orange/AI/api/schemas/analytics.py` | Pydantic models: BillingSummaryItem, AnalyticsResponse |
| `Orange/AI/api/schemas/ingestion.py` | Pydantic models: ParsedSite, IngestionResult |
| `Orange/AI/api/schemas/common.py` | Shared Pydantic models: ErrorResponse, SiteDto |
| `Orange/AI/llm/chain.py` | **Main orchestrator** — ties everything together |
| `Orange/AI/llm/ollama_client.py` | HTTP client to Ollama API |
| `Orange/AI/llm/parsers.py` | Parse + validate LLM structured JSON output |
| `Orange/AI/rag/embeddings.py` | Build 12-dim consumption vectors from DB data |
| `Orange/AI/rag/retriever.py` | Find similar sites via pgvector similarity search |
| `Orange/AI/rag/indexer.py` | Full rebuild of consumption_vectors table |
| `Orange/AI/rag/prompt_templates.py` | Construct system + user prompts for LLM |
| `Orange/AI/ml/config.py` | XGBoost hyperparams + feature column list |
| `Orange/AI/ml/features.py` | Feature engineering: lags, rolling, cyclical encoding |
| `Orange/AI/ml/forecasting/xgboost_model.py` | Train, load, predict with XGBoost |
| `Orange/AI/ml/forecasting/prophet_model.py` | Alternative Prophet model wrapper |
| `Orange/AI/ml/forecasting/trainer.py` | Training pipeline runner |
| `Orange/AI/data/db.py` | Async SQLAlchemy engine + session factory |
| `Orange/AI/data/vector_store.py` | pgvector CRUD: store, search, delete vectors |
| `Orange/AI/data/extractors/consumption.py` | Primary: monthly kWh from invoice_items |
| `Orange/AI/data/extractors/invoices.py` | Billing summaries by direction/year |
| `Orange/AI/data/extractors/visits.py` | Visit compliance + technician performance |
| `Orange/AI/data/extractors/sites.py` | Site metadata queries |
| `Orange/AI/data/extractors/billing.py` | Tariff config + budget calculation |
| `Orange/AI/report/generator.py` | Orchestrates JSON + PDF + Excel generation |
| `Orange/AI/report/puppeteer_renderer.py` | HTML → PDF via headless Chromium |
| `Orange/AI/report/excel_exporter.py` | openpyxl styled Excel workbook builder |
| `Orange/AI/report/templates/budget_forecast.html` | Jinja2 report template |
| `Orange/AI/report/templates/investment_impact.html` | Jinja2 investment template |
| `Orange/AI/config/settings.py` | All env vars with defaults + cached accessor |
| `Orange/AI/scripts/seed_vector_index.py` | CLI: seed consumption_vectors from all history |
| `Orange/AI/scripts/train_models.py` | CLI: train XGBoost from DB |
| `Orange/AI/.env` | Local config: DB, Ollama, Chromium paths |
| `Orange/AI/requirements.txt` | Python package dependencies |
| `egrs_backend/src/ai/ai.module.ts` | NestJS module registration |
| `egrs_backend/src/ai/ai.controller.ts` | NestJS proxy POST/GET routes |
| `egrs_backend/src/ai/ai.service.ts` | NestJS HTTP proxy to FastAPI |
| `egrs_backend/src/ai/dto/` | TypeScript DTO files |

---

## Quick Reference: Data Flow Diagram

```
                    ┌──────────────────────┐
                    │   POST /reports/      │
                    │   budget-forecast     │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  Create Job (UUID)    │
                    │  Spawn Async Task     │
                    │  Return job_id        │
                    └──────────┬───────────┘
                               │ (background)
                               ▼
                    ┌──────────────────────┐
                    │  extract_historical() │
                    │  SQL: invoice_items → │
                    │  ((final_sale-tva)/   │
                    │   1000)/kwh_price     │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  engineer_features()  │
                    │  lags, rolling,       │
                    │  cyclical encoding    │
                    └──────────┬───────────┘
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
            ┌──────────────┐    ┌──────────────────┐
            │ RAG: find    │    │ XGBoost: predict │
            │ similar sites│    │ next year kWh    │
            │ via pgvector │    │ per site         │
            └──────┬───────┘    └────────┬─────────┘
                   │                     │
                   └──────────┬──────────┘
                              ▼
                    ┌──────────────────────┐
                    │  build_prompt()       │
                    │  system + user prompt │
                    │  with all data        │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  ollama_client()      │
                    │  POST /api/generate   │
                    │  qwen2.5:3b           │
                    │  format=json_schema   │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  parse_output()       │
                    │  validate schema     │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  generate_report()    │
                    │  JSON + PDF + Excel   │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  Return {job_id:     │
                    │   status: completed  │
                    │   result: {...}}     │
                    └──────────────────────┘
```

---

*End of Course. For questions, contact the EGRS engineering team.*
