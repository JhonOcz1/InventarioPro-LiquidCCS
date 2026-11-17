"""
dolar_service.py - Servicio optimizado para consultar la Tasa del Dólar en Venezuela
Conexión con DolarApi (BCV y Paralelo) usando librería estándar de Python (compatible 100% con Android APK)
y caché instantáneo en SQLite para funcionamiento sin internet.
"""

import json
import urllib.request
import ssl
from datetime import datetime
from typing import Dict, Any, Tuple
import database

API_URL = "https://ve.dolarapi.com/v1/dolares"
TIMEOUT_SECONDS = 3.0


def obtener_tasa_dolar(forzar_red: bool = False) -> Dict[str, Any]:
    """
    Obtiene la tasa oficial (BCV) y paralelo desde DolarApi.
    Si hay internet, actualiza la base de datos local y retorna los datos en vivo.
    Si no hay conexión o falla la petición, recupera inmediatamente la tasa en caché de SQLite.
    """
    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(
            API_URL,
            headers={"User-Agent": "InventarioPro/1.0 (Android; Windows)"}
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS, context=ctx) as resp:
            if resp.status == 200:
                raw_data = resp.read().decode("utf-8")
                datos = json.loads(raw_data)
                bcv_val = None
                paralelo_val = None
                fecha_act = datetime.now().strftime("%d/%m/%Y %I:%M %p")

                for item in datos:
                    fuente = str(item.get("fuente", "")).lower()
                    promedio = float(item.get("promedio", 0.0) or 0.0)
                    if fuente == "oficial" and promedio > 0:
                        bcv_val = promedio
                    elif fuente == "paralelo" and promedio > 0:
                        paralelo_val = promedio

                if bcv_val is not None:
                    par_final = paralelo_val if paralelo_val else bcv_val
                    database.guardar_tasas_cache(bcv_val, par_final, fecha_act)
                    return {
                        "bcv": bcv_val,
                        "paralelo": par_final,
                        "fecha": fecha_act,
                        "online": True,
                        "mensaje": f"Actualizado hoy ({fecha_act})"
                    }
    except Exception:
        pass

    # Si no hubo internet, recuperar desde la base de datos local (0ms)
    cache = database.obtener_tasas_cache()
    return {
        "bcv": cache["bcv"],
        "paralelo": cache["paralelo"],
        "fecha": cache["fecha"],
        "online": False,
        "mensaje": f"Sin internet: Usando tasa guardada ({cache['fecha']})"
    }


def formatear_precios(monto_usd: float | None, tasa_bcv: float) -> Tuple[str, str]:
    """
    Retorna dos strings formateados: [USD] y [Bs].
    Ejemplo: ("$10,00", "Bs. 9.140,22")
    """
    if monto_usd is None or monto_usd == 0:
        return ("-", "-")

    str_usd = f"${monto_usd:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    monto_bs = monto_usd * tasa_bcv
    str_bs = f"Bs. {monto_bs:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return (str_usd, str_bs)


if __name__ == "__main__":
    tasa = obtener_tasa_dolar()
    print("Resultado Tasa Dólar:")
    print(f"BCV: {tasa['bcv']} Bs/USD")
    print(f"Paralelo: {tasa['paralelo']} Bs/USD")
    print(f"Estado: {'En línea' if tasa['online'] else 'Offline'}")
    print(f"Mensaje: {tasa['mensaje']}")
