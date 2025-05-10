# Changelog

## [0.2.0] - Unreleased

### Added
- Better error handling throughout the solving process

### Changed
- BREAKING CHANGE: New result object format for `solve_captcha` function that includes:
  - `success` boolean indicating whether the solving was successful
  - `token` containing the solution token if successful
  - `error` containing an error message if unsuccessful
- Removed unsupported parameters (`is_invisible` and `is_enterprise`)

### Fixed


## [0.1.0] - Initial Release

### Added
- Initial implementation of captcha-ai-solver
- Support for reCAPTCHA v2
- Audio challenge solving using Wit.ai
- Basic example script
