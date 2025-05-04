# reCAPTCHA Solver

A Python-based solution for automatically solving reCAPTCHA challenges using audio transcription.

## Features

- Solves Google reCAPTCHA v2 challenges using audio transcription
- Handles automatic detection of when challenges are required
- Efficiently processes audio with Wit.ai speech recognition API
- Manages retry logic for multiple audio challenges if needed
- Detects various error cases (blocking, multiple solutions required)
- **Auto-manages SeleniumBase connection states** (CDP mode and WebDriver reconnection)

## Requirements

- Python 3.6+
- SeleniumBase
- A Wit.ai API key for speech-to-text transcription

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/recaptcha-solver.git
   cd recaptcha-solver
   ```

2. Install the required dependencies:
   ```
   pip install seleniumbase requests python-dotenv
   ```

3. Create a `.env` file in the root directory with your Wit.ai API key:
   ```
   WIT_AI_API_KEY=your_wit_ai_api_key
   ```

## Usage

### Basic Usage

```python
from seleniumbase import SB
from captcha_solver import CaptchaSolver
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
wit_api_key = os.getenv("WIT_AI_API_KEY")

# Create a CaptchaSolver instance
captcha_solver = CaptchaSolver(wit_api_key=wit_api_key)

# Use SeleniumBase to navigate to the page with reCAPTCHA
with SB(uc=True) as sb:
    # The CaptchaSolver handles all connection states internally
    # It will reconnect the WebDriver if necessary
    token, success = captcha_solver.solve(sb)
    
    if success:
        print(f"CAPTCHA solved successfully! Token: {token[:20]}...")
        # Continue with form submission or other actions
    else:
        print("Failed to solve CAPTCHA")
```

### Connection State Management

The `CaptchaSolver` class and helper functions now handle all connection state changes internally:

1. `before_captcha_actions(sb)` - Activates CDP mode for initial page interaction
2. `captcha_solver.solve(sb)` - Reconnects the WebDriver as needed for iframe interaction
3. `after_captcha_actions(sb, success, token)` - Reconnects the WebDriver if needed for final form submission

This allows a clean, simple flow in your main code without worrying about connection states.

### Advanced Usage

See the `example_usage.py` and `main.py` files for more comprehensive examples.

## How It Works

1. The solver first locates and clicks the reCAPTCHA checkbox
2. If a challenge appears, it switches to the audio challenge
3. It downloads the audio file and sends it to Wit.ai for transcription
4. The transcribed text is entered into the challenge field
5. The solver verifies if the challenge was successful and returns the reCAPTCHA token

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is for educational purposes only. Using automated tools to solve CAPTCHAs may violate the terms of service of some websites. Use responsibly and at your own risk. 