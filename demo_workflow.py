#!/usr/bin/env python
"""
Demo script showing two approaches to solve reCAPTCHA:

1. Simplified Approach: Using CaptchaSolver with explicitly managed extraction
2. Detailed Approach: Using individual components for maximum control

This demonstrates how the modular library can be used, maintaining
clear separation of concerns between extraction, solving, and token application.
"""

import sys
import time
import os
from seleniumbase import SB
from captcha_solver import CaptchaSolver, CaptchaExtractor, CaptchaReplicator, ChallengeSolver, TokenSubmitter
from dotenv import load_dotenv

load_dotenv()

def demo_simplified_approach():
    """Demo the simplified approach using CaptchaSolver with explicit extraction."""
    # Default settings - use Google's demo page
    target_url = "https://www.google.com/recaptcha/api2/demo"
    
    # Get Wit.ai API key from environment
    wit_api_key = os.environ.get("WIT_API_KEY")
    if not wit_api_key:
        print("ERROR: WIT_API_KEY environment variable is not set.")
        return False
        
    print("\n=== DEMO 1: Simplified reCAPTCHA Solving Approach ===")
    print("Using CaptchaSolver with explicit extraction")
    print(f"Target URL: {target_url}")
    
    # Create CaptchaSolver and CaptchaExtractor instances
    solver = CaptchaSolver(wit_api_key=wit_api_key, download_dir="tmp")
    extractor = CaptchaExtractor(download_dir="tmp")
    
    # Initialize browser
    browser = SB(uc=True, test=True, locale="en", ad_block=True, pls="none", headless=False)
    
    try:
        with browser as sb:
            # Navigate to the target URL
            print(f"\nNavigating to {target_url}...")
            sb.open(target_url)
            
            # Wait for page to load
            print(f"Waiting for page to load...")
            sb.sleep(2)
            
            # Extract parameters
            print("\nExtracting reCAPTCHA parameters...")
            params = extractor.extract_captcha_params(sb)
            
            if not params.get("website_key"):
                print("\nERROR: Could not extract reCAPTCHA site key.")
                return False
            
            # Solve the captcha
            print("\nSolving reCAPTCHA...")
            token, success = solver.solve(params)
            
            if not success or not token:
                print("\nFailed to solve reCAPTCHA.")
                return False
            
            print(f"\nCAPTCHA solved successfully! Token: {token[:20]}...")
            return True
    
    except Exception as e:
        print(f"\nError during simplified demo: {e}")
        return False
    finally:
        try:
            browser.quit()
        except:
            pass

def demo_detailed_approach():
    """Demo the detailed approach with direct component usage."""
    # Default settings - use Google's demo page
    target_url = "https://www.google.com/recaptcha/api2/demo"
    wait_time = 2

    # Get Wit.ai API key from environment
    wit_api_key = os.environ.get("WIT_API_KEY")
    if not wit_api_key:
        print("ERROR: WIT_API_KEY environment variable is not set.")
        return False

    print("\n=== DEMO 2: Detailed reCAPTCHA Solving Approach ===")
    print("Using individual components for maximum control")
    print(f"Target URL: {target_url}")

    # Create instances of all component classes
    extractor = CaptchaExtractor(download_dir="tmp")
    solver = CaptchaSolver(wit_api_key=wit_api_key, download_dir="tmp")
    submitter = TokenSubmitter(download_dir="tmp")

    # Initialize original browser that will be kept open throughout the process
    browser = None

    try:
        # Step 1: Extract reCAPTCHA parameters using browser automation
        print(f"\n=== Step 1: Initializing Browser and Extracting reCAPTCHA Parameters ===")

        # Initialize browser
        browser = SB(uc=True, test=True, locale="en", ad_block=True, pls="none", headless=False)

        with browser as sb:
            # Navigate to the target URL
            print(f"\nNavigating to {target_url}...")
            sb.open(target_url)

            # Wait for page to load
            print(f"Waiting {wait_time} seconds for page to load...")
            sb.sleep(wait_time)

            # Extract parameters using the active browser instance
            print("\nExtracting reCAPTCHA parameters...")
            params = extractor.extract_captcha_params(sb)
            
            # Check if we have the necessary parameters to proceed
            if not params["website_key"]:
                print("\nERROR: Could not extract reCAPTCHA site key.")
                return False

            # Step 2: Solve the captcha using the unified solver
            print("\n=== Step 2: Solving reCAPTCHA ===")
            print("Using the CaptchaSolver to solve the replicated CAPTCHA...")
            
            # Solve the CAPTCHA using extracted parameters
            token, success = solver.solve(params)
                
            # Check if we got a token
            if not token:
                print("\nERROR: Failed to solve the CAPTCHA. Aborting.")
                return False
                
            print(f"CAPTCHA solved successfully! Token obtained (length: {len(token)})")

            # Step 3: Apply the token back to the original page
            print("\n=== Step 3: Applying Solved Token to Original Page ===")

            # Apply the token to the original reCAPTCHA
            success = submitter.apply_token(sb, token, params, submit_form=True)

            if success:
                print("\n✅ Token application successful!")

                # Verify token application
                verification = submitter.verify_token_application(sb)
                if verification:
                    print("✅ Token verification successful")
                else:
                    print("❓ Token verification uncertain (but token was applied)")

                # Try to submit the form
                try:
                    # Look for submit buttons and try to click one
                    submit_result = sb.execute_script("""
                        try {
                            // Look for common submit buttons
                            const candidates = [
                                document.querySelector('button[type="submit"]'),
                                document.querySelector('input[type="submit"]'),
                                document.querySelector('button.g-recaptcha'),
                                document.querySelector('button:contains("Submit")'),
                                document.querySelector('button:contains("Verify")'),
                                document.querySelector('button:contains("Check")'),
                                document.getElementById('recaptcha-demo-submit')
                            ].filter(el => el);
                            
                            if (candidates.length > 0) {
                                candidates[0].click();
                                return "Clicked submit button";
                            }
                            
                            return "No submit button found";
                        } catch (e) {
                            return "Error clicking submit: " + e.message;
                        }
                    """)

                    print(f"Form submission: {submit_result}")
                except Exception as e:
                    print(f"Error attempting to submit form: {e}")
            else:
                print("\n❌ Token application failed")

            # Keep the original browser open for observation
            print("\nKeeping browser open for observation (10 seconds)...")
            sb.sleep(10)

        return success

    except KeyboardInterrupt:
        print("\nDemo interrupted by user. Cleaning up...")
        return False
    except Exception as e:
        print(f"\nError during demo: {e}")
        return False
    finally:
        # Make sure browser is closed
        if browser and hasattr(browser, 'driver') and browser.driver:
            try:
                browser.quit()
            except:
                pass

def main():
    """Run both demo approaches and report results."""
    # Get Wit.ai API key from environment - required for automatic solving
    wit_api_key = os.environ.get("WIT_API_KEY")
    if not wit_api_key:
        print("ERROR: WIT_API_KEY environment variable is not set.")
        print("Set the WIT_API_KEY environment variable with your Wit.ai API key and try again.")
        return 1

    print("\n=== reCAPTCHA Solver Library Demo ===")
    print("This demo shows two different approaches to using the library.")
    
    # Demo 1: Simplified approach
    simplified_success = demo_simplified_approach()
    
    # Demo 2: Detailed approach
    detailed_success = demo_detailed_approach()
    
    # Report results
    print("\n=== Demo Results ===")
    print(f"Simplified approach: {'✅ Success' if simplified_success else '❌ Failed'}")
    print(f"Detailed approach: {'✅ Success' if detailed_success else '❌ Failed'}")
    
    if simplified_success or detailed_success:
        print("\n✅ At least one approach succeeded!")
        return 0
    else:
        print("\n❌ Both approaches failed. This could be due to network issues or reCAPTCHA blocking.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
