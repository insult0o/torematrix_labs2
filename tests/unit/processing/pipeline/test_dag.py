"""
Unit tests for DAG utilities.
"""

import pytest
import networkx as nx

from torematrix.processing.pipeline.dag import (
    build_dag,
    get_execution_order,
    get_parallel_groups,
    get_critical_path,
    validate_dependencies,
    get_stage_depth,
    get_subgraph,
    analyze_dag_complexity,
    optimize_dag
)
from torematrix.processing.pipeline.config import StageConfig, StageType
from torematrix.processing.pipeline.exceptions import CyclicDependencyError


class TestDAGUtilities:
    """Test cases for DAG utility functions."""
    
    @pytest.fixture
    def linear_stages(self):
        """Create linear pipeline stages."""
        return [
            StageConfig(name="A", type=StageType.PROCESSOR, processor="a"),
            StageConfig(name="B", type=StageType.PROCESSOR, processor="b", dependencies=["A"]),
            StageConfig(name="C", type=StageType.PROCESSOR, processor="c", dependencies=["B"]),
            StageConfig(name="D", type=StageType.PROCESSOR, processor="d", dependencies=["C"])
        ]
    
    @pytest.fixture
    def parallel_stages(self):
        """Create pipeline with parallel stages."""
        return [
            StageConfig(name="A", type=StageType.PROCESSOR, processor="a"),
            StageConfig(name="B", type=StageType.PROCESSOR, processor="b", dependencies=["A"]),
            StageConfig(name="C", type=StageType.PROCESSOR, processor="c", dependencies=["A"]),
            StageConfig(name="D", type=StageType.PROCESSOR, processor="d", dependencies=["B", "C"])
        ]
    
    @pytest.fixture
    def complex_stages(self):
        """Create complex pipeline stages."""
        return [
            StageConfig(name="A", type=StageType.PROCESSOR, processor="a"),
            StageConfig(name="B", type=StageType.PROCESSOR, processor="b"),
            StageConfig(name="C", type=StageType.PROCESSOR, processor="c", dependencies=["A"]),
            StageConfig(name="D", type=StageType.PROCESSOR, processor="d", dependencies=["A", "B"]),
            StageConfig(name="E", type=StageType.PROCESSOR, processor="e", dependencies=["C", "D"]),
            StageConfig(name="F", type=StageType.PROCESSOR, processor="f", dependencies=["E"])
        ]
    
    def test_build_dag_linear(self, linear_stages):
        """Test building DAG from linear stages."""
        dag = build_dag(linear_stages)
        
        assert len(dag.nodes()) == 4
        assert len(dag.edges()) == 3
        assert nx.is_directed_acyclic_graph(dag)
        
        # Check edges
        assert dag.has_edge("A", "B")
        assert dag.has_edge("B", "C")
        assert dag.has_edge("C", "D")
    
    def test_build_dag_parallel(self, parallel_stages):
        """Test building DAG with parallel branches."""
        dag = build_dag(parallel_stages)
        
        assert len(dag.nodes()) == 4
        assert len(dag.edges()) == 4
        
        # Check parallel structure
        assert dag.has_edge("A", "B")
        assert dag.has_edge("A", "C")
        assert dag.has_edge("B", "D")
        assert dag.has_edge("C", "D")
    
    def test_build_dag_with_cycle(self):
        """Test that cycles are detected."""
        stages = [
            StageConfig(name="A", type=StageType.PROCESSOR, processor="a", dependencies=["C"]),
            StageConfig(name="B", type=StageType.PROCESSOR, processor="b", dependencies=["A"]),
            StageConfig(name="C", type=StageType.PROCESSOR, processor="c", dependencies=["B"])
        ]
        
        with pytest.raises(CyclicDependencyError) as exc:
            build_dag(stages)
        
        assert "cycle" in str(exc.value).lower()
        assert exc.value.cycles == [['A', 'C', 'B']] or exc.value.cycles == [['B', 'A', 'C']] or exc.value.cycles == [['C', 'B', 'A']]
    
    def test_get_execution_order(self, complex_stages):
        """Test getting topological execution order."""
        dag = build_dag(complex_stages)
        order = get_execution_order(dag)
        
        assert len(order) == 6
        
        # Check ordering constraints
        assert order.index("A") < order.index("C")
        assert order.index("A") < order.index("D")
        assert order.index("B") < order.index("D")
        assert order.index("C") < order.index("E")
        assert order.index("D") < order.index("E")
        assert order.index("E") < order.index("F")
    
    def test_get_parallel_groups(self, parallel_stages):
        """Test getting parallel execution groups."""
        dag = build_dag(parallel_stages)
        groups = get_parallel_groups(dag)
        
        assert len(groups) == 3
        assert groups[0] == {"A"}
        assert groups[1] == {"B", "C"}
        assert groups[2] == {"D"}
    
    def test_get_parallel_groups_complex(self, complex_stages):
        """Test parallel groups for complex DAG."""
        dag = build_dag(complex_stages)
        groups = get_parallel_groups(dag)
        
        # A and B can run in parallel (no dependencies)
        assert {"A", "B"} in groups
        # C and D might run together depending on topological generation
        # E runs after C and D
        # F runs last
        
        # Verify all stages are included
        all_stages = set()
        for group in groups:
            all_stages.update(group)
        assert all_stages == {"A", "B", "C", "D", "E", "F"}
    
    def test_get_critical_path(self, parallel_stages):
        """Test finding critical path."""
        dag = build_dag(parallel_stages)
        
        # Equal execution times
        execution_times = {"A": 1.0, "B": 1.0, "C": 1.0, "D": 1.0}
        path = get_critical_path(dag, execution_times)
        
        # Should be A -> B or C -> D (both have same length)
        assert len(path) == 3
        assert path[0] == "A"
        assert path[-1] == "D"
        
        # Different execution times
        execution_times = {"A": 1.0, "B": 5.0, "C": 2.0, "D": 1.0}
        path = get_critical_path(dag, execution_times)
        
        # Should be A -> B -> D (longer path)
        assert path == ["A", "B", "D"]
    
    def test_validate_dependencies_valid(self, complex_stages):
        """Test validating valid dependencies."""
        errors = validate_dependencies(complex_stages)
        assert errors == []
    
    def test_validate_dependencies_missing(self):
        """Test detecting missing dependencies."""
        stages = [
            StageConfig(name="A", type=StageType.PROCESSOR, processor="a"),
            StageConfig(name="B", type=StageType.PROCESSOR, processor="b", dependencies=["C"])
        ]
        
        errors = validate_dependencies(stages)
        assert len(errors) == 1
        assert "unknown dependency 'C'" in errors[0]
    
    def test_validate_dependencies_self(self):
        """Test detecting self-dependency."""
        stages = [
            StageConfig(name="A", type=StageType.PROCESSOR, processor="a", dependencies=["A"])
        ]
        
        errors = validate_dependencies(stages)
        assert len(errors) == 1
        assert "depends on itself" in errors[0]
    
    def test_get_stage_depth(self, complex_stages):
        """Test calculating stage depth."""
        dag = build_dag(complex_stages)
        
        # Root nodes have depth 0
        assert get_stage_depth(dag, "A") == 0
        assert get_stage_depth(dag, "B") == 0
        
        # Direct children have depth 1
        assert get_stage_depth(dag, "C") == 1
        assert get_stage_depth(dag, "D") == 1
        
        # Further stages
        assert get_stage_depth(dag, "E") == 2
        assert get_stage_depth(dag, "F") == 3
        
        # Non-existent stage
        assert get_stage_depth(dag, "X") == -1
    
    def test_get_subgraph(self, complex_stages):
        """Test extracting subgraph."""
        dag = build_dag(complex_stages)
        
        # Get subgraph with specific nodes
        sub = get_subgraph(dag, {"A", "C", "E"})
        
        assert len(sub.nodes()) == 3
        assert "A" in sub.nodes()
        assert "C" in sub.nodes()
        assert "E" in sub.nodes()
        
        # Should preserve edges between selected nodes
        assert sub.has_edge("A", "C")
        assert sub.has_edge("C", "E")
        
        # Should not have edges to excluded nodes
        assert not sub.has_edge("A", "D")
    
    def test_analyze_dag_complexity(self, complex_stages):
        """Test DAG complexity analysis."""
        dag = build_dag(complex_stages)
        metrics = analyze_dag_complexity(dag)
        
        assert metrics['node_count'] == 6
        assert metrics['edge_count'] == 6
        assert metrics['is_connected'] is True
        assert metrics['max_in_degree'] == 2  # E has 2 inputs
        assert metrics['max_out_degree'] == 2  # A has 2 outputs
        assert metrics['avg_degree'] > 0
        assert metrics['parallel_groups'] >= 3
        assert metrics['longest_path_length'] == 4  # A->C->E->F or B->D->E->F
    
    def test_optimize_dag(self):
        """Test DAG optimization (transitive reduction)."""
        # Create DAG with redundant edge
        stages = [
            StageConfig(name="A", type=StageType.PROCESSOR, processor="a"),
            StageConfig(name="B", type=StageType.PROCESSOR, processor="b", dependencies=["A"]),
            StageConfig(name="C", type=StageType.PROCESSOR, processor="c", dependencies=["A", "B"])
        ]
        
        dag = build_dag(stages)
        
        # Original has redundant edge A->C (implied by A->B->C)
        assert dag.has_edge("A", "C")
        
        # Optimize
        optimized = optimize_dag(dag)
        
        # Should remove redundant edge
        assert not optimized.has_edge("A", "C")
        assert optimized.has_edge("A", "B")
        assert optimized.has_edge("B", "C")
        
        # Should preserve node attributes
        for node in dag.nodes():
            assert node in optimized.nodes()
    
    def test_empty_dag(self):
        """Test handling empty DAG."""
        dag = build_dag([])
        
        assert len(dag.nodes()) == 0
        assert len(dag.edges()) == 0
        assert get_execution_order(dag) == []
        assert get_parallel_groups(dag) == []
    
    def test_single_node_dag(self):
        """Test single node DAG."""
        stages = [
            StageConfig(name="A", type=StageType.PROCESSOR, processor="a")
        ]
        
        dag = build_dag(stages)
        
        assert len(dag.nodes()) == 1
        assert len(dag.edges()) == 0
        assert get_execution_order(dag) == ["A"]
        assert get_parallel_groups(dag) == [{"A"}]
        assert get_stage_depth(dag, "A") == 0