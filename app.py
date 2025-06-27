from flask import Flask, request, send_file, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from utils import *
from weasyprint import HTML
from dotenv import load_dotenv
import io, os
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route("/gerar-proposta", methods=["POST"])
def gerar_proposta():
    try:
        dados = request.get_json()
        app.logger.info(f"Received payload: {dados}")

        # Generate HTML string from input data
        rendered_html = gerar_html_from_data(dados)

        # Generate PDF in memory
        pdf_io = io.BytesIO()
        HTML(string=rendered_html).write_pdf(pdf_io)
        pdf_io.seek(0)

        return send_file(
            pdf_io,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="proposta.pdf"
        )

    except Exception as e:
        app.logger.exception("Erro ao gerar PDF")
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500

# Create ping route to keep app alive
@app.route('/ping', methods = ['GET', 'POST'])

# Function dealing with the ping route
def ping():
    if request.method == 'POST':
        return jsonify({'status': 'alive', 'results': 12345}), 200
    return jsonify({"status": "alive"}), 200

scheduler = BackgroundScheduler()
scheduler.add_job(keep_alive, trigger = 'interval', minutes = 13)
scheduler.start()

if __name__ == '__main__':
    # Check debug flag in the arguments
    load_dotenv()
    PORT = os.getenv('RENDER_PORT', 10000)
    # Host selection based on host_server definitions -> In this case, following Render settings
    app.run(host = '0.0.0.0', port = PORT)
