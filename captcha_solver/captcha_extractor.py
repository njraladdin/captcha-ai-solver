import os
import time
import json
from seleniumbase import SB


class CaptchaExtractor:
    """
    A simple class for extracting reCAPTCHA parameters from websites.
    
    This class extracts parameters like site key, data-s value, and determines if
    the reCAPTCHA is invisible, using JavaScript for reliable extraction.
    """
    
    def __init__(self, download_dir="tmp"):
        """Initialize the CaptchaExtractor."""
        self.download_dir = download_dir
        
        # Ensure the download directory exists
        os.makedirs(self.download_dir, exist_ok=True)
    
    def initialize_browser(self, uc=True, headless=False, **kwargs):
        """Initialize a SeleniumBase browser instance."""
        print("Initializing SeleniumBase browser...")
        return SB(uc=uc, headless=headless, **kwargs)
    
    def extract_recaptcha_params(self, target, wait_time=10, close_browser=True):
        """
        Extract reCAPTCHA parameters from a webpage.
        
        Args:
            target: Either a URL string or an active SeleniumBase instance.
            wait_time: Time to wait for reCAPTCHA elements. Defaults to 10 seconds.
            close_browser: Whether to close the browser after extraction if
                          a new browser was opened. Defaults to True.
        
        Returns:
            dict: Dictionary containing extracted reCAPTCHA parameters
        """
        # Initialize variables
        sb = None
        should_close_browser = False
        params = {
            "website_url": None,
            "website_key": None,
            "is_invisible": False,
            "data_s_value": None,
            "is_enterprise": False,
            "script_src": None,
            "captcha_count": 0
        }
        
        try:
            # Determine if target is a URL or SeleniumBase instance
            if isinstance(target, str):
                # It's a URL, initialize a new browser
                sb = self.initialize_browser(uc=True)
                should_close_browser = close_browser
                
                # Navigate to the URL
                with sb as browser:
                    params["website_url"] = target
                    print(f"Navigating to URL: {target}")
                    browser.open(target)
                    sb = browser  # Save browser instance outside the context manager
                    
                    # Wait for the page to load
                    sb.sleep(wait_time/2)
                    
                    # Extract parameters
                    self._extract_with_javascript(sb, params)
            else:
                # It's a SeleniumBase instance
                sb = target
                params["website_url"] = sb.get_current_url()
                print(f"Using existing browser at URL: {params['website_url']}")
                
                # Extract parameters
                self._extract_with_javascript(sb, params)
            
            return params
            
        except Exception as e:
            print(f"Error during captcha parameter extraction: {e}")
            # Take a screenshot for debugging
            if sb:
                try:
                    screenshot_path = os.path.join(self.download_dir, "captcha_extract_error.png")
                    sb.save_screenshot(screenshot_path)
                    print(f"Error screenshot saved to: {screenshot_path}")
                except:
                    pass
            
            # Return any parameters we managed to collect
            return params
        
        finally:
            # Close the browser if we opened it and were asked to close it
            if should_close_browser and sb and hasattr(sb, 'driver') and sb.driver:
                try:
                    print("Closing browser...")
                    sb.driver.quit()
                except:
                    pass
    
    def _extract_with_javascript(self, sb, params):
        """Extract all reCAPTCHA parameters using JavaScript."""
        print("Extracting reCAPTCHA parameters using JavaScript...")
        
        # First extract the site key - most important parameter
        site_key = sb.execute_script("""
            // 1. Check direct elements with data-sitekey attribute
            const elements = document.querySelectorAll('[data-sitekey]');
            if (elements.length > 0) {
                return elements[0].getAttribute('data-sitekey');
            }

            // 2. Check g-recaptcha divs
            const recaptchaDiv = document.querySelector('.g-recaptcha');
            if (recaptchaDiv && recaptchaDiv.getAttribute('data-sitekey')) {
                return recaptchaDiv.getAttribute('data-sitekey');
            }
            
            // 3. Check iframe src for k= parameter
            const iframes = document.querySelectorAll('iframe');
            for (const iframe of iframes) {
                const src = iframe.getAttribute('src');
                if (src && src.includes('recaptcha')) {
                    const match = src.match(/[?&]k=([^&]+)/);
                    if (match && match[1]) {
                        return match[1];
                    }
                }
            }
            
            // 4. Look in page source as a last resort
            const html = document.documentElement.outerHTML;
            const dataMatch = html.match(/data-sitekey=['"]([^'"]+)['"]/);
            if (dataMatch && dataMatch[1]) {
                return dataMatch[1];
            }
            
            const kMatch = html.match(/[?&]k=([^&'"]+)/);
            if (kMatch && kMatch[1]) {
                return kMatch[1];
            }
            
            return null;
        """)
        
        if site_key:
            params["website_key"] = site_key
            print(f"Successfully extracted site key: {site_key}")
            
            # Now extract additional parameters
            try:
                # Get all captcha information in one JavaScript call
                captcha_data = sb.execute_script("""
                    // Find the element with this site key
                    const el = document.querySelector(`[data-sitekey="${arguments[0]}"]`);
                    if (!el) return { count: 0 };
                    
                    // Check if it's invisible
                    const isInvisible = el.getAttribute('data-size') === 'invisible';
                    
                    // Get data-s value if present
                    const dataS = el.getAttribute('data-s');
                    
                    // Get script source
                    let scriptSrc = null;
                    const scripts = document.querySelectorAll('script[src*="recaptcha"]');
                    if (scripts.length > 0) {
                        scriptSrc = scripts[0].getAttribute('src');
                    }
                    
                    // Count all captchas
                    const count = document.querySelectorAll('[data-sitekey]').length;
                    
                    // Check if enterprise
                    const isEnterprise = (
                        scriptSrc && scriptSrc.includes('enterprise') || 
                        arguments[0].length > 50
                    );
                    
                    return {
                        isInvisible: isInvisible,
                        dataS: dataS,
                        scriptSrc: scriptSrc,
                        count: count,
                        isEnterprise: isEnterprise
                    };
                """, site_key)
                
                if captcha_data:
                    params["is_invisible"] = captcha_data.get("isInvisible", False)
                    params["data_s_value"] = captcha_data.get("dataS")
                    params["script_src"] = captcha_data.get("scriptSrc")
                    params["captcha_count"] = captcha_data.get("count", 1)
                    params["is_enterprise"] = captcha_data.get("isEnterprise", False)
                    
            except Exception as e:
                print(f"Error extracting additional parameters: {e}")
    
    def extract_and_print(self, target, wait_time=10, close_browser=True):
        """
        Extract reCAPTCHA parameters and print them in a nicely formatted way.
        
        Args:
            target: Either a URL string or an active SeleniumBase instance
            wait_time: Time to wait for elements. Defaults to 10 seconds.
            close_browser: Whether to close browser after extraction. Defaults to True.
        
        Returns:
            dict: Dictionary of extracted parameters
        """
        print("\n=== Starting reCAPTCHA Parameter Extraction ===")
        
        # Extract parameters
        params = self.extract_recaptcha_params(target, wait_time, close_browser)
        
        # Print results
        print("\n=== reCAPTCHA Parameters Extracted ===")
        print(f"Website URL: {params['website_url']}")
        print(f"Site Key: {params['website_key']}")
        print(f"Is Invisible reCAPTCHA: {params['is_invisible']}")
        print(f"Is Enterprise reCAPTCHA: {params['is_enterprise']}")
        print(f"Data-S Value: {params['data_s_value']}")
        print(f"reCAPTCHA Script Source: {params['script_src']}")
        print(f"Total Captchas Found: {params['captcha_count']}")
        
        # Save to JSON file
        timestamp = int(time.time())
        json_file = os.path.join(self.download_dir, f"captcha_params_{timestamp}.json")
        
        try:
            with open(json_file, 'w') as f:
                json.dump(params, f, indent=2)
            print(f"\nParameters saved to: {json_file}")
        except Exception as e:
            print(f"Error saving parameters to file: {e}")
        
        return params


# Simple example usage
if __name__ == "__main__":
    import sys
    
    # Get URL from command line or use default
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.google.com/recaptcha/api2/demo"
    
    # Create extractor
    extractor = CaptchaExtractor(download_dir="tmp")
    
    # Extract and print
    try:
        params = extractor.extract_and_print(url)
        print("\nExtraction completed successfully.")
    except Exception as e:
        print(f"\nError during extraction: {e}")
        sys.exit(1)
    
    sys.exit(0) 