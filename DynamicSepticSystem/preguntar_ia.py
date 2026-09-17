import json
import os
from openai import OpenAI

client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

def cargar_grafo():
    ruta = os.path.join("graphify-out", "graph.json")
    if not os.path.exists(ruta):
        raise FileNotFoundError("No se encuentra graphify-out/graph.json.")
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)

def buscar_archivos_en_disco(palabras_clave, pregunta):
    archivos_encontrados = {}
    archivo_objetivo = ""
    for token in pregunta.lower().split():
        if ".cs" in token:
            archivo_objetivo = token.replace("?", "")
            break

    for raiz, dirs, archivos in os.walk("."):
        if "graphify-out" in raiz or ".git" in raiz or "obj" in raiz or "bin" in raiz:
            continue
        for archivo in archivos:
            if archivo.lower().endswith(".cs"):
                if archivo_objetivo and archivo_objetivo in archivo.lower():
                    archivos_encontrados[archivo.upper()] = os.path.join(raiz, archivo)
                elif not archivo_objetivo and any(p in archivo.lower() for p in palabras_clave):
                    if "designer" in archivo.lower() and "designer" not in pregunta.lower():
                        continue
                    archivos_encontrados[archivo.upper()] = os.path.join(raiz, archivo)
                    
    items = list(archivos_encontrados.items())
    return dict(items[:2])

def extraer_codigo_fuente(rutas_archivos):
    contenido_codigo = ""
    for nombre, ruta in rutas_archivos.items():
        try:
            with open(ruta, "r", encoding="utf-8", errors="ignore") as f:
                lineas = f.readlines()
                codigo_recortado = "".join(lineas[:80])
                contenido_codigo += f"\n\n--- CODIGO FUENTE REAL DE: {nombre} ---\n"
                contenido_codigo += codigo_recortado
                if len(lineas) > 80:
                    contenido_codigo += "\n// [... Mas codigo en el archivo original ...]"
        except Exception as e:
            continue
    return contenido_codigo

def filtrar_mapa_por_pregunta(grafo, pregunta):
    nodos = grafo.get("nodes", [])
    nodos_lista = nodos if isinstance(nodos, list) else list(nodos.values())
    
    contexto = []
    pregunta_limpia = pregunta.lower().replace(".cs", "").replace("?", "").replace("que", "").replace("hace", "")
    palabras_clave = [p for p in pregunta_limpia.split() if len(p) > 2]
    
    for nodo in nodos_lista:
        nombre = str(nodo.get("name") or nodo.get("label") or nodo.get("title") or nodo.get("id") or "").lower()
        ruta_archivo = str(nodo.get("file_path") or nodo.get("path") or nodo.get("location") or "").lower()
        tipo = str(nodo.get("type") or nodo.get("category") or "COMPONENTE")
        
        if not nombre or nombre == "none":
            continue
            
        if any(p in nombre for p in palabras_clave) or any(p in ruta_archivo for p in palabras_clave):
            nombre_limpio = nombre.upper()
            archivo_limpio = os.path.basename(ruta_archivo) if ruta_archivo else "Archivo_Local"
            contexto.append(f"- [{tipo.upper()}] {nombre_limpio} encontrado en '{archivo_limpio}'")
            
    dict_archivos = buscar_archivos_en_disco(palabras_clave, pregunta)
    codigo_real = ""
    if dict_archivos:
        codigo_real = extraer_codigo_fuente(dict_archivos)
                    
    return "\n".join(contexto[:10]), codigo_real

def consultar_ia(pregunta, historial):
    grafo = cargar_grafo()
    contexto_filtrado, codigo_real = filtrar_mapa_por_pregunta(grafo, pregunta)
    
    system_prompt = f"""Eres un desarrollador experto en C# y arquitectura de software en Windows Forms.
Tienes acceso al mapa de dependencias y al codigo fuente real del sistema 'DynamicSepticSystem'.

Explica brevemente que hace el archivo solicitado basandote en el codigo fuente real adjunto abajo.

MAPA DE COMPONENTES:
{contexto_filtrado}

CODIGO FUENTE REAL SELECCIONADO:
{codigo_real}
"""

    mensajes = [{"role": "system", "content": system_prompt}]
    for h in historial:
        mensajes.append(h)
    mensajes.append({"role": "user", "content": pregunta})
    
    completion = client.chat.completions.create(
        model="local-model", 
        messages=mensajes,
        temperature=0.2
    )
    # CORREGIDO DEFINITIVAMENTE: Agregado el [0] para leer la primera opcion valida
    return completion.choices[0].message.content

if __name__ == "__main__":
    print("\n=======================================================")
    print("      CHAT ACTIVO: DynamicSepticSystem + LM Studio     ")
    print("   (Escribe 'salir' o 'exit' para cerrar el chat)     ")
    print("=======================================================")
    
    historial_chat = []
    
    while True:
        try:
            pregunta = input("\nTu: ")
            if pregunta.lower() in ['salir', 'exit']:
                print("Cerrando chat. Hasta luego.")
                break
                
            if not pregunta.strip():
                continue
                
            print("[Pensando...] Buscando codigo y consultando a LM Studio...")
            respuesta = consultar_ia(pregunta, historial_chat)
            
            print(f"\n=== RESPUESTA ===")
            print(respuesta)
            
            historial_chat.append({"role": "user", "content": pregunta})
            historial_chat.append({"role": "assistant", "content": respuesta})
            
            if len(historial_chat) > 6:
                historial_chat = historial_chat[-6:]
                
        except Exception as e:
            print(f"\nError de ejecucion: {e}")
