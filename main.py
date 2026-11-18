"""
main.py - Aplicación Móvil (Android APK) y de Escritorio (PC) de Inventario con Python, SQLite y Flet
Implementa Material 3 adaptable (Claro/Oscuro), cálculo dinámico de arbitraje cambiario
(Tasa BCV y Tasa de Reposición), persistencia Android segura y gestión CRUD completa.
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

# Inicialización obligatoria de SQLite (copia desde assets/ en Android e inserta 297 productos semilla)
database.seed_database()

ITEMS_POR_PAGINA = 40


def main(page: ft.Page):
    # =========================================================================
    # CONFIGURACIÓN DE PÁGINA Y TEMA MATERIAL 3 ADAPTABLE
    # =========================================================================
    page.title = "Sistema de Inventario - LiquidCCS"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(color_scheme_seed="#0284C7", use_material3=True)
    page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH
    page.bgcolor = "#F8FAFC"
    page.padding = 12
    page.spacing = 10

    if hasattr(page, "window") and page.window is not None:
        page.window.width = 1100
        page.window.height = 840
        page.window.min_width = 360
        page.window.min_height = 600

    tasas_iniciales = database.obtener_tasas()
    estado = {
        "modo_oscuro": False,
        "filtro_texto": "",
        "solo_stock": False,
        "categoria_filtro": "todos",  # 'todos', 'stock', 'agotados'
        "pagina_actual": 1,
        "total_paginas": 1,
        "tasa_bcv": tasas_iniciales["tasa_bcv"],
        "tasa_reposicion": tasas_iniciales["tasa_reposicion"],
        "tasa_online": False,
        "tasa_mensaje": "Guardado local (SQLite Offline)",
        "productos_filtrados": [],
    }

    # Referencias en memoria para actualización instantánea (+/-) sin reconstruir lista completa
    tarjetas_ui_refs: Dict[int, Dict[str, Any]] = {}

    # IMPORTANTE Flet 1.1.2: FilePicker es un Service y se auto-registra al instanciarlo;
    # NO debe añadirse a page.overlay (causaría "Unknown control: FilePicker").
    file_picker = ft.FilePicker()

    def pal() -> Dict[str, str]:
        """Retorna la paleta activa según tema Claro u Oscuro."""
        if estado["modo_oscuro"]:
            return {
                "bg": "#0F172A",
                "card": "#1E293B",
                "card_sec": "#0F172A",
                "border": "#334155",
                "text": "#F8FAFC",
                "subtext": "#CBD5E1",
                "muted": "#94A3B8",
                "accent": "#38BDF8",
                "chip_inactive_bg": "#1E293B",
                "chip_inactive_txt": "#E2E8F0",
                "bcv_box_bg": "#064E3B",
                "bcv_box_border": "#059669",
                "bcv_box_txt": "#6EE7B7",
                "repo_box_bg": "#0C4A6E",
                "repo_box_border": "#0284C7",
                "repo_box_txt": "#7DD3FC",
                "ubic_bg": "#3B0764",
                "ubic_txt": "#E9D5FF",
                "sku_bg": "#1E3A8A",
                "sku_txt": "#BFDBFE",
            }
        return {
            "bg": "#F8FAFC",
            "card": ft.Colors.WHITE,
            "card_sec": "#F8FAFC",
            "border": "#E2E8F0",
            "text": "#0F172A",
            "subtext": "#334155",
            "muted": "#64748B",
            "accent": "#0284C7",
            "chip_inactive_bg": ft.Colors.WHITE,
            "chip_inactive_txt": "#334155",
            "bcv_box_bg": "#ECFDF5",
            "bcv_box_border": "#6EE7B7",
            "bcv_box_txt": "#047857",
            "repo_box_bg": "#F0F9FF",
            "repo_box_border": "#7DD3FC",
            "repo_box_txt": "#0369A1",
            "ubic_bg": "#F3E8FF",
            "ubic_txt": "#6B21A8",
            "sku_bg": "#DBEAFE",
            "sku_txt": "#1E40AF",
        }

    def obtener_ancho_modal() -> int:
        """Calcula un ancho de modal adaptable tanto a celular (360px+) como a PC."""
        ancho_pag = getattr(page, "width", None) or 480
        return max(290, min(int(ancho_pag) - 36, 480))

    # =========================================================================
    # NOTIFICACIONES
    # =========================================================================
    def notificar(mensaje: str, es_error: bool = False):
        """Muestra una barra de notificación temporal."""
        sb = ft.SnackBar(
            content=ft.Text(mensaje, color=ft.Colors.WHITE, weight=ft.FontWeight.W_500, size=13),
            bgcolor="#DC2626" if es_error else "#059669",
            duration=2800,
        )
        page.show_dialog(sb)

    # =========================================================================
    # PANEL DE TASAS RÁPIDAS Y SINCRONIZACIÓN OPCIONAL
    # =========================================================================
    txt_titulo_app = ft.Text("Inventario Pro", size=18, weight=ft.FontWeight.BOLD, color="#0F172A")
    icono_app = ft.Icon(ft.Icons.INVENTORY_ROUNDED, color="#0284C7", size=24)

    txt_tasa_bcv = ft.Text("", size=15, weight=ft.FontWeight.BOLD, color="#0F172A")
    txt_tasa_repo = ft.Text("", size=15, weight=ft.FontWeight.BOLD, color="#0284C7")
    lbl_fecha_tasa = ft.Text("", size=11, color="#64748B")
    badge_estado_tasas = ft.Container(
        content=ft.Text("SQLITE", size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
        bgcolor="#0284C7",
        padding=ft.Padding.symmetric(horizontal=8, vertical=2),
        border_radius=12,
    )

    def refrescar_tasa_api(e=None):
        """Sincroniza tasas opcionalmente con DolarApi en segundo plano cuando el usuario lo solicita."""
        btn_sync_api.disabled = True
        lbl_fecha_tasa.value = "Consultando DolarApi..."
        page.update()

        def tarea_red():
            res = dolar_service.obtener_tasa_dolar(forzar_red=True)
            if res.get("online"):
                estado["tasa_bcv"] = float(res["bcv"])
                estado["tasa_reposicion"] = float(res["paralelo"])
                estado["tasa_online"] = True
                estado["tasa_mensaje"] = f"API en vivo ({res['fecha']})"
                database.actualizar_tasas(estado["tasa_bcv"], estado["tasa_reposicion"])
            else:
                estado["tasa_online"] = False
                estado["tasa_mensaje"] = f"Sin conexión: usando tasas locales"
            actualizar_panel_tasas()
            actualizar_kpis()
            renderizar_pagina_actual()
            btn_sync_api.disabled = False
            page.update()

            if res.get("online"):
                notificar(
                    f"Tasas sincronizadas: BCV {database.formatear_bs(estado['tasa_bcv'])} | "
                    f"Reposición {database.formatear_bs(estado['tasa_reposicion'])}"
                )
            else:
                notificar("Sin acceso a internet. Se mantienen tus tasas locales.", es_error=True)

        threading.Thread(target=tarea_red, daemon=True).start()

    def abrir_modal_tasas(e=None):
        """Diálogo modal rápido para editar Tasa BCV y Tasa Reposición y recalcular todo al vuelo."""
        p_col = pal()
        in_bcv = ft.TextField(
            label="Tasa Oficial BCV (Bs/$)",
            value=f"{estado['tasa_bcv']:.2f}",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_radius=8,
            content_padding=10,
            autofocus=True,
        )
        in_repo = ft.TextField(
            label="Tasa Reposición / Paralelo (Bs/$)",
            value=f"{estado['tasa_reposicion']:.2f}",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_radius=8,
            content_padding=10,
        )
        lbl_ejemplo = ft.Text("", size=12, color=p_col["accent"], weight=ft.FontWeight.W_600)

        def actualizar_preview_tasas(ev=None):
            try:
                bcv_v = float((in_bcv.value or "").replace(",", "."))
                rep_v = float((in_repo.value or "").replace(",", "."))
                if bcv_v > 0 and rep_v > 0:
                    factor = rep_v / bcv_v
                    ejemplo_usd = 10.0 * factor
                    ejemplo_bs = 10.0 * rep_v
                    lbl_ejemplo.value = (
                        f"Factor arbitraje: ×{factor:.4f}\n"
                        f"Ej. Producto Base $10.00 -> Ajustado BCV: ${ejemplo_usd:,.2f} | "
                        f"Total: {database.formatear_bs(ejemplo_bs)}"
                    )
                else:
                    lbl_ejemplo.value = "Ambas tasas deben ser mayores a 0"
            except Exception:
                lbl_ejemplo.value = "Ingresa valores numéricos válidos"
            if ev is not None:
                page.update()

        actualizar_preview_tasas()
        in_bcv.on_change = actualizar_preview_tasas
        in_repo.on_change = actualizar_preview_tasas

        def cerrar(ev):
            page.pop_dialog()
            page.update()

        def guardar_tasas(ev):
            try:
                nuevo_bcv = float((in_bcv.value or "").strip().replace(",", "."))
                nuevo_repo = float((in_repo.value or "").strip().replace(",", "."))
            except ValueError:
                notificar("Ingresa tasas numéricas válidas (ej. 914.02 y 1200.00)", es_error=True)
                return

            if nuevo_bcv <= 0 or nuevo_repo <= 0:
                notificar("Las tasas deben ser mayores a cero", es_error=True)
                return

            database.actualizar_tasas(nuevo_bcv, nuevo_repo)
            estado["tasa_bcv"] = nuevo_bcv
            estado["tasa_reposicion"] = nuevo_repo
            estado["tasa_online"] = False
            estado["tasa_mensaje"] = "Editado manualmente (SQLite)"

            page.pop_dialog()
            actualizar_panel_tasas()
            actualizar_kpis()
            renderizar_pagina_actual()
            notificar(
                f"Tasas actualizadas: BCV {database.formatear_bs(nuevo_bcv)} | "
                f"Reposición {database.formatear_bs(nuevo_repo)}"
            )

        dlg = ft.AlertDialog(
            title=ft.Row(
                [
                    ft.Row([ft.Icon(ft.Icons.CURRENCY_EXCHANGE_ROUNDED, color="#0284C7"), ft.Text("Editar Tasas Cambiarias", size=16, weight=ft.FontWeight.BOLD)], spacing=8),
                    ft.IconButton(ft.Icons.CLOSE_ROUNDED, icon_color=p_col["muted"], on_click=cerrar),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text("Ajusta las tasas para recalcular al instante todos los precios del catálogo.", size=12, color=p_col["muted"]),
                        in_bcv,
                        in_repo,
                        ft.Container(
                            content=lbl_ejemplo,
                            bgcolor=p_col["repo_box_bg"],
                            border=ft.Border.all(1, p_col["repo_box_border"]),
                            border_radius=8,
                            padding=10,
                        ),
                        ft.Divider(height=10, color=p_col["border"]),
                        ft.FilledButton(
                            content="Guardar y Recalcular Todo",
                            icon=ft.Icons.CHECK_CIRCLE_ROUNDED,
                            bgcolor="#0284C7",
                            color=ft.Colors.WHITE,
                            height=44,
                            on_click=guardar_tasas,
                        ),
                        ft.TextButton(content="Cancelar", on_click=cerrar),
                    ],
                    spacing=10,
                    scroll=ft.ScrollMode.ADAPTIVE,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                ),
                width=obtener_ancho_modal(),
                padding=ft.Padding.only(top=4, bottom=6),
            ),
            actions=[],
        )
        page.show_dialog(dlg)

    btn_editar_tasas = ft.FilledTonalButton(
        content="Editar Tasas",
        icon=ft.Icons.EDIT_ROUNDED,
        on_click=abrir_modal_tasas,
    )
    btn_sync_api = ft.IconButton(
        icon=ft.Icons.SYNC_ROUNDED,
        icon_color="#0284C7",
        tooltip="Sincronizar con DolarApi (internet)",
        on_click=refrescar_tasa_api,
    )

    def actualizar_panel_tasas():
        p_col = pal()
        bcv_s = database.formatear_bs(estado["tasa_bcv"])
        rep_s = database.formatear_bs(estado["tasa_reposicion"])
        factor = estado["tasa_reposicion"] / estado["tasa_bcv"] if estado["tasa_bcv"] > 0 else 1.0

        txt_tasa_bcv.value = f"Tasa BCV: {bcv_s}"
        txt_tasa_bcv.color = p_col["text"]
        txt_tasa_repo.value = f"Tasa Reposición: {rep_s}"
        txt_tasa_repo.color = p_col["accent"]
        lbl_fecha_tasa.value = f"{estado['tasa_mensaje']} • Arbitraje: ×{factor:.4f}"
        lbl_fecha_tasa.color = p_col["muted"]

        if estado["tasa_online"]:
            badge_estado_tasas.bgcolor = "#10B981"
            badge_estado_tasas.content.value = "API LIVE"
        else:
            badge_estado_tasas.bgcolor = "#0284C7"
            badge_estado_tasas.content.value = "OFFLINE"

    actualizar_panel_tasas()

    card_tasa_dolar = ft.Container(
        content=ft.Row(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.CURRENCY_EXCHANGE_ROUNDED, color="#0284C7", size=26),
                        ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Text("PANEL DE TASAS RÁPIDAS", size=11, weight=ft.FontWeight.BOLD, color="#0284C7"),
                                        badge_estado_tasas,
                                    ],
                                    spacing=6,
                                ),
                                ft.Row(controls=[txt_tasa_bcv, txt_tasa_repo], spacing=14, wrap=True),
                                lbl_fecha_tasa,
                            ],
                            spacing=2,
                            expand=True,
                        ),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    expand=True,
                ),
                ft.Row(
                    controls=[btn_editar_tasas, btn_sync_api],
                    spacing=4,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            wrap=True,
        ),
        bgcolor=ft.Colors.WHITE,
        border=ft.Border.all(1, "#E2E8F0"),
        border_radius=12,
        padding=10,
    )

    # =========================================================================
    # MÉTRICAS KPI DEL INVENTARIO
    # =========================================================================
    txt_kpi_total_prods = ft.Text("0", size=15, weight=ft.FontWeight.BOLD, color="#0F172A")
    txt_kpi_total_stock = ft.Text("0", size=15, weight=ft.FontWeight.BOLD, color="#059669")
    txt_kpi_con_stock = ft.Text("0", size=15, weight=ft.FontWeight.BOLD, color="#0284C7")
    txt_kpi_valor_bcv = ft.Text("$0.00", size=15, weight=ft.FontWeight.BOLD, color="#7C3AED")

    kpi_containers = []
    kpi_titulos = []

    def kpi_box(titulo: str, txt_control: ft.Text, icon_name, color_accent: str):
        lbl_t = ft.Text(titulo, size=10, color="#64748B", weight=ft.FontWeight.W_500)
        kpi_titulos.append(lbl_t)
        cont = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(icon_name, color=color_accent, size=21),
                    ft.Column(controls=[lbl_t, txt_control], spacing=0),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.all(1, "#E2E8F0"),
            border_radius=10,
            padding=8,
            col={"xs": 6, "sm": 6, "md": 3},
        )
        kpi_containers.append(cont)
        return cont

    barra_kpis = ft.ResponsiveRow(
        controls=[
            kpi_box("Artículos", txt_kpi_total_prods, ft.Icons.CATEGORY_OUTLINED, "#0284C7"),
            kpi_box("Unidades Stock", txt_kpi_total_stock, ft.Icons.INVENTORY_2_OUTLINED, "#059669"),
            kpi_box("Con Stock (>0)", txt_kpi_con_stock, ft.Icons.CHECK_CIRCLE_OUTLINE, "#0284C7"),
            kpi_box("Valor Ajust. BCV", txt_kpi_valor_bcv, ft.Icons.PAYMENTS_OUTLINED, "#7C3AED"),
        ],
        spacing=8,
        run_spacing=8,
    )

    def actualizar_kpis():
        stats = database.obtener_resumen_estadisticas()
        txt_kpi_total_prods.value = str(stats["total_items"])
        txt_kpi_total_stock.value = f"{stats['total_unidades']} u."
        txt_kpi_con_stock.value = f"{stats['items_con_stock']} / {stats['total_items']}"
        txt_kpi_valor_bcv.value = database.formatear_usd(stats["valor_bcv_ajustado_usd"])

    actualizar_kpis()

    # =========================================================================
    # BUSCADOR FULL-WIDTH Y FILTROS ("Solo con stock (> 0)" + CHIPS)
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
        hint_text="Buscar por nombre, SKU o ubicación (ej. BRIAN, DEP, YUDY, ROUTER)...",
        prefix_icon=ft.Icons.SEARCH,
        suffix=ft.IconButton(ft.Icons.CLEAR, on_click=limpiar_busqueda, tooltip="Limpiar búsqueda"),
        bgcolor=ft.Colors.WHITE,
        border_color="#94A3B8",
        focused_border_color="#0284C7",
        border_radius=10,
        content_padding=10,
        text_size=13,
        expand=True,
        on_change=on_busqueda_change,
    )

    fila_busqueda = ft.Row(controls=[input_busqueda], expand=False)

    def actualizar_estilo_chips():
        p_col = pal()
        cat = estado["categoria_filtro"]
        btn_chip_todos.bgcolor = "#0F172A" if cat == "todos" else p_col["chip_inactive_bg"]
        btn_chip_todos.content.color = ft.Colors.WHITE if cat == "todos" else p_col["chip_inactive_txt"]
        btn_chip_todos.border = ft.Border.all(1, p_col["border"])

        btn_chip_stock.bgcolor = "#059669" if cat == "stock" else p_col["chip_inactive_bg"]
        btn_chip_stock.content.color = ft.Colors.WHITE if cat == "stock" else p_col["chip_inactive_txt"]
        btn_chip_stock.border = ft.Border.all(1, p_col["border"])

        btn_chip_agotados.bgcolor = "#DC2626" if cat == "agotados" else p_col["chip_inactive_bg"]
        btn_chip_agotados.content.color = ft.Colors.WHITE if cat == "agotados" else p_col["chip_inactive_txt"]
        btn_chip_agotados.border = ft.Border.all(1, p_col["border"])

    def cambiar_filtro_categoria(categoria: str):
        estado["categoria_filtro"] = categoria
        estado["solo_stock"] = (categoria == "stock")
        switch_solo_stock.value = estado["solo_stock"]
        estado["pagina_actual"] = 1
        actualizar_estilo_chips()
        recargar_datos_y_renderizar()

    def on_switch_stock_change(e):
        activar = bool(switch_solo_stock.value)
        estado["solo_stock"] = activar
        estado["categoria_filtro"] = "stock" if activar else "todos"
        estado["pagina_actual"] = 1
        actualizar_estilo_chips()
        recargar_datos_y_renderizar()

    switch_solo_stock = ft.Switch(
        label="Solo con stock (> 0)",
        value=False,
        active_color="#059669",
        on_change=on_switch_stock_change,
    )

    btn_chip_todos = ft.Container(
        content=ft.Text("Todos", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
        bgcolor="#0F172A",
        border=ft.Border.all(1, "#CBD5E1"),
        border_radius=20,
        padding=ft.Padding.symmetric(horizontal=12, vertical=5),
        on_click=lambda e: cambiar_filtro_categoria("todos"),
        ink=True,
    )

    btn_chip_stock = ft.Container(
        content=ft.Text("Con Stock", size=12, weight=ft.FontWeight.BOLD, color="#334155"),
        bgcolor=ft.Colors.WHITE,
        border=ft.Border.all(1, "#CBD5E1"),
        border_radius=20,
        padding=ft.Padding.symmetric(horizontal=12, vertical=5),
        on_click=lambda e: cambiar_filtro_categoria("stock"),
        ink=True,
    )

    btn_chip_agotados = ft.Container(
        content=ft.Text("Agotados", size=12, weight=ft.FontWeight.BOLD, color="#334155"),
        bgcolor=ft.Colors.WHITE,
        border=ft.Border.all(1, "#CBD5E1"),
        border_radius=20,
        padding=ft.Padding.symmetric(horizontal=12, vertical=5),
        on_click=lambda e: cambiar_filtro_categoria("agotados"),
        ink=True,
    )

    fila_filtros = ft.Row(
        controls=[btn_chip_todos, btn_chip_stock, btn_chip_agotados, switch_solo_stock],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        wrap=True,
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
        on_click=ir_pagina_anterior,
    )
    btn_pag_sig = ft.IconButton(
        icon=ft.Icons.CHEVRON_RIGHT_ROUNDED,
        icon_color="#0F172A",
        tooltip="Página siguiente",
        on_click=ir_pagina_siguiente,
    )

    barra_paginacion = ft.Container(
        content=ft.Row(
            controls=[btn_pag_ant, lbl_pagina_info, btn_pag_sig],
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        ),
        bgcolor=ft.Colors.WHITE,
        border=ft.Border.all(1, "#E2E8F0"),
        border_radius=10,
        padding=ft.Padding.symmetric(horizontal=8, vertical=2),
        margin=ft.Margin.only(right=68),  # Evita solapamiento con el FloatingActionButton '+'
    )

    # =========================================================================
    # LISTA DE PRODUCTOS Y TARJETAS CON ARBITRAJE CAMBIARIO
    # =========================================================================
    lista_cards_container = ft.ListView(
        controls=[],
        spacing=8,
        padding=ft.Padding.only(bottom=72),  # Espacio inferior para scroll libre sobre el FAB
        expand=True,
    )

    def ajustar_stock_rapido(producto_id: int, delta: int):
        """Actualiza el stock en SQLite bloqueando valores negativos y refresca in-place."""
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

        if (estado["categoria_filtro"] == "stock" and nueva_cantidad == 0) or (
            estado["categoria_filtro"] == "agotados" and nueva_cantidad > 0
        ):
            recargar_datos_y_renderizar()
            return

        es_disp = nueva_cantidad > 0
        badge_st: ft.Container = ref["badge_stock"]
        badge_st.bgcolor = "#DCFCE7" if es_disp else "#FEE2E2"
        badge_st.content.value = f"{nueva_cantidad} en stock" if es_disp else "Agotado (0)"
        badge_st.content.color = "#15803D" if es_disp else "#B91C1C"

        txt_num: ft.Text = ref["txt_cant"]
        txt_num.value = str(nueva_cantidad)
        page.update()

    def confirmar_eliminar_producto(producto_id: int):
        """Diálogo de confirmación antes de eliminar un artículo."""
        p = database.obtener_producto_por_id(producto_id)
        if not p:
            return
        p_col = pal()

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
            title=ft.Row(
                [ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color="#DC2626"), ft.Text("Confirmar Eliminación", size=15, weight=ft.FontWeight.BOLD)],
                spacing=8,
            ),
            content=ft.Container(
                content=ft.Text(
                    f"¿Deseas eliminar permanentemente este artículo del inventario?\n\n{p['sku']} - {p['nombre']}",
                    size=13,
                    color=p_col["subtext"],
                ),
                width=obtener_ancho_modal(),
            ),
            actions=[
                ft.TextButton(content="Cancelar", on_click=cancelar),
                ft.FilledButton(
                    content="Eliminar",
                    icon=ft.Icons.DELETE_FOREVER_ROUNDED,
                    bgcolor="#DC2626",
                    color=ft.Colors.WHITE,
                    on_click=ejecutar_eliminacion,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.show_dialog(dlg)

    def crear_tarjeta_producto(p: Dict[str, Any]) -> ft.Container:
        """Crea una tarjeta adaptable con arbitraje cambiario y control rápido de stock."""
        p_col = pal()
        t_bcv = estado["tasa_bcv"]
        t_repo = estado["tasa_reposicion"]
        cant = p["cantidad"]
        es_disponible = cant > 0

        precios = database.calcular_precios_producto(p, t_bcv, t_repo)
        costo_str = database.formatear_usd(p["costo_usd"]) if p.get("costo_usd") else "-"

        badge_sku = ft.Container(
            content=ft.Text(p["sku"], size=11, weight=ft.FontWeight.BOLD, color=p_col["sku_txt"]),
            bgcolor=p_col["sku_bg"],
            border_radius=6,
            padding=ft.Padding.symmetric(horizontal=8, vertical=3),
        )

        badge_stock = ft.Container(
            content=ft.Text(
                f"{cant} en stock" if es_disponible else "Agotado (0)",
                size=11,
                weight=ft.FontWeight.BOLD,
                color="#15803D" if es_disponible else "#B91C1C",
            ),
            bgcolor="#DCFCE7" if es_disponible else "#FEE2E2",
            border_radius=6,
            padding=ft.Padding.symmetric(horizontal=8, vertical=3),
        )

        badges_cabecera = [badge_sku, badge_stock]
        if p.get("ubicacion_nota"):
            badges_cabecera.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.LOCATION_ON_OUTLINED, size=12, color=p_col["ubic_txt"]),
                            ft.Text(str(p["ubicacion_nota"]), size=11, weight=ft.FontWeight.W_600, color=p_col["ubic_txt"]),
                        ],
                        spacing=3,
                    ),
                    bgcolor=p_col["ubic_bg"],
                    border_radius=6,
                    padding=ft.Padding.symmetric(horizontal=7, vertical=3),
                )
            )

        txt_cant_rapida = ft.Text(str(cant), size=14, weight=ft.FontWeight.BOLD, color=p_col["text"])

        tarjetas_ui_refs[p["id"]] = {
            "datos": p,
            "badge_stock": badge_stock,
            "txt_cant": txt_cant_rapida,
        }

        origen_lbl = f"Base ({precios['origen_base']})" if precios["tiene_precio"] else "Precio Base"
        color_bcv = p_col["bcv_box_txt"] if precios["tiene_precio"] else p_col["muted"]
        color_bs = p_col["repo_box_txt"] if precios["tiene_precio"] else p_col["muted"]

        # Bloque 1: Precio Base
        col_base = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(origen_lbl.upper(), size=10, color=p_col["muted"], weight=ft.FontWeight.W_600),
                    ft.Text(precios["precio_base_str"], size=14, weight=ft.FontWeight.BOLD, color=p_col["text"]),
                    ft.Text(f"Costo: {costo_str}", size=10, color=p_col["muted"]),
                ],
                spacing=1,
            ),
            padding=6,
            col={"xs": 6, "sm": 3},
        )

        # Bloque 2: Precio Ajustado BCV (Destacado)
        col_ajustado_bcv = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("AJUSTADO BCV ($)", size=10, color=color_bcv, weight=ft.FontWeight.BOLD),
                    ft.Text(precios["precio_venta_bcv_usd_str"], size=15, weight=ft.FontWeight.BOLD, color=color_bcv),
                    ft.Text("Cobro ref. BCV", size=10, color=color_bcv),
                ],
                spacing=1,
            ),
            bgcolor=p_col["bcv_box_bg"] if precios["tiene_precio"] else p_col["card_sec"],
            border=ft.Border.all(1, p_col["bcv_box_border"] if precios["tiene_precio"] else p_col["border"]),
            border_radius=8,
            padding=6,
            col={"xs": 6, "sm": 3},
        )

        # Bloque 3: Total en Bs (Reposición)
        col_bs_repo = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("TOTAL REPOSICIÓN (BS)", size=10, color=color_bs, weight=ft.FontWeight.BOLD),
                    ft.Text(precios["monto_bs_reposicion_str"], size=13, weight=ft.FontWeight.BOLD, color=color_bs),
                    ft.Text(f"BCV Directo: {precios['monto_bs_bcv_directo_str']}", size=10, color=p_col["muted"]),
                ],
                spacing=1,
            ),
            bgcolor=p_col["repo_box_bg"] if precios["tiene_precio"] else p_col["card_sec"],
            border=ft.Border.all(1, p_col["repo_box_border"] if precios["tiene_precio"] else p_col["border"]),
            border_radius=8,
            padding=6,
            col={"xs": 6, "sm": 3},
        )

        # Bloque 4: Ajuste rápido de stock (- / +)
        col_stock_ctrl = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("AJUSTAR STOCK", size=10, color=p_col["muted"], weight=ft.FontWeight.W_600),
                    ft.Row(
                        controls=[
                            ft.IconButton(
                                icon=ft.Icons.REMOVE_CIRCLE_OUTLINE,
                                icon_color=p_col["muted"],
                                icon_size=22,
                                tooltip="Restar 1 unidad",
                                on_click=lambda e, pid=p["id"]: ajustar_stock_rapido(pid, -1),
                            ),
                            txt_cant_rapida,
                            ft.IconButton(
                                icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                                icon_color=p_col["accent"],
                                icon_size=22,
                                tooltip="Sumar 1 unidad",
                                on_click=lambda e, pid=p["id"]: ajustar_stock_rapido(pid, 1),
                            ),
                        ],
                        spacing=0,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                spacing=0,
            ),
            padding=ft.Padding.only(left=4, top=2),
            col={"xs": 6, "sm": 3},
        )

        return ft.Container(
            content=ft.Column(
                controls=[
                    # Fila 1: Badges + Editar / Eliminar
                    ft.Row(
                        controls=[
                            ft.Row(controls=badges_cabecera, spacing=6, wrap=True),
                            ft.Row(
                                controls=[
                                    ft.TextButton(
                                        content="Editar",
                                        icon=ft.Icons.EDIT_OUTLINED,
                                        icon_color=p_col["accent"],
                                        tooltip="Editar artículo",
                                        on_click=lambda e, pid=p["id"]: abrir_modal_detalle(pid),
                                    ),
                                    ft.TextButton(
                                        content="Eliminar",
                                        icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
                                        icon_color="#DC2626",
                                        tooltip="Eliminar artículo",
                                        on_click=lambda e, pid=p["id"]: confirmar_eliminar_producto(pid),
                                    ),
                                ],
                                spacing=0,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        wrap=True,
                    ),
                    # Fila 2: Nombre del producto (tocable para editar)
                    ft.Container(
                        content=ft.Text(p["nombre"], size=14, weight=ft.FontWeight.W_700, color=p_col["text"]),
                        on_click=lambda e, pid=p["id"]: abrir_modal_detalle(pid),
                        ink=True,
                        border_radius=6,
                        padding=ft.Padding.symmetric(vertical=2),
                    ),
                    ft.Divider(height=1, color=p_col["border"]),
                    # Fila 3: Desglose financiero y control de stock
                    ft.ResponsiveRow(
                        controls=[col_base, col_ajustado_bcv, col_bs_repo, col_stock_ctrl],
                        spacing=8,
                        run_spacing=8,
                    ),
                ],
                spacing=6,
            ),
            bgcolor=p_col["card"],
            border=ft.Border.all(1, p_col["border"]),
            border_radius=12,
            padding=12,
        )

    def renderizar_pagina_actual():
        """Dibuja únicamente el lote activo (máximo 40 tarjetas) para máxima fluidez."""
        p_col = pal()
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
                            ft.Icon(ft.Icons.SEARCH_OFF_ROUNDED, size=44, color=p_col["muted"]),
                            ft.Text("No se encontraron artículos con ese criterio", size=14, color=p_col["muted"]),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    padding=36,
                    alignment=ft.Alignment.CENTER,
                )
            )
        else:
            for prod in lote:
                lista_cards_container.controls.append(crear_tarjeta_producto(prod))

        lbl_contador_resultados.value = f"{total} artículos encontrados"
        lbl_contador_resultados.color = p_col["subtext"]
        lbl_pagina_info.value = f"Página {pag} de {total_pags} ({inicio + 1 if total else 0}-{min(fin, total)} de {total})"
        lbl_pagina_info.color = p_col["text"]
        btn_pag_ant.disabled = (pag <= 1)
        btn_pag_sig.disabled = (pag >= total_pags)
        barra_paginacion.visible = (total > ITEMS_POR_PAGINA)
        page.update()

    def recargar_datos_y_renderizar():
        """Consulta SQLite con índices optimizados y actualiza la vista."""
        solo_stock = (estado["categoria_filtro"] == "stock") or estado["solo_stock"]
        solo_agotados = (estado["categoria_filtro"] == "agotados")

        estado["productos_filtrados"] = database.obtener_productos(
            filtro=estado["filtro_texto"],
            solo_stock=solo_stock,
            solo_agotados=solo_agotados,
        )
        renderizar_pagina_actual()

    # =========================================================================
    # MODAL 1: CARGA DE UN NUEVO ARTÍCULO
    # =========================================================================
    def abrir_modal_nuevo_producto(e=None):
        p_col = pal()
        sku_sugerido = database.obtener_siguiente_sku()

        in_sku = ft.TextField(label="SKU / Código", value=sku_sugerido, border_radius=8, content_padding=10, expand=True)
        in_cantidad = ft.TextField(label="Stock Inicial", value="0", keyboard_type=ft.KeyboardType.NUMBER, border_radius=8, content_padding=10, expand=True)
        in_nombre = ft.TextField(label="Nombre del Artículo *", border_radius=8, content_padding=10, autofocus=True, expand=True)
        in_detal = ft.TextField(label="Precio Detal ($)", hint_text="10.00", keyboard_type=ft.KeyboardType.NUMBER, border_radius=8, content_padding=10, expand=True)
        in_desc = ft.TextField(label="Precio Lista/Desc. ($)", hint_text="8.00", keyboard_type=ft.KeyboardType.NUMBER, border_radius=8, content_padding=10, expand=True)
        in_costo = ft.TextField(label="Costo Base ($)", hint_text="4.50", keyboard_type=ft.KeyboardType.NUMBER, border_radius=8, content_padding=10, expand=True)
        in_ubicacion = ft.TextField(label="Ubicación / Nota", hint_text="Depósito, BRIAN...", border_radius=8, content_padding=10, expand=True)

        txt_preview_calc = ft.Text("Vista previa de arbitraje: Sin precio", size=12, color=p_col["accent"], weight=ft.FontWeight.W_600)

        def parse_float(val):
            if not val or not val.strip():
                return None
            try:
                return float(val.strip().replace(",", "."))
            except ValueError:
                return None

        def actualizar_preview_nuevo(ev=None):
            sim_prod = {
                "precio_detal_usd": parse_float(in_detal.value),
                "precio_descuento_usd": parse_float(in_desc.value),
            }
            c = database.calcular_precios_producto(sim_prod, estado["tasa_bcv"], estado["tasa_reposicion"])
            if c["tiene_precio"]:
                txt_preview_calc.value = (
                    f"Base ({c['origen_base']}): {c['precio_base_str']}\n"
                    f"Ajustado BCV: {c['precio_venta_bcv_usd_str']}  |  Total: {c['monto_bs_reposicion_str']}"
                )
            else:
                txt_preview_calc.value = "Vista previa de arbitraje: Sin precio"
            if ev is not None:
                page.update()

        in_detal.on_change = actualizar_preview_nuevo
        in_desc.on_change = actualizar_preview_nuevo

        def cerrar_dialogo(ev):
            page.pop_dialog()
            page.update()

        def guardar_nuevo_articulo(ev):
            nombre = (in_nombre.value or "").strip()
            sku = (in_sku.value or "").strip()

            if not nombre:
                notificar("El nombre del artículo es obligatorio", es_error=True)
                return
            if not sku:
                notificar("El SKU es obligatorio", es_error=True)
                return

            try:
                cantidad = max(0, int((in_cantidad.value or "").strip() or "0"))
            except ValueError:
                notificar("La cantidad debe ser un número entero", es_error=True)
                return

            exito = database.agregar_producto(
                sku=sku,
                nombre=nombre,
                cantidad=cantidad,
                precio_detal=parse_float(in_detal.value),
                precio_descuento=parse_float(in_desc.value),
                costo=parse_float(in_costo.value),
                ubicacion=(in_ubicacion.value or "").strip() or None,
            )

            if exito:
                page.pop_dialog()
                actualizar_kpis()
                recargar_datos_y_renderizar()
                notificar(f"Producto '{nombre}' registrado con éxito.")
            else:
                notificar(f"Error: Ya existe un producto activo con el SKU '{sku}'", es_error=True)

        dlg = ft.AlertDialog(
            title=ft.Row(
                [
                    ft.Row([ft.Icon(ft.Icons.ADD_BOX_ROUNDED, color="#059669"), ft.Text("Nuevo Artículo", size=16, weight=ft.FontWeight.BOLD)], spacing=8),
                    ft.IconButton(icon=ft.Icons.CLOSE_ROUNDED, icon_color=p_col["muted"], tooltip="Cerrar", on_click=cerrar_dialogo),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row([in_sku, in_cantidad], spacing=8),
                        ft.Row([in_nombre], spacing=8),
                        ft.Row([in_detal, in_desc], spacing=8),
                        ft.Container(
                            content=txt_preview_calc,
                            bgcolor=p_col["repo_box_bg"],
                            border=ft.Border.all(1, p_col["repo_box_border"]),
                            border_radius=8,
                            padding=8,
                        ),
                        ft.Row([in_costo, in_ubicacion], spacing=8),
                        ft.Divider(height=12, color=p_col["border"]),
                        ft.FilledButton(
                            content="Guardar Artículo",
                            icon=ft.Icons.CHECK_CIRCLE_ROUNDED,
                            bgcolor="#059669",
                            color=ft.Colors.WHITE,
                            height=44,
                            on_click=guardar_nuevo_articulo,
                        ),
                        ft.TextButton(content="Cancelar", on_click=cerrar_dialogo),
                    ],
                    spacing=10,
                    scroll=ft.ScrollMode.ADAPTIVE,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                ),
                width=obtener_ancho_modal(),
                padding=ft.Padding.only(top=4, bottom=6),
            ),
            actions=[],
        )
        page.show_dialog(dlg)

    # =========================================================================
    # MODAL 2: EDICIÓN Y DETALLES COMPLETOS (SIN DESAJUSTE DE TECLADO)
    # =========================================================================
    def abrir_modal_detalle(producto_id: int):
        p = database.obtener_producto_por_id(producto_id)
        if not p:
            return
        p_col = pal()

        ed_sku = ft.TextField(label="SKU / Código", value=p["sku"], border_radius=8, content_padding=10, expand=True)
        ed_cantidad = ft.TextField(label="Stock Actual", value=str(p["cantidad"]), keyboard_type=ft.KeyboardType.NUMBER, border_radius=8, content_padding=10, expand=True)
        ed_nombre = ft.TextField(label="Nombre del Producto", value=p["nombre"], border_radius=8, content_padding=10, expand=True)
        ed_detal = ft.TextField(label="Precio Detal ($)", value=str(p["precio_detal_usd"]) if p["precio_detal_usd"] is not None else "", keyboard_type=ft.KeyboardType.NUMBER, border_radius=8, content_padding=10, expand=True)
        ed_desc = ft.TextField(label="Precio Lista/Desc. ($)", value=str(p["precio_descuento_usd"]) if p["precio_descuento_usd"] is not None else "", keyboard_type=ft.KeyboardType.NUMBER, border_radius=8, content_padding=10, expand=True)
        ed_costo = ft.TextField(label="Costo Base ($)", value=str(p["costo_usd"]) if p["costo_usd"] is not None else "", keyboard_type=ft.KeyboardType.NUMBER, border_radius=8, content_padding=10, expand=True)
        ed_ubicacion = ft.TextField(label="Ubicación / Nota", value=p["ubicacion_nota"] or "", border_radius=8, content_padding=10, expand=True)

        lbl_info_arbitraje = ft.Text("", size=12, color=p_col["accent"], weight=ft.FontWeight.W_600)

        def parse_float(val):
            if not val or not val.strip():
                return None
            try:
                return float(val.strip().replace(",", "."))
            except ValueError:
                return None

        def actualizar_preview_edicion(ev=None):
            sim_prod = {
                "precio_detal_usd": parse_float(ed_detal.value),
                "precio_descuento_usd": parse_float(ed_desc.value),
            }
            c = database.calcular_precios_producto(sim_prod, estado["tasa_bcv"], estado["tasa_reposicion"])
            if c["tiene_precio"]:
                lbl_info_arbitraje.value = (
                    f"Base ({c['origen_base']}): {c['precio_base_str']}\n"
                    f"Ajustado BCV: {c['precio_venta_bcv_usd_str']}  |  "
                    f"Reposición: {c['monto_bs_reposicion_str']}"
                )
            else:
                lbl_info_arbitraje.value = "Sin precio configurado"
            if ev is not None:
                page.update()

        actualizar_preview_edicion()
        ed_detal.on_change = actualizar_preview_edicion
        ed_desc.on_change = actualizar_preview_edicion

        def cerrar_dialogo(ev):
            page.pop_dialog()
            page.update()

        def guardar_cambios(ev):
            if not (ed_nombre.value or "").strip():
                notificar("El nombre del producto no puede estar vacío", es_error=True)
                return

            try:
                nueva_cant = max(0, int((ed_cantidad.value or "").strip() or "0"))
            except ValueError:
                notificar("La cantidad debe ser un número entero", es_error=True)
                return

            exito = database.actualizar_producto(
                producto_id=producto_id,
                sku=(ed_sku.value or "").strip(),
                nombre=(ed_nombre.value or "").strip(),
                cantidad=nueva_cant,
                precio_detal=parse_float(ed_detal.value),
                precio_descuento=parse_float(ed_desc.value),
                costo=parse_float(ed_costo.value),
                ubicacion=(ed_ubicacion.value or "").strip() or None,
            )

            if exito:
                page.pop_dialog()
                actualizar_kpis()
                recargar_datos_y_renderizar()
                notificar(f"Artículo {(ed_sku.value or '').strip()} actualizado.")
            else:
                notificar("Error al guardar: verifique que el SKU no esté duplicado.", es_error=True)

        def eliminar_desde_modal(ev):
            page.pop_dialog()
            confirmar_eliminar_producto(producto_id)

        dlg = ft.AlertDialog(
            title=ft.Row(
                [
                    ft.Row([ft.Icon(ft.Icons.EDIT_NOTE_ROUNDED, color="#0284C7"), ft.Text(f"Editar: {p['sku']}", size=16, weight=ft.FontWeight.BOLD)], spacing=8),
                    ft.IconButton(icon=ft.Icons.CLOSE_ROUNDED, icon_color=p_col["muted"], tooltip="Cerrar", on_click=cerrar_dialogo),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row([ed_sku, ed_cantidad], spacing=8),
                        ft.Row([ed_nombre], spacing=8),
                        ft.Row([ed_detal, ed_desc], spacing=8),
                        ft.Container(
                            content=lbl_info_arbitraje,
                            bgcolor=p_col["repo_box_bg"],
                            border=ft.Border.all(1, p_col["repo_box_border"]),
                            border_radius=8,
                            padding=8,
                        ),
                        ft.Row([ed_costo, ed_ubicacion], spacing=8),
                        ft.Divider(height=12, color=p_col["border"]),
                        ft.FilledButton(
                            content="Guardar Cambios",
                            icon=ft.Icons.SAVE_ROUNDED,
                            bgcolor="#0284C7",
                            color=ft.Colors.WHITE,
                            height=44,
                            on_click=guardar_cambios,
                        ),
                        ft.Row(
                            controls=[
                                ft.TextButton(
                                    content="Eliminar Artículo",
                                    icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
                                    icon_color="#DC2626",
                                    on_click=eliminar_desde_modal,
                                ),
                                ft.TextButton(content="Cancelar", on_click=cerrar_dialogo),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                    ],
                    spacing=10,
                    scroll=ft.ScrollMode.ADAPTIVE,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                ),
                width=obtener_ancho_modal(),
                padding=ft.Padding.only(top=4, bottom=6),
            ),
            actions=[],
        )
        page.show_dialog(dlg)

    # =========================================================================
    # MODAL: VER / DESCARGAR PLANTILLA DE IMPORTACIÓN
    # =========================================================================
    def abrir_modal_plantilla(campo_texto_destino=None):
        p_col = pal()
        texto_plantilla = database.obtener_texto_plantilla_csv()

        def descargar_plantilla(ev):
            try:
                ruta_descarga = database.generar_archivo_plantilla_csv()
                notificar(f"Plantilla guardada en: {ruta_descarga}")
                try:
                    if sys.platform.startswith("win"):
                        os.startfile(os.path.dirname(ruta_descarga))
                    else:
                        webbrowser.open(f"file://{os.path.dirname(ruta_descarga)}")
                except Exception:
                    pass
            except Exception as ex:
                notificar(f"Error al descargar plantilla: {ex}", es_error=True)

        def copiar_al_editor(ev):
            if campo_texto_destino:
                campo_texto_destino.value = texto_plantilla
                page.update()
                page.pop_dialog()
                notificar("Plantilla cargada en el editor de importación.")

        txt_codigo = ft.TextField(
            value=texto_plantilla,
            multiline=True,
            read_only=True,
            min_lines=7,
            max_lines=10,
            text_size=11,
            border_radius=8,
        )

        dlg = ft.AlertDialog(
            title=ft.Row(
                [
                    ft.Row([ft.Icon(ft.Icons.DESCRIPTION_ROUNDED, color="#0284C7"), ft.Text("Plantilla de Importación", size=15, weight=ft.FontWeight.BOLD)], spacing=8),
                    ft.IconButton(ft.Icons.CLOSE_ROUNDED, icon_color=p_col["muted"], tooltip="Cerrar", on_click=lambda x: page.pop_dialog()),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            "Columnas admitidas (comas o punto y coma):\n"
                            "sku, nombre, cantidad, precio_detal_usd, precio_descuento_usd, costo_usd, ubicacion_nota",
                            size=12,
                            color=p_col["subtext"],
                        ),
                        txt_codigo,
                        ft.Row(
                            controls=[
                                ft.FilledTonalButton(content="Descargar CSV", icon=ft.Icons.DOWNLOAD_ROUNDED, on_click=descargar_plantilla),
                                ft.FilledButton(
                                    content="Cargar en Editor",
                                    icon=ft.Icons.INPUT_ROUNDED,
                                    bgcolor="#0284C7",
                                    color=ft.Colors.WHITE,
                                    on_click=copiar_al_editor,
                                    visible=(campo_texto_destino is not None),
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            wrap=True,
                        ),
                    ],
                    spacing=10,
                    scroll=ft.ScrollMode.ADAPTIVE,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                ),
                width=obtener_ancho_modal(),
                padding=ft.Padding.only(top=4, bottom=6),
            ),
            actions=[],
        )
        page.show_dialog(dlg)

    # =========================================================================
    # MODAL: IMPORTACIÓN DE ARTÍCULOS (ASYNC FILEPICKER FLET 1.1.2 + PEGAR)
    # =========================================================================
    def abrir_modal_importar(e=None):
        p_col = pal()
        txt_import_input = ft.TextField(
            label="Pegar filas CSV / Tabla aquí",
            hint_text="INV-301,DISCO SSD 1TB,3,65.00,60.00,45.00,BRIAN",
            multiline=True,
            min_lines=5,
            max_lines=8,
            text_size=12,
            border_radius=8,
        )

        def ejecutar_importacion_texto(ev):
            raw = (txt_import_input.value or "").strip()
            if not raw:
                notificar("Pega el texto CSV o selecciona un archivo primero", es_error=True)
                return

            res = database.importar_productos_desde_csv(raw)
            if res.get("exito"):
                page.pop_dialog()
                actualizar_kpis()
                recargar_datos_y_renderizar()
                notificar(f"Importación completada: {res['nuevos']} nuevos, {res['actualizados']} actualizados.")
            else:
                notificar(f"Error al importar: {res.get('mensaje', 'Verifique el formato')}", es_error=True)

        async def seleccionar_archivo_click(ev):
            try:
                archivos = await file_picker.pick_files(
                    dialog_title="Seleccionar archivo de inventario (CSV / SVG / TXT)",
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=["csv", "svg", "txt", "tsv"],
                    with_data=True,
                )
                if not archivos:
                    return
                archivo_sel = archivos[0]
                contenido_o_ruta = None
                if getattr(archivo_sel, "path", None) and os.path.isfile(archivo_sel.path):
                    contenido_o_ruta = archivo_sel.path
                elif getattr(archivo_sel, "bytes", None):
                    for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
                        try:
                            contenido_o_ruta = archivo_sel.bytes.decode(enc)
                            break
                        except Exception:
                            continue

                if not contenido_o_ruta:
                    notificar("No se pudo leer el contenido del archivo seleccionado", es_error=True)
                    return

                res = database.importar_productos_desde_csv(contenido_o_ruta)
                if res.get("exito"):
                    page.pop_dialog()
                    actualizar_kpis()
                    recargar_datos_y_renderizar()
                    notificar(f"Importados desde {archivo_sel.name}: {res['nuevos']} nuevos, {res['actualizados']} actualizados.")
                else:
                    notificar(f"Error: {res.get('mensaje', 'Error al procesar archivo')}", es_error=True)
            except Exception as ex:
                notificar(f"Error al seleccionar archivo: {ex}", es_error=True)

        def descargar_plantilla_directa(ev):
            try:
                ruta = database.generar_archivo_plantilla_csv()
                notificar(f"Plantilla guardada: {ruta}")
                try:
                    if sys.platform.startswith("win"):
                        os.startfile(os.path.dirname(ruta))
                except Exception:
                    pass
            except Exception as ex:
                notificar(f"Error: {ex}", es_error=True)

        dlg = ft.AlertDialog(
            title=ft.Row(
                [
                    ft.Row([ft.Icon(ft.Icons.FILE_UPLOAD_ROUNDED, color="#0284C7"), ft.Text("Importar Artículos", size=16, weight=ft.FontWeight.BOLD)], spacing=8),
                    ft.IconButton(icon=ft.Icons.CLOSE_ROUNDED, icon_color=p_col["muted"], tooltip="Cerrar", on_click=lambda x: page.pop_dialog()),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.OutlinedButton(content="Ver Plantilla", icon=ft.Icons.VISIBILITY_OUTLINED, on_click=lambda x: abrir_modal_plantilla(txt_import_input)),
                                ft.OutlinedButton(content="Descargar CSV", icon=ft.Icons.DOWNLOAD_ROUNDED, on_click=descargar_plantilla_directa),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            wrap=True,
                        ),
                        ft.Divider(height=10, color=p_col["border"]),
                        ft.FilledTonalButton(
                            content="Seleccionar Archivo (.csv, .svg, .txt)",
                            icon=ft.Icons.FOLDER_OPEN_ROUNDED,
                            height=42,
                            on_click=seleccionar_archivo_click,
                        ),
                        ft.Text("O pegar contenido directamente:", size=11, color=p_col["muted"], weight=ft.FontWeight.W_500),
                        txt_import_input,
                        ft.Divider(height=10, color=p_col["border"]),
                        ft.FilledButton(
                            content="Procesar Importación",
                            icon=ft.Icons.CHECK_CIRCLE_ROUNDED,
                            bgcolor="#059669",
                            color=ft.Colors.WHITE,
                            height=44,
                            on_click=ejecutar_importacion_texto,
                        ),
                        ft.TextButton(content="Cancelar", on_click=lambda x: page.pop_dialog()),
                    ],
                    spacing=10,
                    scroll=ft.ScrollMode.ADAPTIVE,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                ),
                width=obtener_ancho_modal(),
                padding=ft.Padding.only(top=4, bottom=6),
            ),
            actions=[],
        )
        page.show_dialog(dlg)

    # =========================================================================
    # MODAL 3: EXPORTACIÓN PARA IMPRESIÓN (PDF, HTML Y RESUMEN MÓVIL)
    # =========================================================================
    def abrir_modal_exportacion(e=None):
        p_col = pal()
        prods_a_exportar = estado["productos_filtrados"] if estado["productos_filtrados"] else database.obtener_productos()
        t_bcv = estado["tasa_bcv"]
        t_repo = estado["tasa_reposicion"]

        def generar_y_abrir_pdf(ev):
            pdf_path = export_service.exportar_inventario_pdf(
                productos=prods_a_exportar,
                tasa_bcv=t_bcv,
                tasa_reposicion=t_repo,
                filtro_aplicado=estado["filtro_texto"],
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
                tasa_bcv=t_bcv,
                tasa_reposicion=t_repo,
            )
            page.pop_dialog()
            notificar(f"Reporte imprimible guardado: {os.path.basename(html_path)}")
            try:
                webbrowser.open(f"file://{html_path}")
            except Exception:
                pass

        def ver_listado_texto_imprimible(ev):
            page.pop_dialog()
            texto_reporte = export_service.generar_resumen_texto(prods_a_exportar, t_bcv, t_repo)
            campo_texto = ft.TextField(
                value=texto_reporte,
                multiline=True,
                read_only=True,
                min_lines=10,
                max_lines=14,
                text_size=11,
                border_radius=8,
            )
            dlg_txt = ft.AlertDialog(
                title=ft.Text("Listado de Inventario para Copiar / Imprimir", size=15, weight=ft.FontWeight.BOLD),
                content=ft.Container(content=campo_texto, width=obtener_ancho_modal()),
                actions=[ft.TextButton(content="Cerrar", on_click=lambda x: page.pop_dialog())],
            )
            page.show_dialog(dlg_txt)

        dlg = ft.AlertDialog(
            title=ft.Row(
                [ft.Icon(ft.Icons.PRINT_ROUNDED, color="#0284C7"), ft.Text("Exportar / Imprimir Inventario", size=15, weight=ft.FontWeight.BOLD)],
                spacing=8,
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            f"Se exportarán {len(prods_a_exportar)} artículos\n"
                            f"BCV: {database.formatear_bs(t_bcv)} | Reposición: {database.formatear_bs(t_repo)}",
                            size=12,
                            color=p_col["subtext"],
                        ),
                        ft.Container(
                            content=ft.Row(
                                [
                                    ft.Icon(ft.Icons.PICTURE_AS_PDF_ROUNDED, color="#DC2626", size=26),
                                    ft.Column(
                                        [
                                            ft.Text("Generar Reporte PDF Profesional", weight=ft.FontWeight.BOLD, size=13),
                                            ft.Text("Formato carta horizontal con precios Base, Ajustado BCV y Bs.", size=11, color=p_col["muted"]),
                                        ],
                                        spacing=1,
                                        expand=True,
                                    ),
                                ],
                                spacing=10,
                            ),
                            bgcolor=p_col["card_sec"],
                            border=ft.Border.all(1, p_col["border"]),
                            border_radius=8,
                            padding=10,
                            on_click=generar_y_abrir_pdf,
                            ink=True,
                        ),
                        ft.Container(
                            content=ft.Row(
                                [
                                    ft.Icon(ft.Icons.PRINT_ROUNDED, color="#0284C7", size=26),
                                    ft.Column(
                                        [
                                            ft.Text("Impresión Directa (HTML Navegador)", weight=ft.FontWeight.BOLD, size=13),
                                            ft.Text("Abre la vista de impresión del sistema.", size=11, color=p_col["muted"]),
                                        ],
                                        spacing=1,
                                        expand=True,
                                    ),
                                ],
                                spacing=10,
                            ),
                            bgcolor=p_col["card_sec"],
                            border=ft.Border.all(1, p_col["border"]),
                            border_radius=8,
                            padding=10,
                            on_click=generar_y_abrir_html,
                            ink=True,
                        ),
                        ft.Container(
                            content=ft.Row(
                                [
                                    ft.Icon(ft.Icons.DESCRIPTION_OUTLINED, color="#059669", size=26),
                                    ft.Column(
                                        [
                                            ft.Text("Ver / Copiar Listado en Pantalla (Móvil)", weight=ft.FontWeight.BOLD, size=13),
                                            ft.Text("Ideal en celulares para copiar o compartir por WhatsApp.", size=11, color=p_col["muted"]),
                                        ],
                                        spacing=1,
                                        expand=True,
                                    ),
                                ],
                                spacing=10,
                            ),
                            bgcolor=p_col["card_sec"],
                            border=ft.Border.all(1, p_col["border"]),
                            border_radius=8,
                            padding=10,
                            on_click=ver_listado_texto_imprimible,
                            ink=True,
                        ),
                    ],
                    spacing=10,
                    scroll=ft.ScrollMode.ADAPTIVE,
                    tight=True,
                ),
                width=obtener_ancho_modal(),
            ),
            actions=[ft.TextButton(content="Cerrar", on_click=lambda ev: page.pop_dialog())],
        )
        page.show_dialog(dlg)

    # =========================================================================
    # CAMBIO DE TEMA ADAPTABLE (CLARO / OSCURO MATERIAL 3)
    # =========================================================================
    def alternar_tema(e=None):
        estado["modo_oscuro"] = not estado["modo_oscuro"]
        p_col = pal()
        page.theme_mode = ft.ThemeMode.DARK if estado["modo_oscuro"] else ft.ThemeMode.LIGHT
        page.bgcolor = p_col["bg"]
        btn_tema.icon = ft.Icons.LIGHT_MODE_OUTLINED if estado["modo_oscuro"] else ft.Icons.DARK_MODE_OUTLINED
        btn_tema.icon_color = p_col["text"]
        txt_titulo_app.color = p_col["text"]
        btn_pag_ant.icon_color = p_col["text"]
        btn_pag_sig.icon_color = p_col["text"]

        card_tasa_dolar.bgcolor = p_col["card"]
        card_tasa_dolar.border = ft.Border.all(1, p_col["border"])
        barra_paginacion.bgcolor = p_col["card"]
        barra_paginacion.border = ft.Border.all(1, p_col["border"])
        input_busqueda.bgcolor = p_col["card"]
        input_busqueda.border_color = p_col["border"]

        for cont in kpi_containers:
            cont.bgcolor = p_col["card"]
            cont.border = ft.Border.all(1, p_col["border"])
        for t_lbl in kpi_titulos:
            t_lbl.color = p_col["muted"]
        txt_kpi_total_prods.color = p_col["text"]

        actualizar_panel_tasas()
        actualizar_estilo_chips()
        renderizar_pagina_actual()

    btn_tema = ft.IconButton(
        icon=ft.Icons.DARK_MODE_OUTLINED,
        icon_color="#0F172A",
        tooltip="Cambiar tema Claro / Oscuro",
        on_click=alternar_tema,
    )

    # =========================================================================
    # BARRA SUPERIOR DE ACCIONES Y FLOATING ACTION BUTTON (+)
    # =========================================================================
    btn_importar = ft.FilledTonalButton(
        content="Importar",
        icon=ft.Icons.UPLOAD_FILE_ROUNDED,
        on_click=abrir_modal_importar,
    )

    btn_exportar = ft.FilledTonalButton(
        content="Imprimir / PDF",
        icon=ft.Icons.PRINT_ROUNDED,
        on_click=abrir_modal_exportacion,
    )

    btn_nuevo = ft.FilledButton(
        content="Nuevo",
        icon=ft.Icons.ADD_ROUNDED,
        bgcolor="#0284C7",
        color=ft.Colors.WHITE,
        on_click=abrir_modal_nuevo_producto,
    )

    barra_superior = ft.Row(
        controls=[
            ft.Row(controls=[icono_app, txt_titulo_app], spacing=6),
            ft.Row(controls=[btn_tema, btn_importar, btn_exportar, btn_nuevo], spacing=6, wrap=True),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        wrap=True,
    )

    # Botón flotante (+) Material 3 nativo para agregar artículos con un toque en celular
    page.floating_action_button = ft.FloatingActionButton(
        icon=ft.Icons.ADD_ROUNDED,
        bgcolor="#0284C7",
        foreground_color=ft.Colors.WHITE,
        tooltip="Agregar nuevo artículo",
        on_click=abrir_modal_nuevo_producto,
    )

    # =========================================================================
    # ENSAMBLAJE DE LA VISTA PRINCIPAL
    # =========================================================================
    page.add(
        barra_superior,
        card_tasa_dolar,
        barra_kpis,
        fila_busqueda,
        ft.Row(
            controls=[fila_filtros, lbl_contador_resultados],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            wrap=True,
        ),
        lista_cards_container,
        barra_paginacion,
    )

    # Carga inicial inmediata (100% offline desde SQLite en 0ms)
    recargar_datos_y_renderizar()


if __name__ == "__main__":
    ft.run(main)
