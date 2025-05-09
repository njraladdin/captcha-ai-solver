#!/usr/bin/env python
"""
Basic reCAPTCHA solving example with hardcoded parameters.

This example demonstrates the simplest possible usage of the CaptchaSolver
with manually provided captcha parameters.
"""

import os
import time
from dotenv import load_dotenv
from captcha_solver import CaptchaSolver

# Load environment variables (for Wit.ai API key)
load_dotenv()

def main():
    """Run a simple example of solving a reCAPTCHA with hardcoded parameters."""
    # Get Wit.ai API key from environment (required for audio recognition)
    wit_api_key = os.environ.get("WIT_API_KEY")
    if not wit_api_key:
        print("ERROR: WIT_API_KEY environment variable is not set.")
        print("Please set the WIT_API_KEY environment variable with your Wit.ai API key.")
        return 1
    
    print("\n=== Basic reCAPTCHA Solving Example ===")
    print("Using hardcoded parameters for Google's reCAPTCHA demo")
    
    # These are the parameters for Google's reCAPTCHA demo page
    # In a real-world scenario, you would obtain these parameters from your target website
    captcha_params = {
        "website_key": "6Le-wvkSAAAAAPBMRTvw0Q4Muexq9bi0DJwx_mJ-",
        "website_url": "https://www.google.com/recaptcha/api2/demo",
        "is_invisible": False,
        "is_enterprise": False,
        "data_s_value": None  # This parameter is usually None for standard reCAPTCHA
    }
    
    # Print the parameters
    print("\nUsing the following reCAPTCHA parameters:")
    print(f"Site key: {captcha_params['website_key']}")
    print(f"Website URL: {captcha_params['website_url']}")
    print(f"Is invisible: {captcha_params['is_invisible']}")
    print(f"Is enterprise: {captcha_params['is_enterprise']}")
    
    # Create a CaptchaSolver instance
    print("\nInitializing CaptchaSolver...")
    solver = CaptchaSolver(wit_api_key=wit_api_key, download_dir="tmp")
    
    # Solve the CAPTCHA
    print("\nSolving reCAPTCHA...")
    start_time = time.time()
    
    token, success = solver.solve(captcha_params)
    
    # Calculate solve time
    solve_time = time.time() - start_time
    
    # Report results
    if success and token:
        print(f"\n✅ reCAPTCHA solved successfully in {solve_time:.2f} seconds!")
        print(f"Token (first 30 chars): {token[:30]}...")
        
        # In a real application, you would use this token to submit a form or make an API call
        print("\nIn a real application, you would now use this token to:")
        print("1. Apply it to the reCAPTCHA on your page using TokenSubmitter")
        print("2. Or include it in an API request as the 'g-recaptcha-response' parameter")
        
        return 0
    else:
        print(f"\n❌ Failed to solve reCAPTCHA after {solve_time:.2f} seconds")
        return 1

if __name__ == "__main__":
    exit(main()) 