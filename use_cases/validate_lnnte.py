import os
from dotenv import load_dotenv
from captcha_solver import CaptchaSolver
import time
from concurrent.futures import ProcessPoolExecutor
import multiprocessing

# --- Load Environment Variables ---
load_dotenv() # Load variables from .env file
WIT_API_KEY = os.getenv("WIT_AI_API_KEY") # Get key from environment

# Target URL
url = "https://lnnte-dncl.gc.ca/en/Consumer/Check-your-registration/#!/"
# List of phone numbers to check
phone_numbers = ["418-313-3337", "418-313-3338", "418-313-3339", "418-313-3340", "418-313-3337", "418-313-3338", "418-313-3339", "418-313-3340"]
# --- Selectors ---
phone_input_selector = "#phone"
submit_button_selector = 'button[type="submit"]'
check_registration_selector = "body > div:nth-child(5) > div > div > div.container.ng-scope > div > div:nth-child(2) > div:nth-child(1) > div:nth-child(3) > div:nth-child(2) > form > div > div.submit-container > button:nth-child(2)"

# --- Ensure main tmp directory exists ---
TMP_DIR = "tmp"
RESULTS_DIR = "results"
os.makedirs(TMP_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# --- Process-aware printing ---
def process_print(*args, **kwargs):
    """Process-aware print function that includes the process ID"""
    print(f"[Process {os.getpid()}]", *args, **kwargs)

# --- Before CAPTCHA actions ---
def before_captcha_actions(sb, phone_number):
    """
    Actions to perform before solving the captcha.
    
    Args:
        sb: SeleniumBase instance
        phone_number: Phone number to check
    """
    # Explicitly activate CDP mode with the URL
    process_print(f"[{phone_number}] Activating CDP mode and navigating to: {url}")
    sb.activate_cdp_mode(url)
    process_print(f"[{phone_number}] Currently connected: {sb.is_connected()}")  # Should be False in CDP mode
    process_print(f"[{phone_number}] Waiting for page load...")
    sb.sleep(3)
    
    process_print(f"[{phone_number}] Typing phone number using CDP: {phone_number}")
    try:
        sb.cdp.wait_for_element_visible(phone_input_selector, timeout=15)
        sb.cdp.press_keys(phone_input_selector, phone_number)
        process_print(f"[{phone_number}] Phone number typed.")
        sb.sleep(1)
    except Exception as e:
        process_print(f"[{phone_number}] Error interacting with {phone_input_selector} input using CDP: {e}")
        # Save screenshot for debugging - using a single tmp folder
        sb.save_screenshot(f"{TMP_DIR}/error_phone_input_{phone_number.replace('-', '')}.png")
        sb.save_page_source(f"{TMP_DIR}/error_phone_input_{phone_number.replace('-', '')}.html")
        raise

    process_print(f"[{phone_number}] Clicking the submit button using CDP...")
    try:
        sb.cdp.wait_for_element_visible(submit_button_selector, timeout=15)
        sb.cdp.click(submit_button_selector)
        process_print(f"[{phone_number}] Submit button clicked.")
        sb.sleep(1)
    except Exception as e:
        process_print(f"[{phone_number}] Error clicking submit button using CDP: {e}")
        # Save screenshot for debugging - using a single tmp folder
        sb.save_screenshot(f"{TMP_DIR}/error_submit_click_{phone_number.replace('-', '')}.png")
        sb.save_page_source(f"{TMP_DIR}/error_submit_click_{phone_number.replace('-', '')}.html")
        raise

# --- After CAPTCHA actions ---
def after_captcha_actions(sb, captcha_solved_successfully, recaptcha_token, phone_number):
    """
    Actions to perform after attempting to solve the captcha.
    
    Args:
        sb: SeleniumBase instance
        captcha_solved_successfully: Boolean indicating if the CAPTCHA was solved
        recaptcha_token: The reCAPTCHA token if successful, None otherwise
        phone_number: The phone number being checked
    """
    if captcha_solved_successfully and recaptcha_token:
        process_print(f"\n[{phone_number}] --- CAPTCHA Solved - Clicking Submit Button Again ---")
        
        try:
            # Ensure we're in WebDriver mode for proper DOM interaction
            if not sb.is_connected():
                process_print(f"[{phone_number}] WebDriver not connected. Reconnecting for button click...")
                sb.reconnect()
                process_print(f"[{phone_number}] WebDriver connected: {sb.is_connected()}")
            
            # Click the button
            process_print(f"[{phone_number}] Clicking button with selector: {check_registration_selector}")
            sb.click(check_registration_selector)
            process_print(f"[{phone_number}] Button clicked successfully")
            
            # Wait for page transitions and capture the result
            sb.sleep(1)
            
            # Save screenshot of the result for this phone number in the results directory
            sb.save_screenshot(f"{RESULTS_DIR}/result_{phone_number.replace('-', '')}.png")
            
        except Exception as click_err:
            process_print(f"[{phone_number}] ERROR clicking button: {click_err}")
            sb.save_screenshot(f"{TMP_DIR}/error_final_click_{phone_number.replace('-', '')}.png")
            
    else:
        process_print(f"\n[{phone_number}] --- CAPTCHA Not Solved - Skipping final submit button click ---")
        sb.save_screenshot(f"{TMP_DIR}/captcha_failed_{phone_number.replace('-', '')}.png")

# --- Process a single phone number ---
def process_phone_number(phone_number):
    """
    Process a single phone number check
    
    Args:
        phone_number: Phone number to check
        
    Returns:
        tuple: (phone_number, success_status)
    """
    process_print(f"\n=== Processing phone number: {phone_number} ===")
    
    # Create a callback function that includes the phone number
    def before_callback(sb):
        before_captcha_actions(sb, phone_number)
        
    def after_callback(sb, captcha_solved_successfully, recaptcha_token):
        after_captcha_actions(sb, captcha_solved_successfully, recaptcha_token, phone_number)
    
    # Create a filename-safe version of the phone number for file naming
    safe_phone = phone_number.replace('-', '')
    
    # Create a CaptchaSolver instance with callbacks
    try:
        captcha_solver = CaptchaSolver(
            wit_api_key=WIT_API_KEY, 
            download_dir=TMP_DIR,  # Use the main tmp directory
            before_captcha_callback=before_callback,
            after_captcha_callback=after_callback
        )
        
        # Run the workflow for this phone number
        recaptcha_token, captcha_solved_successfully = captcha_solver.run_workflow(
            url=url,
            observation_time=2  # Keep browser open for 2 seconds at the end
        )
        
        # Report the outcome for this phone number
        if captcha_solved_successfully:
            process_print(f"\n[{phone_number}] CAPTCHA workflow completed successfully! Token: {recaptcha_token[:20]}...")
        else:
            process_print(f"\n[{phone_number}] CAPTCHA workflow failed.")
        
        return phone_number, captcha_solved_successfully
    except Exception as e:
        process_print(f"\n[{phone_number}] EXCEPTION during processing: {e}")
        # Save error information to a log file in the tmp directory
        try:
            with open(f"{TMP_DIR}/error_log_{safe_phone}.txt", "w") as f:
                f.write(f"Error processing {phone_number}: {str(e)}")
        except:
            pass  # If we can't write to the log file, just continue
        return phone_number, False

# --- Main Function ---
def validate_lnnte_numbers():
    """Main execution function to validate all phone numbers in the list concurrently"""
    print("Starting CAPTCHA Solver Workflow for multiple phone numbers concurrently...")
    start_time = time.time()
    
    # Set the maximum number of concurrent processes
    MAX_CONCURRENT = 3
    results = {}
    
    # Process phone numbers concurrently using ProcessPoolExecutor
    with ProcessPoolExecutor(max_workers=MAX_CONCURRENT) as executor:
        print(f"\nSubmitting {len(phone_numbers)} phone numbers to {MAX_CONCURRENT} concurrent processes...")
        
        # Submit tasks
        futures = [executor.submit(process_phone_number, phone) for phone in phone_numbers]
        
        # Process completed futures as they come in
        for future in futures:
            try:
                phone_number, success = future.result()
                results[phone_number] = success
            except Exception as exc:
                # We don't have the phone mapping here, so we'll just report the error
                print(f"\nA process generated an exception: {exc}")
    
    # Calculate execution time
    end_time = time.time()
    execution_time = end_time - start_time
    
    # Print summary of results
    print("\n=== Summary of Results ===")
    success_count = sum(1 for success in results.values() if success)
    print(f"Total phone numbers processed: {len(results)}")
    print(f"Successful verifications: {success_count}")
    print(f"Failed verifications: {len(results) - success_count}")
    
    for phone, success in results.items():
        print(f"Phone: {phone} - {'Success' if success else 'Failed'}")
    
    print(f"\nTotal execution time: {execution_time:.2f} seconds")
    print("Script finished.")

# Execute main function if script is run directly
if __name__ == "__main__":
    # This guard is necessary for ProcessPoolExecutor to work properly
    # on some operating systems (especially Windows)
    validate_lnnte_numbers()
