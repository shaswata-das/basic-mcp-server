#!/usr/bin/env python3
"""
Example client for the MCP Server

This script demonstrates how to communicate with the MCP server using JSON-RPC.
"""

import json
import socket
import sys
import argparse


def send_request(request, host="127.0.0.1", port=9000):
    """Send a JSON-RPC request to the server and return the response"""
    # Create a socket connection
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        # Connect to the server
        sock.connect((host, port))
        
        # Send the request
        request_json = json.dumps(request) + "\n"
        sock.sendall(request_json.encode('utf-8'))
        
        # Receive the response
        response_data = sock.recv(65536).decode('utf-8')
        
        # Parse the JSON response
        response = json.loads(response_data)
        return response
    
    except ConnectionRefusedError:
        print(f"Error: Could not connect to server at {host}:{port}")
        print("Make sure the server is running in TCP mode with: python mcp_server.py --tcp")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        sock.close()


def initialize():
    """Initialize connection with the server"""
    request = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "id": 1
    }
    return send_request(request)


def list_tools():
    """List available tools"""
    request = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "id": 2
    }
    return send_request(request)


def echo(text):
    """Call the echo tool"""
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "echo",
            "arguments": {
                "text": text
            }
        },
        "id": 3
    }
    return send_request(request)


def calculate(expression):
    """Call the calculate tool"""
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "calculate",
            "arguments": {
                "expression": expression
            }
        },
        "id": 4
    }
    return send_request(request)


def ask_ai(prompt, service_name=None, model=None, max_tokens=None, temperature=None, system=None):
    """Call any available AI service
    
    Args:
        prompt: The message to send to the AI
        service_name: AI service to use (claude, openai, mock, etc.) - optional, uses server default if not specified
        model: Model to use - optional, uses service default if not specified
        max_tokens: Maximum tokens - optional, uses service default if not specified
        temperature: Temperature - optional, uses service default if not specified
        system: System prompt - optional
    """
    args = {"prompt": prompt}
    if service_name:
        args["service_name"] = service_name
    if model:
        args["model"] = model
    if max_tokens:
        args["max_tokens"] = max_tokens
    if temperature:
        args["temperature"] = temperature
    if system:
        args["system"] = system
    
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "ai/message",
            "arguments": args
        },
        "id": 5
    }
    return send_request(request)


def ask_claude(prompt, model=None, max_tokens=None, temperature=None, system=None):
    """Call Claude API specifically (backward compatibility)"""
    return ask_ai(prompt, "claude", model, max_tokens, temperature, system)


def ask_openai(prompt, model=None, max_tokens=None, temperature=None, system=None):
    """Call OpenAI API specifically (backward compatibility)"""
    return ask_ai(prompt, "openai", model, max_tokens, temperature, system)


def system_info():
    """Get system information"""
    request = {
        "jsonrpc": "2.0",
        "method": "system/info",
        "id": 7
    }
    return send_request(request)


def system_health():
    """Check system health"""
    request = {
        "jsonrpc": "2.0",
        "method": "system/health",
        "id": 8
    }
    return send_request(request)


def print_json(data):
    """Pretty print JSON data"""
    print(json.dumps(data, indent=2))


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='MCP Server Example Client')
    parser.add_argument('--host', default='127.0.0.1', help='Server host address')
    parser.add_argument('--port', type=int, default=9000, help='Server port')
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Initialize command
    subparsers.add_parser('initialize', help='Initialize connection')
    
    # List tools command
    subparsers.add_parser('list-tools', help='List available tools')
    
    # Echo command
    echo_parser = subparsers.add_parser('echo', help='Echo text')
    echo_parser.add_argument('text', help='Text to echo')
    
    # Calculate command
    calc_parser = subparsers.add_parser('calculate', help='Calculate expression')
    calc_parser.add_argument('expression', help='Expression to calculate')
    
    # General AI command (can specify service)
    ai_parser = subparsers.add_parser('ask', help='Ask any AI service')
    ai_parser.add_argument('prompt', help='Prompt to send to the AI')
    ai_parser.add_argument('--service', dest='service_name', help='AI service to use (claude, openai, mock) - uses default if not specified')
    ai_parser.add_argument('--model', help='Model to use - uses service default if not specified')
    ai_parser.add_argument('--max-tokens', type=int, help='Maximum tokens - uses service default if not specified')
    ai_parser.add_argument('--temperature', type=float, help='Temperature - uses service default if not specified')
    ai_parser.add_argument('--system', help='System prompt (optional)')
    
    # Claude command (for backward compatibility)
    claude_parser = subparsers.add_parser('ask-claude', help='Ask Claude specifically')
    claude_parser.add_argument('prompt', help='Prompt to send to Claude')
    claude_parser.add_argument('--model', help='Claude model to use')
    claude_parser.add_argument('--max-tokens', type=int, help='Maximum tokens')
    claude_parser.add_argument('--temperature', type=float, help='Temperature')
    claude_parser.add_argument('--system', help='System prompt')
    
    # OpenAI command (for backward compatibility)
    openai_parser = subparsers.add_parser('ask-openai', help='Ask OpenAI specifically')
    openai_parser.add_argument('prompt', help='Prompt to send to OpenAI')
    openai_parser.add_argument('--model', help='OpenAI model to use')
    openai_parser.add_argument('--max-tokens', type=int, help='Maximum tokens')
    openai_parser.add_argument('--temperature', type=float, help='Temperature')
    openai_parser.add_argument('--system', help='System prompt')
    
    # System info command
    subparsers.add_parser('system-info', help='Get system information')
    
    # System health command
    subparsers.add_parser('system-health', help='Check system health')
    
    args = parser.parse_args()
    
    # Execute the appropriate command
    if args.command == 'initialize':
        print_json(initialize())
    elif args.command == 'list-tools':
        print_json(list_tools())
    elif args.command == 'echo':
        print_json(echo(args.text))
    elif args.command == 'calculate':
        print_json(calculate(args.expression))
    elif args.command == 'ask':
        print_json(ask_ai(
            args.prompt,
            args.service_name,
            args.model,
            args.max_tokens,
            args.temperature,
            args.system
        ))
    elif args.command == 'ask-claude':
        print_json(ask_claude(
            args.prompt, 
            args.model, 
            args.max_tokens, 
            args.temperature, 
            args.system
        ))
    elif args.command == 'ask-openai':
        print_json(ask_openai(
            args.prompt, 
            args.model, 
            args.max_tokens, 
            args.temperature, 
            args.system
        ))
    elif args.command == 'system-info':
        print_json(system_info())
    elif args.command == 'system-health':
        print_json(system_health())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()