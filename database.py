"""
database.py - Módulo de persistencia SQLite optimizado para Móvil (Android APK) y PC
Maneja la inicialización, índices de velocidad, los 297 productos iniciales y consultas CRUD.
"""

import sqlite3
import os
from typing import List, Dict, Any, Optional

DB_NAME = "inventario.db"


def get_writable_app_dir() -> str:
    """
    Obtiene un directorio 100% escribible y persistente tanto en Android APK como en PC.
    En Android/iOS (Flet), crea y utiliza FLET_APP_STORAGE_DATA para persistencia segura.
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


def get_db_path() -> str:
    """Obtiene la ruta de la base de datos compatible tanto con PC como con Android APK."""
    return os.path.join(get_writable_app_dir(), DB_NAME)


def get_connection():
    """Retorna una conexión a SQLite optimizada con row_factory."""
    conn = sqlite3.connect(get_db_path(), timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


PRODUCTOS_INICIALES = [
    ('INV-001', 'ADAPTADOR HDMI A VGA SPIDERTEC', 9, 12.01, 10.0, None, None),
    ('INV-002', 'ADAPTADOR DISPLAY PORT A VGA', 5, 12.01, 10.0, None, None),
    ('INV-003', 'ADAPTADOR HDMI A VGA CON AUDIO', 1, 12.01, 10.0, None, None),
    ('INV-004', 'CABLE DISPLAYPORT A HDMI', 0, 8.0, 7.0, None, None),
    ('INV-005', 'CABLE DISPLAYPORT A DISPLAYPORT GENERICO', 0, None, None, None, None),
    ('INV-006', 'CABLE DISPLAYPORT A DISPLAYPORT SPIDETREC', 11, 14.41, 12.0, 2.15, None),
    ('INV-007', 'ADAPTADOR DISPLAYPORT A HDMI', 0, None, 8.0, None, None),
    ('INV-008', 'ADAPTADOR RECEPTOR BLUETOOTH PARA CORNETA', 2, 8.41, 7.0, 3.0, None),
    ('INV-009', 'ADAPTADOR RECEPTOR BLUETOOTH spidetrec', 24, 8.41, 7.0, 1.15, None),
    ('INV-010', 'ADAPTADOR OTG USB AY USB C UNNO TECNO', 3, 8.41, 7.0, None, None),
    ('INV-011', 'ADAPTADOR OTG USB A TIPO C SAMSUM', 1, 8.41, 7.0, None, None),
    ('INV-012', 'ADAPTADOR DISPLAYPORT A VGA', 0, 9.0, 7.0, None, None),
    ('INV-013', 'AUDIFONOS GENIUS HS G710V CON MICROFONO OMNIDIRECIONAL USB', 2, 48.05, 40.0, 33.97, '1 DEP.*'),
    ('INV-014', 'AUDIFONOS GENIUS GX 580 CON MICROFONO', 0, 41.0, 25.0, None, None),
    ('INV-015', 'AUDIFONO GAMER LAMIA COLOR NEGRO H320RGB1', 0, None, None, 18.85, None),
    ('INV-016', 'AUDIFONO GAMER ONIKUMA K10', 0, None, None, None, None),
    ('INV-017', 'AUDIFONO DEVIL STN-29', 1, 12.01, 10.0, None, None),
    ('INV-018', 'AUDIFONO ALAMBRICO 2K GAME QKZ', 1, 12.01, 10.0, None, None),
    ('INV-019', 'AUDIFONO GAMER CRONUS RGB SONIDO ENVOLVENTE H211', 0, None, 35.0, None, None),
    ('INV-020', 'AUDIFONO ALAMBRICO GENIUS CON MICROFONO HS 300N', 0, None, 15.0, 39.1, None),
    ('INV-021', 'AUDIFONO ALAMBRICO CON MICROFONO INTEGRADO LOGITECH USB', 1, 42.04, 35.0, None, None),
    ('INV-022', 'AUDIFONOS ALAMBRICOS', 7, 8.41, 7.0, None, None),
    ('INV-023', 'AUDIFONOS INALAMBRICO BEATS STN-16 CASCO', 1, 14.41, 12.0, None, None),
    ('INV-024', 'AUDIFONO IRE PRO REDRAGON TRI-MODE CABLE TIPO BLUETOOTH', 0, 50.0, 55.0, None, 'Brian'),
    ('INV-025', 'AUDIFONOS INALAMBRICOS F9-5 TWS CON POWER BANK', 2, 8.41, 7.0, 24.85, None),
    ('INV-026', 'AUDIFONOS GAMER HYLAS NEGRO', 2, 42.04, 35.0, 15.76, None),
    ('INV-027', 'AUDIFONOS GAMER HYLAS BLANCO', 0, 49.0, 35.0, 13.95, None),
    ('INV-028', 'AUDIFONO CON MICROFONO GAMEMAX GAMING HG200 7 COLORES', 1, 36.04, 30.0, None, None),
    ('INV-029', 'AUDIFONOS M10 INALAMBRICOS V53 DURACION 5 HORAS', 0, 10.0, 8.0, None, None),
    ('INV-030', 'AUDIFONOS UNNO TKNO ZENMAX INALAMBRICO CON MICROFONO', 1, 48.05, 40.0, None, 'BRIAN'),
    ('INV-031', 'AUDIFONOS INALAMBRICO CON MICROFONO ZEN PRO', 1, 36.04, 30.0, None, 'BRIAN'),
    ('INV-032', 'AUDIFONO DEVIL STN-25', 1, 14.41, 12.0, None, None),
    ('INV-033', 'AUDIFONOS GAMER ARES RGB REDRAGON NEGRO MOD. H120', 2, 42.04, 35.0, None, None),
    ('INV-034', 'AUDIFONOS CON MICROFONO ALAMBRICO HS02B GENIUS', 0, 15.0, 12.0, 50.0, None),
    ('INV-035', 'BASE PARA TV LED FIJA 42"', 0, None, 20.0, None, None),
    ('INV-036', 'BOBINA NEXCOM 5E EXTERIOR', 0, None, None, None, None),
    ('INV-037', 'BOBINA BEGPROD CAT. 5E EXTERIOR', 0, None, None, None, None),
    ('INV-038', 'BOBINA BEGPROD CAT5 INTERIOR DE 100 MTS, AZUL', 0, None, None, None, None),
    ('INV-039', 'BOBINA COMPLETA UTP CAT.6 STC CARRETE EXTER, 0,90 MTS.', 1, 96.1, 80.0, None, None),
    ('INV-040', 'BASE GAMEPAD PARA CECULAR CON JOSTICK', 1, 9.61, 8.0, None, None),
    ('INV-041', 'BATERIA DE 14W PARA UPS', 0, None, 15.0, None, None),
    ('INV-042', 'CAMARA WIFE ESPIA A9', 1, 24.02, 20.0, 26.57, None),
    ('INV-043', 'BARRA DE SONIDO REDRAGON DARKNET M ODGS570', 0, None, 40.0, None, 'BRIAN'),
    ('INV-044', 'BARRA DE SONIDO GAMING GENIUS', 0, 43.0, 30.0, None, None),
    ('INV-045', 'CORNETA PORTATIL ASTRA 45W BLUETOOTH TWS IPX5 RGB', 0, None, 60.0, None, None),
    ('INV-046', 'CONECTOR RJ45 CAT.6 PAQUETE DE 100 UNID,', 0, None, 10.0, None, None),
    ('INV-047', 'CONECTOR RJ45 BOLSA DE 1000 UNIDADES', 0, None, 1.0, None, 'S/N'),
    ('INV-048', 'CABLE DISPLAYPORT A DVI', 0, 12.0, 10.0, None, None),
    ('INV-049', 'CONECTOR RJ45 PAQUETE DE 100 UND', 0, None, 10.0, None, None),
    ('INV-050', 'CABLE HDMI DE 1,5 MTS 4K PREMIUM', 6, 4.91, None, None, None),
    ('INV-051', 'CABLE HDMI DE 1.5 MTS', 4, 3.28, None, None, None),
    ('INV-052', 'CABLE HDMI DE 10 MTS.', 1, 14.41, 12.0, None, None),
    ('INV-053', 'CABLE HDMI DE 3 MTS.', 6, 7.21, 6.0, None, None),
    ('INV-054', 'CABLE HDMI DE 20 MTS.', 3, 36.04, 30.0, None, None),
    ('INV-055', 'CABLE HDMI DE 5 mts,', 5, 10.81, 9.0, None, None),
    ('INV-056', 'CABLE VGA DE 25 MTS', 1, 30.03, 25.0, None, 'DEP.'),
    ('INV-057', 'CABLE DE PODER PARA PC', 6, 7.21, 6.0, None, None),
    ('INV-058', 'CABLE VGA DE 25 MTS', 0, None, 20.0, None, None),
    ('INV-059', 'CABLE VGA DE 10 MT', 2, 14.41, 12.0, None, None),
    ('INV-060', 'CABLE VGA DE 5 MT', 2, 8.41, 7.0, None, None),
    ('INV-061', 'CABLE VGA DE 3 MTS.', 5, 7.21, 6.0, None, None),
    ('INV-062', 'CABLE DISPLAY PORT A VGA', 0, 7.0, 5.0, None, None),
    ('INV-063', 'CABLES VGA DE 1,5 MTS', 3, 6.01, 5.0, 3.5, None),
    ('INV-064', 'CABLE DISPLAY PORT A HDMI', 0, 10.0, 12.0, None, None),
    ('INV-065', 'CABLE 3RCA DE 1,5 MTS', 1, 6.01, 5.0, None, None),
    ('INV-066', 'CABLE UTP CAT.6 1,5 MT', 5, 7.21, 6.0, None, None),
    ('INV-067', 'CABLE HDTV 3RCA A RCA (DVS , TELEVISOR)', 3, 6.01, 5.0, None, None),
    ('INV-068', 'CABLE SATA 3,0 0,45 CM', 10, 6.01, 5.0, None, None),
    ('INV-069', 'CAMARA DE VIGILANCIA MERCUSYS WIFE 2K DETECCION MOV.', 0, 40.0, 45.0, None, None),
    ('INV-070', 'CAMARA TP LINK TAPO C100 VIGILANCIA WIFE VISION NOCTURNA', 1, 54.05, 45.0, None, None),
    ('INV-071', 'CABLE PARA FIBRA OPTICA 10 MT', 0, 10.0, 8.0, None, None),
    ('INV-072', 'CABLE UTP CAT.6 DE 3 MT.', 2, 7.21, 6.0, None, None),
    ('INV-073', 'CABLE UTP CAT.6 DE 5 MT', 6, 8.41, 7.0, None, None),
    ('INV-074', 'CABLE PARA FIBRA OPTICA 20 MT', 0, 9.0, 7.0, None, None),
    ('INV-075', 'CABLE PARA IMPRESORA AZUL 1,5 MT', 4, 8.41, 4.0, None, None),
    ('INV-076', 'CABLE PARA IMPRESORA AZUL 5 MT.', 2, 8.41, 7.0, None, None),
    ('INV-077', 'CAMARA TP LINK TAPO C200 PARA VIGILANCIA 360 WIFE', 1, 66.07, 55.0, None, None),
    ('INV-078', 'CAMARA DOMO PRO 2K 3MP WIFE DE 2,4 ghZ ROBOTICA MOTORIZADO', 4, 66.07, 55.0, None, 'dos judy DEPOSIT'),
    ('INV-079', 'CAMARA TURBO EXT.INT. HIK VISION', 0, None, 20.0, None, None),
    ('INV-080', 'CAMARA WEB1080P', 0, 32.0, 20.0, None, 'Revisar (*)'),
    ('INV-081', 'CAMARA WEB GENIUS', 0, None, 25.0, None, None),
    ('INV-082', 'CARGADOR PARA LAPTO', 0, None, None, None, None),
    ('INV-083', 'CASE JEMIP GAMING IRON MESH BLANCO', 1, 72.07, 60.0, None, 'YUDY dep.'),
    ('INV-084', 'CARGADOR PARA IPHON 13', 1, 10.81, 9.0, None, None),
    ('INV-085', 'CARGADOR PARA CARRO', 1, 7.21, 6.0, None, None),
    ('INV-086', 'CONTROL PARA TV UNIVERSAL', 1, 8.41, 7.0, None, None),
    ('INV-087', 'CASE EXTERNO USB 2,0 2.5 " HDD', 2, 14.41, 12.0, None, None),
    ('INV-088', 'CASE EXTERNO USB 3,0 2.5 " HDD SSD"', 4, 16.82, 14.0, None, None),
    ('INV-089', 'COMBO TECLADO MOUSE ( SPIDERTEC ) ALAMBRICO USB', 0, None, 10.0, None, None),
    ('INV-090', 'COMBO TECLADO MOUSE (LENOVO - HP)', 5, 20.42, 17.0, None, None),
    ('INV-091', 'COMBO SPIDERTEC TECLADO MOUSE ALAMBRICO', 0, 14.0, 10.0, None, None),
    ('INV-092', 'COMBO XTRAIKE MK -207 ALAMBRICO (TECLADO - MOUSE)', 0, None, 15.0, None, None),
    ('INV-093', 'COMBO JEMIP ALAMBRICO USB (TECLADO - MOUSE)', 0, 14.0, 12.0, None, None),
    ('INV-094', 'COMBO JEMIP TECLADO MOUSE INALAMBRICO 3 BOTONES (BLANCO Y NEGRO)', 0, 32.0, 20.0, None, None),
    ('INV-095', 'MUÑECO FUNKO POR CADA UNO', 3, 20.42, 17.0, None, 'DEPOSITO'),
    ('INV-096', 'CONTROL MANDO GAMING INALAMBRICO HARROW PRO V1 G808', 0, 30.0, 35.0, None, 'brian'),
    ('INV-097', 'CONTROL GENIUS PC GX 17', 2, 30.03, 25.0, None, None),
    ('INV-098', 'CONTROL PLAY STATION 3', 1, 26.43, 15.0, None, None),
    ('INV-099', 'CONTROL PLAY STATION 4', 1, 26.43, 22.0, None, None),
    ('INV-100', 'CONTROL ALAMBRICO PARA JUEGO EN COMPUTADORA MICROSOFT', 0, None, 20.0, None, None),
    ('INV-101', 'CONTROL INALAMBRICO PARA JUEGO EN COMPUTADORA', 0, 19.0, 15.0, 3.8, None),
    ('INV-102', 'CONSOLA JUEGO INALAMBRICO M8 GAME STICK', 1, 42.04, 35.0, None, None),
    ('INV-103', 'CONTROL PLAY STATION 3 ESTAMPADO', 0, 15.0, 14.0, None, None),
    ('INV-104', 'CONVERTIDOR MINI VGA A HDMI', 0, 8.0, 7.0, None, None),
    ('INV-105', 'CONVERTIDOR MINI RCA A VGA', 2, 14.41, 12.0, None, None),
    ('INV-106', 'CONVERTIDOR HDMI A VGA', 0, 10.0, 8.0, None, None),
    ('INV-107', 'CONVERTIDOR MARCA MINI HDMI-2AV RCA NEGRO', 2, 14.41, 12.0, None, None),
    ('INV-108', 'CORNETA CON BLUETOOTH MINI SPEAKER A COLOR C ZQS1448', 1, 14.41, 12.0, None, None),
    ('INV-109', 'CORNETA ZQS 1315 BLUETOOH', 1, 14.41, 12.0, None, None),
    ('INV-110', 'CORNETA RUSH', 1, 30.03, 25.0, None, None),
    ('INV-111', 'CORNETA PARA PC 2,5 W', 2, 14.41, 12.0, None, None),
    ('INV-112', 'CORNETA PARA `PC K2053', 3, 14.41, 12.0, None, None),
    ('INV-113', 'CORNETA PARA PC K2059', 0, None, 10.0, None, None),
    ('INV-114', 'CORNETAS SPIDERTEC DE ESCRITORIO USB LUCES LED', 18, 14.41, 12.0, None, '16 Dep.'),
    ('INV-115', 'DISCO SOLIDO SSD GROUP 1 TB', 0, 70.0, 65.0, None, None),
    ('INV-116', 'DISCO SOLIDO SSD GROUP 256GB', 0, None, None, None, None),
    ('INV-117', 'DISCO SOLIDO SSD GROUP 128GB', 0, None, 40.0, None, None),
    ('INV-118', 'DISCO MECANICO DE 500 GB S/N 5VVP7GBE Y 5VVP1YPN', 2, 48.05, 40.0, None, None),
    ('INV-119', 'DISCO SOLIDO PATRIOT SSD 512GB', 0, 65.0, 40.0, None, None),
    ('INV-120', 'DISCO SOLIDO MSI 240 GB', 0, 45.0, 30.0, None, None),
    ('INV-121', 'DISCO SOLIDO SSD JEMIP 256 GB', 0, 40.0, 25.0, None, None),
    ('INV-122', 'DISCO MECANICO PARA LAPTO 500GB', 0, 15.0, 12.0, None, None),
    ('INV-123', 'DISCO MECANICO SATA PARA LAPTO 320GB', 0, 8.0, 5.0, None, None),
    ('INV-124', 'DISCO SOLIDO PATRIOT SSD 480 GB', 0, 86.0, 55.0, None, None),
    ('INV-125', 'EXTENDER REPETIDOR CUDY DUAL BAND AC 1200 2,4GHZ', 0, None, 25.0, None, 'brian'),
    ('INV-126', 'GAMEPAD INALAMBRICO BSP D11S', 1, 48.05, 40.0, None, None),
    ('INV-127', 'FORRO IPHONE 13', 1, 8.41, 7.0, 10.0, None),
    ('INV-128', 'FIRE TV STICK HD 1080P ALEXA VOICE CONTROL TV', 0, None, 45.0, None, None),
    ('INV-129', 'HUB 4 PUERTOS SPIDERTEC TIPO C', 8, 12.01, 10.0, None, '4 DEP.'),
    ('INV-130', 'HUB 7 PUERTOS USB TIPO C 4USB +2USB', 12, 16.82, 14.0, None, '5 dep.'),
    ('INV-131', 'LAPTO DELL I5 DE 11VA 16 RAM SSD 256 (S/N H26GDK3 ARRIBA) (S/N 8RYGCK3 EXIBICION)', 0, None, 375.0, None, None),
    ('INV-132', 'IMPRESORA TERMICA', 0, 40.0, 25.0, None, None),
    ('INV-133', 'KIT DE CAMARA WIFE SEGURIDAD HI VISION', 0, 140.0, 120.0, None, None),
    ('INV-134', 'LAPTO DELL I5 DE 11VA 16 RAM SSD 256 (S/N HQ2JCK3 ARRIBA) (S/N 4CN8BK3 EXIBICION)', 0, None, 375.0, None, None),
    ('INV-135', 'LAPTOP LENOVO I5 DE 8VA. 8 GB 256 RAM', 0, None, 270.0, None, None),
    ('INV-136', 'LAPTO DELL I5 DE 11VA 16 RAM SSD 256 (S/N 4TG7FDK3)', 0, None, 375.0, None, None),
    ('INV-137', 'LAPTOP LENOVO N4020 4 RAM 120GB', 0, 190.0, 170.0, None, 'YUDY'),
    ('INV-138', 'LECTOR CODIGO DE BARRA JEMIP', 0, None, 40.0, None, None),
    ('INV-139', 'LECTOR DE MEMORIA MICROCD', 4, 8.41, 7.0, None, None),
    ('INV-140', 'MEMORIA RAM PARA PC DDR2 DE 2GB', 0, None, 15.0, None, None),
    ('INV-141', 'MEMORIA RAM MUSKIN 8GB DDR3 PARA PC', 1, 54.05, 45.0, None, 'YUDY'),
    ('INV-142', 'MEMORIA RAM PARA PC REDLINE 16GB DDR4', 0, None, 145.0, None, None),
    ('INV-143', 'MEMORIA RAM GENERICA PARA PC DDR3 DE 8 GB', 0, None, 35.0, 39.74, None),
    ('INV-144', 'MEMORIA ADATA MICRO SD 32GB', 0, 8.0, 6.0, 12.0, None),
    ('INV-145', 'MEMORIA KINSTON MICRO SD 128GB', 0, 20.0, 15.0, None, None),
    ('INV-146', 'MICROFONO BALITA SX12 DOS MICROFONOS INALAMBRICO', 1, 72.07, 60.0, None, None),
    ('INV-147', 'MEMORIA MICRO SD KINGSTON 8 GB', 0, None, 8.0, None, None),
    ('INV-148', 'MEMORIA MICRO SD KINGSTON DE 32GB', 0, None, 10.0, None, None),
    ('INV-149', 'MEMORIA MICRO SD JEMIP DE 32 GB', 0, None, 9.0, None, None),
    ('INV-150', 'MEMORIA MICRO SD 64GB JEMIP', 0, 10.0, 8.0, None, None),
    ('INV-151', 'MEMORIA MICRO SD 256GB JEMIP', 0, 32.0, 20.0, None, None),
    ('INV-152', 'MESAS PARA COMPUTADORA COLOR MADERA Y NEGRA', 0, 85.0, 50.0, None, None),
    ('INV-153', 'MEMORIA MICRO CD DE 4GB KINGSTON', 3, 12.01, 10.0, None, None),
    ('INV-154', 'MICROFONO DE BALITA INALAMBRICO N9 ESPOJNJA', 3, 30.03, 25.0, None, None),
    ('INV-155', 'MICROFONO INALAMBRICO DE ESPONJA PLU F-16', 2, 36.04, 30.0, 5.92, None),
    ('INV-156', 'MICROFONO DE BALITA INALAMBRICO DE DOS MICROFONO K9', 1, 30.03, 25.0, None, None),
    ('INV-157', 'MICROFONO DE BALITA DE UN MICROFONO K8', 1, 24.02, 20.0, None, None),
    ('INV-158', 'MICROFONO DE BALITA K35 DOS MICROFONOS REFURBISH', 1, 14.41, 12.0, None, None),
    ('INV-159', 'MICROFONO INALAMBRICO PARA CONFERENCIA HWIN', 1, 30.03, 25.0, None, None),
    ('INV-160', 'MICROFONO DE B ALITGA UN MICROFONO REFURBISH', 1, 14.41, 12.0, None, None),
    ('INV-161', 'MONITOR led AROA 21,5 HDMI-VGA', 2, 72.07, 60.0, None, None),
    ('INV-162', 'MONITOR REFURBISH DELL 24 PULGADAS', 0, 90.0, 80.0, None, None),
    ('INV-163', 'MONITOR 20 PULGADAS NUEVO AUCE', 0, None, 55.0, None, 'YUDY'),
    ('INV-164', 'EXTENDER REPETIDOR CUDY DUAL BAND AC 1200 2,4GHZ', 0, None, None, None, None),
    ('INV-165', 'MONITOR LED AROA 19 " 60hz HDMI-VGA', 0, None, None, None, None),
    ('INV-166', 'MOUSE FENTECH INALAMBRICO GAMER KANATA (NEGRO Y BLANCO)', 0, None, 20.0, None, None),
    ('INV-167', 'MOUSE DELL CAJA GRANDE', 0, 7.0, 5.0, None, None),
    ('INV-168', 'MOUSE INALAMBRICO VERTICAL ERGONOMICO RGV', 0, 24.0, 15.0, None, None),
    ('INV-169', 'MOUSE GAMER KING ULTRA TRIPLE MODO ULTRA LIVIANO BASE DE CARG', 0, None, 40.0, None, None),
    ('INV-170', 'MOUSE GAMER IMPACT REDRAGON SURGE ALAMBRICO', 0, None, 40.0, None, None),
    ('INV-171', 'MOUSE INALAMBRICO UPRODUCTS OPTICO USB NEGRO', 0, None, 10.0, None, None),
    ('INV-172', 'MOUSE AGILER INALAMBRICO MINI WIRELESS CON NANO RECEPTOR NEGRO', 1, 12.01, 10.0, None, None),
    ('INV-173', 'MOUSE UPRODUC TS 1200 INALAMBRICO RECARGABLE', 2, 12.01, 10.0, None, None),
    ('INV-174', 'MOUSE ALAMBRICO GAMER GRIFFIN REDRAGON NEGRO M,OD M607', 0, 25.0, 30.0, None, None),
    ('INV-175', 'MOUSE HP GAMING S600 A COLOR', 0, 10.0, 8.0, None, None),
    ('INV-176', 'MOUSE INALAMBRICO UPRODUCTS', 1, 14.41, 12.0, None, None),
    ('INV-177', 'MOUSE HP M30', 1, 10.81, 9.0, None, None),
    ('INV-178', 'MOUSE ALAMBRICO GAMER FANTECH RAPTOR X UX2', 1, 48.05, 40.0, None, 'brian'),
    ('INV-179', 'MOUSE GAMING HP ALAMBRICO G270', 3, 10.81, 9.0, None, None),
    ('INV-180', 'MOUSE INALAMBRICO GENIUS GRANDE CAJA ROJA', 0, None, 15.0, None, None),
    ('INV-181', 'MOUSE HP M15', 0, 8.0, 10.0, None, None),
    ('INV-182', 'MOUSE INALAMBRICO HP M300', 2, 14.41, 12.0, None, None),
    ('INV-183', 'MOUSE INALAMBRICO SPIDERTEC RECARGABLE', 6, 14.41, 12.0, 3.3, None),
    ('INV-184', 'MOUSE INALAMBRICO COLORVIS', 1, 14.41, 12.0, None, None),
    ('INV-185', 'MOUSE HP INALAMBRICO RECARGABLE W10', 0, None, None, None, None),
    ('INV-186', 'MOUSE ALAMBRICO GENIUS XSCROLL', 0, None, None, None, None),
    ('INV-187', 'MOUSE MINI BANDA', 10, 8.41, 7.0, None, 'DEP.6'),
    ('INV-188', 'MOUSE MINI BANDA', 0, 6.0, 5.0, None, None),
    ('INV-189', 'MOUSE PAD ESCRITORIO', 1, 6.01, 5.0, None, None),
    ('INV-190', 'MOUSE PAD ARGOM', 0, None, 5.0, None, None),
    ('INV-191', 'MOUSE PAD GAMMING REDRG.,', 0, 16.0, 10.0, None, None),
    ('INV-192', 'MOUSE PAD JEMIP', 0, None, 6.0, None, None),
    ('INV-193', 'MOUSE PAD TIPO ALFOMBRA FANTECH MEDID.450X400X4 ML', 1, 16.82, 14.0, None, None),
    ('INV-194', 'MOUSE PAD PARA NIÑAS', 3, 6.01, 5.0, None, None),
    ('INV-195', 'PENDRIVE HI KSEMI 64 GB', 2, 14.41, 12.0, None, None),
    ('INV-196', 'PENDRIVE HP DE 8GB', 0, 10.0, 12.0, None, None),
    ('INV-197', 'PENDRIVE KINGSTON DE 4 GB', 0, 8.0, 7.0, None, None),
    ('INV-198', 'PENDRIVE SANDISK DE 4 GB', 0, 8.0, 7.0, None, None),
    ('INV-199', 'PENDRIVE HIK SEMI DE64 GB USB 3,2 DUAL SLIM', 0, None, 12.0, None, None),
    ('INV-200', 'PENDRIVE ADATA DE 256 GB', 2, 30.03, 25.0, None, None),
    ('INV-201', 'PENDRIVE BLADE HIKSEMI 128 GB', 0, None, 15.0, None, None),
    ('INV-202', 'PENDRIVE SANDISK DE 8GB', 0, None, 8.0, None, None),
    ('INV-203', 'PENDRIVE KINGSTON 32 GB', 0, 12.0, 14.0, None, None),
    ('INV-204', 'PENDRIVE SANDISK DE 16 GBN', 4, 14.41, 12.0, None, None),
    ('INV-205', 'PENDRIVE DE 16GB KINGSTON', 0, 11.0, 13.0, None, None),
    ('INV-206', 'PASTA TERMICA GENERICA', 0, 1.5, 1.0, 25.0, None),
    ('INV-207', 'PASTA TERMICA GAMEMAX', 0, 10.0, 7.0, None, None),
    ('INV-208', 'PENDRIVE KINGSTON DE 128 GB', 1, 24.02, 20.0, None, None),
    ('INV-209', 'PENDRIVE KINGSTON DE 256GB', 0, None, 30.0, None, None),
    ('INV-210', 'PENDRIVE KINGSTGON DE 64 GB', 0, None, 12.0, None, None),
    ('INV-211', 'PC MINI ESE 256GB 8 RAM PROCESADOR 12AVA GENERACION', 0, None, 255.0, None, None),
    ('INV-212', 'PROJECTOR GAME ULTRA HD 3D', 0, None, 90.0, None, None),
    ('INV-213', 'PROCESADOR RIZEN 7 5700G', 0, None, 200.0, None, 'BRIAN'),
    ('INV-214', 'PARLANTE ECHO POP 1GEN INTELIGENTE ALEXA WIFE', 1, 60.06, 50.0, None, None),
    ('INV-215', 'PENDRIVE HIK SEMI DE 64 GB', 0, None, 7.0, None, None),
    ('INV-216', 'PENDRIVE SANDISK DE 32 GB', 0, None, 12.0, None, None),
    ('INV-217', 'POWERBAND', 2, 36.04, 30.0, None, None),
    ('INV-218', 'REGLETAS DE SEIS TOMAS TONAL', 4, 14.41, 12.0, None, '3 DEPOSITO*'),
    ('INV-219', 'RECEPTOR DE WIFE CON ANTENA ALFA', 2, 14.41, 12.0, None, None),
    ('INV-220', 'RADIO BAOFENG ANALOGICO UHF 16 CANALES', 0, None, 40.0, None, None),
    ('INV-221', 'RECEPTOR DE WIFE AX300 (ROJO) ALFA SIN ANTENA', 2, 14.41, 12.0, None, None),
    ('INV-222', 'RECEPTOR DE WIFE AC 1300 SIN ANTENA CUDY', 0, None, 20.0, None, None),
    ('INV-223', 'RECEPTOR DE WIFE AC 1300 CUDY', 0, None, 25.0, None, None),
    ('INV-224', 'RECEPTOR DE WIFE AC 1300 CON ANTENA VERDE', 3, 18.02, 15.0, None, None),
    ('INV-225', 'RECEPTOR WIFE DUAL BAND 600 MBPS NARANJA', 0, 14.0, 17.0, None, None),
    ('INV-226', 'RELOJ SMART TEROS', 1, 42.04, 35.0, None, None),
    ('INV-227', 'RECEPTOR DE WIFE 300MBPS CON ANTENA', 0, None, 8.0, None, None),
    ('INV-228', 'ROUTER TP LINK DECO X10 WIFE MESH AX 1500 EXTENSOR', 0, 330.0, 200.0, None, None),
    ('INV-229', 'ROUTER AC 1200 TP LINK', 0, None, 35.0, None, None),
    ('INV-230', 'RAIZEN 3 AMD', 0, None, None, None, None),
    ('INV-231', 'ROUTER CUDY TRI BAND 4 PUERTOS Y 6 ANTENAS', 0, None, 150.0, None, 'BRIAN uno deposito'),
    ('INV-232', 'ROUTER HIKVISION WIFE 6 AX 3000 DUAL BAND WR30X', 0, None, 50.0, None, None),
    ('INV-233', 'ROUTER CUDY 4 EN 1 AC 1200', 0, 57.0, 35.0, None, None),
    ('INV-234', 'ROUTER CUDY WIFE 6 AC 1200 DOS ANTENAS 5 EN 1', 0, 45.0, 30.0, None, None),
    ('INV-235', 'ROUTER HIKVISION WIFE AC 1200', 0, None, 40.0, None, 'brian'),
    ('INV-236', 'ROUTER CUDY AC 1200 MESH', 0, 57.0, 35.0, None, None),
    ('INV-237', 'ROUTER TPLINK AX 1500 GIGABIT DUAL BAND 4 ANTENAS', 0, None, 55.0, None, None),
    ('INV-238', 'ROUTER AC 1200 UPPRODUCTS DUAL BAND', 0, 32.0, 28.0, None, None),
    ('INV-239', 'ROUTER AX 1500 CUDY WIFE 6', 1, 48.05, 40.0, None, None),
    ('INV-240', 'ROUTER XIOAMI AC 1200 WIFE', 0, 40.0, 25.0, None, None),
    ('INV-241', 'ROUTER CUDY AX 3000 2,5G MESH WIFE 6 DUAL BAND 3 PACK', 0, None, 150.0, None, 'BRIAN'),
    ('INV-242', 'ROUTER TP LINK INALAMBRICO AC 1200 4 ANTENAS DUAL BAND', 0, None, 40.0, None, None),
    ('INV-243', 'ROUTER CUDY ACCES POINT MESH WIFE 7 3 PACK BE3600', 0, None, 230.0, None, None),
    ('INV-244', 'ROUTER CUDY MESH B11000 WIFE7 TRI BAND 2,5G', 0, None, 300.0, None, None),
    ('INV-245', 'ROUTER CUDY AX 3000 WIFE 6 GIGABIT WR3000E', 0, None, 50.0, None, None),
    ('INV-246', 'ROKU PREMIERE 4K', 0, None, 40.0, None, None),
    ('INV-247', 'SSD PATRIO 128GB', 1, 48.05, 40.0, None, None),
    ('INV-248', 'SSD JEMIP 128 GB', 0, None, 35.0, None, None),
    ('INV-249', 'ROKU EXPRESS TVBOX', 0, None, 35.0, None, None),
    ('INV-250', 'SWITCH CUDY 16 PUERTOS ESCRITORIO MOD. GS1016', 0, None, 55.0, None, 'BRIAN'),
    ('INV-251', 'SWITCH CUDY DE 8 PUERTOS', 7, 24.02, 20.0, None, None),
    ('INV-252', 'SWITCH CUDY DE 5 PUERTOS', 0, None, 15.0, None, None),
    ('INV-253', 'SWITCH CUDY GIGABIT 16 PUERTOS RACKEABLE', 0, None, 60.0, None, '1DEP.'),
    ('INV-254', 'SWITCH CUDY VPN 5 PUERTOSY CONTROLADOR AP GIGABIT MOD. C200P', 1, 78.08, 65.0, None, 'BRIAN'),
    ('INV-255', 'TARJETA MADRE MSI RIZEN A520M APRO', 0, 95.0, 15.0, None, None),
    ('INV-256', 'TARJETA MADRE BIOSTAR', 0, 45.0, None, None, None),
    ('INV-257', 'TARJETA DE VIDEO GRAFICA REFURBISH RX 570 4GB', 0, None, 80.0, None, None),
    ('INV-258', 'TARJETA MADRE ASROCK A520HDV/ATXF', 0, 90.0, 80.0, None, None),
    ('INV-259', 'TECLADO ALAMBRICO HP K1600', 0, None, 8.0, None, None),
    ('INV-260', 'TECLADO GAMING RGB SHIV MODELO K512 NEGRO Y BLANCO', 0, None, 40.0, None, None),
    ('INV-261', 'TECLADO JEMIP USB ALAMBRICO', 0, 12.0, 8.0, None, None),
    ('INV-262', 'TECLADO LOGITECH K122 ALAMBRICO', 0, None, 10.0, None, None),
    ('INV-263', 'TECLADO MECANICO DRAGONBORN NEGR0 MODELO K630RGB', 0, None, 45.0, None, 'BRIAN'),
    ('INV-264', 'TECLADO MECANICO HORUS REDRAGON NEGRO', 1, 108.11, 90.0, None, 'brian'),
    ('INV-265', 'TECLADO MECANINICO KUMARA REDRAGON NEGRO 70/30', 0, 73.0, 45.0, None, 'brian'),
    ('INV-266', 'TECLADO MECANCO FIZZ REDRAGON GRAY WHITE', 1, 66.07, 55.0, None, 'BRIAN'),
    ('INV-267', 'TECLADO MECANICO GAMING TRUNDLE CABLEADO REDRAG. 100%', 0, None, 60.0, None, None),
    ('INV-268', 'TECLADO ALAMBRICO HP K1600', 2, 12.01, 10.0, None, None),
    ('INV-269', 'TECLADO GENIUS SCORPION GAMING A COLORES', 4, 30.03, 25.0, None, '3 en deposito*'),
    ('INV-270', 'TECLADO GAMER HARPE REDRAGON MEMBRANA', 0, None, 35.0, None, 'BRIAN'),
    ('INV-271', 'TECLADO MECANICO GAMER FANTECH ATOM 107S ALAMBRICO', 0, None, 35.0, None, None),
    ('INV-272', 'TECLADO MECANICO FANTECH 80 % MK876V2', 0, None, 35.0, None, None),
    ('INV-273', 'TONER LASER CARTRIDER NEGRO', 1, 30.03, 25.0, None, None),
    ('INV-274', 'TECLADO GAMING REDRAGON MECANICO MITRA', 0, None, 55.0, None, 'Revisar (*)'),
    ('INV-275', 'TELEFONO LOGIG 128 almacenamiento, 4 gb ram , 10 ram expandible', 1, 144.14, 120.0, None, None),
    ('INV-276', 'TRANSFORMADOR 12V DE 2A', 4, 8.41, 7.0, None, None),
    ('INV-277', 'TECLADO SPIDERTECH SENCILLO', 3, 8.41, 7.0, None, '2 DEP.'),
    ('INV-278', 'TECLADO HP Y PEQUEÑO MINI', 1, 14.41, 12.0, None, None),
    ('INV-279', 'UNION RJ 45', 0, None, 3.0, None, None),
    ('INV-280', 'UPS BEGPROD DE 1000VA 4 TOMAS DE 7AH', 0, 76.0, 45.0, None, None),
    ('INV-281', 'UPS MINI CDP POE 120VCA', 0, None, 30.0, None, None),
    ('INV-282', 'UPS APC DE 700V 4 TOMAS', 0, None, 85.0, None, None),
    ('INV-283', 'VIDEO BALOOM HIK VISION', 0, 7.0, 5.0, None, None),
    ('INV-284', 'VIDEO BALOOM PASIVO HDCVI A PRESIÒN', 16, 24.02, 4.0, None, 'DEP.9'),
    ('INV-285', 'WIFI PORTATIL INALAMBRICO 4G LTE MOBILE IWIFI', 0, 32.0, 20.0, None, None),
    ('INV-286', 'COMBOS I5 DE 10TH , MEMORIA DDR4 DE 16GB, SSD 480, CASE JEMIP', 0, 515.0, 380.0, None, None),
    ('INV-287', 'VIDEO BALON', 13, 8.41, 7.0, None, '6 DEP.'),
    ('INV-288', 'UPS APC DE 600V 7 TOMAS', 1, 126.13, 105.0, None, None),
    ('INV-289', 'ADAPTADOR USB AC 1300 TP LINK', 1, 42.04, 35.0, None, None),
    ('INV-290', 'SWICHT MERCUSYS 5 PUERTOS MS 105G', 0, 24.0, 20.0, None, None),
    ('INV-291', 'SWICHT MERCUSYS 8 PUERTOS MS 108G', 0, 37.0, 30.0, None, None),
    ('INV-292', 'ROUTER MERCUSYS AC 1300 GIGABIT INALAMBRICO DUAL BAND', 0, 72.0, 45.0, None, None),
    ('INV-293', 'ADAPTADOR RECEPTOR MERCUSYS USB IHIGH GAIN', 5, 30.03, 25.0, None, '5 en deposito'),
    ('INV-294', 'ROUTER AC 1350 TP LINK DE ALTA POTENCIA DUAL BAND', 0, 86.0, 60.0, None, None),
    ('INV-295', 'MODEN ROUTER MERCUSYS 300 MBPS', 0, 65.0, 40.0, None, None),
    ('INV-296', 'ROUTER MULTI MODE TP LINK WIFE 2 ANTENAS', 1, 36.04, 30.0, None, None),
    ('INV-297', 'DISCO CRUCIAL 1 TB SSD', 0, None, 120.0, None, 'BRIAN'),
]

def inicializar_bd():
    """Crea las tablas, índices de velocidad y carga el inventario inicial si está vacía."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku VARCHAR(20) UNIQUE NOT NULL,
        nombre VARCHAR(255) NOT NULL,
        cantidad INTEGER NOT NULL DEFAULT 0,
        precio_detal_usd DECIMAL(10, 2) NULL,
        precio_descuento_usd DECIMAL(10, 2) NULL,
        costo_usd DECIMAL(10, 2) NULL,
        ubicacion_nota VARCHAR(100) NULL,
        activo BOOLEAN NOT NULL DEFAULT 1,
        fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Índices para búsquedas y filtrados instantáneos
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_productos_activo_id ON productos(activo, id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_productos_activo_cant ON productos(activo, cantidad);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_productos_sku ON productos(sku);")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS configuracion (
        clave TEXT PRIMARY KEY,
        valor TEXT NOT NULL,
        fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('tasa_bcv', '914.02')")
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('tasa_paralelo', '1076.87')")
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('fecha_tasa', 'Inicial por defecto')")

    cursor.execute("SELECT COUNT(*) as total FROM productos")
    total_existente = cursor.fetchone()["total"]

    if total_existente == 0:
        cursor.executemany("""
        INSERT INTO productos (sku, nombre, cantidad, precio_detal_usd, precio_descuento_usd, costo_usd, ubicacion_nota)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """, PRODUCTOS_INICIALES)
        conn.commit()
    else:
        conn.commit()

    conn.close()


def obtener_productos(filtro: str = "", solo_stock: bool = False, solo_agotados: bool = False) -> List[Dict[str, Any]]:
    """Consulta y filtra productos activos en tiempo real por SKU, Nombre o Ubicación."""
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM productos WHERE activo = 1"
    params = []

    if filtro.strip():
        term = f"%{filtro.strip()}%"
        query += " AND (sku LIKE ? OR nombre LIKE ? OR ubicacion_nota LIKE ?)"
        params.extend([term, term, term])

    if solo_stock:
        query += " AND cantidad > 0"
    elif solo_agotados:
        query += " AND cantidad = 0"

    query += " ORDER BY id ASC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    productos = [dict(row) for row in rows]
    conn.close()
    return productos


def obtener_producto_por_id(producto_id: int) -> Optional[Dict[str, Any]]:
    """Devuelve los datos de un producto específico."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM productos WHERE id = ? AND activo = 1", (producto_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def agregar_producto(sku: str, nombre: str, cantidad: int, precio_detal: Optional[float],
                     precio_descuento: Optional[float], costo: Optional[float], ubicacion: Optional[str]) -> bool:
    """Inserta un nuevo artículo en la base de datos."""
    conn = get_connection()
    cursor = conn.cursor()
    sku_norm = sku.strip().upper()
    nombre_norm = nombre.strip().upper()
    ubicacion_norm = ubicacion.strip() if ubicacion and ubicacion.strip() else None

    try:
        # Si existía un registro borrado lógicamente con el mismo SKU, lo eliminamos físicamente para permitir reutilizar el SKU
        cursor.execute("DELETE FROM productos WHERE sku = ? AND activo = 0", (sku_norm,))
        cursor.execute("""
        INSERT INTO productos (sku, nombre, cantidad, precio_detal_usd, precio_descuento_usd, costo_usd, ubicacion_nota)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (sku_norm, nombre_norm, cantidad, precio_detal, precio_descuento, costo, ubicacion_norm))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def actualizar_producto(producto_id: int, sku: str, nombre: str, cantidad: int, precio_detal: Optional[float],
                        precio_descuento: Optional[float], costo: Optional[float], ubicacion: Optional[str]) -> bool:
    """Actualiza los datos de un artículo existente."""
    conn = get_connection()
    cursor = conn.cursor()
    sku_norm = sku.strip().upper()
    nombre_norm = nombre.strip().upper()
    ubicacion_norm = ubicacion.strip() if ubicacion and ubicacion.strip() else None

    try:
        cursor.execute("""
        UPDATE productos 
        SET sku = ?, nombre = ?, cantidad = ?, precio_detal_usd = ?, precio_descuento_usd = ?, costo_usd = ?, ubicacion_nota = ?, fecha_actualizacion = CURRENT_TIMESTAMP
        WHERE id = ?;
        """, (sku_norm, nombre_norm, cantidad, precio_detal, precio_descuento, costo, ubicacion_norm, producto_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def actualizar_solo_cantidad(producto_id: int, nueva_cantidad: int) -> bool:
    """Actualización ultra-rápida únicamente del stock de un artículo."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE productos SET cantidad = ?, fecha_actualizacion = CURRENT_TIMESTAMP WHERE id = ?",
        (max(0, nueva_cantidad), producto_id)
    )
    conn.commit()
    conn.close()
    return True


def eliminar_producto(producto_id: int) -> bool:
    """Elimina un producto del inventario."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM productos WHERE id = ?", (producto_id,))
    conn.commit()
    conn.close()
    return True


def obtener_siguiente_sku() -> str:
    """Genera automáticamente la siguiente sugerencia de SKU (ej. INV-298) basada en los productos activos."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT sku FROM productos WHERE activo = 1 AND sku LIKE 'INV-%'")
    rows = cursor.fetchall()
    conn.close()

    max_num = 0
    for r in rows:
        try:
            partes = r["sku"].split("-")
            if len(partes) > 1 and partes[1].isdigit():
                num = int(partes[1])
                if num > max_num:
                    max_num = num
        except Exception:
            pass
    return f"INV-{max_num + 1:03d}"


def obtener_resumen_estadisticas() -> Dict[str, Any]:
    """Calcula totales globales de existencias y valor del inventario."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT 
        COUNT(*) as total_items,
        SUM(cantidad) as total_unidades,
        SUM(CASE WHEN cantidad > 0 THEN 1 ELSE 0 END) as items_con_stock,
        SUM(CASE WHEN cantidad = 0 THEN 1 ELSE 0 END) as items_agotados,
        SUM(cantidad * COALESCE(precio_detal_usd, precio_descuento_usd, 0)) as valor_estimado_usd
    FROM productos 
    WHERE activo = 1;
    """)
    row = cursor.fetchone()
    conn.close()
    return {
        "total_items": row["total_items"] or 0,
        "total_unidades": row["total_unidades"] or 0,
        "items_con_stock": row["items_con_stock"] or 0,
        "items_agotados": row["items_agotados"] or 0,
        "valor_estimado_usd": row["valor_estimado_usd"] or 0.0
    }


def guardar_tasas_cache(tasa_bcv: float, tasa_paralelo: float, fecha: str):
    """Guarda las tasas del dólar en SQLite para uso offline."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('tasa_bcv', ?)", (str(tasa_bcv),))
    cursor.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('tasa_paralelo', ?)", (str(tasa_paralelo),))
    cursor.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('fecha_tasa', ?)", (fecha,))
    conn.commit()
    conn.close()


def obtener_tasas_cache() -> Dict[str, Any]:
    """Obtiene las tasas guardadas en SQLite de forma instantánea."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT clave, valor FROM configuracion WHERE clave IN ('tasa_bcv', 'tasa_paralelo', 'fecha_tasa')")
    rows = cursor.fetchall()
    conn.close()
    datos = {row["clave"]: row["valor"] for row in rows}
    return {
        "bcv": float(datos.get("tasa_bcv", 914.02)),
        "paralelo": float(datos.get("tasa_paralelo", 1076.87)),
        "fecha": datos.get("fecha_tasa", "Caché Local"),
        "online": False,
        "mensaje": f"Caché local ({datos.get('fecha_tasa', 'Guardada')})"
    }


if __name__ == "__main__":
    inicializar_bd()
    resumen = obtener_resumen_estadisticas()
    print("Base de datos optimizada e inicializada con éxito.")
    print(f"Total productos: {resumen['total_items']}")
    print(f"Total unidades en stock: {resumen['total_unidades']}")
    print(f"Productos con stock: {resumen['items_con_stock']}")
    print(f"Productos agotados: {resumen['items_agotados']}")


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
    return {"exito": True, "nuevos": nuevos, "actualizados": actualizados, "total": nuevos + actualizados, "errores": errores}
