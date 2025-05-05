import os
import time
import json


class TokenSubmitter:
    """
    A class for applying solved reCAPTCHA tokens to the original captcha.
    
    This class handles:
    1. Applying a solved token to a reCAPTCHA
    2. Triggering the reCAPTCHA callback function
    3. Verifying token application
    4. Submitting the form (if requested)
    """
    
    def __init__(self, download_dir="tmp"):
        """Initialize the TokenSubmitter."""
        self.download_dir = download_dir
        
        # Ensure the download directory exists
        os.makedirs(self.download_dir, exist_ok=True)
    
    def apply_token(self, sb, token, params=None, submit_form=False):
        """
        Apply a solved reCAPTCHA token to the original captcha.
        
        Args:
            sb: SeleniumBase instance with the page containing the captcha
            token: The solved reCAPTCHA token
            params (dict, optional): reCAPTCHA parameters. If not provided, they will be extracted.
                Expected keys: is_invisible, is_enterprise
            submit_form (bool, optional): Whether to submit the form after applying token. Defaults to False.
        
        Returns:
            bool: True if token was successfully applied, False otherwise
        """
        print("\n=== Applying reCAPTCHA Token ===")
        
        if params is None:
            # No params provided, extract basic information about the captcha
            params = self._extract_basic_captcha_info(sb)
        
        # Get information about the captcha implementation
        captcha_info = self._find_recaptcha_clients(sb)
        if not captcha_info:
            print("Could not find reCAPTCHA implementation details. Trying direct token injection.")
            success = self._inject_token_directly(sb, token, params.get('is_invisible', False))
        else:
            print(f"Found {len(captcha_info)} reCAPTCHA implementation(s)")
            
            # Loop through all found implementations and apply token
            success = False
            for impl in captcha_info:
                print(f"\nApplying token to reCAPTCHA implementation: {impl['id']} (Version: {impl['version']})")
                
                # Determine the method to use for applying the token
                if impl['version'] == 'V3':
                    success |= self._apply_token_v3(sb, token, impl)
                else:
                    success |= self._apply_token_v2(sb, token, impl)
                    
            if not success:
                # If no implementations were successful, try direct method as fallback
                print("\nNo callback functions found. Trying direct token injection...")
                success = self._inject_token_directly(sb, token, params.get('is_invisible', False))
        
        # Verify the token application
        if success:
            verification = self.verify_token_application(sb)
            if not verification:
                print("Warning: Token verification failed, but proceeding anyway")
        
        # Submit the form if requested
        if submit_form and success:
            print("\nAttempting to submit the form...")
            form_submitted = self.submit_form(sb)
            if form_submitted:
                print("✅ Form submitted successfully")
            else:
                print("❌ Form submission failed or no form found")
            
        return success
    
    def submit_form(self, sb):
        """
        Submit the form containing the reCAPTCHA after token has been applied.
        
        Args:
            sb: SeleniumBase instance
            
        Returns:
            bool: True if form was successfully submitted, False otherwise
        """
        try:
            # Try multiple approaches to submit the form
            result = sb.execute_script("""
                try {
                    // Strategy 1: Try to find the form containing the recaptcha and submit it
                    const recaptchaElements = document.querySelectorAll('textarea[name="g-recaptcha-response"], input[name="g-recaptcha-response"]');
                    for (const recaptchaEl of recaptchaElements) {
                        const form = recaptchaEl.closest('form');
                        if (form) {
                            console.log("Found form containing recaptcha, submitting...");
                            form.submit();
                            return { success: true, method: "form_submit" };
                        }
                    }
                    
                    // Strategy 2: Look for a submit button near the reCAPTCHA
                    const submitButtons = Array.from(document.querySelectorAll('button[type="submit"], input[type="submit"], button:not([type]), [role="button"]'));
                    
                    // Sort by proximity to reCAPTCHA (if any found)
                    if (recaptchaElements.length > 0 && submitButtons.length > 0) {
                        const recaptchaEl = recaptchaElements[0];
                        submitButtons.sort((a, b) => {
                            const aRect = a.getBoundingClientRect();
                            const bRect = b.getBoundingClientRect();
                            const recaptchaRect = recaptchaEl.getBoundingClientRect();
                            
                            // Calculate distances from recaptcha
                            const aDist = Math.hypot(
                                aRect.left + aRect.width/2 - (recaptchaRect.left + recaptchaRect.width/2),
                                aRect.top + aRect.height/2 - (recaptchaRect.top + recaptchaRect.height/2)
                            );
                            const bDist = Math.hypot(
                                bRect.left + bRect.width/2 - (recaptchaRect.left + recaptchaRect.width/2),
                                bRect.top + bRect.height/2 - (recaptchaRect.top + recaptchaRect.height/2)
                            );
                            
                            return aDist - bDist;
                        });
                        
                        // Click the closest submit button
                        console.log("Clicking the submit button closest to reCAPTCHA:", submitButtons[0]);
                        submitButtons[0].click();
                        return { success: true, method: "button_click" };
                    }
                    
                    // Strategy 3: If on Google's demo page, we know the button ID
                    const demoButton = document.getElementById('recaptcha-demo-submit');
                    if (demoButton) {
                        console.log("Found demo submit button by ID");
                        demoButton.click();
                        return { success: true, method: "demo_button" };
                    }
                    
                    // Strategy 4: Find any submit button
                    if (submitButtons.length > 0) {
                        console.log("Clicking first available submit button");
                        submitButtons[0].click();
                        return { success: true, method: "first_button" };
                    }
                    
                    // Strategy 5: Find any form and submit it
                    const forms = document.querySelectorAll('form');
                    if (forms.length > 0) {
                        console.log("Submitting first available form");
                        forms[0].submit();
                        return { success: true, method: "first_form" };
                    }
                    
                    return { success: false, reason: "No suitable form or button found" };
                } catch (e) {
                    console.error("Error submitting form:", e);
                    return { success: false, error: e.message };
                }
            """)
            
            if result and result.get('success'):
                print(f"Form submitted using method: {result.get('method')}")
                return True
            else:
                print(f"Form submission failed: {result.get('reason') or result.get('error') or 'Unknown reason'}")
                return False
                
        except Exception as e:
            print(f"Error attempting to submit form: {e}")
            return False
    
    def _extract_basic_captcha_info(self, sb):
        """Extract basic information about the captcha."""
        print("Extracting basic captcha information...")
        
        params = {
            "is_invisible": False,
            "is_enterprise": False
        }
        
        try:
            # Determine if it's invisible and enterprise using JavaScript
            captcha_data = sb.execute_script("""
                // Check for invisible captcha
                const invisibleEl = document.querySelector('[data-size="invisible"]');
                const isInvisible = !!invisibleEl;
                
                // Check for enterprise captcha
                const scripts = document.querySelectorAll('script[src*="recaptcha"]');
                let isEnterprise = false;
                let scriptSrc = null;
                
                for (const script of scripts) {
                    const src = script.getAttribute('src');
                    if (src && src.includes('enterprise')) {
                        isEnterprise = true;
                        scriptSrc = src;
                        break;
                    }
                }
                
                return {
                    isInvisible: isInvisible,
                    isEnterprise: isEnterprise,
                    scriptSrc: scriptSrc
                };
            """)
            
            if captcha_data:
                params["is_invisible"] = captcha_data.get("isInvisible", False)
                params["is_enterprise"] = captcha_data.get("isEnterprise", False)
                
                print(f"Detected reCAPTCHA: {'Invisible' if params['is_invisible'] else 'Checkbox'}, "
                      f"{'Enterprise' if params['is_enterprise'] else 'Standard'}")
                
        except Exception as e:
            print(f"Error extracting basic captcha information: {e}")
            
        return params
    
    def _find_recaptcha_clients(self, sb):
        """
        Find reCAPTCHA client implementations using the script from 2captcha.
        
        This function adapts the findRecaptchaClients JavaScript from:
        https://gist.github.com/2captcha/2ee70fa1130e756e1693a5d4be4d8c70
        """
        print("Finding reCAPTCHA client implementations...")
        
        try:
            # Execute the findRecaptchaClients script from 2captcha
            captcha_clients = sb.execute_script("""
                function findRecaptchaClients() {
                    if (typeof (___grecaptcha_cfg) !== 'undefined') {
                        return Object.entries(___grecaptcha_cfg.clients).map(([cid, client]) => {
                            const data = { id: cid, version: cid >= 10000 ? 'V3' : 'V2' };
                            const objects = Object.entries(client).filter(([_, value]) => value && typeof value === 'object');
                            
                            objects.forEach(([toplevelKey, toplevel]) => {
                                const found = Object.entries(toplevel).find(([sublevelKey, sublevel]) => {
                                    if (sublevel && typeof sublevel === 'object' && sublevel.sitekey) {
                                        data.sitekey = sublevel.sitekey;
                                        return true;
                                    }
                                    return false;
                                });
                                
                                if (typeof toplevel.callback === 'function') {
                                    data.callback = 'function';
                                    data.function = toplevelKey;
                                }
                                
                                if (typeof toplevel.selectedByButtonElement === 'function') {
                                    data.callback = toplevelKey;
                                    data.function = 'selectedByButtonElement';
                                }
                            });
                            
                            if (!data.sitekey && data.version === 'V3') {
                                console.log("Checking for legacy V3 implementation with enterprise or render mode...");
                                try {
                                    // This is an alternative detection flow for V3 that is embedded via render= mode
                                    // or enterprise mode where we don't have direct access to the sitekey
                                    // Attempt to extract using a different approach for V3
                                    const entries = Object.entries(___grecaptcha_cfg.enterprise2fa || {}).find(([_, value]) => {
                                        return value && typeof value === 'object' && value.sitekey;
                                    }) || [];
                                    if (entries.length > 1) {
                                        const [_, info] = entries;
                                        data.sitekey = info.sitekey;
                                    }
                                } catch (e) {
                                    console.log("V3 enterprise detection failed:", e);
                                }
                            }
                            
                            // Add the URL of the page to help identify which implementation goes with which page
                            data.pageurl = document.location.href;
                            
                            return data;
                        });
                    }
                    return [];
                }
                
                return findRecaptchaClients();
            """)
            
            if captcha_clients:
                for client in captcha_clients:
                    print(f"Found reCAPTCHA client: ID={client.get('id')}, "
                          f"Version={client.get('version')}, "
                          f"Callback={client.get('callback')}")
                return captcha_clients
            else:
                print("No reCAPTCHA clients found using the 2captcha script.")
                return []
                
        except Exception as e:
            print(f"Error finding reCAPTCHA clients: {e}")
            return []
    
    def _apply_token_v2(self, sb, token, impl):
        """
        Apply token to a V2 reCAPTCHA implementation.
        
        Args:
            sb: SeleniumBase instance
            token: Solved reCAPTCHA token
            impl: Implementation details from _find_recaptcha_clients
            
        Returns:
            bool: Success status
        """
        print(f"Applying token to V2 reCAPTCHA (ID: {impl['id']})...")
        
        try:
            # First set the token in the g-recaptcha-response textarea
            success = sb.execute_script("""
                try {
                    // First, inject into the standard textarea field
                    let standard = document.querySelector('textarea[name="g-recaptcha-response"]');
                    if (standard) {
                        standard.value = arguments[0];
                        console.log("Token injected into standard textarea");
                    }
                    
                    // Then try the specific ID-based textarea if available
                    let specific = document.getElementById('g-recaptcha-response');
                    if (specific) {
                        specific.value = arguments[0]; 
                        console.log("Token injected into g-recaptcha-response by ID");
                    }
                    
                    // If there's a specific ID for this implementation
                    let withId = document.getElementById('g-recaptcha-response-' + arguments[1]);
                    if (withId) {
                        withId.value = arguments[0];
                        console.log("Token injected into implementation-specific textarea");
                    }
                    
                    return true;
                } catch (e) {
                    console.error("Error injecting token:", e);
                    return false;
                }
            """, token, impl['id'])
            
            if not success:
                print("Warning: Failed to inject token into textarea")
            
            # Then try to call the callback function if available
            if impl.get('callback') and impl.get('function'):
                print(f"Calling callback function: {impl.get('callback')} / {impl.get('function')}")
                
                callback_result = sb.execute_script("""
                    try {
                        if (arguments[2] === 'function') {
                            // Case 1: The function itself is the callback
                            if (___grecaptcha_cfg.clients[arguments[0]][arguments[1]]) {
                                ___grecaptcha_cfg.clients[arguments[0]][arguments[1]](arguments[3]);
                                return "Called direct function callback";
                            }
                        } else if (arguments[1] === 'selectedByButtonElement') {
                            // Case 2: The selectedByButtonElement function is the callback
                            if (___grecaptcha_cfg.clients[arguments[0]][arguments[2]] && 
                                typeof ___grecaptcha_cfg.clients[arguments[0]][arguments[2]].selectedByButtonElement === 'function') {
                                ___grecaptcha_cfg.clients[arguments[0]][arguments[2]].selectedByButtonElement(arguments[3]);
                                return "Called selectedByButtonElement callback";
                            }
                        } else {
                            // Case 3: Generic callback reference
                            if (___grecaptcha_cfg.clients[arguments[0]][arguments[1]][arguments[2]]) {
                                ___grecaptcha_cfg.clients[arguments[0]][arguments[1]][arguments[2]](arguments[3]);
                                return "Called nested callback function";
                            }
                        }
                        
                        return "No matching callback function structure found";
                    } catch (e) {
                        console.error("Error calling callback:", e);
                        return "Error: " + e.message;
                    }
                """, impl['id'], impl.get('function'), impl.get('callback'), token)
                
                print(f"Callback result: {callback_result}")
                
                # Check if any successful callback message was returned
                callback_success = isinstance(callback_result, str) and callback_result.startswith("Called")
                return success and callback_success
            else:
                print("No callback function available. Token injected but callback not triggered.")
                return success
                
        except Exception as e:
            print(f"Error applying V2 token: {e}")
            return False
    
    def _apply_token_v3(self, sb, token, impl):
        """
        Apply token to a V3 reCAPTCHA implementation.
        
        Args:
            sb: SeleniumBase instance
            token: Solved reCAPTCHA token
            impl: Implementation details from _find_recaptcha_clients
            
        Returns:
            bool: Success status
        """
        print(f"Applying token to V3 reCAPTCHA (ID: {impl['id']})...")
        
        try:
            # For V3, we first need to set the token in the textarea
            success = sb.execute_script("""
                try {
                    // For V3, the textarea typically has a specific ID format
                    let v3Textarea = document.getElementById('g-recaptcha-response-' + arguments[1]);
                    if (v3Textarea) {
                        v3Textarea.value = arguments[0];
                        console.log("Token injected into V3-specific textarea");
                        return true;
                    }
                    
                    // If specific element not found, try to find any hidden input or textarea for recaptcha
                    let possibleElements = document.querySelectorAll('textarea[name="g-recaptcha-response"], input[name="g-recaptcha-response"]');
                    if (possibleElements.length > 0) {
                        for (let el of possibleElements) {
                            el.value = arguments[0];
                        }
                        console.log("Token injected into " + possibleElements.length + " possible elements");
                        return true;
                    }
                    
                    // Last resort: create a hidden input if none exists
                    if (possibleElements.length === 0) {
                        let hiddenInput = document.createElement('input');
                        hiddenInput.type = 'hidden';
                        hiddenInput.name = 'g-recaptcha-response';
                        hiddenInput.value = arguments[0];
                        document.querySelector('form') ? document.querySelector('form').appendChild(hiddenInput) : document.body.appendChild(hiddenInput);
                        console.log("Created and injected hidden input with token");
                        return true;
                    }
                    
                    return false;
                } catch (e) {
                    console.error("Error injecting V3 token:", e);
                    return false;
                }
            """, token, impl['id'])
            
            if not success:
                print("Warning: Failed to inject token into V3 textarea/input")
            
            # Then try to call the callback function if available
            if impl.get('callback') and impl.get('function'):
                print(f"Calling V3 callback function: {impl.get('callback')} / {impl.get('function')}")
                
                # The callback handling for V3 is similar to V2 but might have different structures
                callback_result = sb.execute_script("""
                    try {
                        if (arguments[2] === 'function') {
                            // Direct function callback
                            if (___grecaptcha_cfg.clients[arguments[0]][arguments[1]]) {
                                ___grecaptcha_cfg.clients[arguments[0]][arguments[1]](arguments[3]);
                                return "Called direct V3 function callback";
                            }
                        } else if (___grecaptcha_cfg.clients[arguments[0]][arguments[2]]) {
                            // V3 sometimes has a different callback structure
                            if (typeof ___grecaptcha_cfg.clients[arguments[0]][arguments[2]] === 'function') {
                                ___grecaptcha_cfg.clients[arguments[0]][arguments[2]](arguments[3]);
                                return "Called V3 callback function";
                            } else if (___grecaptcha_cfg.clients[arguments[0]][arguments[2]][arguments[1]]) {
                                ___grecaptcha_cfg.clients[arguments[0]][arguments[2]][arguments[1]](arguments[3]);
                                return "Called nested V3 callback function";
                            }
                        }
                        
                        return "No matching V3 callback function structure found";
                    } catch (e) {
                        console.error("Error calling V3 callback:", e);
                        return "Error: " + e.message;
                    }
                """, impl['id'], impl.get('function'), impl.get('callback'), token)
                
                print(f"V3 callback result: {callback_result}")
                
                # Check if any successful callback message was returned
                callback_success = isinstance(callback_result, str) and callback_result.startswith("Called")
                return success and callback_success
            else:
                print("No V3 callback function available. Token injected but callback not triggered.")
                return success
                
        except Exception as e:
            print(f"Error applying V3 token: {e}")
            return False
    
    def _inject_token_directly(self, sb, token, is_invisible=False):
        """
        Direct method to inject token without using callback functions.
        This is a fallback method when no callback functions are found.
        
        Args:
            sb: SeleniumBase instance
            token: Solved reCAPTCHA token
            is_invisible: Whether the captcha is invisible
            
        Returns:
            bool: Success status
        """
        print("Attempting direct token injection method...")
        
        try:
            # Comprehensive token injection approach
            injection_result = sb.execute_script("""
                try {
                    let success = false;
                    const token = arguments[0];
                    const isInvisible = arguments[1];
                    
                    // Method 1: Standard textarea
                    const textareas = document.querySelectorAll('textarea[name="g-recaptcha-response"]');
                    if (textareas.length > 0) {
                        for (let textarea of textareas) {
                            textarea.value = token;
                            // Dispatch events to simulate user input
                            textarea.dispatchEvent(new Event('change', { bubbles: true }));
                            textarea.dispatchEvent(new Event('input', { bubbles: true }));
                            console.log("Injected token into textarea:", textarea);
                        }
                        success = true;
                    }
                    
                    // Method 2: Try all possible g-recaptcha-response elements with various IDs
                    for (let i = 0; i < 10; i++) {
                        const el = document.getElementById('g-recaptcha-response' + (i > 0 ? '-' + i : ''));
                        if (el) {
                            el.value = token;
                            el.dispatchEvent(new Event('change', { bubbles: true }));
                            console.log("Injected token into element with ID:", el.id);
                            success = true;
                        }
                    }
                    
                    // Method 3: For invisible reCAPTCHA, try to find and call the callback directly
                    if (isInvisible) {
                        // Look for common callback names
                        const commonCallbacks = ['onCaptchaSuccess', 'onSuccess', 'captchaCallback', 
                                               'recaptchaCallback', 'handleCaptcha', 'verifyCallback'];
                        
                        for (let callbackName of commonCallbacks) {
                            if (typeof window[callbackName] === 'function') {
                                try {
                                    window[callbackName](token);
                                    console.log("Called potential callback function:", callbackName);
                                    success = true;
                                } catch (callbackErr) {
                                    console.log("Error calling", callbackName, ":", callbackErr);
                                }
                            }
                        }
                    }
                    
                    // Method 4: Last resort - search for forms and try to add/update hidden inputs
                    const forms = document.querySelectorAll('form');
                    for (let form of forms) {
                        let input = form.querySelector('input[name="g-recaptcha-response"]');
                        if (!input) {
                            input = document.createElement('input');
                            input.type = 'hidden';
                            input.name = 'g-recaptcha-response';
                            form.appendChild(input);
                        }
                        input.value = token;
                        console.log("Added/updated hidden input in form");
                        success = true;
                    }
                    
                    return success;
                } catch (e) {
                    console.error("Error in direct token injection:", e);
                    return false;
                }
            """, token, is_invisible)
            
            if injection_result:
                print("Successfully injected token using direct method")
                return True
            else:
                print("Failed to inject token using direct method")
                return False
                
        except Exception as e:
            print(f"Error in direct token injection: {e}")
            return False
    
    def verify_token_application(self, sb):
        """
        Verify that the token was properly applied.
        
        Args:
            sb: SeleniumBase instance
            
        Returns:
            bool: True if token is present in the expected elements
        """
        print("\nVerifying token application...")
        
        try:
            # Check various elements where the token should be present
            verification_result = sb.execute_script("""
                try {
                    const results = {
                        standardTextarea: false,
                        idBasedElements: [],
                        hiddenInputs: false
                    };
                    
                    // Check standard textarea
                    const textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
                    if (textarea && textarea.value) {
                        results.standardTextarea = true;
                        results.standardTextareaValue = textarea.value.substring(0, 20) + '...';
                    }
                    
                    // Check ID-based elements
                    for (let i = 0; i < 10; i++) {
                        const el = document.getElementById('g-recaptcha-response' + (i > 0 ? '-' + i : ''));
                        if (el && el.value) {
                            results.idBasedElements.push({
                                id: el.id,
                                hasValue: true,
                                valuePreview: el.value.substring(0, 20) + '...'
                            });
                        }
                    }
                    
                    // Check hidden inputs
                    const hiddenInputs = document.querySelectorAll('input[name="g-recaptcha-response"]');
                    if (hiddenInputs.length > 0) {
                        for (let input of hiddenInputs) {
                            if (input.value) {
                                results.hiddenInputs = true;
                                break;
                            }
                        }
                    }
                    
                    return results;
                } catch (e) {
                    console.error("Error verifying token application:", e);
                    return { error: e.message };
                }
            """)
            
            print("\nToken verification results:")
            
            if verification_result.get('error'):
                print(f"Error during verification: {verification_result.get('error')}")
                return False
                
            if verification_result.get('standardTextarea'):
                print(f"✅ Token found in standard textarea: {verification_result.get('standardTextareaValue')}")
                success = True
            else:
                print("❌ No token found in standard textarea")
                success = False
                
            if verification_result.get('idBasedElements'):
                for element in verification_result.get('idBasedElements'):
                    print(f"✅ Token found in element with ID {element.get('id')}: {element.get('valuePreview')}")
                success = True
            else:
                print("❌ No token found in ID-based elements")
                if not success:
                    success = False
                    
            if verification_result.get('hiddenInputs'):
                print("✅ Token found in hidden inputs")
                success = True
            else:
                print("❌ No token found in hidden inputs")
                if not success:
                    success = False
                    
            return success
                
        except Exception as e:
            print(f"Error verifying token application: {e}")
            return False


# Simple example usage
if __name__ == "__main__":
    import sys
    from seleniumbase import SB
    
    # This is just a demonstration - you'd typically get a real token from a solving service
    dummy_token = "03AFcWeA40GxgGLv7AOWLA7apiMvR6zVc36soHi3fuNqfW_yq9RT6mY7gZGSBwniSlbF9p99TbVGNskOdPNfeJ3x8ro2rqWJxI-kqUxefVarJVPDWrbT1re_tW709vZ5ba7QN6jmY6zp7YTQHeFFH3qTh8TLK85AM_5ZpA3FZmA5_09mRPRCYCl3G-gwmd7xR0fx8lCrcK6p4jiPqEzvvGAn0LqYhpDP8Fvxha-Bz1arvMD48Wamd3SI5NleDMZJggWqLUPxdv0RTQeRKhalFdGnh5bDfPt5gwuihaXdrruAjwrgBpxFXBLoo8WfEhcQlDNrBe3pDkuN5Q7aQYrtar29uCAtPwuNcmdQhpc7bdh0uN5uZWpXPv2Ifir0i-lficFj-0K2NMM7r_46xSvdYn76mt0AWfAFaW98gGgu2g00Y-IjYrjUxzYLVXiBqM_pPjJn3Zuwp6T9KmZs1c0NEloYgarVSKLM067bVvGBlV0VfkY7lEqcF-oFxLX6a_jvv_oMCdgBGhDKG8a8ZogD6Mhe6ATNMN2kvwcrdG6mPSYVGia7uHMcHWskJWEmEEPSy3c6xZs4esQlOcDL3mDWG7fkoAw7cYmr6_A5GYBGP0DHMzAapC507S60rZZLvmH78eupd-BqzUDs1EG23ubWXlk1NmYy3IOxKxu6AmTz-KkrLr3TZYmSEHVS_unGzSODOk8byl70z5tLPA4JHEJa4UbUq75_13tXtLz6F8tqWo35L6Z-IWKKu8eBkQqXp7tY7lxi-FZDXwDkDerg0duzigllQKJkp5crqhkycxXRl_qnq77zI111kxUMj6WuiYAhnkIK7UO1LafFGsA38tPNvxOHsWjRP_FDl_srqk5aQzMu0pVawFFfwF1v74oBKBQ6v7Gs281gtI1WC7epNGXAkNJjX-y11NfHYTUB3cVcoz0vRXsWp9C_aV5tPSxAXINp-Tp_ysPSbWCHPawkxGb9B8i6-5g0IuEIzNSEPWMsUpIkZEzHhMf0iGeHKWGaPxbxICi8BTMVTUzY2ZipT9_F4rZfivSssmhMXRFiAV7CoG-LJDCqBxDYOuZYPQKqHIt5LIh9er5w4cgvm_tnUiOiUOWQz_5hmn9ryu_4V_pzzvqBWO-gNAhc_ommW5RwkvrgwUsj7_0fdPyn79h94DkAoKDqIgqD5WB2Tckq28PjoOtgUwrF6kd8jWwVWym3-zbxcQ3YOTXxP34UYijRrsMcdfXcx2Z0gg0ePJUDGxybQM5-Cl__wlW5HIG0ZgM69qH47AAdkOf1DnQ3DT3j9n8vQISh83210JZbrLAcFjfXoRnWcarBdGCftoe1k03SvrfbM_lGRpyjWjLOWVNkPmEVDf8y7Iey1KmtXtc75tmVqNmQcO9vSSvJYfx5ZR65eK_si2lyLTO0WPqhtSlJtmXxNR2ELufFraKm2vAmsaH83Q3oo_KdcYYZUTrvsxlPJwj9BbdVXuZo3mKUog56fSNOhVVvl88hBXM-tVfDW_ChXE8l1iVl27_g_yD9XmYg1Hw3rSdvESBkEEeSZncZhOygys4ZTs9qG9cR9gREkqxAnx_yOD92SoG3b6toGT2FHJoRJVRKCv3tfvUtygRa20Ve9jK_2smfmbc3aQ3aMc7wuv79L3WHrtIyrsNiix2oasvvNS0DS9XZHYQXAeNDfuuPStHdDtuy-dntqTzW4Dj8KeAfo0TJUVdiY7H4Iu7dYG2lumhGoogAgXw8sJcfPe9bBDvOxjEQzJc2iBfefQ8rAMTcdCz1yZDICjOKoxvKggl2Ue8NPwg04b3G3sRjyRQN-5heZTH4iiI2iWv58PkBO6BfH6w1ckLUQMwYCGO5vNTVE_PbH00dtVNCELmPXEChBqaFXJn4QS70pdgNxxi1w1dpzFysXpDMHAxX46wNAxQax4sFbEN4l4qp_0ypP8iLMFp6iXPg3BWMS-SuzmkicKffwtzyXaSRoiaDICrv9EvmI_lSTgA3hcsvNzv3W2sgCNbfLiRRZb0YrYMw"
    
    print("\n=== Token Submitter Demo ===")
    print("This demo will attempt to apply a dummy token to a reCAPTCHA on a demo page.")
    print("For an actual implementation, you would use a real token from a solving service.")
    
    try:
        with SB(uc=True) as sb:
            # Navigate to a page with reCAPTCHA
            url = "https://www.google.com/recaptcha/api2/demo"
            print(f"\nNavigating to: {url}")
            sb.open(url)
            
            # Wait for page to load
            sb.sleep(2)
            
            # Create token submitter
            submitter = TokenSubmitter(download_dir="tmp")
            
            # Apply the dummy token and submit the form
            success = submitter.apply_token(sb, dummy_token, submit_form=True)
            
            if success:
                print("\n✅ Token application process completed successfully")
                
                # Verify token application
                verification = submitter.verify_token_application(sb)
                if verification:
                    print("\n✅ Token verification successful")
                else:
                    print("\n❌ Token verification failed")
            else:
                print("\n❌ Token application failed")
                
            # Keep browser open for observation
            print("\nKeeping browser open for 5 seconds for observation...")
            sb.sleep(5)
    
    except Exception as e:
        print(f"\nError during demo: {e}")
        sys.exit(1)
    
    sys.exit(0) 