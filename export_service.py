"""
export_service.py - Módulo para la exportación e impresión del inventario (Compatible con Android APK y PC)
Incluye soporte para ReportLab (PC) y motor PDF 100% Python Puro integrado (Android/Móvil sin dependencias C),
además de generación de HTML imprimible y resumen de texto calculado según arbitraje cambiario BCV/Reposición.
"""

import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import database


def get_export_dir() -> str:
    """Crea y retorna la carpeta donde se guardan las exportaciones (compatible con Android y PC)."""
    export_dir = os.path.join(database.get_writable_app_dir(), "exportaciones")
    os.makedirs(export_dir, exist_ok=True)
    return export_dir


def _resolver_tasa_repo(tasa_reposicion: Optional[float]) -> float:
    if tasa_reposicion is not None and tasa_reposicion > 0:
        return float(tasa_reposicion)
    return database.obtener_tasas()["tasa_reposicion"]


def _generar_pdf_puro_python(
    pdf_path: str,
    productos: List[Dict[str, Any]],
    tasa_bcv: float,
    tasa_reposicion: Optional[float] = None,
    filtro_aplicado: str = "",
) -> str:
    """
    Generador de PDF 1.4 apaisado (landscape 792x612 pt) escrito en Python 100% puro.
    No requiere librerías en C (como Pillow o ReportLab), funcionando nativamente en Android APK.
    """
    t_repo = _resolver_tasa_repo(tasa_reposicion)

    def esc_pdf(texto: str) -> str:
        limpio = texto.encode("latin-1", errors="replace").decode("latin-1")
        return limpio.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    fecha_actual = datetime.now().strftime("%d/%m/%Y %I:%M %p")
    bcv_str = database.formatear_bs(tasa_bcv)
    repo_str = database.formatear_bs(t_repo)

    filas_por_pagina = 32
    paginas_datos = [productos[i:i + filas_por_pagina] for i in range(0, max(1, len(productos)), filas_por_pagina)]

    total_unidades = 0
    total_valor_bcv_usd = 0.0
    total_valor_bs_repo = 0.0
    for p in productos:
        cant = p["cantidad"]
        total_unidades += cant
        if cant > 0:
            calc = database.calcular_precios_producto(p, tasa_bcv, t_repo)
            if calc["tiene_precio"]:
                total_valor_bcv_usd += calc["precio_venta_bcv_usd"] * cant
                total_valor_bs_repo += calc["monto_bs_reposicion"] * cant

    total_bs_str = database.formatear_bs(total_valor_bs_repo)

    objetos_pdf = []

    def agregar_objeto(contenido_bytes: bytes) -> int:
        objetos_pdf.append(contenido_bytes)
        return len(objetos_pdf)

    agregar_objeto(b"")  # 1: Catalog
    agregar_objeto(b"")  # 2: Pages
    font_reg_id = agregar_objeto(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    font_bold_id = agregar_objeto(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")

    page_ids = []
    num_paginas = len(paginas_datos)

    for idx_pag, lote in enumerate(paginas_datos, start=1):
        lineas_cmd = []
        lineas_cmd.append("0.06 0.09 0.16 rg")
        lineas_cmd.append(f"BT /F2 14 Tf 30 572 Td ({esc_pdf('REPORTE OFICIAL DE INVENTARIO - LIQUIDCCS')}) Tj ET")
        sub = (
            f"Fecha: {fecha_actual} | BCV: {bcv_str} | Reposicion: {repo_str} | "
            f"Articulos: {len(productos)} | Pagina {idx_pag}/{num_paginas}"
        )
        if filtro_aplicado:
            sub += f" | Filtro: {filtro_aplicado}"
        lineas_cmd.append("0.28 0.33 0.41 rg")
        lineas_cmd.append(f"BT /F1 8 Tf 30 556 Td ({esc_pdf(sub)}) Tj ET")

        y_top = 536
        lineas_cmd.append("0.06 0.09 0.16 rg")
        lineas_cmd.append(f"30 {y_top} 732 16 re f")
        lineas_cmd.append("1 1 1 rg")
        lineas_cmd.append(f"BT /F2 8 Tf 35 {y_top + 4} Td ({esc_pdf('SKU')}) Tj ET")
        lineas_cmd.append(f"BT /F2 8 Tf 90 {y_top + 4} Td ({esc_pdf('DESCRIPCION DEL ARTICULO')}) Tj ET")
        lineas_cmd.append(f"BT /F2 8 Tf 385 {y_top + 4} Td ({esc_pdf('STOCK')}) Tj ET")
        lineas_cmd.append(f"BT /F2 8 Tf 428 {y_top + 4} Td ({esc_pdf('BASE ($)')}) Tj ET")
        lineas_cmd.append(f"BT /F2 8 Tf 490 {y_top + 4} Td ({esc_pdf('AJUST. BCV ($)')}) Tj ET")
        lineas_cmd.append(f"BT /F2 8 Tf 565 {y_top + 4} Td ({esc_pdf('REPOS. (Bs)')}) Tj ET")
        lineas_cmd.append(f"BT /F2 8 Tf 655 {y_top + 4} Td ({esc_pdf('UBICACION')}) Tj ET")

        y = y_top - 14
        for idx_fila, p in enumerate(lote):
            if idx_fila % 2 == 1:
                lineas_cmd.append("0.97 0.98 0.99 rg")
                lineas_cmd.append(f"30 {y - 3} 732 14 re f")

            cant = p["cantidad"]
            calc = database.calcular_precios_producto(p, tasa_bcv, t_repo)
            base_s = calc["precio_base_str"] if calc["tiene_precio"] else "Sin precio"
            aj_s = calc["precio_venta_bcv_usd_str"] if calc["tiene_precio"] else "Sin precio"
            bs_s = calc["monto_bs_reposicion_str"] if calc["tiene_precio"] else "Sin precio"
            ubic_s = (p["ubicacion_nota"] or "-")[:18]
            nombre_s = (p["nombre"] or "")[:52]

            lineas_cmd.append("0.12 0.16 0.23 rg")
            lineas_cmd.append(f"BT /F2 8 Tf 35 {y} Td ({esc_pdf(p['sku'])}) Tj ET")
            lineas_cmd.append(f"BT /F1 8 Tf 90 {y} Td ({esc_pdf(nombre_s)}) Tj ET")
            lineas_cmd.append("0.02 0.59 0.41 rg" if cant > 0 else "0.86 0.15 0.15 rg")
            lineas_cmd.append(f"BT /F2 8 Tf 392 {y} Td ({esc_pdf(str(cant))}) Tj ET")
            lineas_cmd.append("0.12 0.16 0.23 rg")
            lineas_cmd.append(f"BT /F1 8 Tf 428 {y} Td ({esc_pdf(base_s)}) Tj ET")
            lineas_cmd.append(f"BT /F2 8 Tf 490 {y} Td ({esc_pdf(aj_s)}) Tj ET")
            lineas_cmd.append(f"BT /F1 8 Tf 565 {y} Td ({esc_pdf(bs_s)}) Tj ET")
            lineas_cmd.append(f"BT /F1 8 Tf 655 {y} Td ({esc_pdf(ubic_s)}) Tj ET")
            y -= 14

        if idx_pag == num_paginas:
            resumen = (
                f"RESUMEN TOTAL: Stock fisico: {total_unidades} unidades | "
                f"Valor Ajustado BCV: ${total_valor_bcv_usd:,.2f} USD ({total_bs_str})"
            )
            lineas_cmd.append("0.06 0.09 0.16 rg")
            lineas_cmd.append(f"BT /F2 9 Tf 30 {max(28, y - 10)} Td ({esc_pdf(resumen)}) Tj ET")

        stream_bytes = "\n".join(lineas_cmd).encode("latin-1", errors="replace")
        content_id = agregar_objeto(
            f"<< /Length {len(stream_bytes)} >>\nstream\n".encode("ascii") + stream_bytes + b"\nendstream"
        )
        page_dict = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 792 612] "
            f"/Resources << /Font << /F1 {font_reg_id} 0 R /F2 {font_bold_id} 0 R >> >> "
            f"/Contents {content_id} 0 R >>"
        ).encode("ascii")
        page_id = agregar_objeto(page_dict)
        page_ids.append(page_id)

    kids_str = " ".join(f"{pid} 0 R" for pid in page_ids)
    objetos_pdf[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objetos_pdf[1] = f"<< /Type /Pages /Kids [{kids_str}] /Count {len(page_ids)} >>".encode("ascii")

    salida = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for idx, obj_bytes in enumerate(objetos_pdf, start=1):
        offsets.append(len(salida))
        salida.extend(f"{idx} 0 obj\n".encode("ascii"))
        salida.extend(obj_bytes)
        salida.extend(b"\nendobj\n")

    xref_pos = len(salida)
    salida.extend(f"xref\n0 {len(objetos_pdf) + 1}\n".encode("ascii"))
    salida.extend(b"0000000000 65535 f \n")
    for off in offsets:
        salida.extend(f"{off:010d} 00000 n \n".encode("ascii"))

    salida.extend(
        f"trailer\n<< /Size {len(objetos_pdf) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("ascii")
    )

    with open(pdf_path, "wb") as f:
        f.write(salida)

    return pdf_path


def exportar_inventario_pdf(
    productos: List[Dict[str, Any]],
    tasa_bcv: float,
    tasa_reposicion: Optional[float] = None,
    filtro_aplicado: str = "",
) -> str:
    """
    Genera un archivo PDF profesional apaisado (landscape) con los precios calculados por arbitraje.
    Utiliza ReportLab si está disponible en PC, o el motor PDF puro Python en Android APK.
    """
    t_repo = _resolver_tasa_repo(tasa_reposicion)
    export_dir = get_export_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_filename = f"Inventario_{timestamp}.pdf"
    pdf_path = os.path.join(export_dir, pdf_filename)

    try:
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=landscape(letter),
            rightMargin=25,
            leftMargin=25,
            topMargin=25,
            bottomMargin=25,
        )

        elements = []
        styles = getSampleStyleSheet()

        titulo_style = ParagraphStyle(
            "TituloDoc",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=21,
            textColor=colors.HexColor("#0F172A"),
            alignment=0,
        )
        subtitulo_style = ParagraphStyle(
            "SubtituloDoc",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#475569"),
        )
        cell_style = ParagraphStyle(
            "CellText",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#1E293B"),
        )
        cell_bold_style = ParagraphStyle(
            "CellBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#0F172A"),
        )
        header_cell_style = ParagraphStyle(
            "HeaderCell",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white,
        )

        fecha_actual = datetime.now().strftime("%d/%m/%Y %I:%M %p")
        bcv_str = database.formatear_bs(tasa_bcv)
        repo_str = database.formatear_bs(t_repo)

        elements.append(Paragraph("REPORTE OFICIAL DE INVENTARIO Y ARBITRAJE CAMBIARIO", titulo_style))
        filtro_info = f" | Filtro: {filtro_aplicado}" if filtro_aplicado else ""
        elements.append(
            Paragraph(
                f"Fecha: <b>{fecha_actual}</b> | BCV: <b>{bcv_str}</b> | Reposición: <b>{repo_str}</b> | "
                f"Artículos: <b>{len(productos)}</b>{filtro_info}",
                subtitulo_style,
            )
        )
        elements.append(Spacer(1, 12))

        headers = [
            Paragraph("SKU", header_cell_style),
            Paragraph("DESCRIPCIÓN DEL ARTÍCULO", header_cell_style),
            Paragraph("STOCK", header_cell_style),
            Paragraph("BASE ($)", header_cell_style),
            Paragraph("AJUST. BCV ($)", header_cell_style),
            Paragraph("REPOSICIÓN (Bs)", header_cell_style),
            Paragraph("COSTO ($)", header_cell_style),
            Paragraph("UBICACIÓN / NOTA", header_cell_style),
        ]

        data = [headers]
        total_unidades = 0
        total_valor_bcv_usd = 0.0
        total_valor_bs_repo = 0.0

        for p in productos:
            cant = p["cantidad"]
            total_unidades += cant
            calc = database.calcular_precios_producto(p, tasa_bcv, t_repo)

            if cant > 0 and calc["tiene_precio"]:
                total_valor_bcv_usd += calc["precio_venta_bcv_usd"] * cant
                total_valor_bs_repo += calc["monto_bs_reposicion"] * cant

            costo_usd_str = database.formatear_usd(p["costo_usd"]) if p.get("costo_usd") else "-"
            ubicacion = p["ubicacion_nota"] or "-"
            stock_texto = f"<b>{cant}</b>" if cant > 0 else "<font color='#DC2626'><b>0</b></font>"

            data.append(
                [
                    Paragraph(p["sku"], cell_bold_style),
                    Paragraph(p["nombre"], cell_style),
                    Paragraph(stock_texto, cell_style),
                    Paragraph(calc["precio_base_str"], cell_style),
                    Paragraph(f"<b>{calc['precio_venta_bcv_usd_str']}</b>", cell_style),
                    Paragraph(calc["monto_bs_reposicion_str"], cell_style),
                    Paragraph(costo_usd_str, cell_style),
                    Paragraph(ubicacion, cell_style),
                ]
            )

        col_widths = [55, 255, 42, 60, 70, 90, 55, 115]
        t = Table(data, colWidths=col_widths, repeatRows=1)
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#FFFFFF"), colors.HexColor("#F8FAFC")]),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        elements.append(t)
        elements.append(Spacer(1, 14))

        resumen_text = (
            f"<b>RESUMEN GENERAL:</b> Unidades en existencia física: <b>{total_unidades}</b> | "
            f"Valoración Ajustada BCV: <b>${total_valor_bcv_usd:,.2f} USD</b> "
            f"(<b>{database.formatear_bs(total_valor_bs_repo)}</b>)"
        )
        elements.append(Paragraph(resumen_text, subtitulo_style))

        doc.build(elements)
        return pdf_path
    except Exception:
        return _generar_pdf_puro_python(pdf_path, productos, tasa_bcv, t_repo, filtro_aplicado)


def exportar_inventario_html(
    productos: List[Dict[str, Any]],
    tasa_bcv: float,
    tasa_reposicion: Optional[float] = None,
) -> str:
    """
    Genera un archivo HTML optimizado para imprimir desde el navegador (Ctrl+P o menú de impresión móvil).
    """
    t_repo = _resolver_tasa_repo(tasa_reposicion)
    export_dir = get_export_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    html_filename = f"Inventario_Imprimir_{timestamp}.html"
    html_path = os.path.join(export_dir, html_filename)

    fecha_actual = datetime.now().strftime("%d/%m/%Y %I:%M %p")
    bcv_str = database.formatear_bs(tasa_bcv)
    repo_str = database.formatear_bs(t_repo)

    filas_html = []
    total_unidades = 0
    total_valor_bcv_usd = 0.0
    total_valor_bs_repo = 0.0

    for p in productos:
        cant = p["cantidad"]
        total_unidades += cant
        calc = database.calcular_precios_producto(p, tasa_bcv, t_repo)

        if cant > 0 and calc["tiene_precio"]:
            total_valor_bcv_usd += calc["precio_venta_bcv_usd"] * cant
            total_valor_bs_repo += calc["monto_bs_reposicion"] * cant

        costo_usd = database.formatear_usd(p["costo_usd"]) if p.get("costo_usd") else "-"
        ubicacion = p["ubicacion_nota"] or "-"
        badge_class = "badge-stock" if cant > 0 else "badge-empty"

        fila = f"""
        <tr>
            <td class="sku">{p['sku']}</td>
            <td class="nombre">{p['nombre']}</td>
            <td class="cant"><span class="{badge_class}">{cant}</span></td>
            <td class="precio">{calc['precio_base_str']}</td>
            <td class="precio-bcv">{calc['precio_venta_bcv_usd_str']}</td>
            <td class="precio-bs">{calc['monto_bs_reposicion_str']}</td>
            <td class="costo">{costo_usd}</td>
            <td class="ubicacion">{ubicacion}</td>
        </tr>
        """
        filas_html.append(fila)

    total_bs_str = database.formatear_bs(total_valor_bs_repo)

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte de Inventario - LiquidCCS</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            margin: 20px;
            color: #1e293b;
            background-color: #ffffff;
        }}
        .header {{ border-bottom: 2px solid #0f172a; padding-bottom: 12px; margin-bottom: 16px; }}
        h1 {{ margin: 0 0 6px 0; font-size: 20px; color: #0f172a; text-transform: uppercase; }}
        .meta {{ font-size: 13px; color: #64748b; }}
        .meta strong {{ color: #0f172a; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 10px; }}
        th {{ background-color: #0f172a; color: white; text-align: left; padding: 8px 6px; font-size: 11px; text-transform: uppercase; }}
        td {{ padding: 6px; border-bottom: 1px solid #e2e8f0; }}
        tr:nth-child(even) {{ background-color: #f8fafc; }}
        .sku {{ font-weight: bold; color: #2563eb; width: 75px; }}
        .cant {{ text-align: center; width: 55px; }}
        .badge-stock {{ background: #dcfce7; color: #15803d; padding: 2px 6px; border-radius: 4px; font-weight: bold; }}
        .badge-empty {{ background: #fee2e2; color: #b91c1c; padding: 2px 6px; border-radius: 4px; font-weight: bold; }}
        .precio {{ font-weight: 600; text-align: right; width: 78px; }}
        .precio-bcv {{ font-weight: bold; color: #047857; text-align: right; width: 85px; }}
        .precio-bs {{ color: #0284c7; font-weight: 600; text-align: right; width: 105px; }}
        .costo {{ color: #64748b; text-align: right; width: 70px; }}
        .ubicacion {{ color: #475569; width: 110px; font-size: 11px; }}
        .footer {{ margin-top: 20px; padding-top: 12px; border-top: 2px solid #e2e8f0; font-size: 13px; font-weight: 500; }}
        .no-print-bar {{ margin-bottom: 15px; padding: 10px; background: #e0f2fe; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; }}
        button {{ background: #0284c7; color: white; border: none; padding: 8px 16px; border-radius: 6px; font-weight: bold; cursor: pointer; }}
        button:hover {{ background: #0369a1; }}
        @media print {{
            .no-print-bar {{ display: none; }}
            body {{ margin: 0; }}
            th {{ background-color: #0f172a !important; -webkit-print-color-adjust: exact; }}
        }}
    </style>
</head>
<body>
    <div class="no-print-bar">
        <span><strong>Vista previa de impresión de Inventario</strong></span>
        <button onclick="window.print()">Imprimir Reporte</button>
    </div>
    <div class="header">
        <h1>Reporte de Inventario - LiquidCCS</h1>
        <div class="meta">
            Fecha: <strong>{fecha_actual}</strong> |
            BCV: <strong>{bcv_str}</strong> |
            Reposición: <strong>{repo_str}</strong> |
            Artículos listados: <strong>{len(productos)}</strong>
        </div>
    </div>

    <table>
        <thead>
            <tr>
                <th>SKU</th>
                <th>Descripción del Producto</th>
                <th style="text-align:center;">Stock</th>
                <th style="text-align:right;">Base ($)</th>
                <th style="text-align:right;">Ajust. BCV ($)</th>
                <th style="text-align:right;">Reposición (Bs)</th>
                <th style="text-align:right;">Costo ($)</th>
                <th>Ubicación / Nota</th>
            </tr>
        </thead>
        <tbody>
            {"".join(filas_html)}
        </tbody>
    </table>

    <div class="footer">
        <strong>RESUMEN:</strong> Unidades físicas en stock: <strong>{total_unidades}</strong> |
        Valoración Ajustada BCV: <strong>${total_valor_bcv_usd:,.2f} USD</strong> ({total_bs_str})
    </div>
</body>
</html>"""

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return html_path


def generar_resumen_texto(
    productos: List[Dict[str, Any]],
    tasa_bcv: float,
    tasa_reposicion: Optional[float] = None,
) -> str:
    """Genera un listado en texto limpio con Precio Base, Ajustado BCV y Total Bs Reposición."""
    t_repo = _resolver_tasa_repo(tasa_reposicion)
    fecha_actual = datetime.now().strftime("%d/%m/%Y %I:%M %p")
    lineas = [
        f"*INVENTARIO LIQUIDCCS* ({fecha_actual})",
        f"BCV: {database.formatear_bs(tasa_bcv)} | Reposición: {database.formatear_bs(t_repo)} | Artículos: {len(productos)}",
        "-" * 42,
    ]
    for p in productos:
        cant = p["cantidad"]
        calc = database.calcular_precios_producto(p, tasa_bcv, t_repo)
        if calc["tiene_precio"]:
            precio_txt = (
                f"Base: {calc['precio_base_str']} | "
                f"BCV Ajust.: {calc['precio_venta_bcv_usd_str']} | "
                f"{calc['monto_bs_reposicion_str']}"
            )
        else:
            precio_txt = "Sin precio"
        lineas.append(f"• [{p['sku']}] {p['nombre']} | Stock: {cant} | {precio_txt}")
    return "\n".join(lineas)
