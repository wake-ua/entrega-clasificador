# 📚 Arquitectura: Sistema de Análisis de Intenciones y Catálogos

## 🎯 Visión General

Sistema de agente conversacional que analiza las intenciones del usuario para búsquedas de datos, detecta ambigüedades, hace preguntas de clarificación de forma inteligente, y accede a catálogos de datasets estructurados en JSON.

**Características clave:**
- ✅ Extracción automática de filtros (espaciales, temporales, demográficos)
- ✅ Detección híbrida de ambigüedades (determinística + LLM)
- ✅ Límite de 3 intentos de clarificación para evitar bucles infinitos
- ✅ Soporte multi-búsqueda en misma sesión con límites conversacionales
- ✅ Catálogos JSON dinámicos con metadatos completos

**Stack tecnológico:**
- LangGraph (grafo de estados con interrupciones)
- ChatOllama + Llama 3.1 (modelo local)
- Python 3.11+ con uv

---

## 🏗️ Arquitectura simplificada del Sistema

```
┌─────────────────────────────────────────────────────────┐
│                   GRAFO DE LANGGRAPH                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────┐     ┌────────────────┐     ┌──────────┐   │
│  │ Router   │ ──► │ Análisis de    │ ──► │ Busca    │   │
│  │ (LLM)    │     │ Intenciones    │     │ Datasets │   │
│  └──────────┘     │ + Clarificación│     └──────────┘   │
│                   └────────────────┘                    │
│                                                         │
│  COMPONENTES:                                           │
│  • confirm_nodes.py → Análisis de intenciones           │
│  • search/catalog.py → Acceso a catálogos JSON          │
│  • search/sources/*.json → Datasets ficticios           │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Estructura de Módulos

```
📁 entrega-clasificador/
├─ app.py                        # Grafo principal (State, nodos, router, ejecución)
├─ confirm_nodes.py              # Análisis de intenciones + clarificación
├─ search/
│  ├─ sources/                   # ⭐ Catálogos de datasets (JSON)
│  │  ├─ health_catalog.json         # Datasets médicos/salud
│  │  └─ environmental_catalog.json  # Datasets ambientales
│  ├─ catalog.py                 # Carga dinámica + búsqueda
│  └─ joiners.py                 # Ranking por completitud
└─ docs/
   └─ refactoring-search-architecture.md
```

### Flujo del Grafo (LangGraph)

```
┌────────────┐
│   START    │
└─────┬──────┘
      │
      ▼
┌────────────────────┐
│  router_route_     │  ◄── Clasifica mensaje usuario
│  intent (LLM)      │      (chatbot vs confirm_search)
└─────┬──────────────┘
      │
      ├─► "chatbot" ──► node_chatbot ──► END
      │
      └─► "confirm_search"
            │
            ▼
      ┌──────────────────────┐
      │ node_analyze_intent  │  ◄── Extrae intent + detecta ambigüedades
      └─────┬────────────────┘
            │
            ├─► "ambiguous" ──┐
            │                 ▼
            │           ┌─────────────────────┐
            │           │ node_ask_           │  ◄── interrupt() pregunta al usuario
            │           │ clarification       │      Incrementa clarification_attempts
            │           └──────┬──────────────┘
            │                  │
            │                  └──► Respuesta usuario ──► VUELVE a analyze_intent
            │
            └─► "not_ambiguous"
                  │
                  ▼
            ┌─────────────────────┐
            │ node_ask_           │  ◄── interrupt() confirmación final
            │ confirmation        │      "¿Es correcto?"
            └─────┬───────────────┘
                  │
                  ├─► "no" ──► VUELVE a analyze_intent
                  │
                  └─► "yes"
                        │
                        ▼
                  ┌─────────────┐
                  │ node_search │  ◄── STUB: Busca datasets en catálogos JSON (futuro buscador)
                  └─────┬───────┘
                        │
                        ▼
                  ┌──────────────┐
                  │ node_        │  ◄── STUB: Muestra datasets encontrados
                  │ negotiate    │      (negociación de licencias deshabilitada)
                  └─────┬────────┘
                        │
                        ▼
                  ┌──────────────┐
                  │ node_compute │  ◄── STUB: Extrae schemas
                  └─────┬────────┘      (cómputo deshabilitado)
                        │
                        ▼
                  ┌───────────────┐
                  │ node_         │  ◄── Resetea estado para nueva búsqueda
                  │ dashboard     │      Añade boundary a search_boundaries
                  └─────┬─────────┘
                        │
                        └──► END
```

### Componentes Principales

**1. Análisis de Intenciones (`confirm_nodes.py`)**

Funciones:
- `extract_intent_components()`: Parsea mensajes → JSON estructurado
- `detect_ambiguities()`: Detecta filtros vacíos/vagos (híbrido determinístico+LLM)
- `node_analyze_intent()`: Nodo principal que orquesta extracción + detección
- `node_ask_clarification()`: Interrupt para preguntar al usuario
- `node_ask_confirmation()`: Interrupt para confirmación final

Intent estructurado:
```python
{
    "topic": "datos de pacientes",
    "spatial_filters": "España",
    "temporal_filters": "2024",
    "demographic_filters": "adultos mayores de 65"
}
```

**2. Catálogos de Datos (`search/sources/*.json`)**

Estructura de cada dataset:
```json
{
  "dataset_id": "ds1",
  "nombre": "Patient Records Spain 2024",
  "topic": "patient records",
  "descripcion": "Registros médicos anonimizados...",
  "columnas": [
    {
      "nombre": "age_group",
      "descripcion": "Grupo etario del paciente",
      "ejemplo": "0-18, 19-35, 36-50, 51-65, 65+"
    },
    {
      "nombre": "diagnosis_code",
      "descripcion": "Código ICD-10 del diagnóstico",
      "ejemplo": "J45.0 (Asma), E11.9 (Diabetes tipo 2)"
    }
  ]
}
```
---

## 📋 Requisitos

### Software necesario:

1. **Python 3.11 o superior**
   - Descargar: https://www.python.org/downloads/

2. **uv** (gestor de dependencias rápido)
   - Windows PowerShell:
     ```powershell
     powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
     ```
   - macOS/Linux:
     ```bash
     curl -LsSf https://astral.sh/uv/install.sh | sh
     ```

3. **Ollama** (servidor LLM local)
   - Descargar: https://ollama.com/download
   - Después de instalar, abrir terminal y ejecutar:
     ```bash
     ollama pull llama3.1
     ```
   - Verificar que está corriendo (debe responder en http://127.0.0.1:11434)

---

## 🚀 Instalación Rápida

### Paso 1: Clonar/Descargar el proyecto

Si tienes git:
```bash
git clone <repo-url>
cd entrega-clasificador
```

O simplemente descarga el ZIP y extráelo.

### Paso 2: Instalar dependencias

Abrir terminal en la carpeta del proyecto y ejecutar:

```bash
uv sync
```

Esto instalará automáticamente:
- `langgraph` (framework de grafos)
- `langchain-ollama` (integración con Ollama)
- `langchain-core` (utilidades)

### Paso 3: Verificar instalación

```bash
uv run python -c "import langgraph; print('✅ Instalación correcta')"
```

---

## ▶️ Cómo Ejecutar

### Opción 1: Ejecución simple

```bash
uv run python app.py
```

### Opción 2: Con depuración (ver mensajes internos)

```bash
uv run python app.py --debug
```

### Primera ejecución:

El sistema iniciará y mostrará:
```
Usuario:
```

**Pruébalo con:**
```
Busca datos de contaminación del aire en Madrid
```

El agente te hará preguntas de clarificación como:
- ¿Período temporal? (ejemplo: 2020-2024)
- ¿Grupo demográfico? (ejemplo: población general)

### Salir del sistema:

Escribe `salir`, `exit`, o `quit`

---

## 💬 Ejemplo de Ejecución

### Caso 1: Búsqueda clara (sin clarificaciones)

```
Usuario: Busca datos de pacientes en España del año 2024 para mayores de 65

[Router clasifica como "confirm_search"]

[node_analyze_intent ejecuta]
  → extract_intent_components():
    {
      "topic": "datos de pacientes",
      "spatial_filters": "España",
      "temporal_filters": "2024",
      "demographic_filters": "mayores de 65"
    }
  
  → detect_ambiguities():
    - Todos los filtros están llenos ✅
    - LLM verifica vaguedad: "NO_VAGO" ✅
    - Resultado: "not_ambiguous"

[node_ask_confirmation ejecuta]
  Sistema: He entendido que buscas:
           - Tema: datos de pacientes
           - Ubicación: España
           - Período: 2024
           - Demografía: mayores de 65
           ¿Es correcto? (sí/no)
  
  Usuario: sí

[node_search se ejecuta] (y sigue el flujo...)

[node_negotiate ejecuta - STUB]

[node_compute ejecuta - STUB]

[node_dashboard ejecuta]
  → Resetea user_search_intent, clarification_attempts
  → Añade len(messages) a search_boundaries
  Sistema: ¿Necesitas algo más?
```

### Caso 2: Búsqueda con ambigüedad (requiere clarificación)

```
Usuario: Busca datos de contaminación del aire

[Router → confirm_search]

[node_analyze_intent - Intento 1]
  → extract_intent_components():
    {
      "topic": "contaminación del aire",
      "spatial_filters": "",        ← VACÍO
      "temporal_filters": "",       ← VACÍO
      "demographic_filters": ""     ← VACÍO (no aplica)
    }
  
  → detect_ambiguities():
    - clarification_attempts = 0 (primer intento)
    - Lógica determinística: 3 filtros vacíos detectados
    - Resultado: "ambiguous"

[node_ask_clarification ejecuta]
  Sistema: Para refinar la búsqueda, ¿podrías especificar?
           - Ubicación geográfica (país, región, ciudad)
           - Período temporal (año, rango de fechas)
  
  [clarification_attempts = 0 + 1 = 1]
  
  Usuario: En Madrid de los últimos años

[node_analyze_intent - Intento 2]
  → extract_intent_components():
    {
      "topic": "contaminación del aire",
      "spatial_filters": "Madrid",
      "temporal_filters": "últimos años",  ← Potencialmente vago
      "demographic_filters": ""
    }
  
  → detect_ambiguities():
    - clarification_attempts = 1
    - Solo 1 filtro vacío, pero 2+ llenos → Verifica vaguedad con LLM
    - LLM detecta: "últimos años" es VAGO (fecha relativa)
    - Resultado: "ambiguous"

[node_ask_clarification ejecuta]
  Sistema: ¿Podrías especificar "últimos años"? (ejemplo: 2020-2024)
  
  [clarification_attempts = 1 + 1 = 2]
  
  Usuario: 2020 a 2024

[node_analyze_intent - Intento 3]
  → extract_intent_components():
    {
      "topic": "contaminación del aire",
      "spatial_filters": "Madrid",
      "temporal_filters": "2020 a 2024",
      "demographic_filters": ""
    }
  
  → detect_ambiguities():
    - clarification_attempts = 2 → ⚠️ LÍMITE ALCANZADO
    - Aunque sea ambiguo (en este caso, no lo es), se acepta por límite de 3 iteraciones
    - Resultado: "not_ambiguous"

[Continúa con confirmation → search → ...]
```

### Caso 3: Múltiples búsquedas en misma sesión

```
Usuario: Busca datos de salud en España del 2024
[... proceso normal ...]
[node_dashboard añade search_boundaries.append(15)]  ← Mensaje #15

Usuario: Ahora busca datos ambientales en Francia
[node_analyze_intent]
  → extract_intent_components():
    - Filtra mensajes desde índice 15 (última boundary)
    - Solo considera "Ahora busca datos ambientales en Francia"
    - NO contamina con "España" de búsqueda anterior ✅
```
---

## ⚠️ Notas Importantes

### 🔁 Límite de Clarificaciones

**El sistema permite un máximo de 3 intentos de análisis de intenciones** (`clarification_attempts` va de 0 a 2).

**Comportamiento:**
- **Intento 0** (primer análisis): Pregunta por TODOS los filtros vacíos
- **Intento 1**: Solo pregunta si ≥2 filtros llenos pero alguno es vago
- **Intento 2**: Acepta automáticamente, aunque haya filtros vacíos/vagos

**Razón:** Evitar bucles infinitos si el usuario no puede/quiere proporcionar más detalles.

### 🔗 Límites Conversacionales (search_boundaries)

`search_boundaries` es una lista de índices de mensajes que marcan el fin de cada búsqueda completada.

> Necesario porque para no pasar conversación entera al LLM para sacar intents, solo lo relevante

---

### 📂 Estructura de Catálogos

**Ubicación:** `search/sources/*.json`

**Carga dinámica:** Cualquier archivo `.json` en `sources/` se carga automáticamente.

**Para añadir nuevo dominio:**
1. Crear `search/sources/mi_dominio_catalog.json`
2. Seguir estructura: `[{dataset_id, nombre, topic, descripcion, columnas: [{nombre, descripcion, ejemplo}]}]`
3. ✅ El sistema lo detecta automáticamente

---

## 📂 Archivos del Sistema

### 📁 app.py (313 líneas)

**Responsabilidad:** Orquestación del grafo completo

**Contiene:**
- `State` (TypedDict): 15+ campos incluyendo messages, user_search_intent, clarification_attempts, search_boundaries
- `Context` (TypedDict): Configuración de LLM
- Nodos:
  - `node_chatbot`: Conversación general
  - `node_search`: Busca datasets en catálogos JSON
  - `node_negotiate`: STUB (muestra datasets encontrados)
  - `node_compute`: STUB (extrae schemas)
  - `node_dashboard`: Resetea estado y añade boundary
- Router: `router_route_intent` (clasifica con LLM)
- Compilación de grafo + loop de ejecución con manejo de interrupts

### 📁 confirm_nodes.py (312 líneas)

**Responsabilidad:** Análisis de intenciones y clarificación

**Funciones clave:**
```python
def extract_intent_components(messages, llm, search_boundaries):
    """
    Filtra mensajes desde última boundary, envía al LLM con prompt estructurado.
    Parsea respuesta JSON en {topic, spatial_filters, temporal_filters, demographic_filters}
    """

def detect_ambiguities(intent, llm, clarification_attempts):
    """
    Lógica adaptativa:
    - attempts=0: Pregunta por todos los filtros vacíos (determinístico)
    - attempts=1: Solo verifica vaguedad con LLM si ≥2 filtros llenos
    - attempts≥2: Acepta automáticamente (límite alcanzado)
    """

def node_analyze_intent(state, config):
    """Llama extract + detect, retorna Command con goto"""

def node_ask_clarification(state, config):
    """interrupt() + incrementa clarification_attempts"""

def node_ask_confirmation(state, config):
    """interrupt() para confirmación final yes/no"""
```

### 📁 search/catalog.py (137 líneas)

**Responsabilidad:** Acceso a catálogos JSON

**Funciones:**
```python
def _load_all_catalogs() -> List[Dict]:
    """Carga todos los .json de sources/, cachea resultado"""

def search_datasets(query: str = None) -> List[Dict]:
    """Devuelve todos los datasets (filtrado delegado a LLM)"""

def extract_schemas(datasets: List[Dict]) -> List[Dict]:
    """Extrae campo 'columnas' de cada dataset"""
```

### 📁 search/joiners.py

**Responsabilidad:** Ranking de datasets

**Función principal:**
```python
def rank_by_completeness(datasets, intent_dict):
    """Ordena datasets por cobertura de filtros del intent"""
```

### 📁 search/sources/health_catalog.json (94 líneas)

**Contenido:** 2 datasets de salud
- `ds1`: Patient Records Spain 2024 (registros médicos)
- `ds2`: Treatment Costs EU 2023-2024 (costos de tratamientos)

**Estructura validada:**
```json
[
  {
    "dataset_id": "ds1",
    "nombre": "Patient Records Spain 2024",
    "topic": "patient records",
    "descripcion": "Registros médicos anonimizados...",
    "columnas": [
      {
        "nombre": "age_group",
        "descripcion": "Grupo etario del paciente",
        "ejemplo": "0-18, 19-35, 36-50, 51-65, 65+"
      },
      ...
    ]
  }
]
```

### 📁 search/sources/environmental_catalog.json

**Contenido:** Datasets ambientales (calidad del aire, etc.)

---

## ✅ Conclusión

El sistema combina **análisis de intenciones robusto**, **detección inteligente de ambigüedades**, y **catálogos extensibles** para proporcionar una experiencia de búsqueda conversacional natural con protecciones contra bucles infinitos.
