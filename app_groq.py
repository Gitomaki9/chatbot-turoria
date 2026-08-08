# app_groq.py - Chatbot con búsqueda semántica (ChromaDB + Sentence Transformers) + Datos de tutores
import streamlit as st
import os
import re
from groq import Groq
from PyPDF2 import PdfReader
import chromadb
from chromadb.utils import embedding_functions
import tempfile

# Forzar recarga de tutores (temporal)
import cargar_tutores
cargar_tutores.cargar_tutores.clear()
tutores_data = cargar_tutores.cargar_tutores()
# Importar funciones para cargar tutores
from cargar_tutores import cargar_tutores, buscar_tutor_por_codigo, buscar_tutorados_por_docente, responder_pregunta_tutores, listar_todos_tutores

# Cargar datos de tutores
tutores_data = cargar_tutores()

# Configuración de la página
st.set_page_config(
    page_title="Chatbot Tutoría UNSAAC",
    page_icon="🎓",
    layout="centered"
)

st.title("🎓 Chatbot de Tutoría Académica - UNSAAC")
st.markdown("*Asistente virtual para consultas sobre el Reglamento de Tutoría Académica y tutores*")

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
            st.error("❌ GROQ_API_KEY no encontrada. Revisa los secretos de Streamlit.")
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
                    page_text = page.extract_text()
                    if page_text:
                        texto += page_text + "\n"
                if texto.strip():
                    docs.append({"texto": texto, "nombre": file})
                    st.info(f"📄 Procesando: {file}")
            except Exception as e:
                st.warning(f"Error al leer {file}: {e}")
    
    if not docs:
        st.warning("⚠️ No se encontraron documentos PDF en data/")
        return None
    
    # Dividir en fragmentos (chunks)
    chunks = []
    for doc in docs:
        texto = doc["texto"]
        for i, parrafo in enumerate(texto.split("\n\n")):
            if len(parrafo.strip()) > 50:
                chunks.append({
                    "texto": parrafo.strip(),
                    "fuente": doc["nombre"],
                    "chunk_id": i
                })
    
    if not chunks:
        st.warning("⚠️ No se pudieron crear fragmentos del PDF")
        return None
    
    st.info(f"📊 {len(chunks)} fragmentos creados")
    
    # Crear embeddings
    try:
        embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="paraphrase-multilingual-MiniLM-L12-v2"
        )
    except Exception as e:
        st.error(f"❌ Error al cargar modelo de embeddings: {e}")
        return None
    
    # Crear base de datos ChromaDB en memoria
    try:
        client = chromadb.Client()
        
        # Eliminar la colección si ya existe
        try:
            client.delete_collection("reglamento")
            st.info("🔄 Colección anterior eliminada")
        except:
            pass  # No existía, continuar
        
        collection = client.create_collection(
            name="reglamento",
            embedding_function=embedding_fn
        )
        
        # Agregar fragmentos a la base de datos en lotes
        batch_size = 50
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]
            for j, chunk in enumerate(batch):
                collection.add(
                    documents=[chunk["texto"]],
                    metadatas=[{"fuente": chunk["fuente"], "chunk_id": str(chunk["chunk_id"])}],
                    ids=[f"chunk_{i+j}"]
                )
        
        st.success(f"✅ Base de datos vectorial lista ({len(chunks)} fragmentos)")
        return collection, chunks
    except Exception as e:
        st.error(f"❌ Error al crear base de datos vectorial: {e}")
        return None

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

# --- 5. Responder (con el orden correcto) ---
def responder(pregunta, corpus, groq_client, vectorstore):
    pregunta_min = pregunta.lower().strip()
    
    # --- 1. PRIMERO: Buscar en datos de tutores (CSV) ---
    respuesta_tutores, fuente_tutores = responder_pregunta_tutores(tutores_data, pregunta)
    if respuesta_tutores:
        return respuesta_tutores, fuente_tutores
    
    # --- 2. SEGUNDO: Buscar en corpus manual ---
    for intent, data in corpus.items():
        for p in data["preguntas"]:
            if p.lower() in pregunta_min or pregunta_min in p.lower():
                return data["respuesta"], "Corpus manual ⚡"
    
    # --- 3. TERCERO: Búsqueda semántica en PDFs (RAG) ---
    if vectorstore:
        try:
            collection, chunks = vectorstore
            fragmentos = buscar_semanticamente(collection, pregunta, n_resultados=5)
            
            if fragmentos:
                contexto = "\n\n".join(fragmentos)
                
                prompt = f"""
                Eres un asistente virtual de la UNSAAC. 
                Responde la pregunta del usuario usando SOLO el contexto proporcionado.
                Si el contexto no contiene información relevante, responde que no encontraste la información.
                
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

# Mostrar estado de los datos cargados en la barra lateral
with st.sidebar:
    st.header("📊 Datos cargados")
    st.write(f"📚 Corpus manual: {len(corpus)} intents")
    if tutores_data:
        st.write(f"👨‍🏫 Tutores: {len(tutores_data)} docentes")
        total_tutorados = sum(len(t) for t in tutores_data.values())
        st.write(f"📋 Tutorados: {total_tutorados} estudiantes")
    else:
        st.write("⚠️ No se cargaron datos de tutores")
    
    st.divider()
    st.caption("🔍 El chatbot busca en:")
    st.caption("1️⃣ Datos de tutores (CSV)")
    st.caption("2️⃣ Corpus manual")
    st.caption("3️⃣ Reglamento (PDF)")

# Inicializar historial de chat
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "¡Hola! Soy el asistente virtual de tutoría académica de la UNSAAC. Puedo ayudarte con:\n\n• 📋 Consultas sobre tutores y tutorados\n• 📚 Preguntas sobre el Reglamento de Tutoría\n• 🎓 Información sobre la Escuela Profesional\n\n¿En qué puedo ayudarte?"}
    ]

# Mostrar mensajes del chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input del usuario
if prompt := st.chat_input("Escribe tu pregunta aquí..."):
    # Agregar mensaje del usuario
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Obtener respuesta
    with st.spinner("Buscando respuesta..."):
        respuesta, fuente = responder(prompt, corpus, groq_client, vectorstore)
    
    # Agregar respuesta del asistente
    st.session_state.messages.append({"role": "assistant", "content": respuesta})
    with st.chat_message("assistant"):
        st.markdown(respuesta)
        st.caption(f"Fuente: {fuente}")
