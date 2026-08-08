# cargar_tutores.py
import csv
import streamlit as st
import pandas as pd
import re

@st.cache_data
def cargar_tutores():
    """
    Carga la lista de tutores y tutorados desde el archivo CSV.
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
        
        tutores = dict(sorted(tutores.items()))
        return tutores
    except FileNotFoundError:
        st.error("❌ Archivo 'tutores.csv' no encontrado.")
        return {}
    except Exception as e:
        st.error(f"❌ Error al cargar tutores: {e}")
        return {}

def buscar_tutor_por_codigo(tutores, codigo):
    """Busca el tutor de un estudiante por su código."""
    codigo = str(codigo).strip()
    for docente, tutorados in tutores.items():
        for t in tutorados:
            if t['codigo'] == codigo:
                return docente, t['nombre']
    return None, None

def buscar_tutor_por_nombre(tutores, nombre):
    """Busca el tutor de un estudiante por su nombre (búsqueda parcial)."""
    nombre = nombre.lower().strip()
    resultados = []
    for docente, tutorados in tutores.items():
        for t in tutorados:
            if nombre in t['nombre'].lower():
                resultados.append((docente, t['nombre'], t['codigo']))
    return resultados

def buscar_tutorados_por_docente(tutores, docente):
    """Devuelve la lista de tutorados de un docente."""
    docente = docente.lower().strip()
    resultados = []
    for d, tutorados in tutores.items():
        if docente in d.lower():
            for t in tutorados:
                resultados.append({
                    'codigo': t['codigo'],
                    'nombre': t['nombre']
                })
    return resultados

def listar_todos_tutores(tutores):
    """Devuelve la lista de todos los docentes."""
    return list(tutores.keys())

def contar_tutorados(tutores, docente=None):
    """Cuenta el número total de tutorados."""
    if docente:
        tutorados = buscar_tutorados_por_docente(tutores, docente)
        return len(tutorados)
    else:
        total = 0
        for tutorados in tutores.values():
            total += len(tutorados)
        return total

def buscar_docente_por_nombre(tutores, nombre):
    """Busca un docente por su nombre."""
    nombre = nombre.lower().strip()
    for docente in tutores.keys():
        if nombre in docente.lower():
            return docente
    return None

def responder_pregunta_tutores(tutores, pregunta):
    """Función principal para procesar preguntas sobre tutores."""
    pregunta_lower = pregunta.lower().strip()
    
    # 1. Buscar código de estudiante (6 dígitos)
    codigo_match = re.search(r'\b(\d{6})\b', pregunta)
    if codigo_match:
        codigo = codigo_match.group(1)
        tutor, nombre = buscar_tutor_por_codigo(tutores, codigo)
        if tutor:
            return f"📋 El tutor del estudiante **{nombre}** (código {codigo}) es: **{tutor}**", "Datos de tutores 📋"
        else:
            return f"❌ No encontré un tutor para el código **{codigo}**. Verifica que el código sea correcto.", "Datos de tutores 📋"
    
    # 2. Buscar por nombre de estudiante
    palabras = pregunta_lower.split()
    for palabra in palabras:
        if len(palabra) > 3 and palabra not in ["estudiante", "alumno", "buscar", "nombre", "código", "codigo", "docente", "tutor"]:
            resultados = buscar_tutor_por_nombre(tutores, palabra)
            if resultados:
                if len(resultados) == 1:
                    tutor, nombre, codigo = resultados[0]
                    return f"📋 El tutor del estudiante **{nombre}** (código {codigo}) es: **{tutor}**", "Datos de tutores 📋"
                else:
                    respuesta = "🔍 Encontré varios resultados:\n\n"
                    for tutor, nombre, codigo in resultados:
                        respuesta += f"- {nombre} (código {codigo}) → Tutor: {tutor}\n"
                    return respuesta, "Datos de tutores 📋"
    
    # 3. Buscar por nombre de docente
    for palabra in palabras:
        if len(palabra) > 3 and palabra not in ["docente", "tutor", "buscar", "nombre"]:
            tutorados = buscar_tutorados_por_docente(tutores, palabra)
            if tutorados:
                # Encontrar el nombre completo del docente
                docente_completo = buscar_docente_por_nombre(tutores, palabra)
                if not docente_completo:
                    docente_completo = palabra.upper()
                
                respuesta = f"👨‍🏫 Los tutorados del docente **{docente_completo}** son:\n\n"
                for t in tutorados:
                    respuesta += f"- {t['nombre']} (código {t['codigo']})\n"
                return respuesta, "Datos de tutores 📋"
    
    return None, None

# --- Prueba rápida ---
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
        
        # Prueba: Buscar tutorados de un docente
        print("\n🔍 Buscando tutorados de 'Quispe':")
        tutorados = buscar_tutorados_por_docente(tutores, "Quispe")
        if tutorados:
            for t in tutorados[:5]:
                print(f"   ✅ {t['nombre']} (código {t['codigo']})")
            if len(tutorados) > 5:
                print(f"   ... y {len(tutorados)-5} más")
    else:
        print("❌ No se pudieron cargar los datos.")
