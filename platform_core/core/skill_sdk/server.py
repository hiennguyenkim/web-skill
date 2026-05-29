from mcp.server.fastmcp import FastMCP

_registered_tools = []

def tool(func):
    """Decorator to register a tool function globally for the SkillServer to pick up."""
    _registered_tools.append(func)
    return func

class SkillServer:
    def __init__(self, name: str, **kwargs):
        self.name = name
        self.mcp = FastMCP(name, **kwargs)

    def run(self, transport: str = "stdio"):
        """Register all globally decorated tools and run the FastMCP server."""
        for func in _registered_tools:
            # Register using FastMCP tool decorator
            self.mcp.tool()(func)
        # Clear the list after registration
        _registered_tools.clear()
        self.mcp.run(transport)
