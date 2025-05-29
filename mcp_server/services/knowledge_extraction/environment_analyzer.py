"""
Environment Analyzer for MCP Server

This module provides environment and dependency analysis capabilities.
It analyzes project dependencies, environment configurations, and system
requirements to provide insights about the development environment.
"""

import os
import logging
import re
import json
import asyncio
import subprocess
from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path

class EnvironmentAnalyzer:
    """Analyzes project environment and dependencies"""
    
    def __init__(self):
        """Initialize the environment analyzer"""
        self.logger = logging.getLogger("mcp_server.services.knowledge_extraction.environment_analyzer")
    
    async def analyze_environment(
        self,
        repo_path: str,
        repo_languages: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Analyze the project environment and dependencies
        
        Args:
            repo_path: Path to the repository
            repo_languages: Optional list of programming languages used in the repo
            
        Returns:
            Analysis results
        """
        self.logger.info(f"Starting environment analysis for repository: {repo_path}")
        
        # Initialize results
        results = {
            "dependencies": {},
            "environment_configs": [],
            "build_systems": [],
            "runtime_requirements": {},
            "package_managers": [],
            "container_configs": []
        }
        
        # Analyze package managers and dependencies
        await self._analyze_dependencies(repo_path, results)
        
        # Analyze environment configurations
        await self._analyze_env_configs(repo_path, results)
        
        # Analyze build systems
        await self._analyze_build_systems(repo_path, results)
        
        # Analyze containerization configs
        await self._analyze_container_configs(repo_path, results)
        
        # Analyze CI/CD configurations
        await self._analyze_cicd_configs(repo_path, results)
        
        return results
    
    async def _analyze_dependencies(
        self, 
        repo_path: str, 
        results: Dict[str, Any]
    ) -> None:
        """Analyze dependencies and package managers
        
        Args:
            repo_path: Path to the repository
            results: Results dictionary to update
        """
        # Check for Node.js dependencies
        package_json_path = os.path.join(repo_path, "package.json")
        if os.path.exists(package_json_path):
            try:
                with open(package_json_path, 'r', encoding='utf-8') as f:
                    package_data = json.load(f)
                
                # Add Node.js as a package manager
                if "package_managers" not in results:
                    results["package_managers"] = []
                results["package_managers"].append("npm/yarn")
                
                # Extract dependencies
                if "dependencies" not in results:
                    results["dependencies"] = {}
                
                results["dependencies"]["node"] = {
                    "dependencies": package_data.get("dependencies", {}),
                    "dev_dependencies": package_data.get("devDependencies", {}),
                    "peer_dependencies": package_data.get("peerDependencies", {})
                }
                
                # Check for specific frameworks
                if package_data.get("dependencies", {}).get("react"):
                    results["dependencies"]["frameworks"] = results.get("dependencies", {}).get("frameworks", [])
                    results["dependencies"]["frameworks"].append("React")
                
                if package_data.get("dependencies", {}).get("@angular/core"):
                    results["dependencies"]["frameworks"] = results.get("dependencies", {}).get("frameworks", [])
                    results["dependencies"]["frameworks"].append("Angular")
                
                if package_data.get("dependencies", {}).get("vue"):
                    results["dependencies"]["frameworks"] = results.get("dependencies", {}).get("frameworks", [])
                    results["dependencies"]["frameworks"].append("Vue.js")
                
                # Node.js runtime requirements
                results["runtime_requirements"]["node"] = {
                    "engines": package_data.get("engines", {})
                }
            except Exception as e:
                self.logger.warning(f"Error parsing package.json: {str(e)}")
        
        # Check for yarn
        yarn_lock_path = os.path.join(repo_path, "yarn.lock")
        if os.path.exists(yarn_lock_path):
            if "yarn" not in results.get("package_managers", []):
                results["package_managers"].append("yarn")
        
        # Check for Python dependencies
        requirements_path = os.path.join(repo_path, "requirements.txt")
        if os.path.exists(requirements_path):
            try:
                with open(requirements_path, 'r', encoding='utf-8') as f:
                    requirements = f.read()
                
                # Add pip as a package manager
                if "package_managers" not in results:
                    results["package_managers"] = []
                if "pip" not in results["package_managers"]:
                    results["package_managers"].append("pip")
                
                # Parse requirements
                python_deps = {}
                for line in requirements.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Handle requirements with version specifiers
                        parts = re.split(r'[=<>~]', line, 1)
                        package = parts[0].strip()
                        version = parts[1].strip() if len(parts) > 1 else "latest"
                        python_deps[package] = version
                
                # Add Python dependencies
                if "dependencies" not in results:
                    results["dependencies"] = {}
                
                results["dependencies"]["python"] = {
                    "requirements": python_deps
                }
                
                # Check for specific frameworks
                if "django" in python_deps:
                    results["dependencies"]["frameworks"] = results.get("dependencies", {}).get("frameworks", [])
                    results["dependencies"]["frameworks"].append("Django")
                
                if "flask" in python_deps:
                    results["dependencies"]["frameworks"] = results.get("dependencies", {}).get("frameworks", [])
                    results["dependencies"]["frameworks"].append("Flask")
                
                if "fastapi" in python_deps:
                    results["dependencies"]["frameworks"] = results.get("dependencies", {}).get("frameworks", [])
                    results["dependencies"]["frameworks"].append("FastAPI")
            except Exception as e:
                self.logger.warning(f"Error parsing requirements.txt: {str(e)}")
        
        # Check for Pipenv
        pipfile_path = os.path.join(repo_path, "Pipfile")
        if os.path.exists(pipfile_path):
            if "package_managers" not in results:
                results["package_managers"] = []
            if "pipenv" not in results["package_managers"]:
                results["package_managers"].append("pipenv")
        
        # Check for Poetry
        pyproject_toml_path = os.path.join(repo_path, "pyproject.toml")
        if os.path.exists(pyproject_toml_path):
            try:
                with open(pyproject_toml_path, 'r', encoding='utf-8') as f:
                    pyproject_content = f.read()
                
                if "[tool.poetry]" in pyproject_content:
                    if "package_managers" not in results:
                        results["package_managers"] = []
                    if "poetry" not in results["package_managers"]:
                        results["package_managers"].append("poetry")
            except Exception as e:
                self.logger.warning(f"Error reading pyproject.toml: {str(e)}")
        
        # Check for .NET dependencies
        csproj_files = []
        for root, dirs, files in os.walk(repo_path):
            for file in files:
                if file.endswith(".csproj"):
                    csproj_files.append(os.path.join(root, file))
        
        if csproj_files:
            # Add .NET as a package manager
            if "package_managers" not in results:
                results["package_managers"] = []
            if "nuget" not in results["package_managers"]:
                results["package_managers"].append("nuget")
            
            # Parse .csproj files for dependencies
            dotnet_deps = {}
            for csproj_file in csproj_files:
                try:
                    with open(csproj_file, 'r', encoding='utf-8') as f:
                        csproj_content = f.read()
                    
                    # Extract package references
                    package_refs = re.findall(r'<PackageReference\s+Include="([^"]+)"\s+Version="([^"]+)"', csproj_content)
                    
                    for package, version in package_refs:
                        dotnet_deps[package] = version
                except Exception as e:
                    self.logger.warning(f"Error parsing .csproj file {csproj_file}: {str(e)}")
            
            # Add .NET dependencies
            if "dependencies" not in results:
                results["dependencies"] = {}
            
            results["dependencies"]["dotnet"] = {
                "packages": dotnet_deps
            }
            
            # Check for specific frameworks
            if any("Microsoft.AspNetCore" in package for package in dotnet_deps.keys()):
                results["dependencies"]["frameworks"] = results.get("dependencies", {}).get("frameworks", [])
                results["dependencies"]["frameworks"].append("ASP.NET Core")
        
        # Check for Java dependencies (Maven)
        pom_xml_path = os.path.join(repo_path, "pom.xml")
        if os.path.exists(pom_xml_path):
            # Add Maven as a package manager
            if "package_managers" not in results:
                results["package_managers"] = []
            if "maven" not in results["package_managers"]:
                results["package_managers"].append("maven")
            
            # We'd need a proper XML parser for full pom.xml parsing, which is beyond scope here
            # Just note that Maven is used
            if "dependencies" not in results:
                results["dependencies"] = {}
            
            results["dependencies"]["java"] = {
                "uses_maven": True
            }
        
        # Check for Gradle
        gradle_path = os.path.join(repo_path, "build.gradle")
        if os.path.exists(gradle_path):
            # Add Gradle as a package manager
            if "package_managers" not in results:
                results["package_managers"] = []
            if "gradle" not in results["package_managers"]:
                results["package_managers"].append("gradle")
            
            # Note that Gradle is used
            if "dependencies" not in results:
                results["dependencies"] = {}
            
            if "java" not in results["dependencies"]:
                results["dependencies"]["java"] = {}
            
            results["dependencies"]["java"]["uses_gradle"] = True
    
    async def _analyze_env_configs(
        self, 
        repo_path: str, 
        results: Dict[str, Any]
    ) -> None:
        """Analyze environment configurations
        
        Args:
            repo_path: Path to the repository
            results: Results dictionary to update
        """
        # Check for .env files
        env_files = []
        for root, dirs, files in os.walk(repo_path):
            for file in files:
                if file.startswith(".env") or file.endswith(".env"):
                    env_files.append(os.path.join(root, file))
        
        for env_file in env_files:
            try:
                with open(env_file, 'r', encoding='utf-8') as f:
                    env_content = f.read()
                
                # Extract environment variable names (but not values for security)
                env_vars = []
                for line in env_content.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split('=', 1)
                        if len(parts) > 0:
                            env_vars.append(parts[0].strip())
                
                # Add to results
                results["environment_configs"].append({
                    "file": os.path.relpath(env_file, repo_path),
                    "variables": env_vars
                })
            except Exception as e:
                self.logger.warning(f"Error parsing env file {env_file}: {str(e)}")
        
        # Check for config files
        config_patterns = [
            "config.json", "config.yaml", "config.yml", "config.xml",
            "appsettings.json", "application.properties", "application.yml"
        ]
        
        for root, dirs, files in os.walk(repo_path):
            for file in files:
                if any(file.endswith(pattern) or file == pattern for pattern in config_patterns):
                    config_file = os.path.join(root, file)
                    try:
                        with open(config_file, 'r', encoding='utf-8') as f:
                            config_content = f.read()
                        
                        # Add to results (without parsing the content for security)
                        results["environment_configs"].append({
                            "file": os.path.relpath(config_file, repo_path),
                            "type": "config"
                        })
                    except Exception as e:
                        self.logger.warning(f"Error reading config file {config_file}: {str(e)}")
    
    async def _analyze_build_systems(
        self, 
        repo_path: str, 
        results: Dict[str, Any]
    ) -> None:
        """Analyze build systems
        
        Args:
            repo_path: Path to the repository
            results: Results dictionary to update
        """
        # Check for webpack
        webpack_config_path = os.path.join(repo_path, "webpack.config.js")
        if os.path.exists(webpack_config_path):
            results["build_systems"].append("webpack")
        
        # Check for Babel
        babel_config_path = os.path.join(repo_path, ".babelrc")
        if os.path.exists(babel_config_path):
            results["build_systems"].append("babel")
        
        # Check for TypeScript
        tsconfig_path = os.path.join(repo_path, "tsconfig.json")
        if os.path.exists(tsconfig_path):
            results["build_systems"].append("typescript")
        
        # Check for Make
        makefile_path = os.path.join(repo_path, "Makefile")
        if os.path.exists(makefile_path):
            results["build_systems"].append("make")
        
        # Check for MSBuild
        if any(file.endswith(".sln") for file in os.listdir(repo_path) if os.path.isfile(os.path.join(repo_path, file))):
            results["build_systems"].append("msbuild")
        
        # Check for Maven
        if os.path.exists(os.path.join(repo_path, "pom.xml")):
            results["build_systems"].append("maven")
        
        # Check for Gradle
        if os.path.exists(os.path.join(repo_path, "build.gradle")):
            results["build_systems"].append("gradle")
        
        # Check for npm scripts
        package_json_path = os.path.join(repo_path, "package.json")
        if os.path.exists(package_json_path):
            try:
                with open(package_json_path, 'r', encoding='utf-8') as f:
                    package_data = json.load(f)
                
                if "scripts" in package_data and package_data["scripts"]:
                    results["build_systems"].append("npm-scripts")
                    
                    # Add specific scripts
                    results["npm_scripts"] = package_data["scripts"]
            except Exception as e:
                self.logger.warning(f"Error parsing package.json for scripts: {str(e)}")
    
    async def _analyze_container_configs(
        self, 
        repo_path: str, 
        results: Dict[str, Any]
    ) -> None:
        """Analyze containerization configurations
        
        Args:
            repo_path: Path to the repository
            results: Results dictionary to update
        """
        # Check for Docker
        dockerfile_path = os.path.join(repo_path, "Dockerfile")
        if os.path.exists(dockerfile_path):
            try:
                with open(dockerfile_path, 'r', encoding='utf-8') as f:
                    dockerfile_content = f.read()
                
                # Extract base image
                base_image_match = re.search(r'FROM\s+(.+)', dockerfile_content)
                base_image = base_image_match.group(1) if base_image_match else "unknown"
                
                # Add to results
                results["container_configs"].append({
                    "type": "docker",
                    "file": "Dockerfile",
                    "base_image": base_image
                })
            except Exception as e:
                self.logger.warning(f"Error parsing Dockerfile: {str(e)}")
        
        # Check for docker-compose
        docker_compose_path = os.path.join(repo_path, "docker-compose.yml")
        if not os.path.exists(docker_compose_path):
            docker_compose_path = os.path.join(repo_path, "docker-compose.yaml")
        
        if os.path.exists(docker_compose_path):
            results["container_configs"].append({
                "type": "docker-compose",
                "file": os.path.basename(docker_compose_path)
            })
        
        # Check for Kubernetes
        kubernetes_dir = os.path.join(repo_path, "kubernetes")
        if os.path.exists(kubernetes_dir) and os.path.isdir(kubernetes_dir):
            results["container_configs"].append({
                "type": "kubernetes",
                "directory": "kubernetes"
            })
        
        # Check for other k8s files in the repo
        k8s_files = []
        for root, dirs, files in os.walk(repo_path):
            for file in files:
                if file.endswith(".yaml") or file.endswith(".yml"):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Simple check for Kubernetes manifest
                        if "apiVersion:" in content and "kind:" in content:
                            if "kind: Deployment" in content or "kind: Service" in content or "kind: Pod" in content:
                                k8s_files.append(os.path.relpath(file_path, repo_path))
                    except Exception as e:
                        pass  # Silently skip files that can't be read
        
        if k8s_files:
            results["container_configs"].append({
                "type": "kubernetes",
                "files": k8s_files
            })
    
    async def _analyze_cicd_configs(
        self, 
        repo_path: str, 
        results: Dict[str, Any]
    ) -> None:
        """Analyze CI/CD configurations
        
        Args:
            repo_path: Path to the repository
            results: Results dictionary to update
        """
        # Check for GitHub Actions
        github_workflows_dir = os.path.join(repo_path, ".github", "workflows")
        if os.path.exists(github_workflows_dir) and os.path.isdir(github_workflows_dir):
            workflow_files = [f for f in os.listdir(github_workflows_dir) 
                             if os.path.isfile(os.path.join(github_workflows_dir, f)) 
                             and (f.endswith(".yml") or f.endswith(".yaml"))]
            
            if workflow_files:
                if "ci_cd" not in results:
                    results["ci_cd"] = []
                
                results["ci_cd"].append({
                    "type": "github_actions",
                    "workflow_files": workflow_files
                })
        
        # Check for GitLab CI
        gitlab_ci_path = os.path.join(repo_path, ".gitlab-ci.yml")
        if os.path.exists(gitlab_ci_path):
            if "ci_cd" not in results:
                results["ci_cd"] = []
            
            results["ci_cd"].append({
                "type": "gitlab_ci",
                "file": ".gitlab-ci.yml"
            })
        
        # Check for Jenkins
        jenkinsfile_path = os.path.join(repo_path, "Jenkinsfile")
        if os.path.exists(jenkinsfile_path):
            if "ci_cd" not in results:
                results["ci_cd"] = []
            
            results["ci_cd"].append({
                "type": "jenkins",
                "file": "Jenkinsfile"
            })
        
        # Check for Travis CI
        travis_path = os.path.join(repo_path, ".travis.yml")
        if os.path.exists(travis_path):
            if "ci_cd" not in results:
                results["ci_cd"] = []
            
            results["ci_cd"].append({
                "type": "travis_ci",
                "file": ".travis.yml"
            })
        
        # Check for Azure Pipelines
        azure_pipelines_path = os.path.join(repo_path, "azure-pipelines.yml")
        if os.path.exists(azure_pipelines_path):
            if "ci_cd" not in results:
                results["ci_cd"] = []
            
            results["ci_cd"].append({
                "type": "azure_pipelines",
                "file": "azure-pipelines.yml"
            })
