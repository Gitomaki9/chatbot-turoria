# app_groq.py - Versión para Streamlit Cloud
import streamlit as st
import os
import re
from dotenv import load_dotenv
from groq import Groq

# Cargar variables de entorno
load_dotenv()

# Configuración de la página
st.set_page_config(
    page_title="Chatbot Tutoría UNSAAC",
    page_icon="🎓",
    layout="centered"
)

st.title("🎓 Chatbot de Tutoría Académica - UNSAAC")
st.markdown("*Asistente virtual para consultas sobre el Reglamento de Tutoría Académica*")

# --- Cargar corpus manual ---
@st.cache_data
def cargar_corpus():
    corpus = {}
    try:
        with open("corpus.txt", "r", encoding="utf-8") as f:
            contenido = f.read()
        
        bloques = contenido.split("###")
        for bloque in bloques:
            bloque = bloque.strip()
            if not bloque:
                continue
            
            intent_match = re.search(r'INTENT:\s*(\w+)', bloque)
            if not intent_match:
                continue
            intent = intent_match.group(1)
            
            preguntas_match = re.search(r'PREGUNTAS:\s*([\s\S]*?)RESPUESTA:', bloque)
            if not preguntas_match:
                continue
            preguntas_texto = preguntas_match.group(1)
            preguntas = []
            for linea in preguntas_texto.strip().split("\n"):
                linea = linea.strip()
                if linea.startswith("-"):
                    preguntas.append(linea[1:].strip())
            
            respuesta_match = re.search(r'RESPUESTA:\s*([\s\S]*?)(?=###|$)', bloque)
            if not respuesta_match:
                continue
            respuesta = respuesta_match.group(1).strip()
            
            if preguntas and respuesta:
                corpus[intent] = {"preguntas": preguntas, "respuesta": respuesta}
        
        return corpus
    except Exception as e:
        st.error(f"Error al cargar corpus: {e}")
        return {}

# --- Configurar Groq ---
# --- Configurar Groq ---
@st.cache_resource
def init_groq():
    # Intentar leer de diferentes formas
    api_key = os.getenv("GROQ_API_KEY")
    
    # Si no está en el entorno, intentar leer desde st.secrets
    if not api_key:
        try:
            api_key = st.secrets["GROQ_API_KEY"]
        except:
            pass
    
    # Si aún no está, mostrar error
    if not api_key:
        st.error("❌ GROQ_API_KEY no encontrada. Revisa los secretos de Streamlit.")
        st.stop()
    
    return Groq(api_key=api_key)

# --- Función para responder ---
def responder(pregunta, corpus, groq_client):
    pregunta_min = pregunta.lower().strip()
    
    # 1. Buscar en corpus manual
    for intent, data in corpus.items():
        for p in data["preguntas"]:
            if p.lower() in pregunta_min or pregunta_min in p.lower():
                return data["respuesta"], "Corpus manual ⚡"
    
    # 2. Usar Groq API
    if groq_client:
        try:
            # Leer el reglamento PDF
            texto_pdf = ""
            data_dir = "./data/"
            if os.path.exists(data_dir):
                from PyPDF2 import PdfReader
                for file in os.listdir(data_dir):
                    if file.endswith(".pdf"):
                        try:
                            reader = PdfReader(os.path.join(data_dir, file))
                            for page in reader.pages:
                                texto_pdf += page.extract_text() + "\n"
                        except Exception:
                            pass
            
            # Construir prompt con contexto
            prompt = f"""
            Eres un asistente virtual de la UNSAAC. Responde la pregunta del usuario usando el contexto proporcionado.
            
            Contexto (del reglamento):
            {texto_pdf[:8000]}  # Limitar a 8000 caracteres
            
            Pregunta del usuario: {pregunta}
            
            Respuesta (basada SOLO en el contexto):
            """
            
            response = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content, "Groq API 🚀"
        except Exception as e:
            return f"Error con Groq: {e}", "Error"
    
    return "No encontré información sobre eso.", "Sin información"

# --- Main ---
corpus = cargar_corpus()
groq_client = init_groq()

if not groq_client:
    st.stop()

# Historial de chat
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "¡Hola! Soy el asistente virtual de tutoría académica de la UNSAAC. ¿En qué puedo ayudarte?"}
    ]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Escribe tu pregunta aquí..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    respuesta, fuente = responder(prompt, corpus, groq_client)
    
    st.session_state.messages.append({"role": "assistant", "content": respuesta})
    with st.chat_message("assistant"):
        st.markdown(respuesta)
        st.caption(f"Fuente: {fuente}")
