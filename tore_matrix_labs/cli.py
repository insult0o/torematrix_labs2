#!/usr/bin/env python3
"""
Command-line interface for TORE Matrix Labs.
"""

import click
import logging
import sys
from pathlib import Path
from typing import List, Optional

from .config.settings import Settings
from .config.logging_config import setup_logging
from .core.document_analyzer import DocumentAnalyzer
from .core.content_extractor import ContentExtractor
from .core.quality_assessor import QualityAssessor
from .core.document_processor import DocumentProcessor


@click.group()
@click.version_option(version="1.0.0")
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--config', '-c', type=click.Path(), help='Configuration file path')
@click.pass_context
def cli(ctx, verbose, config):
    """TORE Matrix Labs - AI Document Processing Pipeline"""
    # Setup logging
    log_level = logging.DEBUG if verbose else logging.INFO
    setup_logging(level=log_level)
    
    # Initialize settings
    settings = Settings(config_file=config) if config else Settings()
    
    # Store in context
    ctx.ensure_object(dict)
    ctx.obj['settings'] = settings
    ctx.obj['verbose'] = verbose


@cli.command()
@click.argument('input_files', nargs=-1, type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output directory')
@click.option('--format', '-f', 
              type=click.Choice(['json', 'jsonl', 'csv', 'txt']), 
              default='jsonl', help='Output format')
@click.option('--quality-threshold', '-q', type=float, default=0.8, 
              help='Minimum quality threshold')
@click.option('--extract-tables', is_flag=True, default=True, 
              help='Extract tables from documents')
@click.option('--extract-images', is_flag=True, default=True, 
              help='Extract images from documents')
@click.option('--post-process/--legacy', default=True,
              help='Enable comprehensive post-processing and quality assessment')
@click.pass_context
def process(ctx, input_files, output, format, quality_threshold, extract_tables, extract_images, post_process):
    """Process documents and extract content with enterprise-grade quality assessment."""
    settings = ctx.obj['settings']
    
    if not input_files:
        click.echo("Error: No input files specified.", err=True)
        sys.exit(1)
    
    # Setup output directory
    output_dir = Path(output) if output else Path.cwd() / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Update settings based on options
    settings.processing.quality_threshold = quality_threshold
    settings.processing.extract_tables = extract_tables
    settings.processing.extract_images = extract_images
    
    click.echo(f"Processing {len(input_files)} documents...")
    click.echo(f"Output directory: {output_dir}")
    click.echo(f"Quality threshold: {quality_threshold}")
    click.echo(f"Post-processing: {'Enabled' if post_process else 'Disabled'}")
    click.echo("-" * 50)
    
    if post_process:
        # Use enhanced document processor
        processor = DocumentProcessor(settings)
        
        if len(input_files) == 1:
            # Single document processing with detailed output
            result = processor.process_document(input_files[0])
            
            if result['success']:
                # Display detailed results
                summary = result['summary']
                click.echo(f"\n✅ Document processed successfully!")
                click.echo(f"📊 Quality Score: {summary['quality_metrics']['overall_score']:.2f} ({summary['quality_metrics']['quality_level']})")
                click.echo(f"⏱️  Processing Time: {summary['processing_metrics']['total_time']:.2f}s")
                click.echo(f"📄 Content: {summary['content_metrics']['text_elements']} text elements, {summary['content_metrics']['tables']} tables, {summary['content_metrics']['images']} images")
                click.echo(f"🔍 Issues: {summary['quality_metrics']['total_issues']} total ({summary['quality_metrics']['critical_issues']} critical)")
                click.echo(f"✅ Export Ready: {'Yes' if summary['validation_status']['export_ready'] else 'No'}")
                
                # Save comprehensive results
                output_file = output_dir / f"{Path(input_files[0]).stem}_complete.json"
                _save_enhanced_output(result, output_file, format)
                click.echo(f"📁 Results saved to: {output_file}")
                
                # Display recommendations
                if result['post_processing'].recommendations:
                    click.echo(f"\n💡 Recommendations:")
                    for rec in result['post_processing'].recommendations[:5]:  # Show top 5
                        click.echo(f"   • {rec}")
                
                # Display next steps
                if summary['next_steps']:
                    click.echo(f"\n🎯 Next Steps:")
                    for step in summary['next_steps']:
                        click.echo(f"   {step}")
            else:
                click.echo(f"❌ Processing failed: {result['error']}", err=True)
        else:
            # Batch processing
            batch_results = processor.process_batch(list(input_files), output_dir=str(output_dir))
            
            # Display batch summary
            summary = batch_results['summary']
            click.echo(f"\n📊 Batch Processing Summary:")
            click.echo(f"   Success Rate: {summary['success_rate']}")
            click.echo(f"   Average Quality: {summary['average_quality_score']:.2f}")
            click.echo(f"   Total Issues: {summary['total_issues_found']}")
            click.echo(f"   Export Ready: {summary['export_ready_documents']}")
            click.echo(f"   Total Time: {summary['total_processing_time']}")
            click.echo(f"   Avg Time/Doc: {summary['average_time_per_document']}")
    else:
        # Legacy processing mode
        _process_legacy_mode(settings, input_files, output_dir, format, quality_threshold)


def _process_legacy_mode(settings, input_files, output_dir, format, quality_threshold):
    """Legacy processing mode without post-processing."""
    # Initialize components
    analyzer = DocumentAnalyzer(settings)
    extractor = ContentExtractor(settings)
    assessor = QualityAssessor(settings)
    
    processed_count = 0
    
    for file_path in input_files:
        try:
            click.echo(f"Processing: {file_path}")
            
            # Analyze document
            analysis = analyzer.analyze_document(file_path)
            
            # Extract content
            content = extractor.extract_content(file_path, analysis.page_analyses)
            
            # Assess quality
            quality = assessor.assess_quality(content, analysis.page_analyses)
            
            # Check quality threshold
            if quality.overall_score < quality_threshold:
                click.echo(f"Warning: Document quality ({quality.overall_score:.2f}) below threshold ({quality_threshold})")
                if not click.confirm("Continue processing this document?"):
                    continue
            
            # Generate output
            output_file = output_dir / f"{Path(file_path).stem}.{format}"
            _save_output(content, quality, output_file, format)
            
            click.echo(f"✓ Processed: {file_path} -> {output_file}")
            processed_count += 1
            
        except Exception as e:
            click.echo(f"✗ Failed to process {file_path}: {str(e)}", err=True)
    
    click.echo(f"\nProcessed {processed_count}/{len(input_files)} documents successfully.")


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.pass_context
def analyze(ctx, input_file):
    """Analyze document structure and quality."""
    settings = ctx.obj['settings']
    
    # Initialize components
    analyzer = DocumentAnalyzer(settings)
    extractor = ContentExtractor(settings)
    assessor = QualityAssessor(settings)
    
    click.echo(f"Analyzing: {input_file}")
    
    try:
        # Analyze document
        analysis = analyzer.analyze_document(input_file)
        content = extractor.extract_content(input_file, analysis.page_analyses)
        quality = assessor.assess_quality(content, analysis.page_analyses)
        
        # Display results
        click.echo("\n=== Document Analysis ===")
        click.echo(f"Document Type: {analysis.document_type.value}")
        click.echo(f"Total Pages: {analysis.total_pages}")
        click.echo(f"Processing Time: {analysis.processing_time:.2f}s")
        click.echo(f"Overall Quality: {analysis.overall_quality.value}")
        
        click.echo("\n=== Content Summary ===")
        click.echo(f"Text Elements: {len(content.text_elements)}")
        click.echo(f"Tables: {len(content.tables)}")
        click.echo(f"Images: {len(content.images)}")
        click.echo(f"Quality Score: {quality.overall_score:.2f}")
        
        if quality.issues:
            click.echo(f"\n=== Quality Issues ({len(quality.issues)}) ===")
            for issue in quality.issues[:5]:  # Show first 5 issues
                click.echo(f"- {issue.severity.upper()}: {issue.description}")
            if len(quality.issues) > 5:
                click.echo(f"... and {len(quality.issues) - 5} more issues")
        
        if quality.recommendations:
            click.echo("\n=== Recommendations ===")
            for rec in quality.recommendations:
                click.echo(f"- {rec}")
                
    except Exception as e:
        click.echo(f"Error analyzing document: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--input-dir', '-i', type=click.Path(exists=True), 
              help='Input directory containing documents')
@click.option('--output-dir', '-o', type=click.Path(), 
              help='Output directory for processed files')
@click.option('--workers', '-w', type=int, default=4, 
              help='Number of parallel workers')
@click.pass_context
def batch(ctx, input_dir, output_dir, workers):
    """Process documents in batch mode."""
    settings = ctx.obj['settings']
    
    if not input_dir:
        click.echo("Error: Input directory required for batch processing.", err=True)
        sys.exit(1)
    
    input_path = Path(input_dir)
    output_path = Path(output_dir) if output_dir else Path.cwd() / "batch_output"
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Find all supported documents
    supported_extensions = ['.pdf', '.docx', '.odt', '.rtf']
    documents = []
    for ext in supported_extensions:
        documents.extend(input_path.glob(f"**/*{ext}"))
    
    if not documents:
        click.echo("No supported documents found in input directory.", err=True)
        sys.exit(1)
    
    click.echo(f"Found {len(documents)} documents for batch processing...")
    
    # Implement parallel processing for batch operations
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from .core.document_analyzer import DocumentAnalyzer
    from .core.content_extractor import ContentExtractor
    
    analyzer = DocumentAnalyzer(settings)
    extractor = ContentExtractor(settings)
    
    # Determine optimal number of worker threads
    max_workers = min(len(documents), 4)  # Limit to 4 for resource management
    click.echo(f"Using {max_workers} parallel workers for batch processing...")
    
    def process_document_batch(doc_path):
        """Process a single document in the batch."""
        try:
            # Process document
            analysis = analyzer.analyze_document(str(doc_path))
            content = extractor.extract_content(str(doc_path), analysis.page_analyses)
            
            # Save output
            output_file = output_path / f"{doc_path.stem}.jsonl"
            _save_output(content, None, output_file, 'jsonl')
            return True, doc_path.name
            
        except Exception as e:
            return False, f"{doc_path.name}: {str(e)}"
    
    # Process documents in parallel
    processed = 0
    failed = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all documents for processing
        future_to_doc = {executor.submit(process_document_batch, doc): doc for doc in documents}
        
        # Process results as they complete
        with click.progressbar(length=len(documents), label="Processing documents") as bar:
            for future in as_completed(future_to_doc):
                doc_path = future_to_doc[future]
                try:
                    success, result = future.result()
                    if success:
                        processed += 1
                    else:
                        failed += 1
                        click.echo(f"\nError: {result}", err=True)
                except Exception as e:
                    failed += 1
                    click.echo(f"\nUnexpected error processing {doc_path}: {str(e)}", err=True)
                
                bar.update(1)
    
    click.echo(f"\nParallel batch processing complete:")
    click.echo(f"  ✅ Successfully processed: {processed}/{len(documents)} documents")
    if failed > 0:
        click.echo(f"  ❌ Failed: {failed} documents")
    click.echo(f"  🚀 Used {max_workers} parallel workers for improved performance")


def _save_output(content, quality, output_file: Path, format: str):
    """Save extracted content to file."""
    import json
    
    # Prepare data for export
    data = {
        'metadata': content.metadata,
        'text_elements': [
            {
                'type': elem.element_type.value,
                'content': elem.content,
                'page': elem.page_number,
                'confidence': elem.confidence,
                'bbox': elem.bbox
            }
            for elem in content.text_elements
        ],
        'tables': [
            {
                'page': table.page_number,
                'data': table.data,
                'headers': table.headers,
                'confidence': table.confidence
            }
            for table in content.tables
        ],
        'images': [
            {
                'page': img.page_number,
                'format': img.format,
                'width': img.width,
                'height': img.height,
                'caption': img.caption
            }
            for img in content.images
        ]
    }
    
    if quality:
        data['quality'] = {
            'score': quality.overall_score,
            'level': quality.quality_level.value,
            'issues_count': len(quality.issues),
            'recommendations': quality.recommendations
        }
    
    # Save based on format
    if format == 'json':
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    elif format == 'jsonl':
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
            f.write('\n')
    
    elif format == 'txt':
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("=== EXTRACTED TEXT ===\n\n")
            for elem in content.text_elements:
                f.write(f"[Page {elem.page_number}] {elem.content}\n\n")
    
    elif format == 'csv':
        import csv
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['page', 'type', 'content', 'confidence'])
            for elem in content.text_elements:
                writer.writerow([elem.page_number, elem.element_type.value, 
                               elem.content, elem.confidence])


def _save_enhanced_output(result: dict, output_file: Path, format: str):
    """Save enhanced processing results with comprehensive details."""
    import json
    
    document = result['document']
    post_processing = result['post_processing']
    summary = result['summary']
    
    # Create comprehensive export data
    enhanced_data = {
        'document_info': summary['document_info'],
        'processing_summary': summary,
        'quality_assessment': {
            'overall_score': post_processing.quality_assessment.overall_score,
            'quality_level': post_processing.quality_assessment.quality_level.value,
            'metrics': post_processing.quality_assessment.metrics,
            'issues': [
                {
                    'type': issue.issue_type.value,
                    'severity': issue.severity,
                    'description': issue.description,
                    'location': issue.location,
                    'confidence': issue.confidence,
                    'suggested_fix': issue.suggested_fix
                }
                for issue in post_processing.quality_assessment.issues
            ],
            'recommendations': post_processing.quality_assessment.recommendations
        },
        'validation_result': {
            'state': post_processing.validation_result.state.value,
            'confidence': post_processing.validation_result.confidence,
            'issues_found': post_processing.validation_result.issues_found,
            'corrections_made': post_processing.validation_result.corrections_made
        },
        'content_optimization': post_processing.content_optimization,
        'extracted_content': {
            'text_elements': [
                {
                    'type': elem.element_type.value,
                    'content': elem.content,
                    'page': elem.page_number,
                    'confidence': elem.confidence,
                    'bbox': elem.bbox
                }
                for elem in result['extracted_content'].text_elements
            ],
            'tables': [
                {
                    'page': table.page_number,
                    'data': table.data,
                    'headers': table.headers,
                    'confidence': table.confidence
                }
                for table in result['extracted_content'].tables
            ],
            'images': [
                {
                    'page': img.page_number,
                    'format': img.format,
                    'width': img.width,
                    'height': img.height,
                    'caption': img.caption
                }
                for img in result['extracted_content'].images
            ]
        },
        'export_ready': post_processing.export_ready,
        'recommendations': post_processing.recommendations,
        'metadata': post_processing.metadata
    }
    
    # Save based on format
    if format in ['json', 'jsonl']:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(enhanced_data, f, indent=2, ensure_ascii=False)
    elif format == 'txt':
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"Document Processing Report\n")
            f.write(f"========================\n\n")
            f.write(f"File: {summary['document_info']['file_name']}\n")
            f.write(f"Quality Score: {summary['quality_metrics']['overall_score']:.2f}\n")
            f.write(f"Quality Level: {summary['quality_metrics']['quality_level']}\n")
            f.write(f"Export Ready: {summary['validation_status']['export_ready']}\n\n")
            
            if post_processing.recommendations:
                f.write("Recommendations:\n")
                for i, rec in enumerate(post_processing.recommendations, 1):
                    f.write(f"{i}. {rec}\n")


@cli.command()
@click.option('--file', '-f', type=click.Path(exists=True), help='Project file to open (.tore)')
@click.pass_context
def gui(ctx, file):
    """Launch the graphical user interface."""
    try:
        # Import GUI components
        from .ui.main_window import MainWindow
        from .config.settings import Settings
        from .ui.qt_compat import QApplication
        import sys
        
        settings = ctx.obj['settings']
        
        # Create QApplication
        app = QApplication(sys.argv)
        
        # Create and show main window
        window = MainWindow(settings)
        window.show()
        
        # Load project file if specified
        if file:
            from pathlib import Path
            project_path = Path(file)
            if project_path.suffix == '.tore':
                click.echo(f"Loading project: {file}")
                window.project_widget.load_project(str(project_path))
            else:
                click.echo("Warning: File does not appear to be a .tore project file", err=True)
        
        # Start event loop
        sys.exit(app.exec_())
        
    except Exception as e:
        click.echo(f"Error launching GUI: {str(e)}", err=True)
        sys.exit(1)


def main():
    """CLI entry point."""
    cli()


if __name__ == "__main__":
    main()