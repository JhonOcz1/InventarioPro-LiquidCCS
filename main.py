"""
main.py - Aplicación Móvil (Android APK) y de Escritorio (PC) de Inventario con Python, SQLite y Flet
Implementa Material 3 adaptable (Claro/Oscuro), cálculo dinámico de arbitraje cambiario
(Tasa BCV y Multiplicador Global editable 1100/1200), orden A-Z (Stock primero),
descripción corta automática de características y persistencia Android segura.
"""

import os
import sys
import math
import time
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
    # IMPORTANTE: NO usar page.horizontal_alignment = STRETCH ni Wrap + expand=True
    # para evitar RenderBox/ParentDataWidgetError (pantalla gris en Flutter).
    # =========================================================================
    page.title = "Sistema de Inventario - LiquidCCS"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(color_scheme_seed="#0284C7", use_material3=True)
    page.bgcolor = "#F8FAFC"
    page.padding = ft.Padding.symmetric(horizontal=10, vertical=6)
    page.spacing = 6

    if hasattr(page, "window") and page.window is not None:
        page.window.width = 1100
        page.window.height = 840
        page.window.min_width = 360
        page.window.min_height = 600

    tasas_iniciales = database.obtener_tasas()
    estado = {
        "modo_oscuro": False,
        "modo_compacto": False,
        "ultimo_cambio_compacto": 0.0,
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

    # Flet 1.1.2: FilePicker es un Service y se auto-registra; NO añadir a page.overlay
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
                "mult_box_bg": "#451A03",
                "mult_box_border": "#D97706",
                "mult_box_txt": "#FCD34D",
                "repo_box_bg": "#0C4A6E",
                "repo_box_border": "#0284C7",
                "repo_box_txt": "#7DD3FC",
                "ubic_bg": "#3B0764",
                "ubic_txt": "#E9D5FF",
                "sku_bg": "#1E3A8A",
                "sku_txt": "#BFDBFE",
                "sec_stock_bg": "#064E3B",
                "sec_stock_txt": "#6EE7B7",
                "sec_zero_bg": "#450A0A",
                "sec_zero_txt": "#FCA5A5",
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
            "mult_box_bg": "#FEF3C7",
            "mult_box_border": "#F59E0B",
            "mult_box_txt": "#92400E",
            "repo_box_bg": "#F0F9FF",
            "repo_box_border": "#7DD3FC",
            "repo_box_txt": "#0369A1",
            "ubic_bg": "#F3E8FF",
            "ubic_txt": "#6B21A8",
            "sku_bg": "#DBEAFE",
            "sku_txt": "#1E40AF",
            "sec_stock_bg": "#ECFDF5",
            "sec_stock_txt": "#15803D",
            "sec_zero_bg": "#FEF2F2",
            "sec_zero_txt": "#B91C1C",
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
    # PANEL DE TASAS Y MULTIPLICADOR GLOBAL (BCV + BASE 1100 EDITABLE)
    # =========================================================================
    txt_titulo_app = ft.Text("Inventario Pro", size=17, weight=ft.FontWeight.BOLD, color="#0F172A")
    icono_app = ft.Icon(ft.Icons.INVENTORY_ROUNDED, color="#0284C7", size=22)

    lbl_titulo_bcv = ft.Text("Tasa Dólar BCV", size=10, color="#64748B", weight=ft.FontWeight.W_500)
    lbl_titulo_mult = ft.Text("Multiplicador Global", size=10, color="#64748B", weight=ft.FontWeight.W_500)
    txt_tasa_bcv = ft.Text("", size=14, weight=ft.FontWeight.BOLD, color="#0F172A")
    txt_tasa_repo = ft.Text("", size=14, weight=ft.FontWeight.BOLD, color="#B45309")
    lbl_fecha_tasa = ft.Text("", size=10, color="#64748B")
    badge_estado_tasas = ft.Container(
        content=ft.Text("SQLITE", size=9, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
        bgcolor="#0284C7",
        padding=ft.Padding.symmetric(horizontal=6, vertical=2),
        border_radius=10,
    )

    def refrescar_tasa_api(e=None):
        """Sincroniza la tasa BCV desde DolarApi cuando el usuario lo solicita."""
        btn_sync_api.disabled = True
        lbl_fecha_tasa.value = "Consultando DolarApi en línea..."
        page.update()

        def tarea_red():
            res = dolar_service.obtener_tasa_dolar(forzar_red=True)
            if res.get("online"):
                # Actualizamos la Tasa BCV desde API conservando el Multiplicador Global si el usuario no desea pisarlo
                estado["tasa_bcv"] = float(res["bcv"])
                estado["tasa_online"] = True
                estado["tasa_mensaje"] = f"Tasa BCV API ({res['fecha']})"
                database.actualizar_tasas(estado["tasa_bcv"], estado["tasa_reposicion"])
            else:
                estado["tasa_online"] = False
                estado["tasa_mensaje"] = "Sin conexión: usando valores locales"
            actualizar_panel_tasas()
            actualizar_kpis()
            renderizar_pagina_actual()
            btn_sync_api.disabled = False
            page.update()

            if res.get("online"):
                notificar(
                    f"Tasa BCV actualizada a {database.formatear_bs(estado['tasa_bcv'])} | "
                    f"Multiplicador: {estado['tasa_reposicion']:,.2f}"
                )
            else:
                notificar("Sin acceso a internet. Se mantienen tus tasas locales.", es_error=True)

        threading.Thread(target=tarea_red, daemon=True).start()

    def abrir_modal_tasas(e=None):
        """Modal para editar el Multiplicador Global (1100) y la Tasa BCV recalibrando todo el inventario."""
        p_col = pal()
        in_bcv = ft.TextField(
            label="Tasa Oficial Dólar BCV (Bs/$)",
            value=f"{estado['tasa_bcv']:.2f}",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_radius=8,
            content_padding=10,
        )
        in_repo = ft.TextField(
            label="Multiplicador Global / Precio Base Bs. (ej. 1100)",
            value=f"{estado['tasa_reposicion']:.2f}",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_radius=8,
            content_padding=10,
            autofocus=True,
        )
        lbl_ejemplo = ft.Text("", size=12, color=p_col["accent"], weight=ft.FontWeight.W_600)

        def actualizar_preview_tasas(ev=None):
            try:
                bcv_v = float((in_bcv.value or "").replace(",", "."))
                rep_v = float((in_repo.value or "").replace(",", "."))
                if bcv_v > 0 and rep_v > 0:
                    factor = rep_v / bcv_v
                    ej_mult = 10.0 * rep_v
                    ej_bcv_bs = 10.0 * bcv_v
                    ej_aj_usd = ej_mult / bcv_v
                    lbl_ejemplo.value = (
                        f"Ejemplo artículo base $10.00 (factor ×{factor:.4f}):\n"
                        f"• Multiplicación (× {rep_v:,.0f}): {database.formatear_bs(ej_mult)}\n"
                        f"• A Tasa BCV ({bcv_v:,.2f}): {database.formatear_bs(ej_bcv_bs)}\n"
                        f"• Ajustado BCV en USD: ${ej_aj_usd:,.2f}"
                    )
                else:
                    lbl_ejemplo.value = "Ambos montos deben ser mayores a 0"
            except Exception:
                lbl_ejemplo.value = "Ingresa valores numéricos válidos"
            if ev is not None:
                page.update()

        def aplicar_preset_mult(valor: float):
            in_repo.value = f"{valor:.2f}"
            actualizar_preview_tasas(ev="preset")

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
                notificar("Ingresa montos numéricos válidos (ej. 914.02 y 1100)", es_error=True)
                return

            if nuevo_bcv <= 0 or nuevo_repo <= 0:
                notificar("Ambos valores deben ser mayores a cero", es_error=True)
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
                f"Actualizado: BCV {database.formatear_bs(nuevo_bcv)} | "
                f"Multiplicador Global {nuevo_repo:,.2f}"
            )

        dlg = ft.AlertDialog(
            title=ft.Row(
                [
                    ft.Row([ft.Icon(ft.Icons.TUNE_ROUNDED, color="#0284C7"), ft.Text("Editar Multiplicador y Tasa BCV", size=15, weight=ft.FontWeight.BOLD)], spacing=8),
                    ft.IconButton(ft.Icons.CLOSE_ROUNDED, icon_color=p_col["muted"], on_click=cerrar),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            "Si aumenta la tasa BCV o aumentas el multiplicador global (ej. 1100 -> 1200), "
                            "todos los precios del catálogo se recalculan al instante.",
                            size=12,
                            color=p_col["muted"],
                        ),
                        in_bcv,
                        in_repo,
                        ft.Row(
                            controls=[
                                ft.Text("Valores rápidos:", size=11, color=p_col["muted"]),
                                ft.OutlinedButton(content="1100", on_click=lambda e: aplicar_preset_mult(1100.0)),
                                ft.OutlinedButton(content="1150", on_click=lambda e: aplicar_preset_mult(1150.0)),
                                ft.OutlinedButton(content="1200", on_click=lambda e: aplicar_preset_mult(1200.0)),
                            ],
                            spacing=6,
                            wrap=True,
                        ),
                        ft.Container(
                            content=lbl_ejemplo,
                            bgcolor=p_col["repo_box_bg"],
                            border=ft.Border.all(1, p_col["repo_box_border"]),
                            border_radius=8,
                            padding=10,
                        ),
                        ft.Divider(height=10, color=p_col["border"]),
                        ft.FilledButton(
                            content="Aplicar a Todo el Inventario",
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

    btn_sync_api = ft.IconButton(
        icon=ft.Icons.REFRESH_ROUNDED,
        icon_color="#0284C7",
        icon_size=18,
        width=28,
        height=28,
        padding=0,
        tooltip="Actualizar tasa BCV desde DolarApi (internet)",
        on_click=refrescar_tasa_api,
    )

    badge_resumen_compacto = ft.Container(
        content=ft.Text("", size=10, weight=ft.FontWeight.BOLD, color="#92400E"),
        bgcolor="#FEF3C7",
        border=ft.Border.all(1, "#F59E0B"),
        border_radius=12,
        padding=ft.Padding.symmetric(horizontal=8, vertical=3),
        visible=False,
        animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
        ink=True,
        tooltip="Editar Tasa BCV / Multiplicador 1100",
        on_click=abrir_modal_tasas,
    )

    def actualizar_panel_tasas():
        p_col = pal()
        bcv_s = database.formatear_bs(estado["tasa_bcv"])
        rep_s = database.formatear_bs(estado["tasa_reposicion"])
        factor = estado["tasa_reposicion"] / estado["tasa_bcv"] if estado["tasa_bcv"] > 0 else 1.0

        lbl_titulo_bcv.color = p_col["muted"]
        lbl_titulo_mult.color = p_col["muted"]
        txt_tasa_bcv.value = bcv_s
        txt_tasa_bcv.color = p_col["text"]
        txt_tasa_repo.value = rep_s
        txt_tasa_repo.color = p_col["mult_box_txt"]
        lbl_fecha_tasa.value = f"{estado['tasa_mensaje']} • Relación: ×{factor:.4f}"
        lbl_fecha_tasa.color = p_col["muted"]

        badge_resumen_compacto.bgcolor = p_col["mult_box_bg"]
        badge_resumen_compacto.border = ft.Border.all(1, p_col["mult_box_border"])
        badge_resumen_compacto.content.color = p_col["mult_box_txt"]
        badge_resumen_compacto.content.value = f"BCV {estado['tasa_bcv']:,.2f} | ×{estado['tasa_reposicion']:,.0f}"

        if estado["tasa_online"]:
            badge_estado_tasas.bgcolor = "#10B981"
            badge_estado_tasas.content.value = "API LIVE"
        else:
            badge_estado_tasas.bgcolor = "#0284C7"
            badge_estado_tasas.content.value = "LOCAL"

    actualizar_panel_tasas()

    card_tasa_dolar = ft.Container(
        content=ft.Column(
            controls=[
                # Fila superior: título + estado a la izquierda, botón recarga en la esquina superior derecha
                ft.Row(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.CURRENCY_EXCHANGE_ROUNDED, color="#0284C7", size=18),
                                ft.Text(
                                    "TASAS DEL DÓLAR Y MULTIPLICADOR",
                                    size=11,
                                    weight=ft.FontWeight.BOLD,
                                    color="#0284C7",
                                    expand_loose=True,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                badge_estado_tasas,
                            ],
                            spacing=6,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            expand=True,
                        ),
                        btn_sync_api,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                # Cuerpo: valores bien separados y cómodos de leer sin solapamientos
                ft.ResponsiveRow(
                    controls=[
                        ft.Column(
                            controls=[lbl_titulo_bcv, txt_tasa_bcv],
                            spacing=1,
                            col={"xs": 6, "sm": 6},
                        ),
                        ft.Column(
                            controls=[lbl_titulo_mult, txt_tasa_repo],
                            spacing=1,
                            col={"xs": 6, "sm": 6},
                        ),
                    ],
                    spacing=8,
                    run_spacing=4,
                ),
                lbl_fecha_tasa,
            ],
            spacing=4,
        ),
        bgcolor=ft.Colors.WHITE,
        border=ft.Border.all(1, "#E2E8F0"),
        border_radius=12,
        padding=ft.Padding.symmetric(horizontal=12, vertical=8),
    )

    # =========================================================================
    # MÉTRICAS KPI DEL INVENTARIO
    # =========================================================================
    txt_kpi_total_prods = ft.Text("0", size=14, weight=ft.FontWeight.BOLD, color="#0F172A")
    txt_kpi_total_stock = ft.Text("0", size=14, weight=ft.FontWeight.BOLD, color="#059669")
    txt_kpi_con_stock = ft.Text("0", size=14, weight=ft.FontWeight.BOLD, color="#0284C7")
    txt_kpi_valor_bcv = ft.Text("$0.00", size=14, weight=ft.FontWeight.BOLD, color="#7C3AED")

    kpi_containers = []
    kpi_titulos = []

    def kpi_box(titulo: str, txt_control: ft.Text, icon_name, color_accent: str):
        lbl_t = ft.Text(titulo, size=10, color="#64748B", weight=ft.FontWeight.W_500)
        kpi_titulos.append(lbl_t)
        cont = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(icon_name, color=color_accent, size=19),
                    ft.Column(controls=[lbl_t, txt_control], spacing=0),
                ],
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.all(1, "#E2E8F0"),
            border_radius=10,
            padding=6,
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
        spacing=6,
        run_spacing=6,
    )

    def actualizar_kpis():
        stats = database.obtener_resumen_estadisticas()
        txt_kpi_total_prods.value = str(stats["total_items"])
        txt_kpi_total_stock.value = f"{stats['total_unidades']} u."
        txt_kpi_con_stock.value = f"{stats['items_con_stock']} / {stats['total_items']}"
        txt_kpi_valor_bcv.value = database.formatear_usd(stats["valor_bcv_ajustado_usd"])

    actualizar_kpis()

    # =========================================================================
    # BUSCADOR COMPACTO, ANIMACIONES DE CABECERA Y FILTROS
    # =========================================================================
    async def _scroll_lista_al_inicio():
        try:
            await lista_cards_container.scroll_to(
                offset=0,
                duration=200,
                curve=ft.AnimationCurve.EASE_OUT_CUBIC,
            )
        except Exception:
            pass

    def ir_al_inicio_lista():
        """Reposiciona la lista suavemente al primer resultado (offset=0)."""
        estado["ultimo_cambio_compacto"] = time.monotonic()
        if hasattr(page, "run_task"):
            try:
                page.run_task(_scroll_lista_al_inicio)
            except Exception:
                pass

    def on_busqueda_change(e):
        estado["filtro_texto"] = input_busqueda.value or ""
        estado["pagina_actual"] = 1
        if estado["filtro_texto"].strip():
            aplicar_modo_compacto(True, actualizar_ui=False)
        recargar_datos_y_renderizar()
        ir_al_inicio_lista()

    def limpiar_busqueda(e):
        if not input_busqueda.value and not estado["filtro_texto"]:
            return
        input_busqueda.value = ""
        estado["filtro_texto"] = ""
        estado["pagina_actual"] = 1
        recargar_datos_y_renderizar()
        ir_al_inicio_lista()

    input_busqueda = ft.TextField(
        hint_text="Buscar nombre, característica, SKU o ubicación...",
        prefix_icon=ft.Icons.SEARCH,
        suffix=ft.IconButton(
            ft.Icons.CLEAR,
            icon_size=16,
            padding=0,
            on_click=limpiar_busqueda,
            tooltip="Limpiar búsqueda",
        ),
        bgcolor=ft.Colors.WHITE,
        border_color="#94A3B8",
        focused_border_color="#0284C7",
        border_radius=10,
        content_padding=ft.Padding.symmetric(horizontal=8, vertical=6),
        text_size=13,
        height=42,
        expand=True,
        on_change=on_busqueda_change,
    )

    btn_quick_tasa = ft.IconButton(
        icon=ft.Icons.CURRENCY_EXCHANGE_ROUNDED,
        icon_color="#B45309",
        icon_size=18,
        width=32,
        height=32,
        padding=0,
        tooltip="Editar Tasa BCV / 1100",
        on_click=lambda e: abrir_modal_tasas(e),
    )
    btn_quick_import = ft.IconButton(
        icon=ft.Icons.UPLOAD_FILE_ROUNDED,
        icon_color="#0284C7",
        icon_size=18,
        width=32,
        height=32,
        padding=0,
        tooltip="Importar artículos",
        on_click=lambda e: abrir_modal_importar(e),
    )
    btn_quick_export = ft.IconButton(
        icon=ft.Icons.PRINT_ROUNDED,
        icon_color="#334155",
        icon_size=18,
        width=32,
        height=32,
        padding=0,
        tooltip="Exportar / Imprimir PDF",
        on_click=lambda e: abrir_modal_exportacion(e),
    )

    modulos_accesibles_compactos = ft.Container(
        content=ft.Row(
            controls=[btn_quick_tasa, btn_quick_import, btn_quick_export],
            spacing=2,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        width=0,
        opacity=0.0,
        animate_size=ft.Animation(220, ft.AnimationCurve.EASE_OUT_CUBIC),
        animate_opacity=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )

    def aplicar_modo_compacto(compacto: bool, actualizar_ui: bool = True):
        """Reduce o expande suavemente el menú superior para maximizar resultados al bajar."""
        if estado["modo_compacto"] == compacto:
            return
        estado["modo_compacto"] = compacto
        estado["ultimo_cambio_compacto"] = time.monotonic()

        panel_superior_colapsable.height = 0 if compacto else None
        panel_superior_colapsable.opacity = 0.0 if compacto else 1.0
        modulos_accesibles_compactos.width = None if compacto else 0
        modulos_accesibles_compactos.opacity = 1.0 if compacto else 0.0
        badge_resumen_compacto.visible = compacto

        btn_toggle_compacto.rotate = ft.Rotate(math.pi if compacto else 0)
        btn_toggle_compacto.tooltip = (
            "Expandir menú superior" if compacto else "Compactar menú superior"
        )
        if actualizar_ui:
            page.update()

    def toggle_modo_compacto_manual(e=None):
        aplicar_modo_compacto(not estado["modo_compacto"], actualizar_ui=True)

    btn_toggle_compacto = ft.IconButton(
        icon=ft.Icons.KEYBOARD_ARROW_UP_ROUNDED,
        icon_color="#475569",
        icon_size=20,
        width=32,
        height=32,
        padding=0,
        rotate=ft.Rotate(0),
        animate_rotation=ft.Animation(260, ft.AnimationCurve.EASE_OUT_CUBIC),
        tooltip="Compactar menú superior",
        on_click=toggle_modo_compacto_manual,
    )

    # Row SIN wrap=True para que expand=True estire la barra de búsqueda sin errores de layout
    fila_busqueda = ft.Row(
        controls=[input_busqueda, modulos_accesibles_compactos, btn_toggle_compacto],
        spacing=4,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

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
        estado["pagina_actual"] = 1
        barra_navegacion.selected_index = 1 if categoria == "stock" else 0
        actualizar_estilo_chips()
        recargar_datos_y_renderizar()
        ir_al_inicio_lista()

    btn_chip_todos = ft.Container(
        content=ft.Text("Todos (A-Z)", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
        bgcolor="#0F172A",
        border=ft.Border.all(1, "#CBD5E1"),
        border_radius=18,
        padding=ft.Padding.symmetric(horizontal=10, vertical=4),
        animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
        on_click=lambda e: cambiar_filtro_categoria("todos"),
        ink=True,
    )

    btn_chip_stock = ft.Container(
        content=ft.Text("Con Stock (>0)", size=11, weight=ft.FontWeight.BOLD, color="#334155"),
        bgcolor=ft.Colors.WHITE,
        border=ft.Border.all(1, "#CBD5E1"),
        border_radius=18,
        padding=ft.Padding.symmetric(horizontal=10, vertical=4),
        animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
        on_click=lambda e: cambiar_filtro_categoria("stock"),
        ink=True,
    )

    btn_chip_agotados = ft.Container(
        content=ft.Text("Agotados", size=11, weight=ft.FontWeight.BOLD, color="#334155"),
        bgcolor=ft.Colors.WHITE,
        border=ft.Border.all(1, "#CBD5E1"),
        border_radius=18,
        padding=ft.Padding.symmetric(horizontal=10, vertical=4),
        animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
        on_click=lambda e: cambiar_filtro_categoria("agotados"),
        ink=True,
    )

    lbl_contador_resultados = ft.Text("", size=11, color="#475569", weight=ft.FontWeight.W_600)

    fila_filtros = ft.Row(
        controls=[
            btn_chip_todos,
            btn_chip_stock,
            btn_chip_agotados,
            badge_resumen_compacto,
            lbl_contador_resultados,
        ],
        spacing=6,
        run_spacing=4,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        wrap=True,
    )

    # =========================================================================
    # CONTROLES DE PAGINACIÓN RÁPIDA
    # =========================================================================
    lbl_pagina_info = ft.Text("Página 1 de 1", size=12, weight=ft.FontWeight.W_600, color="#334155")

    def ir_pagina_anterior(e):
        if estado["pagina_actual"] > 1:
            estado["pagina_actual"] -= 1
            renderizar_pagina_actual()
            ir_al_inicio_lista()

    def ir_pagina_siguiente(e):
        if estado["pagina_actual"] < estado["total_paginas"]:
            estado["pagina_actual"] += 1
            renderizar_pagina_actual()
            ir_al_inicio_lista()

    btn_pag_ant = ft.IconButton(
        icon=ft.Icons.CHEVRON_LEFT_ROUNDED,
        icon_color="#0F172A",
        icon_size=20,
        padding=0,
        tooltip="Página anterior",
        on_click=ir_pagina_anterior,
    )
    btn_pag_sig = ft.IconButton(
        icon=ft.Icons.CHEVRON_RIGHT_ROUNDED,
        icon_color="#0F172A",
        icon_size=20,
        padding=0,
        tooltip="Página siguiente",
        on_click=ir_pagina_siguiente,
    )

    barra_paginacion = ft.Container(
        content=ft.Row(
            controls=[btn_pag_ant, lbl_pagina_info, btn_pag_sig],
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=6,
        ),
        bgcolor=ft.Colors.WHITE,
        border=ft.Border.all(1, "#E2E8F0"),
        border_radius=10,
        padding=ft.Padding.symmetric(horizontal=8, vertical=0),
    )

    # =========================================================================
    # LISTA DE PRODUCTOS (STOCK ARRIBA A-Z / AGOTADOS AL FINAL A-Z)
    # =========================================================================
    def on_lista_scroll(e: ft.OnScrollEvent):
        pixels = getattr(e, "pixels", 0.0) or 0.0
        ahora = time.monotonic()
        if pixels > 45 and not estado["modo_compacto"]:
            if ahora - estado["ultimo_cambio_compacto"] >= 0.35:
                aplicar_modo_compacto(True)
        elif pixels <= 5 and estado["modo_compacto"] and not estado["filtro_texto"].strip():
            if ahora - estado["ultimo_cambio_compacto"] >= 0.45:
                aplicar_modo_compacto(False)

    lista_cards_container = ft.ListView(
        controls=[],
        spacing=8,
        padding=ft.Padding.only(bottom=12),
        scroll_interval=50,
        on_scroll=on_lista_scroll,
        expand=True,
    )

    def ajustar_stock_rapido(producto_id: int, delta: int):
        """Actualiza el stock en SQLite bloqueando negativos; si cambia de grupo (0 <-> >0), reordena A-Z."""
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

        cambio_grupo = (cant_actual == 0 and nueva_cantidad > 0) or (cant_actual > 0 and nueva_cantidad == 0)
        if cambio_grupo:
            recargar_datos_y_renderizar()
            return

        badge_st: ft.Container = ref["badge_stock"]
        badge_st.content.value = f"{nueva_cantidad} en stock"
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
        """Crea tarjeta adaptable con descripción de características y cálculos BCV/Multiplicador."""
        p_col = pal()
        t_bcv = estado["tasa_bcv"]
        t_repo = estado["tasa_reposicion"]
        cant = p["cantidad"]
        es_disponible = cant > 0

        precios = database.calcular_precios_producto(p, t_bcv, t_repo)
        costo_str = database.formatear_usd(p["costo_usd"]) if p.get("costo_usd") else "-"
        desc_corta = p.get("descripcion_corta") or database.obtener_descripcion_caracteristicas(p)

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
                    content=ft.Text(f"📍 {p['ubicacion_nota']}", size=11, weight=ft.FontWeight.W_600, color=p_col["ubic_txt"]),
                    bgcolor=p_col["ubic_bg"],
                    border_radius=6,
                    padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                )
            )

        txt_cant_rapida = ft.Text(str(cant), size=14, weight=ft.FontWeight.BOLD, color=p_col["text"])

        tarjetas_ui_refs[p["id"]] = {
            "datos": p,
            "badge_stock": badge_stock,
            "txt_cant": txt_cant_rapida,
        }

        origen_lbl = "PRECIO VENTA ($)"
        color_bcv = p_col["bcv_box_txt"] if precios["tiene_precio"] else p_col["muted"]
        color_mult = p_col["mult_box_txt"] if precios["tiene_precio"] else p_col["muted"]

        # Bloque 1: Precio Base ($)
        col_base = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(origen_lbl, size=10, color=p_col["muted"], weight=ft.FontWeight.W_600),
                    ft.Text(precios["precio_base_str"], size=14, weight=ft.FontWeight.BOLD, color=p_col["text"]),
                    ft.Text(f"Costo: {costo_str}", size=10, color=p_col["muted"]),
                ],
                spacing=1,
            ),
            padding=6,
            col={"xs": 6, "sm": 3},
        )

        # Bloque 2: Multiplicación (USD × 1100 o valor global configurado)
        mult_titulo = f"MULTIPL. (× {t_repo:,.0f})"
        col_mult_bs = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(mult_titulo, size=10, color=color_mult, weight=ft.FontWeight.BOLD),
                    ft.Text(precios["monto_bs_reposicion_str"], size=13, weight=ft.FontWeight.BOLD, color=color_mult),
                    ft.Text("Base Bs. Reposición", size=10, color=p_col["muted"]),
                ],
                spacing=1,
            ),
            bgcolor=p_col["mult_box_bg"] if precios["tiene_precio"] else p_col["card_sec"],
            border=ft.Border.all(1, p_col["mult_box_border"] if precios["tiene_precio"] else p_col["border"]),
            border_radius=8,
            padding=6,
            col={"xs": 6, "sm": 3},
        )

        # Bloque 3: Precio Ajustado BCV ($) y Bs a BCV directo
        col_ajustado_bcv = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("AJUSTADO BCV ($)", size=10, color=color_bcv, weight=ft.FontWeight.BOLD),
                    ft.Text(precios["precio_venta_bcv_usd_str"], size=14, weight=ft.FontWeight.BOLD, color=color_bcv),
                    ft.Text(f"BCV Directo: {precios['monto_bs_bcv_directo_str']}", size=10, color=p_col["muted"]),
                ],
                spacing=1,
            ),
            bgcolor=p_col["bcv_box_bg"] if precios["tiene_precio"] else p_col["card_sec"],
            border=ft.Border.all(1, p_col["bcv_box_border"] if precios["tiene_precio"] else p_col["border"]),
            border_radius=8,
            padding=6,
            col={"xs": 6, "sm": 3},
        )

        # Bloque 4: Control rápido de stock (- / +)
        col_stock_ctrl = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("STOCK", size=10, color=p_col["muted"], weight=ft.FontWeight.W_600),
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
                    # Fila 1: Badges + Editar / Eliminar (sin wrap anidado ni expand)
                    ft.Row(
                        controls=[
                            ft.Row(controls=badges_cabecera, spacing=6),
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
                    # Fila 2 y 3: Nombre del producto y descripción corta con características
                    ft.Text(p["nombre"], size=14, weight=ft.FontWeight.W_700, color=p_col["text"]),
                    ft.Text(f"📋 {desc_corta}", size=12, color=p_col["subtext"], weight=ft.FontWeight.W_500),
                    ft.Divider(height=1, color=p_col["border"]),
                    # Fila 4: Desglose financiero y control de stock
                    ft.ResponsiveRow(
                        controls=[col_base, col_mult_bs, col_ajustado_bcv, col_stock_ctrl],
                        spacing=8,
                        run_spacing=8,
                    ),
                ],
                spacing=5,
            ),
            bgcolor=p_col["card"],
            border=ft.Border.all(1, p_col["border"]),
            border_radius=12,
            padding=12,
            animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
        )

    def crear_encabezado_seccion(titulo: str, es_stock: bool) -> ft.Container:
        p_col = pal()
        bg = p_col["sec_stock_bg"] if es_stock else p_col["sec_zero_bg"]
        fg = p_col["sec_stock_txt"] if es_stock else p_col["sec_zero_txt"]
        icono = ft.Icons.CHECK_CIRCLE_ROUNDED if es_stock else ft.Icons.CANCEL_OUTLINED
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(icono, size=15, color=fg),
                    ft.Text(titulo, size=12, weight=ft.FontWeight.BOLD, color=fg),
                ],
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=bg,
            border_radius=8,
            padding=ft.Padding.symmetric(horizontal=10, vertical=6),
        )

    def renderizar_pagina_actual():
        """Dibuja únicamente el lote activo (máx. 40 tarjetas) separando Stock A-Z arriba y Agotados A-Z abajo."""
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
            mostro_header_stock = False
            mostro_header_agotados = False
            for prod in lote:
                if prod["cantidad"] > 0 and not mostro_header_stock:
                    lista_cards_container.controls.append(
                        crear_encabezado_seccion("DISPONIBLES EN STOCK (Orden A-Z)", es_stock=True)
                    )
                    mostro_header_stock = True
                elif prod["cantidad"] == 0 and not mostro_header_agotados:
                    lista_cards_container.controls.append(
                        crear_encabezado_seccion("SIN STOCK / AGOTADOS (Orden A-Z)", es_stock=False)
                    )
                    mostro_header_agotados = True
                lista_cards_container.controls.append(crear_tarjeta_producto(prod))

        lbl_contador_resultados.value = f"{total} art."
        lbl_contador_resultados.color = p_col["subtext"]
        lbl_pagina_info.value = f"Página {pag} de {total_pags} ({inicio + 1 if total else 0}-{min(fin, total)} de {total})"
        lbl_pagina_info.color = p_col["text"]
        btn_pag_ant.disabled = (pag <= 1)
        btn_pag_sig.disabled = (pag >= total_pags)
        barra_paginacion.visible = (total > ITEMS_POR_PAGINA)
        page.update()

    def recargar_datos_y_renderizar():
        """Consulta SQLite (Stock primero A-Z, Agotados al final A-Z) y actualiza la vista."""
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
        in_desc_corta = ft.TextField(label="Descripción / Características (Opcional)", hint_text="Se genera automática si se deja vacío", border_radius=8, content_padding=10, expand=True)
        in_precio_usd = ft.TextField(label="Precio Venta ($)", hint_text="10.00", keyboard_type=ft.KeyboardType.NUMBER, border_radius=8, content_padding=10, expand=True)
        in_costo = ft.TextField(label="Costo Base ($)", hint_text="4.50", keyboard_type=ft.KeyboardType.NUMBER, border_radius=8, content_padding=10, expand=True)
        in_ubicacion = ft.TextField(label="Ubicación / Nota", hint_text="Depósito, BRIAN...", border_radius=8, content_padding=10, expand=True)

        txt_preview_calc = ft.Text("Vista previa: Sin precio", size=12, color=p_col["accent"], weight=ft.FontWeight.W_600)

        def parse_float(val):
            if not val or not val.strip():
                return None
            try:
                return float(val.strip().replace(",", "."))
            except ValueError:
                return None

        def actualizar_preview_nuevo(ev=None):
            precio_val = parse_float(in_precio_usd.value)
            sim_prod = {
                "precio_detal_usd": precio_val,
                "precio_descuento_usd": precio_val,
            }
            c = database.calcular_precios_producto(sim_prod, estado["tasa_bcv"], estado["tasa_reposicion"])
            if c["tiene_precio"]:
                txt_preview_calc.value = (
                    f"Precio Venta: {c['precio_base_str']} | "
                    f"Mult. ({estado['tasa_reposicion']:,.0f}): {c['monto_bs_reposicion_str']}\n"
                    f"Ajustado BCV: {c['precio_venta_bcv_usd_str']} | BCV Directo: {c['monto_bs_bcv_directo_str']}"
                )
            else:
                txt_preview_calc.value = "Vista previa: Sin precio"
            if ev is not None:
                page.update()

        in_precio_usd.on_change = actualizar_preview_nuevo

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

            precio_venta = parse_float(in_precio_usd.value)
            exito = database.agregar_producto(
                sku=sku,
                nombre=nombre,
                cantidad=cantidad,
                precio_detal=precio_venta,
                precio_descuento=precio_venta,
                costo=parse_float(in_costo.value),
                ubicacion=(in_ubicacion.value or "").strip() or None,
                descripcion=(in_desc_corta.value or "").strip() or None,
            )

            if exito:
                page.pop_dialog()
                actualizar_kpis()
                recargar_datos_y_renderizar()
                ir_al_inicio_lista()
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
                        ft.Row([in_desc_corta], spacing=8),
                        ft.Row([in_precio_usd, in_costo], spacing=8),
                        ft.Container(
                            content=txt_preview_calc,
                            bgcolor=p_col["repo_box_bg"],
                            border=ft.Border.all(1, p_col["repo_box_border"]),
                            border_radius=8,
                            padding=8,
                        ),
                        ft.Row([in_ubicacion], spacing=8),
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

        precio_inicial = (
            p["precio_descuento_usd"]
            if (p.get("precio_descuento_usd") is not None and float(p["precio_descuento_usd"]) > 0)
            else p.get("precio_detal_usd")
        )

        ed_sku = ft.TextField(label="SKU / Código", value=p["sku"], border_radius=8, content_padding=10, expand=True)
        ed_cantidad = ft.TextField(label="Stock Actual", value=str(p["cantidad"]), keyboard_type=ft.KeyboardType.NUMBER, border_radius=8, content_padding=10, expand=True)
        ed_nombre = ft.TextField(label="Nombre del Producto", value=p["nombre"], border_radius=8, content_padding=10, expand=True)
        ed_desc_corta = ft.TextField(
            label="Descripción / Características",
            value=p.get("descripcion") or "",
            hint_text=p.get("descripcion_corta") or "Se genera automática si se deja vacío",
            border_radius=8,
            content_padding=10,
            expand=True,
        )
        ed_precio_usd = ft.TextField(
            label="Precio Venta ($)",
            value=str(precio_inicial) if precio_inicial is not None else "",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_radius=8,
            content_padding=10,
            expand=True,
        )
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
            precio_val = parse_float(ed_precio_usd.value)
            sim_prod = {
                "precio_detal_usd": precio_val,
                "precio_descuento_usd": precio_val,
            }
            c = database.calcular_precios_producto(sim_prod, estado["tasa_bcv"], estado["tasa_reposicion"])
            if c["tiene_precio"]:
                lbl_info_arbitraje.value = (
                    f"Precio Venta: {c['precio_base_str']} | "
                    f"Mult. ({estado['tasa_reposicion']:,.0f}): {c['monto_bs_reposicion_str']}\n"
                    f"Ajustado BCV: {c['precio_venta_bcv_usd_str']} | BCV Directo: {c['monto_bs_bcv_directo_str']}"
                )
            else:
                lbl_info_arbitraje.value = "Sin precio configurado"
            if ev is not None:
                page.update()

        actualizar_preview_edicion()
        ed_precio_usd.on_change = actualizar_preview_edicion

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

            precio_venta = parse_float(ed_precio_usd.value)
            exito = database.actualizar_producto(
                producto_id=producto_id,
                sku=(ed_sku.value or "").strip(),
                nombre=(ed_nombre.value or "").strip(),
                cantidad=nueva_cant,
                precio_detal=precio_venta,
                precio_descuento=precio_venta,
                costo=parse_float(ed_costo.value),
                ubicacion=(ed_ubicacion.value or "").strip() or None,
                descripcion=(ed_desc_corta.value or "").strip() or None,
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
                        ft.Row([ed_desc_corta], spacing=8),
                        ft.Row([ed_precio_usd, ed_costo], spacing=8),
                        ft.Container(
                            content=lbl_info_arbitraje,
                            bgcolor=p_col["repo_box_bg"],
                            border=ft.Border.all(1, p_col["repo_box_border"]),
                            border_radius=8,
                            padding=8,
                        ),
                        ft.Row([ed_ubicacion], spacing=8),
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
                            f"BCV: {database.formatear_bs(t_bcv)} | Multiplicador: {database.formatear_bs(t_repo)}",
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
        btn_toggle_compacto.icon_color = p_col["subtext"]
        btn_quick_tasa.icon_color = p_col["mult_box_txt"]
        btn_quick_import.icon_color = p_col["accent"]
        btn_quick_export.icon_color = p_col["subtext"]

        card_tasa_dolar.bgcolor = p_col["card"]
        card_tasa_dolar.border = ft.Border.all(1, p_col["border"])
        barra_paginacion.bgcolor = p_col["card"]
        barra_paginacion.border = ft.Border.all(1, p_col["border"])
        input_busqueda.bgcolor = p_col["card"]
        input_busqueda.border_color = p_col["border"]
        barra_navegacion.bgcolor = p_col["card"]
        barra_navegacion.indicator_color = "#0C4A6E" if estado["modo_oscuro"] else "#E0F2FE"

        for cont in kpi_containers:
            cont.bgcolor = p_col["card"]
            cont.border = ft.Border.all(1, p_col["border"])
        for t_lbl in kpi_titulos:
            t_lbl.color = p_col["muted"]
        txt_kpi_total_prods.color = p_col["text"]

        actualizar_panel_tasas()
        actualizar_estilo_chips()
        renderizar_pagina_actual()

    compact_btn_style = ft.ButtonStyle(
        padding=ft.Padding.symmetric(horizontal=8, vertical=0),
        text_style=ft.TextStyle(size=11, weight=ft.FontWeight.W_600),
    )

    btn_tema = ft.IconButton(
        icon=ft.Icons.DARK_MODE_OUTLINED,
        icon_color="#0F172A",
        icon_size=19,
        width=32,
        height=32,
        padding=0,
        tooltip="Cambiar tema Claro / Oscuro",
        on_click=alternar_tema,
    )

    # =========================================================================
    # BARRA SUPERIOR DE ACCIONES Y PANEL COLAPSABLE ANIMADO
    # =========================================================================
    btn_editar_tasas = ft.FilledTonalButton(
        content="Tasa / 1100",
        icon=ft.Icons.CURRENCY_EXCHANGE_ROUNDED,
        height=32,
        style=compact_btn_style,
        tooltip="Editar Tasa Dólar BCV y Multiplicador 1100",
        on_click=abrir_modal_tasas,
    )

    btn_importar = ft.FilledTonalButton(
        content="Importar",
        icon=ft.Icons.UPLOAD_FILE_ROUNDED,
        height=32,
        style=compact_btn_style,
        on_click=abrir_modal_importar,
    )

    btn_exportar = ft.FilledTonalButton(
        content="PDF / Imprimir",
        icon=ft.Icons.PRINT_ROUNDED,
        height=32,
        style=compact_btn_style,
        on_click=abrir_modal_exportacion,
    )

    btn_nuevo = ft.FilledButton(
        content="Nuevo",
        icon=ft.Icons.ADD_ROUNDED,
        bgcolor="#0284C7",
        color=ft.Colors.WHITE,
        height=32,
        style=compact_btn_style,
        on_click=abrir_modal_nuevo_producto,
    )

    barra_superior = ft.Row(
        controls=[
            ft.Row(controls=[icono_app, txt_titulo_app], spacing=6),
            ft.Row(
                controls=[btn_tema, btn_editar_tasas, btn_importar, btn_exportar, btn_nuevo],
                spacing=6,
                run_spacing=6,
                wrap=True,
            ),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        wrap=True,
    )

    panel_superior_colapsable = ft.Container(
        content=ft.Column(
            controls=[barra_superior, card_tasa_dolar, barra_kpis],
            spacing=6,
            tight=True,
        ),
        opacity=1.0,
        animate_size=ft.Animation(280, ft.AnimationCurve.EASE_OUT_CUBIC),
        animate_opacity=ft.Animation(220, ft.AnimationCurve.EASE_IN_OUT),
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )

    # =========================================================================
    # BARRA DE NAVEGACIÓN INFERIOR (NAVBAR MATERIAL 3)
    # =========================================================================
    def on_nav_change(e):
        idx = getattr(e.control, "selected_index", 0)
        if idx == 0:
            if not (estado["filtro_texto"] or "").strip():
                aplicar_modo_compacto(False, actualizar_ui=False)
            cambiar_filtro_categoria("todos")
        elif idx == 1:
            cambiar_filtro_categoria("stock")
        elif idx == 2:
            barra_navegacion.selected_index = 1 if estado["categoria_filtro"] == "stock" else 0
            page.update()
            abrir_modal_nuevo_producto()
        elif idx == 3:
            barra_navegacion.selected_index = 1 if estado["categoria_filtro"] == "stock" else 0
            page.update()
            abrir_modal_tasas()
        elif idx == 4:
            barra_navegacion.selected_index = 1 if estado["categoria_filtro"] == "stock" else 0
            page.update()
            abrir_modal_exportacion()

    barra_navegacion = ft.NavigationBar(
        selected_index=0,
        bgcolor=ft.Colors.WHITE,
        indicator_color="#E0F2FE",
        height=62,
        animation_duration=300,
        destinations=[
            ft.NavigationBarDestination(
                icon=ft.Icons.INVENTORY_2_OUTLINED,
                selected_icon=ft.Icons.INVENTORY_2_ROUNDED,
                label="Inventario",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
                selected_icon=ft.Icons.CHECK_CIRCLE_ROUNDED,
                label="Con Stock",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.ADD_CIRCLE_OUTLINE_ROUNDED,
                selected_icon=ft.Icons.ADD_CIRCLE_ROUNDED,
                label="Nuevo",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.CURRENCY_EXCHANGE_ROUNDED,
                label="Tasa / 1100",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.PRINT_OUTLINED,
                selected_icon=ft.Icons.PRINT_ROUNDED,
                label="Imprimir",
            ),
        ],
        on_change=on_nav_change,
    )
    page.navigation_bar = barra_navegacion

    # =========================================================================
    # ENSAMBLAJE DE LA VISTA PRINCIPAL CON SAFEAREA (EVITA SOLAPAMIENTO CON STATUS BAR)
    # =========================================================================
    contenido_principal = ft.Column(
        controls=[
            panel_superior_colapsable,
            fila_busqueda,
            fila_filtros,
            lista_cards_container,
            barra_paginacion,
        ],
        spacing=6,
        expand=True,
    )
    page.add(ft.SafeArea(content=contenido_principal, expand=True))

    # Carga inicial inmediata (100% offline desde SQLite en 0ms)
    recargar_datos_y_renderizar()


if __name__ == "__main__":
    ft.run(main)
