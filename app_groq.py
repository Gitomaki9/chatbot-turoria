# app_groq.py - Chatbot con búsqueda semántica (ChromaDB + Sentence Transformers) + Datos de tutores + Cursos + Cronograma
import streamlit as st
import os
import re
from groq import Groq
from PyPDF2 import PdfReader
import chromadb
from chromadb.utils import embedding_functions
import tempfile

from dotenv import load_dotenv
load_dotenv()

# Importar funciones para cargar cursos
from cargar_cursos import (
    cargar_cursos,
    buscar_cursos_por_semestre,
    buscar_curso_por_codigo,
    buscar_cursos_por_docente,
    buscar_cursos_por_aula,
    formatear_lista_cursos,
    responder_pregunta_cursos
)

# Cargar datos de cursos
cursos_data = cargar_cursos()

# Importar funciones para cargar tutores
from cargar_tutores import (
    cargar_tutores,
    buscar_tutor_por_codigo,
    buscar_tutorados_por_docente,
    responder_pregunta_tutores,
    listar_todos_tutores
)

# Cargar datos de tutores
tutores_data = cargar_tutores()

# Configuración de la página
st.set_page_config(
    page_title="Chatbot Tutoría UNSAAC",
    page_icon="🎓",
    layout="centered"
)

st.title("🎓 Chatbot de Tutoría y Servicios UNSAAC")
st.markdown("*Asistente virtual para consultas sobre tutoría académica, servicios y vida universitaria UNSAAC*")

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
            st.error("❌ GROQ_API_KEY no encontrada. Configura la variable de entorno GROQ_API_KEY o los secretos de Streamlit.")
            st.stop()
    return Groq(api_key=api_key)

# --- 3. Configurar búsqueda semántica con ChromaDB ---
@st.cache_resource
def init_vectorstore():
    """Crea una base de datos vectorial con los PDFs usando RecursiveCharacterTextSplitter"""
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    
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
            except Exception as e:
                pass
    
    if not docs:
        return None
    
    # Dividir en fragmentos (chunks) usando RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    
    chunks = []
    for doc in docs:
        doc_chunks = splitter.split_text(doc["texto"])
        for i, chunk_text in enumerate(doc_chunks):
            if len(chunk_text.strip()) > 30:
                chunks.append({
                    "texto": chunk_text.strip(),
                    "fuente": doc["nombre"],
                    "chunk_id": f"pdf_{i}"
                })
    
    # Indizar también la información del corpus.txt en la base vectorial para RAG semántico
    corpus_dict = cargar_corpus()
    for intent, data in corpus_dict.items():
        contenido_corpus = f"Información oficial sobre {intent.replace('_', ' ')}:\n" + data["respuesta"]
        chunks.append({
            "texto": contenido_corpus,
            "fuente": f"Servicios UNSAAC ({intent})",
            "chunk_id": f"corpus_{intent}"
        })
    
    if not chunks:
        return None
    
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
        
        try:
            client.delete_collection("reglamento")
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
    
    # ============================================================
    # 🔥 MAPA DE PALABRAS CLAVE (prioridad máxima)
    # ============================================================
    mapa_palabras_clave = {
        # --- Cronograma ---
        "inicio de clases": "cronograma_2026_inicio_clases",
        "empiezan las clases": "cronograma_2026_inicio_clases",
        "comienzo de clases": "cronograma_2026_inicio_clases",
        "cuándo empiezan las clases": "cronograma_2026_inicio_clases",
        "terminan las clases": "cronograma_2026_fin_clases",
        "fin de clases": "cronograma_2026_fin_clases",
        "finaliza el semestre": "cronograma_2026_fin_clases",
        "fechas de matrícula": "cronograma_2026_matricula",
        "cuándo es la matrícula": "cronograma_2026_matricula",
        "matrícula 2026": "cronograma_2026_matricula",
        "exámenes parciales": "cronograma_2026_examenes_parciales",
        "cuándo son los parciales": "cronograma_2026_examenes_parciales",
        "vacaciones": "cronograma_2026_vacaciones",
        "receso académico": "cronograma_2026_vacaciones",
        "actualización docente": "cronograma_2026_actualizacion_docente",
        
        # --- Tutoría (solo preguntas generales, NO para tutores específicos) ---
        "qué hace un tutor": "funciones_tutor",
        "qué es un tutor": "funciones_tutor",
        "funciones del tutor": "funciones_tutor",
        "responsabilidades del tutor": "funciones_tutor",
        "fines de la tutoría": "fines_tutoria",
        "que es la tutoría": "definicion_tutoria",
        
        # --- Aniversario ---
        "aniversario": "aniversario_carrera",
        "13 de diciembre": "aniversario_carrera",
        
        # --- Créditos ---
        "créditos máximos": "creditos_maximos",
        "máximo de créditos": "creditos_maximos",
        "24 créditos": "creditos_maximos",
        
        # --- Movilidad ---
        "a qué universidad puedo irme": "universidades_movilidad",
        "convenios": "universidades_movilidad",
        
        # --- Comedor ---
        "comedor": "comedor_universitario",
        "reserva": "comedor_universitario",
        "cupo": "comedor_universitario",
        "comensal": "comedor_universitario",
        
        # --- Becas ---
        "beca": "becas_unsaac",
        "becas": "becas_unsaac",
        "apoyo económico": "becas_unsaac",
        
        # --- Movilidad Académica ---
        "movilidad académica": "movilidad_academica",
        "intercambio": "movilidad_academica",
        "estudiar en el extranjero": "movilidad_academica",
        
        # --- Carnet ---
        "carnet": "carnet_universitario",
        "carné": "carnet_universitario",
        "lycoris": "carnet_universitario",
        
        # --- Trámites ---
        "pladdes": "tramites_academicos_pladdes",
        "trámite": "tramites_academicos_pladdes",
        "recaudación": "tramites_academicos_pladdes",
        "mesa de partes": "tramites_academicos_pladdes",
        
        # --- Centro de Cómputo ---
        "centro de cómputo": "centro_computo",
        "computo": "centro_computo",
        "pronabec": "centro_computo",
        
        # --- Idiomas ---
        "idiomas": "centro_idiomas",
        "inglés": "centro_idiomas",
        "ingles": "centro_idiomas",
        "suficiencia": "centro_idiomas",
        
        # --- Egreso ---
        "egreso": "creditos_egreso_unsaac",
        "egresar": "creditos_egreso_unsaac",
        "graduarme": "creditos_egreso_unsaac",
        "créditos necesarios": "creditos_egreso_unsaac",
        "requisitos para egresar": "creditos_egreso_unsaac",
        
        # --- Número máximo de tutorados ---
        "cuántos estudiantes puede tener un tutor": "numero_maximo_tutorados",
        "máximo de tutorados": "numero_maximo_tutorados",
        "cuantos alumnos por tutor": "numero_maximo_tutorados",
        
        # --- Requisitos de cursos (para que vaya a CSV) ---
        "requisitos para": "buscar_curso_general",
        "requisitos del curso": "buscar_curso_general",
        "qué necesito para llevar": "buscar_curso_general",
        "prerrequisitos de": "buscar_curso_general",
    }
    
    # 🔍 PRIMERO: Buscar en el mapa de palabras clave
    for kw, intent_key in mapa_palabras_clave.items():
        if kw in pregunta_min and intent_key in corpus:
            return corpus[intent_key]["respuesta"], "Corpus manual ⚡"
    
    # --- 1. Buscar en datos de tutores (CSV) ---
    respuesta_tutores, fuente_tutores = responder_pregunta_tutores(tutores_data, pregunta)
    if respuesta_tutores:
        return respuesta_tutores, fuente_tutores
    
    # --- 2. Buscar en datos de cursos (CSV) ---
    respuesta_cursos, fuente_cursos = responder_pregunta_cursos(cursos_data, pregunta)
    if respuesta_cursos:
        return respuesta_cursos, fuente_cursos
    
    # --- 3. Buscar en corpus manual (coincidencia directa) ---
    for intent, data in corpus.items():
        for p in data["preguntas"]:
            if p.lower() in pregunta_min or pregunta_min in p.lower():
                return data["respuesta"], "Corpus manual ⚡"
    
    # --- 4. Búsqueda semántica en VectorStore (RAG) ---
    if vectorstore:
        try:
            collection, chunks = vectorstore
            fragmentos = buscar_semanticamente(collection, pregunta, n_resultados=5)
            
            if fragmentos:
                contexto = "\n\n".join(fragmentos)
                
                prompt = f"""
                Eres un asistente virtual de la UNSAAC (Universidad Nacional de San Antonio Abad del Cusco). 
                Responde a la pregunta del usuario utilizando la información del contexto proporcionado.
                Sé amable, directo y estructurado. Si la información no está en el contexto, indica amablemente dónde o cómo el estudiante puede consultar (ej. Bienestar Universitario, DRSA, Mesa de Partes).
                
                Contexto oficial UNSAAC:
                {contexto[:8000]}
                
                Pregunta del usuario: {pregunta}
                
                Respuesta:
                """
                
                response = groq_client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.6,
                    max_tokens=600
                )
                
                return response.choices[0].message.content, "Búsqueda semántica 🔍"
            else:
                return "No encontré información específica en nuestros registros. Te sugiero consultar en la página oficial de la UNSAAC o la Mesa de Partes Virtual.", "Sin información"
        except Exception as e:
            return f"Error en búsqueda semántica: {e}", "Error"
    
    return "No encontré información sobre eso.", "Sin información"

# --- Main ---
corpus = cargar_corpus()
groq_client = init_groq()

with st.spinner("⏳ Inicializando base de datos vectorial y cargando reglamentos (solo la primera vez tomará 1-2 minutos para descargar el modelo)..."):
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
    st.caption("1️⃣ Mapa de palabras clave (Cronograma/Servicios)")
    st.caption("2️⃣ Datos de tutores (CSV)")
    st.caption("3️⃣ Datos de cursos (CSV)")
    st.caption("4️⃣ Corpus manual")
    st.caption("5️⃣ Reglamento (PDF) - RAG")

# Inicializar historial de chat
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "¡Hola! Soy el asistente virtual de tutoría académica de la UNSAAC. Puedo ayudarte con:\n\n• 📋 Consultas sobre tutores y tutorados\n• 📚 Preguntas sobre el Reglamento de Tutoría\n• 🎓 Información sobre la Escuela Profesional\n• 📅 Cronograma académico 2026\n\n¿En qué puedo ayudarte?"}
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
