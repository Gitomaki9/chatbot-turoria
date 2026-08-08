# cargar_tutores.py
import csv
import streamlit as st
import pandas as pd

# En cargar_tutores.py, agrega esta función
def buscar_tutor_por_codigo_debug(tutores, codigo):
    """Versión con debug para ver qué está pasando"""
    codigo = str(codigo).strip()
    st.write(f"🔍 Buscando código: {codigo}")
    st.write(f"📚 Docentes disponibles: {list(tutores.keys())}")
    
    for docente, tutorados in tutores.items():
        st.write(f"👨‍🏫 Revisando docente: {docente}")
        for t in tutorados:
            st.write(f"   - Código: {t['codigo']} → {t['nombre']}")
            if t['codigo'] == codigo:
                return docente, t['nombre']
    return None, None
@st.cache_data
def cargar_tutores():
    """
    Carga la lista de tutores y tutorados desde el archivo CSV.
    Retorna un diccionario con la estructura:
    {
        "docente": [
            {"codigo": "123456", "nombre": "Apellido, Nombre"},
            ...
        ],
        ...
    }
    """
    tutores = {}
    
    try:
        with open("tutores.csv", 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                docente = row['docente'].strip()
                codigo = row['codigo_tutorado'].strip()
                nombre = row['nombre_tutorado'].strip()
                
                if docente not in tutores:
                    tutores[docente] = []
                tutores[docente].append({
                    'codigo': codigo,
                    'nombre': nombre
                })
        
        # Ordenar alfabéticamente los docentes
        tutores = dict(sorted(tutores.items()))
        
        return tutores
    except FileNotFoundError:
        st.error("❌ Archivo 'tutores.csv' no encontrado. Verifica que esté en la carpeta del proyecto.")
        return {}
    except Exception as e:
        st.error(f"❌ Error al cargar tutores: {e}")
        return {}

@st.cache_data
def cargar_tutores_dataframe():
    """
    Carga los tutores como DataFrame de pandas para búsquedas más rápidas.
    """
    try:
        df = pd.read_csv("tutores.csv", encoding='utf-8')
        return df
    except FileNotFoundError:
        st.error("❌ Archivo 'tutores.csv' no encontrado.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Error al cargar DataFrame: {e}")
        return pd.DataFrame()

def buscar_tutor_por_codigo(tutores, codigo):
    """
    Busca el tutor de un estudiante por su código.
    Retorna: (docente, nombre_tutorado) o (None, None)
    """
    codigo = str(codigo).strip()
    for docente, tutorados in tutores.items():
        for t in tutorados:
            if t['codigo'] == codigo:
                return docente, t['nombre']
    return None, None

def buscar_tutor_por_nombre(tutores, nombre):
    """
    Busca el tutor de un estudiante por su nombre (búsqueda parcial).
    Retorna: (docente, nombre_tutorado, codigo) o (None, None, None)
    """
    nombre = nombre.lower().strip()
    resultados = []
    for docente, tutorados in tutores.items():
        for t in tutorados:
            if nombre in t['nombre'].lower():
                resultados.append((docente, t['nombre'], t['codigo']))
    return resultados

def buscar_tutorados_por_docente(tutores, docente):
    """
    Devuelve la lista de tutorados de un docente (búsqueda parcial).
    Retorna: lista de tutorados o lista vacía
    """
    docente = docente.lower().strip()
    for d, tutorados in tutores.items():
        if docente in d.lower():
            return tutorados
    return []

def buscar_docente_por_nombre(tutores, nombre):
    """
    Busca un docente por su nombre (búsqueda parcial).
    Retorna: el nombre completo del docente o None
    """
    nombre = nombre.lower().strip()
    for docente in tutores.keys():
        if nombre in docente.lower():
            return docente
    return None

def listar_todos_tutores(tutores):
    """
    Devuelve la lista de todos los docentes.
    """
    return list(tutores.keys())

def contar_tutorados(tutores, docente=None):
    """
    Cuenta el número total de tutorados.
    Si se especifica un docente, cuenta solo los de ese docente.
    """
    if docente:
        tutorados = buscar_tutorados_por_docente(tutores, docente)
        return len(tutorados)
    else:
        total = 0
        for tutorados in tutores.values():
            total += len(tutorados)
        return total

# --- Funciones para integración con el chatbot ---

def responder_pregunta_tutores(tutores, pregunta):
    """
    Función principal para procesar preguntas sobre tutores.
    Retorna: (respuesta, fuente)
    """
    pregunta_lower = pregunta.lower().strip()
    
    # Buscar código de estudiante (6 dígitos)
    import re
    codigo_match = re.search(r'\b(\d{6})\b', pregunta)
    if codigo_match:
        codigo = codigo_match.group(1)
        tutor, nombre = buscar_tutor_por_codigo(tutores, codigo)
        if tutor:
            return f"📋 El tutor del estudiante **{nombre}** (código {codigo}) es: **{tutor}**", "Datos de tutores 📋"
        else:
            return f"❌ No encontré un tutor para el código **{codigo}**. Verifica que el código sea correcto.", "Datos de tutores 📋"
    
    # Buscar por nombre de estudiante
    if "estudiante" in pregunta_lower or "alumno" in pregunta_lower:
        # Extraer posible nombre
        palabras = pregunta_lower.split()
        # Buscar palabras que parezcan nombres (con comas o sin)
        for palabra in palabras:
            if len(palabra) > 3 and palabra not in ["estudiante", "alumno", "buscar", "nombre", "código", "codigo"]:
                resultados = buscar_tutor_por_nombre(tutores, palabra)
                if resultados:
                    respuesta = "🔍 Encontré estos resultados:\n\n"
                    for tutor, nombre, codigo in resultados:
                        respuesta += f"- {nombre} (código {codigo}) → Tutor: {tutor}\n"
                    return respuesta, "Datos de tutores 📋"
    
    # Buscar por nombre de docente
    if "docente" in pregunta_lower or "tutor" in pregunta_lower:
        palabras = pregunta_lower.split()
        for palabra in palabras:
            if len(palabra) > 3 and palabra not in ["docente", "tutor", "buscar", "nombre"]:
                tutorados = buscar_tutorados_por_docente(tutores, palabra)
                if tutorados:
                    respuesta = f"👨‍🏫 Los tutorados del docente **{palabra.upper()}** son:\n\n"
                    for t in tutorados:
                        respuesta += f"- {t['nombre']} (código {t['codigo']})\n"
                    return respuesta, "Datos de tutores 📋"
    
    return None, None

# --- Prueba rápida (solo se ejecuta si se corre el script directamente) ---
if __name__ == "__main__":
    print("="*50)
    print("📋 Cargando datos de tutores...")
    print("="*50)
    
    tutores = cargar_tutores()
    
    if tutores:
        print(f"✅ {len(tutores)} docentes cargados")
        print(f"✅ {contar_tutorados(tutores)} tutorados cargados")
        print("\n📚 Lista de docentes:")
        for i, docente in enumerate(listar_todos_tutores(tutores), 1):
            print(f"   {i}. {docente} ({len(tutores[docente])} tutorados)")
        
        print("\n" + "="*50)
        print("🔍 Prueba de búsqueda:")
        print("="*50)
        
        # Prueba 1: Buscar por código
        print("\n1. Buscando código 164246 (Jean Marco Pacha Quispe):")
        tutor, nombre = buscar_tutor_por_codigo(tutores, "164246")
        if tutor:
            print(f"   ✅ {nombre} → Tutor: {tutor}")
        
        # Prueba 2: Buscar por nombre de estudiante
        print("\n2. Buscando 'Pacha Quispe':")
        resultados = buscar_tutor_por_nombre(tutores, "Pacha Quispe")
        if resultados:
            for tutor, nombre, codigo in resultados:
                print(f"   ✅ {nombre} (código {codigo}) → Tutor: {tutor}")
        
        # Prueba 3: Buscar tutorados de un docente
        print("\n3. Buscando tutorados de 'Cutipa Arapa':")
        tutorados = buscar_tutorados_por_docente(tutores, "Cutipa Arapa")
        if tutorados:
            for t in tutorados[:5]:  # Mostrar solo los primeros 5
                print(f"   ✅ {t['nombre']} (código {t['codigo']})")
            if len(tutorados) > 5:
                print(f"   ... y {len(tutorados)-5} más")
    else:
        print("❌ No se pudieron cargar los datos.")
