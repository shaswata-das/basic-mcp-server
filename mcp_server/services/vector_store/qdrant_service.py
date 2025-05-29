"""
Qdrant Vector Database Service for MCP Server

This module provides vector storage and retrieval using Qdrant, optimized
for code and knowledge embedding.
"""

import logging
import uuid
from typing import Dict, List, Optional, Any, Union
import numpy as np

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct

class QdrantVectorService:
    """Service for vector storage and retrieval using Qdrant"""
    
    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        collection_name: str = "code_knowledge",
        vector_size: int = 1536,  # Default for OpenAI embeddings
        distance: str = "Cosine",
    ):
        """Initialize the Qdrant vector service
        
        Args:
            url: Qdrant server URL (None for in-memory)
            api_key: API key for Qdrant cloud
            collection_name: Name of the collection to use
            vector_size: Size of the embedding vectors
            distance: Distance metric to use ("Cosine", "Euclid", or "Dot")
        """
        self.logger = logging.getLogger("mcp_server.services.qdrant")
        self.collection_name = collection_name
        self.vector_size = vector_size
        
        # Map string distance to enum
        distance_map = {
            "cosine": Distance.COSINE,
            "euclid": Distance.EUCLID,
            "dot": Distance.DOT,
        }
        self.distance = distance_map.get(distance.lower(), Distance.COSINE)
        
        # Initialize Qdrant client
        if url:
            self.client = QdrantClient(url=url, api_key=api_key)
            self.logger.info(f"Initialized Qdrant client with remote server at {url}")
        else:
            self.client = QdrantClient(":memory:")
            self.logger.info("Initialized in-memory Qdrant client")
    
    async def initialize(self):
        """Initialize the vector store (create collection if needed)"""
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.collection_name not in collection_names:
                self.logger.info(f"Creating collection '{self.collection_name}'")
                
                # Create the collection with vector configuration
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=self.distance
                    )
                )
                
                # Create payload index for efficient filtering
                self._create_payload_indices()
                
            self.logger.info(f"Qdrant vector store initialized with collection '{self.collection_name}'")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Qdrant: {str(e)}")
            return False
    
    def _create_payload_indices(self):
        """Create payload indices for efficient querying"""
        # Create index for code file path
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="file_path",
            field_schema="keyword"
        )
        
        # Create index for code language
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="language",
            field_schema="keyword"
        )
        
        # Create index for code type (class, component, etc.)
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="code_type",
            field_schema="keyword"
        )
        
        # Create index for repository ID
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="repo_id",
            field_schema="keyword"
        )
    
    async def store_code_chunk(
        self, 
        embedding: List[float],
        code_text: str,
        metadata: Dict[str, Any],
        chunk_id: Optional[str] = None
    ) -> str:
        """Store a code chunk with its embedding and metadata
        
        Args:
            embedding: Vector embedding of the code
            code_text: The actual code text
            metadata: Additional metadata (file_path, language, etc.)
            chunk_id: Optional ID for the chunk (generated if not provided)
            
        Returns:
            ID of the stored chunk
        """
        # Generate ID if not provided
        if chunk_id is None:
            chunk_id = str(uuid.uuid4())
        
        # Combine code text and metadata
        payload = {
            "code_text": code_text,
            **metadata
        }
        
        # Store the vector
        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=chunk_id,
                    vector=embedding,
                    payload=payload
                )
            ]
        )
        
        return chunk_id
    
    async def store_batch_code_chunks(
        self,
        embeddings: List[List[float]],
        code_texts: List[str],
        metadata_list: List[Dict[str, Any]],
        chunk_ids: Optional[List[str]] = None
    ) -> List[str]:
        """Store multiple code chunks in a batch
        
        Args:
            embeddings: List of vector embeddings
            code_texts: List of code texts
            metadata_list: List of metadata dictionaries
            chunk_ids: Optional list of chunk IDs
            
        Returns:
            List of chunk IDs
        """
        # Generate IDs if not provided
        if chunk_ids is None:
            chunk_ids = [str(uuid.uuid4()) for _ in range(len(embeddings))]
        
        # Create points for batch insertion
        points = []
        for i, (chunk_id, embedding, code_text, metadata) in enumerate(
            zip(chunk_ids, embeddings, code_texts, metadata_list)
        ):
            payload = {
                "code_text": code_text,
                **metadata
            }
            
            points.append(
                PointStruct(
                    id=chunk_id,
                    vector=embedding,
                    payload=payload
                )
            )
        
        # Store the vectors in batch
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        
        return chunk_ids
    
    async def search_similar_code(
        self,
        query_embedding: List[float],
        filter_params: Optional[Dict[str, Any]] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for code chunks similar to the query embedding
        
        Args:
            query_embedding: Vector embedding of the query
            filter_params: Optional filter parameters (language, repo_id, etc.)
            limit: Maximum number of results to return
            
        Returns:
            List of matching code chunks with similarity scores
        """
        # Convert filter_params to Qdrant filter format
        filter_condition = None
        if filter_params:
            filter_condition = self._build_filter(filter_params)
        
        # Search for similar vectors
        search_result = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            query_filter=filter_condition,
            limit=limit
        )
        
        # Format the results
        results = []
        for scored_point in search_result:
            result = {
                "id": scored_point.id,
                "score": scored_point.score,
                "code_text": scored_point.payload.get("code_text", ""),
            }
            
            # Add all metadata
            for key, value in scored_point.payload.items():
                if key != "code_text":
                    result[key] = value
            
            results.append(result)
        
        return results
    
    async def search_by_ids(
        self, 
        chunk_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """Retrieve code chunks by their IDs
        
        Args:
            chunk_ids: List of chunk IDs to retrieve
            
        Returns:
            List of code chunks with their metadata
        """
        # Retrieve points by IDs
        points = self.client.retrieve(
            collection_name=self.collection_name,
            ids=chunk_ids
        )
        
        # Format the results
        results = []
        for point in points:
            result = {
                "id": point.id,
                "code_text": point.payload.get("code_text", ""),
            }
            
            # Add all metadata
            for key, value in point.payload.items():
                if key != "code_text":
                    result[key] = value
            
            results.append(result)
        
        return results
    
    def _build_filter(self, filter_params: Dict[str, Any]) -> models.Filter:
        """Build a Qdrant filter from filter parameters
        
        Args:
            filter_params: Dictionary of filter parameters
            
        Returns:
            Qdrant filter object
        """
        conditions = []
        
        for key, value in filter_params.items():
            if isinstance(value, list):
                # Handle lists (IN operator)
                conditions.append(
                    models.FieldCondition(
                        key=key,
                        match=models.MatchAny(any=value)
                    )
                )
            else:
                # Handle single values (equals)
                conditions.append(
                    models.FieldCondition(
                        key=key,
                        match=models.MatchValue(value=value)
                    )
                )
        
        # Combine all conditions with AND
        return models.Filter(
            must=conditions
        )
    
    async def delete_by_filter(self, filter_params: Dict[str, Any]) -> int:
        """Delete points matching the filter
        
        Args:
            filter_params: Filter parameters
            
        Returns:
            Number of deleted points
        """
        # Convert filter_params to Qdrant filter format
        filter_condition = self._build_filter(filter_params)
        
        # Delete points matching the filter
        result = self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=filter_condition
            )
        )
        
        return result.status
    
    async def clear_collection(self) -> bool:
        """Clear all points from the collection
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.delete_collection(self.collection_name)
            await self.initialize()
            return True
        except Exception as e:
            self.logger.error(f"Failed to clear collection: {str(e)}")
            return False
