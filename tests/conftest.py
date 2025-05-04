import pytest
import os
from dotenv import load_dotenv

# Load environment variables before any tests run
def pytest_configure(config):
    """Load environment variables before pytest starts running tests."""
    load_dotenv()
    
    # Check for required environment variables
    required_vars = ['WIT_AI_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"WARNING: The following required environment variables are missing: {', '.join(missing_vars)}")
        print("Some tests may fail if these variables are not set.")
        
# Add command line options
def pytest_addoption(parser):
    """Add command-line options to pytest."""
    parser.addoption(
        "--run-slow", action="store_true", default=False, help="run slow tests"
    )

# Skip slow tests unless --run-slow is specified
def pytest_collection_modifyitems(config, items):
    """Skip slow tests unless --run-slow is specified."""
    if not config.getoption("--run-slow"):
        skip_slow = pytest.mark.skip(reason="need --run-slow option to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow) 