#!/usr/bin/env python
"""
Demo script combining CaptchaExtractor, ReplicatedCaptcha, and TokenApplier.

This script demonstrates a complete workflow:
1. Extract reCAPTCHA parameters from a target website
2. Automatically solve the reCAPTCHA using audio recognition
3. Apply the solved token back to the original website
"""

import sys
import time
import os
from seleniumbase import SB
from captcha_solver import CaptchaExtractor, ReplicatedCaptcha, TokenApplier
from dotenv import load_dotenv

load_dotenv()

def main():
    """Run the complete reCAPTCHA workflow demonstration."""
    # Default settings - always use Google's demo page
    target_url = "https://www.google.com/recaptcha/api2/demo"
    wait_time = 2

    # Get Wit.ai API key from environment - required for automatic solving
    wit_api_key = os.environ.get("WIT_API_KEY")
    if not wit_api_key:
        print("ERROR: WIT_API_KEY environment variable is not set.")
        print("Set the WIT_API_KEY environment variable with your Wit.ai API key and try again.")
        return 1

    print("\n=== Complete reCAPTCHA Workflow Demo ===")
    print(f"Target URL: {target_url}")
    print(f"Auto-solving is ALWAYS enabled")

    # Create instances of all three classes
    extractor = CaptchaExtractor(download_dir="tmp")
    replicator = ReplicatedCaptcha(download_dir="tmp")
    applier = TokenApplier(download_dir="tmp")

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
                print("The page may not have a reCAPTCHA, or it might be dynamically loaded.")
                return 1

            # Step 2: Automatically solve the reCAPTCHA
            print("\n=== Step 2: Solving reCAPTCHA Automatically ===")
            print("Using audio recognition to solve the CAPTCHA...")

            # Solve the captcha using extracted parameters (always auto-solve)
            _, _, token = replicator.run_replicated_captcha(
                website_key=params["website_key"],
                website_url=params["website_url"],
                is_invisible=params["is_invisible"],
                data_s_value=params["data_s_value"],
                is_enterprise=params["is_enterprise"],
                observation_time=4,      # Give it 30 seconds to solve
                auto_solve=True,          # Always auto-solve
                wit_api_key=wit_api_key   # API key for Wit.ai
            )

            # Check if we got a token
            if not token:
                print("\nERROR: Failed to solve the CAPTCHA automatically.")
                # Try one more time with the get_token method
                print("Trying again with direct token retrieval method...")
                token = replicator.get_token(
                    website_key=params["website_key"],
                    website_url=params["website_url"],
                    is_invisible=params["is_invisible"],
                    data_s_value=params["data_s_value"],
                    is_enterprise=params["is_enterprise"],
                    timeout=45,  # Longer timeout for retry
                    wit_api_key=wit_api_key
                )
                
                if not token:
                    print("\nERROR: Still failed to get a token. Aborting.")
                    return 1

            # Step 3: Apply the token back to the original page
            print("\n=== Step 3: Applying Solved Token to Original Page ===")
            print(f"Token obtained! Length: {len(token)}")

            # Apply the token to the original reCAPTCHA
            success = applier.apply_token(sb, token, params, submit_form=True)

            if success:
                print("\n✅ Token application successful!")

                # Verify token application
                verification = applier.verify_token_application(sb)
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

        print("\n=== Complete reCAPTCHA Workflow Demo Completed ===")
        return 0

    except KeyboardInterrupt:
        print("\nDemo interrupted by user. Cleaning up...")
        # Ensure all resources are cleaned up
        replicator.stop_http_server()
        return 1
    except Exception as e:
        print(f"\nError during demo: {e}")
        # Ensure all resources are cleaned up
        replicator.stop_http_server()
        return 1
    finally:
        # Make sure browser is closed
        if browser and hasattr(browser, 'driver') and browser.driver:
            try:
                browser.quit()
            except:
                pass


if __name__ == "__main__":
    sys.exit(main())
