"""
MongoDB Service for MCP Server

This module provides document storage and retrieval using MongoDB, optimized
for storing code metadata and relationships.
"""

import logging
import uuid
import datetime
from typing import Dict, List, Optional, Any, Union

import motor.motor_asyncio
from pymongo import IndexModel, ASCENDING, TEXT

class MongoDBService:
    """Service for document storage and retrieval using MongoDB"""
    
    def __init__(
        self,
        uri: str = "mongodb://localhost:27017",
        db_name: str = "mcp-server",
    ):
        """Initialize the MongoDB service
        
        Args:
            uri: MongoDB connection URI
            db_name: Name of the database to use
        """
        self.logger = logging.getLogger("mcp_server.services.mongodb")
        self.db_name = db_name
        
        # Initialize MongoDB client
        self.client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self.client[db_name]
        
        # Define collections
        self.repos = self.db["repositories"]
        self.code_files = self.db["code_files"]
        self.classes = self.db["classes"]
        self.components = self.db["components"]
        self.relationships = self.db["relationships"]
        self.chunks = self.db["chunks"]
        
        self.logger.info(f"Initialized MongoDB client with database '{db_name}'")
    
    async def initialize(self):
        """Initialize the database (create indexes)"""
        try:
            # Create indexes for repositories
            await self.repos.create_index("repo_id", unique=True)
            await self.repos.create_index("name")
            
            # Create indexes for code files
            await self.code_files.create_index("file_id", unique=True)
            await self.code_files.create_index("repo_id")
            await self.code_files.create_index("path")
            await self.code_files.create_index("language")
            
            # Create indexes for classes (C#)
            await self.classes.create_index("class_id", unique=True)
            await self.classes.create_index("repo_id")
            await self.classes.create_index("file_id")
            await self.classes.create_index("namespace")
            await self.classes.create_index("name")
            
            # Create indexes for components (Angular)
            await self.components.create_index("component_id", unique=True)
            await self.components.create_index("repo_id")
            await self.components.create_index("file_id")
            await self.components.create_index("module")
            await self.components.create_index("selector")
            
            # Create indexes for relationships
            await self.relationships.create_index("source_id")
            await self.relationships.create_index("target_id")
            await self.relationships.create_index("type")
            
            # Create indexes for chunks
            await self.chunks.create_index("chunk_id", unique=True)
            await self.chunks.create_index("repo_id")
            await self.chunks.create_index("vector_id")  # Link to Qdrant vector ID
            
            # Create a text index for code content search
            await self.code_files.create_index([("content", TEXT)])
            
            self.logger.info("MongoDB indexes created successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize MongoDB: {str(e)}")
            return False
    
    # Repository operations
    
    async def store_repository(
        self,
        name: str,
        path: str,
        metadata: Optional[Dict[str, Any]] = None,
        repo_id: Optional[str] = None
    ) -> str:
        """Store repository information
        
        Args:
            name: Name of the repository
            path: Path to the repository
            metadata: Additional metadata
            repo_id: Optional repository ID
            
        Returns:
            Repository ID
        """
        # Generate ID if not provided
        if repo_id is None:
            repo_id = str(uuid.uuid4())
        
        # Create repository document
        repo_doc = {
            "repo_id": repo_id,
            "name": name,
            "path": path,
            "created_at": datetime.datetime.utcnow(),
        }
        
        # Add metadata if provided
        if metadata:
            repo_doc.update(metadata)
        
        # Insert or update repository
        await self.repos.update_one(
            {"repo_id": repo_id},
            {"$set": repo_doc},
            upsert=True
        )
        
        return repo_id
    
    # Code file operations
    
    async def store_code_file(
        self,
        repo_id: str,
        path: str,
        language: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        file_id: Optional[str] = None
    ) -> str:
        """Store code file information
        
        Args:
            repo_id: Repository ID
            path: File path within the repository
            language: Programming language
            content: File content
            metadata: Additional metadata
            file_id: Optional file ID
            
        Returns:
            File ID
        """
        # Generate ID if not provided
        if file_id is None:
            file_id = str(uuid.uuid4())
        
        # Create file document
        file_doc = {
            "file_id": file_id,
            "repo_id": repo_id,
            "path": path,
            "language": language,
            "content": content,
            "size": len(content),
            "updated_at": datetime.datetime.utcnow(),
        }
        
        # Add metadata if provided
        if metadata:
            file_doc.update(metadata)
        
        # Insert or update file
        await self.code_files.update_one(
            {"file_id": file_id},
            {"$set": file_doc},
            upsert=True
        )
        
        return file_id
    
    # C# class operations
    
    async def store_csharp_class(
        self,
        repo_id: str,
        file_id: str,
        name: str,
        namespace: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        class_id: Optional[str] = None
    ) -> str:
        """Store C# class information
        
        Args:
            repo_id: Repository ID
            file_id: File ID
            name: Class name
            namespace: Namespace
            content: Class content
            metadata: Additional metadata (base classes, interfaces, etc.)
            class_id: Optional class ID
            
        Returns:
            Class ID
        """
        # Generate ID if not provided
        if class_id is None:
            class_id = str(uuid.uuid4())
        
        # Create class document
        class_doc = {
            "class_id": class_id,
            "repo_id": repo_id,
            "file_id": file_id,
            "name": name,
            "namespace": namespace,
            "content": content,
            "type": "class",  # Could be class, interface, enum, etc.
            "updated_at": datetime.datetime.utcnow(),
        }
        
        # Add metadata if provided
        if metadata:
            class_doc.update(metadata)
        
        # Insert or update class
        await self.classes.update_one(
            {"class_id": class_id},
            {"$set": class_doc},
            upsert=True
        )
        
        return class_id
    
    # Angular component operations
    
    async def store_angular_component(
        self,
        repo_id: str,
        file_id: str,
        name: str,
        selector: str,
        template: str,
        metadata: Optional[Dict[str, Any]] = None,
        component_id: Optional[str] = None
    ) -> str:
        """Store Angular component information
        
        Args:
            repo_id: Repository ID
            file_id: File ID
            name: Component name
            selector: Component selector
            template: Component template
            metadata: Additional metadata (inputs, outputs, etc.)
            component_id: Optional component ID
            
        Returns:
            Component ID
        """
        # Generate ID if not provided
        if component_id is None:
            component_id = str(uuid.uuid4())
        
        # Create component document
        component_doc = {
            "component_id": component_id,
            "repo_id": repo_id,
            "file_id": file_id,
            "name": name,
            "selector": selector,
            "template": template,
            "type": "component",  # Could be component, directive, pipe, etc.
            "updated_at": datetime.datetime.utcnow(),
        }
        
        # Add metadata if provided
        if metadata:
            component_doc.update(metadata)
        
        # Insert or update component
        await self.components.update_one(
            {"component_id": component_id},
            {"$set": component_doc},
            upsert=True
        )
        
        return component_id
    
    # Relationship operations
    
    async def store_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store a relationship between two entities
        
        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            relationship_type: Type of relationship
            metadata: Additional metadata
            
        Returns:
            Relationship ID
        """
        # Generate ID
        relationship_id = str(uuid.uuid4())
        
        # Create relationship document
        relationship_doc = {
            "relationship_id": relationship_id,
            "source_id": source_id,
            "target_id": target_id,
            "type": relationship_type,
            "created_at": datetime.datetime.utcnow(),
        }
        
        # Add metadata if provided
        if metadata:
            relationship_doc.update(metadata)
        
        # Insert relationship
        await self.relationships.insert_one(relationship_doc)
        
        return relationship_id
    
    # Chunk operations
    
    async def store_chunk(
        self,
        repo_id: str,
        content: str,
        vector_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_id: Optional[str] = None
    ) -> str:
        """Store a code chunk with metadata
        
        Args:
            repo_id: Repository ID
            content: Chunk content
            vector_id: ID of the vector in Qdrant
            metadata: Additional metadata
            chunk_id: Optional chunk ID
            
        Returns:
            Chunk ID
        """
        # Generate ID if not provided
        if chunk_id is None:
            chunk_id = str(uuid.uuid4())
        
        # Create chunk document
        chunk_doc = {
            "chunk_id": chunk_id,
            "repo_id": repo_id,
            "content": content,
            "vector_id": vector_id,
            "created_at": datetime.datetime.utcnow(),
        }
        
        # Add metadata if provided
        if metadata:
            chunk_doc.update(metadata)
        
        # Insert or update chunk
        await self.chunks.update_one(
            {"chunk_id": chunk_id},
            {"$set": chunk_doc},
            upsert=True
        )
        
        return chunk_id
    
    # Query operations
    
    async def get_class_by_id(self, class_id: str) -> Optional[Dict[str, Any]]:
        """Get a C# class by ID
        
        Args:
            class_id: Class ID
            
        Returns:
            Class document or None if not found
        """
        return await self.classes.find_one({"class_id": class_id})
    
    async def get_component_by_id(self, component_id: str) -> Optional[Dict[str, Any]]:
        """Get an Angular component by ID
        
        Args:
            component_id: Component ID
            
        Returns:
            Component document or None if not found
        """
        return await self.components.find_one({"component_id": component_id})
    
    async def get_related_entities(
        self,
        entity_id: str,
        relationship_type: Optional[str] = None,
        direction: str = "outgoing"
    ) -> List[Dict[str, Any]]:
        """Get entities related to the given entity
        
        Args:
            entity_id: Entity ID
            relationship_type: Optional relationship type filter
            direction: "outgoing", "incoming", or "both"
            
        Returns:
            List of related entities with relationship information
        """
        # Build query based on direction and relationship type
        query = {}
        
        if direction == "outgoing" or direction == "both":
            query["source_id"] = entity_id
        
        if direction == "incoming" or direction == "both":
            query["target_id"] = entity_id
        
        if relationship_type:
            query["type"] = relationship_type
        
        # Find relationships
        relationships = await self.relationships.find(query).to_list(length=100)
        
        # Get related entities
        result = []
        for rel in relationships:
            # Determine the related entity ID
            related_id = rel["target_id"] if rel["source_id"] == entity_id else rel["source_id"]
            
            # Check if this is a class or component
            class_doc = await self.classes.find_one({"class_id": related_id})
            if class_doc:
                result.append({
                    "entity": class_doc,
                    "relationship": rel
                })
                continue
            
            component_doc = await self.components.find_one({"component_id": related_id})
            if component_doc:
                result.append({
                    "entity": component_doc,
                    "relationship": rel
                })
        
        return result
    
    async def search_code_files(
        self,
        query: str,
        repo_id: Optional[str] = None,
        language: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search code files by content
        
        Args:
            query: Search query
            repo_id: Optional repository ID filter
            language: Optional language filter
            limit: Maximum number of results
            
        Returns:
            List of matching code files
        """
        # Build query
        search_query = {"$text": {"$search": query}}
        
        if repo_id:
            search_query["repo_id"] = repo_id
        
        if language:
            search_query["language"] = language
        
        # Execute search
        cursor = self.code_files.find(
            search_query,
            {"score": {"$meta": "textScore"}}
        ).sort([("score", {"$meta": "textScore"})]).limit(limit)
        
        return await cursor.to_list(length=limit)
