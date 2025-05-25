from flask import Flask, request, jsonify
from flask_cors import CORS
import time
import os
import requests
import json
import yt_dlp

app = Flask(__name__)
CORS(app)

cola_json_file = "cola.json"
cancion_actual_file = "cancion_actual.json"
skip_file = "skip.txt"

# Si el archivo no existe, lo inicializamos como lista vacía
if not os.path.exists(cola_json_file):
    with open(cola_json_file, "w", encoding="utf-8") as f:
        json.dump([], f)

@app.route("/pedir-cancion", methods=["POST"])
def pedir_cancion():
    data = request.get_json()
    cancion = data.get("cancion", "").strip()

    if not cancion:
        return jsonify({"msg": "⚠️ Escribí el nombre de la canción", "error": True}), 400

    # Buscar canción en YouTube
    try:
        ydl_opts = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            "default_search": "ytsearch1",
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(cancion, download=False)
            if "entries" in result:
                video = result["entries"][0]
            else:
                video = result

            cancion_obj = {
                "id": video["id"],
                "titulo": video["title"],
                "autor": video["uploader"],
                "duracion": video["duration_string"] if "duration_string" in video else f"{video['duration'] // 60}:{video['duration'] % 60:02}",
                "url": f"https://www.youtube.com/watch?v={video['id']}"
            }

    except Exception as e:
        return jsonify({"msg": f"❌ No se pudo encontrar la canción: {str(e)}", "error": True}), 500

    # Leer la cola actual
    with open(cola_json_file, "r", encoding="utf-8") as f:
        cola = json.load(f)

    # Verificar si la canción ya está en la cola
    if any(c["id"] == cancion_obj["id"] for c in cola):
        return jsonify({"msg": f"⚠️ La canción '{cancion_obj['titulo']}' ya está en la cola.", "error": True}), 409

    # Agregar la canción como objeto
    cola.append(cancion_obj)

    # Guardar la cola actualizada
    with open(cola_json_file, "w", encoding="utf-8") as f:
        json.dump(cola, f, ensure_ascii=False, indent=2)

    return jsonify({"msg": f"✅ ¡'{cancion_obj['titulo']}' fue añadida a la cola!", "error": False})

@app.route("/skip", methods=["POST"])
def skip_cancion():
    with open(skip_file, "w", encoding="utf-8") as f:
        f.write("skip")
    return jsonify({"msg": "⏭️ Canción salteada!"})

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

        texto = r.text
        json_start = texto.find('(') + 1
        json_end = texto.rfind(')')
        json_str = texto[json_start:json_end]

        datos = json.loads(json_str)

        return jsonify(datos[1])

    except Exception as e:
        print("Error al pedir sugerencias:", e)
        return jsonify([]), 500

# 🔁 Función para cargar la cola desde el archivo JSON
def cargar_cola():
    if os.path.exists(cola_json_file):
        with open(cola_json_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# 📥 Ruta para obtener la cola actual
@app.route("/cola", methods=["GET"])
def obtener_cola():
    return jsonify(cargar_cola())

@app.route("/cancion-actual", methods=["GET"])
def cancion_actual():
    if os.path.exists(cancion_actual_file):
        with open(cancion_actual_file, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    else:
        return jsonify({"msg": "No hay canción sonando actualmente"}), 404

@app.route("/cola/<id>", methods=["DELETE"])
def eliminar_cancion(id):
    cola = cargar_cola()
    nueva_cola = [c for c in cola if c["id"] != id]

    if len(nueva_cola) == len(cola):
        return jsonify({"msg": f"⚠️ No se encontró la canción con ID {id}", "error": True}), 404

    with open(cola_json_file, "w", encoding="utf-8") as f:
        json.dump(nueva_cola, f, ensure_ascii=False, indent=2)

    return jsonify({"msg": f"🗑️ Canción eliminada correctamente", "error": False})

print(app.url_map)

if __name__ == "__main__":
    app.run(port=5000)
