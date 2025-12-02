import json
from typing import Dict, Any, List, Optional
from langgraph.types import interrupt, Command
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_ollama import ChatOllama
from langgraph.runtime import Runtime

# NOTA: Usamos Any para runtime/state para evitar importaciones circulares con app.py
# Si tienes un archivo shared.py o types.py, impórtalos desde ahí.

# ==========================================
# 1. FUNCIONES AUXILIARES (HELPERS)
# ==========================================

def extract_intent_components(messages: list, llm: ChatOllama) -> Dict[str, Any]:
    """Extrae componentes atómicos del intent del usuario."""
    user_messages = [m for m in messages if isinstance(m, HumanMessage)]
    if not user_messages:
        return None
    
    conversation_history = "\n".join([
        f"Usuario: {m.content}" if isinstance(m, HumanMessage) else f"Asistente: {m.content[:100]}"
        for m in messages
    ])
    
    prompt = f"""Analiza la solicitud del usuario y divide su intención en componentes estructurados.

MENSAJES:
{conversation_history}

Extrae:
1. topic: Tema principal
2. temporal_filters: Filtros temporales EN LENGUAJE NATURAL
3. demographic_filters: Filtros demográficos EN LENGUAJE NATURAL
4. spatial_filters: Filtros geográficos EN LENGUAJE NATURAL
5. required_columns: Columnas mencionadas
6. aggregation_type: Tipo de agregación

IMPORTANTE: Responde ÚNICAMENTE con un objeto JSON válido, sin explicaciones ni texto adicional.

Formato requerido:
{{
  "topic": "empleo",
  "temporal_filters": ["últimos 5 años"],
  "demographic_filters": ["mayores de 50 años"],
  "spatial_filters": ["en España"],
  "required_columns": ["edad", "fecha", "empleo"],
  "aggregation_type": "statistics"
}}"""
    
    try:
        response = llm.invoke(prompt).content.strip()
        print(f"🔍 Respuesta raw del LLM:\n{response[:200]}...")
        
        # Limpiar markdown
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            response = response.split("```")[1].split("```")[0].strip()
        
        # Intentar parsear JSON
        parsed = json.loads(response)
        print(f"✅ JSON parseado correctamente")
        return parsed
        
    except json.JSONDecodeError as e:
        print(f"❌ Error parseando JSON: {e}")
        print(f"Respuesta problemática: {response[:300]}")
        # Retornar un intent básico por defecto
        return {
            "topic": "consulta general",
            "temporal_filters": [],
            "demographic_filters": [],
            "spatial_filters": [],
            "required_columns": [],
            "aggregation_type": "statistics"
        }
    except Exception as e:
        print(f"❌ Error inesperado extrayendo componentes: {e}")
        return None

def detect_ambiguities(intent: Dict[str, Any], llm: ChatOllama) -> Optional[str]:
    """Detecta ambigüedades o información faltante crítica."""
    prompt = f"""Analiza si esta búsqueda es ambigua onecesita más detalles:

INTENT ACTUAL:
{json.dumps(intent, indent=2, ensure_ascii=False)}

TENEMOS AMBIGÜEDAD CUANDO:
1. BÚSQUEDA DEMASIADO GENERAL: No se especifica DÓNDE (spatial_filters) ni CUÁNDO (temporal_filters), etc. DEBES comprobar que el intent tiene valor para cada filtro. En caso contrario, DEBES preguntar por los vacíos.
3. TÉRMINOS VAGOS: Palabras como "reciente", "actual", "últimos años", "personas mayores", "crisis" que no son concretas.

SI ES AMBIGUO O FALTA CONTEXTO:
Genera preguntas amables y directas para guiar al usuario a completar los filtros.
Ejemplo: "¿Te interesan datos de un país o región específica?" o "¿Buscas datos de este año o una serie histórica?"

IMPORTANTE: Responde SOLO con:
1. Una pregunta corta y amigable, O
2. Exactamente la palabra "NO_AMBIGUITIES"

NO incluyas explicaciones, análisis ni introducciones."""
    
    try:
        response = llm.invoke(prompt).content.strip()
        if "NO_AMBIGUITIES" in response.upper():
            return None
        return response
    except Exception as e:
        return None

def build_confirmation_message(intent: Dict[str, Any], llm: ChatOllama) -> str:
    """Construye mensaje de confirmación en primera persona."""
    prompt = f"""Genera un mensaje de confirmación EN PRIMERA PERSONA basado en este intent:
{json.dumps(intent, indent=2, ensure_ascii=False)}

Ejemplo: "En resumen, busco datos de empleo en España..."
Termina preguntando si es correcto."""
    try:
        return llm.invoke(prompt).content.strip()
    except Exception:
        return f"En resumen, busco datos de {intent.get('topic', 'tu consulta')}. ¿Es correcto?"

# ==========================================
# 2. NODOS DEL PROCESO DE CONFIRMACIÓN
# ==========================================

def node_analyze_intent(state: Dict, runtime: Runtime) -> Command:
    """
    NODO 1: LÓGICA PURA. Analiza y decide el siguiente paso.
    NO contiene interrupt(), por lo que si se re-ejecuta es seguro.
    """
    print("\n--- Entrando en node_analyze_intent ---")
    iterations = state.get("iterations", 0) + 1
    max_iterations = state.get("max_iterations", 15)
    
    if iterations >= max_iterations:
        return Command(
            update={"messages": [AIMessage(content="Límite de pasos alcanzado.")], "iterations": iterations},
            goto="dashboard" # O salida de error
        )

    # 1. Extraer componentes
    print("🔍 Analizando intent...")
    intent_components = extract_intent_components(state["messages"], runtime.context.llm)
    
    if not intent_components:
         return Command(
            update={"messages": [AIMessage(content="No entendí tu solicitud. ¿Reformulamos?")], "iterations": iterations},
            goto="chatbot" # O terminar
        )

    # 2. Detectar ambigüedades
    clarification = detect_ambiguities(intent_components, runtime.context.llm)
    
    if clarification:
        print("⚠️ Ambigüedad detectada. Derivando a pregunta.")
        return Command(
            update={
                "messages": [AIMessage(content=clarification)],
                "iterations": iterations
            },
            goto="ask_clarification"  # Salta al nodo de pregunta
        )
    
    # 3. Preparar confirmación
    print("✅ Intent claro. Preparando confirmación.")
    confirmation_msg = build_confirmation_message(intent_components, runtime.context.llm)
    
    return Command(
        update={
            "messages": [AIMessage(content=confirmation_msg)],
            "user_search_intent_structured": intent_components,
            "iterations": iterations
        },
        goto="ask_confirmation"  # Salta al nodo de confirmación
    )

def node_ask_clarification(state: Dict) -> Command:
    """
    NODO 2: PREGUNTA (Ambigüedad).
    Tiene el interrupt al inicio. Al reanudar, no repite lógica pesada.
    """
    print("\n--- Entrando en node_ask_clarification ---")
    
    # Recuperar la última pregunta (generada por node_analyze_intent)
    last_msg = state["messages"][-1]
    
    # --- PAUSA ---
    user_response = interrupt(last_msg)
    
    print(f"✅ Respuesta recibida: {user_response}")
    
    # Regresar al análisis con la nueva información
    return Command(
        update={
            "messages": [HumanMessage(content=user_response)]
        },
        goto="analyze_intent"
    )

def node_ask_confirmation(state: Dict, runtime: Runtime) -> Command:
    """
    NODO 3: PREGUNTA (Confirmación).
    Tiene el interrupt al inicio.
    """
    print("\n--- Entrando en node_ask_confirmation ---")
    
    last_msg = state["messages"][-1]
    
    # --- PAUSA ---
    user_response = interrupt(last_msg)
    
    # Analizar respuesta (Si/No) - Esto es rápido y barato
    check_prompt = f"""Analiza la respuesta del usuario a una pregunta de confirmación.
    
    Respuesta del usuario: "{user_response}"
    
    CRITERIOS:
    - AFIRMATIVA: Solo si acepta explícitamente (sí, claro, vale, ok, correcto).
    - NEGATIVA: Si dice "no", si pide cambios, si añade información nueva, o si dice algo diferente a confirmar.
    
    Responde SOLO una palabra: "AFIRMATIVA" o "NEGATIVA"."""
    
    decision = runtime.context.llm.invoke(check_prompt).content.strip().upper()
    print(f"🤔 Decisión del LLM sobre la confirmación: {decision}")
    
    if "AFIRMATIVA" in decision:
        print("🚀 Confirmado. Pasando a búsqueda.")
        intent_struct = state.get("user_search_intent_structured", {})
        topic = intent_struct.get("topic", "consulta")
        
        return Command(
            update={
                "messages": [HumanMessage(content=user_response)],
                "user_search_intent": f"Datos de {topic} con filtros confirmados"
            },
            goto="search"  # AVANZA al siguiente paso lógico del grafo
        )
    else:
        print("🔄 Corrección detectada. Volviendo a analizar.")
        return Command(
            update={
                "messages": [HumanMessage(content=user_response)]
            },
            goto="analyze_intent"  # RETROCEDE para re-analizar
        )