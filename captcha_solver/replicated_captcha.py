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
        self.flask_app = None
        self.browser = None
        self.last_token = None  # Store the last solved token
        
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
        """
        Start a Flask HTTP server in a separate thread.
        Returns the port number on which the server is running.
        """
        # Use a free port if the specified one is taken
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', self.server_port))
        except OSError:
            print(f"Port {self.server_port} is in use. Finding an available port...")
            self.server_port = self._get_free_port()
        
        # Ensure absolute path for download directory
        abs_download_dir = os.path.abspath(self.download_dir)
        print(f"Serving files from: {abs_download_dir}")
        
        # Disable Flask logging to avoid cluttering the console
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        
        # Create a Flask app
        self.flask_app = Flask(__name__)
        
        # Define route for root to list files (optional)
        @self.flask_app.route('/')
        def index():
            files = os.listdir(abs_download_dir)
            file_links = ['<li><a href="/{0}">{0}</a></li>'.format(f) for f in files]
            return f"""
            <html>
                <head><title>Replicated CAPTCHA Server</title></head>
                <body>
                    <h1>Available CAPTCHA Files</h1>
                    <ul>{''.join(file_links)}</ul>
                </body>
            </html>
            """
            
        # Define route to serve files from the download directory
        @self.flask_app.route('/<path:filename>')
        def serve_file(filename):
            return send_from_directory(abs_download_dir, filename)
        
        # Add a shutdown route for clean termination
        @self.flask_app.route('/shutdown')
        def shutdown():
            func = flask.request.environ.get('werkzeug.server.shutdown')
            if func is None:
                raise RuntimeError('Not running with the Werkzeug Server')
            func()
            return 'Server shutting down...'
        
        # Start the server in a separate thread
        print(f"Starting HTTP server on port {self.server_port}...")
        self.server_thread = threading.Thread(
            target=lambda: self.flask_app.run(
                host='localhost', 
                port=self.server_port, 
                debug=False, 
                use_reloader=False
            )
        )
        self.server_thread.daemon = True  # So the thread will exit when the main program exits
        self.server_thread.start()
        
        # Brief pause to ensure server starts up
        time.sleep(1)
        
        return self.server_port
    
    def stop_http_server(self):
        """Stop the HTTP server if it's running."""
        if self.server_thread and self.flask_app:
            print("Stopping HTTP server...")
            # Use a more reliable way to shut down the Flask server
            try:
                # Create a request to shutdown the server
                requests.get(f"http://localhost:{self.server_port}/shutdown")
            except:
                pass  # If it fails, the daemon thread will be killed on program exit anyway
            
            self.server_thread = None
            self.flask_app = None
    
    def run_replicated_captcha(self, website_key, website_url, is_invisible=False, data_s_value=None, 
                              is_enterprise=False, api_domain="google.com", user_agent=None, 
                              cookies=None, observation_time=100):
        """
        Create and display a replicated reCAPTCHA challenge.
        
        Args:
            website_key (str): reCAPTCHA sitekey
            website_url (str): The URL of the target website
            is_invisible (bool, optional): Whether to use invisible reCAPTCHA. Defaults to False.
            data_s_value (str, optional): The value of data-s parameter. Defaults to None.
            is_enterprise (bool, optional): Whether to use Enterprise reCAPTCHA. Defaults to False.
            api_domain (str, optional): Domain to load captcha from. Defaults to "google.com".
            user_agent (str, optional): User agent to use. Defaults to None.
            cookies (list, optional): Cookies to set. Defaults to None.
            observation_time (int, optional): Time to keep browser open. Defaults to 100.
                                           Set to 0 to keep open until closed manually.
        
        Returns:
            tuple: (Path to the HTML file, browser instance)
        """
        try:
            # Reset the last token
            self.last_token = None
            
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
            
            # Start HTTP server
            server_port = self.start_http_server()
            if not server_port:
                print("Failed to start HTTP server")
                return None, None
            
            # Form URL to the HTML file (with proper http:// prefix)
            file_basename = os.path.basename(html_path)
            local_file_url = f"http://localhost:{server_port}/{file_basename}"
            print(f"Replicated reCAPTCHA URL: {local_file_url}")
            
            # Initialize browser
            browser = self.initialize_browser(uc=True)
            self.browser = browser
            
            with browser as sb:
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
                    # Keep the window open until manually closed
                    print("Browser will remain open until manually closed or token is received...")
                    while True:
                        # Check if browser is still open
                        try:
                            # Get the current URL to check if browser is still open
                            current_url = sb.get_current_url()
                            
                            # Check if we have a token
                            if self.last_token:
                                print(f"Token received, length: {len(self.last_token)}")
                                print("You can close the browser window now, or it will close automatically in 5 seconds...")
                                sb.sleep(5)
                                break
                            
                            # Brief pause to avoid high CPU usage
                            sb.sleep(1)
                        except:
                            # Browser was closed by user
                            print("Browser was closed by user")
                            break
                
                # Optionally, you can add code here to automatically solve the CAPTCHA
                # or to extract the token once solved
                
                return html_path, browser
        
        except Exception as e:
            print(f"Error in run_replicated_captcha: {e}")
            self.stop_http_server()
            return None, None

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
        # Create an instance of ReplicatedCaptcha
        # Use absolute path for download directory to avoid any issues
        download_dir = os.path.abspath("tmp")
        print(f"Using download directory: {download_dir}")
        
        replicated_captcha = ReplicatedCaptcha(download_dir=download_dir)
        
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
            
            if not html_path or not browser:
                print("Failed to start reCAPTCHA session. See error messages above.")
                replicated_captcha.stop_http_server()
                exit(1)
                
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
    finally:
        # Ensure any lingering servers are stopped
        try:
            replicated_captcha.stop_http_server()
        except:
            pass 