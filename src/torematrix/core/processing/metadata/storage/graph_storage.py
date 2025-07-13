"""Persistent storage for relationship graphs.

This module provides storage capabilities for relationship graphs including
saving, loading, querying, and updating graph data.
"""

import json
import logging
import sqlite3
import pickle
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime
import networkx as nx

from ..graph import ElementRelationshipGraph
from ..models.relationship import Relationship, RelationshipType

logger = logging.getLogger(__name__)


@dataclass
class RelationshipQuery:
    """Query parameters for relationship searches."""
    source_id: Optional[str] = None
    target_id: Optional[str] = None
    relationship_type: Optional[RelationshipType] = None
    min_confidence: float = 0.0
    max_confidence: float = 1.0
    limit: Optional[int] = None
    offset: int = 0
    order_by: str = "confidence"  # "confidence", "created_at", "source_id"
    order_desc: bool = True


class GraphStorage:
    """Persistent storage for relationship graphs."""
    
    def __init__(self, storage_path: Path):
        """Initialize graph storage.
        
        Args:
            storage_path: Directory for storage files
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.db_path = self.storage_path / "relationships.db"
        self.graphs_path = self.storage_path / "graphs"
        self.graphs_path.mkdir(exist_ok=True)
        
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for relationship metadata."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS relationships (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relationship_type TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,
                    FOREIGN KEY (document_id) REFERENCES documents (id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS elements (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    element_type TEXT NOT NULL,
                    text_content TEXT,
                    bbox_left REAL,
                    bbox_top REAL,
                    bbox_right REAL,
                    bbox_bottom REAL,
                    page_number INTEGER,
                    metadata TEXT,
                    FOREIGN KEY (document_id) REFERENCES documents (id)
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_rel_document ON relationships (document_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_rel_source ON relationships (source_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_rel_target ON relationships (target_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_rel_type ON relationships (relationship_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_rel_confidence ON relationships (confidence)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_elem_document ON elements (document_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_elem_type ON elements (element_type)")
            
            conn.commit()
    
    async def save_graph(
        self, 
        document_id: str,
        graph: ElementRelationshipGraph,
        document_metadata: Optional[Dict[str, Any]] = None
    ):
        """Save relationship graph to storage.
        
        Args:
            document_id: Document identifier
            graph: Relationship graph to save
            document_metadata: Optional document metadata
        """
        logger.info(f"Saving graph for document {document_id}")
        
        # Save to database
        await self._save_to_database(document_id, graph, document_metadata)
        
        # Save NetworkX graph as pickle for fast loading
        graph_file = self.graphs_path / f"{document_id}_graph.pkl"
        with open(graph_file, 'wb') as f:
            pickle.dump(graph.graph, f)
        
        # Save graph as JSON for human readability
        json_file = self.graphs_path / f"{document_id}_graph.json"
        graph_data = graph.to_dict()
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Saved graph with {len(graph.element_index)} elements and {graph.graph.number_of_edges()} relationships")
    
    async def load_graph(
        self, 
        document_id: str
    ) -> Optional[ElementRelationshipGraph]:
        """Load relationship graph from storage.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Loaded relationship graph or None if not found
        """
        logger.info(f"Loading graph for document {document_id}")
        
        # Try loading from pickle first (fastest)
        graph_file = self.graphs_path / f"{document_id}_graph.pkl"
        if graph_file.exists():
            try:
                with open(graph_file, 'rb') as f:
                    nx_graph = pickle.load(f)
                
                # Reconstruct ElementRelationshipGraph
                graph = ElementRelationshipGraph()
                graph.graph = nx_graph
                
                # Rebuild indexes
                for node_id, node_data in nx_graph.nodes(data=True):
                    if 'element' in node_data:
                        graph.element_index[node_id] = node_data['element']
                        graph.relationship_index[node_id] = []
                
                for _, _, edge_data in nx_graph.edges(data=True):
                    if 'relationship' in edge_data:
                        rel = edge_data['relationship']
                        graph.relationship_index[rel.source_id].append(rel)
                        if rel.target_id != rel.source_id:
                            graph.relationship_index[rel.target_id].append(rel)
                
                logger.info(f"Loaded graph from pickle with {len(graph.element_index)} elements")
                return graph
                
            except Exception as e:
                logger.warning(f"Failed to load from pickle: {e}, trying JSON")
        
        # Fallback to JSON loading
        json_file = self.graphs_path / f"{document_id}_graph.json"
        if json_file.exists():
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    graph_data = json.load(f)
                
                graph = ElementRelationshipGraph.from_dict(graph_data)
                logger.info(f"Loaded graph from JSON with {len(graph.element_index)} elements")
                return graph
                
            except Exception as e:
                logger.error(f"Failed to load from JSON: {e}")
        
        # Fallback to database reconstruction
        return await self._load_from_database(document_id)
    
    async def update_relationships(
        self, 
        document_id: str,
        relationships: List[Relationship]
    ):
        """Update specific relationships.
        
        Args:
            document_id: Document identifier
            relationships: Relationships to update
        """
        logger.info(f"Updating {len(relationships)} relationships for document {document_id}")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for rel in relationships:
                cursor.execute("""
                    INSERT OR REPLACE INTO relationships 
                    (id, document_id, source_id, target_id, relationship_type, confidence, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    rel.id,
                    document_id,
                    rel.source_id,
                    rel.target_id,
                    rel.relationship_type.value,
                    rel.confidence,
                    json.dumps(rel.metadata)
                ))
            
            # Update document timestamp
            cursor.execute("""
                UPDATE documents SET updated_at = CURRENT_TIMESTAMP WHERE id = ?
            """, (document_id,))
            
            conn.commit()
        
        # Invalidate cached graph files to force reload
        graph_file = self.graphs_path / f"{document_id}_graph.pkl"
        json_file = self.graphs_path / f"{document_id}_graph.json"
        
        if graph_file.exists():
            graph_file.unlink()
        if json_file.exists():
            json_file.unlink()
    
    def query_relationships(
        self, 
        query: RelationshipQuery,
        document_id: Optional[str] = None
    ) -> List[Relationship]:
        """Query relationships with filters.
        
        Args:
            query: Query parameters
            document_id: Optional document filter
            
        Returns:
            List of matching relationships
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Build SQL query
            sql_parts = ["SELECT * FROM relationships WHERE 1=1"]
            params = []
            
            if document_id:
                sql_parts.append("AND document_id = ?")
                params.append(document_id)
            
            if query.source_id:
                sql_parts.append("AND source_id = ?")
                params.append(query.source_id)
            
            if query.target_id:
                sql_parts.append("AND target_id = ?")
                params.append(query.target_id)
            
            if query.relationship_type:
                sql_parts.append("AND relationship_type = ?")
                params.append(query.relationship_type.value)
            
            if query.min_confidence > 0.0:
                sql_parts.append("AND confidence >= ?")
                params.append(query.min_confidence)
            
            if query.max_confidence < 1.0:
                sql_parts.append("AND confidence <= ?")
                params.append(query.max_confidence)
            
            # Add ordering
            order_column = query.order_by
            if order_column not in ['confidence', 'created_at', 'source_id', 'target_id']:
                order_column = 'confidence'
            
            direction = "DESC" if query.order_desc else "ASC"
            sql_parts.append(f"ORDER BY {order_column} {direction}")
            
            # Add limit and offset
            if query.limit:
                sql_parts.append("LIMIT ?")
                params.append(query.limit)
            
            if query.offset > 0:
                sql_parts.append("OFFSET ?")
                params.append(query.offset)
            
            sql = " ".join(sql_parts)
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            # Convert rows to Relationship objects
            relationships = []
            for row in rows:
                metadata = json.loads(row[7]) if row[7] else {}
                rel = Relationship(
                    id=row[0],
                    source_id=row[2],
                    target_id=row[3],
                    relationship_type=RelationshipType(row[4]),
                    confidence=row[5],
                    created_at=datetime.fromisoformat(row[6]) if row[6] else datetime.now(),
                    metadata=metadata
                )
                relationships.append(rel)
            
            return relationships
    
    def get_document_list(self) -> List[Dict[str, Any]]:
        """Get list of stored documents.
        
        Returns:
            List of document metadata
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, created_at, updated_at FROM documents ORDER BY updated_at DESC")
            
            documents = []
            for row in cursor.fetchall():
                documents.append({
                    'id': row[0],
                    'title': row[1],
                    'created_at': row[2],
                    'updated_at': row[3]
                })
            
            return documents
    
    def delete_document(self, document_id: str):
        """Delete document and all its relationships.
        
        Args:
            document_id: Document identifier
        """
        logger.info(f"Deleting document {document_id}")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Delete relationships
            cursor.execute("DELETE FROM relationships WHERE document_id = ?", (document_id,))
            
            # Delete elements
            cursor.execute("DELETE FROM elements WHERE document_id = ?", (document_id,))
            
            # Delete document
            cursor.execute("DELETE FROM documents WHERE id = ?", (document_id,))
            
            conn.commit()
        
        # Delete graph files
        graph_file = self.graphs_path / f"{document_id}_graph.pkl"
        json_file = self.graphs_path / f"{document_id}_graph.json"
        
        if graph_file.exists():
            graph_file.unlink()
        if json_file.exists():
            json_file.unlink()
    
    def get_statistics(self, document_id: Optional[str] = None) -> Dict[str, Any]:
        """Get storage statistics.
        
        Args:
            document_id: Optional document filter
            
        Returns:
            Statistics dictionary
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Document count
            if document_id:
                cursor.execute("SELECT COUNT(*) FROM documents WHERE id = ?", (document_id,))
                stats['documents'] = cursor.fetchone()[0]
                
                # Relationships for specific document
                cursor.execute("SELECT COUNT(*) FROM relationships WHERE document_id = ?", (document_id,))
                stats['relationships'] = cursor.fetchone()[0]
                
                # Elements for specific document
                cursor.execute("SELECT COUNT(*) FROM elements WHERE document_id = ?", (document_id,))
                stats['elements'] = cursor.fetchone()[0]
                
                # Relationship type distribution
                cursor.execute("""
                    SELECT relationship_type, COUNT(*) 
                    FROM relationships 
                    WHERE document_id = ?
                    GROUP BY relationship_type
                """, (document_id,))
                stats['relationship_types'] = dict(cursor.fetchall())
                
            else:
                # Global statistics
                cursor.execute("SELECT COUNT(*) FROM documents")
                stats['documents'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM relationships")
                stats['relationships'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM elements")
                stats['elements'] = cursor.fetchone()[0]
                
                # Relationship type distribution
                cursor.execute("""
                    SELECT relationship_type, COUNT(*) 
                    FROM relationships 
                    GROUP BY relationship_type
                """)
                stats['relationship_types'] = dict(cursor.fetchall())
                
                # Average confidence
                cursor.execute("SELECT AVG(confidence) FROM relationships")
                avg_conf = cursor.fetchone()[0]
                stats['average_confidence'] = avg_conf if avg_conf else 0.0
            
            return stats
    
    async def _save_to_database(
        self, 
        document_id: str, 
        graph: ElementRelationshipGraph,
        document_metadata: Optional[Dict[str, Any]]
    ):
        """Save graph data to database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Save document
            cursor.execute("""
                INSERT OR REPLACE INTO documents (id, title, metadata)
                VALUES (?, ?, ?)
            """, (
                document_id,
                document_metadata.get('title', document_id) if document_metadata else document_id,
                json.dumps(document_metadata) if document_metadata else '{}'
            ))
            
            # Save elements
            cursor.execute("DELETE FROM elements WHERE document_id = ?", (document_id,))
            for element in graph.element_index.values():
                bbox = None
                page_num = None
                
                if element.metadata and element.metadata.coordinates:
                    bbox = element.metadata.coordinates.layout_bbox
                    page_num = element.metadata.page_number
                
                cursor.execute("""
                    INSERT INTO elements 
                    (id, document_id, element_type, text_content, bbox_left, bbox_top, bbox_right, bbox_bottom, page_number, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    element.id,
                    document_id,
                    element.type,
                    element.text,
                    bbox[0] if bbox and len(bbox) > 0 else None,
                    bbox[1] if bbox and len(bbox) > 1 else None,
                    bbox[2] if bbox and len(bbox) > 2 else None,
                    bbox[3] if bbox and len(bbox) > 3 else None,
                    page_num,
                    json.dumps(element.metadata.to_dict() if element.metadata else {})
                ))
            
            # Save relationships
            cursor.execute("DELETE FROM relationships WHERE document_id = ?", (document_id,))
            for _, _, edge_data in graph.graph.edges(data=True):
                if 'relationship' in edge_data:
                    rel = edge_data['relationship']
                    cursor.execute("""
                        INSERT INTO relationships 
                        (id, document_id, source_id, target_id, relationship_type, confidence, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        rel.id,
                        document_id,
                        rel.source_id,
                        rel.target_id,
                        rel.relationship_type.value,
                        rel.confidence,
                        json.dumps(rel.metadata)
                    ))
            
            conn.commit()
    
    async def _load_from_database(self, document_id: str) -> Optional[ElementRelationshipGraph]:
        """Load graph from database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if document exists
            cursor.execute("SELECT COUNT(*) FROM documents WHERE id = ?", (document_id,))
            if cursor.fetchone()[0] == 0:
                return None
            
            # Load elements (simplified - would need full UnifiedElement reconstruction)
            cursor.execute("SELECT * FROM elements WHERE document_id = ?", (document_id,))
            element_rows = cursor.fetchall()
            
            # Load relationships
            cursor.execute("SELECT * FROM relationships WHERE document_id = ?", (document_id,))
            rel_rows = cursor.fetchall()
            
            # Reconstruct graph (simplified version)
            graph = ElementRelationshipGraph()
            
            # Note: This is a simplified reconstruction
            # In a full implementation, you'd need to properly reconstruct UnifiedElement objects
            logger.info(f"Loaded {len(element_rows)} elements and {len(rel_rows)} relationships from database")
            
            return graph