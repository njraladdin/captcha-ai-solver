#!/usr/bin/env python
"""
Simple test script for the captcha solver module.
This script will attempt to solve a real captcha from the Google demo site.

Usage:
    python test_captcha_demo.py

You can set your Wit.ai API key in three ways:
1. Edit this file and replace YOUR_WIT_API_KEY below
2. Set the WIT_API_KEY environment variable
3. Create a .env file with WIT_API_KEY=your_key
"""

import os
import time
import sys
from dotenv import load_dotenv

# Try to load API key from .env file if it exists
load_dotenv()

# Import the CaptchaSolver class
from captcha_solver import CaptchaSolver

# Set your Wit.ai API key here
# Can be overridden by environment variable
WIT_API_KEY = os.environ.get("WIT_API_KEY", "YOUR_WIT_API_KEY")

def main():
    print("\n=== CAPTCHA Solver Demo ===")
    print("This demo will attempt to solve the Google reCAPTCHA demo")
    
    # Check if API key is set
    if WIT_API_KEY == "YOUR_WIT_API_KEY":
        print("\n⚠️  WARNING: No Wit.ai API key provided!")
        print("Please set your Wit.ai API key by:")
        print("  1. Editing this file")
        print("  2. Setting the WIT_API_KEY environment variable")
        print("  3. Creating a .env file with WIT_API_KEY=your_key")
        
        use_default = input("\nDo you want to continue with the default key? (y/n): ").lower()
        if use_default != 'y':
            print("Exiting demo...")
            return False
    
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