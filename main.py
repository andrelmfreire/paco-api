import os
import uuid

import requests

import config
import json
import time
from flask import Flask, jsonify, Response, g, request
from blueprints.activities import activities
from utils.utils import razao_embarcador, send_to_demak


def create_app():
    app = Flask(__name__)
    app.register_blueprint(activities, url_prefix="/api/v1/")

    # Error 404 handler
    @app.errorhandler(404)
    def resource_not_found(e):
        return jsonify(error=str(e)), 404

    # Error 405 handler
    @app.errorhandler(405)
    def resource_not_found(e):
        return jsonify(error=str(e)), 405

    # Error 401 handler
    @app.errorhandler(401)
    def custom_401(error):
        return Response("API Key required.", 401)

    @app.route("/ping")
    def hello_world():
        return "pong"

    @app.route("/tracker/webhook", methods=["GET", "POST"])
    def tracker_webhook():
        """Handles webhook requests from Tracker.
        Returns:
            A tuple containing the response data and status code.
        """
        if request.method != "POST":
            return "Only POST requests are accepted", 405

        data = request.json

        # Extract data from the webhook payload
        data_hora_envio = data["data_hora_envio"]
        cnpj_embarcador = data["cnpj_embarcador"]
        nota_fiscal_numero = data["nota_fiscal"]["numero"]
        recebedor_nome = data["recebedor"]["nome"]
        ocorrencia_descricao = data["ocorrencia"]["descricao"]
        ocorrencia_comprovante_caminho = data["ocorrencia"]["comprovante"]["caminho"]

        cliente, embarcador = razao_embarcador(cnpj_embarcador)

        # Send info to Demak after ENTREGA:
        if ocorrencia_descricao.casefold() == 'entregue' and cliente.casefold() == 'demak':
            try:
                payload = {
                    "notafiscal": nota_fiscal_numero,
                    "cnpjremetente": cnpj_embarcador,
                    "razaosocialremetente": embarcador,
                    "cnpjdestinatario": "pending",
                    "razaosocialdestinatario": "pending",
                    "nomedequemrecebeu": recebedor_nome,
                    "datadeentrega": data_hora_envio,
                    "comprovantedeentrega": ocorrencia_comprovante_caminho,
                    "transportadora": "Pacorush"
                }
                requests.request("POST", url=f'{config.BASE_URL}/api/v1/dmk', json=payload)
            except Exception as e:
                return str(e), 400

        return data, 200

    @app.route("/tracker/test", methods=["GET", "POST"])
    def demak_test():
        if request.method == "POST":
            data = request.json
            print("Data received at DEMAK", data)
            return data

    @app.before_request
    def before_request_func():
        execution_id = uuid.uuid4()
        g.start_time = time.time()
        g.execution_id = execution_id

        print(g.execution_id, "ROUTE CALLED ", request.url)

    @app.after_request
    def after_request(response):
        if response and response.get_json():
            data = response.get_json()

            data["time_request"] = int(time.time())
            data["version"] = config.VERSION

            response.set_data(json.dumps(data))

        return response

    @app.route("/version", methods=["GET"], strict_slashes=False)
    def version():
        response_body = {
            "success": 1,
        }
        return jsonify(response_body)

    return app


app = create_app()

if __name__ == "__main__":
    #    app = create_app()
    print(" Starting app...")
    app.run(host="0.0.0.0", port=5000)
