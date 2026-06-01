# EGRS AI Service Architecture

## Overview
The AI service is a Python FastAPI application that provides budget prediction, 
current year analysis, and investment impact analysis for the EGRS application.

## Flow
```
User (Form + XLS Upload) 
  → NestJS Backend (ai/ proxy, JWT auth) 
  → FastAPI AI Service 
    → RAG (pgvector similarity search) 
    → XGBoost (consumption forecast) 
    → LLM Qwen (reasoning + structured output) 
    → Pyppeteer (PDF) + openpyxl (Excel) + JSON
  → Response to Frontend
```

## Data Sources
- **invoice_items**: Primary consumption data (raw, not rate-derived)
- **visits + visit_measurements**: Technician readings
- **sites**: Site metadata (configuration, network type, direction)
- **tariff_config**: Pricing (BT/MT rates, tax)
- **consumption_vectors**: pgvector table with 12-dim yearly consumption embeddings

## Key Design Decisions
1. **Reads raw tables directly** - avoids the nightly-rebuilt site_consumption table race condition and rate-skew issue
2. **12-dim consumption vectors** - one vector per site per year, cosine similarity for RAG retrieval
3. **Async job pattern** - LLM inference takes 30-120s, so reports are generated asynchronously with job polling
4. **Structured LLM output** - constrained JSON schema prevents hallucination of numerical values
5. **No Docker for now** - runs directly on host with Python venv

## Report Types
| Report | Input | Pipeline |
|--------|-------|----------|
| Budget Forecast | new sites + year | RAG → XGBoost → LLM → PDF/Excel |
| Current Year | year | Extract → Summarize → LLM |
| Investment Impact | new sites configs | RAG → LLM |
| Combined | all | All pipelines |
