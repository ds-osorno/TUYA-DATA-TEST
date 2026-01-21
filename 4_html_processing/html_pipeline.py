import argparse
import base64
import json
import logging
import mimetypes
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from typing import List, Dict, Optional, Tuple


class ProcessingReport:
    """Tracks successful and failed image processing operations."""
    
    def __init__(self):
        self.data = {"success": {}, "fail": {}}
    
    def log_success(self, html_file: Path, image_src: str):
        """Record a successfully processed image."""
        key = str(html_file)
        if key not in self.data["success"]:
            self.data["success"][key] = []
        self.data["success"][key].append(image_src)
    
    def log_failure(self, html_file: Path, image_src: str, reason: str):
        """Record a failed image processing attempt."""
        key = str(html_file)
        if key not in self.data["fail"]:
            self.data["fail"][key] = {}
        self.data["fail"][key][image_src] = reason
    
    def to_dict(self) -> dict:
        """Return the report as a dictionary."""
        return self.data
    
    def save_to_file(self, path: Path):
        """Save report to a JSON file."""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)


class ImageProcessor:
    """Handles image file reading and base64 encoding."""
    
    @staticmethod
    def is_remote_url(src: str) -> bool:
        """Check if the source is a remote URL."""
        normalized = src.strip().lower()
        return normalized.startswith(('http://', 'https://'))
    
    @staticmethod
    def is_data_uri(src: str) -> bool:
        """Check if the source is already a data URI."""
        return src.strip().lower().startswith('data:')
    
    @staticmethod
    def clean_path(src: str) -> str:
        """Remove fragments, query strings, and file:// protocol from path."""
        cleaned = src.strip()
        # Remove fragment identifier
        cleaned = cleaned.split('#')[0]
        # Remove query string
        cleaned = cleaned.split('?')[0]
        # Remove file:// protocol if present
        if cleaned.lower().startswith('file://'):
            cleaned = cleaned[7:]
        return cleaned
    
    @staticmethod
    def get_mime_type(file_path: Path) -> str:
        """Guess MIME type from file extension."""
        mime_type, _ = mimetypes.guess_type(str(file_path))
        return mime_type or 'application/octet-stream'
    
    @classmethod
    def encode_to_data_uri(cls, file_path: Path) -> str:
        """Read image file and encode as data URI."""
        raw_data = file_path.read_bytes()
        encoded = base64.b64encode(raw_data).decode('ascii')
        mime = cls.get_mime_type(file_path)
        return f"data:{mime};base64,{encoded}"


class HTMLImageInliner(HTMLParser):
    """
    Custom HTML parser that inlines image sources as base64 data URIs.
    """
    
    def __init__(self, html_file: Path, report: ProcessingReport):
        super().__init__(convert_charrefs=True)
        self.html_file = html_file
        self.base_directory = html_file.parent
        self.report = report
        self.output_parts = []
        self.processor = ImageProcessor()
    
    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        """Handle opening tags, with special processing for <img>."""
        if tag.lower() == 'img':
            self.output_parts.append(self._process_img_tag(tag, attrs, self_closing=False))
        else:
            self.output_parts.append(self._rebuild_tag(tag, attrs, self_closing=False))
    
    def handle_startendtag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        """Handle self-closing tags."""
        if tag.lower() == 'img':
            self.output_parts.append(self._process_img_tag(tag, attrs, self_closing=True))
        else:
            self.output_parts.append(self._rebuild_tag(tag, attrs, self_closing=True))
    
    def handle_endtag(self, tag: str):
        """Handle closing tags."""
        self.output_parts.append(f"</{tag}>")
    
    def handle_data(self, data: str):
        """Handle text content between tags."""
        self.output_parts.append(data)
    
    def handle_comment(self, data: str):
        """Preserve HTML comments."""
        self.output_parts.append(f"<!--{data}-->")
    
    def handle_decl(self, decl: str):
        """Preserve DOCTYPE and other declarations."""
        self.output_parts.append(f"<!{decl}>")
    
    def get_processed_html(self) -> str:
        """Return the complete processed HTML."""
        return ''.join(self.output_parts)
    
    def _rebuild_tag(self, tag: str, attrs: List[Tuple[str, Optional[str]]], 
                     self_closing: bool) -> str:
        """Reconstruct an HTML tag from its components."""
        parts = [f"<{tag}"]
        
        for key, value in attrs:
            if value is None:
                parts.append(f" {key}")
            else:
                escaped_value = escape(value, quote=True)
                parts.append(f' {key}="{escaped_value}"')
        
        parts.append(" />" if self_closing else ">")
        return ''.join(parts)
    
    def _process_img_tag(self, tag: str, attrs: List[Tuple[str, Optional[str]]], 
                         self_closing: bool) -> str:
        """
        Process an <img> tag, converting local src to data URI if possible.
        Returns the modified tag as a string.
        """
        # Convert attrs to dict for easier access
        attrs_dict = {k: (v or '') for k, v in attrs}
        src = attrs_dict.get('src', '').strip()
        
        # No src attribute or empty src
        if not src:
            self.report.log_failure(self.html_file, '(empty)', 
                                   'Image tag has no src attribute')
            return self._rebuild_tag(tag, attrs, self_closing)
        
        # Already a data URI - leave as is
        if self.processor.is_data_uri(src):
            return self._rebuild_tag(tag, attrs, self_closing)
        
        # Remote URL - can't inline
        if self.processor.is_remote_url(src):
            self.report.log_failure(self.html_file, src, 
                                   'Remote URLs cannot be inlined')
            return self._rebuild_tag(tag, attrs, self_closing)
        
        # Try to resolve and inline local image
        try:
            data_uri = self._inline_local_image(src)
            if data_uri:
                # Replace src attribute with data URI
                new_attrs = [(k, data_uri if k.lower() == 'src' else v) 
                            for k, v in attrs]
                self.report.log_success(self.html_file, src)
                return self._rebuild_tag(tag, new_attrs, self_closing)
            else:
                return self._rebuild_tag(tag, attrs, self_closing)
        except Exception as e:
            self.report.log_failure(self.html_file, src, 
                                   f'Unexpected error: {str(e)}')
            return self._rebuild_tag(tag, attrs, self_closing)
    
    def _inline_local_image(self, src: str) -> Optional[str]:
        """
        Attempt to read a local image and convert to data URI.
        Returns None if the operation fails.
        """
        cleaned_src = self.processor.clean_path(src)
        image_path = Path(cleaned_src)
        
        # Resolve relative paths
        if not image_path.is_absolute():
            image_path = (self.base_directory / image_path).resolve()
        
        # Check if file exists
        if not image_path.exists() or not image_path.is_file():
            self.report.log_failure(self.html_file, src, 
                                   f'File not found: {image_path}')
            return None
        
        # Try to encode
        try:
            return self.processor.encode_to_data_uri(image_path)
        except Exception as e:
            self.report.log_failure(self.html_file, src, 
                                   f'Encoding failed: {str(e)}')
            return None


class HTMLFileFinder:
    """Utility for finding HTML files in paths and directories."""
    
    @staticmethod
    def is_html_file(path: Path) -> bool:
        """Check if a path points to an HTML file."""
        return path.is_file() and path.suffix.lower() in ('.html', '.htm')
    
    @classmethod
    def find_html_files(cls, paths: List[str]) -> List[Path]:
        """
        Find all HTML files from a list of paths (files or directories).
        Returns a deduplicated list of resolved paths.
        """
        found_files = []
        
        for path_str in paths:
            path = Path(path_str)
            
            if not path.exists():
                logging.warning(f"Path does not exist: {path}")
                continue
            
            if path.is_file():
                if cls.is_html_file(path):
                    found_files.append(path.resolve())
                else:
                    logging.warning(f"Not an HTML file: {path}")
            else:
                # Directory - search recursively
                for pattern in ('*.html', '*.htm'):
                    for html_file in path.rglob(pattern):
                        if html_file.is_file():
                            found_files.append(html_file.resolve())
        
        # Remove duplicates while preserving order
        seen = set()
        unique_files = []
        for f in found_files:
            if f not in seen:
                unique_files.append(f)
                seen.add(f)
        
        return unique_files


class OutputFileManager:
    """Manages output file naming to avoid overwriting."""
    
    @staticmethod
    def get_output_path(input_file: Path) -> Path:
        """
        Generate a unique output filename next to the input file.
        Adds _ok suffix, with numerical suffix if file exists.
        """
        output_dir = input_file.parent
        base_name = input_file.stem + '_ok'
        
        # Try base name first
        candidate = output_dir / (base_name + input_file.suffix)
        if not candidate.exists():
            return candidate
        
        # Add numerical suffix if needed
        for i in range(2, 1000):
            candidate = output_dir / (f"{base_name}_{i}{input_file.suffix}")
            if not candidate.exists():
                return candidate
        
        raise RuntimeError(f"Too many output files for {input_file.name}")


class HTMLProcessor:
    """Main processor that coordinates HTML file processing."""
    
    def __init__(self, report: ProcessingReport):
        self.report = report
        self.logger = logging.getLogger(__name__)
    
    def process_file(self, html_file: Path) -> Optional[Path]:
        """
        Process a single HTML file, inlining images.
        Returns the output file path on success, None on failure.
        """
        # Read HTML content
        try:
            html_content = self._read_html_file(html_file)
        except Exception as e:
            self.report.log_failure(html_file, '(file read)', 
                                   f'Could not read HTML file: {str(e)}')
            return None
        
        # Parse and process
        parser = HTMLImageInliner(html_file, self.report)
        try:
            parser.feed(html_content)
            parser.close()
        except Exception as e:
            self.report.log_failure(html_file, '(parsing)', 
                                   f'Invalid HTML structure: {str(e)}')
            return None
        
        # Write output
        try:
            output_path = OutputFileManager.get_output_path(html_file)
            output_path.write_text(parser.get_processed_html(), encoding='utf-8')
            return output_path
        except Exception as e:
            self.report.log_failure(html_file, '(file write)', 
                                   f'Could not write output: {str(e)}')
            return None
    
    @staticmethod
    def _read_html_file(path: Path) -> str:
        """Read HTML file with fallback encoding."""
        raw_bytes = path.read_bytes()
        try:
            return raw_bytes.decode('utf-8')
        except UnicodeDecodeError:
            # Fallback to latin-1 with replacement for invalid chars
            return raw_bytes.decode('latin-1', errors='replace')


def setup_logging(verbose: bool):
    """Configure logging based on verbosity level."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(levelname)s - %(message)s'
    )


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Process HTML files to inline images as base64 data URIs'
    )
    parser.add_argument(
        '--paths',
        nargs='+',
        required=True,
        help='HTML files and/or directories to process'
    )
    parser.add_argument(
        '--report',
        default='',
        help='Optional path to save JSON report'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    return parser.parse_args()


def main():
    """Main entry point for the HTML processor."""
    args = parse_arguments()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Find HTML files
    html_files = HTMLFileFinder.find_html_files(args.paths)
    if not html_files:
        logger.error("No HTML files found in the specified paths")
        raise SystemExit(2)
    
    logger.info(f"Found {len(html_files)} HTML file(s) to process")
    
    # Process files
    report = ProcessingReport()
    processor = HTMLProcessor(report)
    success_count = 0
    
    for html_file in html_files:
        output_path = processor.process_file(html_file)
        if output_path:
            success_count += 1
            logger.info(f"✓ {html_file.name} -> {output_path.name}")
        else:
            logger.warning(f"✗ Failed to process {html_file.name}")
    
    # Print report to console
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    
    # Save report if requested
    if args.report:
        try:
            report.save_to_file(Path(args.report))
            logger.info(f"Report saved to: {args.report}")
        except Exception as e:
            logger.warning(f"Could not save report: {str(e)}")
    
    logger.info(f"Processing complete: {success_count}/{len(html_files)} successful")


if __name__ == '__main__':
    main()
