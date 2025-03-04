import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent

from langchain_openai import AzureChatOpenAI
from langchain_openai import ChatOpenAI

async def main():
    model = AzureChatOpenAI(
        azure_deployment="gpt-4o",  # Replace with your deployment name
        api_version="2024-08-01-preview",  # Use the correct API version
        temperature=0
    )

    server_params = StdioServerParameters(
        command="python",
        # Make sure to update to the full absolute path to your math_server.py file
        args=["./math_server.py"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            # Get tools
            tools = await load_mcp_tools(session)

            # Create and run the agent
            agent = create_react_agent(model, tools)
            agent_response = await agent.ainvoke({"messages": "what's (3 + 5) x 12?"})
            print("**********")
            print(agent_response)

# Run the main function
asyncio.run(main())