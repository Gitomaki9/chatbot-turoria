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
        if curso['codigo'] == codigo:
            resultados.append(curso)
    return resultados

def normalizar_numero_romano(texto):
    romanos = ['i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x']
    numeros = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']
    
    partes = texto.lower().split()
    if len(partes) >= 2:
        ultima = partes[-1]
        if ultima in numeros:
            idx = numeros.index(ultima)
            if idx < len(romanos):
                partes[-1] = romanos[idx]
                return ' '.join(partes)
    return texto

def buscar_curso_por_nombre(cursos, nombre):
    """
    Busca cursos por nombre priorizando números romanos específicos.
    """
    nombre = nombre.lower().strip()
    resultados = []
    
    partes = nombre.split()
    numero_busqueda = None
    nombre_sin_numero = nombre
    
    romanos = ['i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x']
    if len(partes) >= 2:
        ultima = partes[-1]
        if ultima in romanos:
            numero_busqueda = ultima
            nombre_sin_numero = ' '.join(partes[:-1])
    
    # 1. Coincidencia exacta
    for curso in cursos:
        if curso['nombre_curso'].lower() == nombre:
            resultados.append(curso)
    
    # 2. Coincidencia con número romano específico
    if numero_busqueda:
        for curso in cursos:
            nombre_curso_lower = curso['nombre_curso'].lower()
            if nombre_curso_lower.endswith(f" {numero_busqueda}"):
                nombre_curso_sin_numero = ' '.join(nombre_curso_lower.split()[:-1])
                if nombre_sin_numero in nombre_curso_sin_numero or nombre_curso_sin_numero in nombre_sin_numero:
                    if curso not in resultados:
                        resultados.insert(0, curso)
    
    # 3. Coincidencia que comienza con el nombre
    for curso in cursos:
        if curso['nombre_curso'].lower().startswith(nombre) and curso not in resultados:
            resultados.append(curso)
    
    # 4. Coincidencia parcial
    for curso in cursos:
        if nombre in curso['nombre_curso'].lower() and curso not in resultados:
            resultados.append(curso)
    
    # 5. Priorizar el número romano exacto
    if numero_busqueda and len(resultados) > 1:
        def prioridad(curso):
            nombre_curso = curso['nombre_curso'].lower()
            if nombre_curso.endswith(f" {numero_busqueda}"):
                return 0
            for rom in romanos:
                if nombre_curso.endswith(f" {rom}"):
                    return 1
            return 2
        
        resultados.sort(key=prioridad)
    
    return resultados

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
    
    cursos_vistos = set()
    cursos_unicos = []
    for curso in cursos:
        if curso['nombre_curso'] not in cursos_vistos:
            cursos_vistos.add(curso['nombre_curso'])
            cursos_unicos.append(curso)
    
    if len(cursos_unicos) > limite:
        texto = f"🔍 Mostrando {limite} de {len(cursos_unicos)} resultados:\n\n"
        for curso in cursos_unicos[:limite]:
            texto += f"- **{curso['codigo']}** - {curso['nombre_curso']} - {curso['docente']}\n"
        texto += f"\n*... y {len(cursos_unicos) - limite} más.*"
        return texto
    else:
        texto = ""
        for curso in cursos_unicos:
            texto += f"- **{curso['codigo']}** - {curso['nombre_curso']} - {curso['docente']}\n"
        return texto

def obtener_arbol_requisitos(cursos, codigo, nivel=0, max_nivel=5):
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
        return [(curso['codigo'], curso['nombre_curso'], None)]
    
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

def obtener_nombre_completo_requisito(cursos, codigo):
    for c in cursos:
        if c['codigo'] == codigo:
            return f"{codigo} - {c['nombre_curso']}"
    return codigo

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
                        cursos_unicos.sort(key=lambda x: x['nombre_curso'])
                        for curso in cursos_unicos:
                            texto += f"- **{curso['codigo']}** - {curso['nombre_curso']}\n"
                        texto += f"\n📊 **Total: {len(cursos_unicos)} cursos**"
                        return texto, "Datos de cursos 📚"
        
        return "❌ No encontré cursos con esa palabra.", "Datos de cursos 📚"
    
    # --- 1. REQUISITOS ---
    if "requisito" in pregunta_lower or "requisitos" in pregunta_lower or "necesito" in pregunta_lower:
        pregunta_normalizada = normalizar_numero_romano(pregunta_lower)
        palabras = pregunta_normalizada.split()
        curso_encontrado = None
        
        romanos = ['i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x']
        numero_pregunta = None
        nombre_pregunta = pregunta_normalizada
        
        if len(palabras) >= 2:
            ultima = palabras[-1]
            if ultima in romanos:
                numero_pregunta = ultima
                nombre_pregunta = ' '.join(palabras[:-1])
        
        if numero_pregunta:
            nombre_completo = f"{nombre_pregunta} {numero_pregunta}"
            resultados = buscar_curso_por_nombre(cursos, nombre_completo)
            if resultados:
                for c in resultados:
                    if c['nombre_curso'].lower().endswith(f" {numero_pregunta}"):
                        curso_encontrado = c
                        break
                if not curso_encontrado:
                    curso_encontrado = resultados[0]
        
        if not curso_encontrado:
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
            
            if not arbol:
                return f"📚 **{nombre_curso}** no tiene requisitos previos.", "Datos de cursos 📚"
            
            respuesta = f"📚 **Árbol de requisitos para {nombre_curso}**\n\n"
            for i, (cod, nom, req_nom) in enumerate(arbol):
                if i == 0:
                    respuesta += f"📌 **{cod} - {nom}**\n"
                    if req_nom:
                        respuesta += f"   └─ Requiere: **{req_nom}**\n"
                    else:
                        respuesta += f"   └─ **Sin requisitos previos**\n"
                else:
                    if req_nom:
                        respuesta += f"      └─ Requiere: **{req_nom}**\n"
                    else:
                        respuesta += f"      └─ **Sin requisitos previos**\n"
            
            return respuesta, "Datos de cursos 📚"
        
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
    if "semestre" in pregunta_lower or "ciclo" in pregunta_lower:
        numeros = re.findall(r'\b([1-9]|10)\b', pregunta_lower)
        if numeros:
            semestre = numeros[0]
            resultados = buscar_cursos_por_semestre(cursos, semestre)
            if resultados:
                return formatear_lista_cursos(resultados), f"Datos de cursos 📚 (Semestre {semestre})"
            else:
                return f"❌ No encontré cursos para el semestre **{semestre}**.", "Datos de cursos 📚"
        
        palabras_semestre = {
            "primero": "1", "segundo": "2", "tercero": "3", "cuarto": "4",
            "quinto": "5", "sexto": "6", "séptimo": "7", "octavo": "8",
            "noveno": "9", "décimo": "10"
        }
        for palabra, num in palabras_semestre.items():
            if palabra in pregunta_lower:
                resultados = buscar_cursos_por_semestre(cursos, num)
                if resultados:
                    return formatear_lista_cursos(resultados), f"Datos de cursos 📚 (Semestre {num})"
                else:
                    return f"❌ No encontré cursos para el semestre **{num}**.", "Datos de cursos 📚"
    
    # --- 4. NOMBRE ---
    for palabra in pregunta_lower.split():
        if len(palabra) > 3 and palabra not in ["cursos", "curso", "buscar", "nombre", "código", "codigo", "semestre"]:
            resultados = buscar_curso_por_nombre(cursos, palabra)
            if resultados:
                return formatear_lista_cursos(resultados), f"Datos de cursos 📚 ({palabra.upper()})"
    
    # --- 5. PROFESOR ---
    if "profesor" in pregunta_lower or "docente" in pregunta_lower:
        palabras = pregunta_lower.split()
        
        curso_buscado = None
        for i in range(len(palabras) - 1):
            if len(palabras[i]) > 2 and len(palabras[i+1]) > 1:
                frase = f"{palabras[i]} {palabras[i+1]}"
                resultados = buscar_curso_por_nombre(cursos, frase)
                if resultados:
                    curso_buscado = resultados[0]
                    break
        
        if curso_buscado:
            return formatear_horario_curso(curso_buscado), f"Datos de cursos 📚 (Profesor: {curso_buscado['docente']})"
        
        for palabra in palabras:
            if len(palabra) > 3 and palabra not in ["profesor", "docente", "cursos", "enseña", "buscar"]:
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
