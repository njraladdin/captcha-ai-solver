# Captcha AI Solver

Python library that solves reCAPTCHA v2 by replicating the challenge locally and using Wit.ai for audio transcription. Windows-only, requires admin privileges.

## Features

- Replicates reCAPTCHA v2 by spoofing domains in hosts file
- Solves standard reCAPTCHA v2
- Uses Wit.ai API for audio challenge transcription
- Returns solution tokens for form submission

## Installation

```bash
pip install captcha-ai-solver
```

## Important Note

**Windows Only** - Requires Admin privileges (modifies hosts file when it needs to replicate the captcha environment and spoof the original website domain).

This library inputs captcha parameters and outputs solution tokens. For extracting parameters or applying tokens, see: [this guide](https://gist.github.com/2captcha/2ee70fa1130e756e1693a5d4be4d8c70)

## Quick Start

```python
from captcha_solver import solve_captcha

# Define captcha parameters
captcha_params = {
    "website_url": "https://www.google.com/recaptcha/api2/demo",
    "website_key": "6Le-wvkSAAAAAPBMRTvw0Q4Muexq9bi0DJwx_mJ-"
}

# solver configuration
solver_config = {
    "wit_api_key": "YOUR_WIT_API_KEY",  # NEEDED for recaptcha audio challenges
}

# Solve the captcha
result = solve_captcha(
    captcha_type="recaptcha_v2",
    captcha_params=captcha_params,
    solver_config=solver_config
)

if result["success"]:
    print(f"Captcha solved! Token: {result['token'][:30]}...")
    # Use the token in your application
else:
    print(f"Failed to solve captcha: {result['error']}")
```

## Detailed Usage

### Supported Captcha Types

Currently, the library supports:

- `RecaptchaV2`: Standard reCAPTCHA v2

### Captcha Parameters

For `RecaptchaV2`:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| website_url | string | Yes | URL of the website with the captcha |
| website_key | string | Yes | reCAPTCHA site key |

### Solver Configuration

| Option | Type | Description |
|--------|------|-------------|
| wit_api_key | string | API key for Wit.ai speech recognition (required for audio challenges) |
| download_dir | string | Directory for temporary files (default: "tmp") |

### Return Value

The `solve_captcha` function returns a result object with the following properties:

| Property | Type | Description |
|----------|------|-------------|
| success | boolean | Whether the solving was successful |
| token | string or null | The solved captcha token if successful, null otherwise |
| error | string or null | Error message if unsuccessful, null otherwise |

## Example Script

The library includes an example script that demonstrates how to use it:

```bash
python example.py --website "https://example.com" --key "your-recaptcha-key"
```

## How It Works

The library uses a combination of browser automation and AI-powered audio transcription to solve reCAPTCHA challenges:

1. It replicates the reCAPTCHA challenge in a controlled environment
2. For audio challenges, it uses AI to transcribe the audio
3. It submits the answer and retrieves the verification token
4. The token can then be used to bypass the captcha on the target website

## Requirements

- Python 3.7+
- SeleniumBase
- Requests
- Python-dotenv
- Wit.ai API key (for audio challenges)

## Disclaimer

This library is intended for legitimate testing, development, and automation purposes only. Please use responsibly and in accordance with the target website's terms of service.

## Development Setup

If you want to contribute or modify the library, follow these steps to set up a development environment:

1. Clone the repository:
```bash
git clone https://github.com/njraladdin/captcha-ai-solver.git
cd captcha-ai-solver
```

2. Create and activate a virtual environment:

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**On macOS/Linux:**
```bash
python -m venv venv
source venv/bin/activate
```

3. Install the dependencies in development mode:
```bash
python -m pip install -e .
```

4. Install development dependencies (optional):
```bash
pip install -e ".[dev]"
```

5. Create a `.env` file with your WIT.ai API key for audio challenges:
```
WIT_API_KEY=your_key_here
``` 