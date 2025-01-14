import os
import sys
import shutil
from pathlib import Path
import re


def convert_frontmatter(content):
    print("Converting frontmatter...")
    # Extract existing frontmatter between --- markers
    fm_match = re.match(r"---\n(.*?)\n---", content, re.DOTALL)
    if not fm_match:
        print("No frontmatter found")
        return content

    frontmatter = fm_match.group(1)

    # Extract needed fields
    title_match = re.search(r'title:\s*"([^"]+)"', frontmatter)
    desc_match = re.search(r"description:\s*(.+)", frontmatter)
    icon_match = re.search(r"icon:\s*material/(.+)", frontmatter)

    # Build new frontmatter
    new_fm = ["---"]
    if title_match:
        print(f"Found title: {title_match.group(1)}")
        new_fm.append(f'title: "{title_match.group(1)}"')
    if desc_match:
        print(f"Found description: {desc_match.group(1)}")
        new_fm.append(f"description: {desc_match.group(1)}")
    if icon_match:
        print(f"Converting material icon: {icon_match.group(1)} to fontawesome")
        # Convert material icon to fontawesome
        new_fm.append(f'icon: "{icon_match.group(1)}"')
    new_fm.append("---\n")

    # Replace old frontmatter with new
    return re.sub(r"---\n.*?\n---\n", "\n".join(new_fm), content, flags=re.DOTALL)


def convert_admonitions(content):
    print("Converting admonitions...")
    # Map mkdocs admonitions to mintlify callouts
    admonition_map = {"info": "Note", "note": "Info", "warning": "Warning", "danger": "Warning", "bug": "Warning", "question": "Tip", "success": "Success", "failure": "Warning"}

    def replace_admonition(match):
        type_str = match.group(1).lower()  # Convert to lowercase for consistent matching
        title = match.group(2) if len(match.groups()) > 2 else None
        content = match.group(3) if len(match.groups()) > 2 else match.group(2)
        content = content.strip()

        callout_type = admonition_map.get(type_str, "Note")
        print(f"Converting {type_str} admonition to {callout_type} callout")

        if title:
            return f"<{callout_type}>\n\n**{title}**\n\n{content}\n</{callout_type}>"
        else:
            return f"<{callout_type}>\n\n{content}\n\n</{callout_type}>"

    # Updated pattern to better handle admonition variations
    pattern = r'!!!\s+(\w+)(?:\s+"([^"]+)")?\n(.*?)(?=(?:!!!|\n\n|$))|!!!\s+(\w+)\n(.*?)(?=(?:!!!|\n\n|$))'
    return re.sub(pattern, replace_admonition, content, flags=re.DOTALL)


def convert_tabs(content):
    print("Converting tabs...")

    def replace_tabs(match):
        tabs_content = match.group(0)
        tab_pattern = r'===\s+"([^"]+)"\n(.*?)(?=(?:===|\Z))'

        tabs = re.finditer(tab_pattern, tabs_content, re.DOTALL)

        output = ["<Tabs>"]
        for tab in tabs:
            title = tab.group(1)
            content = tab.group(2).strip()
            print(f"Converting tab: {title}")
            output.append(f'  <Tab title="{title}">\n    {content}\n  </Tab>')
        output.append("</Tabs>")

        return "\n".join(output)

    return re.sub(r"(?s)=== .*?(?=\n\n|\Z)", replace_tabs, content)


def convert_cards(content):
    print("Converting cards...")

    def replace_card(match):
        cards = []
        card_pattern = r":[\w-]+:.*?__([^_]+)__\n\n\s*---\n\n\s*(.*?)(?=(?:-   :|$))"

        for card_match in re.finditer(card_pattern, match.group(1), re.DOTALL):
            title = card_match.group(1).strip()
            content = card_match.group(2).strip()
            print(f"Converting card: {title}")
            cards.append(f'  <Card title="{title}" icon="circle">\n    {content}\n  </Card>')

        return f'<CardGroup cols={{2}}>\n{"".join(cards)}\n</CardGroup>'

    return re.sub(r'<div class="grid cards" markdown>\n\n(.*?)\n\n</div>', replace_card, content, flags=re.DOTALL)


def convert_images(content, mdx_filename):
    print("Converting images...")

    def replace_image(match):
        alt_text = match.group(1)
        old_path = match.group(2)
        print(f"Found image: {old_path}")
        if old_path.startswith("assets/"):
            # Generate new filename based on MDX filename
            base_name = Path(mdx_filename).stem
            ext = Path(old_path).suffix
            new_filename = f"{base_name}-1{ext}"
            print(f"Converting image path from {old_path} to /images/{new_filename}")
            return f"![{alt_text}](/images/{new_filename})"
        return match.group(0)

    return re.sub(r"!\[(.*?)\]\((.*?)\)", replace_image, content)


def convert_octicons(content):
    print("Converting octicons...")
    # Replace octicons with markdown bullet points
    pattern = r":octicons-[^:]+:"
    return re.sub(pattern, "*", content)


def remove_template_vars(content):
    print("Removing template variables...")
    return re.sub(r"{{.*?}}", "", content)


def convert_special_characters(content):
    print("Converting special characters...")
    # Replace special quotes with standard quotes
    content = content.replace("”", '"')
    content = content.replace("“", '"')
    content = content.replace("'", "'")
    content = content.replace("’", "'")
    content = content.replace('"', '"')
    content = content.replace('"', '"')
    return content


def clean_markdown_extensions(content):
    print("Cleaning markdown extensions...")

    # Handle both properly formed and malformed target="_blank" tags
    patterns = [r'\{:target="_blank"\}', r'\{:target="_blank"', r"\{:target=\'_blank\'\}", r"\{:target=\'_blank\'", r"\{:target=_blank\}", r"\{:target=_blank"]  # Properly formed  # Missing closing brace  # Single quotes  # Single quotes, missing closing brace  # No quotes  # No quotes, missing closing brace

    # Apply each pattern and report results
    original_length = len(content)
    for pattern in patterns:
        matches = re.findall(pattern, content)
        if matches:
            print(f"Found matches for pattern {pattern}:", len(matches))
            content = re.sub(pattern, "", content)

    # Check if content length changed
    new_length = len(content)
    if original_length != new_length:
        print(f"Removed {original_length - new_length} characters")
    else:
        print("No changes made to content")

    return content


def convert_mkdocs_to_mdx(input_file, output_file):
    print(f"\nStarting conversion of {input_file} to {output_file}")
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            content = f.read()
            print(f"Successfully read input file: {input_file}")
    except Exception as e:
        print(f"Error reading input file: {str(e)}")
        raise

    try:
        # Apply all conversions
        content = convert_frontmatter(content)
        content = convert_admonitions(content)
        content = convert_tabs(content)
        content = convert_cards(content)
        content = convert_images(content, output_file)
        content = convert_octicons(content)
        content = remove_template_vars(content)
        content = convert_special_characters(content)
        content = clean_markdown_extensions(content)
    except Exception as e:
        print(f"Error during conversion process: {str(e)}")
        raise

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)
            print(f"Successfully wrote output file: {output_file}")
    except Exception as e:
        print(f"Error writing output file: {str(e)}")
        raise


def convert_file(input_content):
    content = input_content
    content = clean_markdown_extensions(content)
    content = convert_special_characters(content)
    content = convert_octicons(content)
    # ... rest of your conversion functions ...
    return content


def process_directory(input_path, output_path):
    print(f"\nProcessing directory: {input_path}")
    print(f"Output directory: {output_path}\n")

    # Convert paths to Path objects for easier handling
    input_path = Path(input_path)
    output_path = Path(output_path)

    # Create the output directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)

    # Track statistics
    files_processed = 0
    files_skipped = 0

    # Walk through all files and directories
    for root, dirs, files in os.walk(input_path):
        # Convert current root to Path object
        current_root = Path(root)

        # Calculate relative path from input_path
        relative_path = current_root.relative_to(input_path)

        # Create corresponding output directory
        current_output_dir = output_path / relative_path
        current_output_dir.mkdir(parents=True, exist_ok=True)

        # Process each file in current directory
        for file in files:
            if file.endswith(".md"):
                input_file = current_root / file
                # Change extension to .mdx for output file
                output_file = current_output_dir / file.replace(".md", ".mdx")

                try:
                    print(f"\nStarting conversion of {input_file} to {output_file}")
                    convert_mkdocs_to_mdx(str(input_file), str(output_file))
                    files_processed += 1

                except Exception as e:
                    print(f"Error processing {input_file}: {str(e)}")
                    files_skipped += 1
            else:
                # Copy non-markdown files as-is
                input_file = current_root / file
                output_file = current_output_dir / file
                try:
                    shutil.copy2(input_file, output_file)
                except Exception as e:
                    print(f"Error copying {input_file}: {str(e)}")
                    files_skipped += 1

    # Print summary
    print(f"\nConversion complete!")
    print(f"Files processed: {files_processed}")
    print(f"Files skipped: {files_skipped}")


def main():
    if len(sys.argv) != 3:
        print("Usage: python convert-mkdocs.py <input_path> <output_path>")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    if not os.path.exists(input_path):
        print(f"Error: Input path '{input_path}' does not exist")
        sys.exit(1)

    process_directory(input_path, output_path)


if __name__ == "__main__":
    main()

# # Example usage
# input_file = "docs/getting-started/cloud-prem/gcp/deploy-gcp.md"
# output_file = "deploy-gcp.mdx"
# convert_mkdocs_to_mdx(input_file, output_file)
