from seleniumbase import SB
from captcha_solver import CaptchaSolver
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# URL with reCAPTCHA to solve
TARGET_URL = "https://lnnte-dncl.gc.ca/en/Consumer/Check-your-registration/#!/"
PHONE_NUMBER = "418-313-3337"  # Example phone number

# Define a callback function to execute before solving the captcha
def before_captcha_actions(sb):
    """
    Actions to perform before solving the captcha.
    
    This function is called with the SeleniumBase instance as an argument,
    allowing you to interact with the page before solving the captcha.
    """
    print("\n--- Executing before_captcha_actions ---")
    
    # Input phone number
    phone_input_selector = "#phone"
    print(f"Typing phone number: {PHONE_NUMBER}")
    
    try:
        sb.wait_for_element_visible(phone_input_selector, timeout=15)
        sb.type(phone_input_selector, PHONE_NUMBER)
        print("Phone number typed.")
        sb.sleep(1)
    except Exception as e:
        print(f"Error interacting with {phone_input_selector} input using CDP: {e}")
        # Save screenshot for debugging
        os.makedirs("tmp", exist_ok=True)
        sb.save_screenshot("tmp/error_phone_input.png")
        sb.save_page_source("tmp/error_phone_input.html")
        raise
    
    # Click submit button to trigger captcha
    submit_button_selector = 'button[type="submit"]'
    print("Clicking the submit button...")
    
    try:
        sb.wait_for_element_visible(submit_button_selector, timeout=15)
        sb.click(submit_button_selector)
        print("Submit button clicked.")
        sb.sleep(2)  # Short wait to let page respond
    except Exception as e:
        print(f"Error clicking submit button using CDP: {e}")
        # Save screenshot for debugging
        os.makedirs("tmp", exist_ok=True)
        sb.save_screenshot("tmp/error_submit_click.png")
        sb.save_page_source("tmp/error_submit_click.html")
        raise
    
    print("--- before_captcha_actions completed ---\n")

# Define a callback function to execute after solving the captcha
def after_captcha_actions(sb, captcha_solved_successfully):
    """
    Actions to perform after attempting to solve the captcha.
    
    Args:
        sb: SeleniumBase instance
        captcha_solved_successfully: Boolean indicating if the CAPTCHA was solved
    """
    print("\n--- Executing after_captcha_actions ---")
    
    if captcha_solved_successfully:
        # Define the specific selector for the "Check registration" button after CAPTCHA
        check_registration_selector = ("body > div:nth-child(5) > div > div > div.container.ng-scope > div > "
                                     "div:nth-child(2) > div:nth-child(1) > div:nth-child(3) > div:nth-child(2) > "
                                     "form > div > div.submit-container > button:nth-child(2)")
        
        try:
            # Ensure WebDriver is active and in main frame
            sb.reconnect()
            sb.switch_to_default_content()
            
            # Click the button
            sb.click(check_registration_selector)
            print("Button clicked successfully")
            
            # Wait for page transitions
            sb.sleep(5)
            
        except Exception as click_err:
            print(f"ERROR clicking button: {click_err}")
    else:
        print("CAPTCHA was not solved successfully, skipping final submit button click")
    
    print("--- after_captcha_actions completed ---\n")

def main():
    # Get Wit.ai API key from environment
    wit_api_key = os.getenv("WIT_AI_API_KEY")
    
    if not wit_api_key:
        print("ERROR: Wit.ai API key not found in environment variables")
        print("Please create a .env file with WIT_AI_API_KEY=your_api_key")
        return

    # Create captcha solver instance
    captcha_solver = CaptchaSolver(
        wit_api_key=wit_api_key,
        download_dir="tmp"
    )
    
    print("Starting SeleniumBase with UC Mode...")
    with SB(uc=True, test=True, locale="en", ad_block=True, pls="none") as sb:
        print(f"Navigating to: {TARGET_URL}")
        sb.activate_cdp_mode(TARGET_URL)
        print(f"Currently connected: {sb.is_connected()}")  # False (CDP mode)

        print("Waiting for page load and initial checks...")
        sb.sleep(3)

        # Execute actions before solving captcha (fill form, click submit)
        before_captcha_actions(sb)
        
        # Reconnect WebDriver for iframe DOM interaction
        print("Reconnecting WebDriver...")
        sb.reconnect()
        print(f"Currently connected: {sb.is_connected()}")  # True
        
        # Solve the CAPTCHA using our CaptchaSolver class
        recaptcha_token, captcha_solved_successfully = captcha_solver.solve(sb)
            
        # Execute actions after solving captcha (submit form)
        after_captcha_actions(sb, captcha_solved_successfully)

        print("\nProcessing finished. Observing final state...")
        sb.sleep(10)  # Keep browser open briefly to see result
        
        print("Script finished.")

if __name__ == "__main__":
    main() 