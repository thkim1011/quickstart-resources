import json
from pathlib import Path
from mcp import StdioServerParameters  # Import from the mcp package

def parse_config(config_path):
    """
    Parses the config.json file and returns the server parameters as a StdioServerParameters object.
    
    :param config_path: Path to the config.json file.
    :return: StdioServerParameters object.
    """
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    mcp_servers = config["mcpServers"]
    if len(mcp_servers) != 1:
        raise ValueError("The client currently supports only one server at this time.")
    
    _, server_config = next(iter(mcp_servers.items()))
    command = server_config["command"]
    args = server_config["args"]
    
    server_params = StdioServerParameters(
        command=command,
        args=args,
        env=None
    )
    return server_params
