#!/usr/bin/env python
"""
Demo script combining CaptchaExtractor, CaptchaReplicator, ChallengeSolver, and TokenApplier.

This script demonstrates a complete workflow with clear separation of concerns:
1. Extract reCAPTCHA parameters from a target website
2. Replicate the reCAPTCHA in a separate browser window
3. Solve the replicated reCAPTCHA using audio recognition
4. Apply the solved token back to the original website
"""

import sys
import time
import os
from seleniumbase import SB
from captcha_solver import CaptchaExtractor, CaptchaReplicator, ChallengeSolver, TokenApplier
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

    print("\n=== Complete reCAPTCHA Workflow Demo (Modular Approach) ===")
    print(f"Target URL: {target_url}")

    # Create instances of all component classes
    extractor = CaptchaExtractor(download_dir="tmp")
    replicator = CaptchaReplicator(download_dir="tmp")
    solver = ChallengeSolver(wit_api_key=wit_api_key, download_dir="tmp")
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

            # Step 2: Replicate the reCAPTCHA in a separate browser window
            print("\n=== Step 2: Replicating reCAPTCHA ===")
            print("Opening replicated reCAPTCHA in a new browser window...")

            # Replicate the captcha using extracted parameters
            # Only run the replicated captcha for 5 seconds to initialize the browser,
            # we'll handle solving separately
            html_path, replicated_sb, initial_token = replicator.replicate_captcha(
                website_key=params["website_key"],
                website_url=params["website_url"],
                is_invisible=params["is_invisible"],
                data_s_value=params["data_s_value"],
                is_enterprise=params["is_enterprise"],
                observation_time=5  # Just enough time to load, we'll solve separately
            )
            
            if not replicated_sb:
                print("\nERROR: Failed to create replicated CAPTCHA browser. Aborting.")
                return 1
                
            # Step 3: Solve the replicated CAPTCHA
            print("\n=== Step 3: Solving Replicated reCAPTCHA ===")
            print("Using audio recognition to solve the CAPTCHA...")
            
            # Solve the CAPTCHA using the replicated browser
            token, success = solver.solve(replicated_sb)
            
            # If solving failed, check if token was captured by the monitor thread
            if not success or not token:
                token = replicator.get_last_token()
            
            # Clean up the replicated browser and server
            print("Closing replicated CAPTCHA browser...")
            try:
                replicated_sb.quit()
            except:
                pass
            replicator.stop_http_server()
                
            # Check if we got a token
            if not token:
                print("\nERROR: Failed to solve the CAPTCHA. Aborting.")
                return 1
                
            print(f"CAPTCHA solved successfully! Token obtained (length: {len(token)})")

            # Step 4: Apply the token back to the original page
            print("\n=== Step 4: Applying Solved Token to Original Page ===")

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
