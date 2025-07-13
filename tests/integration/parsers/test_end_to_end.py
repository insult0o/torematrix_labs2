"""End-to-end integration tests for the complete parser system."""

import pytest
import asyncio
import time
from unittest.mock import Mock

from src.torematrix.core.processing.parsers.factory import ParserFactory
from src.torematrix.core.processing.parsers.integration.manager import ParserManager
from src.torematrix.core.processing.parsers.code import CodeParser
from src.torematrix.core.processing.parsers.table import TableParser
from src.torematrix.core.processing.parsers.image import ImageParser
from src.torematrix.core.processing.parsers.types import ProcessingHints


class TestEndToEndParsing:
    """End-to-end tests for the complete parsing system."""
    
    def setup_method(self):
        """Setup complete parser system."""
        # Clear any existing parsers
        ParserFactory.clear_all_parsers()
        
        # Register all parsers
        ParserFactory.register_parser('code', CodeParser)
        ParserFactory.register_parser('table', TableParser) 
        ParserFactory.register_parser('image', ImageParser)
        
        # Create manager with production-like settings
        self.manager = ParserManager({
            'max_concurrent': 5,
            'default_timeout': 30.0,
            'enable_caching': True,
            'enable_monitoring': True,
            'cache': {
                'max_size': 1000,
                'default_ttl': 300,
                'max_memory_mb': 50
            }
        })
    
    def teardown_method(self):
        """Cleanup after tests."""
        ParserFactory.clear_all_parsers()
    
    def create_element(self, element_type: str, text: str, metadata: dict = None):
        """Create mock element for testing."""
        element = Mock()
        element.type = element_type
        element.text = text
        element.metadata = metadata or {}
        return element
    
    @pytest.mark.asyncio
    async def test_complete_document_parsing(self):
        """Test parsing a complete document with multiple element types."""
        # Simulate a document with various elements
        elements = [
            # Code block
            self.create_element("CodeBlock", """
import numpy as np
import matplotlib.pyplot as plt

def analyze_data(data):
    \"\"\"Analyze numerical data and create visualization.\"\"\"
    mean_val = np.mean(data)
    std_val = np.std(data)
    
    plt.figure(figsize=(10, 6))
    plt.hist(data, bins=30, alpha=0.7)
    plt.axvline(mean_val, color='red', linestyle='--', label=f'Mean: {mean_val:.2f}')
    plt.legend()
    plt.title('Data Distribution')
    plt.show()
    
    return {
        'mean': mean_val,
        'std': std_val,
        'count': len(data)
    }

class DataProcessor:
    def __init__(self, config):
        self.config = config
        self.results = []
    
    def process(self, data_list):
        for data in data_list:
            result = analyze_data(data)
            self.results.append(result)
        return self.results
"""),
            
            # Table
            self.create_element("Table", """
| Metric | Q1 2023 | Q2 2023 | Q3 2023 | Q4 2023 |
|--------|---------|---------|---------|---------|
| Revenue | $125,000 | $132,000 | $145,000 | $158,000 |
| Customers | 1,250 | 1,380 | 1,520 | 1,680 |
| Growth Rate | 8.5% | 5.6% | 10.1% | 8.9% |
| Satisfaction | 4.2 | 4.3 | 4.5 | 4.6 |
"""),
            
            # Image/Figure
            self.create_element("Figure", """
Performance Dashboard - Q4 2023 Results
A comprehensive visualization showing revenue trends, customer acquisition metrics, and satisfaction scores across all business units.
"""),
            
            # Another code block (different language)
            self.create_element("CodeBlock", """
const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');

const app = express();
app.use(cors());
app.use(bodyParser.json());

// API endpoints
app.get('/api/metrics', async (req, res) => {
    try {
        const metrics = await getMetrics();
        res.json({
            success: true,
            data: metrics,
            timestamp: new Date().toISOString()
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

app.post('/api/analyze', async (req, res) => {
    const { data, options } = req.body;
    
    if (!data || !Array.isArray(data)) {
        return res.status(400).json({
            success: false,
            error: 'Invalid data format'
        });
    }
    
    try {
        const analysis = await performAnalysis(data, options);
        res.json({
            success: true,
            analysis: analysis
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});
"""),
            
            # Complex table
            self.create_element("Table", """
Department,Employee Count,Avg Salary,Budget 2024,Projects Active,Satisfaction
Engineering,45,$95000,$4275000,12,4.8
Marketing,18,$65000,$1170000,8,4.2
Sales,32,$75000,$2400000,15,4.5
Operations,22,$58000,$1276000,6,4.1
HR,8,$70000,$560000,3,4.3
Finance,12,$80000,$960000,4,4.4
""")
        ]
        
        # Parse all elements
        start_time = time.time()
        responses = await self.manager.parse_batch(elements)
        total_time = time.time() - start_time
        
        # Verify all parsing succeeded
        assert len(responses) == len(elements)
        assert all(response.success for response in responses), \
            f"Some parsing failed: {[r.error for r in responses if not r.success]}"
        
        # Verify correct parser selection
        parser_usage = [response.parser_used for response in responses]
        assert "CodeParser" in parser_usage  # Should parse code blocks
        assert "TableParser" in parser_usage  # Should parse tables
        assert "ImageParser" in parser_usage  # Should parse image
        
        # Verify performance
        assert total_time < 30.0  # Should complete within 30 seconds
        
        # Verify results quality
        for response in responses:
            assert response.result is not None
            assert response.result.metadata.confidence > 0.3  # Reasonable confidence
            assert response.processing_time < 10.0  # Individual parsing shouldn't be too slow
        
        # Check specific parsing results
        code_responses = [r for r in responses if r.parser_used == "CodeParser"]
        for code_response in code_responses:
            result = code_response.result
            assert result.data.get("language") in ["python", "javascript"]
            assert len(result.data.get("elements", {}).get("functions", [])) > 0
        
        table_responses = [r for r in responses if r.parser_used == "TableParser"]
        for table_response in table_responses:
            result = table_response.result
            assert result.data.get("rows", 0) > 0
            assert result.data.get("columns", 0) > 0
    
    @pytest.mark.asyncio
    async def test_caching_behavior(self):
        """Test caching behavior across multiple requests."""
        # Create a code element
        element = self.create_element("CodeBlock", """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n-1)

print(f"Fibonacci(10): {fibonacci(10)}")
print(f"Factorial(5): {factorial(5)}")
""")
        
        # First parse - should hit parser
        response1 = await self.manager.parse_element(element)
        assert response1.success
        assert not response1.cache_hit
        assert response1.processing_time > 0
        
        # Second parse - should hit cache
        response2 = await self.manager.parse_element(element)
        assert response2.success
        assert response2.cache_hit
        assert response2.processing_time < response1.processing_time
        
        # Verify cache statistics
        stats = self.manager.get_statistics()
        assert stats['cache_hits'] >= 1
        assert stats['cache_hit_rate'] > 0
    
    @pytest.mark.asyncio
    async def test_error_handling_and_fallbacks(self):
        """Test error handling and fallback mechanisms."""
        # Test with various challenging inputs
        challenging_elements = [
            # Empty content
            self.create_element("CodeBlock", ""),
            
            # Very short content
            self.create_element("Table", "x"),
            
            # Malformed table
            self.create_element("Table", "| A | B\n| 1 2 |\n 3 | 4 |"),
            
            # Ambiguous content
            self.create_element("CodeBlock", "hello world this could be code or text"),
            
            # Large content (but not too large to fail completely)
            self.create_element("CodeBlock", "# Comment line\n" * 1000 + "def test(): pass\n"),
        ]
        
        responses = await self.manager.parse_batch(challenging_elements)
        
        # Some should succeed (possibly with fallbacks), some might fail
        successful_responses = [r for r in responses if r.success]
        failed_responses = [r for r in responses if not r.success]
        
        # At least some should work (even if with fallbacks)
        assert len(successful_responses) > 0
        
        # Check if fallbacks were used
        fallback_responses = [r for r in successful_responses if "fallback" in r.parser_used.lower()]
        if fallback_responses:
            # Verify fallback responses have basic structure
            for response in fallback_responses:
                assert response.result is not None
                assert response.result.data is not None
    
    @pytest.mark.asyncio
    async def test_performance_under_load(self):
        """Test system performance under load."""
        # Create a mix of different element types
        elements = []
        
        # Add various code snippets
        code_snippets = [
            "def hello(): return 'world'",
            "function test() { return true; }",
            "SELECT * FROM users WHERE active = 1",
            "class Example { public void run() {} }",
            "import os\nprint(os.getcwd())"
        ]
        
        # Add table examples
        table_examples = [
            "| A | B |\n| 1 | 2 |",
            "Name,Age,City\nJohn,25,NYC\nJane,30,LA",
            "Product\tPrice\tStock\nLaptop\t$999\t15\nMouse\t$25\t100"
        ]
        
        # Add image examples
        image_examples = [
            "Company logo with blue background",
            "Chart showing quarterly growth trends",
            "User interface screenshot from mobile app"
        ]
        
        # Create elements (10 of each type = 30 total)
        for snippet in code_snippets * 2:
            elements.append(self.create_element("CodeBlock", snippet))
        
        for table in table_examples * 4:
            elements.append(self.create_element("Table", table))
        
        for image in image_examples * 4:
            elements.append(self.create_element("Image", image))
        
        # Shuffle for realistic processing order
        import random
        random.shuffle(elements)
        
        # Process with timing
        start_time = time.time()
        responses = await self.manager.parse_batch(elements)
        total_time = time.time() - start_time
        
        # Verify results
        assert len(responses) == len(elements)
        
        successful_count = sum(1 for r in responses if r.success)
        success_rate = successful_count / len(responses)
        
        # Should have high success rate
        assert success_rate > 0.8, f"Success rate too low: {success_rate:.2%}"
        
        # Should complete in reasonable time
        assert total_time < 60.0, f"Processing too slow: {total_time:.2f}s"
        
        # Average processing time per element should be reasonable
        avg_time = total_time / len(elements)
        assert avg_time < 2.0, f"Average time per element too high: {avg_time:.2f}s"
        
        # Verify statistics
        stats = self.manager.get_statistics()
        assert stats['total_requests'] >= len(elements)
        assert stats['success_rate'] > 0.8
        
        # Check that all parser types were used
        parser_usage = stats['parser_usage']
        assert len(parser_usage) > 1  # Multiple parsers should be used
    
    @pytest.mark.asyncio
    async def test_monitoring_and_alerting(self):
        """Test monitoring and alerting functionality."""
        # Enable detailed monitoring
        await self.manager.monitor.clear_alerts()
        
        # Process some elements to generate metrics
        elements = [
            self.create_element("CodeBlock", "def test(): pass"),
            self.create_element("Table", "| A | B |\n| 1 | 2 |"),
            self.create_element("Image", "test image")
        ]
        
        responses = await self.manager.parse_batch(elements)
        
        # Check monitoring data
        system_overview = await self.manager.monitor.get_system_overview()
        assert system_overview['total_requests'] > 0
        
        # Check parser-specific performance
        for response in responses:
            if response.success and response.parser_used != "cache":
                perf_data = await self.manager.monitor.get_parser_performance(response.parser_used)
                assert perf_data is not None
                assert perf_data['total_requests'] > 0
                assert 'timing' in perf_data
                assert 'success_rate' in perf_data
        
        # Check health status
        health = await self.manager.health_check()
        assert health['status'] in ['healthy', 'warning', 'degraded']
        assert 'parsers_registered' in health
        assert health['parsers_registered'] > 0
    
    @pytest.mark.asyncio
    async def test_production_scenarios(self):
        """Test realistic production scenarios."""
        # Scenario 1: Document analysis workflow
        document_elements = [
            # Document header/metadata
            self.create_element("Text", "Technical Report: Q4 Performance Analysis"),
            
            # Executive summary table
            self.create_element("Table", """
| Metric | Target | Actual | Variance |
|--------|--------|--------|----------|
| Revenue | $1.2M | $1.35M | +12.5% |
| Customers | 500 | 547 | +9.4% |
| Retention | 85% | 88% | +3.5% |
"""),
            
            # Code example from system
            self.create_element("CodeBlock", """
-- Database query for customer analysis
SELECT 
    c.customer_id,
    c.signup_date,
    COUNT(o.order_id) as total_orders,
    SUM(o.amount) as total_revenue,
    AVG(o.amount) as avg_order_value
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
WHERE c.signup_date >= '2023-01-01'
GROUP BY c.customer_id, c.signup_date
HAVING COUNT(o.order_id) > 0
ORDER BY total_revenue DESC
LIMIT 100;
"""),
            
            # Performance chart description
            self.create_element("Figure", """
Revenue Trend Chart (Monthly)
Shows exponential growth pattern from January to December 2023
Key inflection point in Q3 corresponding to product launch
Seasonal variations visible in retail segments
"""),
            
            # Configuration code
            self.create_element("CodeBlock", """
# Configuration for analytics pipeline
import yaml
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class DatabaseConfig:
    host: str
    port: int
    database: str
    username: str
    password: str
    
@dataclass
class AnalyticsConfig:
    database: DatabaseConfig
    refresh_interval: int = 3600
    retention_days: int = 90
    enable_cache: bool = True
    cache_size_mb: int = 512

def load_config(config_path: str) -> AnalyticsConfig:
    with open(config_path, 'r') as f:
        data = yaml.safe_load(f)
    
    db_config = DatabaseConfig(**data['database'])
    return AnalyticsConfig(
        database=db_config,
        **{k: v for k, v in data.items() if k != 'database'}
    )

# Usage
config = load_config('/etc/analytics/config.yaml')
print(f"Connecting to {config.database.host}:{config.database.port}")
""")
        ]
        
        # Process document
        start_time = time.time()
        responses = await self.manager.parse_batch(document_elements)
        processing_time = time.time() - start_time
        
        # Verify all elements processed successfully
        success_count = sum(1 for r in responses if r.success)
        assert success_count == len(document_elements), \
            f"Only {success_count}/{len(document_elements)} elements processed successfully"
        
        # Check processing efficiency
        assert processing_time < 20.0, f"Document processing too slow: {processing_time:.2f}s"
        
        # Verify quality of results
        for response in responses:
            if response.success:
                confidence = response.result.metadata.confidence
                assert confidence > 0.4, f"Low confidence result: {confidence:.2f}"
        
        # Check that appropriate parsers were selected
        parsers_used = {response.parser_used for response in responses if response.success}
        assert len(parsers_used) > 1, "Should use multiple different parsers"
        
        # Verify specific element parsing
        code_responses = [r for r in responses if r.parser_used == "CodeParser"]
        assert len(code_responses) >= 2, "Should find multiple code blocks"
        
        for code_response in code_responses:
            result = code_response.result
            language = result.data.get("language")
            assert language in ["sql", "python"], f"Unexpected language: {language}"
        
        table_responses = [r for r in responses if r.parser_used == "TableParser"]
        assert len(table_responses) >= 1, "Should find table"
        
        for table_response in table_responses:
            result = table_response.result
            assert result.data.get("rows", 0) > 0
            assert result.data.get("columns", 0) > 0
    
    @pytest.mark.asyncio
    async def test_system_limits_and_boundaries(self):
        """Test system behavior at limits and boundaries."""
        # Test very large input (but within limits)
        large_code = """
# Large Python module with many functions
import os, sys, json, time, datetime, re, math, random
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, field

""" + "\n".join([f"""
def function_{i}(param1, param2={i}):
    \"\"\"Function number {i} for testing.\"\"\"
    result = param1 * param2 + {i}
    if result > 100:
        return result // 2
    else:
        return result * 2
""" for i in range(50)])  # 50 functions
        
        large_element = self.create_element("CodeBlock", large_code)
        response = await self.manager.parse_element(large_element)
        
        # Should succeed but might take longer
        assert response.success, f"Large code parsing failed: {response.error}"
        assert response.result.data.get("language") == "python"
        assert len(response.result.data.get("elements", {}).get("functions", [])) >= 40
        
        # Test empty/minimal inputs
        minimal_elements = [
            self.create_element("CodeBlock", "x"),
            self.create_element("Table", "|"),
            self.create_element("Image", ".")
        ]
        
        responses = await self.manager.parse_batch(minimal_elements)
        
        # Should handle gracefully (success or controlled failure)
        for response in responses:
            if not response.success:
                # Failure should be controlled with meaningful error
                assert response.error is not None
                assert len(response.error) > 0
    
    @pytest.mark.asyncio 
    async def test_concurrent_access_safety(self):
        """Test thread safety and concurrent access."""
        # Create multiple concurrent parsing tasks
        async def parse_batch_task(task_id):
            elements = [
                self.create_element("CodeBlock", f"def task_{task_id}_func(): return {task_id}"),
                self.create_element("Table", f"| Task | ID |\n| {task_id} | {task_id} |"),
            ]
            return await self.manager.parse_batch(elements)
        
        # Run multiple tasks concurrently
        tasks = [parse_batch_task(i) for i in range(10)]
        all_responses = await asyncio.gather(*tasks)
        
        # Verify all tasks completed successfully
        for task_responses in all_responses:
            assert len(task_responses) == 2
            assert all(r.success for r in task_responses)
        
        # Verify system state is consistent
        stats = self.manager.get_statistics()
        assert stats['total_requests'] >= 20  # 10 tasks * 2 elements each
        
        # Check for any race conditions in statistics
        assert stats['total_requests'] == stats['successful_parses'] + stats['errors']