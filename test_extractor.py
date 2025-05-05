#!/usr/bin/env python
"""
Test script for the CaptchaExtractor.

This script tests the CaptchaExtractor on two different websites:
1. Google's reCAPTCHA demo page
2. 2captcha's reCAPTCHA demo page
"""

import sys
from captcha_solver import CaptchaExtractor

def test_site(url, wait_time=10):
    """Test CaptchaExtractor on a specific URL."""
    print(f"\n\n=== Testing CaptchaExtractor on: {url} ===")
    extractor = CaptchaExtractor(download_dir="tmp")
    params = extractor.extract_and_print(url, wait_time=wait_time)
    
    # Check if extraction was successful
    if params["website_key"]:
        print(f"\n✅ Success! Extracted site key: {params['website_key']}")
        return True
    else:
        print("\n❌ Failed! Could not extract site key.")
        return False

def main():
    # Test sites
    test_sites = [
        "https://www.google.com/recaptcha/api2/demo",
        "https://2captcha.com/demo/recaptcha-v2"
    ]
    
    # Keep track of success/failure
    success_count = 0
    
    # Run tests on each site
    for site in test_sites:
        if test_site(site):
            success_count += 1
    
    # Print summary
    print(f"\n=== Test Summary ===")
    print(f"Tested {len(test_sites)} sites")
    print(f"Successfully extracted {success_count}/{len(test_sites)} site keys")
    
    return 0 if success_count == len(test_sites) else 1

if __name__ == "__main__":
    sys.exit(main()) 