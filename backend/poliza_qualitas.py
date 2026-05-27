import fitz  # PyMuPDF
import re
import unicodedata
from collections import Counter


def leer_pdf_completo(ruta_pdf):
    texto = ""
    paginas_dict = []
    with fitz.open(ruta_pdf) as doc:
        for pagina in doc:
            texto += pagina.get_text()
            paginas_dict.append(pagina.get_text("dict"))
    return texto, paginas_dict


def es_poliza_auto_qualitas(texto: str) -> bool:
    texto_upper = texto.upper()
    otras_aseguradoras = [
        "GNP", "AXA", "MAPFRE", "CHUBB", "ZURICH", "ANA SEGUROS", "HDI", "AFIRME", "BANORTE", "BBVA SEGUROS"
    ]
    palabras_clave_auto = ["VEHÍCULO", "COBERTURA", "AUTOMÓVIL", "USO PARTICULAR", "PLACAS"]

    if "QUALITAS" not in texto_upper:
        if any(aseg in texto_upper for aseg in otras_aseguradoras):
            return False
        return False

    if any(p in texto_upper for p in palabras_clave_auto):
        return True
    return False


def extraer_tipo_poliza(texto: str) -> str:
    texto_upper = texto.upper()
    tipos_validos = ["AMPLIA", "LIMITADA", "BÁSICA", "RESPONSABILIDAD CIVIL"]
    contador = Counter()

    for linea in texto_upper.splitlines():
        match = re.search(r'PLAN:\s*(AMPLIA|LIMITADA|BÁSICA|RESPONSABILIDAD CIVIL)', linea)
        if match:
            contador[match.group(1)] += 1

    if contador:
        return contador.most_common(1)[0][0].title()

    for tipo in tipos_validos:
        contador[tipo] += texto_upper.count(tipo)

    if contador:
        return contador.most_common(1)[0][0].title()
    return ""


def extraer_numero_poliza_qualitas(texto):
    match = re.search(r'INCISO\s+(\d{7,15})', texto)
    if match:
        return match.group(1).strip()

    patrones = [
        r'P[oó]liza\s*(?:No\.|Núm\.?|Número)?\s*[:\-]?\s*([A-Z0-9\-]{6,20})',
        r'No\.?\s*de\s*P[oó]liza\s*[:\-]?\s*([A-Z0-9\-]{6,20})',
        r'N°\s*P[oó]liza\s*[:\-]?\s*([A-Z0-9\-]{6,20})'
    ]
    for patron in patrones:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def extraer_rfc_mas_repetido(texto: str) -> str:
    texto_upper = texto.upper()

    # RFC estándar + RFC con guiones tipo SLE-120202-M92
    rfc_regex = r'\b[A-Z&Ñ]{3,4}\d{6}[A-Z0-9]{0,3}\b'
    rfc_guiones_regex = r'\b[A-Z&Ñ]{2,4}-\d{6}-[A-Z0-9]{1,3}\b'

    rfcs_encontrados = re.findall(rfc_regex, texto_upper)
    rfcs_con_guiones = re.findall(rfc_guiones_regex, texto_upper)

    exclusiones_motor = [
        r'\bV[68]\b', r'\bI4\b', r'\bH6\b', r'\b2ZRFE\b', r'\b1\.6L\b',
        r'\b2\.0L\b', r'\bTSI\b', r'\bTDI\b', r'\bDOHC\b', r'\bSOHC\b',
        r'\bTURBO\b', r'\bHYBRID\b', r'\bELECTRIC\b'
    ]
    rfcs_filtrados = []
    for rfc in rfcs_encontrados:
        if not any(re.fullmatch(pat, rfc) for pat in exclusiones_motor):
            rfcs_filtrados.append(rfc)

    # Si encontró RFC con guiones, devolverlo directo (es único y específico)
    if rfcs_con_guiones:
        bloques_asegurado = re.findall(r'INFORMACION DEL ASEGURADO.*?(?:\n\n|\Z)', texto_upper, re.DOTALL)
        for rfc in rfcs_con_guiones:
            if any(rfc in bloque for bloque in bloques_asegurado):
                return rfc
        return rfcs_con_guiones[0]

    if not rfcs_filtrados:
        return "No se encontraron RFCs válidos"

    rfcs_estandar = [rfc for rfc in rfcs_filtrados if len(rfc) in (12, 13)]
    rfcs_truncados = [rfc for rfc in rfcs_filtrados if len(rfc) == 10]

    conteo_estandar = Counter(rfcs_estandar)
    conteo_truncado = Counter(rfcs_truncados)

    bloques_asegurado = re.findall(r'INFORMACION DEL ASEGURADO.*?(?:\n\n|\Z)', texto_upper, re.DOTALL)

    for rfc, _ in conteo_estandar.most_common():
        if any(rfc in bloque for bloque in bloques_asegurado):
            return rfc

    if conteo_estandar:
        return conteo_estandar.most_common(1)[0][0]

    if conteo_truncado:
        return conteo_truncado.most_common(1)[0][0]

    return "No se encontraron RFCs válidos"


def extraer_prima_neta(texto: str) -> str:
    texto_upper = texto.upper()
    lineas = texto_upper.splitlines()
    monto_regex = r'\$?\s?\d{1,3}(?:,\d{3})*(?:\.\d{2})?'

    for i, linea in enumerate(lineas):
        if 'PRIMA NETA' in linea:
            idx_valor = i + 8
            if idx_valor < len(lineas):
                montos = re.findall(monto_regex, lineas[idx_valor])
                if montos:
                    return montos[0].replace(' ', '')
            idx_siguiente = i + 1
            if idx_siguiente < len(lineas):
                montos = re.findall(monto_regex, lineas[idx_siguiente])
                if montos:
                    return montos[0].replace(' ', '')
            break
    return ""


def extraer_tasa_financiamiento(texto: str) -> str:
    texto_upper = texto.upper()
    lineas = texto_upper.splitlines()
    monto_regex = r'-?\d{1,3}(?:,\d{3})*(?:\.\d{2})?'

    for i, linea in enumerate(lineas):
        if "TASA FINANCIAMIENTO" in linea:
            idx_primario = i + 8
            if idx_primario < len(lineas):
                montos = re.findall(monto_regex, lineas[idx_primario])
                if montos:
                    return montos[0]
            idx_fallback = i + 1
            if idx_fallback < len(lineas):
                montos = re.findall(monto_regex, lineas[idx_fallback])
                if montos:
                    return montos[0]
    return ""


def extraer_gastos_expedicion(texto: str) -> str:
    texto_upper = texto.upper()
    lineas = texto_upper.splitlines()
    monto_regex = r'-?\d{1,3}(?:,\d{3})*\.\d{2}'
    claves_busqueda = ["GASTOS POR EXPEDICIÓN", "GASTOS DE EXPEDICIÓN"]

    for i, linea in enumerate(lineas):
        if any(clave in linea for clave in claves_busqueda):
            idx_primario = i + 8
            if idx_primario < len(lineas):
                montos = re.findall(monto_regex, lineas[idx_primario])
                if montos:
                    return montos[0]
            idx_fallback = i + 1
            if idx_fallback < len(lineas):
                montos = re.findall(monto_regex, lineas[idx_fallback])
                if montos:
                    return montos[0]
    return ""


def extraer_subtotal(texto: str) -> str:
    texto_upper = texto.upper()
    lineas = texto_upper.splitlines()
    monto_regex = r'-?\d{1,3}(?:,\d{3})*\.\d{2}'

    for i, linea in enumerate(lineas):
        if "SUBTOTAL" in linea:
            idx_primario = i + 8
            if idx_primario < len(lineas):
                montos = re.findall(monto_regex, lineas[idx_primario])
                if montos:
                    return montos[0]
            idx_fallback = i + 1
            if idx_fallback < len(lineas):
                montos = re.findall(monto_regex, lineas[idx_fallback])
                if montos:
                    return montos[0]
    return ""


def extraer_prima_total(texto: str) -> str:
    texto_upper = texto.upper()
    lineas = texto_upper.splitlines()
    monto_regex = r'-?\d{1,3}(?:,\d{3})*\.\d{2}'

    for i, linea in enumerate(lineas):
        if "IMPORTE TOTAL" in linea or "PRIMA TOTAL" in linea:
            idx_primario = i + 7
            if idx_primario < len(lineas):
                montos = re.findall(monto_regex, lineas[idx_primario])
                if montos:
                    return montos[0]

            montos_encontrados = []
            for j in range(i + 1, min(i + 36, len(lineas))):
                montos = re.findall(monto_regex, lineas[j])
                montos_encontrados.extend(montos)
            if montos_encontrados:
                return montos_encontrados[-1]
    return ""


def normalizar_texto(texto):
    texto = texto.upper()
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    return texto


def extraer_nombre_cliente(texto: str) -> str:
    texto_upper = texto.upper()
    lineas = texto_upper.splitlines()

    patrones_legales = [
        r'S\.?A\.?\s+DE\s+C\.?V\.?',
        r'S\.?\s+DE\s+R\.?L\.?',
        r'SOCIEDAD\s+ANONIMA',
        r'SOCIEDAD\s+DE\s+RESPONSABILIDAD\s+LIMITADA'
    ]
    palabras_excluidas = [
        "DOMICILIO", "RFC", "C.P", "MUNICIPIO", "ESTADO", "VIGENCIA",
        "TELEFONO", "DESDE LAS", "INFORMACIÓN IMPORTANTE", "OFICINA", "ATENCIÓN", "CANAL"
    ]

    for i, linea in enumerate(lineas):
        if "INFORMACION DEL ASEGURADO" in linea or "INFORMACIÓN DEL ASEGURADO" in linea:
            partes = re.split(r"INFORMACION DEL ASEGURADO|INFORMACIÓN DEL ASEGURADO", linea)
            if len(partes) > 1 and partes[1].strip():
                posible_nombre = partes[1].strip()
                if not any(p in posible_nombre for p in palabras_excluidas):
                    return posible_nombre.title()

            for j in range(i + 1, min(i + 6, len(lineas))):
                posible_nombre = lineas[j].strip()
                if not posible_nombre or any(p in posible_nombre for p in palabras_excluidas):
                    continue
                if any(re.search(pat, posible_nombre) for pat in patrones_legales):
                    return posible_nombre.title()
                if re.fullmatch(r"[A-ZÑÁÉÍÓÚ ,\.&]{5,}", posible_nombre) and len(posible_nombre.split()) >= 2:
                    return posible_nombre.title()
            break

    fechas = extraer_vigencia_por_frecuencia(texto)
    if isinstance(fechas, dict):
        ultima_fecha = fechas.get("Fin Vigencia", "")
        if ultima_fecha and ultima_fecha != "No encontrada":
            for i, linea in enumerate(lineas):
                if ultima_fecha in linea:
                    for j in range(i + 1, min(i + 3, len(lineas))):
                        posible_nombre = lineas[j].strip()
                        if not posible_nombre or any(p in posible_nombre for p in palabras_excluidas):
                            continue
                        if any(re.search(pat, posible_nombre) for pat in patrones_legales):
                            return posible_nombre.title()
                        if re.fullmatch(r"[A-ZÑÁÉÍÓÚ ,\.&0-9\-]{5,}", posible_nombre) and len(posible_nombre.split()) >= 2:
                            return posible_nombre.title()
                    break

    for i, linea in enumerate(lineas):
        if "FAX" in linea:
            idx_nombre = i + 7
            if idx_nombre < len(lineas):
                posible_nombre = lineas[idx_nombre].strip()
                if posible_nombre and not any(p in posible_nombre for p in palabras_excluidas):
                    return posible_nombre.title()
    return ""


def extraer_vigencia_por_frecuencia(texto: str) -> dict:
    texto_normalizado = normalizar_texto(texto)
    patrones_fecha = [
        r'\d{2}/\d{2}/\d{4}',
        r'\d{2}-\d{2}-\d{4}',
        r'\d{4}-\d{2}-\d{2}',
        r'\d{2} de [A-ZÁÉÍÓÚÑ]+ de \d{4}',
        r'(\d{2}/(ENE|FEB|MAR|ABR|MAY|JUN|JUL|AGO|SEP|OCT|NOV|DIC)/\d{2,4})'
    ]

    fechas_encontradas = []
    for patron in patrones_fecha:
        coincidencias = re.findall(patron, texto_normalizado, flags=re.IGNORECASE)
        if coincidencias and isinstance(coincidencias[0], tuple):
            fechas_encontradas.extend([c[0] for c in coincidencias])
        else:
            fechas_encontradas.extend(coincidencias)

    if not fechas_encontradas:
        return {"Inicio Vigencia": "", "Fin Vigencia": ""}

    contador = Counter(fechas_encontradas)
    fechas_ordenadas = [fecha for fecha, _ in contador.most_common()]

    return {
        "Inicio Vigencia": fechas_ordenadas[0] if len(fechas_ordenadas) > 0 else "",
        "Fin Vigencia": fechas_ordenadas[1] if len(fechas_ordenadas) > 1 else ""
    }


def extraer_iva(texto: str) -> str:
    texto_upper = texto.upper()
    lineas = texto_upper.splitlines()
    monto_regex = r'-?\d{1,3}(?:,\d{3})*\.\d{2}'
    porcentaje_regex = r'16\s*%'

    for i, linea in enumerate(lineas):
        if "I.V.A." in linea or "IVA" in linea:
            idx_primario = i + 7
            if idx_primario < len(lineas):
                montos = re.findall(monto_regex, lineas[idx_primario])
                if montos:
                    return montos[0]

    for i, linea in enumerate(lineas):
        if re.search(porcentaje_regex, linea):
            idx_fallback = i + 1
            if idx_fallback < len(lineas):
                montos = re.findall(monto_regex, lineas[idx_fallback])
                if montos:
                    return montos[0]
    return ""


def extraer_forma_pago(texto: str) -> str:
    texto_upper = texto.upper()
    lineas = texto_upper.splitlines()
    formas_validas = ["CONTADO", "SEMESTRAL", "TRIMESTRAL", "MENSUAL", "ANUAL"]

    for i, linea in enumerate(lineas):
        if "FORMA DE PAGO" in linea:
            idx_siguiente = i + 1
            if idx_siguiente < len(lineas):
                posible_forma = lineas[idx_siguiente].strip()
                if posible_forma in formas_validas:
                    return posible_forma.title()
            idx_fallback = i + 45
            if idx_fallback < len(lineas):
                posible_forma = lineas[idx_fallback].strip()
                if posible_forma in formas_validas:
                    return posible_forma.title()

    contador = Counter()
    for forma in formas_validas:
        contador[forma] += texto_upper.count(forma)
    if contador:
        return contador.most_common(1)[0][0].title()
    return ""


def extraer_moneda(texto: str) -> str:
    texto_upper = texto.upper()
    lineas = texto_upper.splitlines()
    monedas_validas = ["PESOS", "DÓLARES", "USD", "MXN", "EUROS", "EUR"]

    for i, linea in enumerate(lineas):
        if "MONEDA" in linea:
            idx_siguiente = i + 1
            if idx_siguiente < len(lineas):
                posible_moneda = lineas[idx_siguiente].strip()
                if posible_moneda in monedas_validas:
                    return posible_moneda.title()

    contador = Counter()
    for moneda in monedas_validas:
        contador[moneda] += texto_upper.count(moneda)
    if contador:
        return contador.most_common(1)[0][0].title()
    return ""


def extraer_motor(texto: str) -> str:
    texto_upper = texto.upper()
    lineas = texto_upper.splitlines()

    regex_motor = r'\b[A-Z0-9]{6,15}\b'

    frases_validas = [
        "HECHO EN",
        "FABRICADO EN",
        "ENSAMBLADO EN"
    ]

    palabras_descartadas = {
        "COLONIA", "ESTADO", "MUNICIPIO", "CIUDAD", "MEXICO",
        "NORMAL", "PARTICULAR", "VIGENCIA", "PLACAS",
        "MODELO", "COLOR", "SERIE", "MOTOR", "OCUPANTES",
        "SERVICIO", "MOVIMIENTO", "TRAMITE", "ALTA",
        "CONTADO", "SEMESTRAL", "TRIMESTRAL", "MENSUAL",
        "ANUAL", "IMPORTE", "SUBTOTAL", "MONEDA",
        "PESOS", "AMPLIA", "LIMITADA",
    }

    # -------------------------
    # LOGICA PRINCIPAL
    # -------------------------

    for i, linea in enumerate(lineas):
        if "MOTOR" in linea:
            for desplazamiento in [9, 10, 11]:
                idx = i + desplazamiento
                if idx < len(lineas):
                    valor = lineas[idx].strip()
                    if any(frase in valor for frase in frases_validas):
                        return valor.title()
                    tokens = re.findall(regex_motor, valor)
                    for token in tokens:
                        if token not in palabras_descartadas:
                            if re.search(r'\d', token):
                                return token
            break

    # -------------------------
    # FALLBACK NUEVO
    # -------------------------

    candidatos = []
    for i, linea in enumerate(lineas):
        if re.search(r'^MOTOR\s*[:\-]?\s*$', linea.strip(), re.IGNORECASE):
            ventana = lineas[i:i + 15]
            for valor in ventana:
                valor = valor.strip().upper()
                if not valor:
                    continue
                if valor in palabras_descartadas:
                    continue
                if any(frase in valor for frase in frases_validas):
                    candidatos.append(valor.title())
                    continue
                tokens = re.findall(regex_motor, valor)
                for token in tokens:
                    if (
                        token not in palabras_descartadas
                        and re.search(r'\d', token)
                        and re.search(r'[A-Z]', token)
                        and len(token) >= 8
                    ):
                        candidatos.append(token)
    if candidatos:
        return sorted(candidatos, key=len, reverse=True)[0]
    return ""


def extraer_serie(texto: str) -> str:
    texto_upper = texto.upper()
    lineas = texto_upper.splitlines()
    regex_serie = r'\b[A-Z0-9]{12,17}\b'

    for i, linea in enumerate(lineas):
        if "SERIE" in linea:
            posibles_inline = re.findall(regex_serie, linea)
            if posibles_inline:
                return posibles_inline[0]
            for desplazamiento in [9, 10, 11, 12]:
                idx = i + desplazamiento
                if idx < len(lineas):
                    valor = lineas[idx].strip()
                    posibles = re.findall(regex_serie, valor)
                    if posibles:
                        return posibles[0]
            break
    return "S/N"


def extraer_placas(texto, paginas_dict):
    if re.search(r'tr[áa]mite', texto, re.IGNORECASE):
        return "TRÁMITE"

    def validar_placa(placa):
        if not placa or len(placa) not in [6, 7]:
            return False
        placa = placa.upper()
        return any([
            re.fullmatch(r'^[A-Z]{2,3}\d{3,4}$', placa),
            re.fullmatch(r'^[A-Z]{4}\d{2,3}$', placa),
            re.fullmatch(r'^\d{2,3}[A-Z]{3,4}$', placa),
            re.fullmatch(r'^[A-Z]\d{2}[A-Z]{3}$', placa),
            re.fullmatch(r'^[A-Z]{2}\d{2}[A-Z]{2}$', placa),
            re.fullmatch(r'^[A-Z]{3}\d{3}[A-Z]$', placa),
            re.fullmatch(r'^\d{4}[A-Z]\d$', placa),
            re.fullmatch(r'^\d{2}[A-Z]\d{3}$', placa),   # 08G654
        ])

    def formatear_placa(placa):
        if not placa:
            return ""
        placa_upper = placa.strip().upper()
        if re.fullmatch(r'S/?N', placa_upper):
            return placa_upper          # SN o S/N → tal cual
        if re.fullmatch(r'TR[AÁ]MITE', placa_upper):
            return "TRÁMITE"
        if re.search(r'^HECHO\s+EN\s+', placa_upper):
            return placa_upper
        placa_clean = re.sub(r'[^A-Z0-9]', '', placa_upper)
        if len(placa_clean) == 6:
            return f"{placa_clean[:3]}-{placa_clean[3:]}"
        elif len(placa_clean) == 7:
            return f"{placa_clean[:3]}-{placa_clean[3:]}" if placa_clean[3].isdigit() else f"{placa_clean[:4]}-{placa_clean[4:]}"
        return placa_clean or placa.strip()

    def buscar_desde_patrones(texto):
        patrones = [
            r'INFORMACI[ÓO]N DEL ASEGURADO',
            r'DESCRIPCI[ÓO]N DEL VEH[ÍI]CULO ASEGURADO'
        ]
        lineas = texto.splitlines()
        for i, linea in enumerate(lineas):
            for patron in patrones:
                if re.search(patron, linea, re.IGNORECASE):
                    for j in range(0, 11):
                        if i + j < len(lineas):
                            posible = lineas[i + j].strip()
                            if validar_placa(posible):
                                return formatear_placa(posible)
        return None

    def buscar_en_rango_lineas(texto):
        lineas = texto.splitlines()
        for i, linea in enumerate(lineas):
            if 'placas:' in linea.lower() or 'placa:' in linea.lower():
                for j in range(0, 11):
                    if i + j < len(lineas):
                        posible = lineas[i + j].strip()
                        if re.fullmatch(r'S/?N', posible.upper()):
                            return "S/N"
                        if validar_placa(posible):
                            return formatear_placa(posible)
        return None

    def buscar_en_tabla():
        for pagina in paginas_dict:
            for bloque in pagina.get("blocks", []):
                for linea in bloque.get("lines", []):
                    texto_linea = ' '.join(span["text"] for span in linea.get("spans", []))
                    if "modelo" in texto_linea.lower() and "placas" in texto_linea.lower():
                        match = re.search(r'(?:Placas|Placa)\s*[:\-]?\s*([A-Z0-9]{5,8})\b', texto_linea, re.IGNORECASE)
                        if match and validar_placa(match.group(1)):
                            return formatear_placa(match.group(1))
                        idx = bloque["lines"].index(linea)
                        if idx + 1 < len(bloque["lines"]):
                            siguiente_linea = bloque["lines"][idx + 1]
                            texto_siguiente = ' '.join(span["text"] for span in siguiente_linea.get("spans", []))
                            texto_siguiente = texto_siguiente.strip()
                            if texto_siguiente == "":
                                return ""
                            if validar_placa(texto_siguiente):
                                return formatear_placa(texto_siguiente)
        return None

    placa = buscar_desde_patrones(texto)
    if placa:
        return placa
    placa = buscar_en_rango_lineas(texto)
    if placa:
        return placa
    placa = buscar_en_tabla()
    if placa is not None:
        return placa

    # Fallback: line after "Placas:"
    for linea in texto.splitlines():
        if 'placas:' in linea.lower() or 'placa:' in linea.lower():
            partes = linea.split(':', 1)
            if len(partes) > 1:
                posible = partes[1].strip().upper()
                if not posible or posible.lower() == "none":
                    return ""
                # SN o S/N → normalizar a S/N
                if re.fullmatch(r'S/?N', posible):
                    return "S/N"
                return posible
            break
    return ""  # ← vacío, no "No encontrado"


def extraer_cp(texto):
    conteo_cp = {}
    lineas = texto.splitlines()

    for i, linea in enumerate(lineas):
        if re.search(r'\bINCISO\b', linea, re.IGNORECASE):
            for j in range(7, 10):
                if i + j < len(lineas):
                    posible = lineas[i + j].strip()
                    if re.fullmatch(r'\d{4,5}', posible):
                        conteo_cp[posible] = conteo_cp.get(posible, 0) + 1

    bloques = re.split(r'INFORMACI[ÓO]N DEL ASEGURADO', texto, flags=re.IGNORECASE)
    for bloque in bloques[1:]:
        lineas_bloque = bloque.splitlines()
        for i, linea in enumerate(lineas_bloque):
            if re.search(r'\bC\.P\.:', linea, re.IGNORECASE):
                for j in range(7, 10):
                    if i + j < len(lineas_bloque):
                        posible = lineas_bloque[i + j].strip()
                        if re.fullmatch(r'\d{4,5}', posible):
                            conteo_cp[posible] = conteo_cp.get(posible, 0) + 1
                            break

    for i, linea in enumerate(lineas):
        if re.search(r'\bENDOSO\b', linea, re.IGNORECASE):
            if i + 10 < len(lineas):
                posible = lineas[i + 10].strip()
                match = re.search(r'\b\d{5}\b', posible)
                if match:
                    cp = match.group(0)
                    conteo_cp[cp] = conteo_cp.get(cp, 0) + 1

    if conteo_cp:
        return max(conteo_cp, key=conteo_cp.get)
    return ""


ESTADOS_MX = {
    "AGUASCALIENTES", "BAJA CALIFORNIA", "BAJA CALIFORNIA SUR", "CAMPECHE", "CHIAPAS", "CHIHUAHUA",
    "CIUDAD DE MEXICO", "COAHUILA", "COLIMA", "DURANGO", "GUANAJUATO", "GUERRERO", "HIDALGO",
    "JALISCO", "MEXICO", "ESTADO DE MEXICO", "MICHOACAN", "MORELOS", "NAYARIT", "NUEVO LEON", "OAXACA", "PUEBLA",
    "QUERETARO", "QUINTANA ROO", "SAN LUIS POTOSI", "SINALOA", "SONORA", "TABASCO", "TAMAULIPAS",
    "TLAXCALA", "VERACRUZ", "YUCATAN", "ZACATECAS"
}


def extraer_municipio(texto):
    lineas = texto.splitlines()

    for i, linea in enumerate(lineas):
        if re.search(r'\bMunicipio\b', linea, re.IGNORECASE):
            match = re.search(r'Municipio\s*:\s*(.*?)\s*Estado\s*:', linea, re.IGNORECASE)
            if match:
                municipio = match.group(1).strip()
                if municipio and municipio.upper() not in ESTADOS_MX and not re.fullmatch(r'\d{4,5}', municipio):
                    return municipio

            match_simple = re.search(r'Municipio\s*:\s*(.+)', linea, re.IGNORECASE)
            if match_simple:
                posible = match_simple.group(1).strip()
                if posible and posible.upper() not in ESTADOS_MX and not re.fullmatch(r'\d{4,5}', posible):
                    return posible

            segmento = lineas[i:i+15]
            cp_idx = estado_idx = None
            for j, l in enumerate(segmento):
                if re.fullmatch(r'\d{4,5}', l.strip()):
                    cp_idx = j
                elif l.strip().upper() in ESTADOS_MX:
                    estado_idx = j
                    break

            if cp_idx is not None and estado_idx is not None and estado_idx > cp_idx + 1:
                municipio = segmento[cp_idx + 1:estado_idx]
                municipio = [l.strip() for l in municipio if l.strip()]
                if municipio:
                    return ' '.join(municipio)
    return ""


def extraer_tipo_vehiculo(texto):
    lineas = texto.splitlines()

    patrones = [
        r'^Autom[oó]viles\s+Nacionales',
        r'^Autom[oó]viles\s+Importados',
        r'^Autom[oó]viles\s+Especiales',       # NUEVO
        r'^Camiones\s+Particulares',            # NUEVO
        r'^Camiones\s+Importados',              # NUEVO
        r'^Camiones\s+Nacionales',              # NUEVO
        r'^Camiones\s+Especiales',              # NUEVO
        r'^Camiones-Panel',
        r'^Motocicletas',
        r'^Tractocami[oó]n'
    ]

    for i, linea in enumerate(lineas):
        if re.search(r'DESCRIPCIÓN DEL VEHÍCULO ASEGURADO', linea, re.IGNORECASE):
            for j in range(0, 11):
                if i + j < len(lineas):
                    posible = lineas[i + j].strip()
                    for patron in patrones:
                        if re.match(patron, posible, re.IGNORECASE):
                            return posible
                    match = re.search(r'Tipo\s*:\s*(.+)', lineas[i + j], re.IGNORECASE)
                    if match:
                        posible = match.group(1).strip()
                        for patron in patrones:
                            if re.match(patron, posible, re.IGNORECASE):
                                return posible
            break

    encontrados = []
    for i, linea in enumerate(lineas):
        if re.search(r'DESCRIPCIÓN DEL VEHÍCULO ASEGURADO', linea, re.IGNORECASE):
            for j in range(0, 11):
                if i + j < len(lineas):
                    posible = lineas[i + j].strip()
                    for patron in patrones:
                        if re.match(patron, posible, re.IGNORECASE):
                            encontrados.append(posible)
                    match = re.search(r'Tipo\s*:\s*(.+)', lineas[i + j], re.IGNORECASE)
                    if match:
                        posible = match.group(1).strip()
                        for patron in patrones:
                            if re.match(patron, posible, re.IGNORECASE):
                                encontrados.append(posible)

    if encontrados:
        contador = Counter(encontrados)
        return contador.most_common(1)[0][0]

    return ""


def extraer_direccion(texto):
    lineas = texto.splitlines()
    inicio_idx = None
    fin_idx = None

    for i, linea in enumerate(lineas):
        if re.search(r'INFORMACIÓN DEL ASEGURADO', linea, re.IGNORECASE):
            inicio_idx = i
        if re.search(r'DESCRIPCIÓN DEL VEHÍCULO ASEGURADO', linea, re.IGNORECASE):
            fin_idx = i
            break

    if inicio_idx is not None and fin_idx is not None:
        bloque = "\n".join(lineas[inicio_idx:fin_idx])
        cp = extraer_cp(bloque)
        if cp:
            lineas_bloque = bloque.splitlines()
            for i, linea in enumerate(lineas_bloque):
                if cp in linea:
                    if i - 1 >= 0:
                        return lineas_bloque[i - 1].strip()

    vigencias = extraer_vigencia_por_frecuencia(texto)
    primera_fecha = vigencias.get("Inicio Vigencia")
    if primera_fecha and primera_fecha != "":
        fecha_idx = None
        fin_idx2 = None

        for i, linea in enumerate(lineas):
            if primera_fecha in linea:
                fecha_idx = i
                break
        for i, linea in enumerate(lineas):
            if re.search(r'INFORMACIÓN DEL ASEGURADO', linea, re.IGNORECASE):
                fin_idx2 = i
                break

        if fecha_idx is not None and fin_idx2 is not None and fecha_idx < fin_idx2:
            for desplazamiento in range(2, 6):
                target_idx = fecha_idx + desplazamiento
                if target_idx < fin_idx2 and target_idx < len(lineas):
                    posible = lineas[target_idx].strip()
                    if re.search(r'\b(MZA|MZ|MANZANA|LTE|LOTE|CALLE|AV\.?|AVENIDA|NO\.?\s*EXT|NO\.?\s*INT|COLONIA)\b', posible, re.IGNORECASE):
                        return posible

            cp = extraer_cp(texto)
            if cp:
                for i, linea in enumerate(lineas):
                    if cp in linea:
                        if i - 1 >= 0:
                            return lineas[i - 1].strip()
    return ""


DESCARTAR_PATTERNS = [
    "ESTA POLIZA AMPARA",
    "ESTIMADO ASEGURADO QUÁLITAS COMPAÑÍA DE SEGUROS",
    "ARTÍCULO 25 DE LA LEY SOBRE EL CONTRATO DE SEGURO",
    "NUESTRA UNIDAD ESPECIALIZADA DE ATENCIÓN A USUARIOS",
    "COMISIÓN NACIONAL PARA LA PROTECCIÓN Y DEFENSA",
    "AVISO DE PRIVACIDAD INTEGRAL",
    "GENERALES Y ESPECIALES DE ESTA PÓLIZA, EL VEHÍCULO CONTRA PÉRDIDAS O DAÑOS CAUSADOS POR CUALQUIERA DE LOS RIESGOS QUE SE"
]


def extraer_descripcion_vehiculo(texto):
    lineas = texto.splitlines()
    descripciones = []

    for i, linea in enumerate(lineas):
        if re.search(r'English', linea, re.IGNORECASE):
            for j in range(12, 15):
                if i + j < len(lineas):
                    posible = lineas[i + j].strip()
                    if re.fullmatch(r'\d{2,5}', posible):
                        descripciones.append(posible)
                        if i + j + 1 < len(lineas):
                            descripciones.append(lineas[i + j + 1].strip())
                        break
            break

    inicio_idx = None
    fin_idx = None
    for i, linea in enumerate(lineas):
        if re.search(r'INFORMACIÓN DEL ASEGURADO', linea, re.IGNORECASE):
            inicio_idx = i
        if re.search(r'INFORMACIÓN IMPORTANTE', linea, re.IGNORECASE):
            fin_idx = i
            break

    if inicio_idx is not None and fin_idx is not None:
        bloque = "\n".join(lineas[inicio_idx:fin_idx])
        vigencias = extraer_vigencia_por_frecuencia(bloque)
        primera_fecha = vigencias.get("Inicio Vigencia")
        if primera_fecha and primera_fecha != "":
            for i in range(inicio_idx, fin_idx):
                if primera_fecha in lineas[i]:
                    if i - 1 > inicio_idx:
                        descripciones.append(lineas[i - 1].strip())
                    break

    inicio_fallback = None
    fin_fallback = None
    for i, linea in enumerate(lineas):
        if re.search(r'PÓLIZA DE SEGURO DE AUTOMÓVILES', linea, re.IGNORECASE):
            inicio_fallback = i
        if re.search(r'INFORMACIÓN DEL ASEGURADO', linea, re.IGNORECASE):
            fin_fallback = i
            break

    if inicio_fallback is not None and fin_fallback is not None:
        bloque_fallback = lineas[inicio_fallback:fin_fallback]
        vigencias_fb = extraer_vigencia_por_frecuencia("\n".join(bloque_fallback))
        fecha_fb = vigencias_fb.get("Inicio Vigencia")
        if fecha_fb and fecha_fb != "":
            target_idx = fin_fallback - 7
            if target_idx > inicio_fallback and target_idx >= 0:
                posible_valor = lineas[target_idx].strip()
                for pat in DESCARTAR_PATTERNS:
                    if pat in posible_valor.upper():
                        return ""
                descripciones.append(posible_valor)

    if descripciones:
        contador = Counter(descripciones)
        return contador.most_common(1)[0][0]
    return ""


def extraer_colonia(texto: str) -> str:
    texto_upper = texto.upper()
    lineas = texto_upper.splitlines()

    inicio_idx, fin_idx = None, None
    for i, linea in enumerate(lineas):
        if "INFORMACION DEL ASEGURADO" in linea or "INFORMACIÓN DEL ASEGURADO" in linea:
            inicio_idx = i
        if "DESCRIPCION DEL VEHICULO ASEGURADO" in linea or "DESCRIPCIÓN DEL VEHÍCULO ASEGURADO" in linea:
            fin_idx = i
            break

    if inicio_idx is None or fin_idx is None:
        return ""

    bloque = lineas[inicio_idx:fin_idx]

    for i, linea in enumerate(bloque):
        if re.search(r'\bCOLONIA:', linea, re.IGNORECASE):
            for desplazamiento in range(6, 10):
                idx_colonia = i + desplazamiento
                if idx_colonia < len(bloque):
                    posible_colonia = bloque[idx_colonia].strip()
                    for k in range(1, 6):
                        if idx_colonia - k >= 0:
                            linea_estado = bloque[idx_colonia - k].strip()
                            if linea_estado in ESTADOS_MX:
                                return posible_colonia.title()

    if fin_idx - inicio_idx >= 2:
        idx_colonia = len(bloque) - 2
        posible_colonia = bloque[idx_colonia].strip()
        for k in range(1, 6):
            if idx_colonia - k >= 0:
                linea_estado = bloque[idx_colonia - k].strip()
                if linea_estado in ESTADOS_MX:
                    return posible_colonia.title()

    municipio = extraer_municipio(texto)
    if municipio:
        for i, linea in enumerate(lineas):
            if municipio.upper() in linea.upper():
                if i + 1 < len(lineas):
                    siguiente = lineas[i + 1].strip()
                    if re.search(r'\bCOLONIA:', siguiente, re.IGNORECASE):
                        partes = siguiente.split(":", 1)
                        if len(partes) > 1:
                            return partes[1].strip().title()
    return ""
