# app.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Annotated, Optional, List, Dict, Any, Tuple
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.runtime import Runtime
from langgraph.graph.message import add_messages
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import MemorySaver
from langchain_ollama import ChatOllama
from langchain_core.messages import (
    SystemMessage, HumanMessage, AIMessage, BaseMessage
)
# Importar los nodos de confirmación
from confirm_nodes import (
    node_analyze_intent, 
    node_ask_clarification, 
    node_ask_confirmation
)

# Importar agente Table-QA y funciones de búsqueda
#from agents.table_qa_agent import invoke_table_qa_agent
from search.catalog import search_datasets, extract_schemas
from search.joiners import rank_by_completeness

# ---------- 1) Estado del flujo ----------
class State(TypedDict):
    # ===== Variables Esenciales =====
    messages: Annotated[list, add_messages] # Conversación

    user_search_intent: Optional[str] # Plan de búsqueda del usuario (lenguaje natural)

    user_search_intent_structured: Optional[Dict[str, Any]] # Intent extraido de su plan, dividido en componentes
    # Estructura del intent estructurado:
    # {
    #   "topic": str,  # Tema principal (empleo, salud, medio ambiente)
    #   "temporal_filters": List[Dict],  # [{"raw": "últimos 3 años", "normalized": {"type": "last_n_years", "n": 3}}]
    #   "demographic_filters": List[Dict],  # [{"raw": "mayores de 50", "column": "edad", "operator": ">", "value": 50}]
    #   "spatial_filters": List[Dict],  # [{"raw": "en Madrid", "column": "ciudad", "value": "Madrid"}]
    #   "required_columns": List[str],  # ["empleo", "edad", "fecha"]
    #   "aggregation_type": str  # "statistics" | "count" | "average" | "row_level"
    # }
    
    useful_data: List[Dict[str, Any]] # Datasets seleccionados del catálogo
    
    # ===== Agente Negociador (futuro subgrafo) =====
    negotiation_terms: Dict[str, Any]
        # Términos negociados: {requires_DPA, allowed_commercial, restrictions, etc.}
    
    # ===== Agente Table-QA =====
    schemas: List[Dict[str, Any]]  # Esquemas de tablas para agente
    query_plan: Optional[str]  # Plan de consulta SQL del agente Table-QA
    aggregates: Dict[str, Any]  # Resultados agregados del cómputo
    
    # ===== Control de bucles =====
    iterations: int
    max_iterations: int
    
    # ===== Dashboard final =====
    dashboard: Optional[str]

# ---------- 2) Contexto del runtime (recursos que no van al State) ----------
@dataclass
class Context:
    llm: ChatOllama
    schema_catalog: Dict[str, Any] = None  # Catálogo de esquemas
    
    def __post_init__(self):
        if self.schema_catalog is None:
            self.schema_catalog = {}

# ---------- 3) Nodos ----------
SYSTEM = "Eres un agente de acuerdos/licencias y búsqueda de datos. Responde en español con precisión."

def node_chatbot(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
    """Genera una respuesta conversacional simple."""
    print("\n--- Entrando en node_chatbot ---")
    
    iterations = state.get("iterations", 0) + 1
    print(f"🔄 Iteración {iterations}/{state.get('max_iterations', 15)}")
    
    system_message = SystemMessage(content=SYSTEM)
    msgs = state["messages"]
    local = [system_message] + msgs
    reply = runtime.context.llm.invoke(local)
    print(f"Respuesta del chatbot (LLM): {reply.content}")
    return {"messages": [reply], "iterations": iterations}

def node_search(state: State) -> Dict[str, Any]:
    """Busca datasets en el catálogo del espacio de datos."""
    print("\n--- Entrando en node_search ---")
    
    iterations = state.get("iterations", 0) + 1
    print(f"🔄 Iteración {iterations}/{state.get('max_iterations', 15)}")
    
    # Validación: Debemos tener user_search_intent para buscar
    search_intent = state.get("user_search_intent")
    if not search_intent:
        print("⚠️ ADVERTENCIA: No hay user_search_intent. Esto no debería pasar.")
        search_intent = "consulta sin especificar"
    
    print(f"Buscando datos para: {search_intent}")
    
    # 1. Buscar TODOS los datasets disponibles (sin filtros) --> en el futuro solo relacionados con tematica
    # El agente Table-QA decidirá cuáles usar de los relacionados según user_search_intent
    results = search_datasets()
    print(f"Encontrados {len(results)} datasets en total")
    
    # 2. Ordenar por completeness (más columnas = más completo)
    results = rank_by_completeness(results)
    print(f"Datasets ordenados por completitud")
    
    # 3. Por ahora todos los resultados son "useful_data"
    # El agente Table-QA filtrará los relevantes según el search_intent
    useful = results
    
    return {"useful_data": useful, "iterations": iterations}

def node_negotiate(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
    """
    🚧 STUB: Punto de integración para el AGENTE NEGOCIADOR (futuro subgrafo).
    """
    print("\n--- 🚧 Entrando en node_negotiate (futuro subgrafo) ---")
    
    iterations = state.get("iterations", 0) + 1
    print(f"🔄 Iteración {iterations}/{state.get('max_iterations', 15)}")
    
    return {"iterations": iterations}

def node_compute(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
    """
    🚧 STUB: Punto de integración para el AGENTE TABLE-QA (subgrafo).
    """
    print("\n--- Entrando en node_compute (invocando subgrafo Table-QA) ---")
    
    iterations = state.get("iterations", 0) + 1

    # Devolver resultados del subgrafo
    return {"iterations": iterations}

def node_dashboard(state: State) -> Dict[str, Any]:
    """🚧 STUB: Construye el dashboard final con todo lo recopilado."""
    print("\n--- Entrando en node_dashboard ---")
    
    iterations = state.get("iterations", 0) + 1

    return {"iterations": iterations}

# ---------- 5) Routers ----------
def router_route_intent(state: State, runtime: Runtime[Context]) -> str:
    """
    Router inteligente que usa LLM para decidir el primer nodo del flujo.
    
    Clasifica la intención del usuario y retorna el NOMBRE del nodo destino:
    - "chatbot": conversación general, saludos, preguntas sobre el sistema
    - "confirm_search": peticiones de búsqueda/análisis de datos
    """
    ###################
    # A futuro meteremos una opción más de intent:
    # ("retrieval_data": para recuperar búsquedas de otras sesiones anteriores)
    ###################
    print("\n--- Router: Clasificando intención ---")
    messages = state["messages"]
    
    # Formateamos el historial para el prompt (convierte objetos Message a texto)
    formatted_messages = "\n".join([f"{type(m).__name__}: {m.content}" for m in messages])
    last_message_content = messages[-1].content if messages else ""
    
    # Prompt: pedimos directamente el NOMBRE DEL NODO
    prompt = f"""Analiza la conversación y decide el siguiente nodo:

Historial:
{formatted_messages}

Último mensaje: "{last_message_content}"

Responde SOLO con el nombre del nodo (sin comillas):
- "chatbot" si es conversación general (saludo, pregunta sobre el sistema, agradecimiento)
- "confirm_search" si pide buscar/analizar/consultar datos

Respuesta:"""
    
    out = runtime.context.llm.invoke(prompt)
    next_node = out.content.strip().replace('"', '')

    print(f"Decisión del router (LLM): {next_node}")
    
    # Validación: solo permitimos nodos conocidos
    if next_node not in ["chatbot", "confirm_search"]:
        next_node = "chatbot"  # Opción segura por defecto
        print(f"ADVERTENCIA: Nodo no reconocido, usando: {next_node}")

    return next_node

# ---------- 6) Grafo ----------
def build_graph() -> StateGraph:
    g = StateGraph(State)
    
    # Nodos del grafo
    g.add_node("chatbot", node_chatbot)

    # --- NUEVOS NODOS (Reemplazan a confirm_search) ---
    g.add_node("analyze_intent", node_analyze_intent)
    g.add_node("ask_clarification", node_ask_clarification)
    g.add_node("ask_confirmation", node_ask_confirmation)

    g.add_node("search", node_search)
    g.add_node("negotiate", node_negotiate)
    g.add_node("compute", node_compute)
    g.add_node("dashboard", node_dashboard)


    # 1. Router principal desde START: conversacional → chatbot, búsqueda → confirm_search
    g.add_conditional_edges(
        START,                   # ← Inicia directamente con router (sin nodo previo)
        router_route_intent,     # ← Router que piensa con LLM
        {
            # Si el router dice "confirm_search", ahora enviamos a "analyze_intent"
            "confirm_search": "analyze_intent",
            "chatbot": "chatbot"                 # ← Si retorna "chatbot" → nodo "chatbot"
        }
    )

    # 2. Chatbot → END (respuestas conversacionales simples)
    g.add_edge("chatbot", END)

    # NOTA: Los nodos analyze, ask_clarification y ask_confirmation
    # se conectan entre sí dinámicamente usando Command(goto=...),
    # por lo que no necesitamos definir add_edge fijos entre ellos.
    
    # search → negotiate → compute → dashboard → END
    g.add_edge("search", "negotiate")
    g.add_edge("negotiate", "compute")
    g.add_edge("compute", "dashboard")
    g.add_edge("dashboard", END)
    
    return g

# ---------- 7) Run ----------
if __name__ == "__main__":
    print("Agente de Datos Interactivo. Escribe 'salir' o 'exit' para terminar.")
    
    llm = ChatOllama(model="llama3.1", base_url="http://127.0.0.1:11434", temperature=0.2)
    ctx = Context(llm=llm)
    
    # Checkpointer necesario para interrupt()
    memory = MemorySaver()
    graph = build_graph().compile(checkpointer=memory)

    # Estado inicial vacío que se conservará entre turnos
    state: State = {
        "messages": [],
        "user_search_intent": None,
        "user_search_intent_structured": None,  # Añadido: intent estructurado
        "useful_data": [],
        "negotiation_terms": {},
        "schemas": [],
        "query_plan": None,
        "aggregates": {},
        "iterations": 0,
        "max_iterations": 15,
        "dashboard": None,
    }
    
    # Thread ID para checkpointer (mantiene estado entre interrupts)
    thread_id = "user_session_1"
    config = {"configurable": {"thread_id": thread_id}}

    while True:
        user_input = input(">>> Tú: ")
        if user_input.lower() in ["salir", "exit"]:
            print(">>> Agente: ¡Hasta luego!")
            break
        
        # Añadir mensaje del usuario al historial
        state["messages"].append(HumanMessage(content=user_input))
        
        # Rastrear mensajes ya impresos usando (contenido, índice) como clave única
        # NO usamos id() porque los objetos cambian entre streams
        printed_messages = set()
        for i, msg in enumerate(state.get("messages", [])):
            if isinstance(msg, AIMessage):
                printed_messages.add((i, msg.content[:100]))  # (índice, primeros 100 chars)
        
        # Stream con checkpointer (necesario para interrupt())
        final_state = None
        for chunk in graph.stream(state, context=ctx, config=config, stream_mode='values'):
            final_state = chunk
            
            # Imprimir SOLO mensajes nuevos
            current_messages = final_state.get("messages", [])
            for i, msg in enumerate(current_messages):
                msg_key = (i, msg.content[:100])
                if isinstance(msg, AIMessage) and msg_key not in printed_messages:
                    print(f">>> Agente: {msg.content}")
                    printed_messages.add(msg_key)
        
        # Actualizar estado si terminó la ejecución
        if final_state:
            state = final_state
            
            # Verificar si hay un interrupt pendiente
            if "__interrupt__" in final_state:
                interrupts = final_state["__interrupt__"]
                if interrupts:
                    # El nodo llamó a interrupt() con un AIMessage
                    # La pregunta YA fue impresa en el loop anterior
                    # Solo pedimos la respuesta del usuario
                    
                    # Pedir respuesta del usuario
                    user_response = input(">>> Tú: ")
                    if user_response.lower() in ["salir", "exit"]:
                        print(">>> Agente: ¡Hasta luego!")
                        break
                    
                    # Reanudar con Command(resume=respuesta)
                    print(f"⚙️ Reanudando grafo...")
                    for chunk in graph.stream(Command(resume=user_response), context=ctx, config=config, stream_mode='values'):
                        final_state = chunk
                        
                        # Imprimir SOLO mensajes nuevos
                        current_messages = final_state.get("messages", [])
                        for i, msg in enumerate(current_messages):
                            msg_key = (i, msg.content[:100])
                            if isinstance(msg, AIMessage) and msg_key not in printed_messages:
                                print(f">>> Agente: {msg.content}")
                                printed_messages.add(msg_key)
                    
                    # Actualizar estado después del resume
                    if final_state:
                        state = final_state
