"""
Funciones de búsqueda, filtrado y selección de datasets.
Capa de abstracción sobre los catálogos de fuentes (JSON).
"""
from typing import List, Dict, Any, Optional
import json
import os
from pathlib import Path


# Ruta al directorio de catálogos
SOURCES_DIR = Path(__file__).parent / "sources"

def _load_all_catalogs() -> List[Dict[str, Any]]:
    """Carga dinámicamente todos los catálogos JSON en el directorio sources."""
    all_datasets = []
    
    # Buscar todos los archivos .json en el directorio sources
    if not SOURCES_DIR.exists():
        return all_datasets
    
    for json_file in SOURCES_DIR.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                datasets = json.load(f)
                if isinstance(datasets, list):
                    all_datasets.extend(datasets)
                else:
                    # Si es un solo dataset (dict), añádelo como lista
                    all_datasets.append(datasets)
        except (json.JSONDecodeError, IOError) as e:
            # Ignorar archivos JSON inválidos o con errores de lectura
            print(f"Warning: Could not load {json_file.name}: {e}")
            continue
    
    return all_datasets


# Cache de catálogos (evita releer JSON en cada llamada)
_CATALOG_CACHE = None

def get_all_datasets() -> List[Dict[str, Any]]:
    """
    Obtiene todos los datasets de todos los catálogos.
    Usa caché para eficiencia.
    """
    global _CATALOG_CACHE
    if _CATALOG_CACHE is None:
        _CATALOG_CACHE = _load_all_catalogs()
    return _CATALOG_CACHE

def reload_catalogs():
    """Fuerza recarga de catálogos desde disco (útil para testing)."""
    global _CATALOG_CACHE
    _CATALOG_CACHE = None

# Simula el buscador real de catalogos, en producción solo devolveria los relevantes (ahora todos)
def search_datasets() -> List[Dict[str, Any]]:
    """
    Devuelve todos los datasets disponibles en el catálogo.
    El LLM será responsable de filtrar y seleccionar los relevantes.
    
    Returns:
        Lista completa de todos los datasets
    """
    return get_all_datasets()

def get_dataset_by_id(dataset_id: str) -> Optional[Dict[str, Any]]:
    """
    Obtiene un dataset específico por su ID.
    
    Args:
        dataset_id: ID del dataset
        
    Returns:
        Dataset o None si no existe
    """
    all_datasets = get_all_datasets()
    for dataset in all_datasets:
        if dataset.get("dataset_id") == dataset_id:
            return dataset
    return None

def get_datasets_by_ids(dataset_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Obtiene múltiples datasets por sus IDs.
    
    Args:
        dataset_ids: Lista de IDs de datasets
        
    Returns:
        Lista de datasets encontrados
    """
    result = []
    for ds_id in dataset_ids:
        dataset = get_dataset_by_id(ds_id)
        if dataset:
            result.append(dataset)
    return result

def extract_schemas(datasets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extrae solo los schemas de una lista de datasets.
    
    Args:
        datasets: Lista de datasets completos
        
    Returns:
        Lista de schemas
    """
    schemas = []
    for ds in datasets:
        columnas = ds.get("columnas")
        if columnas:
            schema = {
                "dataset_id": ds.get("dataset_id"),
                "nombre": ds.get("nombre"),
                "topic": ds.get("topic"),
                "columnas": columnas
            }
            schemas.append(schema)
    return schemas

def get_available_topics() -> List[str]:
    """
    Devuelve lista de todos los topics disponibles.
    
    Returns:
        Lista de topics únicos
    """
    all_datasets = get_all_datasets()
    topics = set()
    for ds in all_datasets:
        topic = ds.get("topic")
        if topic:
            topics.add(topic)
    return sorted(list(topics))