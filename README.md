# TIDAL MCP

A Model Context Protocol (MCP) server implementation that provides a bridge between AI assistants and your TIDAL music streaming account. This integration allows AI assistants to interact with your TIDAL account through a standardized interface, enabling functionalities such as browsing your favorite tracks, creating playlists, analyzing your music preferences, and providing personalized music recommendations.

## Features

- 🎵 **Music Recommendations**: Get personalized track recommendations based on your listening history
- 📊 **Music Analysis**: Analyze your music taste and preferences
- 📋 **Playlist Management**: Create, view, and manage your TIDAL playlists

## Quick Start

### Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- TIDAL subscription

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/tidal-mcp-integration.git
   cd tidal-mcp-integration
   ```

2. Create a virtual environment and install dependencies using uv:
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install the package with all dependencies from the pyproject.toml file:
   ```bash
   uv pip install --editable .
   ```

   This will install all dependencies defined in the pyproject.toml file and set up the project in development mode.

## MCP Client Configuration

### Claude Desktop Configuration

To add this MCP server to Claude Desktop, you need to update the MCP configuration file. Here's an example configuration:

```json
{
  "mcpServers": {
    "TIDAL Integration": {
      "command": "/path/to/your/uv",
      "args": [
        "run",
        "--with",
        "requests",
        "--with",
        "mcp[cli]",
        "--with",
        "flask",
        "--with",
        "tidalapi",
        "mcp",
        "run",
        "/path/to/your/project/tidal-mcp/mcp_server/server.py"
      ]
    }
  }
}
```

Replace `/path/to/your/uv` with the actual path to your uv executable and `/path/to/your/project` with the actual path to your project directory.

Example scrrenshot of the MCP configuration in Claude Desktop:
![Claude MCP Configuration](./assets/claude_desktop_config.png)

### Steps to Install MCP Configuration

1. Open Claude Desktop
2. Go to Settings > Developer
3. Click on "Edit Config"
4. Paste the modified JSON configuration
5. Save the configuration
6. Restart Claude Desktop

## Usage Example Prompts

Once configured, you can interact with your TIDAL account through Claude by asking questions like:

- "Login to my TIDAL account"
- "What are my favorite tracks on TIDAL?"
- "Analyze my music preferences"
- "Recommend new music based on my favorites"
- "Create a playlist of relaxing jazz tracks"
- "Show me my existing playlists"

## Available Tools

The TIDAL MCP integration provides the following tools:

- `tidal_login`: Authenticate with TIDAL through browser login flow
- `get_favorite_tracks`: Retrieve your favorite tracks from TIDAL
- `recommend_tracks`: Get personalized music recommendations
- `create_tidal_playlist`: Create a new playlist in your TIDAL account
- `get_user_playlists`: List all your playlists on TIDAL
- `get_playlist_tracks`: Retrieve all tracks from a specific playlist
- `delete_tidal_playlist`: Delete a playlist from your TIDAL account

## License

[MIT License](LICENSE)

## Acknowledgements

- [Model Context Protocol (MCP)](https://github.com/modelcontextprotocol/python-sdk)
- [TIDAL Python API](https://github.com/tamland/python-tidal)