# UI Flow – FörderMatch AI

## Purpose

The UI demonstrates how complex funding programs can be translated into a **simple, structured user experience**.

Focus:

* clarity
* transparency
* explainability


## 1. Entry Screen (Profile Input)

User provides company information:

* industry
* number of employees
* revenue
* location
* project category
* project status

Goal:
→ Create a structured input for evaluation


## 2. Analysis Phase

Triggered after form submission.

Backend performs:

1. Profile normalization
2. Semantic retrieval of relevant documents
3. Rule-based eligibility evaluation
4. Score calculation


## 3. Ranking View

User sees:

* ranked list of funding programs
* overall score
* rule score vs semantic score
* status indicator:

  * eligible
  * partially matching
  * not eligible

Additional insights:

* “Why this program fits”
* missing information / blockers


## 4. Detail View

User selects a program.

Displayed:

### Program Summary

* funding type
* target group
* key conditions

### Requirements

* actionable checklist

### Risks

* typical failure reasons

### Sources

* direct links to original documents
* page-level references

→ Full transparency of decision logic


## 5. Export (PDF Report)

User can export results including:

* company profile
* ranking
* detailed program analysis
* sources

Purpose:
→ usable output for real-world decision making


## UX Principles

* No hidden logic → everything explained
* Minimal friction → single flow
* Evidence over opinion → source-backed outputs


## End-to-End Flow

```
Profile Input
    ↓
Analysis
    ↓
Ranking
    ↓
Detail View
    ↓
Export
```


## Goal of the Demo

To demonstrate how AI can:

* simplify complex regulatory systems
* provide structured decision support
* remain transparent and explainable
