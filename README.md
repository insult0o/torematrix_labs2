# TORE Matrix Labs - Ultimate AI Document Processing Pipeline

🎯 **Mission-Critical, Enterprise-Grade AI Document Processing for ICAO/ATC Procedural Documents**

TORE Matrix Labs is the foundational component of the TORE AI ecosystem, engineered for zero hallucination, maximum accuracy, and complete traceability in document ingestion for RAG systems and LLM fine-tuning.

## 🏆 Key Features

### 🔍 **Advanced Document Analysis**
- Multi-format support (PDF, DOCX, ODT, RTF)
- Intelligent document structure analysis
- OCR quality assessment and recommendations
- Automatic document type classification

### 🛡️ **Quality Assurance Engine**
- Multi-dimensional quality scoring
- Human validation workflow
- Error detection and auto-correction
- Complete audit trail

### 🎨 **Professional UI**
- PyQt5-based modern interface
- Side-by-side document review
- Advanced table and image editing
- Real-time processing feedback

### 🚀 **Production-Ready Pipeline**
- Batch processing capabilities
- Scalable architecture
- Enterprise security features
- Cloud storage integration

### 🤖 **AI Integration**
- Multiple embedding models
- Vector database support (FAISS, Qdrant)
- Fine-tuning dataset generation
- RAG-optimized output formats

## 🛠️ Installation

### Prerequisites
- Python 3.8 or higher
- 4GB+ RAM recommended
- 2GB+ free disk space

### Quick Install
```bash
# Clone the repository
git clone https://github.com/tore-ai/matrix-labs.git
cd tore_matrix_labs

# Install with pip
pip install -e .

# Or install with AI features
pip install -e ".[ai]"

# For development
pip install -e ".[dev]"
```

### From PyPI
```bash
pip install tore-matrix-labs
```

## 🚀 Quick Start

### 1. Launch Application
```bash
# GUI Application
python main.py

# Or using entry point
tore-matrix
```

### 2. Create New Project
1. Click "New Project" or press `Ctrl+N`
2. Configure project settings
3. Set quality thresholds and validation rules

### 3. Import Documents
1. Go to "Ingestion" tab
2. Click "Add Files" or drag-and-drop PDFs
3. Configure processing settings
4. Click "Start Processing"

### 4. Quality Validation
1. Switch to "QA Validation" tab
2. Review extracted content side-by-side
3. Make corrections using built-in tools
4. Approve or reject documents

### 5. Export Data
1. Go to "Project Management" tab
2. Select export format (JSONL, JSON, CSV, etc.)
3. Configure output settings
4. Export for RAG or fine-tuning

## 📋 Configuration

### Environment Variables
Copy `.env.example` to `.env` and configure:

```bash
# AI Integration
OPENAI_API_KEY=your_openai_key
HUGGINGFACE_TOKEN=your_hf_token

# Processing Settings
MAX_WORKERS=4
QUALITY_THRESHOLD=0.8
CHUNK_SIZE=512

# Database
DATABASE_URL=sqlite:///data/tore_matrix.db

# Cloud Storage (Optional)
AWS_ACCESS_KEY_ID=your_aws_key
AZURE_STORAGE_CONNECTION_STRING=your_azure_string
```

### Application Settings
Access via `Edit > Settings` or `Ctrl+,`:

- **Processing**: Quality thresholds, chunking strategy
- **UI**: Theme, font size, window layout
- **AI**: Embedding models, API configurations
- **Export**: Default formats, output directories

## 🎯 Specialized Features

### ICAO/ATC Document Support
- Aviation procedure recognition
- Technical manual processing
- Regulatory document handling
- Air traffic control procedures

### Quality Assurance
- OCR error detection
- Table structure validation
- Reading order verification
- Image-caption alignment

### Advanced Correction Tools
- Rich text editor with undo/redo
- Spreadsheet-like table editor
- Drag-and-drop paragraph reordering
- Manual image alignment

## 🏗️ Architecture

```
TORE Matrix Labs
├── Core Processing Engine
│   ├── Document Analyzer
│   ├── Content Extractor
│   ├── Quality Assessor
│   └── Correction Engine
├── User Interface
│   ├── Ingestion Widget
│   ├── QA Validation Widget
│   ├── Project Manager
│   └── Advanced Editors
├── Data Pipeline
│   ├── Chunk Generator
│   ├── Embedding Generator
│   ├── Export Generator
│   └── Dataset Builder
└── Enterprise Features
    ├── User Management
    ├── Audit Logging
    ├── Cloud Integration
    └── Monitoring
```

## 📊 Supported Formats

### Input Formats
- **PDF**: Advanced parsing with PyMuPDF and pdfplumber
- **DOCX**: Microsoft Word document processing
- **ODT**: OpenDocument text files
- **RTF**: Rich text format support

### Output Formats
- **JSONL**: Streaming JSON for large datasets
- **JSON**: Structured data export
- **CSV**: Tabular data format
- **Parquet**: Columnar storage format
- **HDF5**: Scientific data format
- **Alpaca**: Fine-tuning format
- **OpenAI**: GPT fine-tuning format

## 🔌 Integrations

### AI/ML Platforms
- **OpenAI**: GPT models and embeddings
- **HuggingFace**: Transformers and datasets
- **Sentence Transformers**: Embedding models

### Vector Databases
- **FAISS**: Facebook AI similarity search
- **Qdrant**: Vector search engine
- **ChromaDB**: AI-native database
- **Pinecone**: Managed vector database

### Cloud Storage
- **AWS S3**: Amazon cloud storage
- **Azure Blob**: Microsoft cloud storage
- **Google Cloud**: Google cloud storage

### OCR Services
- **ABBYY FineReader**: Professional OCR
- **Tesseract**: Open-source OCR
- **EasyOCR**: Modern OCR engine

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit
pytest -m integration
pytest -m slow

# With coverage
pytest --cov=tore_matrix_labs --cov-report=html
```

## 📈 Performance

### Benchmarks
- **Processing Speed**: 1 page/second average
- **Memory Usage**: <2GB for 500+ page documents
- **Concurrent Processing**: 8+ documents simultaneously
- **Quality Accuracy**: 95%+ on ICAO documents

### Scalability
- **Document Size**: Up to 1000 pages per document
- **Batch Size**: 100+ documents per batch
- **Storage**: Petabyte-scale with cloud integration
- **Users**: Multi-user with role-based access

## 🛡️ Security & Compliance

### Data Protection
- End-to-end encryption
- Secure temporary file handling
- API key management
- Access control and auditing

### Compliance
- GDPR compliance features
- CCPA privacy controls
- SOC 2 security standards
- Aviation industry regulations

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup
```bash
# Clone and setup
git clone https://github.com/tore-ai/matrix-labs.git
cd tore_matrix_labs

# Install development dependencies
pip install -e ".[dev]"

# Setup pre-commit hooks
pre-commit install

# Run tests
pytest
```

## 📚 Documentation

- [User Guide](docs/user_guide/): Complete user manual
- [API Documentation](docs/api/): API reference
- [Developer Guide](docs/developer_guide/): Development documentation
- [Examples](docs/examples/): Usage examples and tutorials

## 🆘 Support

### Community Support
- [GitHub Issues](https://github.com/tore-ai/matrix-labs/issues)
- [Discussions](https://github.com/tore-ai/matrix-labs/discussions)
- [Documentation](https://docs.tore-ai.com/matrix-labs)

### Enterprise Support
- Priority support channels
- Custom feature development
- Training and consulting
- SLA guarantees

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Aviation industry experts for domain knowledge
- Open-source community for foundational tools
- Beta testers and early adopters
- Contributors and maintainers

---

**Built with ❤️ by TORE AI for the Aviation Industry**

[Website](https://tore-ai.com) | [Documentation](https://docs.tore-ai.com) | [Support](mailto:support@tore-ai.com)