"""Theme style inspection and debugging utility.

Provides tools for inspecting generated stylesheets and debugging theme issues.
"""

import argparse
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Import theme system components
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from torematrix.ui.themes.styles import StyleSheetGenerator, GenerationOptions
from torematrix.ui.themes.engine import ThemeEngine
from torematrix.ui.themes.compiler import ThemeCompiler, CompilationOptions
from torematrix.core.config import ConfigManager
from torematrix.core.events import EventBus


class StyleInspector:
    """Tool for inspecting and debugging theme stylesheets."""
    
    def __init__(self):
        """Initialize style inspector."""
        # Setup theme system
        self.event_bus = EventBus()
        self.config_manager = ConfigManager()
        self.theme_engine = ThemeEngine(self.config_manager, self.event_bus)
        self.stylesheet_generator = StyleSheetGenerator()
        self.theme_compiler = ThemeCompiler()
    
    def inspect_theme_stylesheet(self, theme_name: str) -> Dict[str, Any]:
        """Inspect generated stylesheet for a theme.
        
        Args:
            theme_name: Name of theme to inspect
            
        Returns:
            Inspection results
        """
        print(f"🔍 Inspecting stylesheet for theme: {theme_name}")
        
        try:
            # Load theme
            theme = self.theme_engine.load_theme(theme_name)
            
            # Generate stylesheet
            options = GenerationOptions(
                include_comments=True,
                validate_css=True
            )
            
            stylesheet = self.stylesheet_generator.generate_stylesheet(
                theme, 
                options=options
            )
            
            # Analyze stylesheet
            analysis = self._analyze_stylesheet(stylesheet)
            
            # Get generation metrics
            metrics = self.stylesheet_generator.get_generation_metrics(theme_name)
            
            results = {
                'theme_name': theme_name,
                'stylesheet_length': len(stylesheet),
                'analysis': analysis,
                'metrics': {
                    'generation_time': metrics.generation_time if metrics else None,
                    'output_size': metrics.output_size if metrics else None,
                    'rules_count': metrics.rules_count if metrics else None,
                    'variables_resolved': metrics.variables_resolved if metrics else None,
                } if metrics else None,
                'stylesheet_preview': stylesheet[:500] + '...' if len(stylesheet) > 500 else stylesheet
            }
            
            print(f"  📏 Stylesheet length: {len(stylesheet)} characters")
            print(f"  📊 Rules: {analysis['rules_count']}")
            print(f"  🎯 Selectors: {analysis['selectors_count']}")
            print(f"  🎨 Properties: {analysis['properties_count']}")
            
            return results
            
        except Exception as e:
            print(f"❌ Failed to inspect theme '{theme_name}': {e}")
            return {'error': str(e)}
    
    def _analyze_stylesheet(self, stylesheet: str) -> Dict[str, Any]:
        """Analyze stylesheet structure and content.
        
        Args:
            stylesheet: CSS stylesheet to analyze
            
        Returns:
            Analysis results
        """
        analysis = {
            'rules_count': 0,
            'selectors_count': 0,
            'properties_count': 0,
            'comments_count': 0,
            'selectors': [],
            'properties': {},
            'issues': [],
            'complexity_score': 0
        }
        
        # Count rules (opening braces)
        analysis['rules_count'] = stylesheet.count('{')
        
        # Count comments
        comments = re.findall(r'/\*.*?\*/', stylesheet, re.DOTALL)
        analysis['comments_count'] = len(comments)
        
        # Extract selectors and properties
        rules = re.findall(r'([^{]+)\s*\{([^}]+)\}', stylesheet, re.DOTALL)
        
        property_counts = {}
        all_selectors = []
        
        for selector_text, properties_text in rules:
            # Clean up selector
            selector = selector_text.strip()
            if selector:
                all_selectors.append(selector)
            
            # Count properties
            properties = [p.strip() for p in properties_text.split(';') if p.strip()]
            analysis['properties_count'] += len(properties)
            
            # Track property usage
            for prop in properties:
                if ':' in prop:
                    prop_name = prop.split(':')[0].strip()
                    property_counts[prop_name] = property_counts.get(prop_name, 0) + 1
        
        analysis['selectors_count'] = len(all_selectors)
        analysis['selectors'] = all_selectors[:20]  # First 20 selectors
        analysis['properties'] = property_counts
        
        # Calculate complexity score
        analysis['complexity_score'] = self._calculate_complexity_score(
            analysis['rules_count'],
            analysis['selectors_count'],
            analysis['properties_count']
        )
        
        # Find potential issues
        analysis['issues'] = self._find_stylesheet_issues(stylesheet)
        
        return analysis
    
    def _calculate_complexity_score(self, rules: int, selectors: int, properties: int) -> float:
        """Calculate stylesheet complexity score.
        
        Args:
            rules: Number of CSS rules
            selectors: Number of selectors
            properties: Number of properties
            
        Returns:
            Complexity score (0-100)
        """
        # Simple complexity calculation
        base_score = min(rules * 0.5 + selectors * 0.3 + properties * 0.1, 100)
        return round(base_score, 1)
    
    def _find_stylesheet_issues(self, stylesheet: str) -> List[Dict[str, str]]:
        """Find potential issues in stylesheet.
        
        Args:
            stylesheet: CSS to analyze
            
        Returns:
            List of issues found
        """
        issues = []
        
        # Check for duplicate selectors
        selectors = re.findall(r'([^{]+)\s*\{', stylesheet)
        selector_counts = {}
        for selector in selectors:
            clean_selector = selector.strip()
            if clean_selector:
                selector_counts[clean_selector] = selector_counts.get(clean_selector, 0) + 1
        
        duplicates = [sel for sel, count in selector_counts.items() if count > 1]
        if duplicates:
            issues.append({
                'type': 'duplicate_selectors',
                'severity': 'warning',
                'message': f"Found {len(duplicates)} duplicate selectors",
                'details': duplicates[:5]  # First 5 duplicates
            })
        
        # Check for empty rules
        empty_rules = re.findall(r'[^{]+\{\s*\}', stylesheet)
        if empty_rules:
            issues.append({
                'type': 'empty_rules',
                'severity': 'warning',
                'message': f"Found {len(empty_rules)} empty CSS rules"
            })
        
        # Check for very long selectors
        long_selectors = [sel for sel in selectors if len(sel.strip()) > 100]
        if long_selectors:
            issues.append({
                'type': 'long_selectors',
                'severity': 'info',
                'message': f"Found {len(long_selectors)} very long selectors (>100 chars)"
            })
        
        # Check for potential typos in common properties
        common_props = ['color', 'background', 'border', 'margin', 'padding', 'font']
        properties = re.findall(r'([a-z-]+)\s*:', stylesheet)
        
        for prop in properties:
            for common in common_props:
                if prop != common and self._similarity(prop, common) > 0.8:
                    issues.append({
                        'type': 'potential_typo',
                        'severity': 'warning',
                        'message': f"Potential typo: '{prop}' (did you mean '{common}'?)"
                    })
        
        return issues
    
    def _similarity(self, a: str, b: str) -> float:
        """Calculate string similarity (simple implementation)."""
        if not a or not b:
            return 0.0
        
        # Simple character-based similarity
        common_chars = set(a) & set(b)
        total_chars = set(a) | set(b)
        
        if not total_chars:
            return 1.0
        
        return len(common_chars) / len(total_chars)
    
    def compare_themes(self, theme_names: List[str]) -> Dict[str, Any]:
        """Compare stylesheets of multiple themes.
        
        Args:
            theme_names: List of theme names to compare
            
        Returns:
            Comparison results
        """
        print(f"🔄 Comparing {len(theme_names)} themes...")
        
        comparison = {
            'themes': {},
            'summary': {},
            'differences': []
        }
        
        # Inspect each theme
        for theme_name in theme_names:
            print(f"  🎨 Analyzing {theme_name}...")
            inspection = self.inspect_theme_stylesheet(theme_name)
            if 'error' not in inspection:
                comparison['themes'][theme_name] = inspection
        
        # Generate summary comparison
        if len(comparison['themes']) > 1:
            metrics = ['stylesheet_length', 'rules_count', 'selectors_count', 'properties_count']
            
            for metric in metrics:
                values = {}
                for theme_name, data in comparison['themes'].items():
                    if metric in data['analysis']:
                        values[theme_name] = data['analysis'][metric]
                    elif metric == 'stylesheet_length':
                        values[theme_name] = data['stylesheet_length']
                
                if values:
                    comparison['summary'][metric] = {
                        'min': min(values.values()),
                        'max': max(values.values()),
                        'avg': sum(values.values()) / len(values),
                        'themes': values
                    }
            
            # Find differences
            comparison['differences'] = self._find_theme_differences(comparison['themes'])
        
        return comparison
    
    def _find_theme_differences(self, themes_data: Dict[str, Dict]) -> List[Dict[str, Any]]:
        """Find notable differences between themes.
        
        Args:
            themes_data: Theme inspection data
            
        Returns:
            List of differences found
        """
        differences = []
        
        # Compare complexity scores
        complexity_scores = {}
        for theme_name, data in themes_data.items():
            complexity_scores[theme_name] = data['analysis']['complexity_score']
        
        if complexity_scores:
            min_complexity = min(complexity_scores.values())
            max_complexity = max(complexity_scores.values())
            
            if max_complexity - min_complexity > 20:  # Significant difference
                differences.append({
                    'type': 'complexity_difference',
                    'message': f"Large complexity difference: {min_complexity} to {max_complexity}",
                    'details': complexity_scores
                })
        
        # Compare stylesheet sizes
        sizes = {}
        for theme_name, data in themes_data.items():
            sizes[theme_name] = data['stylesheet_length']
        
        if sizes:
            min_size = min(sizes.values())
            max_size = max(sizes.values())
            
            if max_size > min_size * 2:  # One theme is 2x larger
                differences.append({
                    'type': 'size_difference',
                    'message': f"Large size difference: {min_size} to {max_size} characters",
                    'details': sizes
                })
        
        return differences
    
    def validate_theme_css(self, theme_name: str) -> Dict[str, Any]:
        """Validate theme CSS syntax and structure.
        
        Args:
            theme_name: Name of theme to validate
            
        Returns:
            Validation results
        """
        print(f"✅ Validating CSS for theme: {theme_name}")
        
        try:
            # Load theme
            theme = self.theme_engine.load_theme(theme_name)
            
            # Generate stylesheet with validation
            options = GenerationOptions(validate_css=True)
            stylesheet = self.stylesheet_generator.generate_stylesheet(theme, options=options)
            
            # Perform additional validation
            validation_results = {
                'theme_name': theme_name,
                'valid': True,
                'errors': [],
                'warnings': [],
                'suggestions': []
            }
            
            # Check for balanced braces
            open_braces = stylesheet.count('{')
            close_braces = stylesheet.count('}')
            
            if open_braces != close_braces:
                validation_results['valid'] = False
                validation_results['errors'].append(
                    f"Unbalanced braces: {open_braces} opening, {close_braces} closing"
                )
            
            # Check for common CSS issues
            if ';;' in stylesheet:
                validation_results['warnings'].append("Double semicolons found")
            
            if ':;' in stylesheet:
                validation_results['warnings'].append("Empty property values found")
            
            # Check for missing semicolons (simple check)
            rules = re.findall(r'\{([^}]+)\}', stylesheet)
            for rule in rules:
                properties = [p.strip() for p in rule.split(';') if p.strip()]
                for prop in properties:
                    if ':' in prop and not prop.endswith(';') and prop != properties[-1]:
                        validation_results['warnings'].append(
                            f"Potentially missing semicolon in: {prop[:50]}..."
                        )
                        break
            
            # Performance suggestions
            if len(stylesheet) > 50000:  # Large stylesheet
                validation_results['suggestions'].append(
                    "Consider splitting large stylesheet into components for better performance"
                )
            
            if stylesheet.count('!important') > 10:
                validation_results['suggestions'].append(
                    "High usage of !important detected - consider refactoring selectors"
                )
            
            print(f"  ✅ Valid: {validation_results['valid']}")
            print(f"  ❌ Errors: {len(validation_results['errors'])}")
            print(f"  ⚠️  Warnings: {len(validation_results['warnings'])}")
            print(f"  💡 Suggestions: {len(validation_results['suggestions'])}")
            
            return validation_results
            
        except Exception as e:
            print(f"❌ Validation failed for theme '{theme_name}': {e}")
            return {
                'theme_name': theme_name,
                'valid': False,
                'errors': [str(e)],
                'warnings': [],
                'suggestions': []
            }


def main():
    """Main entry point for style inspector CLI."""
    parser = argparse.ArgumentParser(
        description="Inspect and debug theme stylesheets"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Inspect command
    inspect_parser = subparsers.add_parser('inspect', help='Inspect theme stylesheet')
    inspect_parser.add_argument('theme_name', help='Theme name to inspect')
    inspect_parser.add_argument('--output', '-o', type=Path, help='Output file for results')
    
    # Compare command
    compare_parser = subparsers.add_parser('compare', help='Compare multiple themes')
    compare_parser.add_argument('themes', nargs='+', help='Theme names to compare')
    compare_parser.add_argument('--output', '-o', type=Path, help='Output file for comparison')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate theme CSS')
    validate_parser.add_argument('theme_name', help='Theme name to validate')
    validate_parser.add_argument('--output', '-o', type=Path, help='Output file for validation results')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    inspector = StyleInspector()
    
    try:
        if args.command == 'inspect':
            results = inspector.inspect_theme_stylesheet(args.theme_name)
            
            if args.output:
                import json
                with open(args.output, 'w') as f:
                    json.dump(results, f, indent=2)
                print(f"📄 Results saved to: {args.output}")
            else:
                import json
                print(f"\n🔍 Inspection Results:\n{json.dumps(results, indent=2)}")
        
        elif args.command == 'compare':
            results = inspector.compare_themes(args.themes)
            
            if args.output:
                import json
                with open(args.output, 'w') as f:
                    json.dump(results, f, indent=2)
                print(f"📄 Comparison saved to: {args.output}")
            else:
                import json
                print(f"\n🔄 Comparison Results:\n{json.dumps(results, indent=2)}")
        
        elif args.command == 'validate':
            results = inspector.validate_theme_css(args.theme_name)
            
            if args.output:
                import json
                with open(args.output, 'w') as f:
                    json.dump(results, f, indent=2)
                print(f"📄 Validation results saved to: {args.output}")
            else:
                import json
                print(f"\n✅ Validation Results:\n{json.dumps(results, indent=2)}")
        
    except Exception as e:
        print(f"❌ Inspector failed: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())