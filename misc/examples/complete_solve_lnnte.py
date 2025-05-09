#!/usr/bin/env python
"""
Complete reCAPTCHA solving example for LNNTE website.

This example demonstrates the full workflow using all components:
1. CaptchaExtractor - To extract parameters from the page
2. CaptchaSolver - To solve the reCAPTCHA
3. TokenSubmitter - To apply the token back to the page

This example checks a single phone number on the LNNTE website.
"""

import os
import time
from dotenv import load_dotenv
from seleniumbase import SB
from captcha_solver import CaptchaExtractor, CaptchaSolver, TokenSubmitter

# Load environment variables (for Wit.ai API key)
load_dotenv()

def main():
    """Run a complete example of solving a reCAPTCHA on the LNNTE website."""
    # Target URL - LNNTE website
    target_url = "https://lnnte-dncl.gc.ca/en/Consumer/Check-your-registration/#!/"
    
    # Phone number to check
    phone_number = "418-313-3337"  # Example phone number
    
    # Selectors for the LNNTE website
    phone_input_selector = "#phone"
    submit_button_selector = 'button[type="submit"]'
    check_registration_selector = "body > div:nth-child(5) > div > div > div.container.ng-scope > div > div:nth-child(2) > div:nth-child(1) > div:nth-child(3) > div:nth-child(2) > form > div > div.submit-container > button:nth-child(2)"
    
    # Get Wit.ai API key from environment (required for audio recognition)
    wit_api_key = os.environ.get("WIT_AI_API_KEY")  # Note: Changed from WIT_API_KEY to match validate_lnnte.py
    if not wit_api_key:
        print("ERROR: WIT_AI_API_KEY environment variable is not set.")
        print("Please set the WIT_AI_API_KEY environment variable with your Wit.ai API key.")
        return 1
    
    # Create directories for results and temporary files
    os.makedirs("tmp", exist_ok=True)
    os.makedirs("results", exist_ok=True)
    
    print("\n=== Complete reCAPTCHA Solving Example for LNNTE Website ===")
    print(f"Checking phone number: {phone_number}")
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
            # Step 1: Navigate to the page
            print(f"\n--- Step 1: Navigating to {target_url} ---")
            sb.open(target_url)
            print("Waiting for page to load...")
            sb.sleep(3)
            
            # Step 2: Fill in the phone number
            print(f"\n--- Step 2: Entering phone number {phone_number} ---")
            sb.type(phone_input_selector, phone_number)
            print("Phone number entered successfully.")
            
            # Step 3: Click the submit button to trigger the CAPTCHA
            print("\n--- Step 3: Clicking submit button to trigger CAPTCHA ---")
            sb.click(submit_button_selector)
            print("Submit button clicked.")
            sb.sleep(2)
            
            # Step 4: Extract reCAPTCHA parameters
            print("\n--- Step 4: Extracting reCAPTCHA Parameters ---")
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
            
            # Step 5: Solve the CAPTCHA
            print("\n--- Step 5: Solving reCAPTCHA ---")
            token, success = solver.solve(params)
            
            if not success or not token:
                print("ERROR: Failed to solve the reCAPTCHA.")
                sb.save_screenshot("tmp/captcha_failed.png")
                return 1
                
            solve_time = time.time() - start_time
            print(f"\n✅ reCAPTCHA solved successfully in {solve_time:.2f} seconds!")
            print(f"Token (first 30 chars): {token[:30]}...")
            
            # Step 6: Apply the token to the page
            print("\n--- Step 6: Applying Token to Page ---")
            token_applied = submitter.apply_token(sb, token)
            
            if token_applied:
                print("✅ Token applied successfully to the page!")
                
                # Step 7: Click the check registration button to complete the form submission
                print("\n--- Step 7: Clicking check registration button ---")
                try:
                    sb.click(check_registration_selector)
                    print("Check registration button clicked successfully.")
                    
                    # Wait a moment to see the results
                    print("\nWaiting to observe the result...")
                    sb.sleep(5)
                    
                    # Take a screenshot of the result
                    screenshot_path = "results/lnnte_result.png"
                    sb.save_screenshot(screenshot_path)
                    print(f"Screenshot saved to: {screenshot_path}")
                except Exception as click_err:
                    print(f"ERROR clicking check registration button: {click_err}")
                    sb.save_screenshot("tmp/error_final_click.png")
            else:
                print("❌ Failed to apply token to the page")
                sb.save_screenshot("tmp/token_application_failed.png")
                return 1
            
            # Wait before closing the browser
            print("\nKeeping browser open for 10 seconds for observation...")
            sb.sleep(1000)
            
        # Calculate total time
        total_time = time.time() - start_time
        print(f"\nComplete workflow finished in {total_time:.2f} seconds")
        return 0
            
    except Exception as e:
        print(f"\nError during example: {e}")
        sb.save_screenshot("tmp/error_during_execution.png")
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