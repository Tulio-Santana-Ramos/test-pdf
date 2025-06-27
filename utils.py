from jinja2 import Environment, FileSystemLoader, select_autoescape
import os, requests

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

# Function for the scheduler timer
def keep_alive():
    try:
        response = requests.get('https://test-pdf-e65s.onrender.com/ping')
        print("Keep-alive request sent successfully") if response.status_code == 200 else print("Alive failed")
    except Exception as e:
        print(f"Error during Keep-Alive request: {e}")