import os

# Placeholder SVG images as strings
COVER_IMAGE_SVG = '''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg width="800" height="400" xmlns="http://www.w3.org/2000/svg">
    <rect width="100%" height="100%" fill="#f0f0f0"/>
    <rect x="50" y="50" width="700" height="300" fill="#e0e0e0" rx="10"/>
    <text x="400" y="200" font-family="Arial" font-size="24" text-anchor="middle" fill="#666">
        Room Cover Image Placeholder
    </text>
</svg>'''

GALLERY_IMAGE_SVG = '''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
    <rect width="100%" height="100%" fill="#f5f5f5"/>
    <rect x="25" y="25" width="350" height="250" fill="#e5e5e5" rx="10"/>
    <text x="200" y="150" font-family="Arial" font-size="18" text-anchor="middle" fill="#777">
        Gallery Image Placeholder
    </text>
</svg>'''

def save_placeholder_images(static_dir):
    """Save placeholder SVG images to static directory"""
    # Create directories if they don't exist
    os.makedirs(static_dir, exist_ok=True)
    placeholder_dir = os.path.join(static_dir, "placeholders")
    os.makedirs(placeholder_dir, exist_ok=True)
    
    # Save cover image placeholder
    cover_path = os.path.join(placeholder_dir, "cover.svg")
    with open(cover_path, "w") as f:
        f.write(COVER_IMAGE_SVG)
    
    # Save gallery image placeholder
    gallery_path = os.path.join(placeholder_dir, "gallery.svg")
    with open(gallery_path, "w") as f:
        f.write(GALLERY_IMAGE_SVG)
    
    return {
        "cover": os.path.join("static", "placeholders", "cover.svg"),
        "gallery": os.path.join("static", "placeholders", "gallery.svg")
    } 