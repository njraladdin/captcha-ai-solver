#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Example script for using the captcha-ai-solver library with the updated result object return format.
"""

import os
import argparse
import json
from dotenv import load_dotenv
from captcha_solver import solve_captcha

# Load environment variables
load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="Captcha AI Solver Example")
    parser.add_argument("--website", default="https://2captcha.com/demo/recaptcha-v2", 
                        help="URL of the website with captcha")
    parser.add_argument("--key", default="6LfD3PIbAAAAAJs_eEHvoOl75_83eXSqpPSRFJ_u", 
                        help="reCAPTCHA site key")
    args = parser.parse_args()

    # Get API key from environment
    wit_api_key = os.getenv("WIT_API_KEY")
    if not wit_api_key:
        print("WARNING: No Wit.ai API key provided. Audio challenges will fail.")
    
    # Define captcha parameters
    captcha_params = {
        "website_url": args.website,
        "website_key": args.key
    }

    # Configure solver
    solver_config = {
        "wit_api_key": wit_api_key
    }
    
    print("\n=== Starting CAPTCHA Solving Process ===")
    print(f"Website URL: {captcha_params['website_url']}")
    print(f"reCAPTCHA key: {captcha_params['website_key']}")
    
    # Solve the captcha
    result = solve_captcha(
        captcha_type="recaptcha_v2",
        captcha_params=captcha_params,
        solver_config=solver_config
    )
    

    # Output result in human-readable format
    print("\n=== CAPTCHA Solving Result ===")
    
    print(f"Success: {result['success']}")
        
    if result['success']:
         print("\n✅ CAPTCHA Solved Successfully!")
         print(f"Token (first 30 chars): {result['token'][:30]}...")
            
    else:
        print("\n❌ CAPTCHA Solving Failed")
        print(f"Error: {result['error']}")
    
if __name__ == "__main__":
    main() 