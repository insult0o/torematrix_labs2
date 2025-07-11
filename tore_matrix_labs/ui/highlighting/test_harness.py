#!/usr/bin/env python3
"""
Test Harness for TORE Matrix Labs Highlighting System
Automated testing system for highlighting accuracy and performance.
"""

import logging
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TestCase:
    """Individual test case for highlighting system."""
    name: str
    description: str
    text_content: str
    text_start: int
    text_end: int
    expected_boxes: int
    tolerance: float = 2.0  # pixels
    page: int = 1
    highlight_type: str = 'active_highlight'
    expected_accuracy: float = 0.95


@dataclass
class TestResult:
    """Result of a highlighting test."""
    test_case: TestCase
    success: bool
    accuracy: float
    actual_boxes: int
    execution_time: float
    error_message: Optional[str] = None
    coordinate_accuracy: Optional[float] = None
    visual_accuracy: Optional[float] = None


class HighlightingTestHarness:
    """Automated testing system for highlighting accuracy and performance."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Test configuration
        self.test_cases: List[TestCase] = []
        self.test_results: List[TestResult] = []
        
        # Performance benchmarks
        self.performance_targets = {
            'highlight_creation_time': 0.1,  # seconds
            'coordinate_mapping_time': 0.05,  # seconds
            'rendering_time': 0.1,  # seconds
            'accuracy_threshold': 0.95  # 95% accuracy
        }
        
        # Test data
        self._initialize_test_cases()
        
        self.logger.info("Highlighting test harness initialized")
    
    def _initialize_test_cases(self):
        """Initialize standard test cases."""
        try:
            # Basic test cases
            self.test_cases = [
                TestCase(
                    name="single_line_basic",
                    description="Basic single line highlight",
                    text_content="This is a simple single line text for testing.",
                    text_start=10,
                    text_end=16,  # "simple"
                    expected_boxes=1,
                    tolerance=2.0
                ),
                TestCase(
                    name="multi_line_paragraph",
                    description="Multi-line paragraph highlight",
                    text_content="This is a longer paragraph that spans multiple lines and should be highlighted with multiple boxes for proper rendering.",
                    text_start=20,
                    text_end=80,  # spans multiple lines
                    expected_boxes=2,
                    tolerance=3.0
                ),
                TestCase(
                    name="single_word",
                    description="Single word highlight",
                    text_content="The quick brown fox jumps over the lazy dog.",
                    text_start=16,
                    text_end=19,  # "fox"
                    expected_boxes=1,
                    tolerance=1.0
                ),
                TestCase(
                    name="special_characters",
                    description="Text with special characters",
                    text_content="Special chars: äöü, €, ñ, and symbols @#$%",
                    text_start=15,
                    text_end=18,  # "äöü"
                    expected_boxes=1,
                    tolerance=3.0
                ),
                TestCase(
                    name="long_selection",
                    description="Long text selection across multiple lines",
                    text_content="This is a very long text selection that definitely spans multiple lines and should create multiple highlight boxes. The highlighting system should handle this correctly with proper coordinate mapping and multi-box rendering.",
                    text_start=0,
                    text_end=100,  # Long selection
                    expected_boxes=3,
                    tolerance=4.0
                ),
                TestCase(
                    name="punctuation_heavy",
                    description="Text with heavy punctuation",
                    text_content="Hello, world! How are you? I'm fine, thanks. What about you?",
                    text_start=13,
                    text_end=25,  # "How are you?"
                    expected_boxes=1,
                    tolerance=2.0
                ),
                TestCase(
                    name="numbers_and_symbols",
                    description="Text with numbers and symbols",
                    text_content="Version 1.2.3 (build #456) - Released on 2024-01-15",
                    text_start=8,
                    text_end=21,  # "1.2.3 (build #456)"
                    expected_boxes=1,
                    tolerance=2.0
                ),
                TestCase(
                    name="edge_case_start",
                    description="Selection at the start of text",
                    text_content="Beginning of text selection test case",
                    text_start=0,
                    text_end=9,  # "Beginning"
                    expected_boxes=1,
                    tolerance=1.0
                ),
                TestCase(
                    name="edge_case_end",
                    description="Selection at the end of text",
                    text_content="This selection ends at the very end",
                    text_start=27,
                    text_end=36,  # "very end"
                    expected_boxes=1,
                    tolerance=1.0
                ),
                TestCase(
                    name="whitespace_handling",
                    description="Selection with whitespace",
                    text_content="Text   with   multiple   spaces   between   words",
                    text_start=7,
                    text_end=20,  # "with   multiple"
                    expected_boxes=1,
                    tolerance=2.0
                )
            ]
            
            self.logger.info(f"TEST_HARNESS: Initialized {len(self.test_cases)} test cases")
            
        except Exception as e:
            self.logger.error(f"TEST_HARNESS: Error initializing test cases: {e}")
    
    def run_accuracy_tests(self, highlighting_engine) -> Dict[str, Any]:
        """Run comprehensive accuracy tests on the highlighting engine."""
        try:
            self.logger.info("TEST_HARNESS: Starting accuracy tests")
            
            test_results = []
            start_time = time.time()
            
            for test_case in self.test_cases:
                result = self._run_single_test(test_case, highlighting_engine)
                test_results.append(result)
                
                # Log result
                if result.success:
                    self.logger.info(f"TEST_HARNESS: ✅ {test_case.name} - Accuracy: {result.accuracy:.3f}")
                else:
                    self.logger.warning(f"TEST_HARNESS: ❌ {test_case.name} - Failed: {result.error_message}")
            
            total_time = time.time() - start_time
            
            # Calculate overall statistics
            stats = self._calculate_test_statistics(test_results)
            stats['total_execution_time'] = total_time
            
            # Store results
            self.test_results = test_results
            
            self.logger.info(f"TEST_HARNESS: Completed accuracy tests in {total_time:.3f}s")
            return stats
            
        except Exception as e:
            self.logger.error(f"TEST_HARNESS: Error running accuracy tests: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _run_single_test(self, test_case: TestCase, highlighting_engine) -> TestResult:
        """Run a single test case."""
        try:
            start_time = time.time()
            
            # Create highlight
            highlight_id = highlighting_engine.highlight_text_range(
                test_case.text_start,
                test_case.text_end,
                test_case.highlight_type,
                test_case.page
            )
            
            execution_time = time.time() - start_time
            
            if not highlight_id:
                return TestResult(
                    test_case=test_case,
                    success=False,
                    accuracy=0.0,
                    actual_boxes=0,
                    execution_time=execution_time,
                    error_message="Failed to create highlight"
                )
            
            # Get highlight info
            highlight_info = highlighting_engine.get_highlight_info(highlight_id)
            
            if not highlight_info:
                return TestResult(
                    test_case=test_case,
                    success=False,
                    accuracy=0.0,
                    actual_boxes=0,
                    execution_time=execution_time,
                    error_message="Failed to get highlight info"
                )
            
            # Analyze results
            pdf_boxes = highlight_info.get('pdf_boxes', [])
            actual_boxes = len(pdf_boxes)
            
            # Calculate accuracy
            accuracy = self._calculate_accuracy(test_case, highlight_info)
            
            # Check if test passed
            success = (
                accuracy >= test_case.expected_accuracy and
                abs(actual_boxes - test_case.expected_boxes) <= 1 and
                execution_time <= self.performance_targets['highlight_creation_time']
            )
            
            # Clean up
            highlighting_engine.remove_highlight(highlight_id)
            
            return TestResult(
                test_case=test_case,
                success=success,
                accuracy=accuracy,
                actual_boxes=actual_boxes,
                execution_time=execution_time,
                coordinate_accuracy=self._calculate_coordinate_accuracy(test_case, pdf_boxes),
                visual_accuracy=self._calculate_visual_accuracy(test_case, pdf_boxes)
            )
            
        except Exception as e:
            return TestResult(
                test_case=test_case,
                success=False,
                accuracy=0.0,
                actual_boxes=0,
                execution_time=0.0,
                error_message=str(e)
            )
    
    def _calculate_accuracy(self, test_case: TestCase, highlight_info: Dict[str, Any]) -> float:
        """Calculate overall accuracy for a test case."""
        try:
            # Get PDF boxes
            pdf_boxes = highlight_info.get('pdf_boxes', [])
            
            if not pdf_boxes:
                return 0.0
            
            # Calculate different accuracy metrics
            box_count_accuracy = self._calculate_box_count_accuracy(test_case, pdf_boxes)
            coordinate_accuracy = self._calculate_coordinate_accuracy(test_case, pdf_boxes)
            visual_accuracy = self._calculate_visual_accuracy(test_case, pdf_boxes)
            
            # Weighted average
            overall_accuracy = (
                box_count_accuracy * 0.3 +
                coordinate_accuracy * 0.4 +
                visual_accuracy * 0.3
            )
            
            return min(1.0, max(0.0, overall_accuracy))
            
        except Exception as e:
            self.logger.error(f"TEST_HARNESS: Error calculating accuracy: {e}")
            return 0.0
    
    def _calculate_box_count_accuracy(self, test_case: TestCase, pdf_boxes: List[Dict[str, Any]]) -> float:
        """Calculate accuracy based on box count."""
        try:
            expected = test_case.expected_boxes
            actual = len(pdf_boxes)
            
            if expected == 0:
                return 1.0 if actual == 0 else 0.0
            
            # Allow for some tolerance in box count
            difference = abs(actual - expected)
            max_difference = max(1, expected * 0.2)  # 20% tolerance
            
            if difference <= max_difference:
                return 1.0 - (difference / max_difference) * 0.3
            else:
                return 0.0
            
        except Exception as e:
            self.logger.error(f"TEST_HARNESS: Error calculating box count accuracy: {e}")
            return 0.0
    
    def _calculate_coordinate_accuracy(self, test_case: TestCase, pdf_boxes: List[Dict[str, Any]]) -> float:
        """Calculate accuracy based on coordinate precision."""
        try:
            if not pdf_boxes:
                return 0.0
            
            # Check if coordinates are reasonable
            total_area = 0
            valid_boxes = 0
            
            for box in pdf_boxes:
                if 'width' in box and 'height' in box:
                    width = box['width']
                    height = box['height']
                    
                    # Check if dimensions are reasonable
                    if width > 0 and height > 0 and width < 1000 and height < 100:
                        total_area += width * height
                        valid_boxes += 1
            
            if valid_boxes == 0:
                return 0.0
            
            # Calculate accuracy based on valid boxes ratio
            box_validity = valid_boxes / len(pdf_boxes)
            
            # Check if total area is reasonable for the text length
            text_length = test_case.text_end - test_case.text_start
            expected_area = text_length * 8 * 12  # Rough estimate: 8px width, 12px height per char
            
            if total_area > 0:
                area_accuracy = min(1.0, expected_area / total_area)
                if area_accuracy < 0.1:  # Too different from expected
                    area_accuracy = 0.1
            else:
                area_accuracy = 0.0
            
            return (box_validity * 0.7 + area_accuracy * 0.3)
            
        except Exception as e:
            self.logger.error(f"TEST_HARNESS: Error calculating coordinate accuracy: {e}")
            return 0.0
    
    def _calculate_visual_accuracy(self, test_case: TestCase, pdf_boxes: List[Dict[str, Any]]) -> float:
        """Calculate accuracy based on visual appearance."""
        try:
            if not pdf_boxes:
                return 0.0
            
            # Check if boxes are properly positioned
            boxes_sorted = sorted(pdf_boxes, key=lambda b: (b.get('y', 0), b.get('x', 0)))
            
            # Check for reasonable spacing between boxes
            spacing_score = 1.0
            if len(boxes_sorted) > 1:
                for i in range(1, len(boxes_sorted)):
                    current = boxes_sorted[i]
                    previous = boxes_sorted[i-1]
                    
                    # Check if boxes are on same line or different lines
                    y_diff = abs(current.get('y', 0) - previous.get('y', 0))
                    
                    if y_diff < 5:  # Same line
                        x_diff = current.get('x', 0) - (previous.get('x', 0) + previous.get('width', 0))
                        # Expect small gap between boxes on same line
                        if x_diff < -10 or x_diff > 50:  # Too much overlap or gap
                            spacing_score *= 0.8
                    else:  # Different lines
                        # Check if Y difference is reasonable for line spacing
                        if y_diff < 8 or y_diff > 30:
                            spacing_score *= 0.9
            
            # Check for reasonable box dimensions
            dimension_score = 1.0
            for box in pdf_boxes:
                width = box.get('width', 0)
                height = box.get('height', 0)
                
                if width <= 0 or height <= 0:
                    dimension_score *= 0.5
                elif width > 500 or height > 50:  # Too large
                    dimension_score *= 0.7
                elif width < 5 or height < 8:  # Too small
                    dimension_score *= 0.8
            
            return (spacing_score * 0.6 + dimension_score * 0.4)
            
        except Exception as e:
            self.logger.error(f"TEST_HARNESS: Error calculating visual accuracy: {e}")
            return 0.0
    
    def _calculate_test_statistics(self, test_results: List[TestResult]) -> Dict[str, Any]:
        """Calculate overall test statistics."""
        try:
            if not test_results:
                return {'status': 'no_results'}
            
            total_tests = len(test_results)
            successful_tests = sum(1 for r in test_results if r.success)
            
            accuracies = [r.accuracy for r in test_results]
            execution_times = [r.execution_time for r in test_results]
            
            stats = {
                'status': 'completed',
                'total_tests': total_tests,
                'successful_tests': successful_tests,
                'failed_tests': total_tests - successful_tests,
                'success_rate': successful_tests / total_tests if total_tests > 0 else 0.0,
                'average_accuracy': sum(accuracies) / len(accuracies) if accuracies else 0.0,
                'min_accuracy': min(accuracies) if accuracies else 0.0,
                'max_accuracy': max(accuracies) if accuracies else 0.0,
                'average_execution_time': sum(execution_times) / len(execution_times) if execution_times else 0.0,
                'max_execution_time': max(execution_times) if execution_times else 0.0,
                'performance_targets': self.performance_targets,
                'test_timestamp': datetime.now().isoformat()
            }
            
            # Add performance assessment
            stats['performance_assessment'] = {
                'accuracy_meets_target': stats['average_accuracy'] >= self.performance_targets['accuracy_threshold'],
                'speed_meets_target': stats['average_execution_time'] <= self.performance_targets['highlight_creation_time'],
                'overall_grade': self._calculate_overall_grade(stats)
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"TEST_HARNESS: Error calculating statistics: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _calculate_overall_grade(self, stats: Dict[str, Any]) -> str:
        """Calculate overall grade for the test run."""
        try:
            success_rate = stats['success_rate']
            accuracy = stats['average_accuracy']
            
            if success_rate >= 0.95 and accuracy >= 0.95:
                return 'A'
            elif success_rate >= 0.90 and accuracy >= 0.90:
                return 'B'
            elif success_rate >= 0.80 and accuracy >= 0.80:
                return 'C'
            elif success_rate >= 0.70 and accuracy >= 0.70:
                return 'D'
            else:
                return 'F'
                
        except Exception as e:
            self.logger.error(f"TEST_HARNESS: Error calculating grade: {e}")
            return 'F'
    
    def run_performance_benchmarks(self, highlighting_engine) -> Dict[str, Any]:
        """Run performance benchmarks on the highlighting engine."""
        try:
            self.logger.info("TEST_HARNESS: Starting performance benchmarks")
            
            benchmarks = {}
            
            # Test coordinate mapping performance
            mapping_times = []
            for _ in range(10):
                start_time = time.time()
                # Simulate coordinate mapping
                if hasattr(highlighting_engine, 'coordinate_mapper'):
                    highlighting_engine.coordinate_mapper.map_text_to_pdf(0, 100, 1)
                mapping_times.append(time.time() - start_time)
            
            benchmarks['coordinate_mapping'] = {
                'average_time': sum(mapping_times) / len(mapping_times),
                'max_time': max(mapping_times),
                'meets_target': sum(mapping_times) / len(mapping_times) <= self.performance_targets['coordinate_mapping_time']
            }
            
            # Test highlight creation performance
            creation_times = []
            for i in range(5):
                start_time = time.time()
                highlight_id = highlighting_engine.highlight_text_range(i * 10, (i + 1) * 10)
                creation_times.append(time.time() - start_time)
                if highlight_id:
                    highlighting_engine.remove_highlight(highlight_id)
            
            benchmarks['highlight_creation'] = {
                'average_time': sum(creation_times) / len(creation_times),
                'max_time': max(creation_times),
                'meets_target': sum(creation_times) / len(creation_times) <= self.performance_targets['highlight_creation_time']
            }
            
            self.logger.info("TEST_HARNESS: Performance benchmarks completed")
            return benchmarks
            
        except Exception as e:
            self.logger.error(f"TEST_HARNESS: Error running performance benchmarks: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def add_custom_test_case(self, test_case: TestCase):
        """Add a custom test case."""
        self.test_cases.append(test_case)
        self.logger.info(f"TEST_HARNESS: Added custom test case '{test_case.name}'")
    
    def get_test_results(self) -> List[TestResult]:
        """Get all test results."""
        return self.test_results.copy()
    
    def generate_test_report(self) -> str:
        """Generate a detailed test report."""
        try:
            if not self.test_results:
                return "No test results available."
            
            report = "HIGHLIGHTING SYSTEM TEST REPORT\n"
            report += "=" * 50 + "\n\n"
            
            # Summary
            total_tests = len(self.test_results)
            successful_tests = sum(1 for r in self.test_results if r.success)
            
            report += f"Total Tests: {total_tests}\n"
            report += f"Successful: {successful_tests}\n"
            report += f"Failed: {total_tests - successful_tests}\n"
            report += f"Success Rate: {successful_tests / total_tests * 100:.1f}%\n\n"
            
            # Individual test results
            report += "INDIVIDUAL TEST RESULTS:\n"
            report += "-" * 30 + "\n"
            
            for result in self.test_results:
                status = "✅ PASS" if result.success else "❌ FAIL"
                report += f"{status} {result.test_case.name}\n"
                report += f"  Accuracy: {result.accuracy:.3f}\n"
                report += f"  Execution Time: {result.execution_time:.4f}s\n"
                report += f"  Boxes: {result.actual_boxes} (expected: {result.test_case.expected_boxes})\n"
                
                if result.error_message:
                    report += f"  Error: {result.error_message}\n"
                
                report += "\n"
            
            return report
            
        except Exception as e:
            self.logger.error(f"TEST_HARNESS: Error generating test report: {e}")
            return f"Error generating report: {e}"