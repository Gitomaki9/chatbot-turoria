# app_groq.py - Con búsqueda semántica (ChromaDB + Sentence Transformers)
import streamlit as st
import os
import re
from groq import Groq
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.utils import embedding_functions
import tempfile

from cargar_tutores import cargar_tutores, buscar_tutor_por_codigo, buscar_tutorados_por_docente, responder_pregunta_tutores

# Cargar datos de tutores
tutores_data = cargar_tutores()

# Configuración
st.set_page_config(
    page_title="Chatbot Tutoría UNSAAC",
    page_icon="🎓",
    layout="centered"
)

st.title("🎓 Chatbot de Tutoría Académica - UNSAAC")
st.markdown("*Asistente virtual con búsqueda semántica en el Reglamento de Tutoría Académica*")

# --- 1. Cargar corpus manual ---
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

# --- 2. Configurar Groq ---
@st.cache_resource
def init_groq():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        try:
            api_key = st.secrets["GROQ_API_KEY"]
        except:
            st.error("❌ GROQ_API_KEY no encontrada.")
            st.stop()
    return Groq(api_key=api_key)

# --- 3. Configurar búsqueda semántica con ChromaDB ---
@st.cache_resource
def init_vectorstore():
    """Crea una base de datos vectorial con los PDFs"""
    
    # Leer todos los PDFs
    docs = []
    data_dir = "./data/"
    
    if not os.path.exists(data_dir):
        st.warning("⚠️ Carpeta 'data/' no encontrada")
        return None
    
    for file in os.listdir(data_dir):
        if file.endswith(".pdf"):
            try:
                reader = PdfReader(os.path.join(data_dir, file))
                texto = ""
                for page in reader.pages:
                    texto += page.extract_text() + "\n"
                docs.append({"texto": texto, "nombre": file})
                st.info(f"📄 Procesando: {file}")
            except Exception as e:
                st.warning(f"Error al leer {file}: {e}")
    
    if not docs:
        return None
    
    # Dividir en fragmentos (chunks)
    chunks = []
    for doc in docs:
        texto = doc["texto"]
        # Dividir por párrafos
        for i, parrafo in enumerate(texto.split("\n\n")):
            if len(parrafo.strip()) > 50:
                chunks.append({
                    "texto": parrafo.strip(),
                    "fuente": doc["nombre"],
                    "chunk_id": i
                })
    
    st.info(f"📊 {len(chunks)} fragmentos creados")
    
    # Crear embeddings
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="paraphrase-multilingual-MiniLM-L12-v2"
    )
    
    # Crear base de datos ChromaDB en memoria
    client = chromadb.Client()
    collection = client.create_collection(
        name="reglamento",
        embedding_function=embedding_fn
    )
    
    # Agregar fragmentos a la base de datos
    for i, chunk in enumerate(chunks):
        collection.add(
            documents=[chunk["texto"]],
            metadatas=[{"fuente": chunk["fuente"], "chunk_id": str(chunk["chunk_id"])}],
            ids=[f"chunk_{i}"]
        )
    
    st.success(f"✅ Base de datos vectorial lista ({len(chunks)} fragmentos)")
    
    return collection, chunks

# --- 4. Función para buscar semánticamente ---
def buscar_semanticamente(collection, pregunta, n_resultados=5):
    """Busca los fragmentos más relevantes usando embeddings"""
    try:
        results = collection.query(
            query_texts=[pregunta],
            n_results=n_resultados
        )
        
        if results['documents']:
            return results['documents'][0]
        else:
            return []
    except Exception as e:
        st.warning(f"Error en búsqueda: {e}")
        return []

# --- 5. Responder ---
def responder(pregunta, corpus, groq_client, vectorstore):
    pregunta_min = pregunta.lower().strip()
    
    # 1. Buscar en corpus manual
    for intent, data in corpus.items():
        for p in data["preguntas"]:
            if p.lower() in pregunta_min or pregunta_min in p.lower():
                return data["respuesta"], "Corpus manual ⚡"
    # 1.5 Buscar en datos de tutores (antes de RAG)
    respuesta_tutores, fuente_tutores = responder_pregunta_tutores(tutores_data, pregunta)
    if respuesta_tutores:
        return respuesta_tutores, fuente_tutores
    
    # 2. Búsqueda semántica en PDFs
    if vectorstore:
        try:
            collection, chunks = vectorstore
            fragmentos = buscar_semanticamente(collection, pregunta, n_resultados=5)
            
            if fragmentos:
                contexto = "\n\n".join(fragmentos)
                
                prompt = f"""
                Eres un asistente virtual de la UNSAAC. 
                Responde la pregunta del usuario usando SOLO el contexto proporcionado.
                
                Contexto (del Reglamento de Tutoría Académica):
                {contexto[:8000]}
                
                Pregunta del usuario: {pregunta}
                
                Respuesta (basada SOLO en el contexto):
                """
                
                response = groq_client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=500
                )
                
                return response.choices[0].message.content, "Búsqueda semántica 🔍"
            else:
                return "No encontré información relevante en el reglamento.", "Sin información"
        except Exception as e:
            return f"Error en búsqueda semántica: {e}", "Error"
    
    return "No encontré información sobre eso.", "Sin información"

# --- Main ---
corpus = cargar_corpus()
groq_client = init_groq()
vectorstore = init_vectorstore()

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
    
    respuesta, fuente = responder(prompt, corpus, groq_client, vectorstore)
    
    st.session_state.messages.append({"role": "assistant", "content": respuesta})
    with st.chat_message("assistant"):
        st.markdown(respuesta)
        st.caption(f"Fuente: {fuente}")
