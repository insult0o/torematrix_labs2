# Caching and Incremental Processing System

## 🚀 Overview

Efficient caching and incremental processing are critical for maintaining performance in a document processing pipeline. This guide details the multi-level caching architecture and incremental processing strategies for TORE Matrix Labs V3.

## 🏗️ Multi-Level Cache Architecture

### Cache Hierarchy
```
┌─────────────────────────────────────────────┐
│          L1: Memory Cache (TTL)             │
│         Fast • Limited Size • Short TTL      │
├─────────────────────────────────────────────┤
│           L2: Local Disk Cache              │
│      Persistent • Larger • Medium Speed      │
├─────────────────────────────────────────────┤
│          L3: Distributed Cache              │
│     Redis/Memcached • Shared • Scalable     │
├─────────────────────────────────────────────┤
│         L4: Object Storage Cache            │
│      S3/Blob • Long-term • Large Files      │
└─────────────────────────────────────────────┘
```

### Implementation

```python
from typing import Optional, Any, Dict
from datetime import datetime, timedelta
import hashlib
import pickle
import json
from pathlib import Path
from cachetools import TTLCache
import redis
import diskcache

class MultiLevelCache:
    def __init__(self, config: CacheConfig):
        # L1: Memory cache with TTL
        self.memory_cache = TTLCache(
            maxsize=config.memory_cache_size,  # e.g., 1000 items
            ttl=config.memory_cache_ttl        # e.g., 3600 seconds
        )
        
        # L2: Disk cache
        self.disk_cache = diskcache.Cache(
            directory=config.disk_cache_path,
            size_limit=config.disk_cache_size   # e.g., 10GB
        )
        
        # L3: Redis cache (optional)
        self.redis_cache = None
        if config.use_redis:
            self.redis_cache = redis.Redis(
                host=config.redis_host,
                port=config.redis_port,
                db=config.redis_db,
                decode_responses=False  # Store binary data
            )
        
        # L4: Object storage (optional)
        self.object_storage = None
        if config.use_object_storage:
            self.object_storage = ObjectStorageCache(config.s3_config)
    
    def get(self, key: str, cache_levels: List[str] = None) -> Optional[Any]:
        """Get item from cache, checking each level"""
        if cache_levels is None:
            cache_levels = ['memory', 'disk', 'redis', 'object']
        
        # L1: Check memory cache
        if 'memory' in cache_levels:
            if value := self.memory_cache.get(key):
                self._log_cache_hit('memory', key)
                return value
        
        # L2: Check disk cache
        if 'disk' in cache_levels:
            if value := self.disk_cache.get(key):
                self._log_cache_hit('disk', key)
                # Promote to memory cache
                self.memory_cache[key] = value
                return value
        
        # L3: Check Redis
        if 'redis' in cache_levels and self.redis_cache:
            if cached_data := self.redis_cache.get(key):
                value = pickle.loads(cached_data)
                self._log_cache_hit('redis', key)
                # Promote to faster caches
                self._promote_to_faster_caches(key, value, ['memory', 'disk'])
                return value
        
        # L4: Check object storage
        if 'object' in cache_levels and self.object_storage:
            if value := self.object_storage.get(key):
                self._log_cache_hit('object', key)
                # Promote to all faster caches
                self._promote_to_faster_caches(key, value, ['memory', 'disk', 'redis'])
                return value
        
        self._log_cache_miss(key)
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None,
            cache_levels: List[str] = None) -> None:
        """Set item in specified cache levels"""
        if cache_levels is None:
            cache_levels = self._determine_cache_levels(value)
        
        # L1: Memory cache
        if 'memory' in cache_levels:
            self.memory_cache[key] = value
        
        # L2: Disk cache
        if 'disk' in cache_levels:
            self.disk_cache.set(key, value, expire=ttl)
        
        # L3: Redis cache
        if 'redis' in cache_levels and self.redis_cache:
            serialized = pickle.dumps(value)
            if ttl:
                self.redis_cache.setex(key, ttl, serialized)
            else:
                self.redis_cache.set(key, serialized)
        
        # L4: Object storage (for large/long-term items)
        if 'object' in cache_levels and self.object_storage:
            self.object_storage.put(key, value, ttl=ttl)
    
    def _determine_cache_levels(self, value: Any) -> List[str]:
        """Determine which cache levels to use based on value characteristics"""
        size = self._estimate_size(value)
        
        if size < 1_000_000:  # < 1MB
            return ['memory', 'disk', 'redis']
        elif size < 100_000_000:  # < 100MB
            return ['disk', 'redis', 'object']
        else:  # Large files
            return ['object']
```

## 📋 Incremental Processing System

### Change Detection

```python
class ChangeDetector:
    def __init__(self):
        self.file_hash_cache = {}
        self.metadata_cache = {}
    
    def has_file_changed(self, file_path: Path) -> bool:
        """Detect if file has changed since last processing"""
        current_hash = self._calculate_file_hash(file_path)
        current_mtime = file_path.stat().st_mtime
        
        cached_info = self.file_hash_cache.get(str(file_path))
        
        if not cached_info:
            # First time seeing this file
            self._update_cache(file_path, current_hash, current_mtime)
            return True
        
        # Check both hash and modification time
        if (cached_info['hash'] != current_hash or 
            cached_info['mtime'] != current_mtime):
            self._update_cache(file_path, current_hash, current_mtime)
            return True
        
        return False
    
    def get_changed_pages(self, document_id: str, 
                         current_pages: List[PageInfo]) -> List[int]:
        """Identify which pages have changed"""
        cached_pages = self.metadata_cache.get(f"{document_id}:pages", {})
        changed_pages = []
        
        for page_info in current_pages:
            page_num = page_info.page_number
            page_hash = self._calculate_page_hash(page_info)
            
            if cached_pages.get(page_num) != page_hash:
                changed_pages.append(page_num)
                cached_pages[page_num] = page_hash
        
        # Update cache
        self.metadata_cache[f"{document_id}:pages"] = cached_pages
        
        return changed_pages
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _calculate_page_hash(self, page_info: PageInfo) -> str:
        """Calculate hash of page content"""
        content = f"{page_info.text}{page_info.bbox}{page_info.elements}"
        return hashlib.md5(content.encode()).hexdigest()
```

### Incremental Processing Pipeline

```python
class IncrementalProcessor:
    def __init__(self, cache: MultiLevelCache):
        self.cache = cache
        self.change_detector = ChangeDetector()
        
    def process_document_incremental(self, document_path: Path) -> ProcessingResult:
        """Process only changed parts of document"""
        document_id = self._get_document_id(document_path)
        
        # Check if entire document has changed
        if self.change_detector.has_file_changed(document_path):
            return self._process_with_change_detection(document_path, document_id)
        else:
            # Document unchanged, return cached result
            if cached_result := self.cache.get(f"result:{document_id}"):
                return cached_result
            else:
                # Cache miss, process entire document
                return self._process_full_document(document_path, document_id)
    
    def _process_with_change_detection(self, document_path: Path, 
                                     document_id: str) -> ProcessingResult:
        """Process document with page-level change detection"""
        # Get current page information
        current_pages = self._extract_page_info(document_path)
        
        # Identify changed pages
        changed_pages = self.change_detector.get_changed_pages(
            document_id, current_pages
        )
        
        if not changed_pages:
            # No changes, return cached result
            return self.cache.get(f"result:{document_id}")
        
        # Get previous result if exists
        previous_result = self.cache.get(f"result:{document_id}")
        
        if previous_result and len(changed_pages) < len(current_pages) * 0.3:
            # Less than 30% changed, do incremental update
            return self._incremental_update(
                document_path, document_id, 
                previous_result, changed_pages
            )
        else:
            # Too many changes, reprocess entire document
            return self._process_full_document(document_path, document_id)
    
    def _incremental_update(self, document_path: Path, document_id: str,
                           previous_result: ProcessingResult,
                           changed_pages: List[int]) -> ProcessingResult:
        """Update only changed pages"""
        updated_result = previous_result.copy()
        
        # Process each changed page
        for page_num in changed_pages:
            # Extract page
            page_data = self._extract_page(document_path, page_num)
            
            # Check cache for processed page
            page_cache_key = f"page:{document_id}:{page_num}"
            if cached_page := self.cache.get(page_cache_key):
                processed_page = cached_page
            else:
                # Process page
                processed_page = self._process_page(page_data)
                # Cache processed page
                self.cache.set(page_cache_key, processed_page, 
                             ttl=86400)  # 24 hours
            
            # Update result
            updated_result.update_page(page_num, processed_page)
        
        # Update metadata
        updated_result.metadata['last_updated'] = datetime.now()
        updated_result.metadata['incremental_update'] = True
        updated_result.metadata['changed_pages'] = changed_pages
        
        # Cache updated result
        self.cache.set(f"result:{document_id}", updated_result)
        
        return updated_result
```

## 🔧 Caching Strategies by Processing Stage

### 1. Document Parsing Cache

```python
class ParsingCache:
    def get_or_parse(self, document_path: Path, parser_name: str) -> ParseResult:
        """Cache parsing results per parser"""
        cache_key = self._generate_parsing_cache_key(document_path, parser_name)
        
        # Check cache
        if cached := self.cache.get(cache_key):
            return cached
        
        # Parse document
        parser = self.get_parser(parser_name)
        result = parser.parse(document_path)
        
        # Cache result
        # Longer TTL for stable documents
        ttl = self._determine_parsing_ttl(document_path)
        self.cache.set(cache_key, result, ttl=ttl)
        
        return result
    
    def _generate_parsing_cache_key(self, document_path: Path, 
                                   parser_name: str) -> str:
        """Generate cache key including file hash"""
        file_hash = hashlib.md5(document_path.read_bytes()).hexdigest()[:8]
        return f"parse:{parser_name}:{document_path.name}:{file_hash}"
```

### 2. OCR Results Cache

```python
class OCRCache:
    def get_or_ocr(self, image: np.ndarray, ocr_engine: str,
                   preprocessing: List[str]) -> OCRResult:
        """Cache OCR results with preprocessing fingerprint"""
        # Generate cache key from image hash and settings
        image_hash = hashlib.md5(image.tobytes()).hexdigest()[:8]
        preprocess_hash = hashlib.md5(
            json.dumps(preprocessing).encode()
        ).hexdigest()[:8]
        
        cache_key = f"ocr:{ocr_engine}:{image_hash}:{preprocess_hash}"
        
        # Check cache
        if cached := self.cache.get(cache_key):
            return cached
        
        # Perform OCR
        preprocessed = self._apply_preprocessing(image, preprocessing)
        result = self._run_ocr(preprocessed, ocr_engine)
        
        # Cache with long TTL (OCR results don't change)
        self.cache.set(cache_key, result, ttl=604800)  # 7 days
        
        return result
```

### 3. Table Extraction Cache

```python
class TableExtractionCache:
    def get_or_extract(self, page_data: PageData, 
                      extraction_method: str) -> List[Table]:
        """Cache table extraction results"""
        # Include page content hash in key
        content_hash = hashlib.md5(
            f"{page_data.text}{page_data.layout}".encode()
        ).hexdigest()[:8]
        
        cache_key = f"tables:{extraction_method}:{page_data.page_num}:{content_hash}"
        
        if cached := self.cache.get(cache_key):
            return cached
        
        # Extract tables
        tables = self._extract_tables(page_data, extraction_method)
        
        # Cache with appropriate TTL
        self.cache.set(cache_key, tables, ttl=86400)  # 24 hours
        
        return tables
```

### 4. Embedding Cache

```python
class EmbeddingCache:
    def get_or_embed(self, text: str, model_name: str) -> np.ndarray:
        """Cache text embeddings"""
        # Use hash of text for cache key
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        cache_key = f"embed:{model_name}:{text_hash}"
        
        # Check memory cache first (embeddings are small)
        if cached := self.cache.get(cache_key, cache_levels=['memory']):
            return cached
        
        # Generate embedding
        embedding = self._generate_embedding(text, model_name)
        
        # Cache in memory and disk
        self.cache.set(cache_key, embedding, 
                      cache_levels=['memory', 'disk'],
                      ttl=86400 * 30)  # 30 days
        
        return embedding
```

## 📊 Cache Management and Optimization

### Cache Warming

```python
class CacheWarmer:
    def warm_cache_for_document(self, document_path: Path):
        """Pre-populate cache for better performance"""
        document_id = self._get_document_id(document_path)
        
        # Warm parsing cache
        for parser in ['unstructured', 'pdfplumber', 'llamaparse']:
            self._warm_parser_cache(document_path, parser)
        
        # Warm page-level caches
        num_pages = self._get_page_count(document_path)
        for page_num in range(1, num_pages + 1):
            self._warm_page_cache(document_path, page_num)
    
    async def warm_cache_batch(self, document_paths: List[Path]):
        """Warm cache for multiple documents in parallel"""
        tasks = [
            self._warm_cache_async(path) 
            for path in document_paths
        ]
        await asyncio.gather(*tasks)
```

### Cache Invalidation

```python
class CacheInvalidator:
    def invalidate_document(self, document_id: str):
        """Invalidate all caches for a document"""
        # Find all keys related to document
        patterns = [
            f"parse:*:{document_id}:*",
            f"page:{document_id}:*",
            f"tables:*:{document_id}:*",
            f"result:{document_id}",
            f"embed:*:{document_id}:*"
        ]
        
        for pattern in patterns:
            keys = self.cache.find_keys(pattern)
            for key in keys:
                self.cache.delete(key)
    
    def invalidate_by_age(self, max_age_days: int):
        """Remove cache entries older than specified age"""
        cutoff_time = datetime.now() - timedelta(days=max_age_days)
        self.cache.expire_older_than(cutoff_time)
```

### Cache Metrics

```python
class CacheMetrics:
    def __init__(self):
        self.hits = defaultdict(int)
        self.misses = defaultdict(int)
        self.sizes = defaultdict(int)
    
    def record_hit(self, cache_level: str):
        self.hits[cache_level] += 1
    
    def record_miss(self, cache_level: str):
        self.misses[cache_level] += 1
    
    def get_hit_rate(self, cache_level: str) -> float:
        total = self.hits[cache_level] + self.misses[cache_level]
        return self.hits[cache_level] / total if total > 0 else 0
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        return {
            'hit_rates': {
                level: self.get_hit_rate(level) 
                for level in ['memory', 'disk', 'redis', 'object']
            },
            'total_hits': dict(self.hits),
            'total_misses': dict(self.misses),
            'cache_sizes': dict(self.sizes)
        }
```

## 🚀 Performance Best Practices

### 1. **Intelligent Cache Key Design**
```python
def generate_cache_key(namespace: str, *args, **kwargs) -> str:
    """Generate consistent cache keys"""
    # Include version for cache invalidation
    version = "v1"
    
    # Serialize arguments consistently
    args_str = ":".join(str(arg) for arg in args)
    kwargs_str = ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
    
    # Combine into key
    key_parts = [namespace, version, args_str, kwargs_str]
    key = ":".join(part for part in key_parts if part)
    
    # Hash if too long
    if len(key) > 250:
        key_hash = hashlib.md5(key.encode()).hexdigest()
        key = f"{namespace}:{version}:hash:{key_hash}"
    
    return key
```

### 2. **Batch Operations**
```python
def batch_cache_operations(self, operations: List[CacheOp]):
    """Batch multiple cache operations for efficiency"""
    # Group by operation type
    gets = [op for op in operations if op.type == 'get']
    sets = [op for op in operations if op.type == 'set']
    
    # Batch gets
    if gets:
        keys = [op.key for op in gets]
        values = self.cache.multi_get(keys)
        for op, value in zip(gets, values):
            op.result = value
    
    # Batch sets
    if sets:
        items = {op.key: op.value for op in sets}
        self.cache.multi_set(items)
```

### 3. **Compression for Large Objects**
```python
class CompressedCache:
    def set(self, key: str, value: Any, compress: bool = None):
        """Compress large values before caching"""
        if compress is None:
            # Auto-detect based on size
            compress = self._should_compress(value)
        
        if compress:
            value = self._compress(value)
            key = f"compressed:{key}"
        
        self.cache.set(key, value)
    
    def get(self, key: str) -> Any:
        """Get and decompress if needed"""
        # Try compressed version first
        compressed_key = f"compressed:{key}"
        if value := self.cache.get(compressed_key):
            return self._decompress(value)
        
        # Try uncompressed
        return self.cache.get(key)
```

## 📈 Configuration

### Cache Configuration
```yaml
caching:
  memory:
    enabled: true
    size_mb: 1024
    ttl_seconds: 3600
    
  disk:
    enabled: true
    path: "/var/cache/torematrix"
    size_gb: 50
    ttl_days: 7
    
  redis:
    enabled: true
    host: "localhost"
    port: 6379
    db: 0
    ttl_days: 30
    
  object_storage:
    enabled: false
    type: "s3"
    bucket: "torematrix-cache"
    ttl_days: 90
    
  incremental_processing:
    enabled: true
    change_threshold: 0.3  # Reprocess if >30% changed
    page_cache_ttl: 86400  # 24 hours
    
  metrics:
    enabled: true
    report_interval: 300  # 5 minutes
```

---

*This caching and incremental processing system ensures optimal performance and resource utilization in TORE Matrix Labs V3*