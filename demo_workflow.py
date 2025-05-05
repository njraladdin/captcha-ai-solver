#!/usr/bin/env python
"""
Demo script combining CaptchaExtractor, ReplicatedCaptcha, and TokenApplier.

This script demonstrates a complete workflow:
1. Extract reCAPTCHA parameters from a target website
2. Replicate the reCAPTCHA using the extracted parameters
3. Apply the solved token back to the original website
"""

import sys
import time
from seleniumbase import SB
from captcha_solver import CaptchaExtractor, ReplicatedCaptcha, TokenApplier


def main():
    """Run the complete reCAPTCHA workflow demonstration."""
    # Process command-line arguments
    # Use default if no URL provided
    # Using 2captcha's demo page which should work well
    url = "https://www.google.com/recaptcha/api2/demo"
    wait_time = 1

    print("\n=== Complete reCAPTCHA Workflow Demo ===")
    print("No URL provided. Using 2captcha's demo reCAPTCHA page.")
    print(
        "For custom page, use: python demo_extract_and_replicate.py <url> [wait_time]")
    print(f"Example: python demo_extract_and_replicate.py {url} 15")

    # Create instances of all three classes
    extractor = CaptchaExtractor(download_dir="tmp")
    replicator = ReplicatedCaptcha(download_dir="tmp")
    applier = TokenApplier(download_dir="tmp")

    # Initialize original browser that will be kept open throughout the process
    browser = None

    try:
        # Step 1: Extract reCAPTCHA parameters using browser automation
        print(f"\n=== Step 1: Initializing Browser and Extracting reCAPTCHA Parameters ===")
        print(f"Target URL: {url}")
        print(f"Wait time: {wait_time} seconds")

        # Initialize browser
        browser = SB(uc=True, test=True, locale="en", ad_block=True, pls="none", headless=False)

        with browser as sb:
            # Navigate to the target URL
            print(f"\nNavigating to {url}...")
            sb.open(url)

            # Wait for page to load
            sb.sleep(wait_time/2)

            # Extract parameters using the active browser instance
            print("\nExtracting reCAPTCHA parameters...")
            params = extractor.extract_captcha_params(sb)
            print(params)
            # Check if we have the necessary parameters to proceed
            if not params["website_key"]:
                print("\nERROR: Could not extract reCAPTCHA site key.")
                print(
                    "The page may not have a reCAPTCHA, or it might be dynamically loaded.")
                return 1

            # Step 2: Replicate the reCAPTCHA in a new browser window
            print("\n=== Step 2: Replicating reCAPTCHA in New Window ===")
            print("Opening replicated reCAPTCHA in a new browser window...")

            # Replicate the captcha using extracted parameters
            html_path, replicated_browser = replicator.run_replicated_captcha(
                website_key=params["website_key"],
                website_url=params["website_url"],
                is_invisible=params["is_invisible"],
                data_s_value=params["data_s_value"],
                is_enterprise=params["is_enterprise"],
                observation_time=0  # Keep browser open until manually closed or token received
            )


            # Wait for user to solve the CAPTCHA
            print("\nPlease solve the reCAPTCHA in the newly opened browser window.")
            print("The token will be displayed after solving.")
            print("Copy the token displayed after solving and press Enter to continue...")

            token = input(
                "\nEnter the solved token (or press Enter if token was automatically detected): ")

            # If token is empty, try to get it from the replicator
            if not token:
                token = replicator.get_last_token()

            if not token:
                print(
                    "\nERROR: No token provided or detected. Cannot proceed with token application.")
                # Make sure to clean up
                replicator.stop_http_server()
                if replicated_browser:
                    try:
                        replicated_browser.quit()
                    except:
                        pass
                return 1

            # Step 3: Apply the token back to the original page
            print("\n=== Step 3: Applying Solved Token to Original Page ===")
            print(f"Token (truncated): {token[:30]}...")

            # Apply the token to the original reCAPTCHA
            success = applier.apply_token(sb, token, params, submit_form= True)

            if success:
                print("\n✅ Token application process completed")

                # Verify token application
                verification = applier.verify_token_application(sb)
                if verification:
                    print("\n✅ Token verification successful")
                else:
                    print(
                        "\n❌ Token verification failed (but token may still be applied correctly)")

                # Try to submit the form if possible
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
                                document.querySelector('button:contains("Check")')
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

                    print(f"\nForm submission attempt: {submit_result}")
                except Exception as e:
                    print(f"\nError attempting to submit form: {e}")
            else:
                print("\n❌ Token application failed")

            # Clean up replicated captcha browser and server
            replicator.stop_http_server()
            if replicated_browser:
                try:
                    replicated_browser.quit()
                except:
                    pass

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
