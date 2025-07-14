/**
 * PDF.js Advanced Features Integration (Agent 4)
 * 
 * This module provides client-side JavaScript implementation for advanced
 * PDF features including search, annotations, text selection, and accessibility.
 * 
 * Features implemented:
 * - Full-text search with highlighting
 * - Text selection and clipboard integration
 * - Annotation rendering and interaction
 * - Print functionality
 * - Accessibility support
 */

// Global features manager
window.PDFFeatures = (function() {
    'use strict';
    
    // Feature modules
    let searchManager = null;
    let annotationManager = null;
    let textSelectionManager = null;
    let printManager = null;
    let accessibilityManager = null;
    
    // Configuration
    let config = {
        search: {
            enabled: true,
            highlightColor: '#ffff00',
            highlightOpacity: 0.5,
            maxResults: 1000,
            contextChars: 50
        },
        annotations: {
            enabled: true,
            interactionEnabled: true,
            overlayEnabled: true
        },
        textSelection: {
            enabled: true,
            clipboardEnabled: true,
            contextMenuEnabled: true
        },
        print: {
            enabled: true,
            previewEnabled: true,
            exportEnabled: true
        },
        accessibility: {
            enabled: true,
            screenReaderSupport: true,
            keyboardNavigation: true,
            highContrast: false
        }
    };
    
    // State management
    let isInitialized = false;
    let currentDocument = null;
    let features = {};
    
    /**
     * Initialize PDF features system
     */
    function initialize() {
        if (isInitialized) {
            console.log('PDFFeatures already initialized');
            return;
        }
        
        try {
            console.log('Initializing PDF Features...');
            
            // Initialize feature managers
            initializeSearch();
            initializeAnnotations();
            initializeTextSelection();
            initializePrint();
            initializeAccessibility();
            
            // Setup event listeners
            setupEventListeners();
            
            // Setup bridge communication
            setupBridgeCommunication();
            
            isInitialized = true;
            console.log('PDF Features initialized successfully');
            
            // Notify Qt bridge
            if (window.pdfBridge) {
                window.pdfBridge.bridge_ready();
            }
            
        } catch (error) {
            console.error('Failed to initialize PDF Features:', error);
        }
    }
    
    /**
     * Initialize search functionality
     */
    function initializeSearch() {
        searchManager = {
            currentQuery: null,
            searchResults: [],
            currentResultIndex: -1,
            highlights: [],
            
            search: function(query, options = {}) {
                const startTime = performance.now();
                
                try {
                    // Clear previous results
                    this.clearHighlights();
                    this.searchResults = [];
                    this.currentResultIndex = -1;
                    
                    // Validate query
                    if (!query || typeof query !== 'string') {
                        throw new Error('Invalid search query');
                    }
                    
                    this.currentQuery = query;
                    
                    // Get search options
                    const caseSensitive = options.case_sensitive || false;
                    const wholeWords = options.whole_words || false;
                    const regexEnabled = options.regex_enabled || false;
                    const maxResults = options.max_results || config.search.maxResults;
                    const contextChars = options.context_chars || config.search.contextChars;
                    
                    // Build search pattern
                    let searchPattern;
                    if (regexEnabled) {
                        searchPattern = new RegExp(query, caseSensitive ? 'g' : 'gi');
                    } else {
                        let escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                        if (wholeWords) {
                            escapedQuery = '\\b' + escapedQuery + '\\b';
                        }
                        searchPattern = new RegExp(escapedQuery, caseSensitive ? 'g' : 'gi');
                    }
                    
                    // Search through pages
                    const pageCount = PDFViewerApplication.pagesCount;
                    let totalResults = 0;
                    
                    for (let pageNum = 1; pageNum <= pageCount && totalResults < maxResults; pageNum++) {
                        const results = this.searchPage(pageNum, searchPattern, contextChars);
                        this.searchResults.push(...results);
                        totalResults += results.length;
                    }
                    
                    // Create highlights
                    this.createHighlights();
                    
                    // Calculate search time
                    const searchTime = performance.now() - startTime;
                    
                    // Report results
                    const resultData = {
                        type: 'search_results',
                        query: query,
                        results: this.searchResults.map(r => ({
                            page: r.page,
                            text: r.text,
                            start: r.start,
                            end: r.end,
                            coordinates: r.coordinates,
                            context_before: r.contextBefore,
                            context_after: r.contextAfter,
                            highlight_id: r.highlightId
                        })),
                        search_time_ms: searchTime
                    };
                    
                    // Send to Qt bridge
                    sendFeatureEvent('search', resultData);
                    
                    console.log(`Search completed: ${this.searchResults.length} results in ${searchTime.toFixed(1)}ms`);
                    
                } catch (error) {
                    console.error('Search failed:', error);
                    sendFeatureEvent('search', {
                        type: 'search_error',
                        error: error.message
                    });
                }
            },
            
            searchPage: function(pageNum, pattern, contextChars) {
                const results = [];
                
                try {
                    // Get page text content
                    const page = PDFViewerApplication.pdfViewer.getPageView(pageNum - 1);
                    if (!page || !page.textLayer) {
                        return results;
                    }
                    
                    // Get text content
                    const textContent = page.textLayer.textContent;
                    if (!textContent) {
                        return results;
                    }
                    
                    // Extract full text
                    let fullText = '';
                    let charToItemMap = [];
                    
                    for (let i = 0; i < textContent.items.length; i++) {
                        const item = textContent.items[i];
                        const itemText = item.str || '';
                        const startChar = fullText.length;
                        
                        fullText += itemText + ' ';
                        
                        // Map characters to text items for coordinate calculation
                        for (let j = 0; j < itemText.length; j++) {
                            charToItemMap.push({
                                itemIndex: i,
                                charIndex: j,
                                item: item
                            });
                        }
                        charToItemMap.push({ itemIndex: i, charIndex: itemText.length, item: item }); // Space
                    }
                    
                    // Find matches
                    let match;
                    while ((match = pattern.exec(fullText)) !== null) {
                        const matchText = match[0];
                        const start = match.index;
                        const end = start + matchText.length;
                        
                        // Get coordinates
                        const coordinates = this.getTextCoordinates(charToItemMap, start, end, pageNum);
                        
                        // Get context
                        const contextStart = Math.max(0, start - contextChars);
                        const contextEnd = Math.min(fullText.length, end + contextChars);
                        const contextBefore = fullText.substring(contextStart, start).trim();
                        const contextAfter = fullText.substring(end, contextEnd).trim();
                        
                        // Create result
                        const result = {
                            page: pageNum,
                            text: matchText,
                            start: start,
                            end: end,
                            coordinates: coordinates,
                            contextBefore: contextBefore,
                            contextAfter: contextAfter,
                            highlightId: `search-highlight-${pageNum}-${results.length}`
                        };
                        
                        results.push(result);
                        
                        // Prevent infinite loop with zero-width matches
                        if (match.index === pattern.lastIndex) {
                            pattern.lastIndex++;
                        }
                    }
                    
                } catch (error) {
                    console.error(`Error searching page ${pageNum}:`, error);
                }
                
                return results;
            },
            
            getTextCoordinates: function(charToItemMap, start, end, pageNum) {
                try {
                    if (start >= charToItemMap.length || end > charToItemMap.length) {
                        return { x: 0, y: 0, width: 0, height: 0 };
                    }
                    
                    const startItem = charToItemMap[start];
                    const endItem = charToItemMap[Math.min(end - 1, charToItemMap.length - 1)];
                    
                    if (!startItem || !endItem) {
                        return { x: 0, y: 0, width: 0, height: 0 };
                    }
                    
                    // Calculate approximate coordinates
                    const transform = startItem.item.transform;
                    const fontSize = Math.sqrt(transform[0] * transform[0] + transform[1] * transform[1]);
                    
                    return {
                        x: transform[4],
                        y: transform[5],
                        width: (end - start) * fontSize * 0.6, // Approximate character width
                        height: fontSize
                    };
                    
                } catch (error) {
                    console.error('Error calculating text coordinates:', error);
                    return { x: 0, y: 0, width: 0, height: 0 };
                }
            },
            
            createHighlights: function() {
                // Create visual highlights for search results
                this.searchResults.forEach((result, index) => {
                    try {
                        this.createHighlight(result, index);
                    } catch (error) {
                        console.error('Error creating highlight:', error);
                    }
                });
            },
            
            createHighlight: function(result, index) {
                const pageElement = document.querySelector(`[data-page-number="${result.page}"]`);
                if (!pageElement) {
                    return;
                }
                
                // Create highlight element
                const highlight = document.createElement('div');
                highlight.id = result.highlightId;
                highlight.className = 'search-highlight';
                highlight.style.position = 'absolute';
                highlight.style.backgroundColor = config.search.highlightColor;
                highlight.style.opacity = config.search.highlightOpacity;
                highlight.style.pointerEvents = 'none';
                highlight.style.zIndex = '1000';
                
                // Set position and size
                highlight.style.left = result.coordinates.x + 'px';
                highlight.style.top = result.coordinates.y + 'px';
                highlight.style.width = result.coordinates.width + 'px';
                highlight.style.height = result.coordinates.height + 'px';
                
                // Add to page
                pageElement.appendChild(highlight);
                this.highlights.push(highlight);
            },
            
            navigateToResult: function(index) {
                if (index < 0 || index >= this.searchResults.length) {
                    return;
                }
                
                this.currentResultIndex = index;
                const result = this.searchResults[index];
                
                // Navigate to page
                PDFViewerApplication.page = result.page;
                
                // Scroll to highlight
                const highlight = document.getElementById(result.highlightId);
                if (highlight) {
                    highlight.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
                
                // Send navigation event
                sendFeatureEvent('search', {
                    type: 'result_selected',
                    index: index,
                    result: result
                });
            },
            
            clearHighlights: function() {
                this.highlights.forEach(highlight => {
                    if (highlight.parentNode) {
                        highlight.parentNode.removeChild(highlight);
                    }
                });
                this.highlights = [];
            }
        };
        
        features.search = searchManager;
    }
    
    /**
     * Initialize annotation functionality
     */
    function initializeAnnotations() {
        annotationManager = {
            annotations: new Map(),
            overlays: new Map(),
            
            loadAnnotations: function() {
                try {
                    const annotations = [];
                    
                    // Get annotations from PDF.js
                    const pageCount = PDFViewerApplication.pagesCount;
                    for (let pageNum = 1; pageNum <= pageCount; pageNum++) {
                        const pageAnnotations = this.getPageAnnotations(pageNum);
                        annotations.push(...pageAnnotations);
                    }
                    
                    // Store annotations
                    annotations.forEach(ann => {
                        this.annotations.set(ann.id, ann);
                    });
                    
                    // Send to Qt bridge
                    sendFeatureEvent('annotations', {
                        type: 'annotations_loaded',
                        annotations: annotations
                    });
                    
                    console.log(`Loaded ${annotations.length} annotations`);
                    
                } catch (error) {
                    console.error('Failed to load annotations:', error);
                }
            },
            
            getPageAnnotations: function(pageNum) {
                const annotations = [];
                
                try {
                    const page = PDFViewerApplication.pdfViewer.getPageView(pageNum - 1);
                    if (!page || !page.annotationLayer) {
                        return annotations;
                    }
                    
                    // Get annotation elements
                    const annotationElements = page.annotationLayer.div.children;
                    
                    for (let i = 0; i < annotationElements.length; i++) {
                        const element = annotationElements[i];
                        const annotation = this.parseAnnotationElement(element, pageNum);
                        if (annotation) {
                            annotations.push(annotation);
                        }
                    }
                    
                } catch (error) {
                    console.error(`Error getting annotations for page ${pageNum}:`, error);
                }
                
                return annotations;
            },
            
            parseAnnotationElement: function(element, pageNum) {
                try {
                    const rect = element.getBoundingClientRect();
                    const id = element.id || `annotation-${pageNum}-${Date.now()}-${Math.random()}`;
                    
                    // Determine annotation type
                    let type = 'text';
                    if (element.classList.contains('linkAnnotation')) {
                        type = 'link';
                    } else if (element.classList.contains('highlightAnnotation')) {
                        type = 'highlight';
                    } else if (element.classList.contains('textAnnotation')) {
                        type = 'text';
                    }
                    
                    // Get content
                    const content = element.textContent || element.title || '';
                    
                    return {
                        id: id,
                        type: type,
                        coordinates: {
                            page: pageNum,
                            x: rect.left,
                            y: rect.top,
                            width: rect.width,
                            height: rect.height
                        },
                        content: content,
                        title: element.title || '',
                        author: '',
                        subject: '',
                        creation_date: null,
                        modification_date: null,
                        style: {
                            color: '#ffff00',
                            opacity: 0.5,
                            border_color: '#ff0000',
                            border_width: 1.0
                        },
                        state: 'normal',
                        visible: true,
                        interactive: true,
                        metadata: {}
                    };
                    
                } catch (error) {
                    console.error('Error parsing annotation element:', error);
                    return null;
                }
            },
            
            showAnnotation: function(annotationId) {
                const annotation = this.annotations.get(annotationId);
                if (!annotation) {
                    return;
                }
                
                // Show annotation overlay
                this.createAnnotationOverlay(annotation);
                annotation.visible = true;
            },
            
            hideAnnotation: function(annotationId) {
                const annotation = this.annotations.get(annotationId);
                if (!annotation) {
                    return;
                }
                
                // Hide annotation overlay
                this.removeAnnotationOverlay(annotationId);
                annotation.visible = false;
            },
            
            createAnnotationOverlay: function(annotation) {
                const pageElement = document.querySelector(`[data-page-number="${annotation.coordinates.page}"]`);
                if (!pageElement) {
                    return;
                }
                
                // Create overlay element
                const overlay = document.createElement('div');
                overlay.id = `annotation-overlay-${annotation.id}`;
                overlay.className = 'annotation-overlay';
                overlay.style.position = 'absolute';
                overlay.style.left = annotation.coordinates.x + 'px';
                overlay.style.top = annotation.coordinates.y + 'px';
                overlay.style.width = annotation.coordinates.width + 'px';
                overlay.style.height = annotation.coordinates.height + 'px';
                overlay.style.backgroundColor = annotation.style.color;
                overlay.style.opacity = annotation.style.opacity;
                overlay.style.border = `${annotation.style.border_width}px solid ${annotation.style.border_color}`;
                overlay.style.cursor = 'pointer';
                overlay.style.zIndex = '1001';
                
                // Add click handler
                overlay.addEventListener('click', () => {
                    this.handleAnnotationClick(annotation);
                });
                
                // Add hover handlers
                overlay.addEventListener('mouseenter', () => {
                    this.handleAnnotationHover(annotation, true);
                });
                
                overlay.addEventListener('mouseleave', () => {
                    this.handleAnnotationHover(annotation, false);
                });
                
                // Add to page
                pageElement.appendChild(overlay);
                this.overlays.set(annotation.id, overlay);
            },
            
            removeAnnotationOverlay: function(annotationId) {
                const overlay = this.overlays.get(annotationId);
                if (overlay && overlay.parentNode) {
                    overlay.parentNode.removeChild(overlay);
                    this.overlays.delete(annotationId);
                }
            },
            
            handleAnnotationClick: function(annotation) {
                sendFeatureEvent('annotations', {
                    type: 'annotation_clicked',
                    annotation_id: annotation.id,
                    annotation_data: annotation
                });
            },
            
            handleAnnotationHover: function(annotation, hovering) {
                sendFeatureEvent('annotations', {
                    type: 'annotation_hovered',
                    annotation_id: annotation.id,
                    hovering: hovering
                });
            }
        };
        
        features.annotations = annotationManager;
    }
    
    /**
     * Initialize text selection functionality
     */
    function initializeTextSelection() {
        textSelectionManager = {
            isSelecting: false,
            startCoords: null,
            endCoords: null,
            selectedText: '',
            
            enable: function() {
                document.addEventListener('mousedown', this.onMouseDown.bind(this));
                document.addEventListener('mouseup', this.onMouseUp.bind(this));
                document.addEventListener('keydown', this.onKeyDown.bind(this));
            },
            
            onMouseDown: function(event) {
                // Check if clicking on PDF content
                if (this.isOnPDFContent(event.target)) {
                    this.isSelecting = true;
                    this.startCoords = this.getCoordinates(event);
                }
            },
            
            onMouseUp: function(event) {
                if (this.isSelecting) {
                    this.endCoords = this.getCoordinates(event);
                    this.handleTextSelection();
                    this.isSelecting = false;
                }
            },
            
            onKeyDown: function(event) {
                // Handle Ctrl+C for copy
                if (event.ctrlKey && event.key === 'c') {
                    this.copySelectedText();
                }
            },
            
            isOnPDFContent: function(element) {
                // Check if element is part of PDF content
                return element.closest('.page') !== null;
            },
            
            getCoordinates: function(event) {
                const rect = event.target.getBoundingClientRect();
                return {
                    x: event.clientX - rect.left,
                    y: event.clientY - rect.top,
                    pageX: event.pageX,
                    pageY: event.pageY
                };
            },
            
            handleTextSelection: function() {
                try {
                    // Get selected text
                    const selection = window.getSelection();
                    this.selectedText = selection.toString();
                    
                    if (this.selectedText) {
                        // Send selection event
                        sendFeatureEvent('text_selection', {
                            type: 'text_selected',
                            text: this.selectedText,
                            coordinates: {
                                start: this.startCoords,
                                end: this.endCoords
                            }
                        });
                    }
                    
                } catch (error) {
                    console.error('Error handling text selection:', error);
                }
            },
            
            copySelectedText: function() {
                if (this.selectedText && navigator.clipboard) {
                    navigator.clipboard.writeText(this.selectedText).then(() => {
                        console.log('Text copied to clipboard');
                    }).catch(error => {
                        console.error('Failed to copy text:', error);
                    });
                }
            }
        };
        
        // Enable text selection
        textSelectionManager.enable();
        features.textSelection = textSelectionManager;
    }
    
    /**
     * Initialize print functionality
     */
    function initializePrint() {
        printManager = {
            printDocument: function(options = {}) {
                try {
                    const startTime = performance.now();
                    
                    // Use PDF.js print functionality
                    if (PDFViewerApplication.printService) {
                        PDFViewerApplication.printService.print();
                    } else {
                        window.print();
                    }
                    
                    const printTime = performance.now() - startTime;
                    
                    // Send print event
                    sendFeatureEvent('print', {
                        type: 'print_ready',
                        options: options,
                        preparation_time_ms: printTime
                    });
                    
                } catch (error) {
                    console.error('Print failed:', error);
                    sendFeatureEvent('print', {
                        type: 'print_error',
                        error: error.message
                    });
                }
            }
        };
        
        features.print = printManager;
    }
    
    /**
     * Initialize accessibility functionality
     */
    function initializeAccessibility() {
        accessibilityManager = {
            ariaAnnouncer: null,
            
            initialize: function() {
                this.createAriaAnnouncer();
                this.setupKeyboardNavigation();
                this.setupFocusManagement();
            },
            
            createAriaAnnouncer: function() {
                this.ariaAnnouncer = document.createElement('div');
                this.ariaAnnouncer.id = 'accessibility-announcer';
                this.ariaAnnouncer.setAttribute('aria-live', 'polite');
                this.ariaAnnouncer.setAttribute('aria-atomic', 'true');
                this.ariaAnnouncer.style.position = 'absolute';
                this.ariaAnnouncer.style.left = '-10000px';
                this.ariaAnnouncer.style.width = '1px';
                this.ariaAnnouncer.style.height = '1px';
                this.ariaAnnouncer.style.overflow = 'hidden';
                document.body.appendChild(this.ariaAnnouncer);
            },
            
            announce: function(message) {
                if (this.ariaAnnouncer) {
                    this.ariaAnnouncer.textContent = message;
                }
            },
            
            setupKeyboardNavigation: function() {
                document.addEventListener('keydown', (event) => {
                    if (event.ctrlKey) {
                        switch (event.key) {
                            case 'ArrowRight':
                                event.preventDefault();
                                this.nextPage();
                                break;
                            case 'ArrowLeft':
                                event.preventDefault();
                                this.previousPage();
                                break;
                            case 'Home':
                                event.preventDefault();
                                this.firstPage();
                                break;
                            case 'End':
                                event.preventDefault();
                                this.lastPage();
                                break;
                        }
                    }
                });
            },
            
            setupFocusManagement: function() {
                // Ensure PDF viewer is focusable
                const viewer = document.getElementById('viewer');
                if (viewer) {
                    viewer.setAttribute('tabindex', '0');
                    viewer.setAttribute('role', 'application');
                    viewer.setAttribute('aria-label', 'PDF Document Viewer');
                }
            },
            
            nextPage: function() {
                if (PDFViewerApplication.page < PDFViewerApplication.pagesCount) {
                    PDFViewerApplication.page++;
                    this.announce(`Page ${PDFViewerApplication.page} of ${PDFViewerApplication.pagesCount}`);
                }
            },
            
            previousPage: function() {
                if (PDFViewerApplication.page > 1) {
                    PDFViewerApplication.page--;
                    this.announce(`Page ${PDFViewerApplication.page} of ${PDFViewerApplication.pagesCount}`);
                }
            },
            
            firstPage: function() {
                PDFViewerApplication.page = 1;
                this.announce(`First page - Page 1 of ${PDFViewerApplication.pagesCount}`);
            },
            
            lastPage: function() {
                PDFViewerApplication.page = PDFViewerApplication.pagesCount;
                this.announce(`Last page - Page ${PDFViewerApplication.pagesCount} of ${PDFViewerApplication.pagesCount}`);
            }
        };
        
        // Initialize accessibility
        accessibilityManager.initialize();
        features.accessibility = accessibilityManager;
    }
    
    /**
     * Setup event listeners
     */
    function setupEventListeners() {
        // PDF.js event listeners
        document.addEventListener('pagesinit', function() {
            console.log('PDF pages initialized');
            // Auto-load annotations when pages are ready
            if (features.annotations) {
                features.annotations.loadAnnotations();
            }
        });
        
        document.addEventListener('pagerendered', function(event) {
            const pageNumber = event.detail.pageNumber;
            console.log(`Page ${pageNumber} rendered`);
            
            // Send render complete event
            sendFeatureEvent('annotations', {
                type: 'annotation_render_complete',
                page: pageNumber,
                render_time_ms: performance.now()
            });
        });
    }
    
    /**
     * Setup bridge communication
     */
    function setupBridgeCommunication() {
        // Message handler for Qt bridge
        window.handleBridgeMessage = function(message) {
            try {
                const data = typeof message === 'string' ? JSON.parse(message) : message;
                
                switch (data.type) {
                    case 'feature_command':
                        handleFeatureCommand(data);
                        break;
                    case 'performance_command':
                        handlePerformanceCommand(data);
                        break;
                    default:
                        console.log('Unknown bridge message type:', data.type);
                }
                
            } catch (error) {
                console.error('Error handling bridge message:', error);
            }
        };
    }
    
    /**
     * Handle feature commands from Qt
     */
    function handleFeatureCommand(data) {
        const feature = data.feature;
        const command = data.command;
        const parameters = data.data || {};
        
        try {
            switch (feature) {
                case 'search':
                    handleSearchCommand(command, parameters);
                    break;
                case 'annotations':
                    handleAnnotationCommand(command, parameters);
                    break;
                case 'text_selection':
                    handleTextSelectionCommand(command, parameters);
                    break;
                case 'print':
                    handlePrintCommand(command, parameters);
                    break;
                default:
                    console.log(`Unknown feature command: ${feature}.${command}`);
            }
            
        } catch (error) {
            console.error(`Error handling feature command ${feature}.${command}:`, error);
        }
    }
    
    /**
     * Handle search commands
     */
    function handleSearchCommand(command, parameters) {
        const search = features.search;
        if (!search) return;
        
        switch (command) {
            case 'find_text':
                search.search(parameters.query, parameters);
                break;
            case 'navigate_to_result':
                if (parameters.page) {
                    PDFViewerApplication.page = parameters.page;
                }
                break;
            case 'clear_highlights':
                search.clearHighlights();
                break;
        }
    }
    
    /**
     * Handle annotation commands
     */
    function handleAnnotationCommand(command, parameters) {
        const annotations = features.annotations;
        if (!annotations) return;
        
        switch (command) {
            case 'load_annotations':
                annotations.loadAnnotations();
                break;
            case 'show_annotation':
                if (parameters.annotation_id) {
                    annotations.showAnnotation(parameters.annotation_id);
                }
                break;
            case 'hide_annotation':
                if (parameters.annotation_id) {
                    annotations.hideAnnotation(parameters.annotation_id);
                }
                break;
        }
    }
    
    /**
     * Handle text selection commands
     */
    function handleTextSelectionCommand(command, parameters) {
        const textSelection = features.textSelection;
        if (!textSelection) return;
        
        switch (command) {
            case 'select_text':
                // Handle programmatic text selection
                break;
        }
    }
    
    /**
     * Handle print commands
     */
    function handlePrintCommand(command, parameters) {
        const print = features.print;
        if (!print) return;
        
        switch (command) {
            case 'print_document':
                print.printDocument(parameters);
                break;
        }
    }
    
    /**
     * Handle performance commands
     */
    function handlePerformanceCommand(data) {
        // Handle performance monitoring commands from Agent 3
        console.log('Performance command received:', data.command);
    }
    
    /**
     * Send feature event to Qt bridge
     */
    function sendFeatureEvent(feature, data) {
        if (window.pdfBridge && window.pdfBridge.on_feature_event) {
            const eventData = {
                feature: feature,
                data: data
            };
            window.pdfBridge.on_feature_event(JSON.stringify(eventData));
        }
    }
    
    /**
     * Get feature status
     */
    function getFeatureStatus() {
        return {
            initialized: isInitialized,
            features: Object.keys(features),
            config: config
        };
    }
    
    // Public API
    return {
        initialize: initialize,
        getFeatureStatus: getFeatureStatus,
        config: config,
        features: features
    };
})();

// Auto-initialize when PDF.js is ready
document.addEventListener('DOMContentLoaded', function() {
    // Wait for PDF.js to be available
    function checkPDFJS() {
        if (window.PDFViewerApplication && window.PDFViewerApplication.initialized) {
            console.log('PDF.js is ready, initializing features...');
            window.PDFFeatures.initialize();
        } else {
            setTimeout(checkPDFJS, 100);
        }
    }
    
    checkPDFJS();
});

// Export for global access
window.PDFFeatures = window.PDFFeatures;