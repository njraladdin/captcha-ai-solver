import os
import time
from .captcha_replicator import CaptchaReplicator
from .challenge_solver import ChallengeSolver


class CaptchaSolver:
    """
    Main entry point for solving reCAPTCHAs.
    
    This class handles the core captcha solving process. It focuses only on solving
    and does not handle extraction or application of tokens, maintaining clear separation
    of concerns and modularity.
    
    Usage example:
        # With params already extracted
        solver = CaptchaSolver(wit_api_key="YOUR_API_KEY")
        token, success = solver.solve(params)
        
        # Or with a full workflow using helper classes:
        from captcha_solver import CaptchaExtractor, TokenApplier
        
        extractor = CaptchaExtractor()
        params = extractor.extract_captcha_params(browser)
        
        solver = CaptchaSolver(wit_api_key="YOUR_API_KEY")
        token, success = solver.solve(params)
        
        applier = TokenApplier()
        applier.apply_token(browser, token, params)
    """
    
    def __init__(self, wit_api_key=None, download_dir="tmp"):
        """
        Initialize the CaptchaSolver with required dependencies.
        
        Args:
            wit_api_key (str, optional): API key for Wit.ai speech recognition
            download_dir (str, optional): Directory for temporary files
        """
        self.wit_api_key = wit_api_key
        self.download_dir = download_dir
        
        # Create internal components
        self.replicator = CaptchaReplicator(download_dir=download_dir)
        self.challenge_solver = ChallengeSolver(wit_api_key=wit_api_key, download_dir=download_dir)
        
        # Ensure the download directory exists
        os.makedirs(self.download_dir, exist_ok=True)
    
    def solve(self, params):
        """
        Solve the captcha based on provided parameters.
        
        Args:
            params (dict): Dictionary containing captcha parameters:
                - website_key (str): reCAPTCHA site key
                - website_url (str): URL where captcha appears
                - is_invisible (bool, optional): Whether it's invisible
                - data_s_value (str, optional): data-s parameter if present
                - is_enterprise (bool, optional): If it's enterprise reCAPTCHA
            
        Returns:
            tuple: (token, success_status)
                - token (str): The solved reCAPTCHA token if successful, None otherwise
                - success_status (bool): Whether the solving was successful
        """
        print("\n=== Solving reCAPTCHA with Provided Parameters ===")
        print(f"Site key: {params.get('website_key')}")
        print(f"Website URL: {params.get('website_url')}")
        print(f"Is invisible: {params.get('is_invisible', False)}")
        print(f"Is enterprise: {params.get('is_enterprise', False)}")
        
        # Validate required parameters
        if not params.get("website_key") or not params.get("website_url"):
            print("ERROR: Missing required parameters (website_key and website_url)")
            return None, False
        
        replicated_sb = None
        try:
            # Replicate the captcha in a new browser
            print("\n--- Step 1: Replicating reCAPTCHA ---")
            html_path, replicated_sb, initial_token = self.replicator.replicate_captcha(
                website_key=params["website_key"],
                website_url=params["website_url"],
                is_invisible=params.get("is_invisible", False),
                data_s_value=params.get("data_s_value"),
                is_enterprise=params.get("is_enterprise", False),
                observation_time=5  # Just enough time to load the CAPTCHA
            )
            
            # If we couldn't create the replicated browser
            if not replicated_sb:
                print("ERROR: Failed to replicate CAPTCHA. Aborting.")
                return None, False
                
            # If we already have an initial token from replication, return it
            if initial_token and len(initial_token) > 20:  # Basic validation
                print(f"Initial token found during replication: {initial_token[:20]}...")
                return initial_token, True
                
            # Solve the challenge
            print("\n--- Step 2: Solving Replicated reCAPTCHA ---")
            token, success = self.challenge_solver.solve(replicated_sb)
            
            # If solving failed, check if token was captured by monitor thread
            if not success or not token:
                print("Direct solving unsuccessful, checking monitor thread...")
                token = self.replicator.get_last_token()
                if token:
                    success = True
                    print(f"Token found from monitor thread: {token[:20]}...")
                else:
                    print("No token found from monitor thread.")
            
            if success and token:
                print(f"\n✅ reCAPTCHA solved successfully!")
                print(f"Token (first 20 chars): {token[:20]}...")
            else:
                print("\n❌ Failed to solve reCAPTCHA")
                
            return token, success
            
        except Exception as e:
            print(f"ERROR during solving process: {e}")
            return None, False
            
        finally:
            # Clean up resources
            print("\n--- Cleaning Up Resources ---")
            try:
                if replicated_sb:
                    print("Closing replicated browser...")
                    replicated_sb.quit()
            except Exception as e:
                print(f"Error closing browser: {e}")
                
            try:
                print("Stopping HTTP server...")
                self.replicator.stop_http_server()
            except Exception as e:
                print(f"Error stopping server: {e}")

    def run_workflow(self, url, observation_time=2):
        """
        Run a complete workflow for solving a reCAPTCHA on a given URL.
        
        This is a convenience method that:
        1. Creates a browser and navigates to the URL
        2. Extracts captcha parameters using the separate CaptchaExtractor module
        3. Solves the captcha
        
        Args:
            url (str): The URL of the page containing the reCAPTCHA
            observation_time (int, optional): Time in seconds to keep the browser open after solving
            
        Returns:
            tuple: (token, success_status)
                - token (str): The solved reCAPTCHA token if successful, None otherwise
                - success_status (bool): Whether the solving was successful
        """
        from seleniumbase import SB
        from .captcha_extractor import CaptchaExtractor
        
        print(f"\n=== Starting Complete reCAPTCHA Workflow for URL: {url} ===")
        
        # Create extractor - kept separate to maintain modularity
        extractor = CaptchaExtractor(download_dir=self.download_dir)
        
        # Initialize browser
        browser = SB(uc=True, test=True, locale="en", ad_block=True, pls="none", headless=False)
        
        try:
            with browser as sb:
                # Navigate to URL
                print(f"\n--- Step 1: Navigating to URL ---")
                sb.open(url)
                
                # Wait for page to load
                print(f"Waiting for page to load...")
                sb.sleep(2)
                
                # Extract parameters - using the separate extractor module
                print(f"\n--- Step 2: Extracting reCAPTCHA Parameters ---")
                params = extractor.extract_captcha_params(sb)
                
                if not params.get("website_key"):
                    print("ERROR: Could not extract reCAPTCHA site key.")
                    return None, False
                
                # Solve the captcha - core functionality of this class
                print(f"\n--- Step 3: Solving reCAPTCHA ---")
                token, success = self.solve(params)
                
                # Keep browser open for observation if requested
                if observation_time > 0:
                    print(f"\nKeeping browser open for observation ({observation_time} seconds)...")
                    sb.sleep(observation_time)
                
                return token, success
                
        except Exception as e:
            print(f"ERROR during workflow: {e}")
            return None, False
        finally:
            # Make sure browser is closed
            try:
                browser.quit()
            except:
                pass 