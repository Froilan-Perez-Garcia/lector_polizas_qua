import os
import tempfile
from typing import List
from io import BytesIO

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

import pandas as pd

from poliza_qualitas import (
    leer_pdf_completo,
    es_poliza_auto_qualitas,
    extraer_tipo_poliza,
    extraer_numero_poliza_qualitas,
    extraer_rfc_mas_repetido,
    extraer_prima_neta,
    extraer_tasa_financiamiento,
    extraer_gastos_expedicion,
    extraer_subtotal,
    extraer_prima_total,
    extraer_nombre_cliente,
    extraer_vigencia_por_frecuencia,
    extraer_iva,
    extraer_forma_pago,
    extraer_moneda,
    extraer_motor,
    extraer_serie,
    extraer_placas,
    extraer_cp,
    extraer_direccion,
    extraer_tipo_vehiculo,
    extraer_descripcion_vehiculo,
    extraer_colonia,
    extraer_municipio,
)

app = FastAPI(title="Extractor de Polizas Qualitas")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def procesar_pdf(ruta_pdf: str, nombre_archivo: str) -> dict:
    texto, paginas_dict = leer_pdf_completo(ruta_pdf)

    if not es_poliza_auto_qualitas(texto):
        return {
            "archivo": nombre_archivo,
            "mensaje": "No es una poliza de auto Qualitas",
        }

    vigencia = extraer_vigencia_por_frecuencia(texto)

    return {
        "archivo": nombre_archivo,
        "tipoPoliza": extraer_tipo_poliza(texto),
        "numeroPoliza": extraer_numero_poliza_qualitas(texto),
        "nombreCliente": extraer_nombre_cliente(texto),
        "direccion": extraer_direccion(texto),
        "cp": extraer_cp(texto),
        "municipio": extraer_municipio(texto),
        "colonia": extraer_colonia(texto),
        "rfcAsegurado": extraer_rfc_mas_repetido(texto),
        "descripcionVehiculo": extraer_descripcion_vehiculo(texto),
        "nacionalImportado": extraer_tipo_vehiculo(texto),
        "modelo": "",
        "placas": extraer_placas(texto, paginas_dict),
        "serie": extraer_serie(texto),
        "motor": extraer_motor(texto),
        "formaPago": extraer_forma_pago(texto),
        "moneda": extraer_moneda(texto),
        "primaNeta": extraer_prima_neta(texto),
        "tasaFinanciamiento": extraer_tasa_financiamiento(texto),
        "gastosExpedicion": extraer_gastos_expedicion(texto),
        "subtotal": extraer_subtotal(texto),
        "iva": extraer_iva(texto),
        "primaTotal": extraer_prima_total(texto),
        "inicioVigencia": vigencia.get("Inicio Vigencia", ""),
        "finVigencia": vigencia.get("Fin Vigencia", ""),
        "tipoVehiculo": extraer_tipo_vehiculo(texto),
    }


@app.post("/extraer_poliza_qualitas")
async def extraer_poliza_qualitas(files: List[UploadFile] = File(...)):
    resultados = []

    for file in files:
        contenido = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(contenido)
            tmp_path = tmp.name

        try:
            resultado = procesar_pdf(tmp_path, file.filename or "sin_nombre.pdf")
            resultados.append(resultado)
        except Exception as e:
            resultados.append({
                "archivo": file.filename or "sin_nombre.pdf",
                "mensaje": f"Error al procesar: {str(e)}",
            })
        finally:
            os.unlink(tmp_path)

    return {"success": True, "data": resultados}


@app.post("/exportar_excel")
async def exportar_excel(files: List[UploadFile] = File(...)):
    resultados = []

    for file in files:
        contenido = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(contenido)
            tmp_path = tmp.name

        try:
            resultado = procesar_pdf(tmp_path, file.filename or "sin_nombre.pdf")
            resultados.append(resultado)
        except Exception as e:
            resultados.append({
                "archivo": file.filename or "sin_nombre.pdf",
                "mensaje": f"Error: {str(e)}",
            })
        finally:
            os.unlink(tmp_path)

    validos = [r for r in resultados if "mensaje" not in r]
    rechazados = [r for r in resultados if "mensaje" in r]

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        if validos:
            df = pd.DataFrame(validos)
            df.to_excel(writer, sheet_name="Polizas", index=False)
        if rechazados:
            df_r = pd.DataFrame(rechazados)
            df_r.to_excel(writer, sheet_name="Rechazadas", index=False)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=polizas_qualitas.xlsx"},
    )
