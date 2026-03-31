# FörderMatch AI

## Overview

**FörderMatch AI** is an AI-powered system that analyzes the eligibility of companies for public funding programs.

The German funding landscape is highly complex: programs are defined through legal guidelines, technical documents, and fragmented requirements that are difficult to interpret.

This project demonstrates how **structured data, semantic search, and rule-based reasoning** can be combined into a transparent decision-support system.


## Key Features

### 1. Semantic Analysis of Funding Programs

* PDF-based funding guidelines are parsed and chunked
* Text is embedded and stored in a vector database (Chroma)
* Relevant sections are retrieved via semantic similarity

→ Enables targeted access to legally relevant content


### 2. Rule-Based Eligibility Engine

* Deterministic rule engine evaluates:

  * Company size (KMU logic)
  * Revenue thresholds
  * Project status (e.g. “before project start”)
  * Exclusion criteria
* Produces a transparent, explainable rule score


### 3. Hybrid Scoring System

Each program is evaluated using:

* **Rule-based score** (hard constraints & eligibility)
* **Semantic score** (relevance of retrieved documents)

→ Combined into a final ranking score


### 4. Evidence-Based Output (RAG)

* Results are grounded in original documents
* System returns:

  * structured summaries
  * requirements & risks
  * exact source references (incl. page references)

→ No “black-box AI” – every output is traceable


### 5. Interactive Web Demo

* Input: company profile
* Output:

  * ranked funding programs
  * explanation of fit
  * detailed program analysis
  * PDF export


## Tech Stack

**Frontend**

* HTML, CSS, Vanilla JavaScript

**Backend**

* Python, FastAPI

**Data Layer**

* SQLite (structured program data & rules)
* Chroma (vector database for embeddings)

**AI / Logic**

* Embeddings (semantic retrieval)
* Retrieval-Augmented Generation (RAG)
* Rule-based scoring engine


## System Architecture (High-Level)

```
PDF Documents
    ↓
Text Extraction & Chunking
    ↓
Embeddings → Chroma Vector DB
    ↓
Retrieval Service
    ↓
Rule Engine
    ↓
Scoring Service
    ↓
FastAPI Backend
    ↓
Web Application
```


## Example Workflow

1. User inputs a company profile
2. System retrieves relevant guideline passages
3. Rule engine evaluates eligibility
4. Scores are calculated per program
5. Programs are ranked
6. Detailed view shows reasoning + sources


## Project Structure

```
backend/
  api/                # FastAPI endpoints
  services/           # retrieval, scoring, rule engine, RAG
  db/                 # schema & repository layer

scripts/
  ingest_program.py   # document ingestion pipeline
  rank_programs.py    # ranking logic
  validate_ranking.py # evaluation & testing

demo_webapp/
  index.html
  styles.css
  app.js

data/
  programs.db         # SQLite database
  chroma/             # vector embeddings
```


## What This Project Demonstrates

* Designing **hybrid AI systems (rules + embeddings)**
* Building **RAG pipelines with source grounding**
* Translating **legal/complex documents into structured logic**
* End-to-end system design:

  * data ingestion
  * retrieval
  * scoring
  * API
  * frontend


## Future Improvements

* Automated document updates & monitoring
* Expanded funding program coverage
* LLM-based explanation refinement
* Multi-user / production-ready deployment


## Live Demo

Frontend:
https://foerdermatch-ai.up.railway.app

Backend:
https://foerdermatch-ai-backend.up.railway.app


## Author

Merle Mai
B.Sc. Computer Science (TUHH)
