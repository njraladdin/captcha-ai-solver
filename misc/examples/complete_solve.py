#!/usr/bin/env python
"""
Complete reCAPTCHA solving example using all components.

This example demonstrates the full workflow using all components:
1. CaptchaExtractor - To extract parameters from the page
2. CaptchaSolver - To solve the reCAPTCHA
3. TokenSubmitter - To apply the token back to the page
"""

import os
import time
from dotenv import load_dotenv
from seleniumbase import SB
from captcha_solver import CaptchaExtractor, CaptchaSolver, TokenSubmitter

# Load environment variables (for Wit.ai API key)
load_dotenv()

def main():
    """Run a complete example of solving a reCAPTCHA using all components."""
    # Target URL - Google's reCAPTCHA demo
    target_url = "https://www.google.com/recaptcha/api2/demo"
    
    # Get Wit.ai API key from environment (required for audio recognition)
    wit_api_key = os.environ.get("WIT_API_KEY")
    if not wit_api_key:
        print("ERROR: WIT_API_KEY environment variable is not set.")
        print("Please set the WIT_API_KEY environment variable with your Wit.ai API key.")
        return 1
    
    print("\n=== Complete reCAPTCHA Solving Example ===")
    print("Using all components to solve Google's reCAPTCHA demo")
    print(f"Target URL: {target_url}")
    
    # Initialize components
    print("\nInitializing components...")
    extractor = CaptchaExtractor(download_dir="tmp")
    solver = CaptchaSolver(wit_api_key=wit_api_key, download_dir="tmp")
    submitter = TokenSubmitter(download_dir="tmp")
    
    # Start tracking solve time
    start_time = time.time()
    
    # Initialize browser
    browser = None
    try:
        print("\nInitializing browser...")
        browser = SB(uc=True, test=True, locale="en", ad_block=True, pls="none", headless=False)
        
        with browser as sb:
            # Step 1: Navigate to the page and extract parameters
            print(f"\n--- Step 1: Navigating to {target_url} ---")
            sb.open(target_url)
            print("Waiting for page to load...")
            sb.sleep(2)
            
            # Extract reCAPTCHA parameters
            print("\n--- Step 2: Extracting reCAPTCHA Parameters ---")
            params = extractor.extract_captcha_params(sb)
            
            if not params.get("website_key"):
                print("ERROR: Could not extract reCAPTCHA site key.")
                return 1
                
            # Print the extracted parameters
            print("\nExtracted the following reCAPTCHA parameters:")
            print(f"Site key: {params['website_key']}")
            print(f"Website URL: {params['website_url']}")
            print(f"Is invisible: {params['is_invisible']}")
            print(f"Is enterprise: {params['is_enterprise']}")
            
            # Step 2: Solve the CAPTCHA
            print("\n--- Step 3: Solving reCAPTCHA ---")
            token, success = solver.solve(params)
            
            if not success or not token:
                print("ERROR: Failed to solve the reCAPTCHA.")
                return 1
                
            solve_time = time.time() - start_time
            print(f"\n✅ reCAPTCHA solved successfully in {solve_time:.2f} seconds!")
            print(f"Token (first 30 chars): {token[:30]}...")
            
            # Step 3: Apply the token to the page
            print("\n--- Step 4: Applying Token to Page ---")
            token_applied = submitter.apply_token(sb, token, params, submit_form=True)
            
            if token_applied:
                print("✅ Token applied successfully to the page!")
                
                # Verify token application
                verification = submitter.verify_token_application(sb)
                if verification:
                    print("✅ Token verification successful")
                else:
                    print("❓ Token verification uncertain (but token was applied)")
                
                # Wait a moment to see the results
                print("\nWaiting to observe the result...")
                sb.sleep(5)
                
                # Take a screenshot of the result
                screenshot_path = "tmp/recaptcha_demo_result.png"
                sb.save_screenshot(screenshot_path)
                print(f"Screenshot saved to: {screenshot_path}")
            else:
                print("❌ Failed to apply token to the page")
                return 1
            
            # Wait before closing the browser
            print("\nKeeping browser open for 10 seconds for observation...")
            sb.sleep(10)
            
        # Calculate total time
        total_time = time.time() - start_time
        print(f"\nComplete workflow finished in {total_time:.2f} seconds")
        return 0
            
    except Exception as e:
        print(f"\nError during example: {e}")
        return 1
    finally:
        # Make sure browser is closed
        if browser and hasattr(browser, 'driver') and browser.driver:
            try:
                browser.quit()
            except:
                pass

if __name__ == "__main__":
    exit(main()) 