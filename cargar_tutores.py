# cargar_tutores.py
import csv
import streamlit as st
import re

@st.cache_data
def cargar_tutores():
    """
    Carga la lista de tutores y tutorados desde el archivo CSV.
    Formato (4 columnas):
    apellido_docente, nombre_docente, codigo_tutorado, nombre_tutorado
    """
    tutores = {}
    
    try:
        with open("tutores.csv", 'r', encoding='utf-8') as f:
            # Leer todas las líneas y filtrar vacías
            lines = [line.strip() for line in f if line.strip()]
            
        if not lines:
            st.error("❌ El archivo tutores.csv está vacío.")
            return {}
        
        # Usar csv.DictReader con las líneas limpias
        import io
        reader = csv.DictReader(io.StringIO('\n'.join(lines)))
        
        for row in reader:
            try:
                # 4 columnas: apellido_docente, nombre_docente, codigo_tutorado, nombre_tutorado
                apellido_docente = (row.get('apellido_docente') or '').strip()
                nombre_docente = (row.get('nombre_docente') or '').strip()
                codigo = (row.get('codigo_tutorado') or '').strip()
                nombre_tutorado = (row.get('nombre_tutorado') or '').strip()
                
                # Verificar que todos los campos tengan datos
                if not all([apellido_docente, nombre_docente, codigo, nombre_tutorado]):
                    continue
                
                docente = f"{apellido_docente}, {nombre_docente}"
                
                if docente not in tutores:
                    tutores[docente] = []
                tutores[docente].append({
                    'codigo': codigo,
                    'nombre': nombre_tutorado
                })
            except Exception as e:
                # Saltar filas con errores
                continue
        
        tutores = dict(sorted(tutores.items()))
        return tutores
    except FileNotFoundError:
        st.error("❌ Archivo 'tutores.csv' no encontrado. Verifica que esté en la carpeta del proyecto.")
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

def buscar_docente_por_nombre(tutores, nombre):
    """Busca un docente por su nombre (búsqueda parcial)."""
    nombre = nombre.lower().strip()
    for docente in tutores.keys():
        if nombre in docente.lower():
            return docente
    return None

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

# Lista de palabras comunes que NO deben interpretarse como nombres o apellidos
STOPWORDS = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "del", "de", "al", "en", "yo", "tu", "tú",
    "él", "ella", "ellos", "ellas", "nosotros", "usted", "ustedes", "que", "qué", "quien", "quién",
    "quienes", "quiénes", "cual", "cuál", "cuales", "cuáles", "como", "cómo", "donde", "dónde",
    "cuando", "cuándo", "cuanto", "cuánto", "cuantos", "cuántos", "cuanta", "cuánta", "cuantas", "cuántas",
    "para", "por", "con", "sin", "sobre", "entre", "hasta", "desde", "hacia", "según", "segun", "acerca",
    "respecto", "relación", "relacionado", "referente", "detalle", "detalles", "pero", "mas", "mientras",
    "porque", "porqué", "es", "son", "fue", "fueron", "ser", "estar", "hacer", "tengo", "tiene", "tienen",
    "necesito", "necesitan", "puedo", "puede", "pueden", "saber", "sabe", "sabes", "quiero", "quiere",
    "deseo", "buscar", "solicitar", "pedir", "tramitar", "obtener", "reservar", "pagar", "egresar",
    "matricular", "inscribir", "créditos", "creditos", "requisitos", "requisito", "comedor", "beca",
    "becas", "movilidad", "intercambio", "carnet", "carné", "tramite", "trámite", "pladdes", "lycoris",
    "idiomas", "computo", "cómputo", "escuela", "facultad", "carrera", "semestre", "horario", "pago",
    "constancia", "certificado", "reglamento", "derechos", "deberes", "sanciones", "multas",
    "tutor", "tutores", "tutoria", "tutoría", "tutorado", "tutorados", "docente", "docentes",
    "profesor", "profesores", "estudiante", "estudiantes", "alumno", "alumnos", "nombre", "código",
    "codigo", "lista", "tabla", "ver", "dame", "dime", "diga", "dígame", "info", "información",
    "informacion", "ayuda", "consulta", "duda", "dudas", "tema", "temas"
}

def responder_pregunta_tutores(tutores, pregunta):
    """Función principal para procesar preguntas sobre tutores."""
    if not tutores:
        return None, None

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
    
    # Verificar si la consulta contiene intención o términos explícitos sobre tutores/alumnos
    PALABRAS_INTENCION_TUTOR = {
        "tutor", "tutores", "tutoria", "tutoría", "tutorado", "tutorados",
        "docente", "docentes", "profesor", "profesores", "alumno", "alumnos",
        "estudiante", "estudiantes", "código", "codigo"
    }
    
    palabras_raw = re.findall(r'\b\w+\b', pregunta_lower)
    tiene_intencion_tutor = any(p in PALABRAS_INTENCION_TUTOR for p in palabras_raw)
    
    # Filtrar palabras candidatas que puedan ser nombres o apellidos
    candidatos = [p for p in palabras_raw if len(p) > 2 and p not in STOPWORDS]
    
    if not candidatos:
        return None, None

    # Si NO tiene intención explícita de tutoría y sólo hay 1 palabra candidata común,
    # no interceptar para permitir que las preguntas generales pasen al Corpus / RAG.
    if not tiene_intencion_tutor and len(candidatos) < 2:
        return None, None

    # 2. Probar si la consulta coincide con un docente (ej. "tutorados de acurio")
    for palabra in candidatos:
        tutorados = buscar_tutorados_por_docente(tutores, palabra)
        if tutorados:
            docente_completo = buscar_docente_por_nombre(tutores, palabra)
            if not docente_completo:
                docente_completo = palabra.upper()
            
            respuesta = f"👨‍🏫 Los tutorados del docente **{docente_completo}** son ({len(tutorados)} estudiantes):\n\n"
            for t in tutorados[:15]:  # Limitar a los primeros 15 si son muchos
                respuesta += f"- {t['nombre']} (código {t['codigo']})\n"
            if len(tutorados) > 15:
                respuesta += f"\n*... y {len(tutorados) - 15} estudiantes más.*"
            return respuesta, "Datos de tutores 📋"

    # 3. Probar si la consulta coincide con un estudiante
    resultados_totales = []
    for palabra in candidatos:
        res = buscar_tutor_por_nombre(tutores, palabra)
        if res:
            for item in res:
                if item not in resultados_totales:
                    resultados_totales.append(item)
    
    if resultados_totales:
        if len(resultados_totales) == 1:
            tutor, nombre, codigo = resultados_totales[0]
            return f"📋 El tutor del estudiante **{nombre}** (código {codigo}) es: **{tutor}**", "Datos de tutores 📋"
        elif len(resultados_totales) <= 10:
            respuesta = "🔍 Encontré los siguientes resultados:\n\n"
            for tutor, nombre, codigo in resultados_totales:
                respuesta += f"- **{nombre}** (código {codigo}) → Tutor: **{tutor}**\n"
            return respuesta, "Datos de tutores 📋"
        else:
            # Si hay demasiados resultados (ej. palabra muy común), pedir ser más específico
            respuesta = f"🔍 Encontré {len(resultados_totales)} coincidencias. Por favor, especifica el nombre completo o el código de 6 dígitos del estudiante."
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
        
        print("\n🔍 Buscando código 164246:")
        tutor, nombre = buscar_tutor_por_codigo(tutores, "164246")
        if tutor:
            print(f"   ✅ {nombre} → Tutor: {tutor}")
        else:
            print("   ❌ No encontrado")
    else:
        print("❌ No se pudieron cargar los datos.")
