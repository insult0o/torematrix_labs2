/**
 * PDF.js viewer integration for TORE Matrix Labs
 * Provides core PDF rendering and basic controls
 */

let pdfDoc = null;
let currentPage = 1;
let totalPages = 0;
let currentZoom = 1.0;
let renderTasks = [];
let documentMetadata = {};

// Initialize PDF.js
pdfjsLib.GlobalWorkerOptions.workerSrc = 'pdf.worker.min.js';

// Initialize viewer
document.addEventListener('DOMContentLoaded', function() {
    const viewer = document.getElementById('viewer');
    viewer.innerHTML = '<div class="loading">PDF viewer ready</div>';
    console.log('PDF.js viewer initialized');
});

/**
 * Load PDF from URL
 */
async function loadPDF(url) {
    try {
        console.log('Loading PDF:', url);
        
        // Show loading state
        const viewer = document.getElementById('viewer');
        viewer.innerHTML = '<div class="loading">Loading PDF...</div>';
        
        // Configure PDF.js loading parameters
        const loadingTask = pdfjsLib.getDocument({
            url: url,
            cMapUrl: 'cmaps/',
            cMapPacked: true,
            enableXfa: true,
            verbosity: 0  // Reduce console output
        });
        
        const pdf = await loadingTask.promise;
        pdfDoc = pdf;
        totalPages = pdf.numPages;
        currentPage = 1;
        
        // Get document metadata
        const metadata = await pdf.getMetadata();
        documentMetadata = {
            title: metadata.info?.Title || 'Untitled',
            author: metadata.info?.Author || 'Unknown',
            subject: metadata.info?.Subject || '',
            creator: metadata.info?.Creator || '',
            producer: metadata.info?.Producer || '',
            creationDate: metadata.info?.CreationDate || null,
            modificationDate: metadata.info?.ModDate || null,
            pages: totalPages
        };
        
        console.log('PDF loaded successfully:', {
            pages: totalPages,
            title: documentMetadata.title,
            author: documentMetadata.author
        });
        
        // Clear loading state
        viewer.innerHTML = '';
        
        // Render first page
        await renderPage(1);
        
        // Notify Qt about successful load
        if (typeof qt !== 'undefined' && qt.webChannelTransport) {
            // Bridge communication will be added by Agent 2
        }
        
        return { 
            success: true, 
            pages: totalPages,
            metadata: documentMetadata
        };
        
    } catch (error) {
        console.error('Error loading PDF:', error);
        
        // Show error state
        const viewer = document.getElementById('viewer');
        viewer.innerHTML = `<div class="error">Error loading PDF: ${error.message}</div>`;
        
        return { 
            success: false, 
            error: error.message,
            errorType: error.name || 'PDFLoadError'
        };
    }
}

/**
 * Render specific page
 */
async function renderPage(pageNum) {
    if (!pdfDoc || pageNum < 1 || pageNum > totalPages) {
        console.warn('Invalid page number:', pageNum);
        return;
    }
    
    try {
        console.log('Rendering page:', pageNum);
        
        const page = await pdfDoc.getPage(pageNum);
        
        // Calculate viewport with current zoom
        const viewport = page.getViewport({ scale: currentZoom });
        
        // Create canvas
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        canvas.height = viewport.height;
        canvas.width = viewport.width;
        
        // Get viewer container
        const viewer = document.getElementById('viewer');
        
        // Clear existing page or find existing canvas
        const existingPage = viewer.querySelector(`[data-page="${pageNum}"]`);
        let pageDiv;
        
        if (existingPage) {
            // Update existing page
            pageDiv = existingPage;
            const existingCanvas = pageDiv.querySelector('canvas');
            if (existingCanvas) {
                existingCanvas.remove();
            }
        } else {
            // Create new page container
            pageDiv = document.createElement('div');
            pageDiv.className = 'page';
            pageDiv.setAttribute('data-page', pageNum);
            pageDiv.style.width = viewport.width + 'px';
            pageDiv.style.height = viewport.height + 'px';
            
            // Clear viewer if rendering page 1
            if (pageNum === 1) {
                viewer.innerHTML = '';
            }
            
            viewer.appendChild(pageDiv);
        }
        
        // Add canvas to page
        pageDiv.appendChild(canvas);
        
        // Set up render context
        const renderContext = {
            canvasContext: context,
            viewport: viewport,
            enableWebGL: true,
            renderInteractiveForms: true
        };
        
        // Cancel any existing render task for this page
        const existingTask = renderTasks.find(task => task.pageNum === pageNum);
        if (existingTask && existingTask.task) {
            existingTask.task.cancel();
        }
        
        // Start render task
        const renderTask = page.render(renderContext);
        renderTasks.push({ pageNum, task: renderTask });
        
        await renderTask.promise;
        
        // Remove completed task from array
        const taskIndex = renderTasks.findIndex(task => task.pageNum === pageNum);
        if (taskIndex >= 0) {
            renderTasks.splice(taskIndex, 1);
        }
        
        currentPage = pageNum;
        console.log('Page rendered successfully:', pageNum);
        
        // Scroll to page if needed
        if (pageNum !== 1) {
            pageDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
        
    } catch (error) {
        console.error('Error rendering page:', pageNum, error);
        
        // Show error for this page
        const viewer = document.getElementById('viewer');
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error';
        errorDiv.textContent = `Error rendering page ${pageNum}: ${error.message}`;
        viewer.appendChild(errorDiv);
    }
}

/**
 * Navigation functions
 */
function goToPage(pageNum) {
    if (pageNum >= 1 && pageNum <= totalPages) {
        renderPage(pageNum);
        return true;
    }
    return false;
}

function nextPage() {
    if (currentPage < totalPages) {
        return goToPage(currentPage + 1);
    }
    return false;
}

function prevPage() {
    if (currentPage > 1) {
        return goToPage(currentPage - 1);
    }
    return false;
}

function firstPage() {
    return goToPage(1);
}

function lastPage() {
    return goToPage(totalPages);
}

/**
 * Zoom functions
 */
function setZoom(zoom) {
    if (zoom < 0.1 || zoom > 10.0) {
        console.warn('Zoom level out of range:', zoom);
        return false;
    }
    
    currentZoom = zoom;
    
    // Re-render current page with new zoom
    renderPage(currentPage);
    
    console.log('Zoom set to:', zoom);
    return true;
}

function zoomIn() {
    const newZoom = currentZoom * 1.25;
    return setZoom(newZoom);
}

function zoomOut() {
    const newZoom = currentZoom / 1.25;
    return setZoom(newZoom);
}

function fitWidth() {
    if (!pdfDoc) return false;
    
    const container = document.getElementById('viewerContainer');
    const containerWidth = container.clientWidth - 40; // Account for margins
    
    pdfDoc.getPage(currentPage).then(page => {
        const viewport = page.getViewport({ scale: 1.0 });
        const scale = containerWidth / viewport.width;
        setZoom(scale);
    }).catch(error => {
        console.error('Error in fitWidth:', error);
    });
    
    return true;
}

function fitPage() {
    if (!pdfDoc) return false;
    
    const container = document.getElementById('viewerContainer');
    const containerWidth = container.clientWidth - 40;
    const containerHeight = container.clientHeight - 40;
    
    pdfDoc.getPage(currentPage).then(page => {
        const viewport = page.getViewport({ scale: 1.0 });
        const scaleX = containerWidth / viewport.width;
        const scaleY = containerHeight / viewport.height;
        const scale = Math.min(scaleX, scaleY);
        setZoom(scale);
    }).catch(error => {
        console.error('Error in fitPage:', error);
    });
    
    return true;
}

/**
 * Utility functions
 */
function getCurrentPageInfo() {
    return {
        currentPage: currentPage,
        totalPages: totalPages,
        zoom: currentZoom,
        document: documentMetadata
    };
}

function getDocumentInfo() {
    return {
        isLoaded: pdfDoc !== null,
        pages: totalPages,
        currentPage: currentPage,
        zoom: currentZoom,
        metadata: documentMetadata
    };
}

/**
 * Cleanup function
 */
function clearViewer() {
    console.log('Clearing viewer...');
    
    // Cancel all render tasks
    renderTasks.forEach(taskObj => {
        if (taskObj.task && typeof taskObj.task.cancel === 'function') {
            taskObj.task.cancel();
        }
    });
    renderTasks = [];
    
    // Clear viewer
    const viewer = document.getElementById('viewer');
    if (viewer) {
        viewer.innerHTML = '<div class="loading">PDF viewer ready</div>';
    }
    
    // Reset state
    pdfDoc = null;
    currentPage = 1;
    totalPages = 0;
    currentZoom = 1.0;
    documentMetadata = {};
    
    console.log('Viewer cleared');
}

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    if (!pdfDoc) return;
    
    switch(e.key) {
        case 'ArrowRight':
        case 'PageDown':
            nextPage();
            e.preventDefault();
            break;
        case 'ArrowLeft':
        case 'PageUp':
            prevPage();
            e.preventDefault();
            break;
        case 'Home':
            firstPage();
            e.preventDefault();
            break;
        case 'End':
            lastPage();
            e.preventDefault();
            break;
        case '+':
        case '=':
            if (e.ctrlKey) {
                zoomIn();
                e.preventDefault();
            }
            break;
        case '-':
            if (e.ctrlKey) {
                zoomOut();
                e.preventDefault();
            }
            break;
        case '0':
            if (e.ctrlKey) {
                fitWidth();
                e.preventDefault();
            }
            break;
        case '1':
            if (e.ctrlKey) {
                setZoom(1.0);
                e.preventDefault();
            }
            break;
    }
});

// Window resize handler
window.addEventListener('resize', function() {
    if (pdfDoc && currentPage) {
        // Debounce resize events
        clearTimeout(window.resizeTimeout);
        window.resizeTimeout = setTimeout(function() {
            // Re-render current page to adjust to new container size
            renderPage(currentPage);
        }, 100);
    }
});

// Error handling for PDF.js
window.addEventListener('error', function(e) {
    console.error('PDF.js error:', e.error);
});

console.log('PDF.js viewer initialized with enhanced features');