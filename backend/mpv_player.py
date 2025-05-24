import subprocess
import yt_dlp
import time
import os
import random
import psutil

cola_file = "cola.txt"
genericas_file = "genericas.txt"

def cargar_genericas():
    if os.path.exists(genericas_file):
        with open(genericas_file, "r", encoding="utf-8") as f:
            return list({l.strip() for l in f if l.strip()})
    return []

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

def guardar_genericas(canciones):
    canciones = list(set(canciones))  # evitar duplicados
    with open(genericas_file, "w", encoding="utf-8") as f:
        f.writelines([c + "\n" for c in canciones])

def revisar_skip():
    if os.path.exists("skip.txt"):
        with open("skip.txt", "r", encoding="utf-8") as f:
            if f.read().strip().lower() == "skip":
                return True
    return False

def resetear_skip():
    with open("skip.txt", "w", encoding="utf-8") as f:
        f.write("")

def agregar_a_genericas(cancion_o_url):
    try:
        # Obtener la URL real del video usando yt_dlp
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'default_search': 'ytsearch',
            'skip_download': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(cancion_o_url, download=False)
            if 'entries' in info:  # Si es resultado de búsqueda
                info = info['entries'][0]
            url_real = info['webpage_url']  # URL de YouTube canónica

        canciones = cargar_genericas()
        if url_real not in canciones:
            canciones.append(url_real)
            guardar_genericas(canciones)
            print(f"✅ Agregada a genericas: {info.get('title', url_real)}")
        else:
            print(f"ℹ️ Ya estaba en genericas: {info.get('title', url_real)}")
    except Exception as e:
        print("⚠️ Error al agregar a genericas:", e)

def obtener_audio_url(cancion_o_url):
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
        return info['url'], info.get('title', 'Desconocido')

def obtener_siguiente():
    if os.path.exists(cola_file):
        with open(cola_file, "r", encoding="utf-8") as f:
            canciones = [l.strip() for l in f if l.strip()]
        if canciones:
            siguiente = canciones[0]
            with open(cola_file, "w", encoding="utf-8") as f:
                f.writelines([l + "\n" for l in canciones[1:]])
            return siguiente
    return None

while True:
    cancion = obtener_siguiente()
    if not cancion:
        genericas = cargar_genericas()
        if not genericas:
            print("⚠️ No hay canciones en genericas.txt.")
            time.sleep(3)
            continue
        cancion = random.choice(genericas)
    else:
        agregar_a_genericas(cancion)

    print(f"🎶 Reproduciendo: {cancion}")
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
    except Exception as e:
        print("⚠️ Error:", e)
    time.sleep(1)
