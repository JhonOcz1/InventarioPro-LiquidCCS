# 📦 Sistema de Inventario Pro (Python + SQLite + Flet)
### Diseñado para Móvil (Android APK Offline) y Escritorio (PC Windows/Mac/Linux)

Aplicación moderna de control de existencias, precios dinámicos en Dólares (USD) y Bolívares (Bs), búsqueda en tiempo real, exportación para impresión física y sincronización inteligente de la tasa oficial del BCV y Paralelo con soporte 100% offline.

---

## 🚀 1. Características Principales

1. **100% Offline-First:** Toda la base de datos corre directamente en SQLite dentro del teléfono o PC. No requiere conexión a internet para consultar, buscar, añadir o editar productos.
2. **Tasa del Dólar en Venezuela con Caché Diario:**
   - Consulta la API en vivo (`DolarApi`) para obtener la tasa oficial del Banco Central de Venezuela (BCV) y la tasa Paralelo.
   - Si no hay señal o internet en el teléfono, la app recupera automáticamente la última tasa guardada en SQLite sin colgarse ni mostrar errores.
   - Los precios en Bolívares se calculan dinámicamente multiplicando los USD por la tasa del día.
3. **Módulo de Búsqueda Inteligente:**
   - Filtro reactivo en tiempo real mientras escribes (por nombre, SKU o nota de ubicación).
   - Filtros rápidos por botones de estado: *Todos (297)*, *En Stock (127)* y *Agotados (170)*.
4. **Carga y Edición de Artículos:**
   - Botón modal para nuevos artículos con sugerencia automática de SKU correlativo (ej. `INV-298`).
   - Cálculo en vivo de equivalencia en Bolívares al ingresar el precio en USD.
   - Ajuste rápido de stock (+ / -) directo desde cada tarjeta.
5. **Exportación para Impresión:**
   - **Reporte PDF Profesional:** Formato apaisado (landscape) con encabezados, tasa del día, desglose en USD y Bs, ubicación física y resumen de valoración total de inventario.
   - **Vista de Impresión HTML:** Se abre en el navegador predeterminado y activa el diálogo de impresión física con un clic.
6. **Diseño Frontend Moderno:**
   - Paleta de colores claros (Slate moderno `#0F172A`, fondos `#F8FAFC`, acentos en esmeralda `#059669` y azul cielo `#0284C7`).
   - Totalmente adaptable a pantallas verticales de celular (Android) y pantallas anchas de PC.

---

## 🗄️ 2. Base de Datos SQLite y Limpieza de Datos

### Archivo de base de datos
- Ubicación: `inventario.db` (generado automáticamente por `database.py`).

### Estructura de la Tabla `productos`
```sql
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
```

### Tabla de soporte offline `configuracion`
Guarda la última tasa obtenida para que la app funcione sin internet:
```sql
CREATE TABLE IF NOT EXISTS configuracion (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Decisiones de Limpieza y Normalización Aplicadas
- **Filtrado de filas:** De las 334 filas originales, se importaron exactamente los **297 productos válidos**, totalizando **127 artículos con existencia física** y **385 unidades totales en stock**.
- **SKU secuencial:** Normalizados de `INV-001` a `INV-297`.
- **Ubicaciones preservadas:** Los textos de ubicación y responsables (como `1 DEP.*`, `BRIAN`, `YUDY`, `DEPOSITO`) se asignaron al campo `ubicacion_nota`.
- **Precios dinámicos:** Los montos se guardan en USD limpio. Los bolívares se calculan al vuelo según la tasa activa.

---

## 💻 3. Instrucciones de Ejecución en PC (Pruebas Locales)

### Requisitos previos
- Python 3.10 o superior instalado.

### Opción Rápida (Doble Clic en Windows)
Haz doble clic en el archivo `ejecutar_app.bat` incluido en la carpeta del proyecto.

### Opción Manual por Terminal (PowerShell / CMD)
1. Abre tu terminal en la carpeta del proyecto:
   ```powershell
   cd C:\Users\Jhon\Downloads\kkik
   ```
2. Activa el entorno virtual:
   - En Windows (PowerShell):
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   - En Windows (CMD):
     ```cmd
     .\venv\Scripts\activate.bat
     ```
3. Si vas a instalar en un entorno nuevo, instala las librerías:
   ```bash
   pip install -r requirements.txt
   ```
4. Ejecuta la aplicación:
   ```bash
   python main.py
   ```
*Se abrirá una ventana de escritorio con el sistema completo y los 297 productos cargados.*

---

## 📱 4. Cómo Compilar el Archivo APK para Celular

La aplicación está construida sobre **Flet (Flutter UI engine para Python)**, lo que permite empaquetar directamente a Android APK nativo con alto rendimiento.

### Método A: Compilación Local con Flet CLI
1. Instala el empaquetador de Flet:
   ```bash
   pip install flet
   ```
2. Asegúrate de tener instalado:
   - **Flutter SDK** (versión 3.16 o superior).
   - **Android Studio** con Android SDK y Command-line Tools.
   - **Java JDK 17** configurado en tu `JAVA_HOME`.
3. Ejecuta el comando de compilación en la raíz de tu proyecto:
   ```bash
   flet build apk --project "inventariopro" --org "com.liquidccs.inventario"
   ```
4. El archivo generado se ubicará en:
   `build/apk/app-release.apk`
5. Conecta tu teléfono mediante cable USB o sube el APK a Google Drive, pásalo a tu celular, activa "Instalar aplicaciones de fuentes desconocidas" y abre el archivo.

### Método B: Compilación Gratuita en la Nube (GitHub Actions o Google Colab)
Si no deseas configurar Android Studio o Flutter en tu PC:
1. Puedes crear un repositorio en GitHub con el código.
2. Utilizar un flujo de trabajo de GitHub Actions con el runner `ubuntu-latest` que ejecuta `flet build apk`.
3. Descargar el archivo `.apk` directamente desde la pestaña de *Artifacts* de GitHub e instalarlo en tu móvil.

---

## 🛠️ 5. Estructura del Código

- **`main.py`**: Interfaz gráfica responsiva con Flet (tarjetas, búsqueda reactiva, modales, alertas, dashboard KPI).
- **`database.py`**: Conexión a SQLite, inicialización de datos (297 productos), consultas de búsqueda y transacciones CRUD.
- **`dolar_service.py`**: Cliente HTTP de DolarApi con timeout de seguridad y mecanismo de contingencia offline.
- **`export_service.py`**: Generador de documentos PDF apaisados con ReportLab y páginas HTML listas para imprimir.
- **`requirements.txt`**: Librerías necesarias (`flet`, `reportlab`, `requests`).
- **`ejecutar_app.bat`**: Script de arranque directo para Windows.
