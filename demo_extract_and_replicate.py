#!/usr/bin/env python
"""
Demo script combining CaptchaExtractor and ReplicatedCaptcha.

This script demonstrates a full workflow:
1. Extract reCAPTCHA parameters from a target website
2. Replicate the reCAPTCHA using the extracted parameters
"""

import sys
import time
from captcha_solver import CaptchaExtractor, ReplicatedCaptcha

def main():
    """Run the combined demonstration workflow."""
    # Process command-line arguments
    if len(sys.argv) < 2:
        # Use default if no URL provided
        url = "https://www.google.com/recaptcha/api2/demo"  # Using 2captcha's demo page which should work
        wait_time = 10
        
        print("\n=== reCAPTCHA Extraction and Replication Demo ===")
        print("No URL provided. Using 2captcha's demo reCAPTCHA page.")
        print("For custom page, use: python demo_extract_and_replicate.py <url> [wait_time]")
        print(f"Example: python demo_extract_and_replicate.py {url} 15")
    else:
        # Get URL and optional wait time from command line
        url = sys.argv[1]
        wait_time = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    # Create instances of both classes
    extractor = CaptchaExtractor(download_dir="tmp")
    replicator = ReplicatedCaptcha(download_dir="tmp")
    
    try:
        # Step 1: Extract reCAPTCHA parameters
        print(f"\n=== Step 1: Extracting reCAPTCHA Parameters from {url} ===")
        print(f"Wait time: {wait_time} seconds")
        
        # Extract parameters
        params = extractor.extract_recaptcha_params(url, wait_time=wait_time)
        
        # Display extracted parameters
        print("\n=== Extracted Parameters ===")
        print(f"Website URL: {params['website_url']}")
        print(f"Site Key: {params['website_key']}")
        print(f"Is Invisible: {params['is_invisible']}")
        print(f"Data-S Value: {params['data_s_value']}")
        print(f"Is Enterprise: {params['is_enterprise']}")
        
        # Check if we have the necessary parameters to proceed
        if not params["website_key"]:
            print("\nERROR: Could not extract reCAPTCHA site key.")
            print("The page may not have a reCAPTCHA, or it might be dynamically loaded.")
            return 1
        
        # Step 2: Replicate the reCAPTCHA
        print("\n=== Step 2: Replicating reCAPTCHA ===")
        print("Opening replicated reCAPTCHA in browser...")
        
        # Replicate the captcha using extracted parameters
        html_path, browser = replicator.run_replicated_captcha(
            website_key=params["website_key"],
            website_url=params["website_url"],
            is_invisible=params["is_invisible"],
            data_s_value=params["data_s_value"],
            observation_time=0  # Keep browser open until manually closed
        )
        
        # This point is reached only after browser is closed manually
        print("\n=== Demo completed successfully ===")
        print("Browser was closed by user.")
        
        return 0
    
    except KeyboardInterrupt:
        print("\nDemo interrupted by user. Exiting...")
        # Ensure server is stopped if interrupted
        replicator.stop_http_server()
        return 1
    except Exception as e:
        print(f"\nError during demo: {e}")
        # Ensure server is stopped on error
        replicator.stop_http_server()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 