# 📚 Technical Documentation

> Extended documentation for the Intent Analysis and Data Catalog System

This document contains the technical details that were originally in the README before adapting it to the institutional template.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                   LANGGRAPH GRAPH                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────┐     ┌────────────────┐     ┌──────────┐  │
│  │ Router   │ ──► │ Intent         │ ──► │ Search   │  │
│  │ (LLM)    │     │ Analysis +     │     │ Datasets │  │
│  └──────────┘     │ Clarification  │     └──────────┘  │
│                   └────────────────┘                    │
│                                                         │
│  COMPONENTS:                                            │
│  • confirm_nodes.py → Intent analysis                   │
│  • search/catalog.py → JSON catalog access              │
│  • search/sources/*.json → Fictitious datasets          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Module Structure

```
📁 entrega-clasificador/
├─ app.py                        # Main graph (State, nodes, router, execution)
├─ confirm_nodes.py              # Intent analysis + clarification
├─ search/
│  ├─ sources/                   # Dataset catalogs (JSON)
│  │  ├─ health_catalog.json
│  │  └─ environmental_catalog.json
│  ├─ catalog.py                 # Dynamic loading + search
│  └─ joiners.py                 # Dataset ranking
└─ README.md
```

---

## Execution Examples

### Case 1: Clear search (no clarifications needed)

```
User: Busca datos de pacientes en España del año 2024 para mayores de 65

[Router classifies as "confirm_search"]

[node_analyze_intent executes]
  → extract_intent_components():
    {
      "topic": "patient data",
      "spatial_filters": "Spain",
      "temporal_filters": "2024",
      "demographic_filters": "over 65"
    }
  
  → detect_ambiguities():
    - All filters are filled ✅
    - LLM verifies vagueness: "NOT_VAGUE" ✅
    - Result: "not_ambiguous"

[node_ask_confirmation executes]
  System: I understood you're looking for:
          - Topic: patient data
          - Location: Spain
          - Period: 2024
          - Demographics: over 65
          Is this correct? (yes/no)
  
  User: yes

[node_search executes]
  → search_datasets() → Finds ds1 (Patient Records Spain 2024)
  → rank_by_completeness() → Orders by filter coverage
  → useful_data = [ds1]

[node_negotiate executes - STUB]
  System: Found 1 dataset:
          - ds1: Patient Records Spain 2024 (patient records)

[node_compute executes - STUB]
  → extract_schemas(useful_data)
  System: Schemas extracted for 1 dataset

[node_dashboard executes]
  → Resets user_search_intent, clarification_attempts
  → Adds len(messages) to search_boundaries
  System: Do you need anything else?
```

### Case 2: Ambiguous search (requires clarification)

```
User: Busca datos de contaminación del aire

[Router → confirm_search]

[node_analyze_intent - Attempt 1]
  → extract_intent_components():
    {
      "topic": "air pollution",
      "spatial_filters": "",        ← EMPTY
      "temporal_filters": "",       ← EMPTY
      "demographic_filters": ""     ← EMPTY (not applicable)
    }
  
  → detect_ambiguities():
    - clarification_attempts = 0 (first attempt)
    - Deterministic logic: 3 empty filters detected
    - Result: "ambiguous"

[node_ask_clarification executes]
  System: To refine the search, could you specify?
          - Geographic location (country, region, city)
          - Time period (year, date range)
  
  [clarification_attempts = 0 + 1 = 1]
  
  User: In Madrid from the last 5 years

[node_analyze_intent - Attempt 2]
  → extract_intent_components():
    {
      "topic": "air pollution",
      "spatial_filters": "Madrid",
      "temporal_filters": "last 5 years",  ← Potentially vague
      "demographic_filters": ""
    }
  
  → detect_ambiguities():
    - clarification_attempts = 1
    - Only 1 empty filter, but 2+ filled → Checks vagueness with LLM
    - LLM detects: "last 5 years" is VAGUE (relative date)
    - Result: "ambiguous"

[node_ask_clarification executes]
  System: Could you specify "last 5 years"? (example: 2020-2024)
  
  [clarification_attempts = 1 + 1 = 2]
  
  User: 2020 to 2024

[node_analyze_intent - Attempt 3]
  → extract_intent_components():
    {
      "topic": "air pollution",
      "spatial_filters": "Madrid",
      "temporal_filters": "2020 to 2024",
      "demographic_filters": ""
    }
  
  → detect_ambiguities():
    - clarification_attempts = 2 → ⚠️ LIMIT REACHED
    - Even if demographic_filters is empty, it's accepted automatically
    - Result: "not_ambiguous"

[Continues with confirmation → search → ...]
```

### Case 3: Multiple searches in same session

```
User: Busca datos de salud en España del 2024
[... normal process ...]
[node_dashboard adds search_boundaries.append(15)]  ← Message #15

User: Now search for environmental data in France
[node_analyze_intent]
  → extract_intent_components():
    - Filters messages from index 15 (last boundary)
    - Only considers "Now search for environmental data in France"
    - Does NOT contaminate with "Spain" from previous search ✅
```

---

## Important Notes

### 🔁 Clarification Limit

**The system allows a maximum of 3 intent analysis attempts** (`clarification_attempts` ranges from 0 to 2).

**Behavior:**
- **Attempt 0** (first analysis): Asks for ALL empty filters
- **Attempt 1**: Only asks if ≥2 filters filled but some are vague
- **Attempt 2**: Accepts automatically, even if there are empty/vague filters

**Reason:** Avoid infinite loops if the user cannot/doesn't want to provide more details.

### 🔗 Conversation Boundaries (search_boundaries)

`search_boundaries` is a list of message indices that mark the end of each completed search.

**Problem it solves:**
```python
# Without boundaries:
User: "Search for data from Spain"  
[search 1 complete]
User: "Search for data from France"
[❌ extract_intent_components sees ALL messages]
[❌ Extracts: spatial_filters = "Spain, France" ← CONTAMINATION]

# With boundaries:
search_boundaries = [15]  # Search 1 ended at message 15
User: "Search for data from France"
[✅ extract_intent_components only sees messages from index 15]
[✅ Extracts: spatial_filters = "France" ← CORRECT]
```

### 📂 Catalog Structure

**Location:** `search/sources/*.json`

**Dynamic loading:** Any `.json` file in `sources/` is loaded automatically.

**To add a new domain:**
1. Create `search/sources/my_domain_catalog.json`
2. Follow structure: `[{dataset_id, nombre, topic, descripcion, columnas: [{nombre, descripcion, ejemplo}]}]`
3. ✅ The system detects it automatically

---

## Key System Files

### app.py (331 lines)
Main orchestration file with State definition, nodes, router, and execution loop.

### confirm_nodes.py (325 lines)
Intent analysis and clarification logic with hybrid ambiguity detection.

### search/catalog.py (137 lines)
JSON catalog loading and dataset search functions.

### search/sources/*.json
Fictitious dataset catalogs with complete metadata and column schemas.

---

## Suggested Test Cases

1. **Clear search:** "Busca datos de pacientes en España del año 2024 para mayores de 65"
   - Expected: System confirms directly without clarifications

2. **Ambiguous search:** "Busca datos de contaminación del aire"
   - Expected: System asks for location and time period

3. **Vague values:** "Busca datos de salud en España de hace unos años"
   - Expected: System detects vague temporal filter and asks for specific year

4. **Multiple searches:** Perform two consecutive searches
   - Expected: Second search doesn't contaminate with filters from first

5. **Clarification limit:** Provide incomplete information repeatedly
   - Expected: After 3 attempts, system accepts and continues
