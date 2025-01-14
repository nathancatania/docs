import json
import re
from bs4 import BeautifulSoup
import os


def clean_html_to_markdown(html_content):
    if not html_content:
        return ""

    # Parse HTML
    soup = BeautifulSoup(html_content, "html.parser")

    # Remove all style, class, and id attributes
    for tag in soup.find_all(True):
        tag.attrs = {}

    # Extract text content
    markdown = ""
    for element in soup.find_all(["h1", "p", "ul", "li", "img"]):
        if element.name == "h1":
            markdown += f"## {element.get_text().strip()}\n\n"
        elif element.name == "p":
            text = element.get_text().strip()
            if text:
                markdown += f"{text}\n\n"
        elif element.name == "li":
            markdown += f"- {element.get_text().strip()}\n"
        elif element.name == "img":
            src = element.get("src", "")
            if src.startswith("/hc/"):
                src = f"https://support.glean.com{src}"
            markdown += f'<Frame><img src="{src}"/></Frame>\n\n'

    return markdown.strip()


def create_mdx_file(article, output_dir):
    if not article.get("body"):
        print(f"Skipping article '{article.get('name', 'Unknown')}' - no body content")
        return False

    # Create filename (lowercase, replace underscores with hyphens)
    filename = f"{article['name'].lower().replace('_', '-')}.mdx"

    # Create MDX content
    mdx_content = f"""---
title: {article['title']}
description: {article['title']} Error Code
---

{clean_html_to_markdown(article['body'])}
"""

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Write to file
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(mdx_content)

    print(f"Created: {filepath}")

    return True


def main():
    # Read the JSON file
    with open("articles.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    counter = 0
    total_articles = len(data["articles"])

    # Process all articles
    output_dir = "mdx_output"
    for article in data["articles"]:
        if create_mdx_file(article, output_dir):
            counter += 1

    print(f"Processed {counter} articles out of {total_articles}")


if __name__ == "__main__":
    main()
