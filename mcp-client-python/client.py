import asyncio
import os
from typing import List, Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from google import genai  # Update import to use google.genai
from google.genai import types  # Import types for tool configuration
from dotenv import load_dotenv

import utils

load_dotenv()  # load environment variables from .env

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.gemini_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))  # Initialize genai.Client
        self.mcp_tools = None
        self.chat = None

    async def initialize_chat(self):
        if not self.session:
            raise RuntimeError("Client session is not initialized")

        self.mcp_tools = await self.session.list_tools()
        tools = [
            types.Tool(
                function_declarations=[
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": {
                            k: v
                            for k, v in tool.inputSchema.items()
                            if k not in ["additionalProperties", "$schema"]
                        },
                    }
                ]
            )
            for tool in self.mcp_tools.tools
        ]

        config = types.GenerateContentConfig(tools=tools)

        # Initial Gemini API call
        self.chat = self.gemini_client.chats.create(
            model="gemini-2.0-flash",
            config=config
        )


    async def connect_to_server(self, server_config_path: str):
        """Connect to an MCP server
        
        Args:
            server_script_path: Path to the server script (.py or .js)
        """
            
        server_params = utils.parse_config(server_config_path)
        
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        
        await self.session.initialize() # type: ignore
        
        # List available tools
        if not self.session:
            raise RuntimeError("Client session is not initialized")
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        """Process a query using Gemini and available tools"""

        # See this for reference.
        # https://ai.google.dev/gemini-api/docs/function-calling?example=meeting
        if not self.session:
            raise RuntimeError("Client session is not initialized")

        if not self.chat:
            await self.initialize_chat()

        response = self.chat.send_message(query)
        final_text = []

        for part in response.candidates[0].content.parts:
            if part.function_call:
                function_call = part.function_call
                tool_name = function_call.name
                tool_args = function_call.args

                # Execute tool call
                result = await self.session.call_tool(tool_name, tool_args)
                final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")
                final_text.append(f"[Tool result: {result.content}]")
                response = self.chat.send_message(result.content[0].text)
                final_text.append(response.text)
            else:
                final_text.append(part.text)

        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")
        
        while True:
            try:
                query = input("\nQuery: ").strip()
                
                if query.lower() == 'quit':
                    break
                    
                response = await self.process_query(query)
                print("\n" + response)
                    
            except Exception as e:
                print(f"\nError: {str(e)}")
    
    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)
        
    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    import sys
    asyncio.run(main())
