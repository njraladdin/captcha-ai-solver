from seleniumbase import SB
import time
from selenium.common.exceptions import NoSuchElementException, TimeoutException, NoSuchFrameException
import os
import requests
import random

class CaptchaSolver:
    """
    A class for solving reCAPTCHA challenges using audio transcription.
    
    This class encapsulates all the functionality needed to solve reCAPTCHAs, including:
    1. Browser initialization and lifecycle management
    2. Finding and clicking the initial checkbox
    3. Checking if token is immediately available (no challenge)
    4. If needed, switching to the audio challenge
    5. Downloading, transcribing, and submitting the audio challenge
    6. Handling retry logic for multiple audio challenges if needed
    7. Detecting and handling various error cases (blocking, multiple solutions required)
    8. Executing pre and post-CAPTCHA callbacks
    """
    
    # Default selectors for reCAPTCHA elements
    RECAPTCHA_ANCHOR_FRAME_SELECTOR = 'iframe[src*="api2/anchor"]'  # Initial checkbox iframe
    RECAPTCHA_CHECKBOX_SELECTOR = '.recaptcha-checkbox-border'     # Checkbox inside anchor frame
    RECAPTCHA_CHALLENGE_FRAME_SELECTOR = 'iframe[src*="api2/bframe"]' # Challenge iframe (image/audio)
    AUDIO_BUTTON_SELECTOR = "#recaptcha-audio-button"                # Audio button inside challenge frame
    
    # Selectors for checking state AFTER clicking audio button (inside challenge frame)
    AUDIO_CHALLENGE_INPUT_SELECTOR = "#audio-response"  # Input field for audio answer
    AUDIO_CHALLENGE_SOURCE_SELECTOR = '#audio-source[src]'  # Check if audio source exists and has src
    BLOCKED_MESSAGE_SELECTOR = ".rc-doscaptcha-header-text"  # Element containing potential block message
    BLOCKED_MESSAGE_TEXT = "Try again later"                 # Common blocking text
    RECAPTCHA_VERIFY_BUTTON_SELECTOR = "#recaptcha-verify-button"  # Verify button
    
    # Selectors for post-verification polling
    RECAPTCHA_TOKEN_SELECTOR = 'textarea[name="g-recaptcha-response"]'  # In main content 
    RECAPTCHA_ERROR_MESSAGE_SELECTOR = ".rc-audiochallenge-error-message"  # In challenge frame
    RECAPTCHA_ERROR_MESSAGE_TEXT = "Multiple correct solutions required"  # Common "need more" text
    
    def __init__(self, wit_api_key=None, download_dir="tmp", before_captcha_callback=None, after_captcha_callback=None):
        """
        Initialize the CaptchaSolver.
        
        Args:
            wit_api_key (str, optional): API key for Wit.ai speech recognition service
            download_dir (str, optional): Directory where audio files will be saved. Defaults to 'tmp' directory.
            before_captcha_callback (callable, optional): Function to call before solving captcha. Will receive SeleniumBase instance.
            after_captcha_callback (callable, optional): Function to call after solving captcha. Will receive SeleniumBase instance,
                                                       success status, and token.
        """
        self.wit_api_key = wit_api_key
        self.download_dir = download_dir
        self.before_captcha_callback = before_captcha_callback
        self.after_captcha_callback = after_captcha_callback
        self.browser = None
        
        # Ensure the download directory exists
        os.makedirs(self.download_dir, exist_ok=True)
    
    def initialize_browser(self, uc=True, test=True, locale="en", ad_block=True, pls="none", **kwargs):
        """
        Initialize a SeleniumBase browser instance.
        
        Args:
            uc (bool, optional): Use undetected-chromedriver mode. Defaults to True.
            test (bool, optional): Test mode flag. Defaults to True.
            locale (str, optional): Browser locale. Defaults to "en".
            ad_block (bool, optional): Enable ad blocking. Defaults to True.
            pls (str, optional): Pass level security. Defaults to "none".
            **kwargs: Additional keyword arguments to pass to SeleniumBase constructor.
            
        Returns:
            SB: The initialized SeleniumBase instance.
        """        
        print("Initializing SeleniumBase browser...")
        # Just return the SB class with parameters - will be used with 'with' statement
        return SB(uc=uc, test=test, locale=locale, ad_block=ad_block, pls=pls, **kwargs)

    def _check_for_token(self, sb):
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
    
    def _check_for_need_more_solutions(self, sb, frame_selector):
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
    
    def _check_for_blocking(self, sb, frame_selector):
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
    
    def download_audio(self, audio_url, filename="recaptcha_audio.mp3"):
        """
        Downloads audio from a URL and saves it.
        
        Args:
            audio_url (str): URL of the audio file to download
            filename (str, optional): Filename to save the audio as. Defaults to "recaptcha_audio.mp3".
            
        Returns:
            str or None: Path to the downloaded file if successful, None otherwise
        """
        if not audio_url:
            print("ERROR: No audio URL provided for download.")
            return None
        
        filepath = os.path.join(self.download_dir, filename)
        print(f"Attempting to download audio from: {audio_url[:60]}...")
        print(f"Saving to: {filepath}")
        
        try:
            # Ensure the save directory exists
            os.makedirs(self.download_dir, exist_ok=True)

            # Make the request - no session/cookies needed usually
            response = requests.get(audio_url, stream=True, timeout=30)  # Add timeout
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
    
    def transcribe_audio_with_wit(self, audio_filepath, max_retries=3):
        """
        Sends audio file to Wit.ai for transcription with retries.
        
        Args:
            audio_filepath (str): Path to the audio file to transcribe
            max_retries (int, optional): Maximum number of transcription attempts. Defaults to 3.
            
        Returns:
            str or None: Transcribed text if successful, None otherwise
        """
        if not self.wit_api_key:
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
                    'Authorization': f'Bearer {self.wit_api_key}',
                    'Content-Type': 'audio/mpeg',  # reCAPTCHA usually provides mp3
                }

                # Send POST request to Wit.ai Speech API
                wit_url = 'https://api.wit.ai/speech?v=20230215'  # Use a recent API version
                response = requests.post(wit_url, headers=headers, data=audio_data, timeout=45)  # Increased timeout
                response.raise_for_status()  # Check for HTTP errors

                # Process the response - Wit might send multiple JSON objects
                response_text = response.text.strip()
                print(f"Wit.ai raw response: {response_text[:500]}...")  # Log beginning of response
                
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
                     print(f"Wit.ai response text: {response.text[:500]}...")  # Log beginning of response
                
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

    def solve(self, sb, url=None):
        """
        Solves the reCAPTCHA challenge using audio transcription.
        
        This method handles the complete reCAPTCHA solving process, including:
        1. Finding and clicking the initial checkbox
        2. Checking if token is immediately available (no challenge)
        3. If needed, switching to the audio challenge
        4. Downloading, transcribing, and submitting the audio challenge
        5. Handling retry logic for multiple audio challenges if needed
        6. Detecting and handling various error cases (blocking, multiple solutions required)
        
        Args:
            sb: SeleniumBase instance (should be an active browser session, not a context manager)
            url (str, optional): If provided, will navigate to this URL in CDP mode first
            
        Returns:
            tuple: (token, success_status)
                - token: The reCAPTCHA token string if successful, None otherwise
                - success_status: Boolean indicating whether the CAPTCHA was successfully solved
        """
        print("\n--- Starting reCAPTCHA Interaction ---")
        
        # Handle connection state - we need WebDriver mode for iframe interaction
        # First, navigate to URL in CDP mode if requested
        if url:
            print(f"Navigating to URL using CDP mode: {url}")
            sb.activate_cdp_mode(url)
            print(f"Current connection state: {'Connected' if sb.is_connected() else 'CDP Mode (disconnected)'}")
        
        # Then ensure WebDriver is connected for iframe interactions
        # We need to reconnect if we're in CDP mode
        if not sb.is_connected():
            print("WebDriver not connected. Reconnecting for iframe interaction...")
            sb.reconnect()
            print(f"WebDriver connected: {sb.is_connected()}")
            
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
            print(f"Waiting for reCAPTCHA anchor iframe: '{self.RECAPTCHA_ANCHOR_FRAME_SELECTOR}'")
            sb.wait_for_element_visible(self.RECAPTCHA_ANCHOR_FRAME_SELECTOR, timeout=20)
            print("Anchor iframe is visible.")
            print("Switching to reCAPTCHA anchor iframe...")
            sb.switch_to_frame(self.RECAPTCHA_ANCHOR_FRAME_SELECTOR)

            print(f"Waiting for checkbox inside anchor iframe: '{self.RECAPTCHA_CHECKBOX_SELECTOR}'")
            sb.wait_for_element_visible(self.RECAPTCHA_CHECKBOX_SELECTOR, timeout=15)
            print("Clicking checkbox inside anchor iframe...")
            try:
                sb.click(self.RECAPTCHA_CHECKBOX_SELECTOR)
            except Exception:
                print("Standard click failed, trying JS click on checkbox...")
                sb.js_click(self.RECAPTCHA_CHECKBOX_SELECTOR)
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
                token_val = self._check_for_token(sb)
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
                
                print(f"Waiting for reCAPTCHA challenge iframe: '{self.RECAPTCHA_CHALLENGE_FRAME_SELECTOR}'")
                sb.wait_for_element_visible(self.RECAPTCHA_CHALLENGE_FRAME_SELECTOR, timeout=25)
                print("Challenge iframe is visible.")

                print("Switching to reCAPTCHA challenge iframe...")
                sb.switch_to_frame(self.RECAPTCHA_CHALLENGE_FRAME_SELECTOR)
                challenge_frame_handle = sb.driver.current_window_handle  # Store for potential reuse
                challenge_frame_name_or_id = sb.driver.execute_script("return window.frameElement ? (window.frameElement.name || window.frameElement.id) : null")
                print(f"Identified challenge frame handle/id: {challenge_frame_name_or_id}")  # Helpful for debug

                print(f"Waiting for audio button inside challenge iframe: '{self.AUDIO_BUTTON_SELECTOR}'")
                sb.wait_for_element_visible(self.AUDIO_BUTTON_SELECTOR, timeout=18)
                print("Clicking audio button inside challenge iframe...")
                try:
                     sb.click(self.AUDIO_BUTTON_SELECTOR)
                except Exception:
                    print("Standard click failed, trying JS click on audio button...")
                    sb.js_click(self.AUDIO_BUTTON_SELECTOR)
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
                        if sb.is_element_visible(self.RECAPTCHA_CHALLENGE_FRAME_SELECTOR):
                            print("Polling: Challenge iframe is visible, switching to it...")
                            sb.switch_to_frame(self.RECAPTCHA_CHALLENGE_FRAME_SELECTOR)
                            print("Polling: Successfully switched to challenge frame")
                        else:
                            print("Polling WARNING: Challenge iframe not visible, might be changing...")
                            # Wait a moment for frame to potentially stabilize
                            sb.sleep(0.5)
                            if sb.is_element_visible(self.RECAPTCHA_CHALLENGE_FRAME_SELECTOR):
                                print("Polling: Challenge iframe reappeared, switching to it...")
                                sb.switch_to_frame(self.RECAPTCHA_CHALLENGE_FRAME_SELECTOR)
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
                    if sb.is_text_visible(self.BLOCKED_MESSAGE_TEXT, selector=self.BLOCKED_MESSAGE_SELECTOR):
                        print(f"Polling check: Blocking message FOUND & VISIBLE: '{self.BLOCKED_MESSAGE_TEXT}'")
                        got_blocked = True
                        captcha_solved_successfully = False
                        final_outcome_determined = True
                        break

                    # Check for audio challenge input and extract URL
                    if sb.is_element_visible(self.AUDIO_CHALLENGE_INPUT_SELECTOR):
                         print("Polling check: Audio challenge input field IS visible.")
                         # *** EXTRACT AUDIO URL HERE ***
                         try:
                             # Make sure the source element exists before getting attribute
                             if sb.is_element_present(self.AUDIO_CHALLENGE_SOURCE_SELECTOR):
                                 audio_url = sb.get_attribute(self.AUDIO_CHALLENGE_SOURCE_SELECTOR, "src")
                                 if audio_url:
                                     print(f"Polling check: Extracted Audio URL: {audio_url[:60]}...")  # Print beginning
                                     audio_challenge_loaded = True
                                     captcha_solved_successfully = True  # Tentatively successful
                                 else:
                                     print("Polling check WARNING: Audio source 'src' attribute is empty.")
                                     # Treat as potentially loaded but log warning
                                     audio_challenge_loaded = True
                                     captcha_solved_successfully = True
                             else:
                                  print("Polling check WARNING: Audio source element not found, cannot get URL.")
                                  audio_challenge_loaded = True  # Input is visible, so mark as tentatively loaded
                                  captcha_solved_successfully = True

                         except Exception as get_attr_err:
                              print(f"Polling check ERROR: Failed to get audio src attribute: {get_attr_err}")
                              # Consider this a failure state for audio loading
                              audio_challenge_loaded = False
                              captcha_solved_successfully = False

                         final_outcome_determined = True
                         break  # Exit loop, audio challenge state determined

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
                                if sb.is_element_present(self.AUDIO_CHALLENGE_SOURCE_SELECTOR):
                                    audio_url = sb.get_attribute(self.AUDIO_CHALLENGE_SOURCE_SELECTOR, "src")
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
                        audio_file_path = self.download_audio(audio_url, filename=f"recaptcha_audio_{audio_attempt+1}.mp3")
                        if not audio_file_path:
                            print(f"Download failed on attempt {audio_attempt+1}/{max_audio_attempts}.")
                            continue  # Try next attempt
                            
                        print("\n--- Attempting Audio Transcription (WebDriver connected) ---")
                        transcription = self.transcribe_audio_with_wit(audio_file_path)
                        if not transcription:
                            print(f"Transcription failed on attempt {audio_attempt+1}/{max_audio_attempts}.")
                            continue  # Try next attempt
                            
                        print(f"\n--- Submitting Transcription: '{transcription}' ---")
                        try:
                            # Still inside challenge iframe here
                            print(f"Typing transcription into: {self.AUDIO_CHALLENGE_INPUT_SELECTOR}")
                            sb.type(self.AUDIO_CHALLENGE_INPUT_SELECTOR, transcription)
                            print("Transcription typed.")
                            sb.sleep(0.3 + random.uniform(0.1, 0.4))  # Add jitter

                            print(f"Clicking Verify button: {self.RECAPTCHA_VERIFY_BUTTON_SELECTOR}")
                            sb.wait_for_element_visible(self.RECAPTCHA_VERIFY_BUTTON_SELECTOR, timeout=10)
                            try:
                                sb.click(self.RECAPTCHA_VERIFY_BUTTON_SELECTOR)
                            except Exception:
                                sb.js_click(self.RECAPTCHA_VERIFY_BUTTON_SELECTOR)
                            transcription_submitted = True
                            print("Verify button clicked.")
                            
                            # 5. *** NEW: Poll for result AFTER clicking Verify ***
                            print("\n--- Polling for result after Verify ---")
                            verify_max_wait = 20  # Increased to 20 seconds for more time to detect token
                            verify_poll_interval = 0.1  # More frequent polling (100ms)
                            verify_start_time = time.time()
                            verify_outcome_determined = False
                            captcha_solved_successfully = False  # Reset success, confirm based on token
                            
                            # Main polling loop with all checks
                            while time.time() - verify_start_time < verify_max_wait:
                                # Always check for token first - most important outcome
                                token_val = self._check_for_token(sb)
                                if token_val:
                                    print(f"Verify Polling: SUCCESS! Token found: {token_val[:20]}...")
                                    recaptcha_token = token_val
                                    captcha_solved_successfully = True
                                    verify_outcome_determined = True
                                    break
                                
                                # If token not found, check for frame-based failure cases
                                
                                # Check for "need more solutions" error
                                if self._check_for_need_more_solutions(sb, self.RECAPTCHA_CHALLENGE_FRAME_SELECTOR):
                                    print(f"Verify Polling: FAILURE! Error found: '{self.RECAPTCHA_ERROR_MESSAGE_TEXT}'")
                                    captcha_failed_need_more = True
                                    captcha_solved_successfully = False
                                    verify_outcome_determined = True
                                    break
                                
                                # Check for blocking message
                                if self._check_for_blocking(sb, self.RECAPTCHA_CHALLENGE_FRAME_SELECTOR):
                                    print(f"Verify Polling: FAILURE! Blocked message found: '{self.BLOCKED_MESSAGE_TEXT}'")
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
                                        frame_visible = sb.is_element_visible(self.RECAPTCHA_CHALLENGE_FRAME_SELECTOR)
                                        print(f"Verify Polling: Challenge frame visible: {frame_visible}")
                                    except Exception as e:
                                        print(f"Error checking frame visibility: {e}")

                            # After verify polling loop finishes:
                            if not verify_outcome_determined:
                                # If we get here without a decisive outcome, do one final token check
                                token_val = self._check_for_token(sb)
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
                                    sb.switch_to_frame(self.RECAPTCHA_CHALLENGE_FRAME_SELECTOR)
                                    
                                    # Clear the input field
                                    if sb.is_element_present(self.AUDIO_CHALLENGE_INPUT_SELECTOR):
                                        sb.clear(self.AUDIO_CHALLENGE_INPUT_SELECTOR)
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
                                sb.save_screenshot(os.path.join(self.download_dir, "captcha_submit_error.png"))
                    
                    # End of audio challenge retry loop
                    if not transcription_submitted:
                        print(f"Failed to solve audio challenge after {max_audio_attempts} attempts.")
                        captcha_solved_successfully = False
                elif not got_blocked and audio_challenge_loaded and not audio_url:
                     print("\n--- Submission Skipped (Audio challenge loaded but no URL) ---")
                     captcha_solved_successfully = False  # Can't proceed without URL
                elif not got_blocked:
                     print("\n--- Submission Skipped (Audio challenge did not load) ---")
                     # captcha_solved_successfully should already be False

        except (NoSuchElementException, TimeoutException, NoSuchFrameException) as e:
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
            sb.save_screenshot(os.path.join(self.download_dir, "captcha_reconnect_error.png"))
            sb.save_page_source(os.path.join(self.download_dir, "captcha_reconnect_error.html"))

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
            sb.save_screenshot(os.path.join(self.download_dir, "captcha_unexpected_error.png"))
            sb.save_page_source(os.path.join(self.download_dir, "captcha_unexpected_error.html"))

        finally:
            print("\n--- Finalizing reCAPTCHA Interaction ---")
            
            # Always ensure we're back to default content before returning
            try:
                print("Switching back to default content before returning...")
                sb.switch_to_default_content()
                print("Successfully switched to default content.")
            except Exception as final_switch_err:
                print(f"WARNING: Error switching to default content in finalization: {final_switch_err}")
                # Try to reconnect if switching failed
                try:
                    if hasattr(sb, 'reconnect'):
                        print("Attempting to reconnect WebDriver in finalization...")
                        sb.reconnect()
                        print(f"WebDriver reconnected: {sb.is_connected()}")
                except Exception as reconnect_err:
                    print(f"WARNING: Failed to reconnect in finalization: {reconnect_err}")
                    
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
            final_token = self._check_for_token(sb)
            if final_token:
                print(f"SUCCESS on final check! CAPTCHA was actually solved. Token: {final_token[:20]}...")
                recaptcha_token = final_token
                captcha_solved_successfully = True
            else:
                print("Final token check also failed.")
                # Also try the visible check as a last resort
                try:
                    if sb.is_element_visible(self.RECAPTCHA_TOKEN_SELECTOR):
                        final_token_visible = sb.get_value(self.RECAPTCHA_TOKEN_SELECTOR)
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
        
        # Note: after_captcha_callback is now handled by run_workflow, not here
        return recaptcha_token, captcha_solved_successfully

    def run_workflow(self, url, observation_time=10):
        """
        Run the complete CAPTCHA solving workflow from browser initialization to closing.
        
        This method:
        1. Initializes a browser instance with UC mode enabled
        2. Navigates to the target URL (if no before_captcha_callback provided)
        3. Executes before-captcha actions (if callback provided)
        4. Solves the CAPTCHA
        5. Executes after-captcha actions (if callback provided)
        6. Optionally keeps the browser open for observation
        7. Closes the browser
        
        Args:
            url (str): The URL to navigate to
            observation_time (int, optional): Seconds to keep browser open after completion. Set to 0 to close immediately.
            
        Returns:
            tuple: (recaptcha_token, captcha_solved_successfully)
        """
        # Initialize browser with fixed SeleniumBase options
        print(f"\n--- Starting CaptchaSolver Workflow for URL: {url} ---")
        sb_instance = self.initialize_browser(uc=True, test=True, locale="en", ad_block=True, pls="none")
        
        recaptcha_token = None
        captcha_solved_successfully = False
        
        # Use the context manager properly with 'with' statement
        with sb_instance as sb:
            try:
                # Execute pre-captcha actions
                print("\n--- Executing Pre-CAPTCHA Actions ---")
                if self.before_captcha_callback:
                    print("Running user-provided before_captcha_callback...")
                    # Let the callback handle navigation and setup
                    self.before_captcha_callback(sb)
                else:
                    # Default action - navigate to the URL
                    print(f"No pre-captcha callback provided. Navigating to URL: {url}")
                    sb.activate_cdp_mode(url)
                    print(f"Currently connected: {sb.is_connected()}")  # False in CDP mode
                    sb.sleep(3)  # Wait for page to load
                
                # Solve the CAPTCHA
                print("\n--- Solving CAPTCHA ---")
                recaptcha_token, captcha_solved_successfully = self.solve(sb)
                
                # Execute after-captcha actions (if provided)
                if self.after_captcha_callback:
                    print("\n--- Executing After-CAPTCHA Actions ---")
                    self.after_captcha_callback(sb, captcha_solved_successfully, recaptcha_token)
                
                # Observe final state if requested
                if observation_time > 0:
                    print(f"\nProcessing finished. Observing final state for {observation_time} seconds...")
                    sb.sleep(observation_time)
                
            except Exception as e:
                print(f"ERROR in captcha solving workflow: {e}")
                try:
                    sb.save_screenshot(os.path.join(self.download_dir, "workflow_error.png"))
                    sb.save_page_source(os.path.join(self.download_dir, "workflow_error.html"))
                except Exception as screenshot_err:
                    print(f"Could not save error screenshot: {screenshot_err}")
        
        # When the with block exits, the browser automatically closes
        print("Browser closed. Workflow complete.")
        return recaptcha_token, captcha_solved_successfully 

if __name__ == "__main__":
    import os
    import sys
    
    # Get Wit.ai API key from environment variable or allow user to input it
    wit_api_key = os.environ.get("WIT_API_KEY")
    if not wit_api_key:
        print("Please set the WIT_API_KEY environment variable and try again.")
        sys.exit(1)
    
    # Create solver instance
    print("\n=== Creating CaptchaSolver instance ===")
    solver = CaptchaSolver(
        wit_api_key=wit_api_key,
        download_dir="tmp",
    )
    
    # Define a callback function to display the result after solving
    def after_captcha_callback(sb, success, token):
        if success and token:
            print("\n=== CAPTCHA SOLVED SUCCESSFULLY! ===")
            print(f"Token: {token[:30]}...{token[-30:] if token else ''}")
            
            # If we're on the demo page, we can also submit the form
            if "demo" in sb.get_current_url():
                try:
                    print("\nAttempting to submit the demo form...")
                    submit_button = sb.find_element("recaptcha-demo-submit")
                    if submit_button:
                        sb.click("recaptcha-demo-submit")
                        print("Demo form submitted successfully!")
                        # Wait to see the result
                        sb.sleep(3)
                except Exception as e:
                    print(f"Error submitting the demo form: {e}")
        else:
            print("\n=== CAPTCHA SOLVING FAILED ===")
    
    # Set the demo URL
    recaptcha_demo_url = "https://www.google.com/recaptcha/api2/demo"
    
    # Show instructions
    print(f"\n=== Testing CaptchaSolver with URL: {recaptcha_demo_url} ===")
    print("This will attempt to solve the reCAPTCHA on Google's demo page.")
    print("Browser will stay open for 10 seconds after completion to observe the result.")
    
    try:
        # Run the solver workflow
        solver.after_captcha_callback = after_captcha_callback
        token, success = solver.run_workflow(url=recaptcha_demo_url, observation_time=10)
        
        # Final result
        if success and token:
            print("\n=== TEST COMPLETED SUCCESSFULLY ===")
            print(f"reCAPTCHA token obtained: {token[:20]}...")
        else:
            print("\n=== TEST COMPLETED WITH ERRORS ===")
            print("Failed to solve the reCAPTCHA. See logs above for details.")
    
    except KeyboardInterrupt:
        print("\nTest interrupted by user. Exiting...")
    except Exception as e:
        print(f"\nUnexpected error during test: {e}") 