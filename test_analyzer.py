"""
Test script for enhanced knowledge extractors and documentation building
"""

import os
import asyncio
import json
from pathlib import Path

from mcp_server.services.knowledge_extraction.environment_analyzer import EnvironmentAnalyzer
from mcp_server.services.knowledge_extraction.pattern_extractor import PatternExtractor
from mcp_server.services.knowledge_extraction.code_extractor import CodeExtractor
from mcp_server.services.knowledge_extraction.md_builder import MarkdownBuilder

async def main():
    # Set repository path
    repo_path = "C:/workstation/orbitax-platform-api-fork"
    
    # Create output directory
    output_dir = os.path.join(os.path.dirname(__file__), "analysis_output")
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Analyzing repository: {repo_path}")
    print(f"Output directory: {output_dir}")
    
    # Initialize extractors
    env_analyzer = EnvironmentAnalyzer()
    pattern_analyzer = PatternExtractor()
    code_extractor = CodeExtractor()
    md_builder = MarkdownBuilder()
    
    # Analyze environment
    print("Analyzing environment...")
    env_results = await env_analyzer.analyze_environment(repo_path)
    
    # Save environment results
    with open(os.path.join(output_dir, "environment.json"), "w", encoding="utf-8") as f:
        json.dump(env_results, f, indent=2)
    
    print(f"Environment analysis complete. Found {len(env_results.get('package_managers', []))} package managers.")
    
    # Extract code patterns
    print("Extracting patterns...")
    pattern_results = await pattern_analyzer.extract_patterns(repo_path, [])
    
    # Save pattern results
    with open(os.path.join(output_dir, "patterns.json"), "w", encoding="utf-8") as f:
        json.dump(pattern_results, f, indent=2)
    
    print(f"Pattern extraction complete. Found {len(pattern_results.get('code_organization', []))} code organization patterns.")
    
    # Extract code from a few sample files
    print("Extracting code knowledge from sample files...")
    sample_files = []
    
    # Find 5 sample C# files
    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith(".cs"):
                sample_files.append(os.path.join(root, file))
                if len(sample_files) >= 5:
                    break
        if len(sample_files) >= 5:
            break
    
    # Extract knowledge from sample files
    file_results = []
    for file_path in sample_files:
        print(f"Processing file: {file_path}")
        result = await code_extractor.extract_knowledge_from_file(file_path, "csharp")
        print(f"  Found {len(result.get('classes', []))} classes")
        file_results.append({
            "file_path": file_path,
            "result": result
        })
    
    # Save code extraction results
    with open(os.path.join(output_dir, "code_samples.json"), "w", encoding="utf-8") as f:
        json.dump(file_results, f, indent=2)
    
    print(f"Code extraction complete. Processed {len(file_results)} files.")
    
    # Build Markdown documentation
    print("Building documentation...")
    knowledge = {
        "repo_name": os.path.basename(repo_path),
        "file_count": len(file_results),
        "patterns": pattern_results,
        "environment": env_results,
        "files": [item["result"] for item in file_results]
    }
    
    result = await md_builder.generate_documentation(
        repo_id="sample-repo",
        extracted_knowledge=knowledge,
        output_dir=output_dir
    )
    
    print(f"Documentation generated successfully.")
    print(f"Documentation available at: {os.path.join(output_dir, 'docs')}")
    print(f"All analysis results saved to {output_dir}")

if __name__ == "__main__":
    asyncio.run(main())