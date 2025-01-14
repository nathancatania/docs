from bs4 import BeautifulSoup
import re
import requests
import argparse
from urllib.parse import urlparse
import os
from pathlib import Path
import mimetypes
import urllib.parse


def sanitize_filename(title, format=".md"):
    """Convert a title into a valid filename."""
    print(f"Sanitizing title: {title}")
    filename = title.lower()
    filename = filename.replace(" ", "-")
    filename = re.sub(r"[^a-z0-9-]", "-", filename)
    filename = re.sub(r"-+", "-", filename)
    filename = filename.strip("-")
    final_filename = filename + format
    print(f"Generated filename: {final_filename}")
    return final_filename


def fetch_content(source):
    """Fetch content from either a URL or local file."""
    print(f"Fetching content from: {source}")
    parsed = urlparse(source)
    if parsed.scheme and parsed.netloc:
        print("Source is a URL, fetching via HTTP...")
        try:
            response = requests.get(source)
            response.raise_for_status()
            print("Successfully fetched URL content")
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching URL: {e}")
            raise Exception(f"Error fetching URL: {str(e)}")

    print("Source is a file path, reading file...")
    try:
        with open(source, "r", encoding="utf-8") as file:
            content = file.read()
            print("Successfully read file content")
            return content
    except Exception as e:
        print(f"Error reading file: {e}")
        raise Exception(f"Error reading file: {str(e)}")


def get_iframe_tag(element):
    """Extract just the opening iframe tag."""
    iframe_str = str(element)
    end_of_opening_tag = iframe_str.find(">") + 1
    return iframe_str[:end_of_opening_tag]


def download_image(src_url, base_filename, image_number, script_dir):
    """Download image and save it to the images directory."""
    try:
        # Create images directory if it doesn't exist
        images_dir = os.path.join(script_dir, "images")
        os.makedirs(images_dir, exist_ok=True)

        # Clean up the URL if it contains query parameters
        parsed_url = urlparse(src_url)
        clean_path = parsed_url.path

        # Get file extension from URL or default to .png
        ext = os.path.splitext(clean_path)[1]
        if not ext or ext == ".":
            ext = ".png"

        # Create image filename
        image_filename = f"{base_filename}-{image_number}{ext}"
        image_path = os.path.join("images", image_filename)
        full_path = os.path.join(script_dir, image_path)

        # Download and save the image
        response = requests.get(src_url)
        response.raise_for_status()

        with open(full_path, "wb") as f:
            f.write(response.content)

        print(f"Downloaded image: {image_path}")
        return image_path

    except Exception as e:
        print(f"Error downloading image {src_url}: {str(e)}")
        return None


def process_text_with_formatting(element, is_heading=False, base_filename=None, image_count=None, script_dir=None):
    """Process text content while preserving formatting."""
    if isinstance(element, str):
        return element.replace("'", "'")

    if element.name == "iframe":
        return get_iframe_tag(element)

    # For headings, skip all formatting
    if is_heading:
        return element.get_text().strip()

    # Handle images first
    if element.name == "img":
        if base_filename and image_count is not None and script_dir:
            src = element.get("src", "")
            if src:
                # Ensure src is a full URL
                if not src.startswith(("http://", "https://")):
                    # Handle relative URLs - you might need to add your base URL here
                    src = f"https:{src}" if src.startswith("//") else src
                image_path = download_image(src, base_filename, image_count[0], script_dir)
                if image_path:
                    alt_text = element.get("alt", "") or f"{base_filename}-{image_count[0]}"
                    image_count[0] += 1
                    return f"![{alt_text}]({image_path})"
        return ""

    # Special handling for code elements
    if element.name == "code":
        parent = element.parent
        if parent and parent.name in ["b", "strong", "i", "em"]:
            return f"`{element.get_text().strip()}`"

    # Build formatted text
    text = ""
    for child in element.children:
        if isinstance(child, str):
            text += child.replace("'", "'")
        elif child.name == "code":
            parent = child.parent
            if parent and parent.name in ["b", "strong", "i", "em"]:
                text += f"`{child.get_text().strip()}`"
            else:
                text += f"`{process_text_with_formatting(child)}`"
        elif child.name in ["b", "strong"]:
            text += f"**{process_text_with_formatting(child)}**"
        elif child.name in ["i", "em"]:
            text += f"*{process_text_with_formatting(child)}*"
        elif child.name == "a":
            link_text = process_text_with_formatting(child)
            href = child.get("href", "")
            text += f"[{link_text}]({href})"
        elif child.name == "iframe":
            text += get_iframe_tag(child)
        else:
            text += process_text_with_formatting(child)

    return text.strip()


def process_list_item(li, level=0):
    """Process a single list item and its nested content."""
    indent = "    " * level
    content = []

    # Get the main text content
    p = li.find("p", recursive=False)
    if p:
        text = process_text_with_formatting(p)
    else:
        # Get direct text content
        text = process_text_with_formatting(li)

    content.append(text)

    # Look for nested lists
    nested_lists = li.find_all(["ul", "ol"], recursive=False)
    for nested_list in nested_lists:
        nested_content = process_list(nested_list, level + 1)
        content.extend(nested_content)

    return content


def process_list(list_element, level=0):
    """Process a list element (ul/ol) and return formatted lines."""
    print(f"Processing {'ordered' if list_element.name == 'ol' else 'unordered'} list at level {level}")
    result = []
    indent = "    " * level

    for i, li in enumerate(list_element.find_all("li", recursive=False)):
        marker = f"{i+1}. " if list_element.name == "ol" else "* "
        content_parts = process_list_item(li, level)

        # Add the first part with the list marker
        result.append(f"{indent}{marker}{content_parts[0]}")

        # Add any remaining parts (from nested lists) with proper indentation
        result.extend(content_parts[1:])

    return result


def process_table(table):
    """Process an HTML table and convert it to markdown format."""
    print("Processing table...")
    markdown_rows = []

    # Process header row
    headers = table.find_all("th")
    if headers:
        header_row = [process_text_with_formatting(th) for th in headers]
        markdown_rows.append("| " + " | ".join(header_row) + " |")
        # Add separator row
        markdown_rows.append("| " + " | ".join(["---" for _ in headers]) + " |")

    # Process table rows
    for tr in table.find_all("tr"):
        # Skip if this is a header row we've already processed
        if tr.find("th"):
            continue

        cells = tr.find_all(["td", "th"])
        if cells:
            row_cells = [process_text_with_formatting(cell) for cell in cells]
            # Replace any | characters in cells with HTML entity to avoid breaking table format
            row_cells = [cell.replace("|", "&#124;") for cell in row_cells]
            markdown_rows.append("| " + " | ".join(row_cells) + " |")

    return "\n".join(markdown_rows)


def convert_intercom_to_markdown(html_content, base_filename=None, script_dir=None):
    """Convert Intercom article HTML to Markdown format."""
    print("Starting HTML to Markdown conversion")

    soup = BeautifulSoup(html_content, "html.parser")
    print("HTML parsed successfully")

    # Extract article title and subtitle
    headers = soup.find_all("header", class_="mb-1 font-primary text-2xl font-bold leading-10 text-body-primary-color")
    if not headers:
        title = "Untitled Article"
        subtitle = None
        print(f"No title found, using default: {title}")
    else:
        title = headers[-1].get_text().strip().title()
        print(f"Found article title: {title}")

        # Try to find subtitle
        subtitle_div = headers[-1].find_next_sibling("div", class_="text-md font-normal leading-normal text-body-secondary-color")
        if subtitle_div and subtitle_div.find("p"):
            subtitle = subtitle_div.find("p").get_text().strip()
            print(f"Found article subtitle: {subtitle}")
        else:
            subtitle = None
            print("No subtitle found")

    # Find the main article content
    article = soup.find("article")
    if not article:
        print("No article content found!")
        return "No article content found.", title

    print("Found article content, processing blocks...")

    # Initialize markdown content with frontmatter
    markdown_content = ["---", f"title: {title}"]
    if subtitle:
        markdown_content.append(f"description: {subtitle}")
    markdown_content.extend(["---", ""])

    # Add image counter
    image_count = [0]  # Using list to allow modification in nested function calls

    # Process each block in the article
    blocks_to_skip = set()  # Keep track of elements to skip
    for block in article.find_all(recursive=True):
        # Skip if this element is a child of one we've already processed
        if any(parent in blocks_to_skip for parent in block.parents):
            continue

        # Add table processing
        if block.name == "table":
            print("Found table, converting to markdown format")
            table_markdown = process_table(block)
            markdown_content.extend(["\n", table_markdown, "\n"])
            blocks_to_skip.add(block)  # Skip all children of this table
            continue

        # Only process images that are direct descendants of article or within article blocks
        if block.name == "img" and block.find_parent("article"):
            src = block.get("src", "")
            if src:
                image_path = download_image(src, base_filename, image_count[0], script_dir)
                if image_path:
                    alt_text = block.get("alt", "") or f"{base_filename}-{image_count[0]}"
                    markdown_content.append(f"\n![{alt_text}]({image_path})\n")
                    image_count[0] += 1
                    print(f"Processed image {image_count[0]} from article")
            continue

        # Process other block types only if they're not inside a table
        if not block.find_parent("table"):
            if block.name == "ul" or block.name == "ol":
                print(f"Processing {block.name} list")
                markdown_list = process_list(block)
                markdown_content.extend(["\n"] + markdown_list + [""])
                blocks_to_skip.add(block)
                print(f"Generated {len(markdown_list)} markdown lines for list")

            elif block.name in ["h1", "h2", "h3", "h4"]:
                heading_text = process_text_with_formatting(block, is_heading=True)
                level = int(block.name[1]) + 1  # h1 -> ##, h2 -> ###, etc.
                heading_marks = "#" * level
                print(f"Processing {block.name}: {heading_text}")
                markdown_content.append(f"\n{heading_marks} {heading_text}\n")

            elif block.name == "p" and not any(parent.name in ["li", "td", "th"] for parent in block.parents):
                processed_text = process_text_with_formatting(block, base_filename=base_filename, image_count=image_count, script_dir=script_dir)
                if processed_text:
                    print(f"Processing paragraph: {processed_text[:50]}...")
                    markdown_content.append(f"\n{processed_text}\n")
                blocks_to_skip.add(block)

    print("Cleaning up markdown content...")
    final_content = "\n".join(markdown_content)
    final_content = re.sub(r"\n{3,}", "\n\n", final_content)

    print(f"Conversion completed successfully. Found {image_count[0]} images.")
    return final_content, title


def process_single_article(source, output=None, format=".md"):
    """Process a single article and save to markdown."""
    try:
        html_content = fetch_content(source)
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # First convert without base_filename to get the title
        markdown_output, title = convert_intercom_to_markdown(html_content, base_filename=None, script_dir=script_dir)

        # Now that we have the title, create the sanitized base filename
        base_filename = sanitize_filename(title, "").rstrip("-")  # Remove format extension

        # Convert again with the proper base_filename for images
        markdown_output, _ = convert_intercom_to_markdown(html_content, base_filename=base_filename, script_dir=script_dir)

        if output:
            output_path = output
            print(f"Using specified output path: {output_path}")
        else:
            filename = sanitize_filename(title, format)
            output_path = os.path.join(script_dir, filename)
            print(f"Using generated output path: {output_path}")

        print("Saving markdown content...")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown_output)

        return True, f"Successfully saved to {output_path}"

    except Exception as e:
        return False, str(e)


def process_url_list(list_file, format=".md"):
    """Process multiple URLs from a list file."""
    print(f"\nProcessing URLs from list file: {list_file}")
    try:
        with open(list_file, "r") as f:
            urls = [line.strip() for line in f if line.strip()]

        print(f"Found {len(urls)} URLs to process")

        results = []
        for i, url in enumerate(urls, 1):
            print(f"\n=== Processing URL {i}/{len(urls)}: {url} ===")
            success, message = process_single_article(url, format=format)
            results.append((url, success, message))

        print("\n=== Processing Summary ===")
        successful = sum(1 for _, success, _ in results if success)
        print(f"Successfully processed: {successful}/{len(urls)} articles")

        if len(urls) - successful > 0:
            print("\nFailed URLs:")
            for url, success, message in results:
                if not success:
                    print(f"- {url}: {message}")

    except Exception as e:
        print(f"Error processing list file: {str(e)}")
        exit(1)


def main():
    parser = argparse.ArgumentParser(description="Convert Intercom article to Markdown")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--source", help="URL or file path of the Intercom article")
    group.add_argument("--list", help="File containing list of URLs to process")
    parser.add_argument("-o", "--output", help="Output file path (optional, only used with --source)")
    parser.add_argument("--format", choices=[".md", ".mdx"], default=".md", help="Output file format (default: .md)")
    args = parser.parse_args()

    if args.list:
        process_url_list(args.list, format=args.format)
    else:
        print("\n=== Starting Intercom to Markdown Conversion ===")
        success, message = process_single_article(args.source, args.output, format=args.format)
        if not success:
            print(f"\nError: {message}")
            exit(1)
        else:
            print(f"\nSuccess! {message}")


if __name__ == "__main__":
    main()
