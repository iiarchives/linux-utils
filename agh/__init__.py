__version__ = "0.4.1"

# Handle request errors
class RequestError(Exception):
    pass

# Create a global configuration
from agh.config import Configuration
config = Configuration()
