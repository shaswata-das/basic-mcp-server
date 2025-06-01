#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test Claude API service.
"""

import asyncio
import sys
import os
import time
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from mcp_server.services.claude_service import ClaudeService, MockClaudeService

async def test_mock_claude():
    """Test the MockClaudeService."""
    print("\n=== TESTING MOCK CLAUDE SERVICE ===")
    
    # Create mock service (no API key needed)
    mock_service = MockClaudeService()
    
    # Test text generation
    prompt = "Explain what a vector database is in one sentence."
    print(f"Testing prompt: '{prompt}'")
    
    response = await mock_service.generate_text(prompt)
    print(f"Mock response: {response}")
    
    # Test streaming (mock doesn't actually stream)
    stream_response = await mock_service.generate_stream(prompt)
    print(f"Mock stream response: {stream_response}")
    
    return True

async def test_real_claude():
    """Test the real Claude service if API key is available."""
    print("\n=== TESTING REAL CLAUDE SERVICE ===")
    
    # Load environment variables
    load_dotenv()
    
    # Get API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY")
    
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not found in environment. Skipping real Claude test.")
        return False
    
    try:
        # Create service with API key
        service = ClaudeService(api_key=api_key)
        
        # Test text generation
        prompt = "Explain what a vector database is in one sentence."
        print(f"Testing prompt: '{prompt}'")
        
        start_time = time.time()
        response = await service.generate_text(
            prompt=prompt,
            max_tokens=100,
            temperature=0.7
        )
        
        elapsed_time = time.time() - start_time
        print(f"✅ Response received in {elapsed_time:.2f} seconds")
        print(f"✅ Response: {response}")
        
        return True
        
    except Exception as e:
        print(f"❌ Claude API test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Run the async tests
    print("Testing mock Claude service...")
    asyncio.run(test_mock_claude())
    
    print("\nTesting real Claude service...")
    result = asyncio.run(test_real_claude())
    
    # Exit with appropriate code
    sys.exit(0 if result else 1)