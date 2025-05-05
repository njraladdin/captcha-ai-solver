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
    
    def extract_recaptcha_params(self, target):
        """
        Extract reCAPTCHA parameters from a webpage.
        
        Args:
            target: Either a URL string or an active SeleniumBase instance.
        
        Returns:
            dict: Dictionary containing extracted reCAPTCHA parameters
        """
        # Initialize variables
        sb = None
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
                
                # Navigate to the URL
                with sb as browser:
                    params["website_url"] = target
                    print(f"Navigating to URL: {target}")
                    browser.open(target)
                    sb = browser  # Save browser instance outside the context manager
                    
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
    
    def _extract_with_javascript(self, sb, params):
        """Extract all reCAPTCHA parameters using JavaScript."""
        print("Extracting reCAPTCHA parameters using JavaScript...")
        
        # First check for iframe src with reCAPTCHA
        site_key = sb.execute_script("""
            // Wrap in function to allow return statements
            function extractSiteKey() {
                // Priority 1: Check iframes for reCAPTCHA src with k parameter
                const iframes = document.querySelectorAll('iframe');
                console.log('Found ' + iframes.length + ' iframes');
                
                for (const iframe of iframes) {
                    const src = iframe.getAttribute('src');
                    if (src && src.includes('recaptcha')) {
                        console.log('Found reCAPTCHA iframe with src: ' + src);
                        try {
                            const url = new URL(src);
                            const k = url.searchParams.get('k');
                            if (k) {
                                console.log('Found site key in iframe URL: ' + k);
                                return k;
                            }
                        } catch (e) {
                            console.log('Error parsing iframe URL: ' + e);
                            // Try regex as fallback
                            const match = src.match(/[?&]k=([^&]+)/);
                            if (match && match[1]) {
                                console.log('Found site key via regex: ' + match[1]);
                                return match[1];
                            }
                        }
                    }
                }
                
                // Priority 2: Check direct elements with data-sitekey attribute
                const elements = document.querySelectorAll('[data-sitekey]');
                if (elements.length > 0) {
                    return elements[0].getAttribute('data-sitekey');
                }

                // Priority 3: Check g-recaptcha divs
                const recaptchaDiv = document.querySelector('.g-recaptcha');
                if (recaptchaDiv && recaptchaDiv.getAttribute('data-sitekey')) {
                    return recaptchaDiv.getAttribute('data-sitekey');
                }
                
                // Priority 4: Check in JavaScript variables for reCAPTCHA key
                const scripts = document.querySelectorAll('script:not([src])');
                for (const script of scripts) {
                    const content = script.textContent;
                    if (content && (content.includes('recaptcha') || content.includes('captcha'))) {
                        // Look for common patterns like recaptchaPublicKey, sitekey, etc.
                        const keyMatch = content.match(/recaptcha\w*[Kk]ey['"]*\s*[:=]\s*['"]([\w-]+)['"]/);
                        if (keyMatch && keyMatch[1]) {
                            return keyMatch[1];
                        }
                        // Look for any 6Lxxx... pattern that looks like a reCAPTCHA key
                        const possibleKeyMatch = content.match(/['"]([a-zA-Z0-9\-_]{40,})['"]/)
                        if (possibleKeyMatch && possibleKeyMatch[1].startsWith('6L')) {
                            return possibleKeyMatch[1];
                        }
                    }
                }
                
                // Priority 5: Look in page source as a last resort
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
            }
            
            // Call the function to execute the extraction
            return extractSiteKey();
        """)
        
        if site_key:
            params["website_key"] = site_key
            print(f"Successfully extracted site key: {site_key}")
            
            # Now extract additional parameters
            try:
                # Get all captcha information in one JavaScript call
                captcha_data = sb.execute_script("""
                    function extractCaptchaData() {
                        // First check if it's in an iframe
                        const iframes = document.querySelectorAll('iframe[src*="recaptcha"]');
                        let el = null;
                        let scriptSrc = null;
                        let isEnterprise = false;
                        
                        // If we found the key in an iframe
                        if (iframes.length > 0) {
                            const src = iframes[0].getAttribute('src');
                            
                            // Check if it's enterprise
                            isEnterprise = src.includes('enterprise');
                            
                            // Use src as script source
                            scriptSrc = src;
                            
                            // Check for size parameter in iframe
                            const isInvisible = src.includes('size=invisible');
                            
                            return {
                                isInvisible: isInvisible,
                                dataS: null, // Not available from iframe usually
                                scriptSrc: scriptSrc,
                                count: iframes.length,
                                isEnterprise: isEnterprise
                            };
                        }
                        
                        // If not found in iframe, check elements
                        el = document.querySelector(`[data-sitekey="${arguments[0]}"]`);
                        if (!el) return { count: 0 };
                        
                        // Check if it's invisible
                        const isInvisible = el.getAttribute('data-size') === 'invisible';
                        
                        // Get data-s value if present
                        const dataS = el.getAttribute('data-s');
                        
                        // Get script source
                        const scripts = document.querySelectorAll('script[src*="recaptcha"]');
                        if (scripts.length > 0) {
                            scriptSrc = scripts[0].getAttribute('src');
                        }
                        
                        // Count all captchas
                        const count = document.querySelectorAll('[data-sitekey]').length;
                        
                        // Check if enterprise
                        isEnterprise = (
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
                    }
                    
                    return extractCaptchaData();
                """, site_key)
                
                if captcha_data:
                    params["is_invisible"] = captcha_data.get("isInvisible", False)
                    params["data_s_value"] = captcha_data.get("dataS")
                    params["script_src"] = captcha_data.get("scriptSrc")
                    params["captcha_count"] = captcha_data.get("count", 1)
                    params["is_enterprise"] = captcha_data.get("isEnterprise", False)
                    
            except Exception as e:
                print(f"Error extracting additional parameters: {e}")
        else:
            print("Failed to extract site key using JavaScript methods")
            
            # Try alternative method to find recaptchaPublicKey in scripts
            try:
                alt_site_key = sb.execute_script("""
                    function findRecaptchaKeyInScripts() {
                        // Look for a common pattern in the website you mentioned
                        const scripts = document.querySelectorAll('script:not([src])');
                        for (const script of scripts) {
                            const content = script.textContent || '';
                            
                            // Look specifically for recaptchaPublicKey as in your example
                            if (content.includes('recaptchaPublicKey')) {
                                const match = content.match(/recaptchaPublicKey['"]*\s*[:=]\s*['"]([\w-]+)['"]/);
                                if (match && match[1]) {
                                    console.log('Found recaptchaPublicKey in script:', match[1]);
                                    return match[1];
                                }
                            }
                            
                            // Also look for clientConfiguration object
                            if (content.includes('clientConfiguration') && content.includes('recaptcha')) {
                                const match = content.match(/recaptcha\w*[Kk]ey['"]*\s*[:=]\s*['"]([\w-]+)['"]/);
                                if (match && match[1]) {
                                    console.log('Found key in clientConfiguration:', match[1]);
                                    return match[1];
                                }
                            }
                        }
                        return null;
                    }
                    
                    return findRecaptchaKeyInScripts();
                """)
                
                if alt_site_key:
                    params["website_key"] = alt_site_key
                    print(f"Found site key in script: {alt_site_key}")
            except Exception as e:
                print(f"Error during alternative site key extraction: {e}")
    
    def extract_captcha_params(self, target):
        """
        Extract reCAPTCHA parameters and print them in a nicely formatted way.
        
        Args:
            target: Either a URL string or an active SeleniumBase instance
        
        Returns:
            dict: Dictionary of extracted parameters
        """
        print("\n=== Starting reCAPTCHA Parameter Extraction ===")
        
        # Extract parameters
        params = self.extract_recaptcha_params(target)
        
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
        params = extractor.extract_captcha_params(url)
        print("\nExtraction completed successfully.")
    except Exception as e:
        print(f"\nError during extraction: {e}")
        sys.exit(1)
    
    sys.exit(0) 