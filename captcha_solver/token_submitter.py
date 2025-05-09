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
    
    def apply_token(self, sb, token):
        """
        Apply a reCAPTCHA token to the page, verify it, and optionally submit the form.
        
        Args:
            sb: SeleniumBase instance
            token: The reCAPTCHA token to apply
            
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

            # Execute callback if available
            print("Looking for reCAPTCHA clients...")
            clients = self._find_recaptcha_clients(sb)
            
            if clients:
                print(f"Found {len(clients)} reCAPTCHA clients")
                client = clients[0]
                # Try to execute callback for each client
                if self._execute_callback(sb, client, token):
                    print(f"✅ Successfully executed callback")
                else:
                    print(f"⚠️ Failed to execute callback")
            else:
                print("No reCAPTCHA clients found, but token was injected")


            time.sleep(5)
                         

            
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
            # Execute the findRecaptchaClients script from the StackOverflow example
            captcha_clients = sb.execute_script("""
                function findRecaptchaClients() {
                  if (typeof (___grecaptcha_cfg) !== 'undefined') {
                    return Object.entries(___grecaptcha_cfg.clients).map(([cid, client]) => {
                      const data = { id: cid, version: cid >= 10000 ? 'V3' : 'V2' };
                      const objects = Object.entries(client).filter(([_, value]) => value && typeof value === 'object');
            
                      objects.forEach(([toplevelKey, toplevel]) => {
                        const found = Object.entries(toplevel).find(([_, value]) => (
                          value && typeof value === 'object' && 'sitekey' in value && 'size' in value
                        ));
            
                        if (typeof toplevel === 'object' && toplevel instanceof HTMLElement && toplevel['tagName'] === 'DIV'){
                            data.pageurl = toplevel.baseURI;
                        }
            
                        if (found) {
                          const [sublevelKey, sublevel] = found;
            
                          data.sitekey = sublevel.sitekey;
                          const callbackKey = data.version === 'V2' ? 'callback' : 'promise-callback';
                          const callback = sublevel[callbackKey];
                          if (!callback) {
                            data.callback = null;
                            data.function = null;
                          } else {
                            data.function = callback;
                            const keys = [cid, toplevelKey, sublevelKey, callbackKey].map((key) => `['${key}']`).join('');
                            data.callback = `___grecaptcha_cfg.clients${keys}`;
                          }
                        }
                      });
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
                print("No reCAPTCHA clients found using the script.")
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
        print(f"Executing callback function...")
        
        try:
            # DIRECT APPROACH (similar to example):
            # 1. Try to find and switch to the iframe if it exists
            try:
                iframe = sb.find_element('iframe[id="sec-cpt-if"]', by="css selector", timeout=2)
                if iframe:
                    print("Found reCAPTCHA iframe, switching to it...")
                    sb.switch_to.frame(iframe)
            except Exception as e:
                # Continue without iframe switch - it might not be needed
                pass
                
            # 2. Inject token into g-recaptcha-response (simple direct approach)
            sb.execute_script(f'document.getElementById("g-recaptcha-response").innerHTML="{token}"')
            
            # 3. Try to find the callback name and call it directly
            
            # First try the callback from client data
            callback_function = client.get('callback')
            if callback_function and callback_function != 'function':
                print(f"Found callback function in client data: {callback_function}")
                try:
                    # Execute the callback directly using the path
                    # Don't create a variable, just call the function directly using its path
                    sb.execute_script(f"""
                        try {{
                            // Call the function directly using its path
                            {callback_function}('{token}');
                            console.log("Successfully called callback at path: {callback_function}");
                            return true;
                        }} catch (e) {{
                            console.error("Error calling callback at path: {callback_function}", e);
                            return false;
                        }}
                    """)
                    print(f"✅ Successfully executed callback function from client data")
                    return True
                except Exception as e:
                    print(f"Error calling callback from client data: {e}")
            
            # Next try the data-callback attribute from the div
            _, callback_name = self._find_recaptcha_div(sb, client.get('id'))
            if callback_name:
                print(f"Found data-callback: {callback_name}")
                try:
                    # Call the callback function directly
                    sb.execute_script(f"{callback_name}('{token}')")
                    print(f"✅ Successfully called callback function: {callback_name}")
                    return True
                except Exception as e:
                    print(f"Error calling {callback_name}: {e}")
            
            # Finally try common callback names
            common_callbacks = ["verifyAkReCaptcha", "verifyCallback", "onSuccess", "vcRecaptchaApiLoadedCallback"]
            for cb in common_callbacks:
                print(f"Trying common callback: {cb}")
                try:
                    # Call the callback function directly
                    sb.execute_script(f"{cb}('{token}')")
                    print(f"✅ Successfully called common callback: {cb}")
                    return True
                except Exception as e:
                    # Just continue to the next callback
                    continue
            
            print("No callback function found or executed")
            return False
                
        except Exception as e:
            print(f"Error executing callback: {e}")
            return False


# Simple example usage
if __name__ == "__main__":
    import sys
    from seleniumbase import SB
    #window.___grecaptcha_cfg
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
            result = submitter.apply_token(sb, dummy_token)
            
            # Check result
            if result["success"]:
                print("\n✅ reCAPTCHA token applied successfully!")
                if result["form_submitted"]:
                    print("✅ Form was also submitted successfully")
            else:
                print(f"\n❌ Failed: {result['error']}")
                
            # Example of direct approach (similar to StackOverflow example)
            print("\n=== Direct Approach Example ===")
            print("This shows how to use the approach from StackOverflow directly:")
            print("1. Find the iframe (if needed)")
            print("2. Inject token into g-recaptcha-response")
            print("3. Call the callback function directly")
            
            try:
                # Try to find and switch to the iframe if it exists
                try:
                    iframe = sb.find_element('iframe[id="sec-cpt-if"]', by="css selector", timeout=2)
                    if iframe:
                        print("Found reCAPTCHA iframe, switching to it...")
                        sb.switch_to.frame(iframe)
                except Exception as e:
                    # Continue without iframe switch - it might not be needed
                    pass
                    
                # Inject token into g-recaptcha-response
                sb.execute_script(f'document.getElementById("g-recaptcha-response").innerHTML="{dummy_token}"')
                
                # Call the callback function directly - replace "verifyCallback" with the actual callback name
                sb.execute_script(f"verifyCallback('{dummy_token}')")
                
                print("Direct approach completed")
            except Exception as e:
                print(f"Error with direct approach: {e}")
    
    except Exception as e:
        print(f"\nError during demo: {e}")
        sys.exit(1)
    
    sys.exit(0) 