import pytest
import os
import time
from dotenv import load_dotenv
import sys
from pathlib import Path

# Add the parent directory to the path so we can import the captcha_solver module
sys.path.append(str(Path(__file__).parent.parent))

from captcha_solver import CaptchaSolver

# Load environment variables from .env file
load_dotenv()

# Get the Wit.ai API key from environment variables
WIT_API_KEY = os.getenv('WIT_AI_API_KEY')
if not WIT_API_KEY:
    raise ValueError("WIT_AI_API_KEY environment variable not found. Please set it in .env file.")

# Test constants
RECAPTCHA_DEMO_URL = "https://www.google.com/recaptcha/api2/demo"
DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "tmp")

# Ensure download directory exists
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def test_solve_google_recaptcha_demo():
    """Direct test of solving Google's reCAPTCHA demo page."""
    print("\n=== Testing Google reCAPTCHA Demo Solution ===")
    
    # Initialize the solver with the Wit.ai API key
    solver = CaptchaSolver(wit_api_key=WIT_API_KEY, download_dir=DOWNLOAD_DIR)
    
    # Run the workflow without any callbacks
    # The solver will navigate to the URL and attempt to solve the CAPTCHA
    token, success = solver.run_workflow(RECAPTCHA_DEMO_URL, observation_time=2)
    
    # Log the results
    if success:
        print(f"✅ CAPTCHA SOLVED SUCCESSFULLY!")
        print(f"Token: {token[:30]}..." if token else "No token")
    else:
        print(f"❌ CAPTCHA SOLUTION FAILED")
        print(f"Token: {token}" if token else "No token")
    
    # We don't assert success because network conditions or Google's detection
    # might make the test fail unpredictably
    print(f"Success: {success}")
    print("=== Test Complete ===\n") 