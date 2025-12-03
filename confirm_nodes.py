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

def extract_intent_components(messages: list, llm: ChatOllama, search_boundaries: list = None) -> Dict[str, Any]:
    """Extrae componentes atómicos del intent del usuario."""
    # Filtrar mensajes desde el último boundary
    if search_boundaries:
        last_boundary = search_boundaries[-1] if search_boundaries else 0
        messages = messages[last_boundary:]
        print(f"📍 Analizando mensajes desde índice {last_boundary} ({len(messages)} mensajes)")
    
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

Formato requerido con EJEMPLO DE RESPUESTA:
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

def detect_ambiguities(intent: Dict[str, Any], llm: ChatOllama, clarification_attempts: int = 0) -> Optional[str]:
    """Detecta ambigüedades o información faltante crítica."""
    
    # 1. ANÁLISIS DETERMINISTA: Separar filtros vacíos de llenos
    empty_filters = []
    filled_filters = {}
    
    filter_names = ["spatial_filters", "temporal_filters", "demographic_filters"]
    
    for filter_name in filter_names:
        filter_value = intent.get(filter_name, [])
        if not filter_value or (isinstance(filter_value, list) and len(filter_value) == 0):
            empty_filters.append(filter_name)
        else:
            filled_filters[filter_name] = filter_value
    
    # 2. Contar filtros llenos
    num_filled = len(filled_filters)
    
    # 3. LÍMITE: Después de 2 intentos, aceptar lo que hay
    if clarification_attempts >= 2:
        print(f"⚠️ Límite alcanzado (intento #{clarification_attempts}). Aceptando búsqueda.")
        return None
    
    # 4. LÓGICA ADAPTATIVA
    ask_for_empty = False
    check_vague = False
    
    if clarification_attempts == 0:
        ask_for_empty = True
        check_vague = True
        mode = "PRIMERA_VEZ"
    elif num_filled >= 2:
        ask_for_empty = False
        check_vague = True
        mode = "SOLO_AMBIGUEDADES"
    else:
        ask_for_empty = True
        check_vague = True
        mode = "INSISTIR"
    
    print(f"🔍 Modo: {mode} (intento #{clarification_attempts}, {num_filled}/3 filtros)")
    
    # 5. CONSTRUCCIÓN MODULAR DEL PROMPT
    prompt_base = f"""Analiza esta búsqueda:

TOPIC: {intent.get('topic', 'N/A')}
FILTROS VACÍOS: {', '.join(empty_filters) if empty_filters else 'Ninguno'}
FILTROS CON VALORES: {json.dumps(filled_filters, indent=2, ensure_ascii=False) if filled_filters else 'Ninguno'}

"""
    
    instructions = []
    
    if check_vague and filled_filters:
        instructions.append("""DETECTA AMBIGÜEDADES en los valores (sé estricto):
- VAGOS: "últimos años", "reciente", "actual", "cerca", "personas mayores", "últimamente"
- CLAROS: "España", "2025", "2020-2024", "últimos 5 años", "mayores de 65 años"

IMPORTANTE: Un año específico como "2025" o "2024" es CLARO, no es vago.
Solo pregunta si encuentras términos VAGOS.""")
    
    if ask_for_empty and empty_filters:
        instructions.append("""HAZ PREGUNTAS para llenar filtros vacíos:
- Los 3 filtros son igual de importantes
- Pregunta de forma natural por lo que falta
- Puedes preguntar por varios a la vez""")
    
    # Criterio de salida
    if num_filled >= 2:
        instructions.append("""
CRITERIO DE SALIDA:
- Si tienes 2/3 filtros con valores CLAROS (años específicos, países, rangos concretos) → NO_AMBIGUITIES
- Solo pregunta si hay algo realmente VAGO o AMBIGUO""")
    else:
        instructions.append("\nSi ya hay 2/3 filtros claros, responde: NO_AMBIGUITIES")
    
    prompt = prompt_base + "\n".join(instructions) + """

Genera preguntas amigables y naturales que cubran TODO lo necesario.
Si TODO está suficientemente claro, responde exactamente "NO_AMBIGUITIES"."""
    
    try:
        response = llm.invoke(prompt).content.strip()
        if "NO_AMBIGUITIES" in response.upper():
            return None
        # Extraer solo la pregunta (eliminar prefijos como "Pregunta:")
        lines = response.split('\n')
        for line in lines:
            if '?' in line:
                return line.strip()
        return response.strip()
    except Exception as e:
        print(f"Error en detect_ambiguities: {e}")
        return None

def build_confirmation_message(intent: Dict[str, Any], llm: ChatOllama) -> str:
    """Construye mensaje de confirmación en primera persona."""
    prompt = f"""Genera un mensaje de confirmación EN PRIMERA PERSONA recopilando todos los filtros y el topic de este intent:
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
    search_boundaries = state.get("search_boundaries", [])
    intent_components = extract_intent_components(state["messages"], runtime.context.llm, search_boundaries)
    
    if not intent_components:
         return Command(
            update={"messages": [AIMessage(content="No entendí tu solicitud. ¿Reformulamos?")], "iterations": iterations},
            goto="chatbot" # O terminar
        )

    # 2. Detectar ambigüedades
    attempts = state.get("clarification_attempts", 0)
    clarification = detect_ambiguities(intent_components, runtime.context.llm, attempts)
    
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
    
    # Incrementar contador de intentos
    new_attempts = state.get("clarification_attempts", 0) + 1
    
    # Regresar al análisis con la nueva información
    return Command(
        update={
            "messages": [HumanMessage(content=user_response)],
            "clarification_attempts": new_attempts
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