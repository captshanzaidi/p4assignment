#!/usr/bin/env python3
"""
NB2PDF Agent - AI-Powered Jupyter Notebook to PDF Converter

This agent intelligently extracts components from Jupyter notebooks (.ipynb)
and generates professionally formatted PDF reports.

Usage:
    python nb2pdf_agent.py <notebook.ipynb> [output.pdf]
"""

import argparse
import base64
import io
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import nbformat
from fpdf import FPDF
from markdown import Markdown


@dataclass
class MarkdownCell:
    """Represents a markdown cell from the notebook."""
    source: str
    cell_number: int


@dataclass
class CodeCell:
    """Represents a code cell from the notebook."""
    source: str
    cell_number: int
    outputs: list = field(default_factory=list)


@dataclass
class OutputItem:
    """Represents an output from a code cell."""
    output_type: str
    content: str
    data: Optional[dict] = None


class NotebookParser:
    """Parses Jupyter notebook JSON structure."""

    def __init__(self, notebook_path: Path):
        self.notebook_path = notebook_path
        self.notebook = None

    def load(self) -> None:
        """Load and parse the notebook file."""
        with open(self.notebook_path, 'r', encoding='utf-8') as f:
            self.notebook = nbformat.read(f, as_version=4)

    def extract_cells(self) -> tuple[list[MarkdownCell], list[CodeCell]]:
        """Extract markdown and code cells from the notebook."""
        markdown_cells = []
        code_cells = []

        for idx, cell in enumerate(self.notebook.cells):
            cell_number = idx + 1

            if cell.cell_type == 'markdown':
                source = self._get_cell_source(cell)
                markdown_cells.append(MarkdownCell(
                    source=source,
                    cell_number=cell_number
                ))

            elif cell.cell_type == 'code':
                source = self._get_cell_source(cell)
                outputs = self._extract_outputs(cell)
                code_cells.append(CodeCell(
                    source=source,
                    cell_number=cell_number,
                    outputs=outputs
                ))

        return markdown_cells, code_cells

    def _get_cell_source(self, cell) -> str:
        """Get the source content from a cell."""
        if isinstance(cell.source, list):
            return ''.join(cell.source)
        return cell.source

    def _extract_outputs(self, cell) -> list[OutputItem]:
        """Extract outputs from a code cell."""
        outputs = []

        for output in cell.get('outputs', []):
            output_type = output.get('output_type', '')

            if output_type == 'stream':
                text = ''.join(output.get('text', []))
                outputs.append(OutputItem(
                    output_type='stream',
                    content=text
                ))

            elif output_type == 'execute_result':
                data = output.get('data', {})
                if 'text/plain' in data:
                    outputs.append(OutputItem(
                        output_type='result',
                        content=data['text/plain'],
                        data=data
                    ))
                elif 'image/png' in data:
                    outputs.append(OutputItem(
                        output_type='image',
                        content=data['image/png'],
                        data={'image/png': data['image/png']}
                    ))

            elif output_type == 'display_data':
                data = output.get('data', {})
                if 'text/plain' in data:
                    outputs.append(OutputItem(
                        output_type='display',
                        content=data['text/plain'],
                        data=data
                    ))
                elif 'image/png' in data:
                    outputs.append(OutputItem(
                        output_type='image',
                        content=data['image/png'],
                        data={'image/png': data['image/png']}
                    ))

            elif output_type == 'error':
                ename = output.get('ename', 'Error')
                evalue = output.get('evalue', '')
                traceback = '\n'.join(output.get('traceback', []))
                outputs.append(OutputItem(
                    output_type='error',
                    content=f"{ename}: {evalue}\n\n{traceback}"
                ))

        return outputs

    def get_metadata(self) -> dict:
        """Extract metadata from the notebook."""
        metadata = self.notebook.get('metadata', {})
        return {
            'title': metadata.get('title', self.notebook_path.stem),
            'author': metadata.get('author', 'Unknown Author'),
            'language': metadata.get('language_info', {}).get('name', 'Python'),
        }


class PDFBuilder(FPDF):
    """Custom PDF class with header, footer, and styling."""

    def __init__(self, title: str, author: str):
        super().__init__()
        self.title = title
        self.author = author
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        """Add header to each page."""
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, self.title, align='L')
        self.ln(5)
        self.set_draw_color(52, 152, 219)
        self.set_line_width(0.5)
        self.line(10, 15, 200, 15)
        self.ln(10)

    def footer(self):
        """Add footer with page numbers."""
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

    def chapter_title(self, title: str, level: int = 1):
        """Add a chapter/section title."""
        sizes = {1: 18, 2: 14, 3: 12, 4: 11, 5: 10, 6: 10}
        size = sizes.get(level, 10)

        self.set_font('Helvetica', 'B', size)

        if level == 1:
            self.set_text_color(44, 62, 80)
        else:
            self.set_text_color(52, 73, 94)

        self.ln(5)
        self.multi_cell(0, 8, title)
        self.ln(3)

    def body_text(self, text: str):
        """Add body paragraph text."""
        self.set_font('Helvetica', '', 10)
        self.set_text_color(51, 51, 51)
        self.multi_cell(0, 6, text)
        self.ln(2)

    def code_block(self, code: str, cell_number: int):
        """Add a code block with syntax highlighting effect."""
        # Cell number label
        self.set_font('Courier', '', 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, f'In [{cell_number}]:', new_x='LMARGIN', new_y='NEXT')

        # Code background
        self.set_fill_color(40, 44, 52)
        y_start = self.get_y()

        # Calculate code block height
        lines = code.strip().split('\n') if code.strip() else ['']
        line_height = 5
        block_height = len(lines) * line_height + 6

        # Check if we need a new page
        if self.get_y() + block_height > 270:
            self.add_page()
            y_start = self.get_y()

        # Draw background
        self.set_draw_color(40, 44, 52)
        self.rect(10, y_start, 190, block_height, 'F')

        # Code text with basic syntax coloring
        self.set_font('Courier', '', 9)
        self.set_xy(15, y_start + 3)

        for line in lines:
            self.set_text_color(171, 178, 191)  # Default text color
            self.cell(0, line_height, line[:100], new_x='LMARGIN', new_y='NEXT')  # Truncate long lines
            self.set_x(15)

        self.ln(5)

    def output_block(self, text: str, is_error: bool = False):
        """Add an output block."""
        self.set_font('Courier', '', 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, 'Out:', new_x='LMARGIN', new_y='NEXT')

        if is_error:
            self.set_fill_color(254, 241, 241)
            self.set_draw_color(231, 76, 60)
        else:
            self.set_fill_color(248, 249, 250)
            self.set_draw_color(39, 174, 96)

        y_start = self.get_y()
        lines = text.strip().split('\n')
        line_height = 5
        block_height = min(len(lines) * line_height + 6, 100)  # Cap height

        self.rect(10, y_start, 190, block_height, 'DF')

        if is_error:
            self.set_text_color(192, 57, 43)
        else:
            self.set_text_color(51, 51, 51)

        self.set_xy(15, y_start + 3)

        for i, line in enumerate(lines[:20]):  # Limit output lines
            self.cell(0, line_height, line[:100], new_x='LMARGIN', new_y='NEXT')  # Truncate
            self.set_x(15)

        if len(lines) > 20:
            self.set_text_color(100, 100, 100)
            self.cell(0, line_height, f'... ({len(lines) - 20} more lines)', new_x='LMARGIN', new_y='NEXT')

        self.ln(5)

    def image_output(self, image_data: str):
        """Add an image from base64 data."""
        try:
            img_bytes = base64.b64decode(image_data)
            img_file = io.BytesIO(img_bytes)

            # Save position before image
            x = self.get_x()
            y = self.get_y()

            # Calculate appropriate size
            self.image(img_file, x=x, y=y, w=150)
            self.ln(10)
        except Exception as e:
            self.body_text(f"[Image could not be rendered: {e}]")

    def table_of_contents(self, toc_items: list[tuple[int, str]]):
        """Add table of contents."""
        self.set_font('Helvetica', 'B', 16)
        self.set_text_color(44, 62, 80)
        self.cell(0, 10, 'Table of Contents', new_x='LMARGIN', new_y='NEXT')
        self.ln(5)

        self.set_font('Helvetica', '', 11)
        for level, title in toc_items:
            indent = (level - 1) * 8
            self.set_x(15 + indent)
            self.set_text_color(52, 152, 219)
            self.cell(0, 8, f'- {title}', new_x='LMARGIN', new_y='NEXT')

        self.ln(10)


class PDFGenerator:
    """Generates PDF from notebook cells."""

    def __init__(self, metadata: dict):
        self.metadata = metadata
        self.pdf = PDFBuilder(metadata['title'], metadata['author'])

    def generate(self, markdown_cells: list[MarkdownCell],
                 code_cells: list[CodeCell]) -> None:
        """Generate the PDF document."""
        self.pdf.add_page()

        # Title page header
        self._render_title_page()

        # Build sections and extract TOC
        all_cells = []
        for cell in markdown_cells:
            all_cells.append(('markdown', cell))
        for cell in code_cells:
            all_cells.append(('code', cell))

        all_cells.sort(key=lambda x: x[1].cell_number)

        # Extract TOC items
        toc_items = []
        for cell_type, cell in all_cells:
            if cell_type == 'markdown':
                headings = re.findall(r'^(#{1,6})\s+(.+)$', cell.source, re.MULTILINE)
                for hashes, title in headings:
                    level = len(hashes)
                    toc_items.append((level, title))

        # Table of Contents
        self.pdf.add_page()
        self.pdf.table_of_contents(toc_items)

        # Content
        for cell_type, cell in all_cells:
            if cell_type == 'markdown':
                self._render_markdown(cell)
            else:
                self._render_code_cell(cell)

    def _render_title_page(self):
        """Render the title/header section."""
        self.pdf.set_font('Helvetica', 'B', 24)
        self.pdf.set_text_color(44, 62, 80)
        self.pdf.ln(30)
        self.pdf.multi_cell(0, 12, self.metadata['title'], align='C')
        self.pdf.ln(10)

        self.pdf.set_font('Helvetica', '', 12)
        self.pdf.set_text_color(100, 100, 100)
        self.pdf.cell(0, 8, f"Author: {self.metadata['author']}", align='C', new_x='LMARGIN', new_y='NEXT')
        self.pdf.cell(0, 8, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", align='C', new_x='LMARGIN', new_y='NEXT')
        self.pdf.ln(20)

        # Horizontal line
        self.pdf.set_draw_color(52, 152, 219)
        self.pdf.set_line_width(1)
        self.pdf.line(50, self.pdf.get_y(), 160, self.pdf.get_y())

    def _render_markdown(self, cell: MarkdownCell):
        """Render a markdown cell."""
        source = cell.source

        # Split into lines and process
        lines = source.split('\n')
        current_text = []
        in_code_block = False
        code_content = []

        for line in lines:
            # Check for code blocks
            if line.strip().startswith('```'):
                if in_code_block:
                    # End code block
                    self._flush_text(current_text)
                    current_text = []
                    self._render_markdown_code('\n'.join(code_content))
                    code_content = []
                    in_code_block = False
                else:
                    # Start code block
                    self._flush_text(current_text)
                    current_text = []
                    in_code_block = True
                continue

            if in_code_block:
                code_content.append(line)
                continue

            # Check for headings
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if heading_match:
                self._flush_text(current_text)
                current_text = []
                level = len(heading_match.group(1))
                title = heading_match.group(2)
                self.pdf.chapter_title(title, level)
                continue

            # Check for list items
            list_match = re.match(r'^(\s*)[-*+]\s+(.+)$', line)
            if list_match:
                self._flush_text(current_text)
                current_text = []
                indent = len(list_match.group(1))
                text = list_match.group(2)
                self.pdf.set_x(15 + indent)
                self.pdf.set_font('Helvetica', '', 10)
                self.pdf.set_text_color(51, 51, 51)
                self.pdf.cell(0, 6, f'- {self._clean_markdown(text)}', new_x='LMARGIN', new_y='NEXT')
                continue

            # Check for tables
            if '|' in line and line.strip().startswith('|'):
                self._flush_text(current_text)
                current_text = []
                continue

            # Regular text
            current_text.append(line)

        self._flush_text(current_text)

    def _flush_text(self, lines: list):
        """Flush accumulated text lines."""
        if lines:
            text = '\n'.join(lines).strip()
            if text:
                self.pdf.body_text(self._clean_markdown(text))

    def _clean_markdown(self, text: str) -> str:
        """Remove markdown formatting from text."""
        # Remove bold/italic
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'\*(.+?)\*', r'\1', text)
        text = re.sub(r'__(.+?)__', r'\1', text)
        text = re.sub(r'_(.+?)_', r'\1', text)
        # Remove links
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        # Remove inline code
        text = re.sub(r'`([^`]+)`', r'\1', text)
        return text

    def _render_markdown_code(self, code: str):
        """Render code from markdown code blocks."""
        self.pdf.set_font('Courier', '', 9)
        self.pdf.set_fill_color(248, 249, 250)

        lines = code.strip().split('\n')
        y_start = self.pdf.get_y()
        line_height = 5
        block_height = len(lines) * line_height + 6

        self.pdf.rect(10, y_start, 190, block_height, 'F')

        self.pdf.set_text_color(51, 51, 51)
        self.pdf.set_xy(15, y_start + 3)

        for line in lines:
            self.pdf.cell(0, line_height, line[:100], new_x='LMARGIN', new_y='NEXT')
            self.pdf.set_x(15)

        self.pdf.ln(5)

    def _render_code_cell(self, cell: CodeCell):
        """Render a code cell and its outputs."""
        # Add code block
        self.pdf.code_block(cell.source, cell.cell_number)

        # Add outputs
        for output in cell.outputs:
            if output.output_type == 'image':
                self.pdf.image_output(output.content)
            elif output.output_type == 'error':
                self.pdf.output_block(output.content, is_error=True)
            else:
                self.pdf.output_block(output.content)

    def save(self, output_path: Path) -> None:
        """Save the PDF to a file."""
        self.pdf.output(str(output_path))


class NB2PDFAgent:
    """Main agent class that orchestrates the notebook to PDF conversion."""

    def __init__(self, notebook_path: Path, output_path: Optional[Path] = None):
        self.notebook_path = Path(notebook_path)
        self.output_path = output_path or Path(notebook_path).with_suffix('.pdf')

    def convert(self) -> Path:
        """Convert the notebook to PDF."""
        print(f"[Loading] Notebook: {self.notebook_path}")

        # Parse notebook
        parser = NotebookParser(self.notebook_path)
        parser.load()

        # Extract cells
        print("[Parsing] Extracting cells...")
        markdown_cells, code_cells = parser.extract_cells()
        metadata = parser.get_metadata()

        print(f"   Found {len(markdown_cells)} markdown cells")
        print(f"   Found {len(code_cells)} code cells")

        # Generate PDF
        print("[Creating] PDF...")
        generator = PDFGenerator(metadata)
        generator.generate(markdown_cells, code_cells)
        generator.save(self.output_path)

        print(f"[Done] PDF generated successfully: {self.output_path}")
        return self.output_path


def main():
    """CLI entry point for the agent."""
    parser = argparse.ArgumentParser(
        description='Convert Jupyter Notebook to professional PDF report',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
    python nb2pdf_agent.py notebook.ipynb
    python nb2pdf_agent.py notebook.ipynb output.pdf
    python nb2pdf_agent.py path/to/notebook.ipynb
        '''
    )

    parser.add_argument(
        'notebook',
        type=str,
        help='Path to the Jupyter notebook file (.ipynb)'
    )

    parser.add_argument(
        'output',
        type=str,
        nargs='?',
        help='Path for the output PDF file (default: notebook_name.pdf)'
    )

    args = parser.parse_args()

    notebook_path = Path(args.notebook)

    if not notebook_path.exists():
        print(f"[Error] Notebook file not found: {notebook_path}", file=sys.stderr)
        sys.exit(1)

    if notebook_path.suffix.lower() != '.ipynb':
        print(f"[Error] File must be a Jupyter notebook (.ipynb): {notebook_path}", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output) if args.output else None

    agent = NB2PDFAgent(notebook_path, output_path)

    try:
        result_path = agent.convert()
        print(f"\n[Success] Your PDF report is ready: {result_path}")
    except Exception as e:
        print(f"[Error] During conversion: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()