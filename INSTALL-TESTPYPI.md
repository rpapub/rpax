# Installing rpax from TestPyPI

rpax v0.0.2 is published on TestPyPI for testing before production release.

## Quick Start with uvx (No Installation Required)

Run rpax directly without installing:

```bash
uvx --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    rpax --version
```

## Usage Examples

### Parse a UiPath Project

```bash
uvx --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    rpax parse /path/to/project.json
```

### Show Help

```bash
uvx --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    rpax --help
```

## Why Two Index URLs?

- `--index-url https://test.pypi.org/simple/` - Fetches rpax and cpmf-uips-xaml from TestPyPI
- `--extra-index-url https://pypi.org/simple/` - Fetches all other dependencies from production PyPI

Both are needed because rpax depends on `cpmf-uips-xaml` which is also on TestPyPI.

## Alternative: Install Globally

If you prefer to install rpax permanently:

```bash
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ \
            rpax
```

Then use normally:

```bash
rpax parse /path/to/project.json
rpax --help
```

## Corporate Environment Setup

For easier use in corporate environments, create a shell alias:

```bash
# Add to ~/.bashrc or ~/.zshrc
alias rpax-test='uvx --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ rpax'

# Then use simply as:
rpax-test parse /path/to/project.json
```

## TestPyPI Package Info

- **Package**: https://test.pypi.org/project/rpax/0.0.2/
- **Version**: 0.0.2
- **Dependencies**: Includes cpmf-uips-xaml v0.1.0 from TestPyPI
- **Python**: Requires Python >=3.11

## Troubleshooting

### SSL Certificate Issues

If you encounter SSL errors in corporate environments:

```bash
uvx --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    --trusted-host test.pypi.org \
    --trusted-host pypi.org \
    --trusted-host files.pythonhosted.org \
    rpax --version
```

### Proxy Configuration

If behind a corporate proxy:

```bash
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080
uvx --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ rpax --version
```

## Next Steps

After testing on TestPyPI, rpax will be published to production PyPI for simpler installation:

```bash
# Future production usage (simpler!)
uvx rpax --version
```
