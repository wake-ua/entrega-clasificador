# Intent Analysis and Data Catalog System

> Conversational AI agent that analyzes user search intentions, detects ambiguities through intelligent clarification questions, and accesses structured dataset catalogs for data space applications.

---

## Objectives

- **Main objective:** Demonstrate a robust intent analysis system for conversational data space agents that can extract structured search filters from natural language queries.

- **Secondary goals:**
  - Implement hybrid ambiguity detection (deterministic rules + LLM semantic analysis)
  - Prevent infinite clarification loops with adaptive questioning logic
  - Support multi-search sessions without context contamination
  - Provide extensible JSON-based dataset catalog architecture

- **Expected impact:** This research component enables more natural human-AI interaction in data space environments by intelligently handling ambiguous queries and maintaining conversation context across multiple searches.

---

## Funding Information

This research project is supported by:

**Funding organization/institution:** MINISTERIO PARA LA TRANSFORMACION DIGITAL Y DE LA FUNCION PUBLICA
**Program or grant:** CONVOCATORIA DE AYUDAS PROGRAMA DE ESPACIOS DE DATOS SECTORIALES PARA LA TRANSFORMACIÓN DIGITAL DE LOS SECTORES PRODUCTIVOS ESTRATÉGICOS MEDIANTE LA CREACIÓN DE DEMOSTRADORES Y CASOS DE USO DE ESPACIOS DE COMPARTICIÓN DE DATOS
**Project code/reference:** TSI-100121-2024-24
**Duration:** [01/11/2024 – 31/12/2025]

---

## Technology

This project uses the following technologies:

- **Python 3.11+** - Programming language
- **LangGraph** - State machine framework for building conversational AI agents
- **LangChain** - LLM orchestration and prompt management
- **Ollama** - Local LLM server (Llama 3.1)
- **uv** - Fast Python package manager
- **JSON** - Dataset catalog storage format

### Key Features

- ✅ Automatic extraction of structured filters (spatial, temporal, demographic)
- ✅ Hybrid ambiguity detection (deterministic + LLM)
- ✅ 3-attempt clarification limit to prevent infinite loops
- ✅ Multi-search session support with conversation boundaries
- ✅ Dynamic JSON-based dataset catalogs

For detailed architecture documentation, see [docs.md](docs.md).
---

## Installation and Usage

### Prerequisites

1. **Python 3.11 or higher** - [Download](https://www.python.org/downloads/)

2. **uv** (fast Python package manager)
   - Windows PowerShell:
     ```powershell
     powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
     ```
   - macOS/Linux:
     ```bash
     curl -LsSf https://astral.sh/uv/install.sh | sh
     ```

3. **Ollama** (local LLM server) - [Download](https://ollama.com/download)
   - After installation, run:
     ```bash
     ollama pull llama3.1
     ```
   - Verify it's running at http://127.0.0.1:11434

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/jjmb10-ua/entrega-clasificador.git
   cd entrega-clasificador
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Verify installation**
   ```bash
   uv run python -c "import langgraph; print('✅ Installation successful')"
   ```

### Running the Agent

**Basic execution:**
```bash
uv run python app.py
```

**Example conversation:**
```
>>> Tú: Busca datos de contaminación del aire en Madrid

Sistema: Para refinar la búsqueda, ¿podrías especificar?
         - Período temporal (año, rango de fechas)

>>> Tú: 2020-2024

Sistema: He entendido que buscas:
         - Tema: contaminación del aire
         - Ubicación: Madrid
         - Período: 2020-2024
         ¿Es correcto? (sí/no)

>>> Tú: sí
```

**Exit:** Type `salir`, `exit`, or `quit`

---

## Authors / Contributors

- **Juan José Martínez Berná** – [@jjmb10-ua](https://github.com/jjmb10-ua)

---

## License

This project is distributed under the MIT License.

---

## 💬 Contact

For questions, collaborations, or further information:

📧 [wake@dlsi.ua.es](mailto:wake@dlsi.ua.es)  
🌐 [Wake Research group](https://wake.dlsi.ua.es/)

---

## Documentation

For detailed technical documentation including:
- Complete architecture diagrams
- Execution flow examples
- Implementation details
- Design decisions
- Troubleshooting guide

See [docs.md](docs.md)