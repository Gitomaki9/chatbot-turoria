# cargar_cursos.py
import csv
import streamlit as st
import pandas as pd

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
    """Busca un curso por su nombre (búsqueda parcial)"""
    nombre = nombre.lower().strip()
    resultados = []
    for curso in cursos:
        if nombre in curso['nombre_curso'].lower():
            resultados.append(curso)
    return resultados

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
    Retorna: (respuesta, fuente)
    """
    pregunta_lower = pregunta.lower().strip()
    import re
    
    # 1. Buscar por código de curso (ej. MEG01AIN)
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
            return f"❌ No encontré el curso con código **{codigo}**. Verifica que el código sea correcto.", "Datos de cursos 📚"
    
    # 2. Buscar por semestre
    semestre_match = re.search(r'semestre\s*(\d+)', pregunta_lower)
    if semestre_match:
        semestre = semestre_match.group(1)
        resultados = buscar_cursos_por_semestre(cursos, semestre)
        if resultados:
            # Obtener nombres únicos de cursos
            cursos_vistos = set()
            cursos_unicos = []
            for curso in resultados:
                if curso['nombre_curso'] not in cursos_vistos:
                    cursos_vistos.add(curso['nombre_curso'])
                    cursos_unicos.append(curso)
            return formatear_lista_cursos(cursos_unicos), f"Datos de cursos 📚 (Semestre {semestre})"
        else:
            return f"❌ No encontré cursos para el semestre **{semestre}**.", "Datos de cursos 📚"
    
    # 3. Buscar por docente
    if "docente" in pregunta_lower or "profesor" in pregunta_lower:
        palabras = pregunta_lower.split()
        for palabra in palabras:
            if len(palabra) > 3 and palabra not in ["docente", "profesor", "cursos", "enseña", "buscar"]:
                resultados = buscar_cursos_por_docente(cursos, palabra)
                if resultados:
                    return formatear_lista_cursos(resultados), f"Datos de cursos 📚 (Docente: {palabra.upper()})"
    
    # 4. Buscar por aula
    if "aula" in pregunta_lower:
        palabras = pregunta_lower.split()
        for palabra in palabras:
            if len(palabra) > 2 and palabra not in ["aula", "aulas", "en", "el", "la"]:
                resultados = buscar_cursos_por_aula(cursos, palabra)
                if resultados:
                    return formatear_lista_cursos(resultados), f"Datos de cursos 📚 (Aula: {palabra.upper()})"
    
    return None, None