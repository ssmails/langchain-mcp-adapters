import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient

from langgraph.prebuilt import create_react_agent

from langchain_openai import AzureChatOpenAI
from langchain_openai import ChatOpenAI

async def main():
    model = AzureChatOpenAI(
        azure_deployment="gpt-4o",  # Replace with your deployment name
        api_version="2024-08-01-preview",  # Use the correct API version
        temperature=0
    )

    async with MultiServerMCPClient(
            {
              "math": {
                "command": "python",
                # Make sure to update to the full absolute path to your math_server.py file
                "args": ["./math_server.py"],
                "transport": "stdio",
              },
              "jira": {
                # make sure you start your weather server on port 8000
                "url": "http://localhost:9000/sse",
                "transport": "sse"
              }
            }
    ) as client:
      agent = create_react_agent(model, client.get_tools())
      agent_response = await agent.ainvoke({"messages": "get tickets under project APT"})
      print(agent_response)

    # async with stdio_client(server_params) as (read, write):
    #     async with ClientSession(read, write) as session:
    #         # Initialize the connection
    #         await session.initialize()
    #
    #         # Get tools
    #         tools = await load_mcp_tools(session)
    #         for tool in tools:
    #             print("tools:",tool.name)
    #
    #         # Create and run the agent
    #         agent = create_react_agent(model, tools)
    #         agent_response = await agent.ainvoke({"messages": "what's (3 + 5) x 12?"})
    #         print("**********")
    #         print(agent_response)

# Run the main function
asyncio.run(main())