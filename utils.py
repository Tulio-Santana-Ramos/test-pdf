from jinja2 import Environment, FileSystemLoader, select_autoescape
import os

# Set up Jinja environment
env = Environment(
    loader=FileSystemLoader(os.path.dirname(__file__)),
    autoescape=select_autoescape(['html', 'xml'])
)

def gerar_html_from_data(dados: dict) -> str:
    """Render HTML from a template and data dict."""
    template = env.get_template("template.html")
    rendered_html = template.render(**dados)
    return rendered_html
