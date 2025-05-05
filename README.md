# reCAPTCHA Solver

An automated solution for solving Google's reCAPTCHA v2 challenges using audio recognition.

## Features

- **Extract**: Automatically extract reCAPTCHA parameters from any website
- **Solve**: Automatically solve reCAPTCHA challenges using audio recognition
- **Apply**: Apply the solved token back to the original website

## Components

- **CaptchaExtractor**: Extracts reCAPTCHA parameters from target websites
- **ReplicatedCaptcha**: Creates a clean environment to solve the reCAPTCHA
- **CaptchaSolver**: Automatically solves reCAPTCHA using audio recognition
- **TokenApplier**: Applies the solved token back to the original page

## Requirements

- Python 3.7+
- SeleniumBase
- Requests
- Flask
- Wit.ai API key (required)

## Installation

```bash
pip install seleniumbase requests flask
```

## Setting up Wit.ai

To use the automated solver, you must have a Wit.ai API key:

1. Get a free API key from [Wit.ai](https://wit.ai/)
2. Set it as an environment variable:
   ```bash
   # Windows
   set WIT_API_KEY=your-api-key
   
   # Linux/Mac
   export WIT_API_KEY=your-api-key
   ```

## Usage

### Running the Demo

The demo_workflow.py script demonstrates the complete process:

```bash
python demo_workflow.py
```

This will:
1. Navigate to Google's reCAPTCHA demo page
2. Extract the reCAPTCHA parameters
3. Automatically solve the reCAPTCHA using audio recognition
4. Apply the token back to the original page
5. Submit the form

### Programmatic Usage

```python
from captcha_solver import ReplicatedCaptcha

# Get a token programmatically (fully automatic)
replicated_captcha = ReplicatedCaptcha(download_dir="tmp")
token = replicated_captcha.get_token(
    website_key="your-site-key",
    website_url="https://example.com",
    timeout=30
)

# Use the token in your application
if token:
    # Use the token in your form submission or API call
    payload = {'g-recaptcha-response': token, 'other_data': 'value'}
    response = requests.post('https://example.com/submit', data=payload)
```

## How It Works

1. **Extraction**: The system identifies and extracts reCAPTCHA parameters from the target website
2. **Solving**: The system replicates the challenge, clicks the audio button, downloads the audio, uses Wit.ai to transcribe it, and submits the answer
3. **Application**: The resulting token is applied to the original website using JavaScript injection

## Notes

- Works best with standard reCAPTCHA implementations
- Enterprise reCAPTCHA might require additional customization
- Using the system too frequently from the same IP might trigger Google's blocking mechanisms
- This tool is meant for legitimate automation purposes

## License

MIT 