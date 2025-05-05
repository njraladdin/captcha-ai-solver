#!/usr/bin/env python
"""
Test script for the updated captcha solver module with the fixed browser handling.
This script will attempt to solve a real captcha from the Google demo site.

Usage:
    python test_captcha_fixed.py
"""

import os
import time
import sys
from dotenv import load_dotenv

# Try to load API key from .env file if it exists
load_dotenv()

# Import the CaptchaSolver class
from captcha_solver import CaptchaSolver

# Set your Wit.ai API key here or in environment variable
WIT_API_KEY = os.environ.get("WIT_API_KEY", "YOUR_WIT_API_KEY")

def main():
    print("\n=== FIXED CAPTCHA Solver Demo ===")
    print("This demo will attempt to solve the Google reCAPTCHA demo with the fixed implementation")
    
    # Initialize the solver
    print("\nInitializing CaptchaSolver...")
    solver = CaptchaSolver(wit_api_key=WIT_API_KEY)
    
    # Google demo captcha parameters
    captcha_params = {
        "website_key": "6Le-wvkSAAAAAPBMRTvw0Q4Muexq9bi0DJwx_mJ-",
        "website_url": "https://www.google.com/recaptcha/api2/demo",
        "is_invisible": False,
        "is_enterprise": False,
        "data_s_value": None
    }
    
    # Start solving the captcha
    print("\n🔍 Attempting to solve Google demo captcha...")
    print("(This may take a minute or two)")
    
    start_time = time.time()
    token, success = solver.solve(captcha_params)
    end_time = time.time()
    
    # Print results
    print("\n=== Results ===")
    if success and token:
        print("✅ CAPTCHA solved successfully!")
        print(f"Token (first 30 chars): {token[:30]}...")
        print(f"Token length: {len(token)} characters")
    else:
        print("❌ Failed to solve CAPTCHA")
        
    print(f"Time taken: {end_time - start_time:.2f} seconds")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 