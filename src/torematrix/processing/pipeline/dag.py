"""
DAG (Directed Acyclic Graph) utilities for pipeline management.

Provides functions for validating, analyzing, and optimizing pipeline DAGs.
"""

from typing import List, Set, Dict, Tuple, Optional, Any
import networkx as nx
from collections import defaultdict

from .config import StageConfig
from .exceptions import CyclicDependencyError


def build_dag(stages: List[StageConfig]) -> nx.DiGraph:
    """
    Build a DAG from stage configurations.
    
    Args:
        stages: List of stage configurations
        
    Returns:
        NetworkX directed graph
        
    Raises:
        CyclicDependencyError: If the graph contains cycles
    """
    dag = nx.DiGraph()
    
    # Add nodes
    for stage in stages:
        dag.add_node(stage.name, config=stage)
    
    # Add edges (dependencies)
    for stage in stages:
        for dependency in stage.dependencies:
            dag.add_edge(dependency, stage.name)
    
    # Validate DAG
    if not nx.is_directed_acyclic_graph(dag):
        cycles = list(nx.simple_cycles(dag))
        raise CyclicDependencyError(cycles)
    
    return dag


def get_execution_order(dag: nx.DiGraph) -> List[str]:
    """
    Get topological execution order for stages.
    
    Args:
        dag: Pipeline DAG
        
    Returns:
        List of stage names in execution order
    """
    return list(nx.topological_sort(dag))


def get_parallel_groups(dag: nx.DiGraph) -> List[Set[str]]:
    """
    Get groups of stages that can be executed in parallel.
    
    Args:
        dag: Pipeline DAG
        
    Returns:
        List of sets, each containing stages that can run in parallel
    """
    # Use topological generations to find parallel groups
    generations = list(nx.topological_generations(dag))
    return [set(gen) for gen in generations]


def get_critical_path(dag: nx.DiGraph, execution_times: Dict[str, float]) -> List[str]:
    """
    Find the critical path through the DAG.
    
    Args:
        dag: Pipeline DAG
        execution_times: Estimated execution time for each stage
        
    Returns:
        List of stage names forming the critical path
    """
    # Add execution times as edge weights
    weighted_dag = dag.copy()
    for node in weighted_dag.nodes():
        time = execution_times.get(node, 1.0)
        for successor in weighted_dag.successors(node):
            weighted_dag[node][successor]['weight'] = time
    
    # Find longest path (critical path)
    try:
        path = nx.dag_longest_path(weighted_dag, weight='weight')
        return path
    except nx.NetworkXError:
        # Fallback to simple topological order
        return get_execution_order(dag)


def validate_dependencies(stages: List[StageConfig]) -> List[str]:
    """
    Validate all stage dependencies exist and are valid.
    
    Args:
        stages: List of stage configurations
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    stage_names = {s.name for s in stages}
    
    for stage in stages:
        # Check for missing dependencies
        for dep in stage.dependencies:
            if dep not in stage_names:
                errors.append(f"Stage '{stage.name}' has unknown dependency '{dep}'")
        
        # Check for self-dependency
        if stage.name in stage.dependencies:
            errors.append(f"Stage '{stage.name}' depends on itself")
    
    return errors


def get_stage_depth(dag: nx.DiGraph, stage_name: str) -> int:
    """
    Get the depth of a stage in the DAG (longest path from any root).
    
    Args:
        dag: Pipeline DAG
        stage_name: Name of the stage
        
    Returns:
        Depth of the stage
    """
    if stage_name not in dag:
        return -1
    
    # Find all nodes with no predecessors (roots)
    roots = [n for n in dag.nodes() if dag.in_degree(n) == 0]
    
    # Find longest path from any root to this stage
    max_depth = 0
    for root in roots:
        try:
            paths = nx.all_simple_paths(dag, root, stage_name)
            for path in paths:
                max_depth = max(max_depth, len(path) - 1)
        except nx.NetworkXNoPath:
            continue
    
    return max_depth


def get_subgraph(dag: nx.DiGraph, stage_names: Set[str]) -> nx.DiGraph:
    """
    Get a subgraph containing only specified stages and their connections.
    
    Args:
        dag: Pipeline DAG
        stage_names: Set of stage names to include
        
    Returns:
        Subgraph containing only specified stages
    """
    return dag.subgraph(stage_names).copy()


def analyze_dag_complexity(dag: nx.DiGraph) -> Dict[str, Any]:
    """
    Analyze DAG complexity metrics.
    
    Args:
        dag: Pipeline DAG
        
    Returns:
        Dictionary of complexity metrics
    """
    metrics = {
        'node_count': dag.number_of_nodes(),
        'edge_count': dag.number_of_edges(),
        'is_connected': nx.is_weakly_connected(dag),
        'max_in_degree': max((dag.in_degree(n) for n in dag.nodes()), default=0),
        'max_out_degree': max((dag.out_degree(n) for n in dag.nodes()), default=0),
        'avg_degree': sum(dag.degree(n) for n in dag.nodes()) / dag.number_of_nodes() if dag.number_of_nodes() > 0 else 0,
        'parallel_groups': len(get_parallel_groups(dag)),
        'longest_path_length': len(nx.dag_longest_path(dag)) if dag.number_of_nodes() > 0 else 0
    }
    
    return metrics


def optimize_dag(dag: nx.DiGraph) -> nx.DiGraph:
    """
    Optimize DAG by removing redundant edges.
    
    Removes edges that are implied by transitivity.
    
    Args:
        dag: Pipeline DAG
        
    Returns:
        Optimized DAG
    """
    # Compute transitive reduction
    reduced = nx.transitive_reduction(dag)
    
    # Copy node attributes
    for node in dag.nodes():
        reduced.nodes[node].update(dag.nodes[node])
    
    return reduced