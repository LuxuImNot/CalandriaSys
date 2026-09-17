import json
import os

ruta_json = os.path.join("graphify-out", "graph.json")
if not os.path.exists(ruta_json):
    print("Error: No se encuentra graphify-out/graph.json")
    exit()

with open(ruta_json, "r", encoding="utf-8") as f:
    data = json.load(f)

# 1. Diagnostico de llaves reales
print("\n--- DIAGNOSTICO DE ESTRUCTURA ---")
print("Llaves principales encontradas en tu JSON:", list(data.keys()))

# Intentar extraer nodos buscando variantes comunes de nombres
nodos = data.get("nodes", data.get("vertices", data.get("elements", None)))
if isinstance(nodos, dict):
    nodos_lista = list(nodos.values())
elif isinstance(nodos, list):
    nodos_lista = nodos
else:
    nodos_lista = []

# Intentar extraer conexiones/aristas
aristas = data.get("edges", data.get("links", data.get("connections", None)))
if isinstance(aristas, dict):
    aristas_lista = list(aristas.values())
elif isinstance(aristas, list):
    aristas_lista = aristas
else:
    aristas_lista = []

print(f"Cantidad de nodos leidos con exito: {len(nodos_lista)}")
print(f"Cantidad de conexiones leidas con exito: {len(aristas_lista)}")

if len(nodos_lista) == 0:
    print("?? No se encontraron nodos. Vamos a imprimir una muestra del JSON para entenderlo:")
    print(str(data)[:500])
    exit()

# 2. Generar version HTML hiper-compatible usando SVG puro en lugar de librerias complejas
# Esto asegura que se dibuje SI O SI en tu navegador sin sobrecargar la memoria
elementos_svg = []
ancho, alto = 1920, 1080

# Mapear IDs para posicionamiento basico en cuadricula dinamica
import math
columnas = int(math.ceil(math.sqrt(len(nodos_lista)))) if nodos_lista else 1
posiciones = {}

for idx, n in enumerate(nodos_lista):
    # Intentar obtener el ID sin importar el nombre de la propiedad
    nid = str(n.get("id", n.get("key", n.get("uid", idx))))
    nombre = n.get("name", n.get("label", f"Nodo-{idx}"))
    tipo = n.get("type", "unknown")
    archivo = os.path.basename(n.get("file_path", ""))
    
    # Calcular posicion x, y basica para que no colapsen en el mismo punto
    col = idx % columnas
    row = idx // columnas
    x = 100 + col * (ancho / (columnas + 1))
    y = 100 + row * (alto / (columnas + 1))
    posiciones[nid] = (x, y)
    
    color = "#2b7ce9" if tipo == "class" else "#5cd65c" if tipo == "function" else "#ff9900"
    
    # Agregar circulo del nodo en SVG
    elementos_svg.append(f'<circle cx="{x}" cy="{y}" r="12" fill="{color}" stroke="#fff" stroke-width="2"><title>Tipo: {tipo}\nArchivo: {archivo}</title></circle>')
    # Agregar texto del nodo
    elementos_svg.append(f'<text x="{x}" y="{y+25}" fill="#fff" font-size="10" text-anchor="middle" font-family="Arial">{nombre}</text>')

# Dibujar las lineas de conexion
for e in aristas_lista:
    origen = str(e.get("source", e.get("from", "")))
    destino = str(e.get("target", e.get("to", "")))
    if origen in posiciones and destino in posiciones:
        x1, y1 = posiciones[origen]
        x2, y2 = posiciones[destino]
        elementos_svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#555" stroke-dasharray="4" stroke-width="1" />')

html_completo = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Mapa SVG - DynamicSepticSystem</title>
    <style>
        body {{ margin: 0; background-color: #141419; color: #fff; font-family: sans-serif; overflow: auto; }}
        #panel {{ position: fixed; top: 10px; left: 10px; background: rgba(30,30,40,0.9); padding: 15px; border-radius: 8px; border: 1px solid #444; z-index: 10; }}
        h3 {{ margin-top: 0; color: #5cd65c; }}
        svg {{ background-color: #111; display: block; }}
    </style>
</head>
<body>
    <div id="panel">
        <h3>Mapa Estructural Real</h3>
        <p><b>Azul:</b> Clases | <b>Verde:</b> Metodos</p>
        <p>Pasa el mouse sobre las esferas para ver el archivo de C#.</p>
    </div>
    <svg width="{ancho*1.5}" height="{alto*1.5}">
        {"".join(elementos_svg)}
    </svg>
</body>
</html>
"""

with open("mapa_proyecto_real.html", "w", encoding="utf-8") as f:
    f.write(html_completo)
print("\n[Exito] Archivo 'mapa_proyecto_real.html' generado con exito.")
