import streamlit as st
import json
import os
from openai import OpenAI

st.set_page_config(page_title="UX Studio", layout="wide")
client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

def buscar_archivos_en_disco(pregunta):
    archivos_encontrados = {}
    tokens = pregunta.lower().replace("?", "").split()
    palabras = [t.replace(".cs", "") for t in tokens if len(t) > 2]
    
    for raiz, dirs, archivos in os.walk("."):
        if any(x in raiz for x in ["graphify-out", ".git", "obj", "bin", "SKILLS4AI", "node_modules"]):
            continue
        for archivo in archivos:
            if archivo.lower().endswith(".cs"):
                nombre_base = archivo.lower().replace(".cs", "")
                if any(p in nombre_base for p in palabras) or any(nombre_base in p for p in palabras):
                    archivos_encontrados[archivo.upper()] = os.path.join(raiz, archivo)
    return archivos_encontrados

def extraer_codigo_fuente(rutas_archivos):
    contenido_codigo = ""
    for nombre, ruta in rutas_archivos.items():
        try:
            with open(ruta, "r", encoding="utf-8", errors="ignore") as f:
                lineas = f.readlines()
                codigo_recortado = "".join(lineas[:120])
                contenido_codigo += f"\n\n--- CODIGO FUENTE REAL DE: {nombre} ---\n{codigo_recortado}"
        except Exception:
            continue
    return contenido_codigo

st.title("🎨 UX/UI Pro Max Studio")
st.caption("Workspace local conectado a tus archivos de C# y Skill MCP")

prompt = st.text_input("Ingresa tu consulta (ej: Redisena PanelPrincipal.cs) y presiona Enter:")

if prompt:
    dict_archivos = buscar_archivos_en_disco(prompt)
    codigo_real = extraer_codigo_fuente(dict_archivos)
    
    with st.sidebar:
        st.header("🔍 Workspace C#")
        if dict_archivos:
            st.success(f"Inyectado: {list(dict_archivos.keys())}")
        else:
            st.warning("Sin archivo fuente directo.")
            
    system_prompt = f"Eres un Ingeniero UX/UI Senior experto en C# Windows Forms. Genera estructuras interactivas web completas envueltas de forma estricta entre bloques ```html utilizando componentes responsivos oscuros modernos.\n\nCODIGO FUENTE REAL:\n{codigo_real}"
    mensajes_ia = [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]
    
    with st.spinner("Tu RTX 3060 Ti esta procesando el codigo..."):
        try:
            completion = client.chat.completions.create(model="local-model", messages=mensajes_ia, temperature=0.4)
            respuesta = completion.choices[0].message.content
            
            st.markdown("### 🖥️ Propuesta Arquitectonica e Interfaz:")
            if "```html" in respuesta:
                partes = respuesta.split("```html")
                st.markdown(partes[0])
                for parte in partes[1:]:
                    subpartes = parte.split("```")
                    st.components.v1.html(subpartes[0], height=500, scrolling=True)
                    if len(subpartes) > 1:
                        st.markdown(subpartes[1])
            else:
                st.markdown(respuesta)
        except Exception as e:
            st.error(f"Error de conexion con LM Studio: {e}")
