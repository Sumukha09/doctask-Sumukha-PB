import logging
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP Server
mcp = FastMCP("FlowDocs MCP Server")

# Import tools so they are registered with the decorator
import app.mcp.tools

def main():
    """Run the MCP server via stdio transport."""
    logger.info("Starting FlowDocs MCP Server...")
    mcp.run()

if __name__ == "__main__":
    main()
