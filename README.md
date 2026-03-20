# NB2PDF Agent

**AI-Powered Jupyter Notebook to Professional PDF Converter**

Transform your Jupyter notebooks into polished, publication-ready PDF reports with proper formatting, syntax highlighting, and structured layouts.

## Features

- **Smart Parsing**: Intelligently extracts markdown cells, code cells, and outputs from `.ipynb` files
- **Professional Formatting**: Clean typography, proper heading hierarchy, and styled tables
- **Code Styling**: Dark-themed code blocks with syntax coloring
- **Output Support**: Renders text outputs, tables, images, and error tracebacks
- **Table of Contents**: Auto-generated navigation from notebook headings
- **Page Numbers**: Professional header and footer with pagination
- **Image Support**: Embedded images from notebook outputs (PNG, base64)

## Installation

### Prerequisites

- Python 3.10 or higher
- pip package manager

### Install Dependencies

```bash
# Using pip
pip install -e .

# Or install dependencies directly
pip install nbformat markdown fpdf2

# Or using uv
uv pip install nbformat markdown fpdf2
```

## Usage

### Basic Usage

```bash
python nb2pdf_agent.py notebook.ipynb
```

This generates `notebook.pdf` in the same directory.

### Specify Output Path

```bash
python nb2pdf_agent.py notebook.ipynb output_report.pdf
```

### As a Python Module

```python
from nb2pdf_agent import NB2PDFAgent
from pathlib import Path

agent = NB2PDFAgent(
    notebook_path=Path("notebook.ipynb"),
    output_path=Path("report.pdf")
)
agent.convert()
```

## Project Structure

```
p4assignment/
├── nb2pdf_agent.py      # Main agent script
├── README.md            # This documentation
├── pyproject.toml       # Project dependencies
├── sample_notebook.ipynb # Demo notebook for testing
└── sample_output.pdf    # Generated PDF example
```

## How It Works

### Architecture

```
+------------------+     +------------------+     +------------------+
|  NotebookParser  |---->|   PDFBuilder     |---->|   PDF Output     |
|                  |     |                  |     |                  |
| - Load .ipynb    |     | - Markdown render|     | - Page numbers   |
| - Extract cells  |     | - Code blocks    |     | - Headers/footers|
| - Parse outputs  |     | - Output blocks  |     | - TOC            |
+------------------+     +------------------+     +------------------+
```

### Components

1. **NotebookParser**: Reads the `.ipynb` JSON structure and extracts:
   - Markdown cells with formatted text
   - Code cells with Python source code
   - Output items (streams, results, images, errors)

2. **PDFBuilder (FPDF)**: Builds the PDF document with:
   - Title page with metadata
   - Table of contents from headings
   - Formatted markdown sections
   - Syntax-highlighted code blocks
   - Styled output and error blocks

3. **PDF Output**: Generates professional PDF with:
   - Page headers and footers
   - Page numbers
   - Proper fonts and spacing

## Supported Output Types

| Output Type | Support |
|-------------|---------|
| Text streams (stdout/stderr) | Supported |
| Execute results | Supported |
| Display data | Supported |
| PNG images | Embedded (base64) |
| Error tracebacks | Styled error blocks |
| Tables | Supported |

## Customization

### Modifying Styles

Edit the `PDFBuilder` class in `nb2pdf_agent.py` to customize:
- Font families and sizes
- Color schemes
- Page margins and layout
- Header/footer styling

### Adding Metadata

Set notebook metadata in your `.ipynb` file:

```json
{
 "metadata": {
  "title": "My Report Title",
  "author": "Your Name"
 }
}
```

## Error Handling

The agent gracefully handles:
- Invalid notebook formats
- Missing output data
- Image encoding issues
- Unicode characters in content

## Development

### Running Tests

```bash
pip install pytest
pytest tests/
```

### Code Style

```bash
pip install black
black nb2pdf_agent.py
```

## License

MIT License - Feel free to use, modify, and distribute.

## Acknowledgments

- [nbformat](https://nbformat.readthedocs.io/) - Jupyter notebook format handling
- [fpdf2](https://pyfpdf.github.io/fpdf2/) - PDF generation
- [Python-Markdown](https://python-markdown.github.io/) - Markdown processing"# Project4" 
