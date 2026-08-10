# cargar_cursos.py
import csv
import streamlit as st
import pandas as pd
import re

@st.cache_data
def cargar_cursos():
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
    semestre = str(semestre).strip()
    resultados = []
    for curso in cursos:
        if curso['semestre'] == semestre:
            resultados.append(curso)
    return resultados

def buscar_curso_por_codigo(cursos, codigo):
    codigo = codigo.strip().upper()
    resultados = []
    for curso in cursos:
        if curso['codigo'] == codigo or codigo in curso['codigo']:
            resultados.append(curso)
    return resultados

def buscar_curso_por_nombre(cursos, nombre):
    """Busca un curso por su nombre priorizando números romanos"""
    nombre = nombre.lower().strip()
    resultados_exactos = []
    resultados_parciales = []
    
    palabras = nombre.split()
    numero_romano = None
    nombre_sin_numero = nombre
    
    if len(palabras) >= 2:
        posibles_romanos = ['i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x']
        ultima = palabras[-1]
        if ultima in posibles_romanos:
            numero_romano = ultima
            nombre_sin_numero = ' '.join(palabras[:-1])
    
    for curso in cursos:
        nombre_curso_lower = curso['nombre_curso'].lower()
        
        if nombre_curso_lower == nombre:
            resultados_exactos.insert(0, curso)
            continue
        
        if numero_romano:
            if nombre_curso_lower.endswith(f" {numero_romano}"):
                nombre_curso_sin_numero = ' '.join(nombre_curso_lower.split()[:-1])
                if nombre_sin_numero in nombre_curso_sin_numero:
                    resultados_exactos.append(curso)
                    continue
                else:
                    resultados_parciales.append(curso)
                    continue
        
        if nombre in nombre_curso_lower:
            if nombre_curso_lower.startswith(nombre) or f" {nombre}" in nombre_curso_lower:
                resultados_exactos.append(curso)
            else:
                resultados_parciales.append(curso)
    
    return resultados_exactos + resultados_parciales

def buscar_cursos_por_docente(cursos, docente):
    docente = docente.lower().strip()
    resultados = []
    for curso in cursos:
        if docente in curso['docente'].lower():
            resultados.append(curso)
    return resultados

def buscar_cursos_por_aula(cursos, aula):
    aula = aula.strip().upper()
    resultados = []
    for curso in cursos:
        if aula in curso['aula'].upper():
            resultados.append(curso)
    return resultados

def buscar_cursos_por_dia(cursos, dia):
    dia = dia.strip().upper()
    resultados = []
    for curso in cursos:
        if dia in curso['dia'].upper():
            resultados.append(curso)
    return resultados

def formatear_horario_curso(curso):
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

def obtener_arbol_requisitos(cursos, codigo, nivel=0, max_nivel=5):
    """Obtiene el árbol de requisitos de un curso de forma recursiva"""
    if nivel > max_nivel:
        return []
    
    curso = None
    for c in cursos:
        if c['codigo'] == codigo:
            curso = c
            break
    
    if not curso:
        return []
    
    req = curso['requisito']
    if not req or req == "-" or req == "—":
        return [(curso['codigo'], curso['nombre_curso'], "Sin requisitos")]
    
    req_curso = None
    for c in cursos:
        if c['codigo'] == req:
            req_curso = c
            break
    
    if req_curso:
        sub_requisitos = obtener_arbol_requisitos(cursos, req, nivel + 1, max_nivel)
        return [(curso['codigo'], curso['nombre_curso'], req_curso['nombre_curso'])] + sub_requisitos
    else:
        return [(curso['codigo'], curso['nombre_curso'], req)]

def responder_pregunta_cursos(cursos, pregunta):
    pregunta_lower = pregunta.lower().strip()
    import re
    
    # --- 0. PREGUNTAS SOBRE CANTIDAD ---
    if "cuantos" in pregunta_lower or "cantidad" in pregunta_lower or "cuántos" in pregunta_lower:
        palabras = pregunta_lower.split()
        for palabra in palabras:
            if len(palabra) > 3 and palabra not in ["cuantos", "cuántos", "cursos", "hay", "de", "el", "la"]:
                resultados = buscar_curso_por_nombre(cursos, palabra)
                if resultados:
                    cursos_vistos = set()
                    cursos_unicos = []
                    for curso in resultados:
                        if curso['nombre_curso'] not in cursos_vistos:
                            cursos_vistos.add(curso['nombre_curso'])
                            cursos_unicos.append(curso)
                    
                    if cursos_unicos:
                        texto = f"📚 **Cursos encontrados con '{palabra.upper()}':**\n\n"
                        for curso in cursos_unicos:
                            texto += f"- **{curso['codigo']}** - {curso['nombre_curso']}\n"
                        texto += f"\n📊 **Total: {len(cursos_unicos)} cursos**"
                        return texto, "Datos de cursos 📚"
    
    # --- 1. REQUISITOS ---
    if "requisito" in pregunta_lower or "requisitos" in pregunta_lower or "necesito" in pregunta_lower:
        palabras = pregunta_lower.split()
        
        # Buscar el curso
        curso_encontrado = None
        for i in range(len(palabras) - 1):
            if len(palabras[i]) > 2 and len(palabras[i+1]) > 1:
                frase = f"{palabras[i]} {palabras[i+1]}"
                if i + 2 < len(palabras) and len(palabras[i+2]) > 1:
                    frase_3 = f"{palabras[i]} {palabras[i+1]} {palabras[i+2]}"
                    resultados = buscar_curso_por_nombre(cursos, frase_3)
                    if resultados:
                        curso_encontrado = resultados[0]
                        break
                
                if not curso_encontrado:
                    resultados = buscar_curso_por_nombre(cursos, frase)
                    if resultados:
                        curso_encontrado = resultados[0]
                        break
        
        if not curso_encontrado:
            for palabra in palabras:
                if len(palabra) > 3 and palabra not in ["requisito", "requisitos", "para", "curso", "de", "necesito", "tener", "llevar"]:
                    resultados = buscar_curso_por_nombre(cursos, palabra)
                    if resultados:
                        curso_encontrado = resultados[0]
                        break
        
        if curso_encontrado:
            codigo = curso_encontrado['codigo']
            nombre_curso = curso_encontrado['nombre_curso']
            
            arbol = obtener_arbol_requisitos(cursos, codigo)
            
            if arbol and len(arbol) > 1:
                respuesta = f"📚 **Árbol de requisitos para {nombre_curso}**\n\n"
                for i, (cod, nom, req_nom) in enumerate(arbol):
                    if i == 0:
                        respuesta += f"📌 **{cod} - {nom}**\n"
                        respuesta += f"   └─ Requiere: **{req_nom}**\n"
                    else:
                        respuesta += f"      └─ Requiere: **{req_nom}**\n"
                return respuesta, "Datos de cursos 📚"
            elif arbol:
                req_nom = arbol[0][2]
                if req_nom == "Sin requisitos":
                    return f"📚 **{nombre_curso}** no tiene requisitos previos.", "Datos de cursos 📚"
                else:
                    return f"📚 **Requisitos para {nombre_curso}**\n\n➡️ **{req_nom}**", "Datos de cursos 📚"
        
        return "❌ No encontré información sobre ese curso.", "Datos de cursos 📚"
    
    # --- 2. CÓDIGO ---
    codigo_match = re.search(r'\b([A-Z]{2,4}\d{2,4}[A-Z]{0,3})\b', pregunta.upper())
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
    
    # --- 3. SEMESTRE ---
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
    
    # --- 4. NOMBRE ---
    for palabra in pregunta_lower.split():
        if len(palabra) > 3 and palabra not in ["cursos", "curso", "buscar", "nombre", "código", "codigo", "semestre"]:
            resultados = buscar_curso_por_nombre(cursos, palabra)
            if resultados:
                if len(resultados) <= 5:
                    return formatear_lista_cursos(resultados), f"Datos de cursos 📚 ({palabra.upper()})"
                else:
                    return formatear_lista_cursos(resultados[:5]) + f"\n\n*... y {len(resultados)-5} cursos más.*", f"Datos de cursos 📚"
    
    # --- 5. DOCENTE ---
    if "docente" in pregunta_lower or "profesor" in pregunta_lower:
        palabras = pregunta_lower.split()
        for palabra in palabras:
            if len(palabra) > 3 and palabra not in ["docente", "profesor", "cursos", "enseña", "buscar"]:
                resultados = buscar_cursos_por_docente(cursos, palabra)
                if resultados:
                    return formatear_lista_cursos(resultados), f"Datos de cursos 📚 (Docente: {palabra.upper()})"
    
    # --- 6. AULA ---
    if "aula" in pregunta_lower:
        palabras = pregunta_lower.split()
        for palabra in palabras:
            if len(palabra) > 2 and palabra not in ["aula", "aulas", "en", "el", "la"]:
                resultados = buscar_cursos_por_aula(cursos, palabra)
                if resultados:
                    return formatear_lista_cursos(resultados), f"Datos de cursos 📚 (Aula: {palabra.upper()})"
    
    return None, None
