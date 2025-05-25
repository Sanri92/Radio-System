import os
import json
import random
import time
import subprocess
import psutil
import yt_dlp

cola_json_file = "cola.json"
genericas_json_file = "genericas.json"
cancion_actual_file = "cancion_actual.json"
skip_file = "skip.txt"

def cargar_json(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def guardar_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def guardar_cancion_actual(cancion_obj):
    with open(cancion_actual_file, "w", encoding="utf-8") as f:
        json.dump(cancion_obj, f, ensure_ascii=False, indent=2)

def cargar_cola():
    return cargar_json(cola_json_file)

def guardar_cola(canciones):
    guardar_json(cola_json_file, canciones)

def cargar_genericas():
    return cargar_json(genericas_json_file)

def guardar_genericas(canciones):
    # Evitar duplicados por 'url' (o 'id'), comparando por url
    urls_vistos = set()
    canciones_unicas = []
    for c in canciones:
        url = c.get("url")
        if url and url not in urls_vistos:
            urls_vistos.add(url)
            canciones_unicas.append(c)
    guardar_json(genericas_json_file, canciones_unicas)

def kill_proceso_y_hijos(proceso):
    try:
        parent = psutil.Process(proceso.pid)
        children = parent.children(recursive=True)
        for child in children:
            child.terminate()
        gone, still_alive = psutil.wait_procs(children, timeout=5)
        parent.terminate()
        parent.wait(5)
    except Exception as e:
        print(f"⚠️ Error al terminar procesos: {e}")

def revisar_skip():
    if os.path.exists(skip_file):
        with open(skip_file, "r", encoding="utf-8") as f:
            if f.read().strip().lower() == "skip":
                return True
    return False

def resetear_skip():
    with open(skip_file, "w", encoding="utf-8") as f:
        f.write("")

def agregar_a_genericas(cancion_o_url):
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'default_search': 'ytsearch',
            'skip_download': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(cancion_o_url, download=False)
            if 'entries' in info:
                info = info['entries'][0]

            cancion_obj = {
                "id": info.get("id"),
                "titulo": info.get("title"),
                "autor": info.get("uploader"),
                "duracion": info.get("duration_string") or f"{info['duration'] // 60}:{info['duration'] % 60:02}" if "duration" in info else None,
                "url": info.get("webpage_url")
            }

        genericas = cargar_genericas()
        # Verificamos si ya existe por url
        if not any(c.get("url") == cancion_obj["url"] for c in genericas):
            genericas.append(cancion_obj)
            guardar_genericas(genericas)
            print(f"✅ Agregada a genericas: {cancion_obj['titulo']}")
        else:
            print(f"ℹ️ Ya estaba en genericas: {cancion_obj['titulo']}")
    except Exception as e:
        print("⚠️ Error al agregar a genericas:", e)

def obtener_audio_url(cancion_obj):
    # Recibe objeto con "url" o string URL
    url_busqueda = cancion_obj["url"] if isinstance(cancion_obj, dict) else cancion_obj
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'skip_download': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url_busqueda, download=False)
        if 'entries' in info:
            info = info['entries'][0]
        return info['url'], info.get('title', 'Desconocido')

def obtener_siguiente():
    canciones = cargar_cola()
    if canciones:
        siguiente = canciones.pop(0)
        guardar_cola(canciones)
        return siguiente
    return None

def agregar_a_cola(cancion_obj):
    canciones = cargar_cola()
    canciones.append(cancion_obj)
    guardar_cola(canciones)
    print(f"✅ Canción añadida a la cola: {cancion_obj.get('titulo', cancion_obj.get('url', 'Desconocido'))}")

# Ejemplo de uso en el loop principal
if __name__ == "__main__":
    while True:
        cancion = obtener_siguiente()
        if not cancion:
            genericas = cargar_genericas()
            if not genericas:
                print("⚠️ No hay canciones en genericas.json.")
                time.sleep(3)
                continue
            cancion = random.choice(genericas)
        else:
            # Agregar la canción reproducida a genericas para ir completando la lista
            agregar_a_genericas(cancion["url"])
            guardar_cancion_actual(cancion)
        print(f"🎶 Reproduciendo: {cancion.get('titulo', cancion.get('url'))}")
        try:
            url, title = obtener_audio_url(cancion)
            print(f"▶️ {title}")
            player = subprocess.Popen(
                ['mpv.com', '--no-video', '--quiet', '--force-window=no', url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            while player.poll() is None:
                if revisar_skip():
                    kill_proceso_y_hijos(player)
                    resetear_skip()
                    print("⏭️ Canción salteada por el usuario")
                    break
                time.sleep(0.5)
                
                # <- aquí borramos el archivo porque la canción ya terminó o fue salteada
            if os.path.exists(cancion_actual_file):
                os.remove(cancion_actual_file)
                print("🧹 Archivo cancion_actual.json eliminado")
        except Exception as e:
            print("⚠️ Error:", e)
        time.sleep(1)
