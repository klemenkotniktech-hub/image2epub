import os
import sys
import zipfile
from PIL import Image
from lxml import etree
import shutil
import uuid
from datetime import datetime
import mimetypes
import tempfile
import re

class ImageToEPUB:
    def __init__(self, image_files, cover_image_path=None, output_path=None):
        # Accepts a list of image files (full paths) and a cover image path
        if not image_files:
            raise ValueError("No images provided for EPUB generation.")
        self.image_files = image_files
        self.cover_image_path = cover_image_path or image_files[0]
        self.output_path = output_path or "output.epub"
        self.temp_dir = tempfile.mkdtemp()
        self.book_id = str(uuid.uuid4())
        self.width, self.height = self._get_image_dimensions(self.cover_image_path)

    # For backward compatibility
    @classmethod
    def from_chapter_folder(cls, chapter_path, output_path=None):
        chapter_path = os.path.abspath(chapter_path)
        if not os.path.isdir(chapter_path):
            raise ValueError(f"Chapter directory not found: {chapter_path}")
        image_files = cls._get_sorted_images_static(chapter_path)
        return cls(image_files, cover_image_path=image_files[0] if image_files else None, output_path=output_path)

    @staticmethod
    def _get_sorted_images_static(chapter_path):
        image_extensions = ('.jpg', '.jpeg', '.png', '.webp')
        images = [f for f in os.listdir(chapter_path) if f.lower().endswith(image_extensions)]
        
        def extract_chapter_number(filename):
            # Extract chapter number (supports decimal chapters like 99.5)
            # Try multiple patterns to match different chapter naming conventions
            patterns = [
                r'Chapter\s*(\d+(?:\.\d+)?)',  # Chapter 99, Chapter 99.5
                r'\s*(\d+(?:\.\d+)?)',         # 99, 99.5
                r'\b(\d+(?:\.\d+)?)\b'        # Any number that's not part of another word
            ]
            
            for pattern in patterns:
                match = re.search(pattern, filename, re.IGNORECASE)
                if match:
                    try:
                        # Convert to float if it contains a decimal point
                        return float(match.group(1))
                    except ValueError:
                        continue
            
            # Fallback to original sorting if no chapter number found
            return float(''.join(c for c in filename if c.isdigit()) or 0)
        
        # Sort images by chapter number (float values)
        images.sort(key=extract_chapter_number)
        return [os.path.join(chapter_path, img) for img in images]

    def __del__(self):
        # Cleanup temporary directory
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _get_sorted_images(self):
        image_extensions = ('.jpg', '.jpeg', '.png', '.webp')
        images = [f for f in os.listdir(self.chapter_path) if f.lower().endswith(image_extensions)]
        
        def extract_chapter_number(filename):
            # Extract chapter number (supports decimal chapters like 99.5)
            # Try multiple patterns to match different chapter naming conventions
            patterns = [
                r'Chapter\s*(\d+(?:\.\d+)?)',  # Chapter 99, Chapter 99.5
                r'\s*(\d+(?:\.\d+)?)',         # 99, 99.5
                r'\b(\d+(?:\.\d+)?)\b'        # Any number that's not part of another word
            ]
            
            for pattern in patterns:
                match = re.search(pattern, filename, re.IGNORECASE)
                if match:
                    try:
                        # Convert to float if it contains a decimal point
                        return float(match.group(1))
                    except ValueError:
                        continue
            
            # Fallback to original sorting if no chapter number found
            return float(''.join(c for c in filename if c.isdigit()) or 0)
        
        # Sort images by chapter number (float values)
        images.sort(key=extract_chapter_number)
        return [os.path.join(self.chapter_path, img) for img in images]

    def _get_image_dimensions(self, image_path):
        with Image.open(image_path) as img:
            return img.size

    def _get_mime_type(self, filename):
        mime_type = mimetypes.guess_type(filename)[0]
        return mime_type or 'application/octet-stream'

    def _create_container_xml(self):
        container = etree.Element('container',
                                version="1.0",
                                xmlns="urn:oasis:names:tc:opendocument:xmlns:container")
        rootfiles = etree.SubElement(container, 'rootfiles')
        etree.SubElement(rootfiles, 'rootfile',
                        {'full-path': 'OEBPS/content.opf',
                         'media-type': 'application/oebps-package+xml'})
        return etree.tostring(container, encoding='utf-8', xml_declaration=True)

    def _create_content_opf(self, manifest_items, spine_items):
        package = etree.Element('package',
                              {'version': "3.0",
                               'xmlns': "http://www.idpf.org/2007/opf",
                               'prefix': "rendition: http://www.idpf.org/vocab/rendition/#",
                               'unique-identifier': "book-id"})

        # Metadata
        NSMAP = {
            'dc': "http://purl.org/dc/elements/1.1/",
            'opf': "http://www.idpf.org/2007/opf"
        }
        metadata = etree.SubElement(package, 'metadata', nsmap=NSMAP)

        DC = "http://purl.org/dc/elements/1.1/"
        etree.SubElement(metadata, f'{{{DC}}}identifier', id="book-id").text = self.book_id
        book_title = os.path.splitext(os.path.basename(self.output_path))[0]
        etree.SubElement(metadata, f'{{{DC}}}title').text = book_title
        etree.SubElement(metadata, f'{{{DC}}}language').text = 'en'
        etree.SubElement(metadata, f'{{{DC}}}creator').text = 'epubConverter'
        etree.SubElement(metadata, 'meta', property='dcterms:modified').text = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        etree.SubElement(metadata, 'meta', property='rendition:layout').text = 'pre-paginated'
        etree.SubElement(metadata, 'meta', property='rendition:orientation').text = 'portrait'

        # Manifest
        manifest = etree.SubElement(package, 'manifest')
        for item in manifest_items:
            etree.SubElement(manifest, 'item', item)

        # Spine
        spine = etree.SubElement(package, 'spine')
        for idref in spine_items:
            etree.SubElement(spine, 'itemref', idref=idref, properties='page-spread-right')

        return etree.tostring(package, encoding='utf-8', xml_declaration=True)

    def _create_nav_xhtml(self, pages):
        NSMAP = {None: 'http://www.w3.org/1999/xhtml',
                 'epub': 'http://www.idpf.org/2007/ops'}
        
        html = etree.Element('html', nsmap=NSMAP)
        head = etree.SubElement(html, 'head')
        etree.SubElement(head, 'title').text = 'Navigation'
        
        body = etree.SubElement(html, 'body')
        EPUB = "http://www.idpf.org/2007/ops"
        nav = etree.SubElement(body, 'nav',
                             attrib={
                                 f'{{{EPUB}}}type': 'toc',
                                 'id': 'toc'
                             })
        
        h1 = etree.SubElement(nav, 'h1')
        h1.text = "Table of Contents"
        
        ol = etree.SubElement(nav, 'ol')
        
        # Add all pages (including page 1)
        for i in range(1, len(pages) + 1):
            li = etree.SubElement(ol, 'li')
            a = etree.SubElement(li, 'a', href=f"page_{i:03d}.xhtml")
            a.text = f"Page {i}"
            
        return etree.tostring(html, encoding='utf-8', xml_declaration=True,
                            doctype='<!DOCTYPE html>')

    def _create_page_xhtml(self, image_path, page_num=None, is_cover=False):
        NSMAP = {None: 'http://www.w3.org/1999/xhtml'}
        
        html = etree.Element('html', nsmap=NSMAP)
        head = etree.SubElement(html, 'head')
        
        title_text = "Cover" if is_cover else f"Page {page_num}"
        etree.SubElement(head, 'title').text = title_text
        
        # Add viewport and fixed-layout metadata
        etree.SubElement(head, 'meta',
                        name="viewport",
                        content=f"width={self.width}, height={self.height}")
        
        # Add style
        style = etree.SubElement(head, 'style')
        style.text = f"""
            @page {{ margin: 0; padding: 0; size: {self.width}px {self.height}px; }}
            body {{ margin: 0; padding: 0; width: 100%; height: 100%; 
                   display: flex; align-items: center; justify-content: center; }}
            img {{ max-width: 100%; max-height: 100%; object-fit: contain; }}
        """
        
        body = etree.SubElement(html, 'body')
        image_filename = os.path.basename(image_path)
        etree.SubElement(body, 'img',
                        src=f"images/{image_filename}",
                        alt=title_text)
        
        return etree.tostring(html, encoding='utf-8', xml_declaration=True,
                            doctype='<!DOCTYPE html>')

    def create_epub(self):
        if not self.image_files:
            print("No image files found in the chapter directory.")
            return False

        try:
            # Create necessary directories in temp folder
            os.makedirs(os.path.join(self.temp_dir, 'META-INF'))
            os.makedirs(os.path.join(self.temp_dir, 'OEBPS/images'))

            # Create container.xml
            with open(os.path.join(self.temp_dir, 'META-INF/container.xml'), 'wb') as f:
                f.write(self._create_container_xml())

            # Prepare manifest items and spine
            manifest_items = []
            spine_items = []

            # Add nav document to manifest
            manifest_items.append({
                'id': 'nav',
                'href': 'nav.xhtml',
                'media-type': 'application/xhtml+xml',
                'properties': 'nav'
            })

            # Add cover image to manifest with cover-image property
            cover_image_path = self.image_files[0]
            cover_image_filename = os.path.basename(cover_image_path)
            manifest_items.append({
                'id': 'cover-image',
                'href': f'images/{cover_image_filename}',
                'media-type': self._get_mime_type(cover_image_filename),
                'properties': 'cover-image'
            })
            shutil.copy2(
                cover_image_path,
                os.path.join(self.temp_dir, 'OEBPS/images', cover_image_filename)
            )

            # Add all images to manifest (except cover-image, which is already added)
            for i, image_path in enumerate(self.image_files):
                if i == 0:
                    continue  # already added as cover-image
                image_filename = os.path.basename(image_path)
                manifest_items.append({
                    'id': f'image_{i+1:03d}',
                    'href': f'images/{image_filename}',
                    'media-type': self._get_mime_type(image_filename)
                })
                shutil.copy2(
                    image_path,
                    os.path.join(self.temp_dir, 'OEBPS/images', image_filename)
                )

            # Create XHTML pages: page 1 uses cover image, then continue with the rest
            xhtml_filenames = []
            for i, image_path in enumerate(self.image_files):
                page_num = i + 1
                xhtml_filename = f'page_{page_num:03d}.xhtml'
                xhtml_content = self._create_page_xhtml(
                    image_path,
                    page_num=page_num,
                    is_cover=False
                )
                with open(os.path.join(self.temp_dir, 'OEBPS', xhtml_filename), 'wb') as f:
                    f.write(xhtml_content)
                # Add XHTML to manifest and spine
                manifest_items.append({
                    'id': f'page_{page_num:03d}',
                    'href': xhtml_filename,
                    'media-type': 'application/xhtml+xml'
                })
                spine_items.append(f'page_{page_num:03d}')
                xhtml_filenames.append(xhtml_filename)

            # Create and save nav.xhtml
            nav_content = self._create_nav_xhtml(self.image_files)
            with open(os.path.join(self.temp_dir, 'OEBPS/nav.xhtml'), 'wb') as f:
                f.write(nav_content)

            # Create content.opf
            content_opf = self._create_content_opf(manifest_items, spine_items)
            with open(os.path.join(self.temp_dir, 'OEBPS/content.opf'), 'wb') as f:
                f.write(content_opf)

            # Create mimetype file
            with open(os.path.join(self.temp_dir, 'mimetype'), 'w') as f:
                f.write('application/epub+zip')

            # Create EPUB (ZIP) file
            print(f"Creating EPUB file: {self.output_path}")
            with zipfile.ZipFile(self.output_path, 'w', zipfile.ZIP_DEFLATED) as epub:
                # Add mimetype first, uncompressed
                epub.write(
                    os.path.join(self.temp_dir, 'mimetype'),
                    'mimetype',
                    compress_type=zipfile.ZIP_STORED
                )

                # Add all other files
                for root, _, files in os.walk(self.temp_dir):
                    for file in files:
                        if file == 'mimetype':
                            continue
                        file_path = os.path.join(root, file)
                        arc_name = os.path.relpath(file_path, self.temp_dir)
                        epub.write(file_path, arc_name)

            print(f"Successfully created: {self.output_path}")
            return True

        except Exception as e:
            print(f"Error creating EPUB: {e}", file=sys.stderr)
            return False

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Convert image book (multiple chapters) to fixed-layout EPUB')
    parser.add_argument('--input-book', required=True, help='Path to the book folder containing chapter folders')
    parser.add_argument('--start-chapter', required=True, type=int, help='Start chapter number (inclusive)')
    parser.add_argument('--end-chapter', required=True, type=int, help='End chapter number (inclusive)')
    parser.add_argument('--output-name', help='Output EPUB file name (default: <parent_folder_name>.epub)')
    parser.add_argument('--output-dir', help='Output directory (default: current directory)')
    args = parser.parse_args()

    import re
    input_book = os.path.abspath(args.input_book)
    if not os.path.isdir(input_book):
        print(f"Book folder not found: {input_book}", file=sys.stderr)
        return 1
    # Find chapter folders in the book directory
    chapter_dirs = []
    chapter_num_map = {}
    for entry in os.listdir(input_book):
        full_path = os.path.join(input_book, entry)
        if os.path.isdir(full_path):
            # Extract chapter number (supports decimal chapters like 99.5)
            # Try multiple patterns to match different chapter naming conventions
            patterns = [
                r'Chapter\s*(\d+(?:\.\d+)?)',  # Chapter 99, Chapter 99.5
                r'\s*(\d+(?:\.\d+)?)',         # 99, 99.5
                r'\b(\d+(?:\.\d+)?)\b'        # Any number that's not part of another word
            ]
            
            chapter_num = None
            for pattern in patterns:
                match = re.search(pattern, entry, re.IGNORECASE)
                if match:
                    try:
                        # Convert to float if it contains a decimal point
                        chapter_num = float(match.group(1))
                        break
                    except ValueError:
                        continue
            
            if chapter_num is not None:
                chapter_num_map[chapter_num] = full_path
    # Select chapters in the specified range
    selected_chapters = [chapter_num_map[num] for num in sorted(chapter_num_map) if args.start_chapter <= num <= args.end_chapter]
    if not selected_chapters:
        print("No chapters found in the specified range.", file=sys.stderr)
        return 1
    #else:
    #    for chapter in selected_chapters:
    #        print(f"Selected chapter: {chapter}")

    # Collect images from all selected chapters, in order
    all_images = []
    for chap_dir in selected_chapters:
        imgs = ImageToEPUB._get_sorted_images_static(chap_dir)
        all_images.extend(imgs)
    if not all_images:
        print("No images found in the selected chapters.", file=sys.stderr)
        return 1
    # Use first image of start chapter as cover
    cover_image = ImageToEPUB._get_sorted_images_static(selected_chapters[0])[0]
    # Determine output file name
    if args.output_name:
        output_name = args.output_name if args.output_name.lower().endswith('.epub') else args.output_name + '.epub'
    else:
        parent_folder = os.path.basename(os.path.normpath(input_book))
        output_name = parent_folder + '.epub'
    # Determine output location
    output_dir = os.path.abspath(args.output_dir) if args.output_dir else os.getcwd()
    output_path = os.path.join(output_dir, output_name)
    try:
        converter = ImageToEPUB(all_images, cover_image_path=cover_image, output_path=output_path)
        converter.create_epub()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0

# For backward compatibility, allow old usage
# Usage: python epubConverter.py <chapter_path> [-o output]
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and not sys.argv[1].startswith('--'):
        # Old usage: chapter_path [-o output]
        import argparse
        parser = argparse.ArgumentParser(description='Convert chapter to fixed-layout EPUB (legacy mode)')
        parser.add_argument('chapter_path', help='Path to the chapter directory containing images')
        parser.add_argument('-o', '--output', help='Output EPUB file path (default: <chapter_name>.epub)')
        args = parser.parse_args()
        try:
            converter = ImageToEPUB.from_chapter_folder(args.chapter_path, args.output)
            converter.create_epub()
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        sys.exit(0)
    else:
        sys.exit(main())

if __name__ == "__main__":
    sys.exit(main())