import os
import time
import json


class TokenSubmitter:
    """
    A class for applying solved reCAPTCHA v2 tokens to the original captcha.
    
    This class handles:
    1. Applying a solved token to a reCAPTCHA v2 (standard or invisible)
    2. Triggering the reCAPTCHA callback function
    3. Verifying token application
    4. Submitting the form (if requested)
    
    Note: This class only supports reCAPTCHA v2. It does not support reCAPTCHA v3.
    """
    
    def __init__(self, download_dir="tmp"):
        """Initialize the TokenSubmitter."""
        self.download_dir = download_dir
        
        # Ensure the download directory exists
        os.makedirs(self.download_dir, exist_ok=True)
    
    def apply_token(self, sb, token, submit_form=False):
        """
        Apply a reCAPTCHA token to the page, verify it, and optionally submit the form.
        
        Args:
            sb: SeleniumBase instance
            token: The reCAPTCHA token to apply
            submit_form: Whether to submit the form after applying the token
            
        Returns:
            dict: Result containing success status and other information
        """
        print("\n=== Applying reCAPTCHA Token ===")
        result = {
            "success": False,
            "token_applied": False,
            "verified": False,
            "form_submitted": False,
            "error": None
        }
        
        try:
            response_fields = sb.find_elements('textarea[name="g-recaptcha-response"]')
                        
            if not response_fields or len(response_fields) == 0:
                print("⚠️ No reCAPTCHA response field found")
                result["error"] = "No reCAPTCHA response field found"
                return result
                
            response_field = response_fields[0]  # Get the first element from the list
            print(f"Found reCAPTCHA response field")
            print(response_field.get_attribute("name") + " " + response_field.get_attribute("id"))
            
            # Inject token into the response field
            print(f"Injecting token into response field")

            # Make it visible first and not hidden, then set the value
            sb.execute_script("""
                // Make the element visible
                arguments[0].style.display = 'block';
                arguments[0].style.visibility = 'visible';
                arguments[0].style.opacity = '1';
                
                // Set the token value
                arguments[0].value = arguments[1];
                
                // Trigger change event to ensure the page recognizes the token
                const event = new Event('change', { bubbles: true });
                arguments[0].dispatchEvent(event);
                
                // Also trigger input event for good measure
                const inputEvent = new Event('input', { bubbles: true });
                arguments[0].dispatchEvent(inputEvent);
                
                return true;
            """, response_field, token)
            
            print("✅ Token successfully applied to response field")
            result["token_applied"] = True

      
            # Step 3: Execute callback if available
            print("Looking for reCAPTCHA clients...")
            clients = self._find_recaptcha_clients(sb)
            
            if clients:
                print(f"Found {len(clients)} reCAPTCHA clients")
                # Try to execute callback for each client
                for client in clients:
                    if self._execute_callback(sb, client, token):
                        print(f"✅ Successfully executed callback for client {client['id']}")
                        break
                    else:
                        print(f"⚠️ Failed to execute callback for client {client['id']}")
            else:
                print("No reCAPTCHA clients found, but token was injected")
            
            # Step 4: Verify token application
            print("\nVerifying token application...")
            # Check if the response field has the token value
            has_token = False
            
            # Re-fetch the response fields to ensure we have the latest state
            response_fields = sb.find_elements('textarea[name="g-recaptcha-response"]')
            
            for i, field in enumerate(response_fields):
                value = sb.execute_script("return arguments[0].value", field)
                if value:
                    print(f"✅ Response field {i+1}/{len(response_fields)} has a token value")
                    has_token = True
                else:
                    print(f"⚠️ Response field {i+1}/{len(response_fields)} is empty")
            
            if not has_token:
                print("❌ No token found in any response field")
                result["error"] = "Token verification failed - no token found"
                return result
                
            # Check if the reCAPTCHA challenge is still visible (which would indicate failure)
            challenge_iframes = sb.find_elements('iframe[src*="recaptcha/api2/bframe"]')
            
            for iframe in challenge_iframes:
                # Use JavaScript to check visibility instead of is_element_visible
                is_visible = sb.execute_script("""
                    const iframe = arguments[0];
                    const style = window.getComputedStyle(iframe);
                    return style.visibility !== 'hidden' && style.display !== 'none';
                """, iframe)
                
                if is_visible:
                    # Use JavaScript to get the style attribute instead of get_attribute
                    style = sb.execute_script("return arguments[0].getAttribute('style') || '';", iframe)
                    if "visibility: visible" in style or "display: block" in style:
                        print("❌ reCAPTCHA challenge is still visible, token may not have been accepted")
                        result["error"] = "Token verification failed - challenge still visible"
                        return result
            
            # Check if the checkbox is checked (for checkbox reCAPTCHA)
            try:
                checkbox_status = sb.execute_script("""
                    const iframes = document.querySelectorAll('iframe[src*="recaptcha/api2/anchor"]');
                    for (let iframe of iframes) {
                        try {
                            const checked = iframe.contentDocument.querySelector('.recaptcha-checkbox-checked');
                            if (checked) return "CHECKED";
                        } catch (e) {
                            // Cross-origin access error, expected
                        }
                    }
                    return "UNKNOWN";
                """)
                
                if checkbox_status == "CHECKED":
                    print("✅ reCAPTCHA checkbox is checked")
                else:
                    print("ℹ️ Could not determine if reCAPTCHA checkbox is checked (likely due to cross-origin restrictions)")
            except Exception as e:
                print(f"Error checking reCAPTCHA checkbox status: {e}")
            
            print("✅ reCAPTCHA token appears to be properly applied")
            result["verified"] = True
            
            # Step 5: Submit the form if requested
            if submit_form:
                print("\nSubmitting form...")
                try:
                    # Find the form containing the reCAPTCHA response element
                    print("Looking for form containing reCAPTCHA...")
                    recaptcha_elements = sb.find_elements("textarea[name='g-recaptcha-response'], input[name='g-recaptcha-response']")
                    
                    if not recaptcha_elements:
                        print("No reCAPTCHA response elements found")
                        result["error"] = "Form submission failed - no reCAPTCHA elements found"
                        return result
                        
                    print(f"Found {len(recaptcha_elements)} reCAPTCHA elements")
                    
                    # Try to submit using the first element found
                    # Find the parent form using JavaScript
                    form = sb.execute_script("return arguments[0].closest('form')", recaptcha_elements[0])
                    if not form:
                        print("No parent form found for reCAPTCHA element")
                        result["error"] = "Form submission failed - no parent form found"
                        return result
                        
                    print("Found form containing reCAPTCHA")
                    
                    # First try to find and click a submit button in this form
                    submit_buttons = sb.execute_script(
                        "return Array.from(arguments[0].querySelectorAll('button[type=\"submit\"], input[type=\"submit\"]'))", 
                        form
                    )
                    
                    if submit_buttons and len(submit_buttons) > 0:
                        print("Found submit button in form, clicking it...")
                        sb.execute_script("arguments[0].click()", submit_buttons[0])
                        print("Form submitted by clicking submit button")
                        result["form_submitted"] = True
                    else:
                        # If no submit button found, try to submit the form directly
                        print("No submit button found, submitting form directly...")
                        sb.execute_script("arguments[0].submit()", form)
                        print("Form submitted using submit() method")
                        result["form_submitted"] = True
                        
                except Exception as e:
                    print(f"Error submitting form: {e}")
                    result["error"] = f"Form submission failed: {str(e)}"
                    # Don't return here, as the token was still applied successfully
            
            # Success!
            result["success"] = True
            return result
            
        except Exception as e:
            print(f"Error applying token: {e}")
            result["error"] = str(e)
            return result
    
    
    
    def _find_recaptcha_clients(self, sb):
        """
        Find reCAPTCHA client implementations.
        
        """
        print("Finding reCAPTCHA client implementations...")
        
        try:
            # Execute the findRecaptchaClients script from 2captcha
            captcha_clients = sb.execute_script("""
                function findRecaptchaClients() {
                    if (typeof (___grecaptcha_cfg) !== 'undefined') {
                        return Object.entries(___grecaptcha_cfg.clients).map(([cid, client]) => {
                            // Only include V2 implementations (cid < 10000)
                            if (cid >= 10000) {
                                return null; // Skip V3 implementations
                            }
                            
                            const data = { id: cid, version: 'V2' };
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
                            
                            // Add the URL of the page to help identify which implementation goes with which page
                            data.pageurl = document.location.href;
                            
                            return data;
                        }).filter(item => item !== null); // Filter out null entries (V3)
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
    
    def _find_recaptcha_div(self, sb, client_id=None):
        """
        Find the reCAPTCHA div element and extract its data-callback attribute.
        
        Args:
            sb: SeleniumBase instance
            client_id: Optional client ID to help locate the specific div
            
        Returns:
            tuple: (div_element, callback_name) or (None, None) if not found
        """
        print("Finding reCAPTCHA div element...")
        
        try:
            # Find all reCAPTCHA divs
            recaptcha_divs = sb.find_elements('.g-recaptcha, [class*="g-recaptcha"]')
            
            if not recaptcha_divs:
                print("No reCAPTCHA div elements found")
                return None, None
                
            print(f"Found {len(recaptcha_divs)} reCAPTCHA div elements")
            
            # If client_id is provided, try to find the specific div for this client
            if client_id:
                for div in recaptcha_divs:
                    # Check if this div is associated with the client_id
                    # This could be via data-sitekey, data-widget-id, or other attributes
                    widget_id = sb.execute_script("return arguments[0].getAttribute('data-widget-id')", div)
                    if widget_id and widget_id == client_id:
                        print(f"Found div with matching widget ID: {widget_id}")
                        callback_name = sb.execute_script("return arguments[0].getAttribute('data-callback')", div)
                        return div, callback_name
            
            # If no specific div found or no client_id provided, use the first div
            div = recaptcha_divs[0]
            callback_name = sb.execute_script("return arguments[0].getAttribute('data-callback')", div)
            
            if callback_name:
                print(f"Found data-callback attribute: {callback_name}")
            else:
                print("No data-callback attribute found on reCAPTCHA div")
                
            return div, callback_name
            
        except Exception as e:
            print(f"Error finding reCAPTCHA div: {e}")
            return None, None
            
    def _execute_callback(self, sb, client, token):
        """
        Execute the callback function for a specific reCAPTCHA client.
        
        Args:
            sb: SeleniumBase instance
            client: Client implementation details from _find_recaptcha_clients
            token: Solved reCAPTCHA token
            
        Returns:
            bool: True if callback was executed successfully, False otherwise
        """
        print(f"Executing callback function for client {client['id']}...")
        
        try:
            # STEP 1: Try to execute callback from client information
            if client.get('callback') and client.get('function'):
                print(f"Found callback information: {client.get('callback')} / {client.get('function')}")
                
                # There are different possible callback structures, try them all
                callback_result = sb.execute_script("""
                    try {
                        const clientId = arguments[0];
                        const funcName = arguments[1];
                        const callbackType = arguments[2];
                        const token = arguments[3];
                        const clients = ___grecaptcha_cfg.clients;
                        
                        // Case 1: Function reference directly in the client object
                        if (callbackType === 'function' && 
                            typeof clients[clientId][funcName] === 'function') {
                            console.log("Calling direct function callback");
                            clients[clientId][funcName](token);
                            return "CALLED_DIRECT_FUNCTION";
                        }
                        
                        // Case 2: The selectedByButtonElement function
                        else if (funcName === 'selectedByButtonElement' && 
                                typeof clients[clientId][callbackType] === 'object' && 
                                typeof clients[clientId][callbackType].selectedByButtonElement === 'function') {
                            console.log("Calling selectedByButtonElement");
                            clients[clientId][callbackType].selectedByButtonElement(token);
                            return "CALLED_SELECTED_BY_BUTTON";
                        }
                        
                        // Case 3: String name of global function
                        else if (typeof callbackType === 'string' && window[callbackType]) {
                            console.log("Calling global function by name");
                            window[callbackType](token);
                            return "CALLED_GLOBAL_FUNCTION";
                        }
                        
                        // Case 4: Nested function in client object
                        else if (clients[clientId][funcName] && 
                                typeof clients[clientId][funcName][callbackType] === 'function') {
                            console.log("Calling nested callback function");
                            clients[clientId][funcName][callbackType](token);
                            return "CALLED_NESTED_FUNCTION";
                        }
                        
                        return "NO_CALLBACK_MATCH";
                    } catch (e) {
                        console.error("Error calling callback:", e);
                        return "ERROR: " + e.message;
                    }
                """, client['id'], client.get('function'), client.get('callback'), token)
                
                print(f"Callback execution result: {callback_result}")
                
                if isinstance(callback_result, str) and callback_result.startswith("CALLED_"):
                    print("✅ Successfully called callback function")
                    return True
                else:
                    print("⚠️ Failed to call callback function from client info")
            else:
                print("No callback information found in client data")
            
            # STEP 2: Try to find callback from data-callback attribute as fallback
            print("Looking for callback in data-callback attribute...")
            _, callback_name = self._find_recaptcha_div(sb, client.get('id'))
            
            if callback_name:
                print(f"Found data-callback: {callback_name}")
                result = sb.execute_script(f"""
                    try {{
                        if (typeof window['{callback_name}'] === 'function') {{
                            console.log("Calling callback function: {callback_name}");
                            window['{callback_name}']("{token}");
                            return true;
                        }}
                        return false;
                    }} catch (e) {{
                        console.error("Error calling {callback_name}:", e);
                        return false;
                    }}
                """)
                
                if result:
                    print(f"✅ Successfully called callback function: {callback_name}")
                    return True
                else:
                    print(f"⚠️ Failed to call callback function: {callback_name}")
            
            # No callback found or executed
            print("No callback function found or executed")
            return False
                
        except Exception as e:
            print(f"Error executing callback for client {client['id']}: {e}")
            return False


# Simple example usage
if __name__ == "__main__":
    import sys
    from seleniumbase import SB
    
    # This is just a demonstration token - you'd get a real one from a solving service
    dummy_token = "03AFcWeA40GxgGLv7AOWLA7apiMvR6zVc36soHi3fuNqfW_yq9RT6mY7gZGSBwniSlbF9p99TbVGNskOdPNfeJ3x8ro2rqWJxI-kqUxefVarJVPDWrbT1re_tW709vZ5ba7QN6jmY6zp7YTQHeFFH3qTh8TLK85AM_5ZpA3FZmA5_09mRPRCYCl3G-gwmd7xR0fx8lCrcK6p4jiPqEzvvGAn0LqYhpDP8Fvxha-Bz1arvMD48Wamd3SI5NleDMZJggWqLUPxdv0RTQeRKhalFdGnh5bDfPt5gwuihaXdrruAjwrgBpxFXBLoo8WfEhcQlDNrBe3pDkuN5Q7aQYrtar29uCAtPwuNcmdQhpc7bdh0uN5uZWpXPv2Ifir0i-lficFj-0K2NMM7r_46xSvdYn76mt0AWfAFaW98gGgu2g00Y-IjYrjUxzYLVXiBqM_pPjJn3Zuwp6T9KmZs1c0NEloYgarVSKLM067bVvGBlV0VfkY7lEqcF-oFxLX6a_jvv_oMCdgBGhDKG8a8ZogD6Mhe6ATNMN2kvwcrdG6mPSYVGia7uHMcHWskJWEmEEPSy3c6xZs4esQlOcDL3mDWG7fkoAw7cYmr6_A5GYBGP0DHMzAapC507S60rZZLvmH78eupd-BqzUDs1EG23ubWXlk1NmYy3IOxKxu6AmTz-KkrLr3TZYmSEHVS_unGzSODOk8byl70z5tLPA4JHEJa4UbUq75_13tXtLz6F8tqWo35L6Z-IWKKu8eBkQqXp7tY7lxi-FZDXwDkDerg0duzigllQKJkp5crqhkycxXRl_qnq77zI111kxUMj6WuiYAhnkIK7UO1LafFGsA38tPNvxOHsWjRP_FDl_srqk5aQzMu0pVawFFfwF1v74oBKBQ6v7Gs281gtI1WC7epNGXAkNJjX-y11NfHYTUB3cVcoz0vRXsWp9C_aV5tPSxAXINp-Tp_ysPSbWCHPawkxGb9B8i6-5g0IuEIzNSEPWMsUpIkZEzHhMf0iGeHKWGaPxbxICi8BTMVTUzY2ZipT9_F4rZfivSssmhMXRFiAV7CoG-LJDCqBxDYOuZYPQKqHIt5LIh9er5w4cgvm_tnUiOiUOWQz_5hmn9ryu_4V_pzzvqBWO-gNAhc_ommW5RwkvrgwUsj7_0fdPyn79h94DkAoKDqIgqD5WB2Tckq28PjoOtgUwrF6kd8jWwVWym3-zbxcQ3YOTXxP34UYijRrsMcdfXcx2Z0gg0ePJUDGxybQM5-Cl__wlW5HIG0ZgM69qH47AAdkOf1DnQ3DT3j9n8vQISh83210JZbrLAcFjfXoRnWcarBdGCftoe1k03SvrfbM_lGRpyjWjLOWVNkPmEVDf8y7Iey1KmtXtc75tmVqNmQcO9vSSvJYfx5ZR65eK_si2lyLTO0WPqhtSlJtmXxNR2ELufFraKm2vAmsaH83Q3oo_KdcYYZUTrvsxlPJwj9BbdVXuZo3mKUog56fSNOhVVvl88hBXM-tVfDW_ChXE8l1iVl27_g_yD9XmYg1Hw3rSdvESBkEEeSZncZhOygys4ZTs9qG9cR9gREkqxAnx_yOD92SoG3b6toGT2FHJoRJVRKCv3tfvUtygRa20Ve9jK_2smfmbc3aQ3aMc7wuv79L3WHrtIyrsNiix2oasvvNS0DS9XZHYQXAeNDfuuPStHdDtuy-dntqTzW4Dj8KeAfo0TJUVdiY7H4Iu7dYG2lumhGoogAgXw8sJcfPe9bBDvOxjEQzJc2iBfefQ8rAMTcdCz1yZDICjOKoxvKggl2Ue8NPwg04b3G3sRjyRQN-5heZTH4iiI2iWv58PkBO6BfH6w1ckLUQMwYCGO5vNTVE_PbH00dtVNCELmPXEChBqaFXJn4QS70pdgNxxi1w1dpzFysXpDMHAxX46wNAxQax4sFbEN4l4qp_0ypP8iLMFp6iXPg3BWMS-SuzmkicKffwtzyXaSRoiaDICrv9EvmI_lSTgA3hcsvNzv3W2sgCNbfLiRRZb0YrYMw"
    
    print("\n=== Token Submitter Demo ===")
    print("This demo will attempt to apply a token to a reCAPTCHA v2 on a demo page.")
    print("For an actual implementation, you would use a real token from a solving service.")
    print("Note: This class only supports reCAPTCHA v2, not v3.")
    
    try:
        with SB(uc=True) as sb:
            # Navigate to a page with reCAPTCHA v2
            url = "https://www.google.com/recaptcha/api2/demo"
            print(f"\nNavigating to: {url}")
            sb.open(url)
            
            # Wait for page to load
            sb.sleep(2)
            
            # Create token submitter and apply token
            submitter = TokenSubmitter(download_dir="tmp")
            result = submitter.apply_token(sb, dummy_token, submit_form=True)
            
            # Check result
            if result["success"]:
                print("\n✅ reCAPTCHA token applied successfully!")
                if result["form_submitted"]:
                    print("✅ Form was also submitted successfully")
            else:
                print(f"\n❌ Failed: {result['error']}")
    
    except Exception as e:
        print(f"\nError during demo: {e}")
        sys.exit(1)
    
    sys.exit(0) 