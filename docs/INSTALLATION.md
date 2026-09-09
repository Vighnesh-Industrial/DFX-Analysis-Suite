# Installation Guide - DFX Analysis Suite

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Git

## Step 1: Clone the Repository

```bash
git clone https://github.com/Vighnesh-Industrial/DFX-Analysis-Suite.git
cd DFX-Analysis-Suite
```

## Step 2: Create Virtual Environment

### Windows
```bash
python -m venv venv
venv\Scripts\activate
```

### macOS/Linux
```bash
python3 -m venv venv
source venv/bin/activate
```

## Step 3: Install Dependencies

### For Command-Line Use
```bash
pip install -r requirements.txt
```

### For Web Dashboard
```bash
pip install -r requirements_web.txt
```

## Step 4: Verify Installation

```bash
python -c "from dfx_analyzers import ComprehensiveDFXAnalyzer; print('✅ Installation successful!')"
```

## Troubleshooting

### Issue: Module not found error
**Solution:** Ensure you're in the virtual environment and in the correct directory

```bash
# Verify virtual environment is active
which python  # macOS/Linux
where python  # Windows

# Reinstall requirements
pip install --upgrade -r requirements.txt
```

### Issue: FreeCAD import errors
**Solution:** Install FreeCAD separately

```bash
# Ubuntu/Debian
sudo apt-get install freecad

# macOS
brew install freecad

# Windows
# Download from https://www.freecad.org/
```

## Next Steps

- See [EXAMPLES.md](EXAMPLES.md) for usage examples
- See [CREO_INTEGRATION.md](CREO_INTEGRATION.md) for Creo support
- See [API_REFERENCE.md](API_REFERENCE.md) for API documentation
