from flask import Flask, request, jsonify
from flask_cors import CORS
import time
import requests
import json

app = Flask(__name__)
CORS(app)  # permite recibir desde cualquier web

cola_file = "cola.txt"
skip_file = "skip.txt"

@app.route("/pedir-cancion", methods=["POST"])
def pedir_cancion():
    data = request.get_json()
    cancion = data.get("cancion", "").strip()

    if not cancion:
        return jsonify({"msg": "⚠️ Escribí el nombre de la canción"}), 400

    with open(cola_file, "a", encoding="utf-8") as f:
        f.write(cancion + "\n")

    return jsonify({"msg": f"✅ ¡'{cancion}' fue añadida a la cola!"})

@app.route("/skip", methods=["POST"])
def skip_cancion():
    with open(skip_file, "w", encoding="utf-8") as f:
        f.write("skip")
    return jsonify({"msg": "⏭️ Canción salteada!"})

# 🔽 NUEVA RUTA PARA SUGERENCIAS DE YOUTUBE
@app.route("/sugerencias")
def sugerencias():
    print("⚡ ENTRÓ A sugerencias ⚡", flush=True)
    q = request.args.get("q", "")
    print(f"Sugerencias recibidas con q = '{q}'")
    if not q:
        return jsonify([])

    try:
        r = requests.get(
            "https://suggestqueries.google.com/complete/search",
            params={"client": "youtube", "ds": "yt", "q": q}
        )
        r.raise_for_status()

        # r.text es algo como: window.google.ac.h([...]);
        # Extraemos la parte JSON dentro del paréntesis:
        texto = r.text
        json_start = texto.find('(') + 1
        json_end = texto.rfind(')')
        json_str = texto[json_start:json_end]

        datos = json.loads(json_str)
        # datos[1] es la lista de sugerencias, ejemplo:
        # ["palabra", ["sugerencia1", "sugerencia2", ...]]

        return jsonify(datos[1])

    except Exception as e:
        print("Error al pedir sugerencias:", e)
        return jsonify([]), 500

print(app.url_map)

if __name__ == "__main__":
    app.run(port=5000)
