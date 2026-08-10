# cargar_cursos.py
import csv
import streamlit as st
import pandas as pd
import re

@st.cache_data
def cargar_cursos():
    """Carga todos los cursos desde el archivo CSV completo"""
    cursos = []
    try:
        with open("cursos_completo.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cursos.append(row)
        return cursos
    except FileNotFoundError:
        st.error("❌ Archivo 'cursos_completo.csv' no encontrado.")
        return []
    except Exception as e:
        st.error(f"❌ Error al cargar cursos: {e}")
        return []

def buscar_cursos_por_semestre(cursos, semestre):
    """Busca cursos por número de semestre"""
    semestre = str(semestre).strip()
    resultados = []
    for curso in cursos:
        if curso['semestre'] == semestre:
            resultados.append(curso)
    return resultados

def buscar_curso_por_codigo(cursos, codigo):
    """Busca un curso por su código"""
    codigo = codigo.strip().upper()
    resultados = []
    for curso in cursos:
        if curso['codigo'] == codigo:
            resultados.append(curso)
    return resultados

def buscar_curso_por_nombre(cursos, nombre):
    """
    Busca un curso por su nombre (búsqueda parcial con prioridad)
    Prioriza coincidencias exactas sobre coincidencias parciales
    """
    nombre = nombre.lower().strip()
    resultados_exactos = []
    resultados_parciales = []
    
    for curso in cursos:
        nombre_curso_lower = curso['nombre_curso'].lower()
        
        # 1. Coincidencia exacta (prioridad máxima)
        if nombre_curso_lower == nombre:
            resultados_exactos.insert(0, curso)  # Poner al inicio
        
        # 2. Coincidencia con número romano (ej: "calculo ii" -> "CÁLCULO II")
        elif nombre in nombre_curso_lower:
            # Dividir la búsqueda para priorizar el número romano
            partes = nombre.split()
            if len(partes) >= 2:
                # Si la búsqueda tiene número romano (ej: "calculo ii")
                # Dar prioridad a cursos que terminen con ese número
                numero = partes[-1]  # "ii"
                if nombre_curso_lower.endswith(numero):
                    resultados_exactos.append(curso)
                else:
                    resultados_parciales.append(curso)
            else:
                # Búsqueda simple de una palabra
                if nombre_curso_lower.startswith(nombre) or f" {nombre}" in nombre_curso_lower:
                    resultados_exactos.append(curso)
                else:
                    resultados_parciales.append(curso)
    
    # Devolver primero los resultados exactos, luego los parciales
    return resultados_exactos + resultados_parciales

def buscar_cursos_por_docente(cursos, docente):
    """Busca cursos por nombre de docente (búsqueda parcial)"""
    docente = docente.lower().strip()
    resultados = []
    for curso in cursos:
        if docente in curso['docente'].lower():
            resultados.append(curso)
    return resultados

def buscar_cursos_por_aula(cursos, aula):
    """Busca cursos por aula (búsqueda parcial)"""
    aula = aula.strip().upper()
    resultados = []
    for curso in cursos:
        if aula in curso['aula'].upper():
            resultados.append(curso)
    return resultados

def buscar_cursos_por_dia(cursos, dia):
    """Busca cursos por día de la semana"""
    dia = dia.strip().upper()
    resultados = []
    for curso in cursos:
        if dia in curso['dia'].upper():
            resultados.append(curso)
    return resultados

def formatear_horario_curso(curso):
    """Formatea la información de un curso para mostrarla"""
    return f"""
**{curso['codigo']} - {curso['nombre_curso']}**
- Créditos: {curso['creditos']}
- Categoría: {curso['categoria']}
- Requisito: {curso['requisito']}
- Docente: {curso['docente']}
- Día: {curso['dia']}
- Horario: {curso['horario']}
- Tipo: {curso['tipo']}
- Aula: {curso['aula']}
- Horas: {curso['horas']}
"""

def formatear_lista_cursos(cursos, limite=10):
    """Formatea una lista de cursos para mostrarla"""
    if not cursos:
        return "No se encontraron cursos."
    
    if len(cursos) > limite:
        texto = f"🔍 Mostrando {limite} de {len(cursos)} resultados:\n\n"
        for curso in cursos[:limite]:
            texto += f"- **{curso['codigo']}** - {curso['nombre_curso']} - {curso['docente']}\n"
        texto += f"\n*... y {len(cursos) - limite} más.*"
        return texto
    else:
        texto = ""
        for curso in cursos:
            texto += f"- **{curso['codigo']}** - {curso['nombre_curso']} - {curso['docente']}\n"
        return texto

def responder_pregunta_cursos(cursos, pregunta):
    """
    Función principal para procesar preguntas sobre cursos.
    Retorna: (respuesta, fuente) o (None, None)
    """
    pregunta_lower = pregunta.lower().strip()
    import re
    
    # --- 1. DETECTAR PREGUNTAS SOBRE REQUISITOS ---
    if "requisito" in pregunta_lower or "requisitos" in pregunta_lower or "necesito" in pregunta_lower:
        # Extraer posibles nombres de curso
        palabras = pregunta_lower.split()
        
        # Buscar frases como "computacion grafica" (dos palabras juntas)
        # Primero intentar con frases de 2 palabras
        for i in range(len(palabras) - 1):
            if len(palabras[i]) > 2 and len(palabras[i+1]) > 2:
                frase = f"{palabras[i]} {palabras[i+1]}"
                resultados = buscar_curso_por_nombre(cursos, frase)
                if resultados:
                    # Buscar el curso que coincida mejor
                    for curso in resultados:
                        # Priorizar cursos que contengan exactamente la frase
                        if frase in curso['nombre_curso'].lower():
                            req = curso['requisito']
                            if req and req != "-" and req != "—":
                                req_cursos = buscar_curso_por_codigo(cursos, req)
                                if req_cursos:
                                    # ✅ MEJORA: Mostrar nombre completo del curso requisito
                                    req_nombre = f"{req} - {req_cursos[0]['nombre_curso']}"
                                    return f"📚 **Requisitos para {curso['nombre_curso']}**\n\n➡️ **{req_nombre}**", "Datos de cursos 📚"
                                else:
                                    return f"📚 **Requisitos para {curso['nombre_curso']}**\n\n➡️ **{req}**", "Datos de cursos 📚"
                            else:
                                return f"📚 **{curso['nombre_curso']}** no tiene requisitos previos.", "Datos de cursos 📚"
        
        # Si no encontró con frases, buscar palabra por palabra
        for palabra in palabras:
            if len(palabra) > 3 and palabra not in ["requisito", "requisitos", "para", "curso", "de", "necesito", "tener", "llevar"]:
                resultados = buscar_curso_por_nombre(cursos, palabra)
                if resultados:
                    # Buscar el curso que coincida mejor (priorizar el más largo)
                    mejor_curso = max(resultados, key=lambda x: len(x['nombre_curso']))
                    req = mejor_curso['requisito']
                    if req and req != "-" and req != "—":
                        req_cursos = buscar_curso_por_codigo(cursos, req)
                        if req_cursos:
                            # ✅ MEJORA: Mostrar nombre completo del curso requisito
                            req_nombre = f"{req} - {req_cursos[0]['nombre_curso']}"
                            return f"📚 **Requisitos para {mejor_curso['nombre_curso']}**\n\n➡️ **{req_nombre}**", "Datos de cursos 📚"
                        else:
                            return f"📚 **Requisitos para {mejor_curso['nombre_curso']}**\n\n➡️ **{req}**", "Datos de cursos 📚"
                    else:
                        return f"📚 **{mejor_curso['nombre_curso']}** no tiene requisitos previos.", "Datos de cursos 📚"
        
        return "❌ No encontré información sobre ese curso. Por favor, especifica el nombre completo del curso (ej: Computación Gráfica II).", "Datos de cursos 📚"
    
    # --- 2. BUSCAR POR CÓDIGO DE CURSO ---
    codigo_match = re.search(r'\b([A-Z]{2,4}\d{2,3}[A-Z]{1,3})\b', pregunta.upper())
    if codigo_match:
        codigo = codigo_match.group(1)
        resultados = buscar_curso_por_codigo(cursos, codigo)
        if resultados:
            if len(resultados) == 1:
                return formatear_horario_curso(resultados[0]), "Datos de cursos 📚"
            else:
                return formatear_lista_cursos(resultados), "Datos de cursos 📚"
        else:
            return f"❌ No encontré el curso con código **{codigo}**.", "Datos de cursos 📚"
    
    # --- 3. BUSCAR POR SEMESTRE ---
    semestre_match = re.search(r'semestre\s*(\d+)', pregunta_lower)
    if semestre_match:
        semestre = semestre_match.group(1)
        resultados = buscar_cursos_por_semestre(cursos, semestre)
        if resultados:
            cursos_vistos = set()
            cursos_unicos = []
            for curso in resultados:
                if curso['nombre_curso'] not in cursos_vistos:
                    cursos_vistos.add(curso['nombre_curso'])
                    cursos_unicos.append(curso)
            return formatear_lista_cursos(cursos_unicos), f"Datos de cursos 📚 (Semestre {semestre})"
        else:
            return f"❌ No encontré cursos para el semestre **{semestre}**.", "Datos de cursos 📚"
    
    # --- 4. BUSCAR POR NOMBRE DE CURSO (BÚSQUEDA FLEXIBLE) ---
    for palabra in pregunta_lower.split():
        if len(palabra) > 3 and palabra not in ["cursos", "curso", "buscar", "nombre", "código", "codigo", "semestre"]:
            resultados = buscar_curso_por_nombre(cursos, palabra)
            if resultados:
                if len(resultados) <= 5:
                    return formatear_lista_cursos(resultados), f"Datos de cursos 📚 ({palabra.upper()})"
                else:
                    return formatear_lista_cursos(resultados[:5]) + f"\n\n*... y {len(resultados)-5} cursos más.*", f"Datos de cursos 📚"
    
    # --- 5. BUSCAR POR DOCENTE ---
    if "docente" in pregunta_lower or "profesor" in pregunta_lower:
        palabras = pregunta_lower.split()
        for palabra in palabras:
            if len(palabra) > 3 and palabra not in ["docente", "profesor", "cursos", "enseña", "buscar"]:
                resultados = buscar_cursos_por_docente(cursos, palabra)
                if resultados:
                    return formatear_lista_cursos(resultados), f"Datos de cursos 📚 (Docente: {palabra.upper()})"
    
    # --- 6. BUSCAR POR AULA ---
    if "aula" in pregunta_lower:
        palabras = pregunta_lower.split()
        for palabra in palabras:
            if len(palabra) > 2 and palabra not in ["aula", "aulas", "en", "el", "la"]:
                resultados = buscar_cursos_por_aula(cursos, palabra)
                if resultados:
                    return formatear_lista_cursos(resultados), f"Datos de cursos 📚 (Aula: {palabra.upper()})"
    
    return None, None
