from html5lib import HTMLParser


def validate_html(html_string: str):
    parser = HTMLParser(strict=False, namespaceHTMLElements=False)
    try:
        document = parser.parse(html_string)
        if document is None:
            raise ValueError("Failed to parse HTML: document is None")
    except Exception as e:
        raise ValueError(f"Invalid HTML: {str(e)}") from e
