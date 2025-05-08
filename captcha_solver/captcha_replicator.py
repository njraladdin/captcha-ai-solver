import os
import time
import http.server
import socketserver
import threading
import socket
from urllib.parse import urlparse
from seleniumbase import SB
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import flask
import logging
from flask import Flask, send_from_directory
import requests
from . import hosts_manager  # Changed to relative import
import ssl
import tempfile
import subprocess
from OpenSSL import crypto


class CaptchaReplicator:
    """
    A class for creating and displaying a replicated reCAPTCHA v2 challenge.
    
    This class allows loading a reCAPTCHA widget using only the sitekey and page URL,
    similar to how services like 2captcha work. It creates a simple HTML page with
    the reCAPTCHA challenge and displays it in a browser.
    """
    
    def __init__(self, download_dir="tmp", server_port=8080):
        """
        Initialize the CaptchaReplicator.
        
        Args:
            download_dir (str, optional): Directory where HTML files will be saved.
                                         Defaults to 'tmp' directory.
            server_port (int, optional): Port to use for the local HTTP server.
                                        Defaults to 8080 (will be forwarded to 443 with admin rights).
        """
        self.download_dir = download_dir
        self.server_port = server_port
        self.server = None
        self.server_thread = None
        self.flask_app = None
        self.browser = None
        self.last_token = None  # Store the last solved token
        self.port_forwarding_enabled = False  # Track if port forwarding is active
        self.cert_file = None
        self.key_file = None
        
        # Ensure the download directory exists
        os.makedirs(self.download_dir, exist_ok=True)
    
    def _create_self_signed_cert(self, domain):
        """
        Create a self-signed SSL certificate for the domain.
        
        Args:
            domain (str): The domain to create the certificate for
            
        Returns:
            tuple: (cert_file_path, key_file_path) or (None, None) if failed
        """
        try:
            # Create a key pair
            k = crypto.PKey()
            k.generate_key(crypto.TYPE_RSA, 2048)
            
            # Create a self-signed cert
            cert = crypto.X509()
            cert.get_subject().C = "US"
            cert.get_subject().ST = "State"
            cert.get_subject().L = "City"
            cert.get_subject().O = "Organization"
            cert.get_subject().OU = "Organizational Unit"
            cert.get_subject().CN = domain
            
            # Add SubjectAltName for the domain and its www version
            san_extension = crypto.X509Extension(
                b"subjectAltName", 
                False, 
                f"DNS:{domain}, DNS:www.{domain}".encode()
            )
            cert.add_extensions([san_extension])
            
            cert.set_serial_number(int(time.time() * 1000))
            cert.gmtime_adj_notBefore(0)
            cert.gmtime_adj_notAfter(10*365*24*60*60)  # 10 years
            cert.set_issuer(cert.get_subject())
            cert.set_pubkey(k)
            cert.sign(k, 'sha256')
            
            # Write certificate and key to files in temp directory
            cert_file = tempfile.NamedTemporaryFile(delete=False, suffix='.crt')
            key_file = tempfile.NamedTemporaryFile(delete=False, suffix='.key')
            
            cert_file.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
            key_file.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k))
            
            cert_file.close()
            key_file.close()
            
            print(f"Created self-signed certificate for {domain}")
            
            return cert_file.name, key_file.name
            
        except Exception as e:
            print(f"Error creating self-signed certificate: {e}")
            return None, None
            
    def _cleanup_cert_files(self):
        """Clean up temporary certificate files."""
        try:
            if self.cert_file and os.path.exists(self.cert_file):
                os.unlink(self.cert_file)
                self.cert_file = None
            
            if self.key_file and os.path.exists(self.key_file):
                os.unlink(self.key_file)
                self.key_file = None
                
        except Exception as e:
            print(f"Error cleaning up certificate files: {e}")
    
    def create_captcha_html(self, website_key, website_url, is_invisible=False, data_s_value=None, api_domain="google.com"):
        """
        Create an HTML page with the reCAPTCHA widget for the given parameters.
        
        Args:
            website_key (str): reCAPTCHA sitekey
            website_url (str): The URL of the target website
            is_invisible (bool, optional): Whether to use invisible reCAPTCHA. Defaults to False.
            data_s_value (str, optional): The value of data-s parameter. Defaults to None.
            api_domain (str, optional): Domain used to load captcha (google.com or recaptcha.net). 
                                       Defaults to "google.com".
        
        Returns:
            str: Path to the created HTML file
        """
        # Generate a unique filename
        timestamp = int(time.time())
        html_file_path = os.path.join(self.download_dir, f"replicated_captcha_{timestamp}.html")
        
        # Create the HTML content
        # Add data-callback for invisible reCAPTCHA
        callback_attr = 'data-callback="onCaptchaSuccess"' if is_invisible else ''
        size_attr = 'data-size="invisible"' if is_invisible else ''
        data_s_attr = f'data-s="{data_s_value}"' if data_s_value else ''
        
        # Extract domain from original URL to display
        original_domain = urlparse(website_url).netloc if website_url else "unknown"
        
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Replicated reCAPTCHA Challenge</title>
    <script src="//www.{api_domain}/recaptcha/api.js" async defer></script>
    <style>
    body {{
        font-family: Arial, sans-serif;
        margin: 20px;
        line-height: 1.6;
    }}
    .container {{
        max-width: 800px;
        margin: 0 auto;
        padding: 20px;
        border: 1px solid #ddd;
        border-radius: 5px;
    }}
    .info {{
        background-color: #f9f9f9;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 20px;
    }}
    .captcha-container {{
        margin: 20px 0;
    }}
    .token-display {{
        background-color: #f5f5f5;
        padding: 10px;
        border: 1px solid #ddd;
        border-radius: 5px;
        word-break: break-all;
        margin: 10px 0;
        max-height: 100px;
        overflow-y: auto;
        font-family: monospace;
        font-size: 12px;
    }}
    button {{
        padding: 8px 15px;
        background-color: #4285f4;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        margin: 10px 0;
    }}
    button:hover {{
        background-color: #3367d6;
    }}
    .error {{
        color: red;
        margin: 10px 0;
    }}
    .note {{
        font-size: 0.9em;
        color: #666;
    }}
    </style>
    <script>
        function onCaptchaSuccess(token) {{
            document.getElementById('g-recaptcha-response-display').innerText = token;
            
            // For invisible reCAPTCHA, we need to reset after getting the token
            if ({str(is_invisible).lower()}) {{
                grecaptcha.reset();
            }}
        }}
        
        function copyToken() {{
            const tokenText = document.getElementById('g-recaptcha-response-display').innerText;
            if (!tokenText || tokenText === '[No token yet]') {{
                alert('No token available to copy');
                return;
            }}
            
            navigator.clipboard.writeText(tokenText)
                .then(() => {{
                    alert('Token copied to clipboard');
                }})
                .catch(err => {{
                    console.error('Failed to copy token: ', err);
                    alert('Failed to copy token');
                }});
        }}
        
        // For non-invisible reCAPTCHA, we need to monitor the textarea
        function monitorToken() {{
            if (!{str(is_invisible).lower()}) {{
                setInterval(() => {{
                    const token = document.querySelector('textarea[name="g-recaptcha-response"]');
                    if (token && token.value) {{
                        document.getElementById('g-recaptcha-response-display').innerText = token.value;
                    }}
                }}, 1000);
            }}
        }}
        
        // Check for reCAPTCHA errors
        function checkForErrors() {{
            // Look for error messages in the DOM
            const errorElements = document.querySelectorAll('.rc-anchor-error-msg');
            if (errorElements.length > 0) {{
                const errorMessages = Array.from(errorElements).map(el => el.textContent).join(' ');
                document.getElementById('error-message').textContent = 'reCAPTCHA Error: ' + errorMessages;
            }}
            
            setTimeout(checkForErrors, 2000); // Check every 2 seconds
        }}
        
        window.onload = function() {{
            monitorToken();
            checkForErrors();
        }}
    </script>
</head>
<body>
    <div class="container">
        <h2>Replicated reCAPTCHA Challenge</h2>
        <div class="info">
            <p><strong>Original Website:</strong> {original_domain}</p>
            <p><strong>Website URL:</strong> {website_url}</p>
            <p><strong>Site Key:</strong> {website_key}</p>
            <p><strong>Type:</strong> {'Invisible' if is_invisible else 'Checkbox'} reCAPTCHA v2</p>
        </div>
        
        <div class="captcha-container">
            <div class="g-recaptcha" 
                data-sitekey="{website_key}" 
                {size_attr} 
                {callback_attr}
                {data_s_attr}>
            </div>
        </div>
        
        <div id="error-message" class="error"></div>
        
        {f'<button onclick="grecaptcha.execute()">Execute Invisible reCAPTCHA</button>' if is_invisible else ''}
        
        <div>
            <h3>reCAPTCHA Token:</h3>
            <div class="token-display" id="g-recaptcha-response-display">
                [No token yet]
            </div>
            <button onclick="copyToken()">Copy Token</button>
            <p class="note">Note: If you see "Invalid domain for site key" error, the site key is restricted to be used only on the original domain.</p>
        </div>
    </div>
</body>
</html>
"""
        
        # Write the HTML content to a file
        with open(html_file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"Created replicated reCAPTCHA HTML page at: {html_file_path}")
        return html_file_path
    
    def _get_free_port(self):
        """Get a free port on the system by letting OS assign one, then closing it."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[1]
    
    def start_http_server(self, domain=None, use_ssl=True):
        """
        Start a Flask HTTP server in a separate thread.
        If admin privileges are available, set up port forwarding to port 443 for HTTPS.
        
        Args:
            domain (str, optional): Domain to create SSL certificate for
            use_ssl (bool, optional): Whether to use SSL (HTTPS). Defaults to True.
            
        Returns:
            int: The port number on which the server is running.
        """
        # Find an available port to use
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('0.0.0.0', self.server_port))
        except OSError:
            print(f"Port {self.server_port} is in use. Finding an available port...")
            self.server_port = self._get_free_port()
        
        ssl_context = None
        
        # If using SSL and domain is provided, create self-signed certificate
        if use_ssl and domain:
            print(f"Setting up SSL with self-signed certificate for {domain}...")
            self.cert_file, self.key_file = self._create_self_signed_cert(domain)
            
            if self.cert_file and self.key_file:
                ssl_context = (self.cert_file, self.key_file)
                target_port = 443  # HTTPS port
            else:
                print("Failed to create SSL certificate. Falling back to HTTP.")
                use_ssl = False
                target_port = 80  # HTTP port
        else:
            target_port = 80  # Default HTTP port if not using SSL
        
        # If we have admin rights, try to set up port forwarding
        if hosts_manager.is_admin():
            print(f"Attempting to set up port forwarding from port {target_port} to hide port number in URLs...")
            self.port_forwarding_enabled = hosts_manager.setup_port_forwarding(self.server_port, target_port)
        else:
            print("No admin privileges. Port numbers will be visible in URLs.")
            self.port_forwarding_enabled = False
        
        # Ensure absolute path for download directory
        abs_download_dir = os.path.abspath(self.download_dir)
        print(f"Serving files from: {abs_download_dir}")
        
        # Disable Flask logging to avoid cluttering the console
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        
        # Create a Flask app
        self.flask_app = Flask(__name__)
        
        # Define route for root to serve the HTML file with the original path structure
        @self.flask_app.route('/', defaults={'path': ''})
        @self.flask_app.route('/<path:path>')
        def catch_all(path):
            # Check if the path is a specific file in download directory
            file_path = os.path.join(abs_download_dir, path)
            if os.path.isfile(file_path):
                return send_from_directory(abs_download_dir, path)
            
            # Otherwise find the most recent HTML file and serve it
            html_files = [f for f in os.listdir(abs_download_dir) if f.endswith('.html')]
            if html_files:
                # Sort by creation time, newest first
                latest_html = sorted(html_files, key=lambda f: os.path.getctime(os.path.join(abs_download_dir, f)), reverse=True)[0]
                return send_from_directory(abs_download_dir, latest_html)
            
            # If no HTML files found
            return "No HTML files available"
        
        # Add a shutdown route for clean termination
        @self.flask_app.route('/shutdown')
        def shutdown():
            func = flask.request.environ.get('werkzeug.server.shutdown')
            if func is None:
                raise RuntimeError('Not running with the Werkzeug Server')
            func()
            return 'Server shutting down...'
        
        # Start the server in a separate thread
        print(f"Starting {'HTTPS' if use_ssl else 'HTTP'} server on port {self.server_port}...")
        self.server_thread = threading.Thread(
            target=lambda: self.flask_app.run(
                host='0.0.0.0',  # Bind to all interfaces instead of just localhost
                port=self.server_port, 
                debug=False, 
                use_reloader=False,
                ssl_context=ssl_context
            )
        )
        self.server_thread.daemon = True  # So the thread will exit when the main program exits
        self.server_thread.start()
        
        # Brief pause to ensure server starts up
        time.sleep(1)
        
        return self.server_port
    
    def stop_http_server(self):
        """Stop the HTTP server if it's running and clean up port forwarding if enabled."""
        # Clean up certificate files
        self._cleanup_cert_files()
        
        # Remove port forwarding if it was set up
        if self.port_forwarding_enabled and hosts_manager.is_admin():
            hosts_manager.remove_port_forwarding()
            self.port_forwarding_enabled = False
        
        if self.server_thread and self.flask_app:
            print("Stopping HTTP server...")
            # Use a more reliable way to shut down the Flask server
            try:
                # Create a request to shutdown the server
                requests.get(f"http://127.0.0.1:{self.server_port}/shutdown", verify=False)
            except:
                pass  # If it fails, the daemon thread will be killed on program exit anyway
            
            self.server_thread = None
            self.flask_app = None
    
    def replicate_captcha(self, website_key, website_url, browser, is_invisible=False, data_s_value=None, 
                          is_enterprise=False, api_domain="google.com", user_agent=None, 
                          cookies=None, observation_time=5, bypass_domain_check=False, use_ssl=True):
        """
        Create and display a replicated reCAPTCHA challenge.
        
        Args:
            website_key (str): reCAPTCHA sitekey
            website_url (str): The URL of the target website
            browser (SB): SeleniumBase browser instance to use
            is_invisible (bool, optional): Whether to use invisible reCAPTCHA. Defaults to False.
            data_s_value (str, optional): The value of data-s parameter. Defaults to None.
            is_enterprise (bool, optional): Whether to use Enterprise reCAPTCHA. Defaults to False.
            api_domain (str, optional): Domain to load captcha from. Defaults to "google.com".
            user_agent (str, optional): User agent to use. Defaults to None.
            cookies (list, optional): Cookies to set. Defaults to None.
            observation_time (int, optional): Time to keep browser open in seconds. Defaults to 5.
                                           Set to 0 to keep open until closed manually or token received.
            bypass_domain_check (bool, optional): Whether to bypass domain check by adding to hosts file. Defaults to False.
            use_ssl (bool, optional): Whether to use SSL (HTTPS). Defaults to True.
        
        Returns:
            tuple: (html_path, token)
        """
        sb = None
        domain_added = False
        original_domain = None
        original_scheme = None
        
        try:
            # Reset the last token
            self.last_token = None
            
            # Extract the original domain for reference only
            if website_url:
                parsed_url = urlparse(website_url)
                original_domain = parsed_url.netloc
                original_scheme = parsed_url.scheme or "http"  # Get the original protocol (http or https)
                
                # If bypass_domain_check is enabled, add the domain to hosts file
                if bypass_domain_check and original_domain:
                    print(f"Attempting to add domain '{original_domain}' to hosts file for bypass...")
                    # Check if we have admin rights
                    if not hosts_manager.is_admin():
                        print("Administrator privileges required. Requesting elevation...")
                        hosts_manager.restart_with_admin()
                    # Add domain to hosts file
                    domain_added = hosts_manager.add_to_hosts(original_domain)
                    if domain_added:
                        print(f"Domain '{original_domain}' added to hosts file successfully.")
                    else:
                        print(f"Failed to add domain '{original_domain}' to hosts file.")
            
            # Select appropriate API domain for Enterprise reCAPTCHA
            if is_enterprise and not api_domain.endswith('enterprise'):
                if api_domain == "google.com":
                    api_domain = "www.google.com/recaptcha/enterprise"
                elif api_domain == "recaptcha.net":
                    api_domain = "recaptcha.net/recaptcha/enterprise"
            
            # Create HTML file with appropriate challenge type
            html_path = self.create_captcha_html(
                website_key, 
                website_url, 
                is_invisible=is_invisible,
                data_s_value=data_s_value,
                api_domain=api_domain
            )
            
            # Start HTTP server with SSL if requested
            server_port = self.start_http_server(domain=original_domain, use_ssl=use_ssl)
            if not server_port:
                print("Failed to start HTTP server")
                return None, None
            
            # Form URL to the HTML file
            file_basename = os.path.basename(html_path)
            
            # If domain bypass is enabled and domain was added successfully, use the original domain
            # instead of localhost in the URL to pass reCAPTCHA domain check
            if bypass_domain_check and domain_added and original_domain:
                # Extract path and query from original URL to mimic the full original URL structure
                original_path = parsed_url.path
                original_query = parsed_url.query
                original_fragment = parsed_url.fragment
                
                # Use the original domain with the exact original path
                if self.port_forwarding_enabled:
                    # If port forwarding is active, we can use clean URLs without port numbers
                    # Use HTTPS if SSL certificate is set up
                    protocol = "https" if use_ssl else "http"
                    local_file_url = f"{protocol}://{original_domain}{original_path}"
                    if original_query:
                        local_file_url += f"?{original_query}"
                    if original_fragment:
                        local_file_url += f"#{original_fragment}"
                    print(f"Using clean spoofed domain URL: {local_file_url}")
                else:
                    # Need to include port which makes the URL look different
                    protocol = "https" if use_ssl else "http"
                    local_file_url = f"{protocol}://{original_domain}:{self.server_port}{original_path}"
                    if original_query:
                        local_file_url += f"?{original_query}"
                    if original_fragment:
                        local_file_url += f"#{original_fragment}"
                    print(f"Using spoofed domain URL (with port): {local_file_url}")
            else:
                protocol = "https" if use_ssl else "http"
                local_file_url = f"{protocol}://localhost:{self.server_port}/{file_basename}"
                print(f"Using localhost URL: {local_file_url}")
            
            # Store the browser reference
            self.browser = browser
            sb = browser
            
            # Add option to ignore SSL certificate errors
            if use_ssl:
                sb.driver.execute_cdp_cmd("Security.setIgnoreCertificateErrors", {"ignore": True})
            
            result = self._handle_captcha_interaction(
                sb, local_file_url, user_agent, cookies, 
                observation_time
            )
            
            # Return the results
            return html_path, self.last_token
        
        except Exception as e:
            print(f"Error in replicate_captcha: {e}")
            import traceback
            traceback.print_exc()
            self.stop_http_server()
            return None, None
        finally:
            # Clean up hosts file if we added a domain
            if domain_added and original_domain:
                print(f"Removing domain '{original_domain}' from hosts file...")
                hosts_manager.remove_from_hosts(original_domain)
                print(f"Domain '{original_domain}' removed from hosts file.")
    
    def _handle_captcha_interaction(self, sb, local_file_url, user_agent=None, 
                                   cookies=None, observation_time=5):
        """
        Handle the interaction with the captcha in the browser.
        
        Args:
            sb: SeleniumBase browser instance
            local_file_url: URL to the captcha HTML file
            user_agent: User agent to set (optional)
            cookies: Cookies to set (optional)
            observation_time: Time to keep browser open
            
        Returns:
            bool: Success status
        """
        try:
            # Navigate to the HTML page
            sb.open(local_file_url)
            
            # Set user agent if specified
            if user_agent:
                sb.execute_script(f"Object.defineProperty(navigator, 'userAgent', " + 
                                 f"{{get: function() {{return '{user_agent}'}}}});")
            
            # Set cookies if specified
            if cookies:
                for cookie in cookies:
                    sb.add_cookie(cookie)
            
            # Check if reCAPTCHA loads properly or has domain error
            try:
                # Wait for either the reCAPTCHA iframe or error message
                sb.wait_for_element_present("iframe[src*='recaptcha']", timeout=10)
                print("reCAPTCHA iframe loaded successfully")
                
            except (NoSuchElementException, TimeoutException):
                try:
                    # Check for domain error message
                    error_element = sb.find_element("div#error-message")
                    if error_element:
                        print(f"Error: {error_element.text}")
                        print("This may be due to domain restrictions on the reCAPTCHA site key.")
                except:
                    print("reCAPTCHA failed to load but no specific error was found")
            
            # Start a thread to monitor for token updates
            self._start_token_monitor(sb)
                
            if observation_time > 0:
                # Keep the window open for the specified time
                print(f"Keeping browser open for {observation_time} seconds...")
                sb.sleep(observation_time)
            else:
                # Keep the window open until manually closed or token is received
                print("Browser will remain open until manually closed or token is received...")
                while True:
                    # Check if browser is still open
                    try:
                        # Get the current URL to check if browser is still open
                        current_url = sb.get_current_url()
                        
                        # Check if we have a token
                        if self.last_token:
                            token = self.last_token
                            print(f"Token received, length: {len(token)}")
                            print("You can close the browser window now, or it will close automatically in 5 seconds...")
                            sb.sleep(5)
                            break
                        
                        # Brief pause to avoid high CPU usage
                        sb.sleep(1)
                    except:
                        # Browser was closed by user
                        print("Browser was closed by user")
                        break
            
            return True
            
        except Exception as e:
            print(f"Error in _handle_captcha_interaction: {e}")
            return False
    
    def _start_token_monitor(self, sb):
        """
        Start a background thread to monitor for token updates.
        
        Args:
            sb: SeleniumBase browser instance
        """
        def monitor():
            try:
                # Check every second for token updates
                for _ in range(600):  # Monitor for up to 10 minutes
                    try:
                        # Get token from the display element
                        token = sb.execute_script("""
                            const display = document.getElementById('g-recaptcha-response-display');
                            if (display && display.innerText && display.innerText !== '[No token yet]') {
                                return display.innerText;
                            }
                            return null;
                        """)
                        
                        if token and token != '[No token yet]':
                            self.last_token = token
                            print(f"Token captured (length: {len(token)})")
                            break
                            
                        # Also check the textarea directly
                        textarea_token = sb.execute_script("""
                            const textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
                            if (textarea && textarea.value) {
                                return textarea.value;
                            }
                            return null;
                        """)
                        
                        if textarea_token:
                            self.last_token = textarea_token
                            print(f"Token captured from textarea (length: {len(textarea_token)})")
                            break
                            
                    except Exception as e:
                        print(f"Error in token monitor: {e}")
                        break
                        
                    # Sleep for 1 second before checking again
                    time.sleep(1)
            except:
                # Handle any exceptions in the monitor thread
                pass
                
        # Start the monitor in a background thread
        threading.Thread(target=monitor, daemon=True).start()
        
    def get_last_token(self):
        """
        Get the last solved reCAPTCHA token.
        
        Returns:
            str: The last solved token, or None if no token has been captured
        """
        return self.last_token


# Simple example usage
if __name__ == "__main__":
    try:
        # Create an instance of CaptchaReplicator
        # Use absolute path for download directory to avoid any issues
        download_dir = os.path.abspath("tmp")
        print(f"Using download directory: {download_dir}")
        
        captcha_replicator = CaptchaReplicator(download_dir=download_dir)
        
        # Example reCAPTCHA parameters from Google's demo page
        website_key = "6LdnlkAUAAAAAL2zK68LwI1rDeclqZFiYr9jTSOX"
        website_url = "https://lnnte-dncl.gc.ca/en/Consumer/Check-your-registration/#!/"
        # website_key = "6Le-wvkSAAAAAPBMRTvw0Q4Muexq9bi0DJwx_mJ-"
        # website_url = "https://www.google.com/recaptcha/api2/demo"
        
        print("\n=== Testing CaptchaReplicator ===")
        print(f"Opening replicated reCAPTCHA with sitekey: {website_key}")
        print("Browser will stay open for 100 seconds by default (or until manually closed).")
        
        # Create browser directly using SB, same as in captcha_solver.py
        print("\n--- Step 1: Creating browser instance ---")
        
        # Create and use a SeleniumBase browser with a context manager
        with SB(uc=True, headless=False) as browser:
            print(f"Browser instance created: {type(browser)}")
            
            # Replicate the captcha with the provided browser
            html_path, token = captcha_replicator.replicate_captcha(
                website_key=website_key,
                website_url=website_url,
                browser=browser,
                observation_time=100,  # Keep open longer for demonstration
                bypass_domain_check=True,  # Enable hosts file bypass
                use_ssl=True  # Use SSL with self-signed certificate
            )
            
            if not html_path:
                print("Failed to start reCAPTCHA session. See error messages above.")
                captcha_replicator.stop_http_server()
                exit(1)
            
            # Display token info if available
            if token:
                print("\n=== CAPTCHA TOKEN OBTAINED ===")
                print(f"Token (first 30 chars): {token[:30]}...")
                print(f"Token length: {len(token)}")
            else:
                print("\n=== NO TOKEN OBTAINED ===")
                print("The CAPTCHA was not solved or token was not captured.")
                
            # This point is reached only after browser is closed or timeout
            print("\n=== Completed replicated CAPTCHA session ===")
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user. Exiting...")
        # Ensure server is stopped
        captcha_replicator.stop_http_server()
    except Exception as e:
        print(f"\nUnexpected error during test: {e}")
        # Ensure server is stopped
        captcha_replicator.stop_http_server()
    finally:
        # Ensure any lingering servers are stopped
        try:
            captcha_replicator.stop_http_server()
        except:
            pass 