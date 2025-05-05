import os
import sys
import time

# Add the parent directory to the path so we can import the captcha_solver module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from captcha_solver import CaptchaSolver

def test_solve_google_demo_captcha():
    """
    Integration test that attempts to solve a real captcha from the Google demo site.
    This test will:
    1. Initialize the CaptchaSolver with your Wit.ai API key
    2. Solve a real captcha from the Google demo site
    3. Print the results
    
    Note: This requires a valid Wit.ai API key to work properly
    """
    print("\n=== Integration Test: Solving Google Demo Captcha ===")
    
    # Get Wit.ai API key from environment variable or use a default for testing
    # In a real scenario, you should set this environment variable with your actual API key
    wit_api_key = os.environ.get("WIT_API_KEY", "YOUR_WIT_API_KEY_HERE")
    
    # Initialize the solver
    solver = CaptchaSolver(wit_api_key=wit_api_key)
    
    # Test parameters from the Google reCAPTCHA demo site
    captcha_params = {
        "website_key": "6Le-wvkSAAAAAPBMRTvw0Q4Muexq9bi0DJwx_mJ-",
        "website_url": "https://www.google.com/recaptcha/api2/demo",
        "is_invisible": False,
        "is_enterprise": False,
        "data_s_value": None  # This parameter is usually None for standard reCAPTCHA
    }
    
    # Start timer
    start_time = time.time()
    
    # Attempt to solve the captcha
    print("\nAttempting to solve Google demo captcha...")
    token, success = solver.solve(captcha_params)
    
    # End timer
    end_time = time.time()
    duration = end_time - start_time
    
    # Print results
    print("\n=== Results ===")
    print(f"Success: {success}")
    if token:
        print(f"Token received (first 30 chars): {token[:30]}...")
        print(f"Token length: {len(token)} characters")
    else:
        print("No token received")
    
    print(f"\nSolving took {duration:.2f} seconds")
    
    return success, token

if __name__ == "__main__":
    # Run the integration test
    success, token = test_solve_google_demo_captcha()
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1) 