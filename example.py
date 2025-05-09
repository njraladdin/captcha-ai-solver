import os
import time
import argparse
from dotenv import load_dotenv
from captcha_solver import solve_captcha

# Load environment variables
load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="Captcha AI Solver Example")
    parser.add_argument("--website", default="https://2captcha.com/demo/recaptcha-v2", 
                        help="URL of the website with captcha")
    parser.add_argument("--key", default="6LfD3PIbAAAAAJs_eEHvoOl75_83eXSqpPSRFJ_u", 
                        help="reCAPTCHA site key")
    parser.add_argument("--invisible", action="store_true", help="Is invisible captcha")
    parser.add_argument("--enterprise", action="store_true", help="Is enterprise captcha")
    args = parser.parse_args()

    # Get API key from environment
    wit_api_key = os.getenv("WIT_API_KEY")
    if not wit_api_key:
        print("WARNING: WIT_API_KEY not found in environment. Audio challenges may fail.")

    # Prepare captcha parameters
    captcha_params = {
        "website_url": args.website,
        "website_key": args.key,
        "is_invisible": args.invisible,
        "is_enterprise": args.enterprise
    }

    # Configure solver
    solver_config = {
        "wit_api_key": wit_api_key
                }

    print("Captcha AI Solver Example")
    print(f"Website URL: {captcha_params['website_url']}")
    print(f"Website Key: {captcha_params['website_key']}")
    print(f"Is Invisible: {captcha_params['is_invisible']}")
    print(f"Is Enterprise: {captcha_params['is_enterprise']}")
    print("\nSolving captcha...")
    
    start_time = time.time()
    
    # Solve the captcha
    token = solve_captcha(
        captcha_type="recaptcha_v2",
        captcha_params=captcha_params,
        solver_config=solver_config
    )
    
    end_time = time.time()
    
    if token:
        print(f"\n✅ Captcha solved successfully!")
        print(f"Time taken: {end_time - start_time:.2f} seconds")
        print(f"Token (first 30 chars): {token[:30]}...")
        
        # Example of how to use the token
        print("\nExample JavaScript to use this token:")
        print(f'document.querySelector("[name=g-recaptcha-response]").innerHTML = "{token}";')
    else:
        print("\n❌ Failed to solve captcha")
        print(f"Time taken: {end_time - start_time:.2f} seconds")

if __name__ == "__main__":
    main() 