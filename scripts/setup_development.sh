#!/bin/bash
# Development environment setup script for TORE Matrix Labs V3

echo "🚀 Setting up TORE Matrix Labs V3 development environment..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED_VERSION="3.11"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" = "$REQUIRED_VERSION" ]; then 
    print_status "Python $PYTHON_VERSION is installed (>= $REQUIRED_VERSION required)"
else
    print_error "Python $PYTHON_VERSION is too old. Please install Python $REQUIRED_VERSION or newer"
    exit 1
fi

# Create virtual environment
echo "Creating virtual environment..."
if [ -d "venv" ]; then
    print_warning "Virtual environment already exists. Skipping creation."
else
    python3 -m venv venv
    print_status "Virtual environment created"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
print_status "Virtual environment activated"

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel
print_status "pip upgraded"

# Install development dependencies
echo "Installing development dependencies..."
pip install -e ".[dev]"
print_status "Development dependencies installed"

# Install pre-commit hooks
echo "Setting up pre-commit hooks..."
pre-commit install
print_status "Pre-commit hooks installed"

# Create necessary directories
echo "Creating project directories..."
mkdir -p data/samples data/exports logs cache temp
print_status "Project directories created"

# Initialize test database
echo "Setting up test database..."
python -c "from torematrix.core.storage import init_db; init_db()" 2>/dev/null || print_warning "Database initialization will be available after core implementation"

# Set up git hooks
echo "Setting up git hooks..."
cat > .git/hooks/pre-push << 'EOF'
#!/bin/bash
# Run tests before push
echo "Running tests before push..."
pytest tests/unit -x -q
if [ $? -ne 0 ]; then
    echo "Tests failed! Push aborted."
    exit 1
fi
echo "All tests passed!"
EOF
chmod +x .git/hooks/pre-push
print_status "Git hooks configured"

# Create local configuration
echo "Creating local configuration..."
if [ ! -f "config/local_settings.yaml" ]; then
    cat > config/local_settings.yaml << EOF
# Local development settings
debug: true
database:
  url: "sqlite:///data/torematrix_dev.db"
logging:
  level: "DEBUG"
  file: "logs/torematrix_dev.log"
EOF
    print_status "Local configuration created"
else
    print_warning "Local configuration already exists"
fi

# Final message
echo ""
echo "✨ Development environment setup complete!"
echo ""
echo "To activate the environment in future sessions, run:"
echo "  source venv/bin/activate"
echo ""
echo "To run the application:"
echo "  python -m torematrix.cli"
echo ""
echo "To run tests:"
echo "  pytest"
echo ""
echo "Happy coding! 🎉"