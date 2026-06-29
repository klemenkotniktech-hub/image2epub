# image2epub

A simple tool to convert folders of images into a fixed-layout EPUB format for manga.

## Project purpose

Convert images from sequential chapters into an EPUB file where each page is represented as an XHTML document with an embedded image.

## Key features

- Supports JPG, JPEG, PNG, and WEBP images
- Automatically sorts images by filename/chapter number
- Creates fixed-layout EPUB3 with `pre-paginated` rendering
- Generates `nav.xhtml` for a basic table of contents
- Supports both new and legacy usage modes (chapter folder or book folder)

## Technologies

- Python 3
- Pillow for image handling
- lxml for XML/XHTML generation
- zipfile for EPUB archive creation

## Architecture

- `image2epub.py` contains the `ImageToEPUB` class, which:
  - stores the list of image files
  - generates EPUB metadata
  - creates `content.opf`, `nav.xhtml`, and individual `page_XXX.xhtml` files
  - builds the EPUB package with `mimetype` and `META-INF/container.xml`
- The main script supports:
  - new usage with `--input-book`, `--start-chapter`, and `--end-chapter`
  - legacy usage with a chapter folder path and optional output path

## Expected input book image structure
book
 |
 ├── Chapter 001
 |      ├── Chapter_001_1
 |      ├── Chapter_001_2
 |       ...
 |      └──Chapter_001_100
 ├── Chapter 002
 |      ├── Chapter_002_1
 |      ├── Chapter_002_2
 |       ...
 |      └──Chapter_002_100
...

## How to run

1. Install dependencies:
```
pip install -r requirements.txt
```

2. Run the converter from the command line:

```bash
python image2epub.py --input-book "<book-path>" --start-chapter 1 --end-chapter 10 --output-name "name.epub" --output-dir "<output-path>"
```

3. Or use the legacy mode for a single chapter folder:

```bash
python image2epub.py "<path-to-chapter>" -o "output.epub"
```

### Example usage

```bash
python image2epub.py --input-book "E:\Klemen\02 Projekti\Manga\image2epub\input\book1" --start-chapter 1 --end-chapter 2 --output-name "book.epub" --output-dir "E:\Klemen\02 Projekti\Manga\image2epub\output"
```

## Requirements

- Python 3.11 or newer
- `requirements.txt` includes:
  - pillow
  - lxml
  - ebooklib

## Testing
1. Install EPUBCheck 5.2.1
EPUBCheck is not installed via UV, because it is a Java-based tool.  
Download EPUBCheck 5.2.1 separately from Maven Central:  
https://repo1.maven.org/maven2/org/w3c/epubcheck/5.2.1/

Place the downloaded JAR file in the project folder, for example:
```
tools/epubcheck-5.2.1.jar
```

2. Run using
```bash
java -jar "<epubcheck.jar-path>" "<epub-output-path>"
```

### Example
```bash
java -jar "E:\Klemen\02 Projekti\Manga\epubcheck-5.2.1\epubcheck.jar" "E:\Klemen\02 Projekti\Manga\image2epub\output.epub"
```

## Possible improvements

- export chapter headings and cover pages
- more advanced table of contents with chapter titles
- support for additional metadata and import formats (author, publisher, date)
- automatic EPUB with EPUBCheck validation
