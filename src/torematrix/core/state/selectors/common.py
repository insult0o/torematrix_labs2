"""
Common selectors for TORE Matrix application state.
"""

from typing import Any, Dict, List, Optional
from .base import create_selector, create_parametric_selector
from .factory import default_factory

# Basic state accessors
get_document = lambda state: state.get('document', {})
get_elements = lambda state: state.get('elements', [])
get_ui_state = lambda state: state.get('ui', {})
get_processing_state = lambda state: state.get('processing', {})
get_validation_state = lambda state: state.get('validation', {})

# Document selectors
get_document_metadata = create_selector(
    get_document,
    output_fn=lambda doc: doc.get('metadata', {}),
    name='get_document_metadata'
)

get_document_pages = create_selector(
    get_document,
    output_fn=lambda doc: doc.get('pages', []),
    name='get_document_pages'
)

get_current_page = create_selector(
    get_document,
    get_ui_state,
    output_fn=lambda doc, ui: ui.get('current_page', 0),
    name='get_current_page'
)

# Element selectors
get_element_count = create_selector(
    get_elements,
    output_fn=lambda elements: len(elements),
    name='get_element_count'
)

get_visible_elements = create_selector(
    get_elements,
    output_fn=lambda elements: [e for e in elements if e.get('visible', True)],
    name='get_visible_elements'
)

get_selected_elements = create_selector(
    get_elements,
    output_fn=lambda elements: [e for e in elements if e.get('selected', False)],
    name='get_selected_elements'
)

get_validated_elements = create_selector(
    get_elements,
    output_fn=lambda elements: [e for e in elements if e.get('validated', False)],
    name='get_validated_elements'
)

get_unvalidated_elements = create_selector(
    get_elements,
    output_fn=lambda elements: [e for e in elements if not e.get('validated', False)],
    name='get_unvalidated_elements'
)

# Element type selectors
get_text_elements = create_selector(
    get_elements,
    output_fn=lambda elements: [e for e in elements if e.get('type') == 'text'],
    name='get_text_elements'
)

get_table_elements = create_selector(
    get_elements,
    output_fn=lambda elements: [e for e in elements if e.get('type') == 'table'],
    name='get_table_elements'
)

get_image_elements = create_selector(
    get_elements,
    output_fn=lambda elements: [e for e in elements if e.get('type') == 'image'],
    name='get_image_elements'
)

# Parametric selectors for dynamic queries
get_elements_by_type = create_parametric_selector(
    get_elements,
    output_fn=lambda elements, element_type: [
        e for e in elements if e.get('type') == element_type
    ],
    name='get_elements_by_type'
)

get_elements_by_page = create_parametric_selector(
    get_elements,
    output_fn=lambda elements, page_num: [
        e for e in elements if e.get('page', 0) == page_num
    ],
    name='get_elements_by_page'
)

get_elements_by_status = create_parametric_selector(
    get_elements,
    output_fn=lambda elements, status: [
        e for e in elements if e.get('status') == status
    ],
    name='get_elements_by_status'
)

# Validation selectors
get_validation_status = create_selector(
    get_elements,
    output_fn=lambda elements: {
        'total': len(elements),
        'validated': len([e for e in elements if e.get('validated', False)]),
        'pending': len([e for e in elements if not e.get('validated', False)]),
        'errors': len([e for e in elements if e.get('validation_error')]),
        'warnings': len([e for e in elements if e.get('validation_warning')])
    },
    name='get_validation_status'
)

get_validation_progress = create_selector(
    get_validation_status,
    lambda status: (status['validated'] / status['total'] * 100) if status['total'] > 0 else 0,
    name='get_validation_progress'
)

get_elements_with_errors = create_selector(
    get_elements,
    lambda elements: [e for e in elements if e.get('validation_error')],
    name='get_elements_with_errors'
)

get_elements_with_warnings = create_selector(
    get_elements,
    lambda elements: [e for e in elements if e.get('validation_warning')],
    name='get_elements_with_warnings'
)

# Processing selectors
get_processing_status = create_selector(
    get_processing_state,
    lambda processing: processing.get('status', 'idle'),
    name='get_processing_status'
)

get_processing_progress = create_selector(
    get_processing_state,
    lambda processing: processing.get('progress', 0),
    name='get_processing_progress'
)

get_processing_errors = create_selector(
    get_processing_state,
    lambda processing: processing.get('errors', []),
    name='get_processing_errors'
)

# UI state selectors
get_selected_element_id = create_selector(
    get_ui_state,
    lambda ui: ui.get('selected_element_id'),
    name='get_selected_element_id'
)

get_selected_element = create_selector(
    get_elements,
    get_selected_element_id,
    lambda elements, element_id: next(
        (e for e in elements if e.get('id') == element_id),
        None
    ) if element_id else None,
    name='get_selected_element'
)

get_view_mode = create_selector(
    get_ui_state,
    lambda ui: ui.get('view_mode', 'document'),
    name='get_view_mode'
)

get_zoom_level = create_selector(
    get_ui_state,
    lambda ui: ui.get('zoom_level', 1.0),
    name='get_zoom_level'
)

get_sidebar_visible = create_selector(
    get_ui_state,
    lambda ui: ui.get('sidebar_visible', True),
    name='get_sidebar_visible'
)

# Complex computed selectors
get_page_elements = create_parametric_selector(
    get_elements,
    get_current_page,
    output_fn=lambda elements, current_page, target_page=None: [
        e for e in elements 
        if e.get('page', 0) == (target_page if target_page is not None else current_page)
    ],
    name='get_page_elements'
)

get_element_statistics = create_selector(
    get_elements,
    lambda elements: {
        'by_type': _count_by_field(elements, 'type'),
        'by_page': _count_by_field(elements, 'page'),
        'by_status': _count_by_field(elements, 'status'),
        'validation_stats': {
            'validated': len([e for e in elements if e.get('validated', False)]),
            'unvalidated': len([e for e in elements if not e.get('validated', False)]),
            'with_errors': len([e for e in elements if e.get('validation_error')]),
            'with_warnings': len([e for e in elements if e.get('validation_warning')])
        }
    },
    name='get_element_statistics'
)

get_search_results = create_parametric_selector(
    get_elements,
    output_fn=lambda elements, query: [
        e for e in elements
        if query.lower() in str(e.get('content', '')).lower()
    ] if query else [],
    name='get_search_results'
)

# Performance-optimized selectors for large datasets
get_visible_page_elements = create_selector(
    get_elements,
    get_current_page,
    get_ui_state,
    lambda elements, current_page, ui: [
        e for e in elements
        if (e.get('page', 0) == current_page and 
            e.get('visible', True) and
            _is_element_in_viewport(e, ui))
    ],
    name='get_visible_page_elements'
)

# Helper functions
def _count_by_field(items: List[Dict], field: str) -> Dict[Any, int]:
    """Count items grouped by field value."""
    counts = {}
    for item in items:
        value = item.get(field, 'unknown')
        counts[value] = counts.get(value, 0) + 1
    return counts

def _is_element_in_viewport(element: Dict, ui_state: Dict) -> bool:
    """Check if element is in current viewport (simplified)."""
    # This would be more complex in real implementation
    # considering scroll position, zoom level, etc.
    return True

# Export commonly used selectors
__all__ = [
    'get_document',
    'get_elements', 
    'get_ui_state',
    'get_processing_state',
    'get_validation_state',
    'get_document_metadata',
    'get_document_pages',
    'get_current_page',
    'get_element_count',
    'get_visible_elements',
    'get_selected_elements',
    'get_validated_elements',
    'get_unvalidated_elements',
    'get_text_elements',
    'get_table_elements',
    'get_image_elements',
    'get_elements_by_type',
    'get_elements_by_page',
    'get_elements_by_status',
    'get_validation_status',
    'get_validation_progress',
    'get_elements_with_errors',
    'get_elements_with_warnings',
    'get_processing_status',
    'get_processing_progress',
    'get_processing_errors',
    'get_selected_element_id',
    'get_selected_element',
    'get_view_mode',
    'get_zoom_level',
    'get_sidebar_visible',
    'get_page_elements',
    'get_element_statistics',
    'get_search_results',
    'get_visible_page_elements'
]