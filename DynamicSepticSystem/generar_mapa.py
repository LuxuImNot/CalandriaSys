import json
import os

def construir_interfaz_visual():
    ruta_json = os.path.join("graphify-out", "graph.json")
    if not os.path.exists(ruta_json):
        print("Error: No se encuentra graphify-out/graph.json")
        return

    with open(ruta_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Normalizar nodos (por si vienen en formato lista o diccionario)
    raw_nodes = data.get("nodes", [])
    nodes_list = raw_nodes if isinstance(raw_nodes, list) else list(raw_nodes.values())
    
    # Normalizar aristas/conexiones
    raw_edges = data.get("edges", []) or data.get("links", [])
    edges_list = raw_edges if isinstance(raw_edges, list) else list(raw_edges.values())

    elementos_js = []
    
    # Procesar Clases y Metodos principales para no saturar el mapa con miles de puntos minusculos
    for n in nodes_list:
        nid = str(n.get("id", n.get("key", "")))
        nombre = n.get("name", "Sin Nombre")
        tipo = n.get("type", "unknown")
        archivo = os.path.basename(n.get("file_path", ""))
        
        # Color segun el tipo de componente C#
        color = "#2b7ce9" if tipo == "class" else "#5cd65c" if tipo == "function" else "#ff9900"
        
        elementos_js.append({
            "data": {
                "id": nid, 
                "label": f"{nombre}\n({tipo})", 
                "color": color,
                "info": f"Tipo: {tipo} | Archivo: {archivo}"
            }
        })

    for e in edges_list:
        origen = str(e.get("source", e.get("from", "")))
        destino = str(e.get("target", e.get("to", "")))
        elementos_js.append({
            "data": {
                "source": origen, 
                "target": destino
            }
        })

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Mapa de Arquitectura - DynamicSepticSystem</title>
    <script src="https://cloudflare.com"></script>
    <style>
        body {{ margin: 0; padding: 0; background-color: #141419; color: #fff; font-family: Arial, sans-serif; }}
        #cy {{ width: 100vw; height: 100vh; position: absolute; top: 0; left: 0; z-index: 1; }}
        #panel {{ position: absolute; top: 10px; left: 10px; background: rgba(30,30,40,0.9); padding: 15px; border-radius: 8px; z-index: 10; max-width: 300px; border: 1px solid #444; }}
        h3 {{ margin-top: 0; color: #5cd65c; }}
    </style>
</head>
<body>
    <div id="panel">
        <h3>DynamicSepticSystem</h3>
        <p><b>Azul:</b> Clases C#<br><b>Verde:</b> Metodos/Funciones</p>
        <p id="detalles">Pasa el mouse sobre un nodo para ver sus detalles.</p>
    </div>
    <div id="cy"></div>
    <script>
        var cy = cytoscape({{
            container: document.getElementById('cy'),
            elements: {json.dumps(elementos_js)},
            style: [
                {{
                    selector: 'node',
                    style: {{
                        'background-color': 'data(color)',
                        'label': 'data(label)',
                        'color': '#fff',
                        'font-size': '10px',
                        'text-wrap': 'wrap',
                        'text-valign': 'center',
                        'width': '40px',
                        'height': '40px'
                    }}
                }},
                {{
                    selector: 'edge',
                    style: {{
                        'width': 1.5,
                        'line-color': '#555',
                        'target-arrow-color': '#555',
                        'target-arrow-shape': 'triangle',
                        'curve-style': 'haystack'
                    }}
                }}
            ],
            layout: {{
                name: 'cose',
                componentSpacing: 40,
                nodeOverlap: 20,
                refresh: 20,
                fit: true
            }}
        }});
        
        cy.on('mouseover', 'node', function(evt){{
            var node = evt.target;
            document.getElementById('detalles').innerHTML = node.data('info');
        }});
    </script>
</body>
</html>
"""
    with open("mapa_proyecto.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("\n[Exito] Mapa visual creado correctamente en el archivo: mapa_proyecto.html")

if __name__ == "__main__":
    construir_interfaz_visual()
