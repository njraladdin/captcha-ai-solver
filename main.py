from seleniumbase import SB
import time
from selenium.common.exceptions import NoSuchElementException, TimeoutException, NoSuchFrameException
import os
import requests
from dotenv import load_dotenv
import json
import random  # Add import for random module

# --- Load Environment Variables ---
load_dotenv() # Load variables from .env file
WIT_API_KEY = os.getenv("WIT_AI_API_KEY") # Get key from environment

# Target URL
url = "https://lnnte-dncl.gc.ca/en/Consumer/Check-your-registration/#!/"
phone_number_to_enter = "418-313-3337" # Example

# --- Selectors ---
phone_input_selector = "#phone"
submit_button_selector = 'button[type="submit"]'
recaptcha_anchor_frame_selector = 'iframe[src*="api2/anchor"]' # Initial checkbox iframe
recaptcha_checkbox_selector = '.recaptcha-checkbox-border'   # Checkbox inside anchor frame
recaptcha_challenge_frame_selector = 'iframe[src*="api2/bframe"]' # Challenge iframe (image/audio)
audio_button_selector = "#recaptcha-audio-button"              # Audio button inside challenge frame

# Selectors for checking state AFTER clicking audio button (inside challenge frame)
audio_challenge_input_selector = "#audio-response" # Input field for audio answer
audio_challenge_source_selector = '#audio-source[src]' # Check if audio source exists and has src
blocked_message_selector = ".rc-doscaptcha-header-text" # Element containing potential block message
blocked_message_text = "Try again later"               # Common blocking text
recaptcha_verify_button_selector = "#recaptcha-verify-button"  # Add verify button selector
# New selectors for post-verification polling
recaptcha_token_selector = 'textarea[name="g-recaptcha-response"]' # In main content 
recaptcha_error_message_selector = ".rc-audiochallenge-error-message" # In challenge frame
recaptcha_error_message_text = "Multiple correct solutions required" # Common "need more" text

# --- Audio Download Function ---
def download_audio(audio_url, save_dir=".", filename="recaptcha_audio.mp3"):
    """Downloads audio from a URL and saves it."""
    if not audio_url:
        print("ERROR: No audio URL provided for download.")
        return None
    filepath = os.path.join(save_dir, filename)
    print(f"Attempting to download audio from: {audio_url[:60]}...")
    print(f"Saving to: {filepath}")
    try:
        # Ensure the save directory exists
        os.makedirs(save_dir, exist_ok=True)

        # Make the request - no session/cookies needed usually
        response = requests.get(audio_url, stream=True, timeout=30) # Add timeout
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        # Save the content to a file
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"SUCCESS: Audio downloaded and saved to {filepath}")
        return filepath
    except requests.exceptions.RequestException as req_err:
        print(f"ERROR downloading audio (Request failed): {req_err}")
    except OSError as os_err:
        print(f"ERROR saving audio file: {os_err}")
    except Exception as e:
        print(f"UNEXPECTED ERROR during audio download: {e}")
    return None


def transcribe_audio_with_wit(audio_filepath, api_key, max_retries=3):
    """Sends audio file to Wit.ai for transcription with retries."""
    if not api_key:
        print("ERROR: Wit.ai API Key not provided or found in environment.")
        return None
    if not audio_filepath or not os.path.exists(audio_filepath):
        print(f"ERROR: Audio file not found at {audio_filepath}")
        return None

    for attempt in range(max_retries):
        if attempt > 0:
            print(f"Transcription RETRY attempt {attempt+1}/{max_retries}...")
        
        print(f"Transcribing audio file: {audio_filepath} using Wit.ai...")
        try:
            # Read audio file data
            with open(audio_filepath, 'rb') as audio_file:
                audio_data = audio_file.read()

            # Prepare headers for Wit.ai API
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'audio/mpeg', # reCAPTCHA usually provides mp3
            }

            # Send POST request to Wit.ai Speech API
            wit_url = 'https://api.wit.ai/speech?v=20230215' # Use a recent API version
            response = requests.post(wit_url, headers=headers, data=audio_data, timeout=45) # Increased timeout
            response.raise_for_status() # Check for HTTP errors

            # Process the response - Wit might send multiple JSON objects
            response_text = response.text.strip()
            print(f"Wit.ai raw response: {response_text[:500]}...") # Log beginning of response
            
            # Use a simpler approach: extract all "text" values and use the last one
            import re
            text_matches = re.findall(r'"text":\s*"([^"]+)"', response_text)
            
            if text_matches:
                # Get the last text match which is typically the most confident transcription
                transcription = text_matches[-1]
                print(f"SUCCESS: Wit.ai transcription: '{transcription}'")
                return transcription
            else:
                print(f"WARNING: Could not extract transcription from Wit.ai response (Attempt {attempt+1}/{max_retries})")
                # Only return None on the last retry
                if attempt == max_retries - 1:
                    print("ERROR: All transcription attempts failed.")
                    return None
                # Add a small delay before retrying
                time.sleep(1)
                continue

        except requests.exceptions.RequestException as req_err:
            print(f"ERROR during Wit.ai request: {req_err}")
            # Log potentially useful info from response if available
            if 'response' in locals() and response is not None:
                 print(f"Wit.ai response status: {response.status_code}")
                 print(f"Wit.ai response text: {response.text[:500]}...") # Log beginning of response
            
            # Only return None on the last retry
            if attempt == max_retries - 1:
                print(f"ERROR: All {max_retries} transcription attempts failed due to request errors.")
                return None
            time.sleep(1)
            continue
            
        except FileNotFoundError:
            print(f"ERROR: Audio file disappeared before transcription: {audio_filepath}")
            return None  # No point retrying if file is gone
            
        except Exception as e:
            print(f"UNEXPECTED ERROR during transcription: {e}")
            
            # Only return None on the last retry
            if attempt == max_retries - 1:
                print(f"ERROR: All {max_retries} transcription attempts failed due to unexpected errors.")
                return None
            time.sleep(1)
            continue

    return None  # Should never reach here, but just in case

# --- Helper Functions ---
def check_for_token(sb):
    """Check for token presence and return it if found"""
    try:
        # Check using JavaScript evaluation rather than Selenium's visibility check
        token_script = """
            const textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
            return textarea && textarea.value ? textarea.value : null;
        """
        token_val = sb.execute_script(token_script)
        if token_val and len(token_val) > 50:  # Basic validation
            return token_val
        return None
    except Exception as e:
        print(f"Token check error (non-fatal): {e}")
        return None

def check_for_need_more_solutions(sb, frame_selector):
    """Check if challenge requires more solutions"""
    try:
        # First ensure we're in the challenge frame
        sb.switch_to_default_content()
        if not sb.is_element_visible(frame_selector):
            return False  # Frame not even visible
        
        sb.switch_to_frame(frame_selector)
        
        # Check using JavaScript for more reliable visibility detection
        error_script = """
            const errorEl = document.querySelector('.rc-audiochallenge-error-message');
            if (!errorEl) return false;
            
            const style = window.getComputedStyle(errorEl);
            const isVisible = style.display !== 'none' && style.visibility !== 'hidden';
            
            return isVisible && errorEl.textContent.includes('Multiple correct solutions required');
        """
        return sb.execute_script(error_script)
    except Exception as e:
        print(f"Need more check error (non-fatal): {e}")
        return False

def check_for_blocking(sb, frame_selector):
    """Check if we're blocked"""
    try:
        # First ensure we're in the challenge frame
        sb.switch_to_default_content()
        if not sb.is_element_visible(frame_selector):
            return False  # Frame not even visible
        
        sb.switch_to_frame(frame_selector)
        
        # Check using JavaScript for more reliable visibility detection
        blocked_script = """
            const msgEl = document.querySelector('.rc-doscaptcha-header-text');
            if (!msgEl) return false;
            
            const style = window.getComputedStyle(msgEl);
            const isVisible = style.display !== 'none' && style.visibility !== 'hidden';
            
            return isVisible && msgEl.textContent.includes('Try again later');
        """
        return sb.execute_script(blocked_script)
    except Exception as e:
        print(f"Blocking check error (non-fatal): {e}")
        return False

def solve_captcha(sb):
    """
    Solves the reCAPTCHA challenge using audio transcription.
    
    This function handles the complete reCAPTCHA solving process, including:
    1. Finding and clicking the initial checkbox
    2. Checking if token is immediately available (no challenge)
    3. If needed, switching to the audio challenge
    4. Downloading, transcribing, and submitting the audio challenge
    5. Handling retry logic for multiple audio challenges if needed
    6. Detecting and handling various error cases (blocking, multiple solutions required)
    
    Args:
        sb: SeleniumBase instance with an active connection
        
    Returns:
        tuple: (token, success_status)
            - token: The reCAPTCHA token string if successful, None otherwise
            - success_status: Boolean indicating whether the CAPTCHA was successfully solved
    """
    print("\n--- Starting reCAPTCHA Interaction ---")
    
    # Initialize result variables
    captcha_solved_successfully = False
    audio_challenge_loaded = False
    got_blocked = False
    audio_url = None
    audio_file_path = None
    unexpected_error_occurred = False
    error_message = ""
    transcription = None
    transcription_submitted = False
    captcha_failed_need_more = False
    recaptcha_token = None

    try:
        # 1. Interact with the Anchor Frame (Initial Checkbox)
        print(f"Waiting for reCAPTCHA anchor iframe: '{recaptcha_anchor_frame_selector}'")
        sb.wait_for_element_visible(recaptcha_anchor_frame_selector, timeout=20)
        print("Anchor iframe is visible.")
        print("Switching to reCAPTCHA anchor iframe...")
        sb.switch_to_frame(recaptcha_anchor_frame_selector)

        print(f"Waiting for checkbox inside anchor iframe: '{recaptcha_checkbox_selector}'")
        sb.wait_for_element_visible(recaptcha_checkbox_selector, timeout=15)
        print("Clicking checkbox inside anchor iframe...")
        try:
            sb.click(recaptcha_checkbox_selector)
        except Exception:
            print("Standard click failed, trying JS click on checkbox...")
            sb.js_click(recaptcha_checkbox_selector)
        print("Clicked the initial reCAPTCHA checkbox.")
        sb.sleep(1.5)
        
        # Check if token appeared immediately after clicking checkbox
        # (some CAPTCHAs don't require a challenge)
        sb.switch_to_default_content()
        print("Checking for immediate token after checkbox click...")
        immediate_token_check_time = time.time()
        immediate_token_max_wait = 3  # Check for 3 seconds
        
        # Quick poll for immediate token
        while time.time() - immediate_token_check_time < immediate_token_max_wait:
            token_val = check_for_token(sb)
            if token_val:
                print(f"SUCCESS! Immediate token found: {token_val[:20]}...")
                recaptcha_token = token_val
                captcha_solved_successfully = True
                break
            sb.sleep(0.1)
            
        # Only proceed to challenge frame if we didn't get an immediate token
        if not recaptcha_token:
            # 2. Interact with the Challenge Frame (Audio Button)
            print("No immediate token found. Proceeding to challenge frame...")
            
            print(f"Waiting for reCAPTCHA challenge iframe: '{recaptcha_challenge_frame_selector}'")
            sb.wait_for_element_visible(recaptcha_challenge_frame_selector, timeout=25)
            print("Challenge iframe is visible.")

            print("Switching to reCAPTCHA challenge iframe...")
            sb.switch_to_frame(recaptcha_challenge_frame_selector)
            challenge_frame_handle = sb.driver.current_window_handle # Store for potential reuse
            challenge_frame_name_or_id = sb.driver.execute_script("return window.frameElement ? (window.frameElement.name || window.frameElement.id) : null")
            print(f"Identified challenge frame handle/id: {challenge_frame_name_or_id}") # Helpful for debug

            print(f"Waiting for audio button inside challenge iframe: '{audio_button_selector}'")
            sb.wait_for_element_visible(audio_button_selector, timeout=18)
            print("Clicking audio button inside challenge iframe...")
            try:
                 sb.click(audio_button_selector)
            except Exception:
                print("Standard click failed, trying JS click on audio button...")
                sb.js_click(audio_button_selector)
            print("Clicked the audio button.")

            # 3. Check the state AFTER clicking the audio button using polling ("race")
            print("Checking outcome after clicking audio button (polling)...")

            max_wait_time = 15
            poll_interval = 0.2
            start_time = time.time()
            final_outcome_determined = False

            while time.time() - start_time < max_wait_time:
                # Ensure we're in the right frame before each check iteration
                try:
                    # First go back to default content to get a clean slate
                    sb.switch_to_default_content()
                    print("Polling: Switched to default content for fresh frame reference")
                    
                    # Make sure challenge frame is still available and visible
                    if sb.is_element_visible(recaptcha_challenge_frame_selector):
                        print("Polling: Challenge iframe is visible, switching to it...")
                        sb.switch_to_frame(recaptcha_challenge_frame_selector)
                        print("Polling: Successfully switched to challenge frame")
                    else:
                        print("Polling WARNING: Challenge iframe not visible, might be changing...")
                        # Wait a moment for frame to potentially stabilize
                        sb.sleep(0.5)
                        if sb.is_element_visible(recaptcha_challenge_frame_selector):
                            print("Polling: Challenge iframe reappeared, switching to it...")
                            sb.switch_to_frame(recaptcha_challenge_frame_selector)
                            print("Polling: Successfully switched to challenge frame")
                        else:
                            print("Polling ERROR: Challenge iframe still not visible after waiting")
                            # Don't mark as error yet, just continue to next poll iteration
                            sb.sleep(poll_interval)
                            continue
                except Exception as frame_err:
                    print(f"Polling WARNING: Could not switch to challenge frame: {frame_err}")
                    # Don't fail immediately, try again on next iteration
                    sb.sleep(poll_interval)
                    continue
                    
                # Check for blocking message
                if sb.is_text_visible(blocked_message_text, selector=blocked_message_selector):
                    print(f"Polling check: Blocking message FOUND & VISIBLE: '{blocked_message_text}'")
                    got_blocked = True
                    captcha_solved_successfully = False
                    final_outcome_determined = True
                    break

                # Check for audio challenge input and extract URL
                if sb.is_element_visible(audio_challenge_input_selector):
                     print("Polling check: Audio challenge input field IS visible.")
                     # *** EXTRACT AUDIO URL HERE ***
                     try:
                         # Make sure the source element exists before getting attribute
                         if sb.is_element_present(audio_challenge_source_selector):
                             audio_url = sb.get_attribute(audio_challenge_source_selector, "src")
                             if audio_url:
                                 print(f"Polling check: Extracted Audio URL: {audio_url[:60]}...") # Print beginning
                                 audio_challenge_loaded = True
                                 captcha_solved_successfully = True # Tentatively successful
                             else:
                                 print("Polling check WARNING: Audio source 'src' attribute is empty.")
                                 # Treat as potentially loaded but log warning
                                 audio_challenge_loaded = True
                                 captcha_solved_successfully = True
                         else:
                              print("Polling check WARNING: Audio source element not found, cannot get URL.")
                              audio_challenge_loaded = True # Input is visible, so mark as tentatively loaded
                              captcha_solved_successfully = True

                     except Exception as get_attr_err:
                          print(f"Polling check ERROR: Failed to get audio src attribute: {get_attr_err}")
                          # Consider this a failure state for audio loading
                          audio_challenge_loaded = False
                          captcha_solved_successfully = False

                     final_outcome_determined = True
                     break # Exit loop, audio challenge state determined

                sb.sleep(poll_interval)

            if not final_outcome_determined:
                print(f"WARNING: Neither blocking message nor audio challenge found after polling for {max_wait_time} seconds.")
                captcha_solved_successfully = False

            sb.sleep(0.5)
            
            # Process audio challenge if loaded successfully
            transcription_submitted = False  # Track if we submitted the transcription
            
            #    *** This section now happens WHILE WebDriver is connected and IN challenge frame ***
            if audio_url and captcha_solved_successfully and not got_blocked:
                # Set up audio challenge retry loop
                max_audio_attempts = 3  # Maximum number of audio challenge attempts
                for audio_attempt in range(max_audio_attempts):
                    if audio_attempt > 0:
                        print(f"\n--- Audio Challenge Retry {audio_attempt+1}/{max_audio_attempts} ---")
                        # Click the reload button to get a new audio
                        try:
                            reload_button_selector = "#recaptcha-reload-button"
                            print(f"Clicking reload button: {reload_button_selector}")
                            sb.wait_for_element_visible(reload_button_selector, timeout=10)
                            sb.click(reload_button_selector)
                            print("Clicked reload button for new audio challenge.")
                            
                            # Wait for the new audio to load
                            sb.sleep(1.5)
                            
                            # Get the new audio URL
                            if sb.is_element_present(audio_challenge_source_selector):
                                audio_url = sb.get_attribute(audio_challenge_source_selector, "src")
                                if audio_url:
                                    print(f"New audio URL: {audio_url[:60]}...")
                                else:
                                    print("WARNING: New audio source 'src' attribute is empty.")
                                    continue  # Try next attempt
                            else:
                                print("WARNING: Audio source element not found after reload.")
                                continue  # Try next attempt
                        except Exception as reload_err:
                            print(f"ERROR clicking reload button: {reload_err}")
                            continue  # Try next attempt
                    
                    print("\n--- Attempting Audio Download (WebDriver connected) ---")
                    # Note: Download happens outside the browser process, connection is just maintained
                    audio_file_path = download_audio(audio_url, filename=f"recaptcha_audio_{audio_attempt+1}.mp3")
                    if not audio_file_path:
                        print(f"Download failed on attempt {audio_attempt+1}/{max_audio_attempts}.")
                        continue  # Try next attempt
                        
                    print("\n--- Attempting Audio Transcription (WebDriver connected) ---")
                    transcription = transcribe_audio_with_wit(audio_file_path, WIT_API_KEY)
                    if not transcription:
                        print(f"Transcription failed on attempt {audio_attempt+1}/{max_audio_attempts}.")
                        continue  # Try next attempt
                        
                    print(f"\n--- Submitting Transcription: '{transcription}' ---")
                    try:
                        # Still inside challenge iframe here
                        print(f"Typing transcription into: {audio_challenge_input_selector}")
                        sb.type(audio_challenge_input_selector, transcription)
                        print("Transcription typed.")
                        sb.sleep(0.3 + random.uniform(0.1, 0.4)) # Add jitter

                        print(f"Clicking Verify button: {recaptcha_verify_button_selector}")
                        sb.wait_for_element_visible(recaptcha_verify_button_selector, timeout=10)
                        try:
                            sb.click(recaptcha_verify_button_selector)
                        except Exception:
                            sb.js_click(recaptcha_verify_button_selector)
                        transcription_submitted = True
                        print("Verify button clicked.")
                        
                        # 5. *** NEW: Poll for result AFTER clicking Verify ***
                        print("\n--- Polling for result after Verify ---")
                        verify_max_wait = 20 # Increased to 20 seconds for more time to detect token
                        verify_poll_interval = 0.1  # More frequent polling (100ms)
                        verify_start_time = time.time()
                        verify_outcome_determined = False
                        captcha_solved_successfully = False # Reset success, confirm based on token
                        
                        # Main polling loop with all checks
                        while time.time() - verify_start_time < verify_max_wait:
                            # Always check for token first - most important outcome
                            token_val = check_for_token(sb)
                            if token_val:
                                print(f"Verify Polling: SUCCESS! Token found: {token_val[:20]}...")
                                recaptcha_token = token_val
                                captcha_solved_successfully = True
                                verify_outcome_determined = True
                                break
                            
                            # If token not found, check for frame-based failure cases
                            
                            # Check for "need more solutions" error
                            if check_for_need_more_solutions(sb, recaptcha_challenge_frame_selector):
                                print(f"Verify Polling: FAILURE! Error found: '{recaptcha_error_message_text}'")
                                captcha_failed_need_more = True
                                captcha_solved_successfully = False
                                verify_outcome_determined = True
                                break
                            
                            # Check for blocking message
                            if check_for_blocking(sb, recaptcha_challenge_frame_selector):
                                print(f"Verify Polling: FAILURE! Blocked message found: '{blocked_message_text}'")
                                got_blocked = True
                                captcha_solved_successfully = False
                                verify_outcome_determined = True
                                break
                            
                            # None of the success/failure conditions met yet, wait and try again
                            sb.sleep(verify_poll_interval)
                            
                            # Diagnostic message every few seconds
                            elapsed = time.time() - verify_start_time
                            if elapsed > 0 and elapsed % 2 < verify_poll_interval:
                                print(f"Verify Polling: Still checking outcomes... ({elapsed:.1f}s elapsed)")
                                
                                # Check if challenge frame is still visible
                                try:
                                    sb.switch_to_default_content()
                                    frame_visible = sb.is_element_visible(recaptcha_challenge_frame_selector)
                                    print(f"Verify Polling: Challenge frame visible: {frame_visible}")
                                except Exception as e:
                                    print(f"Error checking frame visibility: {e}")

                        # After verify polling loop finishes:
                        if not verify_outcome_determined:
                            # If we get here without a decisive outcome, do one final token check
                            token_val = check_for_token(sb)
                            if token_val:
                                print(f"Final check: SUCCESS! Token found after timeout: {token_val[:20]}...")
                                recaptcha_token = token_val
                                captcha_solved_successfully = True
                            else:
                                print("Verify Polling WARNING: Timed out waiting for result after clicking Verify.")
                                # Don't set captcha_solved_successfully to False if this is not the final attempt
                                if audio_attempt == max_audio_attempts - 1:
                                    captcha_solved_successfully = False
                                continue  # Try next audio if we still have attempts left
                        
                        # If we got a token or a definitive failure, check which type
                        if captcha_solved_successfully:
                            # Success! Break out of retry loop
                            break
                        elif got_blocked:
                            # Blocked - no point retrying
                            break
                        elif captcha_failed_need_more:
                            # "Multiple correct solutions required" error
                            print("Detected 'Multiple correct solutions required' error, trying a new audio challenge...")
                            captcha_failed_need_more = False  # Reset the flag for next attempt
                            
                            # Clear the previous input field
                            try:
                                # Ensure we're in the challenge frame
                                sb.switch_to_default_content()
                                sb.switch_to_frame(recaptcha_challenge_frame_selector)
                                
                                # Clear the input field
                                if sb.is_element_present(audio_challenge_input_selector):
                                    sb.clear(audio_challenge_input_selector)
                                    print("Cleared previous audio challenge input field.")
                            except Exception as clear_err:
                                print(f"Warning: Could not clear input field: {clear_err}")
                            
                            # Continue to next iteration (get new audio)
                            continue
                            
                    except Exception as submit_err:
                        print(f"ERROR submitting transcription or clicking verify: {submit_err}")
                        # Only mark as failed if this is our last attempt
                        if audio_attempt == max_audio_attempts - 1:
                            captcha_solved_successfully = False
                            error_message = f"Submission failed: {submit_err}"
                            sb.save_screenshot("captcha_submit_error.png")
                
                # End of audio challenge retry loop
                if not transcription_submitted:
                    print(f"Failed to solve audio challenge after {max_audio_attempts} attempts.")
                    captcha_solved_successfully = False
            elif not got_blocked and audio_challenge_loaded and not audio_url:
                 print("\n--- Submission Skipped (Audio challenge loaded but no URL) ---")
                 captcha_solved_successfully = False # Can't proceed without URL
            elif not got_blocked:
                 print("\n--- Submission Skipped (Audio challenge did not load) ---")
                 # captcha_solved_successfully should already be False

    except (NoSuchElementException, TimeoutException, NoSuchFrameException) as e: # Added NoSuchFrameException
        print(f"ERROR during WebDriver interaction (Timeout/Element Not Found/No Frame): {e}")
        unexpected_error_occurred = True
        error_message = str(e)
        try:
            if hasattr(sb, 'driver') and sb.driver:
                 current_frame = sb.driver.execute_script("return window.frameElement ? window.frameElement.outerHTML : 'default_content';")
                 print(f"Error occurred possibly in frame: {current_frame[:150]}...")
            else:
                print("Driver not available to determine frame context.")
        except Exception as frame_err:
            print(f"Could not determine current frame context: {frame_err}")
        sb.save_screenshot("captcha_reconnect_error.png")
        sb.save_page_source("captcha_reconnect_error.html")

    except Exception as e:
        print(f"UNEXPECTED ERROR during WebDriver interaction: {e}")
        unexpected_error_occurred = True
        error_message = str(e)
        try:
            if hasattr(sb, 'driver') and sb.driver:
                current_frame = sb.driver.execute_script("return window.frameElement ? window.frameElement.outerHTML : 'default_content';")
                print(f"Error occurred possibly in frame: {current_frame[:150]}...")
            else:
                print("Driver not available to determine frame context.")
        except Exception as frame_err:
            print(f"Could not determine current frame context: {frame_err}")
        sb.save_screenshot("captcha_unexpected_error.png")
        sb.save_page_source("captcha_unexpected_error.html")

    finally:
        print("\n--- Finalizing reCAPTCHA Interaction ---")
        print("--------------------------------------------------")
    
    # Final outcome assessment
    if unexpected_error_occurred:
        print(f"RESULT: FAILED due to unexpected error during WebDriver phase: {error_message}")
    elif got_blocked:
        print("RESULT: Process stopped - Account/IP appears to be BLOCKED by reCAPTCHA ('Try again later').")
    elif captcha_failed_need_more:
        print(f"RESULT: FAILED - reCAPTCHA required multiple solutions and all attempts were exhausted.")
    elif captcha_solved_successfully and recaptcha_token:
        print(f"RESULT: SUCCESS! CAPTCHA Solved. Token: {recaptcha_token[:20]}...")
    elif transcription_submitted and not captcha_solved_successfully:
        print("RESULT: FAILED - Transcription submitted, but token/error polling timed out or failed")
        
        # If transcription was submitted but no token was found, do one final check
        # as a last resort - sometimes the token appears after our polling window
        sb.reconnect()
        print("Doing one final token check after reconnecting...")
        sb.switch_to_default_content()
        final_token = check_for_token(sb)
        if final_token:
            print(f"SUCCESS on final check! CAPTCHA was actually solved. Token: {final_token[:20]}...")
            recaptcha_token = final_token
            captcha_solved_successfully = True
        else:
            print("Final token check also failed.")
            # Also try the visible check as a last resort
            try:
                if sb.is_element_visible(recaptcha_token_selector):
                    final_token_visible = sb.get_value(recaptcha_token_selector)
                    if final_token_visible and len(final_token_visible) > 50:
                        print(f"SUCCESS via visible check! CAPTCHA solved. Token: {final_token_visible[:20]}...")
                        recaptcha_token = final_token_visible
                        captcha_solved_successfully = True
                    else:
                        print(f"Visible element found but value invalid: {final_token_visible}")
                else:
                    print("Token element not visible.")
            except Exception as e:
                print(f"Error during final visual token check: {e}")
    elif transcription and not transcription_submitted:
        print("RESULT: FAILED - Transcription obtained but submission failed")
    elif audio_challenge_loaded and not transcription:
        print("RESULT: FAILED - Audio loaded but Transcription failed")
    elif audio_challenge_loaded and not audio_url:
        print("RESULT: FAILED - Audio loaded but URL extraction failed")
    else:
        print("RESULT: FAILED - Could not complete the CAPTCHA interaction process (Polling timed out or check failed).")

    # Additional detailed reporting
    if audio_url: 
        print(f"--> Audio URL: {audio_url}")
    if audio_file_path: 
        print(f"--> Audio File: {audio_file_path}")
    if transcription: 
        print(f"--> Transcription: '{transcription}'")
    
    # Return token and success status
    return recaptcha_token, captcha_solved_successfully

print("Starting SeleniumBase with UC Mode...")
with SB(uc=True, test=True, locale="en", ad_block=True, pls="none") as sb:

    print(f"Navigating to: {url}")
    sb.activate_cdp_mode(url)
    print(f"Currently connected: {sb.is_connected()}") # False

    print("Waiting for page load and initial checks...")
    sb.sleep(3)

    print(f"Typing phone number using CDP: {phone_number_to_enter}")
    try:
        sb.cdp.wait_for_element_visible(phone_input_selector, timeout=15)
        sb.cdp.press_keys(phone_input_selector, phone_number_to_enter)
        print("Phone number typed.")
        sb.sleep(1)
    except Exception as e:
        print(f"Error interacting with {phone_input_selector} input using CDP: {e}")
        sb.save_screenshot("error_phone_input.png")
        sb.save_page_source("error_phone_input.html")
        raise

    print("Clicking the submit button using CDP...")
    try:
        sb.cdp.wait_for_element_visible(submit_button_selector, timeout=15)
        sb.cdp.click(submit_button_selector)
        print("Submit button clicked.")
        sb.sleep(5)
    except Exception as e:
        print(f"Error clicking submit button using CDP: {e}")
        sb.save_screenshot("error_submit_click.png")
        sb.save_page_source("error_submit_click.html")
        raise

    # --- Reconnect WebDriver for iframe DOM interaction ---
    print("Reconnecting WebDriver...")
    sb.reconnect() # **** RECONNECT ****
    print(f"Currently connected: {sb.is_connected()}") # True
    
    # --- Solve the CAPTCHA using the refactored function ---
    recaptcha_token, captcha_solved_successfully = solve_captcha(sb)
        
    # --- Phase 4: Click Submit Button Again (if CAPTCHA successful) ---
    if captcha_solved_successfully and recaptcha_token:
        print("\n--- CAPTCHA Solved - Clicking Submit Button Again ---")
        
        # Define the specific selector for the "Check registration" button after CAPTCHA
        check_registration_selector = "body > div:nth-child(5) > div > div > div.container.ng-scope > div > div:nth-child(2) > div:nth-child(1) > div:nth-child(3) > div:nth-child(2) > form > div > div.submit-container > button:nth-child(2)"
        
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
         print("\n--- CAPTCHA Not Solved - Skipping final submit button click ---")

    print("\nProcessing finished. Observing final state...")
    # We are back in disconnected CDP mode here
    sb.sleep(150) # Keep browser open

    print("Script finished.")
