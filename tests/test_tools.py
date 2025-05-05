from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool, ToolException
from mcp.types import (
    CallToolResult,
    EmbeddedResource,
    ImageContent,
    TextContent,
    TextResourceContents,
)
from mcp.types import Tool as MCPTool

from langchain_mcp_adapters.tools import (
    _convert_call_tool_result,
    convert_mcp_tool_to_langchain_tool,
    load_mcp_tools,
)


def test_convert_empty_text_content():
    # Test with a single text content
    result = CallToolResult(
        content=[],
        isError=False,
    )

    text_content, non_text_content = _convert_call_tool_result(result)

    assert text_content == ""
    assert non_text_content is None


def test_convert_single_text_content():
    # Test with a single text content
    result = CallToolResult(
        content=[TextContent(type="text", text="test result")],
        isError=False,
    )

    text_content, non_text_content = _convert_call_tool_result(result)

    assert text_content == "test result"
    assert non_text_content is None


def test_convert_multiple_text_contents():
    # Test with multiple text contents
    result = CallToolResult(
        content=[
            TextContent(type="text", text="result 1"),
            TextContent(type="text", text="result 2"),
        ],
        isError=False,
    )

    text_content, non_text_content = _convert_call_tool_result(result)

    assert text_content == ["result 1", "result 2"]
    assert non_text_content is None


def test_convert_with_non_text_content():
    # Test with non-text content
    image_content = ImageContent(type="image", mimeType="image/png", data="base64data")
    resource_content = EmbeddedResource(
        type="resource",
        resource=TextResourceContents(uri="resource://test", mimeType="text/plain", text="hi"),
    )

    result = CallToolResult(
        content=[
            TextContent(type="text", text="text result"),
            image_content,
            resource_content,
        ],
        isError=False,
    )

    text_content, non_text_content = _convert_call_tool_result(result)

    assert text_content == "text result"
    assert non_text_content == [image_content, resource_content]


def test_convert_with_error():
    # Test with error
    result = CallToolResult(
        content=[TextContent(type="text", text="error message")],
        isError=True,
    )

    with pytest.raises(ToolException) as exc_info:
        _convert_call_tool_result(result)

    assert str(exc_info.value) == "error message"


@pytest.mark.asyncio
async def test_convert_mcp_tool_to_langchain_tool():
    tool_input_schema = {
        "properties": {
            "param1": {"title": "Param1", "type": "string"},
            "param2": {"title": "Param2", "type": "integer"},
        },
        "required": ["param1", "param2"],
        "title": "ToolSchema",
        "type": "object",
    }
    # Mock session and MCP tool
    session = AsyncMock()
    session.call_tool.return_value = CallToolResult(
        content=[TextContent(type="text", text="tool result")],
        isError=False,
    )

    mcp_tool = MCPTool(
        name="test_tool",
        description="Test tool description",
        inputSchema=tool_input_schema,
    )

    # Convert MCP tool to LangChain tool
    lc_tool = convert_mcp_tool_to_langchain_tool(session, mcp_tool)

    # Verify the converted tool
    assert lc_tool.name == "test_tool"
    assert lc_tool.description == "Test tool description"
    assert lc_tool.args_schema == tool_input_schema

    # Test calling the tool
    result = await lc_tool.ainvoke(
        {"args": {"param1": "test", "param2": 42}, "id": "1", "type": "tool_call"}
    )

    # Verify session.call_tool was called with correct arguments
    session.call_tool.assert_called_once_with("test_tool", {"param1": "test", "param2": 42})

    # Verify result
    assert result == ToolMessage(content="tool result", name="test_tool", tool_call_id="1")


@pytest.mark.asyncio
async def test_load_mcp_tools():
    tool_input_schema = {
        "properties": {
            "param1": {"title": "Param1", "type": "string"},
            "param2": {"title": "Param2", "type": "integer"},
        },
        "required": ["param1", "param2"],
        "title": "ToolSchema",
        "type": "object",
    }
    # Mock session and list_tools response
    session = AsyncMock()
    mcp_tools = [
        MCPTool(
            name="tool1",
            description="Tool 1 description",
            inputSchema=tool_input_schema,
        ),
        MCPTool(
            name="tool2",
            description="Tool 2 description",
            inputSchema=tool_input_schema,
        ),
    ]
    session.list_tools.return_value = MagicMock(tools=mcp_tools)

    # Mock call_tool to return different results for different tools
    async def mock_call_tool(tool_name, arguments):
        if tool_name == "tool1":
            return CallToolResult(
                content=[TextContent(type="text", text=f"tool1 result with {arguments}")],
                isError=False,
            )
        else:
            return CallToolResult(
                content=[TextContent(type="text", text=f"tool2 result with {arguments}")],
                isError=False,
            )

    session.call_tool.side_effect = mock_call_tool

    # Load MCP tools
    tools = await load_mcp_tools(session)

    # Verify the tools
    assert len(tools) == 2
    assert all(isinstance(tool, BaseTool) for tool in tools)
    assert tools[0].name == "tool1"
    assert tools[1].name == "tool2"

    # Test calling the first tool
    result1 = await tools[0].ainvoke(
        {"args": {"param1": "test1", "param2": 1}, "id": "1", "type": "tool_call"}
    )
    assert result1 == ToolMessage(
        content="tool1 result with {'param1': 'test1', 'param2': 1}", name="tool1", tool_call_id="1"
    )

    # Test calling the second tool
    result2 = await tools[1].ainvoke(
        {"args": {"param1": "test2", "param2": 2}, "id": "2", "type": "tool_call"}
    )
    assert result2 == ToolMessage(
        content="tool2 result with {'param1': 'test2', 'param2': 2}", name="tool2", tool_call_id="2"
    )
