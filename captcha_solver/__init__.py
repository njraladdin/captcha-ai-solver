from .captcha_solver import CaptchaSolver

def solve_captcha(captcha_type, captcha_params, solver_config=None):
    """
    Solve a captcha challenge of the specified type with given parameters.
    
    Args:
        captcha_type (str): The type of captcha to solve (currently only "RecaptchaV2" is supported)
        captcha_params (dict): Parameters specific to the captcha type
            
            For RecaptchaV2:
                website_url (str): URL where captcha appears
                website_key (str): reCAPTCHA site key
        
        solver_config (dict, optional): Configuration for the solver
                wit_api_key (str, optional): API key for Wit.ai speech recognition
                download_dir (str, optional): Directory for temporary files
    
    Returns:
        dict: A result object containing:
            - success (bool): Whether the solving was successful
            - token (str or None): The solved captcha token if successful, None otherwise
            - error (str or None): Error message if unsuccessful, None otherwise
    
    Raises:
        ValueError: If the captcha type is not supported or required parameters are missing
    """
    result = {
        "success": False,
        "token": None,
        "error": None
    }
    
    try:
        if captcha_type != "recaptcha_v2":
            raise ValueError(f"Unsupported captcha type: {captcha_type}. Currently only 'RecaptchaV2' is supported.")
        
        # Check for required parameters
        required_params = ["website_url", "website_key"]
        for param in required_params:
            if param not in captcha_params:
                raise ValueError(f"Missing required parameter for RecaptchaV2: {param}")
        
        # Initialize solver with configuration
        solver_config = solver_config or {}
        solver = CaptchaSolver(
            wit_api_key=solver_config.get("wit_api_key"),
            download_dir=solver_config.get("download_dir", "tmp")
        )
        
        # Solve the captcha
        token, success, error = solver.solve(captcha_params)
        
        # Update result object
        result["success"] = success
        result["token"] = token
        result["error"] = error
        
    except Exception as e:
        result["error"] = str(e)
        
    return result

__version__ = "0.2.0"
__all__ = ["CaptchaSolver", "solve_captcha"] 