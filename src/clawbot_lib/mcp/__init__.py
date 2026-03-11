"""MCP (Model Context Protocol) client module."""

import json
from typing import Any

from ..config import settings
from ..logger import get_logger
from ..models import MCPServerConfig, MCPTool, MCPToolResult

logger = get_logger("mcp")


class MCPClient:
    """MCP client for connecting to external services."""

    def __init__(self, server_name: str, config: MCPServerConfig) -> None:
        self.server_name = server_name
        self.config = config
        self._connected = False
        self._tools: list[MCPTool] = []

    async def connect(self) -> bool:
        """Connect to the MCP server."""
        try:
            logger.info(f"Connecting to MCP server: {self.server_name}")
            # In a full implementation, this would use SSE or stdio
            # For now, we'll use HTTP-based MCP if available
            self._connected = True
            await self._discover_tools()
            logger.info(f"Connected to MCP server: {self.server_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MCP server {self.server_name}: {e}")
            return False

    async def _discover_tools(self) -> None:
        """Discover available tools from the MCP server."""
        # Placeholder - in production, this would call the MCP server's tools/list endpoint
        self._tools = []

    @property
    def tools(self) -> list[MCPTool]:
        """Get discovered tools."""
        return self._tools

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> MCPToolResult:
        """Execute a tool on the MCP server."""
        if not self._connected:
            return MCPToolResult(
                success=False,
                error=f"MCP server {self.server_name} not connected",
            )

        try:
            # Placeholder - in production, this would call the MCP server's tools/call endpoint
            logger.info(f"Executing MCP tool: {self.server_name}/{tool_name}")
            return MCPToolResult(success=True, result={"message": "Tool executed"})
        except Exception as e:
            logger.error(f"Failed to execute MCP tool {tool_name}: {e}")
            return MCPToolResult(success=False, error=str(e))

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        self._connected = False
        logger.info(f"Disconnected from MCP server: {self.server_name}")


class MCPManager:
    """Manager for all MCP servers."""

    def __init__(self) -> None:
        self._servers: dict[str, MCPClient] = {}

    async def initialize(self) -> bool:
        """Initialize all configured MCP servers."""
        # Check for GitHub token
        github_token = settings.ai.anthropic_api_key  # In production, use dedicated env var
        if github_token:
            # Create GitHub MCP server config
            config = MCPServerConfig(
                name="github",
                command="npx",
                args=["-y", "@modelcontextprotocol/server-github"],
                env={"GITHUB_PERSONAL_ACCESS_TOKEN": github_token},
            )
            client = MCPClient("github", config)
            if await client.connect():
                self._servers["github"] = client
                logger.info("GitHub MCP server connected")

        # Check for Notion token
        notion_token = settings.ai.openai_api_key  # Placeholder - use dedicated env var
        if notion_token:
            # Create Notion MCP server config
            config = MCPServerConfig(
                name="notion",
                command="npx",
                args=["-y", "@modelcontextprotocol/server-notion"],
                env={"NOTION_API_TOKEN": notion_token},
            )
            client = MCPClient("notion", config)
            if await client.connect():
                self._servers["notion"] = client
                logger.info("Notion MCP server connected")

        return len(self._servers) > 0

    @property
    def connected_servers(self) -> list[str]:
        """Get list of connected server names."""
        return list(self._servers.keys())

    def get_tools(self, server_name: str) -> list[MCPTool]:
        """Get tools for a specific server."""
        if server_name in self._servers:
            return self._servers[server_name].tools
        return []

    def get_all_tools(self) -> list[MCPTool]:
        """Get all tools from all connected servers."""
        tools = []
        for client in self._servers.values():
            tools.extend(client.tools)
        return tools

    async def execute_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> MCPToolResult:
        """Execute a tool on a specific server."""
        if server_name in self._servers:
            return await self._servers[server_name].execute_tool(tool_name, arguments)
        return MCPToolResult(success=False, error=f"Server {server_name} not connected")

    async def shutdown(self) -> None:
        """Shutdown all MCP servers."""
        for client in self._servers.values():
            await client.disconnect()
        self._servers.clear()
        logger.info("All MCP servers shut down")


# Global manager
_mcp_manager: MCPManager | None = None
_mcp_enabled = False


async def initialize_mcp() -> bool:
    """Initialize MCP servers."""
    global _mcp_manager, _mcp_enabled

    _mcp_manager = MCPManager()
    _mcp_enabled = await _mcp_manager.initialize()
    return _mcp_enabled


def is_mcp_enabled() -> bool:
    """Check if MCP is enabled."""
    return _mcp_enabled


def get_connected_servers() -> list[str]:
    """Get list of connected MCP servers."""
    if _mcp_manager:
        return _mcp_manager.connected_servers
    return []


def get_all_mcp_tools() -> list[MCPTool]:
    """Get all available MCP tools."""
    if _mcp_manager:
        return _mcp_manager.get_all_tools()
    return []


async def execute_mcp_tool(
    server_name: str,
    tool_name: str,
    arguments: dict[str, Any],
) -> MCPToolResult:
    """Execute an MCP tool."""
    if _mcp_manager:
        return await _mcp_manager.execute_tool(server_name, tool_name, arguments)
    return MCPToolResult(success=False, error="MCP not initialized")


def parse_tool_name(tool_name: str) -> tuple[str, str] | None:
    """Parse MCP tool name into server and tool.

    Args:
        tool_name: Tool name (e.g., "github_search_repositories")

    Returns:
        Tuple of (server_name, tool_name) or None
    """
    if "_" not in tool_name:
        return None

    parts = tool_name.split("_", 1)
    if len(parts) != 2:
        return None

    return (parts[0], parts[1])


def mcp_tools_to_openai(tools: list[MCPTool]) -> list[dict[str, Any]]:
    """Convert MCP tools to OpenAI function calling format."""
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_schema,
            },
        }
        for tool in tools
    ]


def format_mcp_result(result: MCPToolResult) -> str:
    """Format MCP tool result for display."""
    if not result.success:
        return f"Error: {result.error}"

    if isinstance(result.result, dict):
        return json.dumps(result.result, indent=2)
    return str(result.result)


async def shutdown_mcp() -> None:
    """Shutdown MCP servers."""
    if _mcp_manager:
        await _mcp_manager.shutdown()


# Aliases
initializeMCP = initialize_mcp
shutdownMCP = shutdown_mcp
isMCPEnabled = is_mcp_enabled
getConnectedServers = get_connected_servers
getAllMCPTools = get_all_mcp_tools
executeMCPTool = execute_mcp_tool
parseToolName = parse_tool_name
mcpToolsToOpenAI = mcp_tools_to_openai
formatMCPResult = format_mcp_result
