#!/usr/bin/env python
"""
Script to run the test suite for the MCP Server.
"""
import os
import sys
import subprocess
import argparse
import time

def run_tests(test_path=None, verbose=False, coverage=False, integration=False, ollama=True):
    """Run the test suite.
    
    Args:
        test_path: Optional path to specific test file or directory
        verbose: Enable verbose output
        coverage: Generate coverage report
        integration: Run integration tests
        ollama: Enable Ollama integration tests
    """
    print("Running MCP Server tests...")
    
    # Set environment variables for tests
    os.environ["OLLAMA_URL"] = "http://localhost:5656" if ollama else ""
    
    # Determine test command
    cmd = ["pytest"]
    
    # Add options
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend(["--cov=mcp_server", "--cov-report=term", "--cov-report=html"])
    
    # Add test path if specified
    if test_path:
        cmd.append(test_path)
    elif integration:
        # Run only integration tests
        cmd.extend([
            "tests/test_ollama_embeddings.py",
            "tests/test_mongodb_integration.py",
            "tests/test_codebase_analysis.py"
        ])
    else:
        cmd.append("tests/")
    
    start_time = time.time()
    
    # Run tests
    try:
        subprocess.run(cmd, check=True)
        elapsed_time = time.time() - start_time
        print(f"\nAll tests completed successfully in {elapsed_time:.2f} seconds!")
        
        if coverage:
            print("\nCoverage report generated. See htmlcov/index.html for details.")
        
        return 0
    except subprocess.CalledProcessError as e:
        elapsed_time = time.time() - start_time
        print(f"\nTest run failed with exit code {e.returncode} after {elapsed_time:.2f} seconds")
        return e.returncode

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run MCP Server tests")
    parser.add_argument("test_path", nargs="?", help="Path to specific test file or directory")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--no-ollama", dest="ollama", action="store_false", 
                        help="Disable Ollama integration tests")
    parser.add_argument("--ollama-url", default="http://localhost:5656",
                        help="URL for Ollama API (default: http://localhost:5656)")
    
    args = parser.parse_args()
    
    # Set Ollama URL from argument
    if args.ollama:
        os.environ["OLLAMA_URL"] = args.ollama_url
    
    sys.exit(run_tests(
        args.test_path, 
        args.verbose, 
        args.coverage, 
        args.integration,
        args.ollama
    ))
