# Architecture – FörderMatch AI

## System Overview

FörderMatch AI is a modular system combining:

1. Document Processing Pipeline
2. Vector-Based Retrieval
3. Rule-Based Decision Engine
4. Scoring Layer
5. API Layer
6. Web Frontend

The architecture separates **data extraction, reasoning, and presentation** to ensure scalability and transparency.


## Core Design Principle

The system follows a hybrid approach:

* **Deterministic logic (rules)** → for eligibility & constraints
* **Semantic retrieval (embeddings)** → for contextual understanding
* **Grounded output (RAG)** → for explainability


## 1. Data Layer

### SQLite (Relational Layer)

Stores structured program data:

* programs
* documents
* chunks
* program_rules

The schema explicitly models:

* eligibility rules
* document metadata
* traceability of sources 


### Chroma (Vector Layer)

Stores:

* embeddings of document chunks
* semantic metadata

Used for:

* similarity search
* contextual retrieval


## 2. Document Pipeline

Processing steps:

1. PDF ingestion
2. Text extraction
3. Chunking (overlapping windows)
4. Embedding generation
5. Storage in Chroma + SQLite linkage

Each chunk contains:

* program_id
* document_id
* page reference
* text


## 3. Retrieval Service

Responsibilities:

* Generate query embeddings
* Retrieve top-k relevant chunks
* Filter by program_id

Provides:

* semantic context for scoring
* evidence for explanations


## 4. Rule Engine

Deterministic evaluation of eligibility constraints:

* Boolean, enum, numeric rules
* Weighted scoring
* Hard-fail conditions (e.g. project already started)

Key properties:

* fully explainable
* reproducible
* independent of AI models


## 5. Scoring Layer

Each program is evaluated via:

* Rule Score (structured constraints)
* Semantic Score (retrieval relevance)

Example pipeline: 

Sorting logic:

* hard_fail programs pushed to bottom
* then sorted by effective score


## 6. RAG-Based Detail Generation

The system generates structured outputs using retrieved chunks:

* summaries
* requirements
* risks
* source references

Output is strictly **grounded in retrieved evidence**, not hallucinated.

Implementation includes:

* sentence extraction
* deduplication
* source linking 


## 7. API Layer (FastAPI)

Core endpoints:

* `/health` → system status
* `/rank` → program ranking
* `/detail` → detailed analysis
* `/evaluate` → debug scoring

The API orchestrates:

* retrieval
* scoring
* RAG generation

Reference implementation: 


## 8. Frontend (Demo Application)

Responsibilities:

* collect user input
* visualize ranking
* display explanations
* show source references
* export results as PDF

No framework used → focuses on clarity and control


## Data Flow

```
User Input (Profile)
        ↓
API (/rank)
        ↓
Retrieval Service (Chroma)
        ↓
Rule Engine (SQLite rules)
        ↓
Scoring Service
        ↓
Top Programs Selected
        ↓
RAG Detail Generation
        ↓
Frontend Rendering
```


## Key Engineering Decisions

### 1. Hybrid AI Approach

Avoids pure LLM reliance → ensures reliability

### 2. Source Grounding

Every output is linked to original documents

### 3. Deterministic Rule Layer

Critical for legal/eligibility logic

### 4. Modular Services

Clear separation:

* retrieval
* scoring
* rules
* API


## Scalability Considerations

The system is designed for extension:

* Add new programs via ingestion pipeline
* Extend rule sets per program
* Replace embedding model if needed
* Integrate LLMs for richer explanations


## Limitations

* Demo-level UI (not production-grade)
* Limited program dataset
* No automated document updates yet