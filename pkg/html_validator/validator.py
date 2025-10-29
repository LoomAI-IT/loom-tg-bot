from bs4 import BeautifulSoup


def validate_html(html_string: str):
    try:
        soup = BeautifulSoup(html_string, 'lxml')
    except Exception as e:
        raise
