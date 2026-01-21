from pathlib import Path


def create_svg(color: str, size: int = 100) -> str:
    """Generate a simple colored SVG square."""
    return f'''<svg width="{size}" height="{size}" xmlns="http://www.w3.org/2000/svg">
  <rect width="{size}" height="{size}" fill="{color}"/>
  <text x="50%" y="50%" text-anchor="middle" dy=".3em" fill="white" font-size="16">{color.upper()}</text>
</svg>'''


def create_png_placeholder() -> bytes:
    """Create a minimal valid PNG (1x1 red pixel)."""
    return bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
        0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
        0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,
        0x54, 0x08, 0xD7, 0x63, 0xF8, 0xCF, 0xC0, 0x00,
        0x00, 0x03, 0x01, 0x01, 0x00, 0x18, 0xDD, 0x8D,
        0xB4, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,
        0x44, 0xAE, 0x42, 0x60, 0x82
    ])


def setup_test_environment():
    """Create test files in 4_html_processing/html/ directory."""
    # Use existing structure
    base = Path('4_html_processing/html')
    
    if not base.exists():
        print(f"❌ Directory not found: {base}")
        print("Creating it now...")
        base.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 Using existing structure: {base.absolute()}")
    
    # Create subdirectories
    assets_dir = base / 'assets'
    nested_dir = base / 'nested' / 'deep'
    
    assets_dir.mkdir(parents=True, exist_ok=True)
    nested_dir.mkdir(parents=True, exist_ok=True)
    
    # ===== Create image assets =====
    print("🖼️  Generating test images...")
    
    # SVG files in assets/
    (assets_dir / 'red.svg').write_text(create_svg('red'), encoding='utf-8')
    (assets_dir / 'green.svg').write_text(create_svg('green'), encoding='utf-8')
    (assets_dir / 'blue.svg').write_text(create_svg('blue'), encoding='utf-8')
    
    # PNG file
    (assets_dir / 'icon.png').write_bytes(create_png_placeholder())
    
    # SVG in nested directory
    (nested_dir / 'yellow.svg').write_text(create_svg('yellow'), encoding='utf-8')
    
    # ===== Create HTML test files =====
    print("📄 Creating HTML test files...")
    
    # Test 1: Basic functionality
    html1 = '''<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Test 1: Basic Images</title>
</head>
<body>
  <h1>Test 1: Multiple Local Images</h1>
  <p>This page has three local SVG images that should be inlined.</p>
  <img src="assets/red.svg" alt="Red square">
  <img src="assets/green.svg" alt="Green square">
  <img src="assets/blue.svg" alt="Blue square">
</body>
</html>'''
    (base / 'test_basic.html').write_text(html1, encoding='utf-8')
    
    # Test 2: Mixed content
    html2 = '''<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Test 2: Mixed Sources</title>
</head>
<body>
  <h1>Test 2: Mixed Image Sources</h1>
  
  <h2>Local images (should be inlined)</h2>
  <img src="assets/red.svg" alt="Local red">
  <img src="assets/icon.png" alt="Local PNG">
  
  <h2>Remote image (should NOT be inlined)</h2>
  <img src="https://via.placeholder.com/150" alt="Remote placeholder">
  
  <h2>Already data URI (should remain unchanged)</h2>
  <img src="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KICA8cmVjdCB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgZmlsbD0iZ3JheSIvPgo8L3N2Zz4=" alt="Already encoded">
  
  <h2>Missing image (should fail gracefully)</h2>
  <img src="assets/nonexistent.svg" alt="Missing file">
  
  <h2>Empty src (should fail)</h2>
  <img src="" alt="Empty source">
  <img alt="No src attribute">
</body>
</html>'''
    (base / 'test_mixed.html').write_text(html2, encoding='utf-8')
    
    # Test 3: Relative paths (FIXED - now points to correct location)
    html3 = '''<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Test 3: Relative Paths</title>
</head>
<body>
  <h1>Test 3: Relative Path Resolution</h1>
  <p>Testing different relative path styles:</p>
  
  <h2>Parent directory (../../assets/red.svg)</h2>
  <img src="../../assets/red.svg" alt="Parent directory">
  
  <h2>Same directory (./yellow.svg)</h2>
  <img src="./yellow.svg" alt="Same directory with dot">
  
  <h2>Same directory (yellow.svg)</h2>
  <img src="yellow.svg" alt="Same directory no dot">
</body>
</html>'''
    (nested_dir / 'test_relative.html').write_text(html3, encoding='utf-8')
    
    # Test 4: Tag variants
    html4 = '''<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Test 4: Tag Variants</title>
</head>
<body>
  <h1>Test 4: Different Image Tag Styles</h1>
  
  <h2>Self-closing tag</h2>
  <img src="assets/red.svg" alt="Self closing" />
  
  <h2>Regular opening tag</h2>
  <img src="assets/green.svg" alt="Regular tag">
  
  <h2>With multiple attributes</h2>
  <img src="assets/blue.svg" alt="Blue" width="200" height="200" class="test-class" id="test-id">
  
  <h2>With query string (should be cleaned)</h2>
  <img src="assets/red.svg?version=1.0" alt="With query">
  
  <h2>With fragment (should be cleaned)</h2>
  <img src="assets/green.svg#layer1" alt="With fragment">
</body>
</html>'''
    (base / 'test_tags.html').write_text(html4, encoding='utf-8')
    
    # Test 5: Special characters
    html5 = '''<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Test 5: Special Characters</title>
</head>
<body>
  <h1>Test 5: Caracteres Especiales y Codificación</h1>
  <p>Página con tildes, eñes y símbolos: áéíóú ñ ¿¡</p>
  <img src="assets/blue.svg" alt="Azul con descripción española">
  <p>Testing UTF-8 encoding: 日本語 中文 العربية Ελληνικά</p>
</body>
</html>'''
    (base / 'test_encoding.html').write_text(html5, encoding='utf-8')
    
    # Test 6: No images
    html6 = '''<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Test 6: No Images</title>
</head>
<body>
  <h1>Test 6: Page Without Images</h1>
  <p>This page has no images. The processor should handle it gracefully.</p>
  <div>Just some regular content here.</div>
</body>
</html>'''
    (base / 'test_no_images.html').write_text(html6, encoding='utf-8')
    
    print("✅ Test environment created successfully!")
    print(f"\n📍 Location: {base.absolute()}")
    print("\n📋 Structure created:")
    print(f"   4_html_processing/")
    print(f"   └── html/")
    print(f"       ├── test_basic.html")
    print(f"       ├── test_mixed.html")
    print(f"       ├── test_tags.html")
    print(f"       ├── test_encoding.html")
    print(f"       ├── test_no_images.html")
    print(f"       ├── assets/")
    print(f"       │   ├── red.svg")
    print(f"       │   ├── green.svg")
    print(f"       │   ├── blue.svg")
    print(f"       │   └── icon.png")
    print(f"       └── nested/")
    print(f"           └── deep/")
    print(f"               ├── test_relative.html")
    print(f"               └── yellow.svg")
    
    return base


if __name__ == '__main__':
    test_dir = setup_test_environment()
    
    print("\n" + "="*70)
    print("🚀 READY TO TEST!")
    print("="*70)
    print("\nNow run these commands:\n")
    
    print("1️⃣  Process all HTML files in the html/ directory:")
    print(f"   python 4_html_processing/html_pipeline.py --paths 4_html_processing/html --report 4_html_processing/report.json --verbose\n")
    
    print("2️⃣  Process a single file:")
    print(f"   python 4_html_processing/html_pipeline.py --paths 4_html_processing/html/test_basic.html --verbose\n")
    
    print("3️⃣  Process only the nested directory:")
    print(f"   python 4_html_processing/html_pipeline.py --paths 4_html_processing/html/nested --verbose\n")
    
    print("📊 Expected results:")
    print(f"   - *_inlined.html files created inside 4_html_processing/html/")
    print(f"   - report.json created at 4_html_processing/report.json")
    print(f"   - All images in assets/ should be successfully inlined")
    print(f"   - test_relative.html now uses correct path: ../../assets/red.svg")