"""
database.py - Módulo de persistencia SQLite optimizado para Móvil (Android APK) y PC
Maneja rutas seguras con copia desde assets/inventario.db, índices de velocidad,
tasas cambiarias configurables, cálculo de arbitraje en tiempo real y consultas CRUD.
"""

import os
import re
import shutil
import sqlite3
from typing import List, Dict, Any, Optional

DB_NAME = "inventario.db"
TASA_BCV_DEFECTO = 914.02
TASA_REPOSICION_DEFECTO = 1100.00
_ultima_fecha_sync = "Guardada local"

# Cachés en memoria RAM para filtrado/estadísticas instantáneos (< 1 ms)
_CACHE_PRODUCTOS: Optional[List[Dict[str, Any]]] = None
_CACHE_TASAS: Optional[Dict[str, float]] = None


def invalidar_cache(invalidar_productos: bool = True, invalidar_tasas: bool = False):
    """Limpia selectivamente la caché en memoria RAM cuando ocurren cambios en SQLite."""
    global _CACHE_PRODUCTOS, _CACHE_TASAS
    if invalidar_productos:
        _CACHE_PRODUCTOS = None
    if invalidar_tasas:
        _CACHE_TASAS = None


def get_writable_app_dir() -> str:
    """
    Obtiene un directorio 100% escribible y persistente para exportaciones y archivos temporales
    tanto en Android APK (FLET_APP_STORAGE_DATA / TEMP) como en PC.
    """
    for env_key in ("FLET_APP_STORAGE_DATA", "FLET_APP_STORAGE_TEMP"):
        ruta_env = os.environ.get(env_key)
        if ruta_env:
            try:
                os.makedirs(ruta_env, exist_ok=True)
                return ruta_env
            except Exception:
                pass

    base_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.isdir(base_dir) and os.access(base_dir, os.W_OK):
        return base_dir

    home_dir = os.path.join(os.path.expanduser("~"), ".inventariopro")
    os.makedirs(home_dir, exist_ok=True)
    return home_dir


def obtener_ruta_db() -> str:
    """
    Obtiene la ruta de inventario.db garantizando permisos de escritura en Android y PC.
    En Android (FLET_APP_STORAGE_DATA): si inventario.db aún no existe allí,
    la copia desde assets/inventario.db mediante shutil.copy para evitar errores 'readonly database'.
    En escritorio (Windows/Linux/Mac): utiliza inventario.db en el directorio local.
    """
    storage_data = os.environ.get("FLET_APP_STORAGE_DATA")
    if storage_data:
        os.makedirs(storage_data, exist_ok=True)
        db_destino = os.path.join(storage_data, DB_NAME)
        if not os.path.exists(db_destino):
            base_dir = os.path.dirname(os.path.abspath(__file__))
            db_origen = os.path.join(base_dir, "assets", DB_NAME)
            if not os.path.exists(db_origen) and os.environ.get("FLET_ASSETS_DIR"):
                alt_origen = os.path.join(os.environ["FLET_ASSETS_DIR"], DB_NAME)
                if os.path.exists(alt_origen):
                    db_origen = alt_origen
            if os.path.exists(db_origen):
                shutil.copy(db_origen, db_destino)
        return db_destino

    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, DB_NAME)


def get_db_path() -> str:
    """Alias compatible hacia obtener_ruta_db()."""
    return obtener_ruta_db()


def get_connection():
    """Retorna una conexión a SQLite optimizada en memoria con row_factory."""
    conn = sqlite3.connect(obtener_ruta_db(), timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA temp_store=MEMORY;")
    conn.execute("PRAGMA cache_size=-8000;")
    return conn


PRODUCTOS_INICIALES = [
    ('INV-001', 'ADAPTADOR HDMI A VGA SPIDERTEC', 9, 10.00, 10.00, None, None),
    ('INV-002', 'ADAPTADOR DISPLAY PORT A VGA', 5, 10.00, 10.00, None, None),
    ('INV-003', 'ADAPTADOR HDMI A VGA CON AUDIO', 1, 10.00, 10.00, None, None),
    ('INV-004', 'CABLE DISPLAYPORT A HDMI', 0, 8.00, 7.00, None, None),
    ('INV-005', 'CABLE DISPLAYPORT A DISPLAYPORT GENERICO', 0, None, None, None, None),
    ('INV-006', 'CABLE DISPLAYPORT A DISPLAYPORT SPIDETREC', 11, 10.00, 12.00, 2.15, None),
    ('INV-007', 'ADAPTADOR DISPLAYPORT A HDMI', 0, None, 8.00, None, None),
    ('INV-008', 'ADAPTADOR RECEPTOR BLUETOOTH PARA CORNETA', 2, 5.00, 7.00, 3.00, None),
    ('INV-009', 'ADAPTADOR RECEPTOR BLUETOOTH spidetrec', 24, 5.00, 7.00, 1.15, None),
    ('INV-010', 'ADAPTADOR OTG USB AY USB C UNNO TECNO', 3, 5.00, 7.00, None, None),
    ('INV-011', 'ADAPTADOR OTG USB A TIPO C SAMSUM', 1, 5.00, 7.00, None, None),
    ('INV-012', 'ADAPTADOR DISPLAYPORT A VGA', 0, 9.00, 7.00, None, None),
    ('INV-013', 'AUDIFONOS GENIUS HS G710V CON MICROFONO OMNIDIRECIONAL USB', 2, 35.00, 40.00, 33.97, '1 DEP.*'),
    ('INV-014', 'AUDIFONOS GENIUS GX 580 CON MICROFONO', 0, 41.00, 25.00, None, None),
    ('INV-015', 'AUDIFONO GAMER LAMIA COLOR NEGRO H320RGB1', 0, None, None, 18.85, None),
    ('INV-016', 'AUDIFONO GAMER ONIKUMA K10', 0, None, None, None, None),
    ('INV-017', 'AUDIFONO DEVIL STN-29', 1, 10.00, 10.00, None, None),
    ('INV-018', 'AUDIFONO ALAMBRICO 2K GAME QKZ', 1, 10.00, 10.00, None, None),
    ('INV-019', 'AUDIFONO GAMER CRONUS RGB SONIDO ENVOLVENTE H211', 0, None, 35.00, None, None),
    ('INV-020', 'AUDIFONO ALAMBRICO GENIUS CON MICROFONO HS 300N', 0, None, 15.00, 39.10, None),
    ('INV-021', 'AUDIFONO ALAMBRICO CON MICROFONO INTEGRADO LOGITECH USB', 1, 30.00, 35.00, None, None),
    ('INV-022', 'AUDIFONOS ALAMBRICOS', 7, 5.00, 7.00, None, None),
    ('INV-023', 'AUDIFONOS INALAMBRICO BEATS STN-16 CASCO', 1, 10.00, 12.00, None, None),
    ('INV-024', 'AUDIFONO IRE PRO REDRAGON TRI-MODE CABLE TIPO BLUETOOTH', 0, 50.00, 55.00, None, 'Brian'),
    ('INV-025', 'AUDIFONOS INALAMBRICOS F9-5 TWS CON POWER BANK', 2, 5.00, 7.00, 24.85, None),
    ('INV-026', 'AUDIFONOS GAMER HYLAS NEGRO', 2, 30.00, 35.00, 15.76, None),
    ('INV-027', 'AUDIFONOS GAMER HYLAS BLANCO', 0, 49.00, 35.00, 13.95, None),
    ('INV-028', 'AUDIFONO CON MICROFONO GAMEMAX GAMING HG200 7 COLORES', 1, 25.00, 30.00, None, None),
    ('INV-029', 'AUDIFONOS M10 INALAMBRICOS V53 DURACION 5 HORAS', 0, 10.00, 8.00, None, None),
    ('INV-030', 'AUDIFONOS UNNO TKNO ZENMAX INALAMBRICO CON MICROFONO', 1, 35.00, 40.00, None, 'BRIAN'),
    ('INV-031', 'AUDIFONOS INALAMBRICO CON MICROFONO ZEN PRO', 1, 25.00, 30.00, None, 'BRIAN'),
    ('INV-032', 'AUDIFONO DEVIL STN-25', 1, 10.00, 12.00, None, None),
    ('INV-033', 'AUDIFONOS GAMER ARES RGB REDRAGON NEGRO MOD. H120', 2, 30.00, 35.00, None, None),
    ('INV-034', 'AUDIFONOS CON MICROFONO ALAMBRICO HS02B GENIUS', 0, 15.00, 12.00, 50.00, None),
    ('INV-035', 'BASE PARA TV LED FIJA 42"', 0, None, 20.00, None, None),
    ('INV-036', 'BOBINA NEXCOM 5E EXTERIOR', 0, None, None, None, None),
    ('INV-037', 'BOBINA BEGPROD CAT. 5E EXTERIOR', 0, None, None, None, None),
    ('INV-038', 'BOBINA BEGPROD CAT5 INTERIOR DE 100 MTS, AZUL', 0, None, None, None, None),
    ('INV-039', 'BOBINA COMPLETA UTP CAT.6 STC CARRETE EXTER, 0,90 MTS.', 1, None, 80.00, None, None),
    ('INV-040', 'BASE GAMEPAD PARA CECULAR CON JOSTICK', 1, None, 8.00, None, None),
    ('INV-041', 'BATERIA DE 14W PARA UPS', 0, None, 15.00, None, None),
    ('INV-042', 'CAMARA WIFE ESPIA A9', 1, 15.00, 20.00, 26.57, None),
    ('INV-043', 'BARRA DE SONIDO REDRAGON DARKNET M ODGS570', 0, None, 40.00, None, 'BRIAN'),
    ('INV-044', 'BARRA DE SONIDO GAMING GENIUS', 0, 43.00, 30.00, None, None),
    ('INV-045', 'CORNETA PORTATIL ASTRA 45W BLUETOOTH TWS IPX5 RGB', 0, None, 60.00, None, None),
    ('INV-046', 'CONECTOR RJ45 CAT.6 PAQUETE DE 100 UNID,', 0, None, 10.00, None, None),
    ('INV-047', 'CONECTOR RJ45 BOLSA DE 1000 UNIDADES', 0, None, 1.00, None, 'S/N'),
    ('INV-048', 'CABLE DISPLAYPORT A DVI', 0, 12.00, 10.00, None, None),
    ('INV-049', 'CONECTOR RJ45 PAQUETE DE 100 UND', 0, None, 10.00, None, None),
    ('INV-050', 'CABLE HDMI DE 1,5 MTS 4K PREMIUM', 6, 6.00, 8.00, None, None),
    ('INV-051', 'CABLE HDMI DE 1.5 MTS', 4, 3.00, 4.00, None, None),
    ('INV-052', 'CABLE HDMI DE 10 MTS.', 1, 10.00, 12.00, None, None),
    ('INV-053', 'CABLE HDMI DE 3 MTS.', 6, 4.00, 6.00, None, None),
    ('INV-054', 'CABLE HDMI DE 20 MTS.', 3, 25.00, 30.00, None, None),
    ('INV-055', 'CABLE HDMI DE 5 mts,', 5, 7.00, 9.00, None, None),
    ('INV-056', 'CABLE VGA DE 25 MTS', 1, 20.00, 25.00, None, 'DEP.'),
    ('INV-057', 'CABLE DE PODER PARA PC', 6, 4.00, 6.00, None, None),
    ('INV-058', 'CABLE VGA DE 25 MTS', 0, None, 20.00, None, None),
    ('INV-059', 'CABLE VGA DE 10 MT', 2, 10.00, 12.00, None, None),
    ('INV-060', 'CABLE VGA DE 5 MT', 2, 5.00, 7.00, None, None),
    ('INV-061', 'CABLE VGA DE 3 MTS.', 5, 4.00, 6.00, None, None),
    ('INV-062', 'CABLE DISPLAY PORT A VGA', 0, 7.00, 5.00, None, None),
    ('INV-063', 'CABLES VGA DE 1,5 MTS', 3, 3.00, 5.00, 3.50, None),
    ('INV-064', 'CABLE DISPLAY PORT A HDMI', 0, 10.00, 12.00, None, None),
    ('INV-065', 'CABLE 3RCA DE 1,5 MTS', 1, 3.00, 5.00, None, None),
    ('INV-066', 'CABLE UTP CAT.6 1,5 MT', 5, 4.00, 6.00, None, None),
    ('INV-067', 'CABLE HDTV 3RCA A RCA (DVS , TELEVISOR)', 3, 3.00, 5.00, None, None),
    ('INV-068', 'CABLE SATA 3,0 0,45 CM', 10, 3.00, 5.00, None, None),
    ('INV-069', 'CAMARA DE VIGILANCIA MERCUSYS WIFE 2K DETECCION MOV.', 0, 40.00, 45.00, None, None),
    ('INV-070', 'CAMARA TP LINK TAPO C100 VIGILANCIA WIFE VISION NOCTURNA', 1, 40.00, 45.00, None, None),
    ('INV-071', 'CABLE PARA FIBRA OPTICA 10 MT', 0, 10.00, 8.00, None, None),
    ('INV-072', 'CABLE UTP CAT.6 DE 3 MT.', 2, 4.00, 6.00, None, None),
    ('INV-073', 'CABLE UTP CAT.6 DE 5 MT', 6, 5.00, 7.00, None, None),
    ('INV-074', 'CABLE PARA FIBRA OPTICA 20 MT', 0, 9.00, 7.00, None, None),
    ('INV-075', 'CABLE PARA IMPRESORA AZUL 1,5 MT', 4, 3.00, 4.00, None, None),
    ('INV-076', 'CABLE PARA IMPRESORA AZUL 5 MT.', 2, 5.00, 7.00, None, None),
    ('INV-077', 'CAMARA TP LINK TAPO C200 PARA VIGILANCIA 360 WIFE', 1, 50.00, 55.00, None, None),
    ('INV-078', 'CAMARA DOMO PRO 2K 3MP WIFE DE 2,4 ghZ ROBOTICA MOTORIZADO', 4, 50.00, 55.00, None, 'dos judy DEPOSIT'),
    ('INV-079', 'CAMARA TURBO EXT.INT. HIK VISION', 0, None, 20.00, None, None),
    ('INV-080', 'CAMARA WEB1080P', 0, 32.00, 20.00, None, 'Revisar (*)'),
    ('INV-081', 'CAMARA WEB GENIUS', 0, None, 25.00, None, None),
    ('INV-082', 'CARGADOR PARA LAPTO', 0, None, None, None, None),
    ('INV-083', 'CASE JEMIP GAMING IRON MESH BLANCO', 1, 55.00, 60.00, None, 'YUDY dep.'),
    ('INV-084', 'CARGADOR PARA IPHON 13', 1, 7.00, 9.00, None, None),
    ('INV-085', 'CARGADOR PARA CARRO', 1, 7.00, 6.00, None, None),
    ('INV-086', 'CONTROL PARA TV UNIVERSAL', 1, 5.00, 7.00, None, None),
    ('INV-087', 'CASE EXTERNO USB 2,0 2.5 " HDD', 2, 10.00, 12.00, None, None),
    ('INV-088', 'CASE EXTERNO USB 3,0 2.5 " HDD SSD"', 4, 12.00, 14.00, None, None),
    ('INV-089', 'COMBO TECLADO MOUSE ( SPIDERTEC ) ALAMBRICO USB', 0, None, 10.00, None, None),
    ('INV-090', 'COMBO TECLADO MOUSE (LENOVO - HP)', 5, 15.00, 17.00, None, None),
    ('INV-091', 'COMBO SPIDERTEC TECLADO MOUSE ALAMBRICO', 0, 14.00, 10.00, None, None),
    ('INV-092', 'COMBO XTRAIKE MK -207 ALAMBRICO (TECLADO - MOUSE)', 0, None, 15.00, None, None),
    ('INV-093', 'COMBO JEMIP ALAMBRICO USB (TECLADO - MOUSE)', 0, 14.00, 12.00, None, None),
    ('INV-094', 'COMBO JEMIP TECLADO MOUSE INALAMBRICO 3 BOTONES (BLANCO Y NEGRO)', 0, 32.00, 20.00, None, None),
    ('INV-095', 'MUÑECO FUNKO POR CADA UNO', 3, 15.00, 17.00, None, 'DEPOSITO'),
    ('INV-096', 'CONTROL MANDO GAMING INALAMBRICO HARROW PRO V1 G808', 0, 30.00, 35.00, None, 'brian'),
    ('INV-097', 'CONTROL GENIUS PC GX 17', 2, 20.00, 25.00, None, None),
    ('INV-098', 'CONTROL PLAY STATION 3', 1, 12.00, 15.00, None, None),
    ('INV-099', 'CONTROL PLAY STATION 4', 1, 20.00, 22.00, None, None),
    ('INV-100', 'CONTROL ALAMBRICO PARA JUEGO EN COMPUTADORA MICROSOFT', 0, None, 20.00, None, None),
    ('INV-101', 'CONTROL INALAMBRICO PARA JUEGO EN COMPUTADORA', 0, 19.00, 15.00, 3.80, None),
    ('INV-102', 'CONSOLA JUEGO INALAMBRICO M8 GAME STICK', 1, 30.00, 35.00, None, None),
    ('INV-103', 'CONTROL PLAY STATION 3 ESTAMPADO', 0, 15.00, 14.00, None, None),
    ('INV-104', 'CONVERTIDOR MINI VGA A HDMI', 0, 8.00, 7.00, None, None),
    ('INV-105', 'CONVERTIDOR MINI RCA A VGA', 2, 10.00, 12.00, None, None),
    ('INV-106', 'CONVERTIDOR HDMI A VGA', 0, 10.00, 8.00, None, None),
    ('INV-107', 'CONVERTIDOR MARCA MINI HDMI-2AV RCA NEGRO', 2, 10.00, 12.00, None, None),
    ('INV-108', 'CORNETA CON BLUETOOTH MINI SPEAKER A COLOR C ZQS1448', 1, 10.00, 12.00, None, None),
    ('INV-109', 'CORNETA ZQS 1315 BLUETOOH', 1, 10.00, 12.00, None, None),
    ('INV-110', 'CORNETA RUSH', 1, 20.00, 25.00, None, None),
    ('INV-111', 'CORNETA PARA PC 2,5 W', 2, 10.00, 12.00, None, None),
    ('INV-112', 'CORNETA PARA `PC K2053', 3, 10.00, 12.00, None, None),
    ('INV-113', 'CORNETA PARA PC K2059', 0, None, 10.00, None, None),
    ('INV-114', 'CORNETAS SPIDERTEC DE ESCRITORIO USB LUCES LED', 18, 10.00, 12.00, None, '16 Dep.'),
    ('INV-115', 'DISCO SOLIDO SSD GROUP 1 TB', 0, 70.00, 65.00, None, None),
    ('INV-116', 'DISCO SOLIDO SSD GROUP 256GB', 0, None, None, None, None),
    ('INV-117', 'DISCO SOLIDO SSD GROUP 128GB', 0, None, 40.00, None, None),
    ('INV-118', 'DISCO MECANICO DE 500 GB S/N 5VVP7GBE Y 5VVP1YPN', 2, 35.00, 40.00, None, None),
    ('INV-119', 'DISCO SOLIDO PATRIOT SSD 512GB', 0, 65.00, 40.00, None, None),
    ('INV-120', 'DISCO SOLIDO MSI 240 GB', 0, 45.00, 30.00, None, None),
    ('INV-121', 'DISCO SOLIDO SSD JEMIP 256 GB', 0, 40.00, 25.00, None, None),
    ('INV-122', 'DISCO MECANICO PARA LAPTO 500GB', 0, 15.00, 12.00, None, None),
    ('INV-123', 'DISCO MECANICO SATA PARA LAPTO 320GB', 0, 8.00, 5.00, None, None),
    ('INV-124', 'DISCO SOLIDO PATRIOT SSD 480 GB', 0, 86.00, 55.00, None, None),
    ('INV-125', 'EXTENDER REPETIDOR CUDY DUAL BAND AC 1200 2,4GHZ', 0, None, 25.00, None, 'brian'),
    ('INV-126', 'GAMEPAD INALAMBRICO BSP D11S', 1, 35.00, 40.00, None, None),
    ('INV-127', 'FORRO IPHONE 13', 1, 5.00, 7.00, 10.00, None),
    ('INV-128', 'FIRE TV STICK HD 1080P ALEXA VOICE CONTROL TV', 0, None, 45.00, None, None),
    ('INV-129', 'HUB 4 PUERTOS SPIDERTEC TIPO C', 8, 8.00, 10.00, None, '4 DEP.'),
    ('INV-130', 'HUB 7 PUERTOS USB TIPO C 4USB +2USB', 12, 12.00, 14.00, None, '5 dep.'),
    ('INV-131', 'LAPTO DELL I5 DE 11VA 16 RAM SSD 256 (S/N H26GDK3 ARRIBA) (S/N 8RYGCK3 EXIBICION)', 0, None, 375.00, None, None),
    ('INV-132', 'IMPRESORA TERMICA', 0, 40.00, 25.00, None, None),
    ('INV-133', 'KIT DE CAMARA WIFE SEGURIDAD HI VISION', 0, 140.00, 120.00, None, None),
    ('INV-134', 'LAPTO DELL I5 DE 11VA 16 RAM SSD 256 (S/N HQ2JCK3 ARRIBA) (S/N 4CN8BK3 EXIBICION)', 0, None, 375.00, None, None),
    ('INV-135', 'LAPTOP LENOVO I5 DE 8VA. 8 GB 256 RAM', 0, None, 270.00, None, None),
    ('INV-136', 'LAPTO DELL I5 DE 11VA 16 RAM SSD 256 (S/N 4TG7FDK3)', 0, None, 375.00, None, None),
    ('INV-137', 'LAPTOP LENOVO N4020 4 RAM 120GB', 0, 190.00, 170.00, None, 'YUDY'),
    ('INV-138', 'LECTOR CODIGO DE BARRA JEMIP', 0, None, 40.00, None, None),
    ('INV-139', 'LECTOR DE MEMORIA MICROCD', 4, 5.00, 7.00, None, None),
    ('INV-140', 'MEMORIA RAM PARA PC DDR2 DE 2GB', 0, None, 15.00, None, None),
    ('INV-141', 'MEMORIA RAM MUSKIN 8GB DDR3 PARA PC', 1, 40.00, 45.00, None, 'YUDY'),
    ('INV-142', 'MEMORIA RAM PARA PC REDLINE 16GB DDR4', 0, None, 145.00, None, None),
    ('INV-143', 'MEMORIA RAM GENERICA PARA PC DDR3 DE 8 GB', 0, None, 35.00, 39.74, None),
    ('INV-144', 'MEMORIA ADATA MICRO SD 32GB', 0, 8.00, 6.00, 12.00, None),
    ('INV-145', 'MEMORIA KINSTON MICRO SD 128GB', 0, 20.00, 15.00, None, None),
    ('INV-146', 'MICROFONO BALITA SX12 DOS MICROFONOS INALAMBRICO', 1, 50.00, 60.00, None, None),
    ('INV-147', 'MEMORIA MICRO SD KINGSTON 8 GB', 0, None, 8.00, None, None),
    ('INV-148', 'MEMORIA MICRO SD KINGSTON DE 32GB', 0, None, 10.00, None, None),
    ('INV-149', 'MEMORIA MICRO SD JEMIP DE 32 GB', 0, None, 9.00, None, None),
    ('INV-150', 'MEMORIA MICRO SD 64GB JEMIP', 0, 10.00, 8.00, None, None),
    ('INV-151', 'MEMORIA MICRO SD 256GB JEMIP', 0, 32.00, 20.00, None, None),
    ('INV-152', 'MESAS PARA COMPUTADORA COLOR MADERA Y NEGRA', 0, 85.00, 50.00, None, None),
    ('INV-153', 'MEMORIA MICRO CD DE 4GB KINGSTON', 3, 8.00, 10.00, None, None),
    ('INV-154', 'MICROFONO DE BALITA INALAMBRICO N9 ESPOJNJA', 3, 20.00, 25.00, None, None),
    ('INV-155', 'MICROFONO INALAMBRICO DE ESPONJA PLU F-16', 2, 25.00, 30.00, 5.92, None),
    ('INV-156', 'MICROFONO DE BALITA INALAMBRICO DE DOS MICROFONO K9', 1, 20.00, 25.00, None, None),
    ('INV-157', 'MICROFONO DE BALITA DE UN MICROFONO K8', 1, 15.00, 20.00, None, None),
    ('INV-158', 'MICROFONO DE BALITA K35 DOS MICROFONOS REFURBISH', 1, 10.00, 12.00, None, None),
    ('INV-159', 'MICROFONO INALAMBRICO PARA CONFERENCIA HWIN', 1, 20.00, 25.00, None, None),
    ('INV-160', 'MICROFONO DE B ALITGA UN MICROFONO REFURBISH', 1, 10.00, 12.00, None, None),
    ('INV-161', 'MONITOR led AROA 21,5 HDMI-VGA', 2, 50.00, 60.00, None, None),
    ('INV-162', 'MONITOR REFURBISH DELL 24 PULGADAS', 0, 90.00, 80.00, None, None),
    ('INV-163', 'MONITOR 20 PULGADAS NUEVO AUCE', 0, None, 55.00, None, 'YUDY'),
    ('INV-164', 'EXTENDER REPETIDOR CUDY DUAL BAND AC 1200 2,4GHZ', 0, None, None, None, None),
    ('INV-165', 'MONITOR LED AROA 19 " 60hz HDMI-VGA', 0, None, None, None, None),
    ('INV-166', 'MOUSE FENTECH INALAMBRICO GAMER KANATA (NEGRO Y BLANCO)', 0, None, 20.00, None, None),
    ('INV-167', 'MOUSE DELL CAJA GRANDE', 0, 7.00, 5.00, None, None),
    ('INV-168', 'MOUSE INALAMBRICO VERTICAL ERGONOMICO RGV', 0, 24.00, 15.00, None, None),
    ('INV-169', 'MOUSE GAMER KING ULTRA TRIPLE MODO ULTRA LIVIANO BASE DE CARG', 0, None, 40.00, None, None),
    ('INV-170', 'MOUSE GAMER IMPACT REDRAGON SURGE ALAMBRICO', 0, None, 40.00, None, None),
    ('INV-171', 'MOUSE INALAMBRICO UPRODUCTS OPTICO USB NEGRO', 0, None, 10.00, None, None),
    ('INV-172', 'MOUSE AGILER INALAMBRICO MINI WIRELESS CON NANO RECEPTOR NEGRO', 1, 8.00, 10.00, None, None),
    ('INV-173', 'MOUSE UPRODUC TS 1200 INALAMBRICO RECARGABLE', 2, 8.00, 10.00, None, None),
    ('INV-174', 'MOUSE ALAMBRICO GAMER GRIFFIN REDRAGON NEGRO M,OD M607', 0, 25.00, 30.00, None, None),
    ('INV-175', 'MOUSE HP GAMING S600 A COLOR', 0, 10.00, 8.00, None, None),
    ('INV-176', 'MOUSE INALAMBRICO UPRODUCTS', 1, 10.00, 12.00, None, None),
    ('INV-177', 'MOUSE HP M30', 1, 7.00, 9.00, None, None),
    ('INV-178', 'MOUSE ALAMBRICO GAMER FANTECH RAPTOR X UX2', 1, 35.00, 40.00, None, 'brian'),
    ('INV-179', 'MOUSE GAMING HP ALAMBRICO G270', 3, 7.00, 9.00, None, None),
    ('INV-180', 'MOUSE INALAMBRICO GENIUS GRANDE CAJA ROJA', 0, None, 15.00, None, None),
    ('INV-181', 'MOUSE HP M15', 0, 8.00, 10.00, None, None),
    ('INV-182', 'MOUSE INALAMBRICO HP M300', 2, 10.00, 12.00, None, None),
    ('INV-183', 'MOUSE INALAMBRICO SPIDERTEC RECARGABLE', 6, 10.00, 12.00, 3.30, None),
    ('INV-184', 'MOUSE INALAMBRICO COLORVIS', 1, 10.00, 12.00, None, None),
    ('INV-185', 'MOUSE HP INALAMBRICO RECARGABLE W10', 0, None, None, None, None),
    ('INV-186', 'MOUSE ALAMBRICO GENIUS XSCROLL', 0, None, None, None, None),
    ('INV-187', 'MOUSE MINI BANDA', 10, 5.00, 7.00, None, 'DEP.6'),
    ('INV-188', 'MOUSE MINI BANDA', 0, 6.00, 5.00, None, None),
    ('INV-189', 'MOUSE PAD ESCRITORIO', 1, 4.00, 5.00, None, None),
    ('INV-190', 'MOUSE PAD ARGOM', 0, None, 5.00, None, None),
    ('INV-191', 'MOUSE PAD GAMMING REDRG.,', 0, 16.00, 10.00, None, None),
    ('INV-192', 'MOUSE PAD JEMIP', 0, None, 6.00, None, None),
    ('INV-193', 'MOUSE PAD TIPO ALFOMBRA FANTECH MEDID.450X400X4 ML', 1, 12.00, 14.00, None, None),
    ('INV-194', 'MOUSE PAD PARA NIÑAS', 3, 3.00, 5.00, None, None),
    ('INV-195', 'PENDRIVE HI KSEMI 64 GB', 2, 10.00, 12.00, None, None),
    ('INV-196', 'PENDRIVE HP DE 8GB', 0, 10.00, 12.00, None, None),
    ('INV-197', 'PENDRIVE KINGSTON DE 4 GB', 0, 8.00, 7.00, None, None),
    ('INV-198', 'PENDRIVE SANDISK DE 4 GB', 0, 8.00, 7.00, None, None),
    ('INV-199', 'PENDRIVE HIK SEMI DE64 GB USB 3,2 DUAL SLIM', 0, None, 12.00, None, None),
    ('INV-200', 'PENDRIVE ADATA DE 256 GB', 2, 20.00, 25.00, None, None),
    ('INV-201', 'PENDRIVE BLADE HIKSEMI 128 GB', 0, None, 15.00, None, None),
    ('INV-202', 'PENDRIVE SANDISK DE 8GB', 0, None, 8.00, None, None),
    ('INV-203', 'PENDRIVE KINGSTON 32 GB', 0, 12.00, 14.00, None, None),
    ('INV-204', 'PENDRIVE SANDISK DE 16 GBN', 4, 10.00, 12.00, None, None),
    ('INV-205', 'PENDRIVE DE 16GB KINGSTON', 0, 11.00, 13.00, None, None),
    ('INV-206', 'PASTA TERMICA GENERICA', 0, 1.50, 1.00, 25.00, None),
    ('INV-207', 'PASTA TERMICA GAMEMAX', 0, 10.00, 7.00, None, None),
    ('INV-208', 'PENDRIVE KINGSTON DE 128 GB', 1, 15.00, 20.00, None, None),
    ('INV-209', 'PENDRIVE KINGSTON DE 256GB', 0, None, 30.00, None, None),
    ('INV-210', 'PENDRIVE KINGSTGON DE 64 GB', 0, None, 12.00, None, None),
    ('INV-211', 'PC MINI ESE 256GB 8 RAM PROCESADOR 12AVA GENERACION', 0, None, 255.00, None, None),
    ('INV-212', 'PROJECTOR GAME ULTRA HD 3D', 0, None, 90.00, None, None),
    ('INV-213', 'PROCESADOR RIZEN 7 5700G', 0, None, 200.00, None, 'BRIAN'),
    ('INV-214', 'PARLANTE ECHO POP 1GEN INTELIGENTE ALEXA WIFE', 1, None, 50.00, None, None),
    ('INV-215', 'PENDRIVE HIK SEMI DE 64 GB', 0, None, 7.00, None, None),
    ('INV-216', 'PENDRIVE SANDISK DE 32 GB', 0, None, 12.00, None, None),
    ('INV-217', 'POWERBAND', 2, 0.00, 30.00, None, None),
    ('INV-218', 'REGLETAS DE SEIS TOMAS TONAL', 4, 10.00, 12.00, None, '3 DEPOSITO*'),
    ('INV-219', 'RECEPTOR DE WIFE CON ANTENA ALFA', 2, 10.00, 12.00, None, None),
    ('INV-220', 'RADIO BAOFENG ANALOGICO UHF 16 CANALES', 0, None, 40.00, None, None),
    ('INV-221', 'RECEPTOR DE WIFE AX300 (ROJO) ALFA SIN ANTENA', 2, 10.00, 12.00, None, None),
    ('INV-222', 'RECEPTOR DE WIFE AC 1300 SIN ANTENA CUDY', 0, None, 20.00, None, None),
    ('INV-223', 'RECEPTOR DE WIFE AC 1300 CUDY', 0, None, 25.00, None, None),
    ('INV-224', 'RECEPTOR DE WIFE AC 1300 CON ANTENA VERDE', 3, 12.00, 15.00, None, None),
    ('INV-225', 'RECEPTOR WIFE DUAL BAND 600 MBPS NARANJA', 0, 14.00, 17.00, None, None),
    ('INV-226', 'RELOJ SMART TEROS', 1, None, 35.00, None, None),
    ('INV-227', 'RECEPTOR DE WIFE 300MBPS CON ANTENA', 0, None, 8.00, None, None),
    ('INV-228', 'ROUTER TP LINK DECO X10 WIFE MESH AX 1500 EXTENSOR', 0, 330.00, 200.00, None, None),
    ('INV-229', 'ROUTER AC 1200 TP LINK', 0, None, 35.00, None, None),
    ('INV-230', 'RAIZEN 3 AMD', 0, None, None, None, None),
    ('INV-231', 'ROUTER CUDY TRI BAND 4 PUERTOS Y 6 ANTENAS', 0, None, 150.00, None, 'BRIAN uno deposito'),
    ('INV-232', 'ROUTER HIKVISION WIFE 6 AX 3000 DUAL BAND WR30X', 0, None, 50.00, None, None),
    ('INV-233', 'ROUTER CUDY 4 EN 1 AC 1200', 0, 57.00, 35.00, None, None),
    ('INV-234', 'ROUTER CUDY WIFE 6 AC 1200 DOS ANTENAS 5 EN 1', 0, 45.00, 30.00, None, None),
    ('INV-235', 'ROUTER HIKVISION WIFE AC 1200', 0, None, 40.00, None, 'brian'),
    ('INV-236', 'ROUTER CUDY AC 1200 MESH', 0, 57.00, 35.00, None, None),
    ('INV-237', 'ROUTER TPLINK AX 1500 GIGABIT DUAL BAND 4 ANTENAS', 0, None, 55.00, None, None),
    ('INV-238', 'ROUTER AC 1200 UPPRODUCTS DUAL BAND', 0, 32.00, 28.00, None, None),
    ('INV-239', 'ROUTER AX 1500 CUDY WIFE 6', 1, None, 40.00, None, None),
    ('INV-240', 'ROUTER XIOAMI AC 1200 WIFE', 0, 40.00, 25.00, None, None),
    ('INV-241', 'ROUTER CUDY AX 3000 2,5G MESH WIFE 6 DUAL BAND 3 PACK', 0, None, 150.00, None, 'BRIAN'),
    ('INV-242', 'ROUTER TP LINK INALAMBRICO AC 1200 4 ANTENAS DUAL BAND', 0, None, 40.00, None, None),
    ('INV-243', 'ROUTER CUDY ACCES POINT MESH WIFE 7 3 PACK BE3600', 0, None, 230.00, None, None),
    ('INV-244', 'ROUTER CUDY MESH B11000 WIFE7 TRI BAND 2,5G', 0, None, 300.00, None, None),
    ('INV-245', 'ROUTER CUDY AX 3000 WIFE 6 GIGABIT WR3000E', 0, None, 50.00, None, None),
    ('INV-246', 'ROKU PREMIERE 4K', 0, None, 40.00, None, None),
    ('INV-247', 'SSD PATRIO 128GB', 1, None, 40.00, None, None),
    ('INV-248', 'SSD JEMIP 128 GB', 0, None, 35.00, None, None),
    ('INV-249', 'ROKU EXPRESS TVBOX', 0, None, 35.00, None, None),
    ('INV-250', 'SWITCH CUDY 16 PUERTOS ESCRITORIO MOD. GS1016', 0, None, 55.00, None, 'BRIAN'),
    ('INV-251', 'SWITCH CUDY DE 8 PUERTOS', 7, None, 20.00, None, None),
    ('INV-252', 'SWITCH CUDY DE 5 PUERTOS', 0, None, 15.00, None, None),
    ('INV-253', 'SWITCH CUDY GIGABIT 16 PUERTOS RACKEABLE', 0, None, 60.00, None, '1DEP.'),
    ('INV-254', 'SWITCH CUDY VPN 5 PUERTOSY CONTROLADOR AP GIGABIT MOD. C200P', 1, None, 65.00, None, 'BRIAN'),
    ('INV-255', 'TARJETA MADRE MSI RIZEN A520M APRO', 0, 95.00, 15.00, None, None),
    ('INV-256', 'TARJETA MADRE BIOSTAR', 0, 45.00, None, None, None),
    ('INV-257', 'TARJETA DE VIDEO GRAFICA REFURBISH RX 570 4GB', 0, None, 80.00, None, None),
    ('INV-258', 'TARJETA MADRE ASROCK A520HDV/ATXF', 0, 90.00, 80.00, None, None),
    ('INV-259', 'TECLADO ALAMBRICO HP K1600', 0, None, 8.00, None, None),
    ('INV-260', 'TECLADO GAMING RGB SHIV MODELO K512 NEGRO Y BLANCO', 0, None, 40.00, None, None),
    ('INV-261', 'TECLADO JEMIP USB ALAMBRICO', 0, 12.00, 8.00, None, None),
    ('INV-262', 'TECLADO LOGITECH K122 ALAMBRICO', 0, None, 10.00, None, None),
    ('INV-263', 'TECLADO MECANICO DRAGONBORN NEGR0 MODELO K630RGB', 0, None, 45.00, None, 'BRIAN'),
    ('INV-264', 'TECLADO MECANICO HORUS REDRAGON NEGRO', 1, None, 90.00, None, 'brian'),
    ('INV-265', 'TECLADO MECANINICO KUMARA REDRAGON NEGRO 70/30', 0, 73.00, 45.00, None, 'brian'),
    ('INV-266', 'TECLADO MECANCO FIZZ REDRAGON GRAY WHITE', 1, None, 55.00, None, 'BRIAN'),
    ('INV-267', 'TECLADO MECANICO GAMING TRUNDLE CABLEADO REDRAG. 100%', 0, None, 60.00, None, None),
    ('INV-268', 'TECLADO ALAMBRICO HP K1600', 2, None, 10.00, None, None),
    ('INV-269', 'TECLADO GENIUS SCORPION GAMING A COLORES', 4, 20.00, 25.00, None, '3 en deposito*'),
    ('INV-270', 'TECLADO GAMER HARPE REDRAGON MEMBRANA', 0, None, 35.00, None, 'BRIAN'),
    ('INV-271', 'TECLADO MECANICO GAMER FANTECH ATOM 107S ALAMBRICO', 0, None, 35.00, None, None),
    ('INV-272', 'TECLADO MECANICO FANTECH 80 % MK876V2', 0, None, 35.00, None, None),
    ('INV-273', 'TONER LASER CARTRIDER NEGRO', 1, 20.00, 25.00, None, None),
    ('INV-274', 'TECLADO GAMING REDRAGON MECANICO MITRA', 0, None, 55.00, None, 'Revisar (*)'),
    ('INV-275', 'TELEFONO LOGIG 128 almacenamiento, 4 gb ram , 10 ram expandible', 1, None, 120.00, None, None),
    ('INV-276', 'TRANSFORMADOR 12V DE 2A', 4, 5.00, 7.00, None, None),
    ('INV-277', 'TECLADO SPIDERTECH SENCILLO', 3, 5.00, 7.00, None, '2 DEP.'),
    ('INV-278', 'TECLADO HP Y PEQUEÑO MINI', 1, 10.00, 12.00, None, None),
    ('INV-279', 'UNION RJ 45', 0, None, 3.00, None, None),
    ('INV-280', 'UPS BEGPROD DE 1000VA 4 TOMAS DE 7AH', 0, 76.00, 45.00, None, None),
    ('INV-281', 'UPS MINI CDP POE 120VCA', 0, None, 30.00, None, None),
    ('INV-282', 'UPS APC DE 700V 4 TOMAS', 0, None, 85.00, None, None),
    ('INV-283', 'VIDEO BALOOM HIK VISION', 0, 7.00, 5.00, None, None),
    ('INV-284', 'VIDEO BALOOM PASIVO HDCVI A PRESIÒN', 16, 5.00, 4.00, None, 'DEP.9'),
    ('INV-285', 'WIFI PORTATIL INALAMBRICO 4G LTE MOBILE IWIFI', 0, 32.00, 20.00, None, None),
    ('INV-286', 'COMBOS I5 DE 10TH , MEMORIA DDR4 DE 16GB, SSD 480, CASE JEMIP', 0, 515.00, 380.00, None, None),
    ('INV-287', 'VIDEO BALON', 13, 5.00, 7.00, None, '6 DEP.'),
    ('INV-288', 'UPS APC DE 600V 7 TOMAS', 1, 100.00, 105.00, None, None),
    ('INV-289', 'ADAPTADOR USB AC 1300 TP LINK', 1, None, 35.00, None, None),
    ('INV-290', 'SWICHT MERCUSYS 5 PUERTOS MS 105G', 0, 24.00, 20.00, None, None),
    ('INV-291', 'SWICHT MERCUSYS 8 PUERTOS MS 108G', 0, 37.00, 30.00, None, None),
    ('INV-292', 'ROUTER MERCUSYS AC 1300 GIGABIT INALAMBRICO DUAL BAND', 0, 72.00, 45.00, None, None),
    ('INV-293', 'ADAPTADOR RECEPTOR MERCUSYS USB IHIGH GAIN', 5, None, 25.00, None, '5 en deposito'),
    ('INV-294', 'ROUTER AC 1350 TP LINK DE ALTA POTENCIA DUAL BAND', 0, 86.00, 60.00, None, None),
    ('INV-295', 'MODEN ROUTER MERCUSYS 300 MBPS', 0, 65.00, 40.00, None, None),
    ('INV-296', 'ROUTER MULTI MODE TP LINK WIFE 2 ANTENAS', 1, None, 30.00, None, None),
    ('INV-297', 'DISCO CRUCIAL 1 TB SSD', 0, None, 120.00, None, 'BRIAN')
]


def _poblar_descripciones_faltantes(cursor) -> int:
    """Pre-calcula y persiste en SQLite la descripción corta de artículos que aún no la tengan."""
    cursor.execute("SELECT id, nombre, descripcion FROM productos WHERE descripcion IS NULL OR TRIM(descripcion) = ''")
    faltantes = cursor.fetchall()
    if not faltantes:
        return 0
    actualizaciones = []
    for row in faltantes:
        desc = obtener_descripcion_caracteristicas({"nombre": row["nombre"], "descripcion": ""})
        actualizaciones.append((desc, row["id"]))
    cursor.executemany("UPDATE productos SET descripcion = ? WHERE id = ?", actualizaciones)
    return len(actualizaciones)


def seed_database():
    """Inicializa tablas/datos si hace falta, con vía rápida de lectura sin escrituras en arranques posteriores."""
    global _CACHE_TASAS, _CACHE_PRODUCTOS
    db_path = obtener_ruta_db()
    if os.path.exists(db_path) and os.path.getsize(db_path) > 4096:
        conn_fast = sqlite3.connect(db_path, timeout=10.0)
        conn_fast.row_factory = sqlite3.Row
        try:
            cur_f = conn_fast.cursor()
            cur_f.execute(
                "SELECT COUNT(*) AS total, "
                "SUM(CASE WHEN descripcion IS NULL OR TRIM(descripcion) = '' THEN 1 ELSE 0 END) AS sin_desc "
                "FROM productos"
            )
            stats_row = cur_f.fetchone()
            cur_f.execute(
                "SELECT clave, valor FROM configuracion WHERE clave IN ('tasa_bcv', 'tasa_reposicion')"
            )
            cfg_rows = cur_f.fetchall()
            cfg = {r["clave"]: float(r["valor"]) for r in cfg_rows if r["valor"] is not None}
            if (
                stats_row
                and int(stats_row["total"] or 0) > 0
                and int(stats_row["sin_desc"] or 0) == 0
                and "tasa_bcv" in cfg
                and "tasa_reposicion" in cfg
            ):
                _CACHE_TASAS = {
                    "tasa_bcv": cfg["tasa_bcv"],
                    "tasa_reposicion": cfg["tasa_reposicion"],
                }
                _CACHE_PRODUCTOS = None
                return
        except sqlite3.Error:
            pass
        finally:
            conn_fast.close()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        cantidad INTEGER NOT NULL DEFAULT 0,
        precio_detal_usd REAL NULL,
        precio_descuento_usd REAL NULL,
        costo_usd REAL NULL,
        ubicacion_nota TEXT NULL,
        descripcion TEXT NULL,
        activo INTEGER NOT NULL DEFAULT 1,
        fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Migración segura si existía tabla previa sin columna descripcion
    try:
        cursor.execute("ALTER TABLE productos ADD COLUMN descripcion TEXT NULL;")
    except sqlite3.OperationalError:
        pass

    # Índices para búsquedas y ordenamiento instantáneo (Stock primero A-Z)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_productos_activo_id ON productos(activo, id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_productos_activo_cant ON productos(activo, cantidad);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_productos_orden ON productos(activo, cantidad, nombre);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_productos_sku ON productos(sku);")

    # Verificar esquema de configuracion para garantizar (clave TEXT PRIMARY KEY, valor REAL NOT NULL)
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='configuracion';")
    existe_cfg = cursor.fetchone() is not None
    if existe_cfg:
        cursor.execute("PRAGMA table_info(configuracion);")
        cols = {row["name"]: row["type"].upper() for row in cursor.fetchall()}
        if cols.get("valor") != "REAL" or len(cols) != 2:
            bcv_val = TASA_BCV_DEFECTO
            repo_val = TASA_REPOSICION_DEFECTO
            try:
                cursor.execute("SELECT clave, valor FROM configuracion;")
                for r in cursor.fetchall():
                    if r["clave"] == "tasa_bcv":
                        bcv_val = float(r["valor"])
                    elif r["clave"] == "tasa_reposicion":
                        repo_val = float(r["valor"])
            except Exception:
                pass
            cursor.execute("DROP TABLE configuracion;")
            cursor.execute("""
            CREATE TABLE configuracion (
                clave TEXT PRIMARY KEY,
                valor REAL NOT NULL
            );
            """)
            cursor.execute("INSERT INTO configuracion (clave, valor) VALUES ('tasa_bcv', ?);", (bcv_val,))
            cursor.execute("INSERT INTO configuracion (clave, valor) VALUES ('tasa_reposicion', ?);", (repo_val,))
        else:
            cursor.execute("DELETE FROM configuracion WHERE typeof(valor) NOT IN ('real', 'integer');")
            cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('tasa_bcv', ?);", (TASA_BCV_DEFECTO,))
            cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('tasa_reposicion', ?);", (TASA_REPOSICION_DEFECTO,))
    else:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS configuracion (
            clave TEXT PRIMARY KEY,
            valor REAL NOT NULL
        );
        """)
        cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('tasa_bcv', ?);", (TASA_BCV_DEFECTO,))
        cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('tasa_reposicion', ?);", (TASA_REPOSICION_DEFECTO,))

    cursor.execute("SELECT COUNT(*) as total FROM productos;")
    total_existente = cursor.fetchone()["total"]

    if total_existente == 0:
        cursor.executemany("""
        INSERT INTO productos (sku, nombre, cantidad, precio_detal_usd, precio_descuento_usd, costo_usd, ubicacion_nota)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """, PRODUCTOS_INICIALES)

    _poblar_descripciones_faltantes(cursor)

    conn.commit()
    conn.close()
    invalidar_cache(invalidar_productos=True, invalidar_tasas=True)


inicializar_bd = seed_database


def formatear_usd(monto: Optional[float]) -> str:
    """Formatea un monto en dólares ($XX.XX) o devuelve 'Sin precio' si es nulo."""
    if monto is None:
        return "Sin precio"
    return f"${float(monto):,.2f}"


def formatear_bs(monto: Optional[float]) -> str:
    """Formatea un monto en bolívares (Bs. XX.XXX,XX) o devuelve 'Sin precio' si es nulo."""
    if monto is None:
        return "Sin precio"
    num_str = f"{float(monto):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"Bs. {num_str}"


def calcular_precios_producto(p: Dict[str, Any], tasa_bcv: float, tasa_reposicion: float) -> Dict[str, Any]:
    """
    Calcula al vuelo el arbitraje cambiario del negocio para un producto:
    - precio_base: precio_descuento_usd si existe y > 0; si no, precio_detal_usd.
    - monto_bs_reposicion = precio_base * tasa_reposicion
    - precio_venta_bcv_usd = monto_bs_reposicion / tasa_bcv
    - monto_bs_bcv_directo = precio_detal_usd * tasa_bcv (o precio_base * tasa_bcv si detal es nulo)
    """
    raw_desc = p.get("precio_descuento_usd")
    raw_detal = p.get("precio_detal_usd")

    precio_desc = float(raw_desc) if (raw_desc is not None and float(raw_desc) > 0) else None
    precio_detal = float(raw_detal) if (raw_detal is not None and float(raw_detal) > 0) else None

    if precio_desc is not None:
        precio_base = precio_desc
        origen_base = "Lista/Desc."
    elif precio_detal is not None:
        precio_base = precio_detal
        origen_base = "Detal"
    else:
        return {
            "tiene_precio": False,
            "origen_base": None,
            "precio_base": None,
            "monto_bs_reposicion": None,
            "precio_venta_bcv_usd": None,
            "monto_bs_bcv_directo": None,
            "precio_base_str": "Sin precio",
            "precio_venta_bcv_usd_str": "Sin precio",
            "monto_bs_reposicion_str": "Sin precio",
            "monto_bs_bcv_directo_str": "Sin precio",
        }

    t_bcv = float(tasa_bcv) if (tasa_bcv is not None and float(tasa_bcv) > 0) else TASA_BCV_DEFECTO
    t_repo = float(tasa_reposicion) if (tasa_reposicion is not None and float(tasa_reposicion) > 0) else TASA_REPOSICION_DEFECTO

    monto_bs_reposicion = precio_base * t_repo
    precio_venta_bcv_usd = monto_bs_reposicion / t_bcv
    monto_bs_bcv_directo = (precio_detal * t_bcv) if precio_detal is not None else (precio_base * t_bcv)

    return {
        "tiene_precio": True,
        "origen_base": origen_base,
        "precio_base": precio_base,
        "monto_bs_reposicion": monto_bs_reposicion,
        "precio_venta_bcv_usd": precio_venta_bcv_usd,
        "monto_bs_bcv_directo": monto_bs_bcv_directo,
        "precio_base_str": formatear_usd(precio_base),
        "precio_venta_bcv_usd_str": formatear_usd(precio_venta_bcv_usd),
        "monto_bs_reposicion_str": formatear_bs(monto_bs_reposicion),
        "monto_bs_bcv_directo_str": formatear_bs(monto_bs_bcv_directo),
    }


_CATEGORIAS_DESC = [
    (("ADAPTADOR",), "Adaptador de señal"),
    (("CABLE",), "Cable de conexión"),
    (("AUDIFONO", "AUDÍFONO"), "Audio personal"),
    (("ROUTER", "MODEN", "MODEM"), "Red e Internet Wi-Fi"),
    (("BOBINA",), "Bobina de cableado"),
    (("CONECTOR", "RJ45"), "Conector de red"),
    (("SWITCH",), "Switch de red"),
    (("CAMARA", "CÁMARA"), "Cámara de seguridad"),
    (("CORNETA", "BARRA DE SONIDO", "PARLANTE"), "Sistema de audio"),
    (("PENDRIVE", "MEMORIA", "RAM"), "Memoria / Almacenamiento"),
    (("DISCO", "SSD", "HDD"), "Unidad de almacenamiento"),
    (("MOUSE",), "Mouse periférico"),
    (("TECLADO",), "Teclado periférico"),
    (("COMBO",), "Combo de periféricos"),
    (("FUENTE",), "Fuente de poder"),
    (("BATERIA", "BATERÍA", "UPS"), "Respaldo de energía"),
    (("REGULADOR", "PROTECTOR"), "Protección eléctrica"),
    (("BASE", "SOPORTE"), "Soporte / Montaje"),
    (("WEBCAM",), "Cámara web"),
    (("MICROFONO", "MICRÓFONO"), "Micrófono"),
    (("CARGADOR",), "Cargador / Alimentación"),
    (("MONITOR", "PANTALLA"), "Monitor / Pantalla"),
    (("TARJETA",), "Tarjeta / Interfaz"),
    (("HUB", "MULTIPUERTO"), "Concentrador de puertos"),
]

_TAGS_TECNICOS = [
    ("HDMI A VGA", "Conversión HDMI a VGA"),
    ("DISPLAY PORT A VGA", "DisplayPort a VGA"),
    ("DISPLAYPORT A VGA", "DisplayPort a VGA"),
    ("DISPLAYPORT A HDMI", "DisplayPort a HDMI"),
    ("DISPLAY PORT A HDMI", "DisplayPort a HDMI"),
    ("DISPLAYPORT", "Interfaz DisplayPort"),
    ("DISPLAY PORT", "Interfaz DisplayPort"),
    ("HDMI", "Video HDMI"),
    ("VGA", "Video VGA"),
    ("DVI", "Video DVI"),
    ("3RCA", "Audio/Video 3RCA"),
    ("RCA", "Video RCA"),
    ("OTG", "Función OTG"),
    ("TIPO C", "Conector USB-C"),
    ("USB C", "Conector USB-C"),
    ("USB", "Interfaz USB"),
    ("SATA", "Bus SATA 3.0"),
    ("RJ45", "Ethernet RJ45"),
    ("CAT.6", "Categoría 6"),
    ("CAT 6", "Categoría 6"),
    ("CAT. 6", "Categoría 6"),
    ("CAT.5E", "Categoría 5e"),
    ("CAT. 5E", "Categoría 5e"),
    ("CAT5", "Categoría 5"),
    ("5E", "Categoría 5e"),
    ("BLUETOOTH", "Bluetooth"),
    ("DUAL BAND", "Doble banda"),
    ("WIFE", "Conectividad Wi-Fi"),
    ("WIFI", "Conectividad Wi-Fi"),
    ("INALAMBRICO", "Inalámbrico"),
    ("INALAMBRICOS", "Inalámbrico"),
    ("ALAMBRICO", "Conexión por cable"),
    ("ALAMBRICOS", "Conexión por cable"),
    ("MICROFONO", "Con micrófono"),
    ("GAMER", "Línea Gamer"),
    ("GAMING", "Línea Gamer"),
    ("RGB", "Iluminación RGB"),
    ("4K", "Soporte 4K UHD"),
    ("2K", "Resolución 2K"),
    ("SSD", "Estado sólido SSD"),
    ("DDR4", "DDR4"),
    ("DDR3", "DDR3"),
    ("TWS", "Estéreo TWS"),
    ("EXTERIOR", "Uso exterior"),
    ("INTERIOR", "Uso interior"),
]

_MARCAS_CONOCIDAS = [
    "SPIDERTEC", "SPIDETREC", "GENIUS", "REDRAGON", "LOGITECH", "TP LINK", "TP-LINK",
    "MERCUSYS", "KINGSTON", "CRUCIAL", "UNNO TECNO", "UNNO TKNO", "CORSAIR", "EVGA",
    "GAMEMAX", "ONIKUMA", "BEGPROD", "NEXCOM", "SAMSUM", "SAMSUNG",
]


def obtener_descripcion_caracteristicas(p: Dict[str, Any]) -> str:
    """
    Retorna la descripción personalizada del artículo o genera automáticamente
    un resumen corto con categoría, especificaciones técnicas y marca (máx. ~95 caracteres).
    """
    desc_manual = (p.get("descripcion") or "").strip()
    if desc_manual:
        return desc_manual[:95] + ("..." if len(desc_manual) > 95 else "")

    nombre_up = (p.get("nombre") or "").upper()
    partes = []

    cat = "Hardware / Accesorio"
    for claves, etiqueta in _CATEGORIAS_DESC:
        if any(k in nombre_up for k in claves):
            cat = etiqueta
            break
    partes.append(cat)

    # Extraer medidas relevantes (mts, GB, TB, Mbps, W, ")
    medidas = re.findall(r'\b\d+(?:[.,]\d+)?\s*(?:MTS?\.?|MT\.?|GB|TB|MBPS|W|HZ|AH)\b|\b\d{2}"', nombre_up)
    for m in medidas[:2]:
        limpia = m.replace(".", "").strip()
        if limpia and limpia not in partes:
            partes.append(limpia)

    # Extraer especificaciones clave sin duplicar conceptos
    specs_agregadas = 0
    for token, desc_token in _TAGS_TECNICOS:
        if token in nombre_up and desc_token not in partes:
            texto_acum = " ".join(partes).upper()
            primera_palabra = desc_token.split()[-1].upper()
            if primera_palabra in texto_acum:
                continue
            partes.append(desc_token)
            specs_agregadas += 1
            if specs_agregadas >= 2:
                break

    if "CON AUDIO" in nombre_up and "AUDIO" not in " ".join(partes).upper():
        partes.append("Salida de audio")

    for marca in _MARCAS_CONOCIDAS:
        if marca in nombre_up:
            m_clean = "Spidertec" if marca == "SPIDETREC" else ("Samsung" if marca == "SAMSUM" else ("Unno Tecno" if marca == "UNNO TKNO" else marca.title()))
            partes.append(f"Marca {m_clean}")
            break

    resumen = " • ".join(partes)
    return resumen[:95] + ("..." if len(resumen) > 95 else "")


def _construir_sort_key(d: Dict[str, Any]):
    return (0 if (d.get("cantidad") or 0) > 0 else 1, (d.get("nombre") or "").strip().upper(), d.get("id") or 0)


def _obtener_catalogo_en_memoria() -> List[Dict[str, Any]]:
    """Carga una única vez los productos activos en RAM, pre-calculando búsqueda, descripción y orden A-Z."""
    global _CACHE_PRODUCTOS
    if _CACHE_PRODUCTOS is not None:
        return _CACHE_PRODUCTOS

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM productos WHERE activo = 1")
    rows = cursor.fetchall()
    conn.close()

    productos: List[Dict[str, Any]] = []
    for row in rows:
        d = dict(row)
        d["cantidad"] = int(d.get("cantidad") or 0)
        desc_corta = obtener_descripcion_caracteristicas(d)
        d["descripcion_corta"] = desc_corta
        d["_sort_key"] = _construir_sort_key(d)
        d["_search_blob"] = (
            f"{d.get('sku') or ''} {d.get('nombre') or ''} "
            f"{d.get('ubicacion_nota') or ''} {d.get('descripcion') or ''} {desc_corta}"
        ).lower()
        productos.append(d)

    productos.sort(key=lambda x: x["_sort_key"])
    _CACHE_PRODUCTOS = productos
    return _CACHE_PRODUCTOS


def obtener_productos(filtro: str = "", solo_stock: bool = False, solo_agotados: bool = False) -> List[Dict[str, Any]]:
    """
    Filtra instantáneamente en memoria RAM por SKU, Nombre, Ubicación o Descripción (< 0.2 ms).
    Orden garantizado: Primero artículos con stock (> 0) A-Z, luego agotados (= 0) A-Z.
    """
    catalogo = _obtener_catalogo_en_memoria()
    filtro_norm = (filtro or "").strip().lower()
    terminos = filtro_norm.split() if filtro_norm else []

    if not terminos and not solo_stock and not solo_agotados:
        return list(catalogo)

    resultados: List[Dict[str, Any]] = []
    for p in catalogo:
        cant = p["cantidad"]
        if solo_stock and cant <= 0:
            continue
        if solo_agotados and cant != 0:
            continue
        if terminos:
            blob = p["_search_blob"]
            if not all(t in blob for t in terminos):
                continue
        resultados.append(p)
    return resultados


def obtener_producto_por_id(producto_id: int) -> Optional[Dict[str, Any]]:
    """Devuelve los datos de un producto específico desde la caché en memoria RAM."""
    for p in _obtener_catalogo_en_memoria():
        if p["id"] == producto_id:
            return p
    return None


def agregar_producto(sku: str, nombre: str, cantidad: int, precio_detal: Optional[float],
                     precio_descuento: Optional[float], costo: Optional[float],
                     ubicacion: Optional[str], descripcion: Optional[str] = None) -> bool:
    """Inserta un nuevo artículo en la base de datos e invalida la caché de productos."""
    conn = get_connection()
    cursor = conn.cursor()
    sku_norm = sku.strip().upper()
    nombre_norm = nombre.strip().upper()
    ubicacion_norm = ubicacion.strip() if ubicacion and ubicacion.strip() else None
    desc_norm = descripcion.strip() if descripcion and descripcion.strip() else None

    try:
        cursor.execute("DELETE FROM productos WHERE sku = ? AND activo = 0", (sku_norm,))
        cursor.execute("""
        INSERT INTO productos (sku, nombre, cantidad, precio_detal_usd, precio_descuento_usd, costo_usd, ubicacion_nota, descripcion)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (sku_norm, nombre_norm, cantidad, precio_detal, precio_descuento, costo, ubicacion_norm, desc_norm))
        conn.commit()
        invalidar_cache(invalidar_productos=True)
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def actualizar_producto(producto_id: int, sku: str, nombre: str, cantidad: int, precio_detal: Optional[float],
                        precio_descuento: Optional[float], costo: Optional[float],
                        ubicacion: Optional[str], descripcion: Optional[str] = None) -> bool:
    """Actualiza los datos de un artículo existente e invalida la caché de productos."""
    conn = get_connection()
    cursor = conn.cursor()
    sku_norm = sku.strip().upper()
    nombre_norm = nombre.strip().upper()
    ubicacion_norm = ubicacion.strip() if ubicacion and ubicacion.strip() else None
    desc_norm = descripcion.strip() if descripcion and descripcion.strip() else None

    try:
        cursor.execute("""
        UPDATE productos 
        SET sku = ?, nombre = ?, cantidad = ?, precio_detal_usd = ?, precio_descuento_usd = ?, costo_usd = ?, ubicacion_nota = ?, descripcion = ?, fecha_actualizacion = CURRENT_TIMESTAMP
        WHERE id = ?;
        """, (sku_norm, nombre_norm, cantidad, precio_detal, precio_descuento, costo, ubicacion_norm, desc_norm, producto_id))
        conn.commit()
        invalidar_cache(invalidar_productos=True)
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def actualizar_solo_cantidad(producto_id: int, nueva_cantidad: int) -> bool:
    """Actualiza stock en SQLite y en caliente dentro de la caché RAM sin releer el disco."""
    cant_segura = max(0, int(nueva_cantidad))
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE productos SET cantidad = ?, fecha_actualizacion = CURRENT_TIMESTAMP WHERE id = ?",
        (cant_segura, producto_id)
    )
    conn.commit()
    conn.close()

    if _CACHE_PRODUCTOS is not None:
        for p in _CACHE_PRODUCTOS:
            if p["id"] == producto_id:
                p["cantidad"] = cant_segura
                p["_sort_key"] = _construir_sort_key(p)
                break
        _CACHE_PRODUCTOS.sort(key=lambda x: x["_sort_key"])
    return True


def eliminar_producto(producto_id: int) -> bool:
    """Elimina un producto del inventario e invalida la caché en RAM."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM productos WHERE id = ?", (producto_id,))
    conn.commit()
    conn.close()
    invalidar_cache(invalidar_productos=True)
    return True


def obtener_siguiente_sku() -> str:
    """Genera la siguiente sugerencia de SKU (ej. INV-298) leyendo desde la caché RAM."""
    max_num = 0
    for p in _obtener_catalogo_en_memoria():
        sku = (p.get("sku") or "").upper()
        if not sku.startswith("INV-"):
            continue
        try:
            partes = sku.split("-")
            if len(partes) > 1 and partes[1].isdigit():
                num = int(partes[1])
                if num > max_num:
                    max_num = num
        except Exception:
            pass
    return f"INV-{max_num + 1:03d}"


def obtener_tasas() -> Dict[str, float]:
    """Obtiene la Tasa BCV y el Multiplicador Global usando caché en memoria RAM."""
    global _CACHE_TASAS
    if _CACHE_TASAS is not None:
        return dict(_CACHE_TASAS)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT clave, valor FROM configuracion WHERE clave IN ('tasa_bcv', 'tasa_reposicion')")
    rows = cursor.fetchall()
    conn.close()
    datos = {row["clave"]: float(row["valor"]) for row in rows}
    _CACHE_TASAS = {
        "tasa_bcv": datos.get("tasa_bcv", TASA_BCV_DEFECTO),
        "tasa_reposicion": datos.get("tasa_reposicion", TASA_REPOSICION_DEFECTO),
    }
    return dict(_CACHE_TASAS)


def actualizar_tasas(tasa_bcv: float, tasa_reposicion: float) -> bool:
    """Actualiza Tasa BCV y Multiplicador Global en SQLite y actualiza caché RAM."""
    global _CACHE_TASAS
    if tasa_bcv <= 0 or tasa_reposicion <= 0:
        return False
    bcv_f = float(tasa_bcv)
    repo_f = float(tasa_reposicion)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('tasa_bcv', ?)", (bcv_f,))
    cursor.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('tasa_reposicion', ?)", (repo_f,))
    conn.commit()
    conn.close()
    _CACHE_TASAS = {"tasa_bcv": bcv_f, "tasa_reposicion": repo_f}
    return True


def obtener_resumen_estadisticas() -> Dict[str, Any]:
    """Calcula totales globales iterando directamente sobre la caché RAM (< 0.1 ms)."""
    tasas = obtener_tasas()
    t_bcv = tasas["tasa_bcv"]
    t_repo = tasas["tasa_reposicion"]

    catalogo = _obtener_catalogo_en_memoria()
    total_items = len(catalogo)
    total_unidades = 0
    items_con_stock = 0
    valor_base_usd = 0.0

    for p in catalogo:
        cant = p["cantidad"]
        total_unidades += cant
        if cant > 0:
            items_con_stock += 1
            raw_desc = p.get("precio_descuento_usd")
            raw_detal = p.get("precio_detal_usd")
            precio = (
                float(raw_desc)
                if (raw_desc is not None and float(raw_desc) > 0)
                else (float(raw_detal) if (raw_detal is not None and float(raw_detal) > 0) else 0.0)
            )
            valor_base_usd += cant * precio

    items_agotados = total_items - items_con_stock
    valor_bs_reposicion = valor_base_usd * t_repo
    valor_bcv_ajustado_usd = (valor_bs_reposicion / t_bcv) if t_bcv > 0 else 0.0

    return {
        "total_items": total_items,
        "total_unidades": total_unidades,
        "items_con_stock": items_con_stock,
        "items_agotados": items_agotados,
        "valor_base_usd": valor_base_usd,
        "valor_bs_reposicion": valor_bs_reposicion,
        "valor_bcv_ajustado_usd": valor_bcv_ajustado_usd,
        "valor_estimado_usd": valor_bcv_ajustado_usd,
    }


def guardar_tasas_cache(tasa_bcv: float, tasa_paralelo: float, fecha: str = ""):
    """Sincroniza tasas desde API/caché hacia configuracion (clave TEXT, valor REAL)."""
    global _ultima_fecha_sync
    if fecha:
        _ultima_fecha_sync = fecha
    actualizar_tasas(float(tasa_bcv), float(tasa_paralelo))


def obtener_tasas_cache() -> Dict[str, Any]:
    """Obtiene las tasas configuradas en SQLite en formato compatible con dolar_service y UI."""
    tasas = obtener_tasas()
    return {
        "bcv": tasas["tasa_bcv"],
        "paralelo": tasas["tasa_reposicion"],
        "tasa_bcv": tasas["tasa_bcv"],
        "tasa_reposicion": tasas["tasa_reposicion"],
        "fecha": _ultima_fecha_sync,
        "online": False,
        "mensaje": f"Tasas SQLite ({_ultima_fecha_sync})"
    }


if __name__ == "__main__":
    seed_database()
    resumen = obtener_resumen_estadisticas()
    tasas = obtener_tasas()
    print("Base de datos optimizada e inicializada con éxito.")
    print(f"Ruta DB: {obtener_ruta_db()}")
    print(f"Tasa BCV: {tasas['tasa_bcv']} | Tasa Reposición: {tasas['tasa_reposicion']}")
    print(f"Total productos: {resumen['total_items']}")
    print(f"Total unidades en stock: {resumen['total_unidades']}")
    print(f"Productos con stock: {resumen['items_con_stock']}")
    print(f"Productos agotados: {resumen['items_agotados']}")
    print(f"Valor Base USD: ${resumen['valor_base_usd']:,.2f} | Valor Ajustado BCV: ${resumen['valor_bcv_ajustado_usd']:,.2f}")


PLANTILLA_CSV_TEXTO = """sku,nombre,cantidad,precio_detal_usd,precio_descuento_usd,costo_usd,ubicacion_nota
INV-300,MEMORIA RAM DDR4 16GB CORSAIR,5,45.00,40.00,32.00,DEPOSITO 1
INV-301,DISCO SOLIDO SSD 1TB KINGSTON,3,65.00,60.00,45.00,BRIAN
INV-302,FUENTE DE PODER 600W EVGA,2,55.00,,38.00,ESTANTE A
INV-303,TECLADO GAMER MECANICO RGB,4,35.00,30.00,22.50,DEPOSITO 2
"""


def obtener_texto_plantilla_csv() -> str:
    """Retorna el contenido de texto estándar de la plantilla CSV."""
    return PLANTILLA_CSV_TEXTO


def generar_archivo_plantilla_csv() -> str:
    """Crea y guarda el archivo plantilla_inventario.csv en la carpeta exportaciones y retorna su ruta."""
    export_dir = os.path.join(get_writable_app_dir(), "exportaciones")
    os.makedirs(export_dir, exist_ok=True)
    ruta = os.path.join(export_dir, "plantilla_inventario.csv")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(PLANTILLA_CSV_TEXTO)
    return ruta


def importar_productos_desde_csv(contenido_texto_o_ruta: str) -> Dict[str, Any]:
    """
    Importa artículos a SQLite desde un archivo o texto plano (CSV / SVG / TXT).
    Soporta separadores por coma (,), punto y coma (;) o tabulador (\t).
    Si el SKU existe, actualiza sus datos; si es nuevo o vacío, genera correlativo.
    """
    import csv
    import io

    contenido = contenido_texto_o_ruta.strip()
    if os.path.isfile(contenido):
        for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
            try:
                with open(contenido, "r", encoding=enc) as f:
                    contenido = f.read()
                break
            except Exception:
                continue

    lineas = [l for l in contenido.splitlines() if l.strip()]
    if not lineas:
        return {"exito": False, "mensaje": "El archivo o texto está vacío", "nuevos": 0, "actualizados": 0, "total": 0}

    primera_linea = lineas[0]
    delimitador = ";" if ";" in primera_linea else ("\t" if "\t" in primera_linea else ",")
    reader = csv.reader(io.StringIO(contenido), delimiter=delimitador)
    filas = list(reader)
    if not filas:
        return {"exito": False, "mensaje": "No se encontraron filas válidas", "nuevos": 0, "actualizados": 0, "total": 0}

    encabezados = [c.strip().lower() for c in filas[0]]
    tiene_encabezado = any(k in encabezados for k in ("sku", "codigo", "código", "nombre", "producto", "cantidad", "stock", "precio"))
    filas_datos = filas[1:] if tiene_encabezado else filas

    conn = get_connection()
    cur = conn.cursor()
    nuevos = 0
    actualizados = 0
    errores = []

    def parse_float(val):
        if val is None:
            return None
        v = str(val).strip().replace("$", "").replace(" ", "").replace(",", ".")
        try:
            return float(v) if v else None
        except Exception:
            return None

    def parse_int(val):
        if val is None:
            return 0
        v = str(val).strip().replace(" ", "")
        try:
            return int(float(v)) if v else 0
        except Exception:
            return 0

    col_sku, col_nombre, col_cant, col_detal, col_desc, col_costo, col_ubic = 0, 1, 2, 3, 4, 5, 6
    if tiene_encabezado:
        for idx, col in enumerate(encabezados):
            if col in ("sku", "codigo", "código"): col_sku = idx
            elif col in ("nombre", "producto", "descripcion", "artículo", "articulo"): col_nombre = idx
            elif col in ("cantidad", "stock", "unidades", "existencia"): col_cant = idx
            elif "detal" in col or col in ("precio", "precio_usd", "valor"): col_detal = idx
            elif "desc" in col: col_desc = idx
            elif "costo" in col: col_costo = idx
            elif "ubic" in col or "nota" in col: col_ubic = idx

    for fila in filas_datos:
        if not fila or not any(str(c).strip() for c in fila):
            continue

        def get_val(col_idx):
            return fila[col_idx].strip() if col_idx < len(fila) else ""

        nombre = get_val(col_nombre)
        if not nombre:
            continue

        raw_sku = get_val(col_sku).upper()
        cant = parse_int(get_val(col_cant))
        detal = parse_float(get_val(col_detal))
        desc = parse_float(get_val(col_desc))
        costo = parse_float(get_val(col_costo))
        ubic = get_val(col_ubic) or None

        if not raw_sku:
            cur.execute("SELECT sku FROM productos WHERE activo = 1 AND sku LIKE 'INV-%'")
            rows = cur.fetchall()
            max_num = 0
            for r in rows:
                try:
                    num = int(r["sku"].split("-")[1])
                    if num > max_num: max_num = num
                except Exception: pass
            raw_sku = f"INV-{max_num + 1:03d}"

        cur.execute("SELECT id FROM productos WHERE sku = ?", (raw_sku,))
        existente = cur.fetchone()

        if existente:
            cur.execute("""
            UPDATE productos 
            SET nombre = ?, cantidad = ?, precio_detal_usd = ?, precio_descuento_usd = ?, costo_usd = ?, ubicacion_nota = ?, activo = 1, fecha_actualizacion = CURRENT_TIMESTAMP
            WHERE id = ?
            """, (nombre.upper(), cant, detal, desc, costo, ubic, existente["id"]))
            actualizados += 1
        else:
            cur.execute("""
            INSERT INTO productos (sku, nombre, cantidad, precio_detal_usd, precio_descuento_usd, costo_usd, ubicacion_nota, activo)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """, (raw_sku, nombre.upper(), cant, detal, desc, costo, ubic))
            nuevos += 1

    conn.commit()
    conn.close()
    invalidar_cache(invalidar_productos=True)
    return {"exito": True, "nuevos": nuevos, "actualizados": actualizados, "total": nuevos + actualizados, "errores": errores}
