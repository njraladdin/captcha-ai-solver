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
                is_invisible (bool, optional): Whether it's invisible. Default is False.
                is_enterprise (bool, optional): If it's enterprise reCAPTCHA. Default is False.
                data_s_value (str, optional): data-s parameter if present. Default is None.
        
        solver_config (dict, optional): Configuration for the solver
                wit_api_key (str, optional): API key for Wit.ai speech recognition
                download_dir (str, optional): Directory for temporary files
    
    Returns:
        str or None: The solved captcha token if successful, None otherwise
    
    Raises:
        ValueError: If the captcha type is not supported or required parameters are missing
    """
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
    token, success = solver.solve(captcha_params)
    
    # Return only the token (or None if unsuccessful)
    return token if success else None

__version__ = "0.1.0"
__all__ = ["CaptchaSolver", "solve_captcha"] 