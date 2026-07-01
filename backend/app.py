from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
import tempfile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from poliza_qualitas import (
    leer_pdf_completo,
    extraer_direccion,
    extraer_tipo_vehiculo,
    extraer_descripcion_vehiculo,
    extraer_colonia,
    extraer_municipio,
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
)

from poliza_gnp import (
    leer_pdf_completo as leer_pdf_gnp,
    es_poliza_auto_gnp,
    extraer_tipo_poliza as gnp_tipo_poliza,
    extraer_nombre_cliente as gnp_nombre_cliente,
    extraer_renovacion,
    extraer_rfc,
    extraer_numero_poliza,
    extraer_vigencia,
    extraer_prima_neta as gnp_prima_neta,
    extraer_derecho_poliza,
    extraer_iva as gnp_iva,
    extraer_importe_pagar,
    extraer_uso,
    extraer_recargo_fraccionado,
    extraer_descripcion,
    extraer_serie as gnp_serie,
    extraer_modelo,
    extraer_placas as gnp_placas,
    extraer_direccion as gnp_direccion,
    extraer_clave_agente,
    extraer_nombre_agente,
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/extraer_poliza_qualitas")
async def extraer_poliza_qualitas(file: UploadFile):
    temp_file_path = None
    try:
        logger.info(f"Recibiendo archivo: {file.filename}")

        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Solo se aceptan archivos PDF")

        contenido = await file.read()
        logger.info(f"Tamaño del archivo: {len(contenido)} bytes")

        temp_file_path = os.path.join(tempfile.gettempdir(), "temp_qualitas.pdf")
        with open(temp_file_path, "wb") as f:
            f.write(contenido)

        logger.info("Leyendo PDF completo...")
        texto, paginas_dict = leer_pdf_completo(temp_file_path)

        if not texto:
            raise HTTPException(status_code=400, detail="No se pudo extraer texto del PDF")

        logger.info(f"Texto extraído: {len(texto)} caracteres")

        if not es_poliza_auto_qualitas(texto):
            return {"error": "El archivo no corresponde a una póliza de auto Qualitas."}

        logger.info("Extrayendo información de la póliza...")
        numero = extraer_numero_poliza_qualitas(texto)
        vigencia = extraer_vigencia_por_frecuencia(texto)

        informacion = {
            "Tipo de Póliza": extraer_tipo_poliza(texto),
            "Número de Póliza": numero,
            "RFC del Asegurado": extraer_rfc_mas_repetido(texto),
            "Inicio Vigencia": vigencia.get("Inicio Vigencia", "No encontrada"),
            "Fin Vigencia": vigencia.get("Fin Vigencia", "No encontrada"),
            "Prima Neta": extraer_prima_neta(texto),
            "Tasa de Financiamiento": extraer_tasa_financiamiento(texto),
            "Gastos de Expedición": extraer_gastos_expedicion(texto),
            "Subtotal": extraer_subtotal(texto),
            "I.V.A. 16%": extraer_iva(texto),
            "Prima Total": extraer_prima_total(texto),
            "Forma de Pago": extraer_forma_pago(texto),
            "Moneda": extraer_moneda(texto),
            "Motor": extraer_motor(texto),
            "Serie": extraer_serie(texto),
            "Placas": extraer_placas(texto, paginas_dict),
            "C.P.": extraer_cp(texto),
            "Dirección": extraer_direccion(texto),
            "Tipo de Vehículo": extraer_tipo_vehiculo(texto),
            "Descripción del Vehículo": extraer_descripcion_vehiculo(texto),
            "Colonia": extraer_colonia(texto),
            "Municipio": extraer_municipio(texto),
            "Nombre o razon social del cliente": extraer_nombre_cliente(texto),
        }

        logger.info("Extracción completada exitosamente")
        return informacion

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error procesando archivo: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al procesar el archivo: {str(e)}")
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.info("Archivo temporal eliminado")
            except:
                pass


@app.post("/extraer_poliza_gnp")
async def extraer_poliza_gnp(file: UploadFile):
    temp_file_path = None
    try:
        logger.info(f"Recibiendo archivo: {file.filename}")

        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Solo se aceptan archivos PDF")

        contenido = await file.read()
        logger.info(f"Tamaño del archivo: {len(contenido)} bytes")

        temp_file_path = os.path.join(tempfile.gettempdir(), "temp_gnp.pdf")
        with open(temp_file_path, "wb") as f:
            f.write(contenido)

        logger.info("Leyendo PDF completo...")
        texto, paginas_dict = leer_pdf_gnp(temp_file_path)

        if not texto:
            raise HTTPException(status_code=400, detail="No se pudo extraer texto del PDF")

        logger.info(f"Texto extraído: {len(texto)} caracteres")

        if not es_poliza_auto_gnp(texto):
            return {"error": "El archivo no corresponde a una póliza de auto GNP."}

        logger.info("Extrayendo información de la póliza...")
        vigencia = extraer_vigencia(texto, paginas_dict)

        informacion = {
            "Tipo de Póliza": gnp_tipo_poliza(texto, paginas_dict),
            "Renovación": extraer_renovacion(texto, paginas_dict),
            "Número de Póliza": extraer_numero_poliza(texto, paginas_dict),
            "Nombre o razón social del cliente": gnp_nombre_cliente(texto, paginas_dict),
            "RFC": extraer_rfc(texto, paginas_dict),
            "Inicio Vigencia": vigencia.get("Inicio Vigencia", "No encontrada"),
            "Fin Vigencia": vigencia.get("Fin Vigencia", "No encontrada"),
            "Prima Neta": f"${gnp_prima_neta(texto, paginas_dict)}",
            "Derecho de Póliza": f"${extraer_derecho_poliza(texto, paginas_dict)}",
            "IVA": f"${gnp_iva(texto, paginas_dict)}",
            "Importe por Pagar": f"${extraer_importe_pagar(texto, paginas_dict)}",
            "Uso": extraer_uso(texto, paginas_dict),
            "Recargo por Pago Fraccionado": f"${extraer_recargo_fraccionado(texto, paginas_dict)}",
            "Descripción": extraer_descripcion(texto, paginas_dict),
            "Serie": gnp_serie(texto, paginas_dict),
            "Modelo": extraer_modelo(texto, paginas_dict),
            "Placas": gnp_placas(texto, paginas_dict),
            "Dirección": gnp_direccion(texto, paginas_dict),
            "Clave del Agente": extraer_clave_agente(texto, paginas_dict),
            "Nombre del Agente": extraer_nombre_agente(texto, paginas_dict),
        }

        logger.info("Extracción GNP completada exitosamente")
        return informacion

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error procesando archivo GNP: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al procesar el archivo: {str(e)}")
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.info("Archivo temporal GNP eliminado")
            except:
                pass