#!/bin/bash
# TORE Matrix Labs Installation Script

set -e

echo "🚀 TORE Matrix Labs Installation Script"
echo "======================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python 3.8+ is available
check_python() {
    print_status "Checking Python version..."
    
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3.8 or higher."
        exit 1
    fi
    
    python_version=$(python3 -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
    required_version="3.8"
    
    if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
        print_error "Python $python_version found, but Python $required_version or higher is required."
        exit 1
    fi
    
    print_success "Python $python_version found"
}

# Check for system dependencies
check_system_deps() {
    print_status "Checking system dependencies..."
    
    # Check for development tools
    if ! dpkg -l | grep -q build-essential; then
        print_warning "build-essential not found. Installing..."
        sudo apt update && sudo apt install -y build-essential python3-dev
    fi
    
    # Check for Qt5 libraries (optional)
    if dpkg -l | grep -q python3-pyqt5; then
        print_success "System PyQt5 found"
        SYSTEM_QT=true
    else
        print_warning "System PyQt5 not found. Will use pip installation."
        SYSTEM_QT=false
    fi
}

# Create virtual environment
create_venv() {
    print_status "Creating virtual environment..."
    
    if [ -d "venv" ]; then
        print_warning "Virtual environment already exists. Removing..."
        rm -rf venv
    fi
    
    python3 -m venv venv
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    print_success "Virtual environment created and activated"
}

# Install package with dependencies
install_package() {
    print_status "Installing TORE Matrix Labs..."
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install core package
    pip install -e .
    
    # Install GUI dependencies
    print_status "Installing GUI dependencies..."
    if [ "$SYSTEM_QT" = true ]; then
        print_status "Using system PyQt5..."
    else
        print_status "Installing PyQt5 via pip..."
        pip install ".[gui]" || {
            print_warning "PyQt5 installation failed. Trying PySide6..."
            pip install ".[pyside]" || {
                print_warning "Both PyQt5 and PySide6 installation failed. GUI will not be available."
            }
        }
    fi
    
    # Install AI dependencies (optional)
    read -p "Install AI/ML dependencies? This may take a while and requires significant disk space. [y/N]: " install_ai
    if [[ $install_ai =~ ^[Yy]$ ]]; then
        print_status "Installing AI/ML dependencies..."
        pip install ".[ai]" || print_warning "Some AI dependencies failed to install"
    fi
    
    print_success "Package installation completed"
}

# Test installation
test_installation() {
    print_status "Testing installation..."
    
    source venv/bin/activate
    
    # Test CLI
    if python -m tore_matrix_labs --help > /dev/null 2>&1; then
        print_success "CLI interface working"
    else
        print_warning "CLI interface test failed"
    fi
    
    # Test imports
    python -c "import tore_matrix_labs; print('✓ Package import successful')" || {
        print_error "Package import failed"
        return 1
    }
    
    # Test GUI (if available)
    if python -c "from tore_matrix_labs.ui.main_window import MainWindow; print('✓ GUI components available')" 2>/dev/null; then
        print_success "GUI components available"
        GUI_AVAILABLE=true
    else
        print_warning "GUI components not available (this is OK for headless setups)"
        GUI_AVAILABLE=false
    fi
    
    print_success "Installation test completed"
}

# Create desktop launcher (Linux)
create_launcher() {
    if [ "$GUI_AVAILABLE" = true ] && [ "$XDG_CURRENT_DESKTOP" != "" ]; then
        read -p "Create desktop launcher? [y/N]: " create_desktop
        if [[ $create_desktop =~ ^[Yy]$ ]]; then
            print_status "Creating desktop launcher..."
            
            INSTALL_DIR=$(pwd)
            DESKTOP_FILE="$HOME/.local/share/applications/tore-matrix-labs.desktop"
            
            mkdir -p "$HOME/.local/share/applications"
            
            cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Name=TORE Matrix Labs
Comment=AI Document Processing Pipeline
Exec=$INSTALL_DIR/venv/bin/python -m tore_matrix_labs
Icon=$INSTALL_DIR/resources/icons/app-icon.png
Terminal=false
Type=Application
Categories=Office;Development;
StartupWMClass=tore-matrix-labs
EOF
            
            chmod +x "$DESKTOP_FILE"
            print_success "Desktop launcher created"
        fi
    fi
}

# Print usage instructions
print_usage() {
    echo ""
    echo "🎉 Installation Complete!"
    echo "========================"
    echo ""
    echo "To use TORE Matrix Labs:"
    echo ""
    echo "1. Activate the virtual environment:"
    echo "   source venv/bin/activate"
    echo ""
    echo "2. Run the application:"
    if [ "$GUI_AVAILABLE" = true ]; then
        echo "   tore-matrix                    # GUI mode"
    fi
    echo "   tore-matrix --help             # CLI help"
    echo "   tore-matrix process file.pdf   # Process document"
    echo "   tore-matrix analyze file.pdf   # Analyze document"
    echo ""
    echo "3. Or run directly with Python:"
    echo "   python -m tore_matrix_labs"
    echo ""
    echo "For more information, see the README.md file."
    echo ""
}

# Main installation flow
main() {
    echo ""
    
    # Check requirements
    check_python
    check_system_deps
    
    # Install
    create_venv
    install_package
    
    # Test and finalize
    test_installation
    create_launcher
    
    # Show usage
    print_usage
    
    print_success "TORE Matrix Labs installation completed successfully!"
}

# Run main installation
main "$@"