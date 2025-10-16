from flask import Flask, request, send_file, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from weasyprint import HTML
from utils import *
import io, os, logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Rota principal para aramazenar propostas da ASW S3 e apenas retornar o link das mesmas
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
        link = send_file_s3(pdf_io, f"{dados.get('nome')}.pdf")

        # Retorno de links aos arquivos na AWS S3
        if 'advogado' in dados.get('template'):
            return jsonify({ "reclamada": link }), 200
        else:
            return jsonify({ "reclamante": link }), 200

    except Exception as e:
        app.logger.exception("Erro ao gerar PDF")
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500

# Rota auxiliar para obter diretamente o arquivo de propostas, sem envio à AWS S3
@app.route('/gerar-proposta-antigo', methods=["POST"])
def gerar_proposta_pdf():
    try:
        dados = request.get_json()
        app.logger.info(f"Received payload: {dados}")

        # Generate HTML string from input data
        rendered_html = gerar_html_from_data(dados)

        # Generate PDF in memory
        pdf_io = io.BytesIO()
        HTML(string=rendered_html).write_pdf(pdf_io)
        pdf_io.seek(0)

        # Retorno direto de arquivo pdf
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
