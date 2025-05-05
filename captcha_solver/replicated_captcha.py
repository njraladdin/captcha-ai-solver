import os
import time
import http.server
import socketserver
import threading
import socket
from urllib.parse import urlparse
from seleniumbase import SB
from selenium.common.exceptions import NoSuchElementException, TimeoutException


class ReplicatedCaptcha:
    """
    A class for creating and displaying a replicated reCAPTCHA v2 challenge.
    
    This class allows loading a reCAPTCHA widget using only the sitekey and page URL,
    similar to how services like 2captcha work. It creates a simple HTML page with
    the reCAPTCHA challenge and displays it in a browser.
    """
    
    def __init__(self, download_dir="tmp", server_port=8000):
        """
        Initialize the ReplicatedCaptcha.
        
        Args:
            download_dir (str, optional): Directory where HTML files will be saved.
                                         Defaults to 'tmp' directory.
            server_port (int, optional): Port to use for the local HTTP server.
                                        Defaults to 8000.
        """
        self.download_dir = download_dir
        self.server_port = server_port
        self.server = None
        self.server_thread = None
        self.browser = None
        
        # Ensure the download directory exists
        os.makedirs(self.download_dir, exist_ok=True)
    
    def initialize_browser(self, uc=True, headless=False, **kwargs):
        """
        Initialize a SeleniumBase browser instance.
        
        Args:
            uc (bool, optional): Use undetected-chromedriver mode. Defaults to True.
            headless (bool, optional): Run browser in headless mode. Defaults to False.
            **kwargs: Additional keyword arguments to pass to SeleniumBase constructor.
            
        Returns:
            SB: The initialized SeleniumBase browser class for use with 'with' statement.
        """
        print("Initializing SeleniumBase browser...")
        return SB(uc=uc, headless=headless, **kwargs)
    
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
    <script src="https://{api_domain}/recaptcha/api.js" async defer></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            text-align: center;
            margin: 50px;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            border: 1px solid #e0e0e0;
            border-radius: 5px;
        }}
        .info {{
            margin-bottom: 20px;
            color: #666;
            font-size: 14px;
        }}
        .captcha-container {{
            display: flex;
            justify-content: center;
            margin: 20px 0;
        }}
        .token-display {{
            margin-top: 20px;
            padding: 10px;
            background-color: #f7f7f7;
            border: 1px solid #ddd;
            border-radius: 3px;
            text-align: left;
            word-break: break-all;
        }}
        button {{
            padding: 8px 16px;
            background-color: #4285f4;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }}
        button:hover {{
            background-color: #357ae8;
        }}
        .note {{
            margin-top: 10px;
            font-size: 12px;
            color: #999;
        }}
        .error {{
            color: #e53935;
            margin-top: 10px;
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
    
    def start_http_server(self):
        """Start a simple HTTP server in a separate thread."""
        # Use a free port if the specified one is taken
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', self.server_port))
        except OSError:
            print(f"Port {self.server_port} is in use. Finding an available port...")
            self.server_port = self._get_free_port()
        
        # Create a handler and server
        handler = http.server.SimpleHTTPRequestHandler
        self.server = socketserver.TCPServer(("", self.server_port), handler)
        
        # Change the working directory to the download directory
        os.chdir(self.download_dir)
        
        # Start the server in a separate thread
        print(f"Starting HTTP server on port {self.server_port}...")
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True  # So the thread will exit when the main program exits
        self.server_thread.start()
        
        return self.server_port
    
    def stop_http_server(self):
        """Stop the HTTP server if it's running."""
        if self.server:
            print("Stopping HTTP server...")
            self.server.shutdown()
            self.server.server_close()
            self.server = None
            self.server_thread = None
    
    def run_replicated_captcha(self, website_key, website_url, is_invisible=False, data_s_value=None, 
                              api_domain="google.com", user_agent=None, cookies=None, observation_time=100):
        """
        Create and open a replicated reCAPTCHA challenge in a browser.
        
        Args:
            website_key (str): reCAPTCHA sitekey
            website_url (str): The URL of the target website
            is_invisible (bool, optional): Whether to use invisible reCAPTCHA. Defaults to False.
            data_s_value (str, optional): The value of data-s parameter. Defaults to None.
            api_domain (str, optional): Domain used to load captcha (google.com or recaptcha.net). 
                                       Defaults to "google.com".
            user_agent (str, optional): User-Agent to use for the browser. Defaults to None.
            cookies (str, optional): Cookies to set in the browser. Format: "key1=val1; key2=val2". 
                                    Defaults to None.
            observation_time (int, optional): Seconds to keep browser open. 0 means stay open until manually closed.
                                           Defaults to 100.
        
        Returns:
            tuple: (html_file_path, browser_instance)
                - html_file_path: Path to the created HTML file
                - browser_instance: The SeleniumBase browser instance (if still open)
        """
        print(f"\n--- Starting Replicated reCAPTCHA for sitekey: {website_key} ---")
        
        # Create the HTML file with the reCAPTCHA
        html_file_path = self.create_captcha_html(
            website_key=website_key,
            website_url=website_url,
            is_invisible=is_invisible,
            data_s_value=data_s_value,
            api_domain=api_domain
        )
        
        # Start the HTTP server to serve the HTML file
        server_port = self.start_http_server()
        
        # Extract just the filename from the full path
        html_filename = os.path.basename(html_file_path)
        server_url = f"http://localhost:{server_port}/{html_filename}"
        
        # Initialize browser
        sb_instance = self.initialize_browser(uc=True)
        browser = None
        
        with sb_instance as sb:
            try:
                # Set user agent if provided
                if user_agent:
                    print(f"Setting user agent: {user_agent}")
                    sb.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": user_agent})
                
                # Navigate to the HTML file through the local server
                print(f"Opening replicated reCAPTCHA page via HTTP server: {server_url}")
                sb.open(server_url)
                
                # Set cookies for the target website if provided
                if cookies and website_url:
                    try:
                        print(f"Setting cookies for domain: {website_url}")
                        # Extract domain from website_url
                        domain = urlparse(website_url).netloc
                        
                        # Parse and set cookies
                        cookie_pairs = cookies.split(';')
                        for pair in cookie_pairs:
                            if '=' in pair:
                                name, value = pair.strip().split('=', 1)
                                sb.add_cookie({'name': name, 'value': value, 'domain': domain})
                    except Exception as cookie_err:
                        print(f"Warning: Could not set cookies: {cookie_err}")
                
                # Wait for reCAPTCHA to load
                print("Waiting for reCAPTCHA to load...")
                sb.wait_for_element_present('iframe[src*="api2/anchor"]', timeout=10)
                print("reCAPTCHA loaded successfully.")
                
                # If we need to keep the browser open
                if observation_time > 0:
                    print(f"Observing for {observation_time} seconds...")
                    sb.sleep(observation_time)
                    browser = None
                else:
                    print("Keeping browser open. Please close manually when finished.")
                    browser = sb
                    return html_file_path, browser  # Return without closing the browser
                
            except (NoSuchElementException, TimeoutException) as e:
                print(f"Error loading reCAPTCHA: {e}")
                sb.save_screenshot(os.path.join(self.download_dir, "replicated_captcha_error.png"))
                browser = None
                
            except Exception as e:
                print(f"Unexpected error: {e}")
                sb.save_screenshot(os.path.join(self.download_dir, "replicated_captcha_error.png"))
                browser = None
        
        # Stop the server
        self.stop_http_server()
        return html_file_path, browser


# Simple example usage
if __name__ == "__main__":
    # Create an instance of ReplicatedCaptcha
    replicated_captcha = ReplicatedCaptcha(download_dir="tmp")
    
    # Example reCAPTCHA parameters from Google's demo page
    website_key = "6Le-wvkSAAAAAPBMRTvw0Q4Muexq9bi0DJwx_mJ-"
    website_url = "https://www.google.com/recaptcha/api2/demo"
    
    print("\n=== Testing ReplicatedCaptcha ===")
    print(f"Opening replicated reCAPTCHA with sitekey: {website_key}")
    print("Browser will stay open for 100 seconds by default (or until manually closed).")
    
    try:
        # Run the replicated captcha
        html_path, browser = replicated_captcha.run_replicated_captcha(
            website_key=website_key,
            website_url=website_url
        )
        
        # This point is reached only after browser is closed or timeout
        print("\n=== Completed replicated CAPTCHA session ===")
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user. Exiting...")
        # Ensure server is stopped
        replicated_captcha.stop_http_server()
    except Exception as e:
        print(f"\nUnexpected error during test: {e}")
        # Ensure server is stopped
        replicated_captcha.stop_http_server() 