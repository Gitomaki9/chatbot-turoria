# cargar_tutores.py
import csv
import streamlit as st
import re

@st.cache_data
def cargar_tutores():
    """
    Carga la lista de tutores y tutorados desde el archivo CSV.
    Formato (5 columnas):
    apellido_docente, nombre_docente, codigo_tutorado, apellido_tutorado, nombre_tutorado
    """
    tutores = {}
    
    try:
        with open("tutores.csv", 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Leer las 5 columnas
                apellido_docente = row['apellido_docente'].strip()
                nombre_docente = row['nombre_docente'].strip()
                codigo = row['codigo_tutorado'].strip()
                apellido_tutorado = row['apellido_tutorado'].strip()
                nombre_tutorado = row['nombre_tutorado'].strip()
                
                # Crear nombre completo del docente
                docente = f"{apellido_docente}, {nombre_docente}"
                
                # Crear nombre completo del tutorado
                nombre_completo = f"{apellido_tutorado}, {nombre_tutorado}"
                
                if docente not in tutores:
                    tutores[docente] = []
                tutores[docente].append({
                    'codigo': codigo,
                    'nombre': nombre_completo
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
    Retorna: lista de (docente, nombre_tutorado, codigo)
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
    Retorna: lista de tutorados
    """
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

def responder_pregunta_tutores(tutores, pregunta):
    """
    Función principal para procesar preguntas sobre tutores.
    Retorna: (respuesta, fuente)
    """
    pregunta_lower = pregunta.lower().strip()
    import re
    
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
                docente_completo = buscar_docente_por_nombre(tutores, palabra)
                if not docente_completo:
                    docente_completo = palabra.upper()
                
                respuesta = f"👨‍🏫 Los tutorados del docente **{docente_completo}** son:\n\n"
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
        print("\n1. Buscando código 164246:")
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
        print("\n3. Buscando tutorados de 'Pillco Quispe':")
        tutorados = buscar_tutorados_por_docente(tutores, "Pillco Quispe")
        if tutorados:
            for t in tutorados[:5]:
                print(f"   ✅ {t['nombre']} (código {t['codigo']})")
            if len(tutorados) > 5:
                print(f"   ... y {len(tutorados)-5} más")
    else:
        print("❌ No se pudieron cargar los datos.")
