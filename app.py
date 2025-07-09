import streamlit as st
import cv2
import numpy as np
import pytesseract
from PIL import Image
import os
import tempfile
import json

# Configuración inicial
st.set_page_config(page_title="ArquitectoBot", page_icon="🏗️")
st.title("🏗️ ArquitectoBot - Asistente para Planos Arquitectónicos")

# Inicializar el historial del chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostrar historial del chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Función para procesar planos
def procesar_plano(archivo_plano):
    # Guardar archivo temporalmente
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(archivo_plano.read())
        tmp_path = tmp.name
    
    # Convertir PDF a imagen (simplificado - en producción usar pdf2image)
    images = [np.array(Image.open(archivo_plano))]  # Esto funciona para imágenes directas
    
    resultados = []
    
    for img in images:
        # Preprocesamiento de imagen
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
        
        # Detección de contornos
        contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filtrar contornos importantes
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 100:  # Filtrar por tamaño
                x, y, w, h = cv2.boundingRect(cnt)
                centro_x = x + w/2
                centro_y = y + h/2
                resultados.append({
                    "x": centro_x,
                    "y": centro_y,
                    "tipo": "elemento_arquitectonico",
                    "descripcion": f"Elemento de {w}x{h}px"
                })
    
    # OCR para detectar texto
    texto = pytesseract.image_to_string(img)
    lineas_texto = [linea for linea in texto.split('\n') if linea.strip()]
    
    # Procesar texto para coordenadas (ejemplo: "(x, y)" )
    for linea in lineas_texto:
        if '(' in linea and ')' in linea:
            try:
                coord_str = linea[linea.index('(')+1:linea.index(')')]
                x, y = map(float, coord_str.split(','))
                resultados.append({
                    "x": x,
                    "y": y,
                    "tipo": "coordenada_texto",
                    "descripcion": linea
                })
            except:
                pass
    
    os.unlink(tmp_path)
    return resultados

# Función para generar código Dynamo
def generar_codigo_dynamo(puntos):
    codigo = """# Python script for Dynamo
import clr
clr.AddReference('ProtoGeometry')
from Autodesk.DesignScript.Geometry import *

# Puntos detectados en el plano
puntos = [\n"""
    
    for punto in puntos:
        codigo += f"    Point.ByCoordinates({punto['x']}, {punto['y']}, 0),  # {punto['descripcion']}\n"
    
    codigo += """]

# Output para Dynamo
OUT = puntos
"""
    return codigo

# Cargador de archivos
uploaded_file = st.file_uploader("Cargar plano arquitectónico (PDF o imagen)", type=["pdf", "png", "jpg", "jpeg"])

if uploaded_file is not None:
    # Mostrar imagen
    if uploaded_file.type in ["image/png", "image/jpeg"]:
        image = Image.open(uploaded_file)
        st.image(image, caption="Plano cargado", use_column_width=True)
    
    # Procesar plano cuando el usuario lo solicite
    if st.button("Analizar plano"):
        with st.spinner("Procesando plano..."):
            puntos = procesar_plano(uploaded_file)
            
            if puntos:
                st.success(f"Se detectaron {len(puntos)} puntos importantes!")
                
                # Mostrar puntos en un dataframe
                st.dataframe(puntos)
                
                # Generar código Dynamo
                codigo_dynamo = generar_codigo_dynamo(puntos)
                
                # Mostrar código
                st.subheader("Código Python para Dynamo")
                st.code(codigo_dynamo, language='python')
                
                # Agregar al chat
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"He analizado el plano y encontrado {len(puntos)} puntos importantes. Aquí está el código para Dynamo."
                })
                
                # Botón para descargar código
                st.download_button(
                    label="Descargar script Python",
                    data=codigo_dynamo,
                    file_name="plano_a_dynamo.py",
                    mime="text/python"
                )
            else:
                st.warning("No se detectaron puntos importantes en el plano.")

# Interfaz de chat
if prompt := st.chat_input("Hazme preguntas sobre el plano..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Respuesta del bot (simplificada)
    with st.chat_message("assistant"):
        respuesta = "Puedo ayudarte a analizar planos arquitectónicos. Por favor, carga un plano para comenzar."
        if uploaded_file:
            respuesta = "Tengo el plano cargado. Haz clic en 'Analizar plano' para extraer las coordenadas."
        st.markdown(respuesta)
    
    st.session_state.messages.append({"role": "assistant", "content": respuesta})
