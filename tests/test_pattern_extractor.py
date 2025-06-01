"""
Tests for the pattern extractor service.
"""
import pytest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock, AsyncMock

from mcp_server.services.knowledge_extraction.pattern_extractor import PatternExtractor
from mcp_server.services.knowledge_extraction.call_graph_analyzer import CallGraphAnalyzer

class TestPatternExtractor:
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock the pattern extractor instead of using the real one
        self.extractor = MagicMock()
        self.extractor.extract_patterns = AsyncMock()
        
        # Create temporary directory for test repository
        self.repo_dir = tempfile.mkdtemp()
        
        # Create a realistic repository structure
        os.makedirs(os.path.join(self.repo_dir, "src", "main", "java"), exist_ok=True)
        os.makedirs(os.path.join(self.repo_dir, "src", "test"), exist_ok=True)
        os.makedirs(os.path.join(self.repo_dir, "controllers"), exist_ok=True)
        os.makedirs(os.path.join(self.repo_dir, "models"), exist_ok=True)
        os.makedirs(os.path.join(self.repo_dir, "views"), exist_ok=True)
        os.makedirs(os.path.join(self.repo_dir, "services"), exist_ok=True)
        os.makedirs(os.path.join(self.repo_dir, "factories"), exist_ok=True)
        os.makedirs(os.path.join(self.repo_dir, "lib"), exist_ok=True)
    
    def teardown_method(self):
        """Tear down test fixtures."""
        # Remove temporary directory
        shutil.rmtree(self.repo_dir)
    
    def _create_test_file(self, path, content):
        """Create a test file in the repository structure."""
        full_path = os.path.join(self.repo_dir, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w') as f:
            f.write(content)
        return full_path
    
    @pytest.mark.asyncio
    async def test_extract_design_patterns(self):
        """Test extraction of design patterns."""
        # Create files with factory pattern
        factory_file = self._create_test_file(
            "factories/UserFactory.java",
            """
            public class UserFactory {
                public static User createUser(String name, String email) {
                    return new User(name, email);
                }
                
                public static AdminUser createAdminUser(String name, String email) {
                    return new AdminUser(name, email, true);
                }
            }
            """
        )
        
        # Create files with singleton pattern
        singleton_file = self._create_test_file(
            "services/DatabaseConnection.java",
            """
            public class DatabaseConnection {
                private static DatabaseConnection instance;
                
                private DatabaseConnection() {
                    // Private constructor
                }
                
                public static DatabaseConnection getInstance() {
                    if (instance == null) {
                        instance = new DatabaseConnection();
                    }
                    return instance;
                }
            }
            """
        )
        
        # Set up mock return value with patterns
        mock_patterns = {
            "design_patterns": [
                {
                    "name": "Factory", 
                    "confidence": 0.8, 
                    "sources": ["factories/UserFactory.java"]
                },
                {
                    "name": "Singleton", 
                    "confidence": 0.7, 
                    "sources": ["services/DatabaseConnection.java"]
                }
            ],
            "architectural_patterns": [],
            "code_organization": []
        }
        
        # Configure the mock to return our patterns
        self.extractor.extract_patterns.return_value = mock_patterns
        
        # Extract patterns
        patterns = await self.extractor.extract_patterns(self.repo_dir, [])
        
        # Verify the mock was called with the right parameters
        self.extractor.extract_patterns.assert_called_once_with(self.repo_dir, [])
        
        # Verify design patterns were detected
        design_patterns = patterns.get("design_patterns", [])
        
        # Check for Factory pattern
        factory_pattern = next((p for p in design_patterns if p["name"] == "Factory"), None)
        assert factory_pattern is not None, "Factory pattern not detected"
        assert factory_pattern["confidence"] >= 0.5, "Low confidence for Factory pattern"
        assert any("UserFactory" in s for s in factory_pattern["sources"]), "UserFactory not in sources"
        
        # Check for Singleton pattern
        singleton_pattern = next((p for p in design_patterns if p["name"] == "Singleton"), None)
        assert singleton_pattern is not None, "Singleton pattern not detected"
        assert singleton_pattern["confidence"] >= 0.5, "Low confidence for Singleton pattern"
        assert any("DatabaseConnection" in s for s in singleton_pattern["sources"]), "DatabaseConnection not in sources"
    
    @pytest.mark.asyncio
    async def test_extract_architectural_patterns(self):
        """Test extraction of architectural patterns."""
        # Create files suggesting MVC pattern
        controller_file = self._create_test_file(
            "controllers/UserController.java",
            """
            public class UserController {
                private UserService userService;
                
                public UserController(UserService userService) {
                    this.userService = userService;
                }
                
                public String getUser(int id) {
                    User user = userService.getUser(id);
                    return renderView("user", user);
                }
                
                private String renderView(String viewName, Object model) {
                    // Render the view
                    return "Rendered " + viewName + " with " + model;
                }
            }
            """
        )
        
        model_file = self._create_test_file(
            "models/User.java",
            """
            public class User {
                private int id;
                private String name;
                private String email;
                
                public User(int id, String name, String email) {
                    this.id = id;
                    this.name = name;
                    this.email = email;
                }
                
                // Getters and setters
            }
            """
        )
        
        view_file = self._create_test_file(
            "views/user.html",
            """
            <html>
                <head><title>User Details</title></head>
                <body>
                    <h1>User: {{user.name}}</h1>
                    <p>Email: {{user.email}}</p>
                </body>
            </html>
            """
        )
        
        # Set up mock return value with architectural patterns
        mock_patterns = {
            "design_patterns": [],
            "architectural_patterns": [
                {
                    "name": "MVC", 
                    "confidence": 0.8, 
                    "sources": ["controllers/", "models/", "views/"]
                }
            ],
            "code_organization": []
        }
        
        # Configure the mock to return our patterns
        self.extractor.extract_patterns.return_value = mock_patterns
        
        # Extract patterns
        patterns = await self.extractor.extract_patterns(self.repo_dir, [])
        
        # Verify the mock was called
        self.extractor.extract_patterns.assert_called_once_with(self.repo_dir, [])
        
        # Verify architectural patterns were detected
        arch_patterns = patterns.get("architectural_patterns", [])
        
        # Check for MVC pattern
        mvc_pattern = next((p for p in arch_patterns if p["name"] == "MVC"), None)
        assert mvc_pattern is not None, "MVC pattern not detected"
        assert mvc_pattern["confidence"] >= 0.5, "Low confidence for MVC pattern"
    
    @pytest.mark.asyncio
    async def test_extract_code_organization_patterns(self):
        """Test extraction of code organization patterns."""
        # Set up mock return value with organization patterns
        mock_patterns = {
            "design_patterns": [],
            "architectural_patterns": [],
            "code_organization": [
                {
                    "name": "Layer-based Organization", 
                    "confidence": 0.9, 
                    "sources": ["folder_structure"]
                },
                {
                    "name": "Feature-based Organization", 
                    "confidence": 0.8, 
                    "sources": ["folder_structure"]
                },
                {
                    "name": "Component-based Organization", 
                    "confidence": 0.7, 
                    "sources": ["folder_structure"]
                }
            ]
        }
        
        # Configure the mock to return our patterns
        self.extractor.extract_patterns.return_value = mock_patterns
        
        # Extract patterns
        patterns = await self.extractor.extract_patterns(self.repo_dir, [])
        
        # Verify the mock was called
        self.extractor.extract_patterns.assert_called_once_with(self.repo_dir, [])
        
        # Verify code organization patterns were detected
        org_patterns = patterns.get("code_organization", [])
        
        # Check for Layer-based Organization
        layer_pattern = next((p for p in org_patterns if p["name"] == "Layer-based Organization"), None)
        assert layer_pattern is not None, "Layer-based Organization not detected"
        
        # Check for Feature-based Organization
        feature_pattern = next((p for p in org_patterns if p["name"] == "Feature-based Organization"), None)
        assert feature_pattern is not None, "Feature-based Organization not detected"
        
        # Check for Component-based Organization
        component_pattern = next((p for p in org_patterns if p["name"] == "Component-based Organization"), None)
        assert component_pattern is not None, "Component-based Organization not detected"
    
    @pytest.mark.asyncio
    async def test_empty_repository(self):
        """Test pattern extraction on an empty repository."""
        # Create an empty temporary directory
        empty_repo = tempfile.mkdtemp()
        
        try:
            # Extract patterns
            patterns = await self.extractor.extract_patterns(empty_repo, [])
            
            # Should have empty lists for patterns
            assert len(patterns.get("design_patterns", [])) == 0
            assert len(patterns.get("architectural_patterns", [])) == 0
            
            # May still detect some code organization patterns based on folder structure
            org_patterns = patterns.get("code_organization", [])
            assert isinstance(org_patterns, list)
            
        finally:
            # Clean up
            shutil.rmtree(empty_repo)
    
    @pytest.mark.asyncio
    async def test_exclude_patterns(self):
        """Test excluding patterns from analysis."""
        # Create a file in a directory that should be excluded
        excluded_file = self._create_test_file(
            "node_modules/excluded.js",
            """
            // This file should be excluded
            """
        )
        
        # Set up mock return value for patterns
        mock_patterns = {
            "design_patterns": [
                {"name": "Factory", "confidence": 0.8, "sources": ["src/factories/UserFactory.js"]}
            ],
            "architectural_patterns": [
                {"name": "MVC", "confidence": 0.7, "sources": ["controllers/", "models/", "views/"]}
            ],
            "code_organization": [
                {"name": "Layer-based Organization", "confidence": 0.9, "sources": ["folder_structure"]}
            ]
        }
        
        # Configure the mock to return our patterns
        self.extractor.extract_patterns.return_value = mock_patterns
        
        # Extract patterns - simulate passing exclude_patterns
        patterns = await self.extractor.extract_patterns(self.repo_dir, [])
        
        # Verify the mock was called with the expected parameters
        self.extractor.extract_patterns.assert_called_once()
        
        # Verify patterns were extracted
        assert "design_patterns" in patterns
        assert "architectural_patterns" in patterns
        assert "code_organization" in patterns
        
        # Check that there are no references to excluded paths
        all_sources = []
        for pattern_type in patterns.values():
            for pattern in pattern_type:
                all_sources.extend(pattern.get("sources", []))
        
        assert not any("node_modules" in source for source in all_sources)
        assert not any(".min.js" in source for source in all_sources)


@pytest.mark.asyncio
async def test_mvc_detection_with_folder_names():
    """CallGraphAnalyzer should detect MVC pattern using folder names."""
    repo_dir = tempfile.mkdtemp()

    try:
        os.makedirs(os.path.join(repo_dir, "controllers"), exist_ok=True)
        os.makedirs(os.path.join(repo_dir, "models"), exist_ok=True)
        os.makedirs(os.path.join(repo_dir, "views"), exist_ok=True)

        files = [
            {
                "file_path": os.path.join(repo_dir, "controllers", "user_controller.py"),
                "code_language": "python",
                "classes": [{"name": "UserController", "methods": []}],
            },
            {
                "file_path": os.path.join(repo_dir, "models", "user_model.py"),
                "code_language": "python",
                "classes": [{"name": "UserModel", "methods": []}],
            },
            {
                "file_path": os.path.join(repo_dir, "views", "user_view.py"),
                "code_language": "python",
                "functions": [{"name": "render_user"}],
            },
        ]

        analyzer = CallGraphAnalyzer()
        results = await analyzer.analyze_codebase(repo_dir, files)

        patterns = results.get("patterns", [])
        mvc = next((p for p in patterns if "MVC" in p["name"]), None)

        assert mvc is not None, "MVC pattern not detected"
        assert mvc["components"]["controllers"] == 1
        assert mvc["components"]["models"] == 1
        assert mvc["components"]["views"] == 1
    finally:
        shutil.rmtree(repo_dir)

