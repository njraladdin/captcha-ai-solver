# reCAPTCHA Solver

A modular solution for solving Google's reCAPTCHA v2 challenges using audio recognition.

## Features

- **Extract**: Automatically extract reCAPTCHA parameters from any website
- **Replicate**: Create a clean environment to display the reCAPTCHA
- **Solve**: Automatically solve reCAPTCHA challenges using audio recognition
- **Apply**: Apply the solved token back to the original website

## Components

- **CaptchaExtractor**: Extracts reCAPTCHA parameters from target websites
- **ReplicatedCaptcha**: Creates a clean environment to display the reCAPTCHA
- **CaptchaSolver**: Automatically solves reCAPTCHA using audio recognition
- **TokenApplier**: Applies the solved token back to the original page

Each component focuses on one specific task, maintaining separation of concerns and modularity.

## Requirements

- Python 3.7+
- SeleniumBase
- Requests
- Flask
- python-dotenv
- Wit.ai API key (required for audio solving)

## Installation

```bash
pip install seleniumbase requests flask python-dotenv
```

## Setting up Wit.ai

To use the audio solver, you must have a Wit.ai API key:

1. Get a free API key from [Wit.ai](https://wit.ai/)
2. Set it as an environment variable:
   ```bash
   # Windows
   set WIT_API_KEY=your-api-key
   
   # Linux/Mac
   export WIT_API_KEY=your-api-key
   ```
   
   Alternatively, create a `.env` file with:
   ```
   WIT_API_KEY=your-api-key
   ```

## Usage

### Running the Demo Workflow

The demo_workflow.py script demonstrates the complete process with separate steps:

```bash
python demo_workflow.py
```

This will:
1. Navigate to Google's reCAPTCHA demo page
2. Extract the reCAPTCHA parameters
3. Replicate the reCAPTCHA in a separate browser window
4. Solve the replicated reCAPTCHA using audio recognition
5. Apply the token back to the original page
6. Submit the form

### Programmatic Usage

```python
# Import the necessary components
from captcha_solver import CaptchaExtractor, ReplicatedCaptcha, CaptchaSolver, TokenApplier

# 1. Extract parameters from target website
extractor = CaptchaExtractor()
params = extractor.extract_captcha_params(browser)

# 2. Replicate the reCAPTCHA
replicator = ReplicatedCaptcha(download_dir="tmp")
html_path, replicated_browser, _ = replicator.run_replicated_captcha(
    website_key=params["website_key"],
    website_url=params["website_url"]
)

# 3. Solve the replicated reCAPTCHA
solver = CaptchaSolver(wit_api_key="your-wit-ai-key")
token, success = solver.solve(replicated_browser)

# Clean up the replicated browser
replicated_browser.quit()
replicator.stop_http_server()

# 4. Apply the token to the original website
if token:
    applier = TokenApplier()
    success = applier.apply_token(browser, token, params, submit_form=True)
```

## How It Works

The modular design allows each component to focus on a specific task:

1. **Extraction**: CaptchaExtractor identifies and extracts reCAPTCHA parameters from the target website
2. **Replication**: ReplicatedCaptcha creates a clean HTML page with just the reCAPTCHA challenge
3. **Solving**: CaptchaSolver clicks the audio button, downloads the audio, uses Wit.ai to transcribe it, and submits the answer
4. **Application**: TokenApplier injects the token back into the original website using JavaScript

This separation of concerns makes the system more maintainable and allows components to be used independently.

## Notes

- Works best with standard reCAPTCHA implementations
- Enterprise reCAPTCHA might require additional customization
- Using the system too frequently from the same IP might trigger Google's blocking mechanisms
- This tool is meant for legitimate automation purposes

## License

MIT 