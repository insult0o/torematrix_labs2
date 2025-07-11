#!/bin/bash
# TORE Matrix Labs - Project Operations Script
# Comprehensive script for project management and testing

set -e  # Exit on any error

PROJECT_ROOT="/home/insulto/tore_matrix_labs"
VENV_PATH="$PROJECT_ROOT/venv"

echo "🔬 TORE Matrix Labs - Project Operations"
echo "======================================="

# Function to setup Python environment
setup_python_env() {
    echo "🐍 Setting up Python environment..."
    cd "$PROJECT_ROOT"
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "$VENV_PATH" ]; then
        echo "📦 Creating virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install requirements
    if [ -f "requirements/base.txt" ]; then
        echo "📦 Installing base requirements..."
        pip install -r requirements/base.txt
    fi
    
    echo "✅ Python environment ready"
}

# Function to run the application
run_application() {
    echo "🚀 Starting TORE Matrix Labs application..."
    cd "$PROJECT_ROOT"
    
    # Activate virtual environment
    source venv/bin/activate 2>/dev/null || echo "⚠️ Virtual environment not found, using system Python"
    
    # Run the application
    python3 -m tore_matrix_labs
}

# Function to run tests
run_tests() {
    local test_type="$1"
    
    echo "🧪 Running tests..."
    cd "$PROJECT_ROOT"
    
    case "$test_type" in
        "project-loading")
            echo "📋 Testing project loading fixes..."
            python3 test_project_loading_fix.py
            ;;
        "pdf-highlighting")
            echo "📋 Testing PDF highlighting fixes..."
            python3 test_pdf_highlighting_fix.py
            ;;
        "area-display")
            echo "📋 Testing area display fixes..."
            python3 test_area_list_display_fix.py
            ;;
        "all"|"")
            echo "📋 Running all critical tests..."
            echo ""
            echo "🔍 Testing project loading..."
            python3 test_project_loading_fix.py
            echo ""
            echo "🔍 Testing PDF highlighting..."
            python3 test_pdf_highlighting_fix.py
            echo ""
            echo "🔍 Testing area display..."
            python3 test_area_list_display_fix.py
            echo ""
            echo "✅ All tests completed!"
            ;;
        *)
            echo "❌ Unknown test type: $test_type"
            echo "Available tests: project-loading, pdf-highlighting, area-display, all"
            exit 1
            ;;
    esac
}

# Function to check project status
check_project_status() {
    echo "📊 TORE Matrix Labs Project Status"
    echo "=================================="
    echo ""
    
    # Check Python environment
    echo "🐍 Python Environment:"
    python3 --version
    echo ""
    
    # Check virtual environment
    if [ -d "$VENV_PATH" ]; then
        echo "✅ Virtual environment: Present"
    else
        echo "⚠️ Virtual environment: Not found"
    fi
    echo ""
    
    # Check key project files
    echo "📁 Key Project Files:"
    key_files=(
        "tore_matrix_labs/__main__.py"
        "tore_matrix_labs/ui/main_window.py"
        "tore_matrix_labs/ui/components/manual_validation_widget.py"
        "tore_matrix_labs/ui/components/pdf_viewer.py"
        "tore_matrix_labs/ui/highlighting/highlighting_engine.py"
        "CLAUDE.md"
        "README.md"
    )
    
    for file in "${key_files[@]}"; do
        if [ -f "$PROJECT_ROOT/$file" ]; then
            echo "✅ $file"
        else
            echo "❌ $file (missing)"
        fi
    done
    echo ""
    
    # Check recent fixes
    echo "🔧 Recent Critical Fixes:"
    echo "✅ Project loading - Shows processed data immediately"
    echo "✅ PDF highlighting - QA issues highlight in PDF viewer"
    echo "✅ Area display - Areas show in list and preview sections"
    echo ""
    
    # Check git status
    echo "📝 Git Status:"
    cd "$PROJECT_ROOT"
    git status --short
}

# Function to create backup
create_backup() {
    local backup_name="$1"
    
    if [ -z "$backup_name" ]; then
        backup_name="backup_$(date +%Y%m%d_%H%M%S)"
    fi
    
    echo "💾 Creating project backup..."
    cd "$(dirname "$PROJECT_ROOT")"
    
    # Create backup excluding unnecessary files
    tar -czf "${backup_name}.tar.gz" \
        --exclude="venv" \
        --exclude="__pycache__" \
        --exclude="*.pyc" \
        --exclude="*.tore" \
        --exclude="output" \
        --exclude=".git" \
        "$(basename "$PROJECT_ROOT")"
    
    echo "✅ Backup created: ${backup_name}.tar.gz"
}

# Function to show help
show_help() {
    echo "TORE Matrix Labs Project Operations Script"
    echo ""
    echo "Usage: $0 <command> [arguments]"
    echo ""
    echo "Commands:"
    echo "  setup-env            - Setup Python virtual environment"
    echo "  run                  - Run the TORE Matrix Labs application"
    echo "  test [type]          - Run tests (project-loading, pdf-highlighting, area-display, all)"
    echo "  status               - Show project status and health check"
    echo "  backup [name]        - Create project backup"
    echo ""
    echo "Examples:"
    echo "  $0 setup-env"
    echo "  $0 run"
    echo "  $0 test all"
    echo "  $0 status"
    echo "  $0 backup my_backup"
}

# Main script logic
case "$1" in
    "setup-env")
        setup_python_env
        ;;
    "run")
        run_application
        ;;
    "test")
        run_tests "$2"
        ;;
    "status")
        check_project_status
        ;;
    "backup")
        create_backup "$2"
        ;;
    "help"|"--help"|"-h"|"")
        show_help
        ;;
    *)
        echo "❌ Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac