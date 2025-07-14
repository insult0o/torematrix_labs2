/**
 * PDF.js Performance Optimization JavaScript Module
 * 
 * This module provides client-side performance optimizations for PDF.js
 * including lazy loading, memory management, and hardware acceleration.
 */

(function() {
    'use strict';

    // Performance optimization configuration
    let performanceConfig = {
        enableLazyLoading: true,
        enableMemoryManagement: true,
        enableHardwareAcceleration: true,
        maxPreloadPages: 5,
        memoryPressureThreshold: 0.8,
        renderQuality: 'medium',
        enableProgressiveRendering: true,
        maxConcurrentRenders: 3,
        cacheSize: 50 * 1024 * 1024, // 50MB default
        enableCompression: true
    };

    // Performance monitoring
    let performanceMetrics = {
        pageLoadTimes: [],
        renderTimes: [],
        memoryUsage: [],
        cacheHitRate: 0,
        cacheMissRate: 0,
        concurrentRenders: 0,
        totalPageLoads: 0,
        totalRenders: 0
    };

    // Memory management
    let memoryManager = {
        pageCache: new Map(),
        textCache: new Map(),
        imageCache: new Map(),
        currentMemoryUsage: 0,
        maxMemoryUsage: performanceConfig.cacheSize,
        
        addToCache: function(key, data, type = 'page') {
            const size = this.estimateSize(data);
            
            // Check if we need to evict
            if (this.currentMemoryUsage + size > this.maxMemoryUsage) {
                this.evictLRU(size);
            }
            
            const cache = this.getCache(type);
            cache.set(key, {
                data: data,
                size: size,
                timestamp: Date.now(),
                accessCount: 0
            });
            
            this.currentMemoryUsage += size;
        },
        
        getFromCache: function(key, type = 'page') {
            const cache = this.getCache(type);
            const entry = cache.get(key);
            
            if (entry) {
                entry.accessCount++;
                entry.timestamp = Date.now();
                return entry.data;
            }
            
            return null;
        },
        
        getCache: function(type) {
            switch (type) {
                case 'text': return this.textCache;
                case 'image': return this.imageCache;
                default: return this.pageCache;
            }
        },
        
        evictLRU: function(requiredSize) {
            const allCaches = [this.pageCache, this.textCache, this.imageCache];
            let entries = [];
            
            // Collect all entries with timestamps
            allCaches.forEach(cache => {
                cache.forEach((entry, key) => {
                    entries.push({
                        key: key,
                        cache: cache,
                        timestamp: entry.timestamp,
                        size: entry.size
                    });
                });
            });
            
            // Sort by timestamp (oldest first)
            entries.sort((a, b) => a.timestamp - b.timestamp);
            
            // Evict until we have enough space
            let freedMemory = 0;
            for (const entry of entries) {
                if (freedMemory >= requiredSize) break;
                
                entry.cache.delete(entry.key);
                freedMemory += entry.size;
                this.currentMemoryUsage -= entry.size;
            }
        },
        
        estimateSize: function(data) {
            if (typeof data === 'string') {
                return data.length * 2; // UTF-16 encoding
            } else if (data instanceof ArrayBuffer) {
                return data.byteLength;
            } else if (data instanceof ImageData) {
                return data.width * data.height * 4; // RGBA
            } else if (data && typeof data === 'object') {
                return JSON.stringify(data).length * 2;
            }
            return 1024; // Default estimate
        },
        
        getMemoryStats: function() {
            return {
                currentUsage: this.currentMemoryUsage,
                maxUsage: this.maxMemoryUsage,
                utilization: this.currentMemoryUsage / this.maxMemoryUsage,
                pageCacheSize: this.pageCache.size,
                textCacheSize: this.textCache.size,
                imageCacheSize: this.imageCache.size
            };
        }
    };

    // Lazy loading manager
    let lazyLoader = {
        loadedPages: new Set(),
        loadingPages: new Set(),
        preloadQueue: [],
        
        loadPage: function(pageNumber, priority = 'normal') {
            return new Promise((resolve, reject) => {
                if (this.loadedPages.has(pageNumber)) {
                    resolve(this.getPageFromCache(pageNumber));
                    return;
                }
                
                if (this.loadingPages.has(pageNumber)) {
                    // Already loading, wait for completion
                    this.waitForPageLoad(pageNumber).then(resolve).catch(reject);
                    return;
                }
                
                this.loadingPages.add(pageNumber);
                
                const startTime = performance.now();
                
                // Check cache first
                const cachedPage = memoryManager.getFromCache(`page_${pageNumber}`);
                if (cachedPage) {
                    this.loadedPages.add(pageNumber);
                    this.loadingPages.delete(pageNumber);
                    resolve(cachedPage);
                    return;
                }
                
                // Load page
                this.loadPageFromPDF(pageNumber).then(page => {
                    const loadTime = performance.now() - startTime;
                    
                    // Cache the page
                    memoryManager.addToCache(`page_${pageNumber}`, page, 'page');
                    
                    // Update metrics
                    performanceMetrics.pageLoadTimes.push(loadTime);
                    performanceMetrics.totalPageLoads++;
                    
                    // Notify performance monitoring
                    if (window.qtBridge) {
                        window.qtBridge.notifyPerformanceEvent('page_load', {
                            pageNumber: pageNumber,
                            loadTime: loadTime,
                            priority: priority
                        });
                    }
                    
                    this.loadedPages.add(pageNumber);
                    this.loadingPages.delete(pageNumber);
                    resolve(page);
                }).catch(error => {
                    this.loadingPages.delete(pageNumber);
                    reject(error);
                });
            });
        },
        
        loadPageFromPDF: function(pageNumber) {
            // This would integrate with PDF.js loading
            return new Promise((resolve, reject) => {
                // Simulate PDF.js page loading
                setTimeout(() => {
                    resolve({
                        pageNumber: pageNumber,
                        content: `Page ${pageNumber} content`,
                        rendered: false
                    });
                }, Math.random() * 100 + 50); // 50-150ms simulation
            });
        },
        
        preloadPages: function(currentPage, direction = 'forward') {
            if (!performanceConfig.enableLazyLoading) return;
            
            const preloadCount = Math.min(performanceConfig.maxPreloadPages, 5);
            const pages = [];
            
            if (direction === 'forward') {
                for (let i = 1; i <= preloadCount; i++) {
                    pages.push(currentPage + i);
                }
            } else {
                for (let i = 1; i <= preloadCount; i++) {
                    pages.push(currentPage - i);
                }
            }
            
            pages.forEach(pageNumber => {
                if (pageNumber > 0 && !this.loadedPages.has(pageNumber)) {
                    this.preloadQueue.push(pageNumber);
                }
            });
            
            this.processPreloadQueue();
        },
        
        processPreloadQueue: function() {
            if (this.preloadQueue.length === 0) return;
            
            const pageNumber = this.preloadQueue.shift();
            this.loadPage(pageNumber, 'preload').then(() => {
                // Continue processing queue
                setTimeout(() => this.processPreloadQueue(), 10);
            }).catch(() => {
                // Continue on error
                setTimeout(() => this.processPreloadQueue(), 10);
            });
        },
        
        waitForPageLoad: function(pageNumber) {
            return new Promise((resolve) => {
                const checkInterval = setInterval(() => {
                    if (this.loadedPages.has(pageNumber)) {
                        clearInterval(checkInterval);
                        resolve(this.getPageFromCache(pageNumber));
                    }
                }, 10);
            });
        },
        
        getPageFromCache: function(pageNumber) {
            return memoryManager.getFromCache(`page_${pageNumber}`);
        }
    };

    // Progressive rendering
    let progressiveRenderer = {
        renderQueue: [],
        activeRenders: 0,
        maxConcurrentRenders: performanceConfig.maxConcurrentRenders,
        
        renderPage: function(pageNumber, quality = 'medium') {
            return new Promise((resolve, reject) => {
                if (this.activeRenders >= this.maxConcurrentRenders) {
                    this.renderQueue.push({ pageNumber, quality, resolve, reject });
                    return;
                }
                
                this.executeRender(pageNumber, quality).then(resolve).catch(reject);
            });
        },
        
        executeRender: function(pageNumber, quality) {
            return new Promise((resolve, reject) => {
                this.activeRenders++;
                performanceMetrics.concurrentRenders = this.activeRenders;
                
                const startTime = performance.now();
                
                // Check for cached render
                const cacheKey = `render_${pageNumber}_${quality}`;
                const cachedRender = memoryManager.getFromCache(cacheKey, 'page');
                
                if (cachedRender) {
                    this.activeRenders--;
                    this.processRenderQueue();
                    resolve(cachedRender);
                    return;
                }
                
                // Simulate rendering based on quality
                const renderTime = this.estimateRenderTime(quality);
                
                setTimeout(() => {
                    const actualRenderTime = performance.now() - startTime;
                    
                    // Create render result
                    const renderResult = {
                        pageNumber: pageNumber,
                        quality: quality,
                        renderTime: actualRenderTime,
                        canvas: this.createCanvas(pageNumber, quality)
                    };
                    
                    // Cache the render
                    memoryManager.addToCache(cacheKey, renderResult, 'page');
                    
                    // Update metrics
                    performanceMetrics.renderTimes.push(actualRenderTime);
                    performanceMetrics.totalRenders++;
                    
                    // Notify performance monitoring
                    if (window.qtBridge) {
                        window.qtBridge.notifyPerformanceEvent('page_render', {
                            pageNumber: pageNumber,
                            renderTime: actualRenderTime,
                            quality: quality,
                            concurrentRenders: this.activeRenders
                        });
                    }
                    
                    this.activeRenders--;
                    this.processRenderQueue();
                    resolve(renderResult);
                }, renderTime);
            });
        },
        
        processRenderQueue: function() {
            if (this.renderQueue.length === 0 || this.activeRenders >= this.maxConcurrentRenders) {
                return;
            }
            
            const next = this.renderQueue.shift();
            this.executeRender(next.pageNumber, next.quality)
                .then(next.resolve)
                .catch(next.reject);
        },
        
        estimateRenderTime: function(quality) {
            switch (quality) {
                case 'low': return 50;
                case 'medium': return 100;
                case 'high': return 200;
                case 'lossless': return 300;
                default: return 100;
            }
        },
        
        createCanvas: function(pageNumber, quality) {
            // Simulate canvas creation
            return {
                width: quality === 'low' ? 800 : quality === 'medium' ? 1200 : 1600,
                height: quality === 'low' ? 600 : quality === 'medium' ? 900 : 1200,
                data: new Uint8Array(1024) // Simulated image data
            };
        }
    };

    // Hardware acceleration
    let hardwareAcceleration = {
        available: false,
        context: null,
        
        initialize: function() {
            if (!performanceConfig.enableHardwareAcceleration) return false;
            
            try {
                const canvas = document.createElement('canvas');
                this.context = canvas.getContext('webgl2') || canvas.getContext('webgl');
                this.available = !!this.context;
                
                if (this.available) {
                    this.setupGPUResources();
                }
                
                return this.available;
            } catch (error) {
                console.warn('Hardware acceleration initialization failed:', error);
                return false;
            }
        },
        
        setupGPUResources: function() {
            if (!this.context) return;
            
            // Set up shaders and buffers for PDF rendering
            // This is a simplified example
            const vertexShader = this.createShader(this.context.VERTEX_SHADER, `
                attribute vec2 a_position;
                attribute vec2 a_texCoord;
                varying vec2 v_texCoord;
                
                void main() {
                    gl_Position = vec4(a_position, 0, 1);
                    v_texCoord = a_texCoord;
                }
            `);
            
            const fragmentShader = this.createShader(this.context.FRAGMENT_SHADER, `
                precision mediump float;
                uniform sampler2D u_texture;
                varying vec2 v_texCoord;
                
                void main() {
                    gl_FragColor = texture2D(u_texture, v_texCoord);
                }
            `);
            
            this.program = this.createProgram(vertexShader, fragmentShader);
        },
        
        createShader: function(type, source) {
            const shader = this.context.createShader(type);
            this.context.shaderSource(shader, source);
            this.context.compileShader(shader);
            
            if (!this.context.getShaderParameter(shader, this.context.COMPILE_STATUS)) {
                console.error('Shader compilation error:', this.context.getShaderInfoLog(shader));
                this.context.deleteShader(shader);
                return null;
            }
            
            return shader;
        },
        
        createProgram: function(vertexShader, fragmentShader) {
            const program = this.context.createProgram();
            this.context.attachShader(program, vertexShader);
            this.context.attachShader(program, fragmentShader);
            this.context.linkProgram(program);
            
            if (!this.context.getProgramParameter(program, this.context.LINK_STATUS)) {
                console.error('Program linking error:', this.context.getProgramInfoLog(program));
                this.context.deleteProgram(program);
                return null;
            }
            
            return program;
        },
        
        renderWithGPU: function(pageData) {
            if (!this.available || !this.context) {
                return this.fallbackRender(pageData);
            }
            
            try {
                // GPU-accelerated rendering implementation
                const startTime = performance.now();
                
                // Simulate GPU rendering
                const result = this.performGPURendering(pageData);
                
                const renderTime = performance.now() - startTime;
                
                // Notify performance improvement
                if (window.qtBridge) {
                    window.qtBridge.notifyPerformanceEvent('gpu_render', {
                        renderTime: renderTime,
                        accelerated: true
                    });
                }
                
                return result;
            } catch (error) {
                console.warn('GPU rendering failed, falling back to CPU:', error);
                return this.fallbackRender(pageData);
            }
        },
        
        performGPURendering: function(pageData) {
            // Simulate GPU rendering
            return {
                canvas: this.createAcceleratedCanvas(pageData),
                accelerated: true,
                renderTime: 25 // Faster than CPU rendering
            };
        },
        
        createAcceleratedCanvas: function(pageData) {
            return {
                width: 1200,
                height: 900,
                data: new Uint8Array(1200 * 900 * 4), // RGBA
                accelerated: true
            };
        },
        
        fallbackRender: function(pageData) {
            return progressiveRenderer.createCanvas(pageData.pageNumber, 'medium');
        }
    };

    // Performance monitoring
    let performanceMonitor = {
        collectMetrics: function() {
            const memoryStats = memoryManager.getMemoryStats();
            const now = Date.now();
            
            const metrics = {
                timestamp: now,
                memory: {
                    usage: memoryStats.currentUsage,
                    utilization: memoryStats.utilization,
                    cacheSize: memoryStats.pageCacheSize + memoryStats.textCacheSize + memoryStats.imageCacheSize
                },
                performance: {
                    averageLoadTime: this.calculateAverage(performanceMetrics.pageLoadTimes),
                    averageRenderTime: this.calculateAverage(performanceMetrics.renderTimes),
                    totalPageLoads: performanceMetrics.totalPageLoads,
                    totalRenders: performanceMetrics.totalRenders,
                    concurrentRenders: performanceMetrics.concurrentRenders
                },
                hardware: {
                    accelerationAvailable: hardwareAcceleration.available,
                    accelerationEnabled: performanceConfig.enableHardwareAcceleration
                }
            };
            
            // Send to Qt bridge
            if (window.qtBridge) {
                window.qtBridge.notifyPerformanceEvent('metrics_collection', metrics);
            }
            
            return metrics;
        },
        
        calculateAverage: function(array) {
            if (array.length === 0) return 0;
            return array.reduce((a, b) => a + b, 0) / array.length;
        },
        
        startMonitoring: function(interval = 1000) {
            setInterval(() => {
                this.collectMetrics();
            }, interval);
        }
    };

    // Public API
    window.PDFPerformance = {
        // Configuration
        configure: function(config) {
            Object.assign(performanceConfig, config);
            
            // Update memory limits
            if (config.cacheSize) {
                memoryManager.maxMemoryUsage = config.cacheSize;
            }
            
            // Update concurrent renders
            if (config.maxConcurrentRenders) {
                progressiveRenderer.maxConcurrentRenders = config.maxConcurrentRenders;
            }
        },
        
        // Page loading
        loadPage: function(pageNumber, priority = 'normal') {
            return lazyLoader.loadPage(pageNumber, priority);
        },
        
        // Rendering
        renderPage: function(pageNumber, quality = 'medium') {
            return progressiveRenderer.renderPage(pageNumber, quality);
        },
        
        // Preloading
        preloadPages: function(currentPage, direction = 'forward') {
            lazyLoader.preloadPages(currentPage, direction);
        },
        
        // Memory management
        clearCache: function(type = 'all') {
            if (type === 'all') {
                memoryManager.pageCache.clear();
                memoryManager.textCache.clear();
                memoryManager.imageCache.clear();
                memoryManager.currentMemoryUsage = 0;
            } else {
                const cache = memoryManager.getCache(type);
                cache.clear();
            }
        },
        
        // Performance monitoring
        getMetrics: function() {
            return performanceMonitor.collectMetrics();
        },
        
        startMonitoring: function(interval = 1000) {
            performanceMonitor.startMonitoring(interval);
        },
        
        // Hardware acceleration
        enableHardwareAcceleration: function() {
            return hardwareAcceleration.initialize();
        },
        
        // Cache management
        getCacheStats: function() {
            return memoryManager.getMemoryStats();
        },
        
        // Optimization
        optimizeForLargePDF: function(documentSizeMB) {
            if (documentSizeMB > 100) {
                // Extreme optimization for very large PDFs
                this.configure({
                    maxPreloadPages: 2,
                    maxConcurrentRenders: 1,
                    renderQuality: 'low',
                    cacheSize: Math.max(50 * 1024 * 1024, documentSizeMB * 0.5 * 1024 * 1024)
                });
            } else if (documentSizeMB > 50) {
                // High optimization for large PDFs
                this.configure({
                    maxPreloadPages: 3,
                    maxConcurrentRenders: 2,
                    renderQuality: 'medium',
                    cacheSize: Math.max(100 * 1024 * 1024, documentSizeMB * 1024 * 1024)
                });
            }
        }
    };

    // Initialize hardware acceleration on load
    document.addEventListener('DOMContentLoaded', function() {
        if (performanceConfig.enableHardwareAcceleration) {
            hardwareAcceleration.initialize();
        }
    });

    // Start performance monitoring
    performanceMonitor.startMonitoring();

    console.log('PDF.js Performance Optimization Module loaded');
})();