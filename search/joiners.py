"""
Funciones auxiliares para ordenar y limitar resultados de datasets.
"""
from typing import List, Dict, Any


def rank_by_completeness(
    datasets: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Ordena datasets por número de columnas (más completo = más columnas).
    
    Args:
        datasets: Lista de datasets
        
    Returns:
        Lista ordenada por número de columnas descendente
    """
    return sorted(datasets, key=lambda ds: len(ds.get("columnas", [])), reverse=True)


def get_top_n(
    datasets: List[Dict[str, Any]],
    n: int = 10
) -> List[Dict[str, Any]]:
    """
    Devuelve los primeros N datasets de una lista.
    
    Args:
        datasets: Lista de datasets
        n: Número máximo de datasets a devolver
        
    Returns:
        Lista con máximo N elementos
    """
    return datasets[:n]
