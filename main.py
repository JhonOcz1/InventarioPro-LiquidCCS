"""
main.py - Aplicación Móvil (Android APK) y de Escritorio (PC) de Inventario con Python, SQLite y Flet
Optimizada para arranque instantáneo, paginación fluida, actualización quirúrgica de tarjetas
y adaptabilidad total en pantallas de celular (360px+) y monitores de escritorio.
"""

import os
import sys
import math
import threading
import webbrowser
import flet as ft
from typing import Dict, Any

import database
import dolar_service
import export_service

# Inicialización obligatoria de SQLite e índices
database.inicializar_bd()

ITEMS_POR_PAGINA = 40


def main(page: ft.Page):
    # Configuración de ventana y tema claro moderno
    page.title = "Sistema de Inventario - LiquidCCS"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = "#F8FAFC"
    page.padding = 12
    page.spacing = 10

    # Dimensiones iniciales para prueba en escritorio
    if hasattr(page, "window") and page.window is not None:
        page.window.width = 1050
        page.window.height = 820
        page.window.min_width = 360
        page.window.min_height = 600

    # Estado reactivo en memoria (arranque instantáneo desde caché SQLite en 0ms)
    estado = {
        "filtro_texto": "",
        "categoria_filtro": "todos",  # 'todos', 'stock', 'agotados'
        "pagina_actual": 1,
        "total_paginas": 1,
        "tasa_datos": database.obtener_tasas_cache(),
        "productos_filtrados": []
    }

    # Referencias en memoria a los controles de cada tarjeta visible para actualización instantánea (+/-)
    tarjetas_ui_refs: Dict[int, Dict[str, Any]] = {}

    def obtener_ancho_modal() -> int:
        """Calcula un ancho de ventana modal adaptable tanto a celular (360px) como a PC."""
        ancho_pag = getattr(page, "width", None) or 480
        return max(290, min(int(ancho_pag) - 40, 480))

    # =========================================================================
    # COMPONENTES DE NOTIFICACIÓN
    # =========================================================================
    def notificar(mensaje: str, es_error: bool = False):
        """Muestra una barra de notificación temporal en la pantalla."""
        sb = ft.SnackBar(
            content=ft.Text(mensaje, color=ft.Colors.WHITE, weight=ft.FontWeight.W_500, size=13),
            bgcolor="#EF4444" if es_error else "#059669",
            duration=2800
        )
        page.show_dialog(sb)

    # =========================================================================
    # LÓGICA DE DATOS Y TASAS (ASÍNCRONA NO BLOQUEANTE)
    # =========================================================================
    def refrescar_tasa(e=None):
        """Consulta la API de DolarApi en un hilo secundario sin congelar la interfaz."""
        btn_refresh_tasa.disabled = True
        lbl_fecha_tasa.value = "Sincronizando tasa con DolarApi..."
        page.update()

        def tarea_red():
            tasa_actualizada = dolar_service.obtener_tasa_dolar(forzar_red=True)
            estado["tasa_datos"] = tasa_actualizada
            actualizar_tarjeta_tasa()
            renderizar_pagina_actual()
            btn_refresh_tasa.disabled = False
            page.update()

            if e is not None:
                if tasa_actualizada["online"]:
                    notificar(f"Tasa BCV actualizada: Bs. {tasa_actualizada['bcv']:,.2f}")
                else:
                    notificar("Modo sin internet: Usando última tasa guardada en SQLite.", es_error=True)

        threading.Thread(target=tarea_red, daemon=True).start()

    # =========================================================================
    # WIDGETS DE CABECERA Y RESUMEN KPI
    # =========================================================================
    txt_tasa_bcv = ft.Text("BCV: ...", size=15, weight=ft.FontWeight.BOLD, color="#0F172A")
    txt_tasa_paralelo = ft.Text("Paralelo: ...", size=13, weight=ft.FontWeight.W_600, color="#475569")
    badge_estado_red = ft.Container(
        content=ft.Text("CACHÉ", size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
        bgcolor="#F59E0B",
        padding=ft.Padding.symmetric(horizontal=8, vertical=2),
        border_radius=12
    )
    lbl_fecha_tasa = ft.Text("", size=11, color="#64748B")

    btn_refresh_tasa = ft.IconButton(
        icon=ft.Icons.REFRESH_ROUNDED,
        icon_color="#0284C7",
        tooltip="Actualizar tasa del dólar ahora",
        on_click=refrescar_tasa
    )

    def actualizar_tarjeta_tasa():
        t = estado["tasa_datos"]
        bcv_fmt = f"Bs. {t['bcv']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        par_fmt = f"Bs. {t['paralelo']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        txt_tasa_bcv.value = f"BCV: {bcv_fmt}"
        txt_tasa_paralelo.value = f"Paralelo: {par_fmt}"
        lbl_fecha_tasa.value = t["mensaje"]

        if t.get("online"):
            badge_estado_red.bgcolor = "#10B981"
            badge_estado_red.content.value = "EN LÍNEA"
        else:
            badge_estado_red.bgcolor = "#F59E0B"
            badge_estado_red.content.value = "OFFLINE"

    actualizar_tarjeta_tasa()

    card_tasa_dolar = ft.Container(
        content=ft.Row(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.CURRENCY_EXCHANGE_ROUNDED, color="#0284C7", size=26),
                        ft.Column(
                            controls=[
                                ft.Row(controls=[
                                    ft.Text("TASA DEL DÓLAR (VZLA)", size=11, weight=ft.FontWeight.BOLD, color="#0284C7"),
                                    badge_estado_red
                                ], spacing=6),
                                ft.Row(controls=[txt_tasa_bcv, txt_tasa_paralelo], spacing=10, wrap=True),
                                lbl_fecha_tasa
                            ],
                            spacing=1,
                            alignment=ft.MainAxisAlignment.CENTER
                        )
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    expand=True
                ),
                btn_refresh_tasa
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        ),
        bgcolor=ft.Colors.WHITE,
        border=ft.Border.all(1, "#E2E8F0"),
        border_radius=12,
        padding=10
    )

    # Métricas KPI del Inventario (2 columnas en celular, 4 en PC)
    txt_kpi_total_prods = ft.Text("0", size=16, weight=ft.FontWeight.BOLD, color="#0F172A")
    txt_kpi_total_stock = ft.Text("0", size=16, weight=ft.FontWeight.BOLD, color="#059669")
    txt_kpi_con_stock = ft.Text("0", size=16, weight=ft.FontWeight.BOLD, color="#0284C7")
    txt_kpi_agotados = ft.Text("0", size=16, weight=ft.FontWeight.BOLD, color="#DC2626")

    def kpi_box(titulo: str, txt_control: ft.Text, icon_name, color_accent: str):
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(icon_name, color=color_accent, size=22),
                    ft.Column(
                        controls=[
                            ft.Text(titulo, size=10, color="#64748B", weight=ft.FontWeight.W_500),
                            txt_control
                        ],
                        spacing=0
                    )
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER
            ),
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.all(1, "#E2E8F0"),
            border_radius=10,
            padding=8,
            col={"xs": 6, "sm": 6, "md": 3}
        )

    barra_kpis = ft.ResponsiveRow(
        controls=[
            kpi_box("Artículos", txt_kpi_total_prods, ft.Icons.CATEGORY_OUTLINED, "#0F172A"),
            kpi_box("Unidades Stock", txt_kpi_total_stock, ft.Icons.INVENTORY_2_OUTLINED, "#059669"),
            kpi_box("Con Stock", txt_kpi_con_stock, ft.Icons.CHECK_CIRCLE_OUTLINE, "#0284C7"),
            kpi_box("Agotados", txt_kpi_agotados, ft.Icons.HIGHLIGHT_OFF_ROUNDED, "#DC2626")
        ],
        spacing=8,
        run_spacing=8
    )

    def actualizar_kpis():
        stats = database.obtener_resumen_estadisticas()
        txt_kpi_total_prods.value = str(stats["total_items"])
        txt_kpi_total_stock.value = f"{stats['total_unidades']} u."
        txt_kpi_con_stock.value = str(stats["items_con_stock"])
        txt_kpi_agotados.value = str(stats["items_agotados"])

    actualizar_kpis()

    # =========================================================================
    # BARRA DE BÚSQUEDA Y FILTRADO EN TIEMPO REAL
    # =========================================================================
    def on_busqueda_change(e):
        estado["filtro_texto"] = input_busqueda.value or ""
        estado["pagina_actual"] = 1
        recargar_datos_y_renderizar()

    def limpiar_busqueda(e):
        if not input_busqueda.value and not estado["filtro_texto"]:
            return
        input_busqueda.value = ""
        estado["filtro_texto"] = ""
        estado["pagina_actual"] = 1
        recargar_datos_y_renderizar()

    input_busqueda = ft.TextField(
        hint_text="Buscar por nombre, SKU (ej. INV-001) o ubicación...",
        prefix_icon=ft.Icons.SEARCH,
        suffix=ft.IconButton(ft.Icons.CLEAR, on_click=limpiar_busqueda, tooltip="Limpiar búsqueda"),
        bgcolor=ft.Colors.WHITE,
        border_color="#94A3B8",
        focused_border_color="#0284C7",
        border_radius=10,
        content_padding=10,
        text_size=13,
        on_change=on_busqueda_change
    )

    def cambiar_filtro_categoria(categoria: str):
        estado["categoria_filtro"] = categoria
        estado["pagina_actual"] = 1
        btn_chip_todos.bgcolor = "#0F172A" if categoria == "todos" else ft.Colors.WHITE
        btn_chip_todos.content.color = ft.Colors.WHITE if categoria == "todos" else "#334155"

        btn_chip_stock.bgcolor = "#059669" if categoria == "stock" else ft.Colors.WHITE
        btn_chip_stock.content.color = ft.Colors.WHITE if categoria == "stock" else "#334155"

        btn_chip_agotados.bgcolor = "#DC2626" if categoria == "agotados" else ft.Colors.WHITE
        btn_chip_agotados.content.color = ft.Colors.WHITE if categoria == "agotados" else "#334155"

        recargar_datos_y_renderizar()

    btn_chip_todos = ft.Container(
        content=ft.Text("Todos", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
        bgcolor="#0F172A",
        border=ft.Border.all(1, "#CBD5E1"),
        border_radius=20,
        padding=ft.Padding.symmetric(horizontal=12, vertical=5),
        on_click=lambda e: cambiar_filtro_categoria("todos"),
        ink=True
    )

    btn_chip_stock = ft.Container(
        content=ft.Text("Con Stock", size=12, weight=ft.FontWeight.BOLD, color="#334155"),
        bgcolor=ft.Colors.WHITE,
        border=ft.Border.all(1, "#CBD5E1"),
        border_radius=20,
        padding=ft.Padding.symmetric(horizontal=12, vertical=5),
        on_click=lambda e: cambiar_filtro_categoria("stock"),
        ink=True
    )

    btn_chip_agotados = ft.Container(
        content=ft.Text("Agotados", size=12, weight=ft.FontWeight.BOLD, color="#334155"),
        bgcolor=ft.Colors.WHITE,
        border=ft.Border.all(1, "#CBD5E1"),
        border_radius=20,
        padding=ft.Padding.symmetric(horizontal=12, vertical=5),
        on_click=lambda e: cambiar_filtro_categoria("agotados"),
        ink=True
    )

    fila_filtros = ft.Row(
        controls=[btn_chip_todos, btn_chip_stock, btn_chip_agotados],
        spacing=6,
        wrap=True
    )

    lbl_contador_resultados = ft.Text("", size=12, color="#475569", weight=ft.FontWeight.W_600)

    # =========================================================================
    # CONTROLES DE PAGINACIÓN RÁPIDA
    # =========================================================================
    lbl_pagina_info = ft.Text("Página 1 de 1", size=12, weight=ft.FontWeight.W_600, color="#334155")

    def ir_pagina_anterior(e):
        if estado["pagina_actual"] > 1:
            estado["pagina_actual"] -= 1
            renderizar_pagina_actual()

    def ir_pagina_siguiente(e):
        if estado["pagina_actual"] < estado["total_paginas"]:
            estado["pagina_actual"] += 1
            renderizar_pagina_actual()

    btn_pag_ant = ft.IconButton(
        icon=ft.Icons.CHEVRON_LEFT_ROUNDED,
        icon_color="#0F172A",
        tooltip="Página anterior",
        on_click=ir_pagina_anterior
    )
    btn_pag_sig = ft.IconButton(
        icon=ft.Icons.CHEVRON_RIGHT_ROUNDED,
        icon_color="#0F172A",
        tooltip="Página siguiente",
        on_click=ir_pagina_siguiente
    )

    barra_paginacion = ft.Container(
        content=ft.Row(
            controls=[
                btn_pag_ant,
                lbl_pagina_info,
                btn_pag_sig
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8
        ),
        bgcolor=ft.Colors.WHITE,
        border=ft.Border.all(1, "#E2E8F0"),
        border_radius=10,
        padding=ft.Padding.symmetric(horizontal=8, vertical=2)
    )

    # =========================================================================
    # LISTA DE PRODUCTOS (CON ACTUALIZACIÓN QUIRÚRGICA IN-PLACE)
    # =========================================================================
    lista_cards_container = ft.ListView(
        controls=[],
        spacing=8,
        expand=True
    )

    def ajustar_stock_rapido(producto_id: int, delta: int):
        """
        Actualiza el stock en SQLite y modifica únicamente el nodo visual de la tarjeta
        en memoria (sin reconstruir toda la lista ni perder el scroll).
        """
        ref = tarjetas_ui_refs.get(producto_id)
        if not ref:
            return

        cant_actual = ref["datos"]["cantidad"]
        nueva_cantidad = max(0, cant_actual + delta)
        if nueva_cantidad == cant_actual:
            return

        database.actualizar_solo_cantidad(producto_id, nueva_cantidad)
        ref["datos"]["cantidad"] = nueva_cantidad
        actualizar_kpis()

        # Si hay un filtro activo de stock/agotados y el artículo cambió de estado, recargar lista
        if (estado["categoria_filtro"] == "stock" and nueva_cantidad == 0) or (
            estado["categoria_filtro"] == "agotados" and nueva_cantidad > 0
        ):
            recargar_datos_y_renderizar()
            return

        # Actualización quirúrgica instantánea en la tarjeta actual
        es_disp = nueva_cantidad > 0
        badge_st: ft.Container = ref["badge_stock"]
        badge_st.bgcolor = "#DCFCE7" if es_disp else "#FEE2E2"
        badge_st.content.value = f"{nueva_cantidad} en stock" if es_disp else "Agotado (0)"
        badge_st.content.color = "#15803D" if es_disp else "#B91C1C"

        txt_num: ft.Text = ref["txt_cant"]
        txt_num.value = str(nueva_cantidad)
        page.update()

    def confirmar_eliminar_producto(producto_id: int):
        """Muestra un diálogo de confirmación antes de eliminar un artículo."""
        p = database.obtener_producto_por_id(producto_id)
        if not p:
            return

        def cancelar(ev):
            page.pop_dialog()
            page.update()

        def ejecutar_eliminacion(ev):
            database.eliminar_producto(producto_id)
            page.pop_dialog()
            actualizar_kpis()
            recargar_datos_y_renderizar()
            notificar(f"Artículo '{p['sku']}' eliminado correctamente.")

        dlg = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color="#DC2626"),
                ft.Text("Confirmar Eliminación", size=15, weight=ft.FontWeight.BOLD)
            ], spacing=8),
            content=ft.Container(
                content=ft.Text(
                    f"¿Deseas eliminar permanentemente este artículo del inventario?\n\n{p['sku']} - {p['nombre']}",
                    size=13,
                    color="#334155"
                ),
                width=obtener_ancho_modal()
            ),
            actions=[
                ft.TextButton(content="Cancelar", on_click=cancelar),
                ft.FilledButton(
                    content="Eliminar",
                    icon=ft.Icons.DELETE_FOREVER_ROUNDED,
                    bgcolor="#DC2626",
                    color=ft.Colors.WHITE,
                    on_click=ejecutar_eliminacion
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        page.show_dialog(dlg)

    def crear_tarjeta_producto(p: Dict[str, Any]) -> ft.Container:
        """Crea una tarjeta adaptable a pantallas de celular (360px+) y escritorio."""
        tasa_bcv = estado["tasa_datos"]["bcv"]
        cant = p["cantidad"]
        es_disponible = cant > 0

        p_detal_usd, p_detal_bs = dolar_service.formatear_precios(p["precio_detal_usd"], tasa_bcv)
        p_desc_usd, p_desc_bs = dolar_service.formatear_precios(p["precio_descuento_usd"], tasa_bcv)
        costo_usd, _ = dolar_service.formatear_precios(p["costo_usd"], tasa_bcv)

        ubicacion_txt = p["ubicacion_nota"] or "Sin ubicación"

        badge_stock = ft.Container(
            content=ft.Text(
                f"{cant} en stock" if es_disponible else "Agotado (0)",
                size=11,
                weight=ft.FontWeight.BOLD,
                color="#15803D" if es_disponible else "#B91C1C"
            ),
            bgcolor="#DCFCE7" if es_disponible else "#FEE2E2",
            border_radius=6,
            padding=ft.Padding.symmetric(horizontal=8, vertical=3)
        )

        badge_sku = ft.Container(
            content=ft.Text(p["sku"], size=11, weight=ft.FontWeight.BOLD, color="#1E40AF"),
            bgcolor="#DBEAFE",
            border_radius=6,
            padding=ft.Padding.symmetric(horizontal=8, vertical=3)
        )

        txt_cant_rapida = ft.Text(str(cant), size=13, weight=ft.FontWeight.BOLD, color="#0F172A")

        tarjetas_ui_refs[p["id"]] = {
            "datos": p,
            "badge_stock": badge_stock,
            "txt_cant": txt_cant_rapida
        }

        return ft.Container(
            content=ft.Column(
                controls=[
                    # Fila 1: SKU + Stock + Botones Editar / Eliminar
                    ft.Row(
                        controls=[
                            ft.Row(controls=[badge_sku, badge_stock], spacing=6),
                            ft.Row(
                                controls=[
                                    ft.TextButton(
                                        content="Editar",
                                        icon=ft.Icons.EDIT_OUTLINED,
                                        icon_color="#0284C7",
                                        tooltip="Editar artículo",
                                        on_click=lambda e, pid=p["id"]: abrir_modal_detalle(pid)
                                    ),
                                    ft.TextButton(
                                        content="Eliminar",
                                        icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
                                        icon_color="#DC2626",
                                        tooltip="Eliminar artículo",
                                        on_click=lambda e, pid=p["id"]: confirmar_eliminar_producto(pid)
                                    )
                                ],
                                spacing=0
                            )
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        wrap=True
                    ),
                    # Fila 2: Nombre del producto
                    ft.Text(
                        p["nombre"],
                        size=14,
                        weight=ft.FontWeight.W_700,
                        color="#0F172A"
                    ),
                    ft.Divider(height=1, color="#F1F5F9"),
                    # Fila 3: Precios responsivos (2x2 en celular estrecho, 4 columnas en PC)
                    ft.ResponsiveRow(
                        controls=[
                            ft.Column(
                                controls=[
                                    ft.Text("PRECIO DETAL", size=10, color="#64748B", weight=ft.FontWeight.W_600),
                                    ft.Text(p_detal_usd, size=14, weight=ft.FontWeight.BOLD, color="#059669"),
                                    ft.Text(p_detal_bs, size=11, color="#0284C7", weight=ft.FontWeight.W_600)
                                ],
                                spacing=1,
                                col={"xs": 6, "sm": 3}
                            ),
                            ft.Column(
                                controls=[
                                    ft.Text("PRECIO DESC.", size=10, color="#64748B", weight=ft.FontWeight.W_600),
                                    ft.Text(p_desc_usd, size=13, weight=ft.FontWeight.W_600, color="#334155"),
                                    ft.Text(p_desc_bs, size=11, color="#64748B")
                                ],
                                spacing=1,
                                col={"xs": 6, "sm": 3}
                            ),
                            ft.Column(
                                controls=[
                                    ft.Text("COSTO BASE", size=10, color="#64748B", weight=ft.FontWeight.W_600),
                                    ft.Text(costo_usd, size=13, weight=ft.FontWeight.W_600, color="#64748B")
                                ],
                                spacing=1,
                                col={"xs": 6, "sm": 3}
                            ),
                            ft.Row(
                                controls=[
                                    ft.IconButton(
                                        icon=ft.Icons.REMOVE_CIRCLE_OUTLINE,
                                        icon_color="#64748B",
                                        icon_size=22,
                                        tooltip="Restar 1 unidad",
                                        on_click=lambda e, pid=p["id"]: ajustar_stock_rapido(pid, -1)
                                    ),
                                    txt_cant_rapida,
                                    ft.IconButton(
                                        icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                                        icon_color="#0284C7",
                                        icon_size=22,
                                        tooltip="Sumar 1 unidad",
                                        on_click=lambda e, pid=p["id"]: ajustar_stock_rapido(pid, 1)
                                    )
                                ],
                                spacing=0,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                col={"xs": 6, "sm": 3}
                            )
                        ],
                        run_spacing=6
                    ),
                    # Fila 4: Ubicación
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.LOCATION_ON_OUTLINED, size=14, color="#64748B"),
                            ft.Text(f"Ubicación / Nota: {ubicacion_txt}", size=11, color="#64748B", weight=ft.FontWeight.W_500)
                        ],
                        spacing=4
                    )
                ],
                spacing=6
            ),
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.all(1, "#E2E8F0"),
            border_radius=12,
            padding=12
        )

    def renderizar_pagina_actual():
        """Dibuja únicamente el bloque de la página activa (máximo 40 tarjetas) para máxima fluidez."""
        prods = estado["productos_filtrados"]
        total = len(prods)
        total_pags = max(1, math.ceil(total / ITEMS_POR_PAGINA))
        estado["total_paginas"] = total_pags
        if estado["pagina_actual"] > total_pags:
            estado["pagina_actual"] = total_pags

        pag = estado["pagina_actual"]
        inicio = (pag - 1) * ITEMS_POR_PAGINA
        fin = inicio + ITEMS_POR_PAGINA
        lote = prods[inicio:fin]

        tarjetas_ui_refs.clear()
        lista_cards_container.controls.clear()

        if not lote:
            lista_cards_container.controls.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Icon(ft.Icons.SEARCH_OFF_ROUNDED, size=44, color="#94A3B8"),
                            ft.Text("No se encontraron artículos con ese criterio", size=14, color="#64748B")
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8
                    ),
                    padding=36,
                    alignment=ft.Alignment.CENTER
                )
            )
        else:
            for p in lote:
                lista_cards_container.controls.append(crear_tarjeta_producto(p))

        lbl_contador_resultados.value = f"{total} artículos encontrados"
        lbl_pagina_info.value = f"Página {pag} de {total_pags} ({inicio + 1 if total else 0}-{min(fin, total)} de {total})"
        btn_pag_ant.disabled = (pag <= 1)
        btn_pag_sig.disabled = (pag >= total_pags)
        barra_paginacion.visible = (total > ITEMS_POR_PAGINA)
        page.update()

    def recargar_datos_y_renderizar():
        """Consulta SQLite con índices optimizados y actualiza la página actual."""
        solo_stock = (estado["categoria_filtro"] == "stock")
        solo_agotados = (estado["categoria_filtro"] == "agotados")

        estado["productos_filtrados"] = database.obtener_productos(
            filtro=estado["filtro_texto"],
            solo_stock=solo_stock,
            solo_agotados=solo_agotados
        )
        renderizar_pagina_actual()

    # =========================================================================
    # MODAL 1: CARGA DE UN NUEVO ARTÍCULO
    # =========================================================================
    def abrir_modal_nuevo_producto(e=None):
        sku_sugerido = database.obtener_siguiente_sku()

        in_sku = ft.TextField(label="SKU / Código", value=sku_sugerido, border_radius=8, content_padding=10, expand=True)
        in_cantidad = ft.TextField(label="Stock Inicial", value="0", keyboard_type=ft.KeyboardType.NUMBER, border_radius=8, content_padding=10, expand=True)
        in_nombre = ft.TextField(label="Nombre del Artículo *", border_radius=8, content_padding=10, autofocus=True, expand=True)
        in_detal = ft.TextField(label="Precio Detal ($)", hint_text="10.00", keyboard_type=ft.KeyboardType.NUMBER, border_radius=8, content_padding=10, expand=True)
        in_desc = ft.TextField(label="Precio Desc. ($)", hint_text="8.00", keyboard_type=ft.KeyboardType.NUMBER, border_radius=8, content_padding=10, expand=True)
        in_costo = ft.TextField(label="Costo Base ($)", hint_text="4.50", keyboard_type=ft.KeyboardType.NUMBER, border_radius=8, content_padding=10, expand=True)
        in_ubicacion = ft.TextField(label="Ubicación / Nota", hint_text="Depósito, Brian...", border_radius=8, content_padding=10, expand=True)

        txt_preview_bs = ft.Text("Equivalente Detal en Bs: -", size=12, color="#0284C7", weight=ft.FontWeight.W_600)

        def actualizar_preview_bs(ev):
            try:
                val = float(in_detal.value.replace(",", "."))
                bs = val * estado["tasa_datos"]["bcv"]
                bs_fmt = f"Bs. {bs:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                txt_preview_bs.value = f"Equivalente Detal: {bs_fmt} (Tasa BCV)"
            except Exception:
                txt_preview_bs.value = "Equivalente Detal en Bs: -"
            page.update()

        in_detal.on_change = actualizar_preview_bs

        def cerrar_dialogo(ev):
            page.pop_dialog()
            page.update()

        def guardar_nuevo_articulo(ev):
            nombre = in_nombre.value.strip()
            sku = in_sku.value.strip()

            if not nombre:
                notificar("El nombre del artículo es obligatorio", es_error=True)
                return
            if not sku:
                notificar("El SKU es obligatorio", es_error=True)
                return

            try:
                cantidad = int(in_cantidad.value.strip() or "0")
            except ValueError:
                notificar("La cantidad debe ser un número entero", es_error=True)
                return

            def parse_float(val):
                if not val or not val.strip():
                    return None
                try:
                    return float(val.strip().replace(",", "."))
                except ValueError:
                    return None

            exito = database.agregar_producto(
                sku=sku,
                nombre=nombre,
                cantidad=cantidad,
                precio_detal=parse_float(in_detal.value),
                precio_descuento=parse_float(in_desc.value),
                costo=parse_float(in_costo.value),
                ubicacion=in_ubicacion.value.strip() or None
            )

            if exito:
                page.pop_dialog()
                actualizar_kpis()
                recargar_datos_y_renderizar()
                notificar(f"Producto '{nombre}' registrado con éxito.")
            else:
                notificar(f"Error: Ya existe un producto activo con el SKU '{sku}'", es_error=True)

        dlg = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.Icons.ADD_BOX_ROUNDED, color="#0284C7"),
                ft.Text("Nuevo Artículo", size=16, weight=ft.FontWeight.BOLD)
            ], spacing=8),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row([in_sku, in_cantidad], spacing=8),
                        ft.Row([in_nombre], spacing=8),
                        ft.Row([in_detal, in_desc], spacing=8),
                        txt_preview_bs,
                        ft.Row([in_costo, in_ubicacion], spacing=8)
                    ],
                    spacing=10,
                    tight=True
                ),
                width=obtener_ancho_modal()
            ),
            actions=[
                ft.TextButton(content="Cancelar", on_click=cerrar_dialogo),
                ft.FilledButton(content="Guardar", icon=ft.Icons.CHECK, bgcolor="#059669", color=ft.Colors.WHITE, on_click=guardar_nuevo_articulo)
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        page.show_dialog(dlg)

    # =========================================================================
    # MODAL 2: DETALLES COMPLETOS Y EDICIÓN DE ARTÍCULO
    # =========================================================================
    def abrir_modal_detalle(producto_id: int):
        p = database.obtener_producto_por_id(producto_id)
        if not p:
            return

        tasa_bcv = estado["tasa_datos"]["bcv"]

        ed_sku = ft.TextField(label="SKU / Código", value=p["sku"], border_radius=8, content_padding=10, expand=True)
        ed_cantidad = ft.TextField(label="Stock Actual", value=str(p["cantidad"]), keyboard_type=ft.KeyboardType.NUMBER, border_radius=8, content_padding=10, expand=True)
        ed_nombre = ft.TextField(label="Nombre del Producto", value=p["nombre"], border_radius=8, content_padding=10, expand=True)
        ed_detal = ft.TextField(label="Precio Detal ($)", value=str(p["precio_detal_usd"]) if p["precio_detal_usd"] is not None else "", keyboard_type=ft.KeyboardType.NUMBER, border_radius=8, content_padding=10, expand=True)
        ed_desc = ft.TextField(label="Precio Desc. ($)", value=str(p["precio_descuento_usd"]) if p["precio_descuento_usd"] is not None else "", keyboard_type=ft.KeyboardType.NUMBER, border_radius=8, content_padding=10, expand=True)
        ed_costo = ft.TextField(label="Costo Base ($)", value=str(p["costo_usd"]) if p["costo_usd"] is not None else "", keyboard_type=ft.KeyboardType.NUMBER, border_radius=8, content_padding=10, expand=True)
        ed_ubicacion = ft.TextField(label="Ubicación / Nota", value=p["ubicacion_nota"] or "", border_radius=8, content_padding=10, expand=True)

        detal_bs_txt = f"Bs. {p['precio_detal_usd'] * tasa_bcv:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if p["precio_detal_usd"] else "-"
        lbl_info_bs = ft.Text(f"Valor Detal en Bolívares: {detal_bs_txt}", size=12, color="#0284C7", weight=ft.FontWeight.W_600)

        def actualizar_preview_edicion(ev):
            try:
                val = float(ed_detal.value.replace(",", "."))
                bs = val * tasa_bcv
                bs_fmt = f"Bs. {bs:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                lbl_info_bs.value = f"Valor Detal en Bolívares: {bs_fmt}"
            except Exception:
                lbl_info_bs.value = "Valor Detal en Bolívares: -"
            page.update()

        ed_detal.on_change = actualizar_preview_edicion

        def cerrar_dialogo(ev):
            page.pop_dialog()
            page.update()

        def guardar_cambios(ev):
            if not ed_nombre.value.strip():
                notificar("El nombre del producto no puede estar vacío", es_error=True)
                return

            try:
                nueva_cant = int(ed_cantidad.value.strip() or "0")
            except ValueError:
                notificar("La cantidad debe ser un número entero", es_error=True)
                return

            def parse_float(val):
                if not val or not val.strip():
                    return None
                try:
                    return float(val.strip().replace(",", "."))
                except ValueError:
                    return None

            exito = database.actualizar_producto(
                producto_id=producto_id,
                sku=ed_sku.value.strip(),
                nombre=ed_nombre.value.strip(),
                cantidad=nueva_cant,
                precio_detal=parse_float(ed_detal.value),
                precio_descuento=parse_float(ed_desc.value),
                costo=parse_float(ed_costo.value),
                ubicacion=ed_ubicacion.value.strip() or None
            )

            if exito:
                page.pop_dialog()
                actualizar_kpis()
                recargar_datos_y_renderizar()
                notificar(f"Artículo {ed_sku.value.strip()} actualizado.")
            else:
                notificar("Error al guardar: verifique que el SKU no esté duplicado.", es_error=True)

        def eliminar_desde_modal(ev):
            page.pop_dialog()
            confirmar_eliminar_producto(producto_id)

        dlg = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.Icons.EDIT_NOTE_ROUNDED, color="#0284C7"),
                ft.Text(f"Editar: {p['sku']}", size=16, weight=ft.FontWeight.BOLD)
            ], spacing=8),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row([ed_sku, ed_cantidad], spacing=8),
                        ft.Row([ed_nombre], spacing=8),
                        ft.Row([ed_detal, ed_desc], spacing=8),
                        lbl_info_bs,
                        ft.Row([ed_costo, ed_ubicacion], spacing=8),
                    ],
                    spacing=10,
                    tight=True
                ),
                width=obtener_ancho_modal()
            ),
            actions=[
                ft.TextButton(content="Eliminar", icon=ft.Icons.DELETE_OUTLINE, icon_color="#DC2626", on_click=eliminar_desde_modal),
                ft.TextButton(content="Cancelar", on_click=cerrar_dialogo),
                ft.FilledButton(content="Guardar", icon=ft.Icons.SAVE_ROUNDED, bgcolor="#0284C7", color=ft.Colors.WHITE, on_click=guardar_cambios)
            ],
            actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )
        page.show_dialog(dlg)

    # =========================================================================
    # MODAL 3: EXPORTACIÓN PARA IMPRESIÓN (PDF, HTML Y RESUMEN MÓVIL)
    # =========================================================================
    def abrir_modal_exportacion(e=None):
        prods_a_exportar = estado["productos_filtrados"] if estado["productos_filtrados"] else database.obtener_productos()
        tasa_bcv = estado["tasa_datos"]["bcv"]

        def generar_y_abrir_pdf(ev):
            pdf_path = export_service.exportar_inventario_pdf(
                productos=prods_a_exportar,
                tasa_bcv=tasa_bcv,
                filtro_aplicado=estado["filtro_texto"]
            )
            page.pop_dialog()
            notificar(f"PDF guardado en: {pdf_path}")
            try:
                if sys.platform.startswith("win"):
                    os.startfile(pdf_path)
                else:
                    webbrowser.open(f"file://{pdf_path}")
            except Exception:
                pass

        def generar_y_abrir_html(ev):
            html_path = export_service.exportar_inventario_html(
                productos=prods_a_exportar,
                tasa_bcv=tasa_bcv
            )
            page.pop_dialog()
            notificar(f"Reporte imprimible guardado: {os.path.basename(html_path)}")
            try:
                webbrowser.open(f"file://{html_path}")
            except Exception:
                pass

        def ver_listado_texto_imprimible(ev):
            page.pop_dialog()
            texto_reporte = export_service.generar_resumen_texto(prods_a_exportar, tasa_bcv)
            campo_texto = ft.TextField(
                value=texto_reporte,
                multiline=True,
                read_only=True,
                min_lines=10,
                max_lines=14,
                text_size=11,
                border_radius=8
            )
            dlg_txt = ft.AlertDialog(
                title=ft.Text("Listado de Inventario para Copiar / Imprimir", size=15, weight=ft.FontWeight.BOLD),
                content=ft.Container(
                    content=campo_texto,
                    width=obtener_ancho_modal()
                ),
                actions=[
                    ft.TextButton(content="Cerrar", on_click=lambda x: page.pop_dialog())
                ]
            )
            page.show_dialog(dlg_txt)

        dlg = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.Icons.PRINT_ROUNDED, color="#0284C7"),
                ft.Text("Exportar / Imprimir Inventario", size=15, weight=ft.FontWeight.BOLD)
            ], spacing=8),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(f"Se exportarán {len(prods_a_exportar)} artículos (Tasa BCV: Bs. {tasa_bcv:,.2f}).", size=12, color="#475569"),
                        ft.Container(
                            content=ft.Row([
                                ft.Icon(ft.Icons.PICTURE_AS_PDF_ROUNDED, color="#DC2626", size=26),
                                ft.Column([
                                    ft.Text("Generar Reporte PDF Profesional", weight=ft.FontWeight.BOLD, size=13),
                                    ft.Text("Formato carta horizontal listo para imprimir o enviar.", size=11, color="#64748B")
                                ], spacing=1, expand=True)
                            ], spacing=10),
                            bgcolor="#F8FAFC",
                            border=ft.Border.all(1, "#E2E8F0"),
                            border_radius=8,
                            padding=10,
                            on_click=generar_y_abrir_pdf,
                            ink=True
                        ),
                        ft.Container(
                            content=ft.Row([
                                ft.Icon(ft.Icons.PRINT_ROUNDED, color="#0284C7", size=26),
                                ft.Column([
                                    ft.Text("Impresión Directa (HTML Navegador)", weight=ft.FontWeight.BOLD, size=13),
                                    ft.Text("Abre la vista de impresión del sistema.", size=11, color="#64748B")
                                ], spacing=1, expand=True)
                            ], spacing=10),
                            bgcolor="#F8FAFC",
                            border=ft.Border.all(1, "#E2E8F0"),
                            border_radius=8,
                            padding=10,
                            on_click=generar_y_abrir_html,
                            ink=True
                        ),
                        ft.Container(
                            content=ft.Row([
                                ft.Icon(ft.Icons.DESCRIPTION_OUTLINED, color="#059669", size=26),
                                ft.Column([
                                    ft.Text("Ver / Copiar Listado en Pantalla (Móvil)", weight=ft.FontWeight.BOLD, size=13),
                                    ft.Text("Ideal en celulares para copiar o compartir por WhatsApp.", size=11, color="#64748B")
                                ], spacing=1, expand=True)
                            ], spacing=10),
                            bgcolor="#F8FAFC",
                            border=ft.Border.all(1, "#E2E8F0"),
                            border_radius=8,
                            padding=10,
                            on_click=ver_listado_texto_imprimible,
                            ink=True
                        )
                    ],
                    spacing=10,
                    tight=True
                ),
                width=obtener_ancho_modal()
            ),
            actions=[
                ft.TextButton(content="Cerrar", on_click=lambda ev: page.pop_dialog())
            ]
        )
        page.show_dialog(dlg)

    # =========================================================================
    # BARRA SUPERIOR DE ACCIONES ADAPTABLE A MÓVIL Y PC
    # =========================================================================
    btn_exportar = ft.FilledTonalButton(
        content="Imprimir / PDF",
        icon=ft.Icons.PRINT_ROUNDED,
        on_click=abrir_modal_exportacion
    )

    btn_nuevo = ft.FilledButton(
        content="Nuevo",
        icon=ft.Icons.ADD_ROUNDED,
        bgcolor="#0F172A",
        color=ft.Colors.WHITE,
        on_click=abrir_modal_nuevo_producto
    )

    barra_superior = ft.Row(
        controls=[
            ft.Row(
                controls=[
                    ft.Icon(ft.Icons.INVENTORY_ROUNDED, color="#0F172A", size=24),
                    ft.Text("Inventario Pro", size=18, weight=ft.FontWeight.BOLD, color="#0F172A")
                ],
                spacing=6
            ),
            ft.Row(
                controls=[btn_exportar, btn_nuevo],
                spacing=6,
                wrap=True
            )
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        wrap=True
    )

    # =========================================================================
    # ENSAMBLAJE DE LA VISTA PRINCIPAL
    # =========================================================================
    page.add(
        barra_superior,
        card_tasa_dolar,
        barra_kpis,
        input_busqueda,
        ft.Row(
            controls=[fila_filtros, lbl_contador_resultados],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            wrap=True
        ),
        lista_cards_container,
        barra_paginacion
    )

    # 1. Carga inmediata (0ms) de los productos en pantalla
    recargar_datos_y_renderizar()

    # 2. Sincronización en segundo plano de la tasa del dólar (no bloquea el arranque)
    refrescar_tasa()


if __name__ == "__main__":
    ft.run(main)
