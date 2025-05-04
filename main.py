import os
from dotenv import load_dotenv
from captcha_solver import CaptchaSolver
import time

# --- Load Environment Variables ---
load_dotenv() # Load variables from .env file
WIT_API_KEY = os.getenv("WIT_AI_API_KEY") # Get key from environment

# Target URL
url = "https://lnnte-dncl.gc.ca/en/Consumer/Check-your-registration/#!/"
phone_number_to_enter = "418-313-3337" # Example

# --- Selectors ---
phone_input_selector = "#phone"
submit_button_selector = 'button[type="submit"]'
check_registration_selector = "body > div:nth-child(5) > div > div > div.container.ng-scope > div > div:nth-child(2) > div:nth-child(1) > div:nth-child(3) > div:nth-child(2) > form > div > div.submit-container > button:nth-child(2)"

# --- Before CAPTCHA actions ---
def before_captcha_actions(sb):
    """
    Actions to perform before solving the captcha.
    
    Args:
        sb: SeleniumBase instance
    """
    # Explicitly activate CDP mode with the URL
    print(f"Activating CDP mode and navigating to: {url}")
    sb.activate_cdp_mode(url)
    print(f"Currently connected: {sb.is_connected()}")  # Should be False in CDP mode
    print("Waiting for page load...")
    sb.sleep(3)
    
    print(f"Typing phone number using CDP: {phone_number_to_enter}")
    try:
        sb.cdp.wait_for_element_visible(phone_input_selector, timeout=15)
        sb.cdp.press_keys(phone_input_selector, phone_number_to_enter)
        print("Phone number typed.")
        sb.sleep(1)
    except Exception as e:
        print(f"Error interacting with {phone_input_selector} input using CDP: {e}")
        # Save screenshot for debugging
        os.makedirs("tmp", exist_ok=True)
        sb.save_screenshot("tmp/error_phone_input.png")
        sb.save_page_source("tmp/error_phone_input.html")
        raise

    print("Clicking the submit button using CDP...")
    try:
        sb.cdp.wait_for_element_visible(submit_button_selector, timeout=15)
        sb.cdp.click(submit_button_selector)
        print("Submit button clicked.")
        sb.sleep(5)
    except Exception as e:
        print(f"Error clicking submit button using CDP: {e}")
        # Save screenshot for debugging
        os.makedirs("tmp", exist_ok=True)
        sb.save_screenshot("tmp/error_submit_click.png")
        sb.save_page_source("tmp/error_submit_click.html")
        raise

# --- After CAPTCHA actions ---
def after_captcha_actions(sb, captcha_solved_successfully, recaptcha_token):
    """
    Actions to perform after attempting to solve the captcha.
    
    Args:
        sb: SeleniumBase instance
        captcha_solved_successfully: Boolean indicating if the CAPTCHA was solved
        recaptcha_token: The reCAPTCHA token if successful, None otherwise
    """
    if captcha_solved_successfully and recaptcha_token:
        print("\n--- CAPTCHA Solved - Clicking Submit Button Again ---")
        
        try:
            # Ensure we're in WebDriver mode for proper DOM interaction
            if not sb.is_connected():
                print("WebDriver not connected. Reconnecting for button click...")
                sb.reconnect()
                print(f"WebDriver connected: {sb.is_connected()}")
            
            # Click the button
            print(f"Clicking button with selector: {check_registration_selector}")
            sb.click(check_registration_selector)
            print("Button clicked successfully")
            
            # Wait for page transitions
            sb.sleep(5)
            
        except Exception as click_err:
            print(f"ERROR clicking button: {click_err}")
            
    else:
        print("\n--- CAPTCHA Not Solved - Skipping final submit button click ---")

# --- Main Function ---
def main():
    """Main execution function"""
    print("Starting CAPTCHA Solver Workflow...")

    # Create a CaptchaSolver instance with callbacks
    captcha_solver = CaptchaSolver(
        wit_api_key=WIT_API_KEY, 
        download_dir="tmp",
        before_captcha_callback=before_captcha_actions,
        after_captcha_callback=after_captcha_actions
    )
    
    # Let the CaptchaSolver handle the entire workflow
    # This includes:
    # 1. Creating a SeleniumBase instance with UC mode enabled
    # 2. Calling before_captcha_actions (which activates CDP and fills the form)
    # 3. Solving the CAPTCHA (which handles reconnection internally)
    # 4. Calling after_captcha_actions (which clicks the final button)
    # 5. Closing the browser
    recaptcha_token, captcha_solved_successfully = captcha_solver.run_workflow(
        url=url,
        observation_time=10  # Keep browser open for 10 seconds at the end
    )
    
    # Report the final outcome
    if captcha_solved_successfully:
        print(f"\nCAPTCHA workflow completed successfully! Token: {recaptcha_token[:20]}...")
    else:
        print("\nCAPTCHA workflow failed.")
    
    print("Script finished.")

# Execute main function if script is run directly
if __name__ == "__main__":
    main()
