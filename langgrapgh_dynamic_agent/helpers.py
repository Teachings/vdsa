from termcolor import colored
from datetime import datetime
import yaml

def load_config():
    """Load configuration from config.yml."""
    try:
        with open("config.yml", "r") as config_file:
            return yaml.safe_load(config_file)
    except Exception as e:
        log(f"Error loading config.yml: {str(e)}", level="ERROR")
        return {}


def log(message, level="INFO", color=None):
    """Log messages with timestamp and optional color."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    levels = {"INFO": "cyan", "WARNING": "yellow", "ERROR": "red", "SUCCESS": "green"}
    
    # Convert level to uppercase to ensure case-insensitivity
    level_upper = level.upper()
    
    # Determine the color to use: if a color is provided, use it; otherwise, use the default for the level
    if color:
        level_color = color
    else:
        level_color = levels.get(level_upper, "cyan")  # Default to cyan if level is unknown
    
    print(colored(f"[{timestamp}] [{level_upper}] {message}", level_color))