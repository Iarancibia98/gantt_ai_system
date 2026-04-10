import streamlit as st
from data import cargar_demo, importar_csv
from styles import aplicar_estilos, CSS

st.set_page_config(
    page_title="Carta Gantt Inteligente",
    page_icon="📊",
    layout="wide"
)

# ── Estilos globales ──────────────────────────────────────────────────────────
aplicar_estilos()

# ── Estado global ─────────────────────────────────────────────────────────────
if "proyectos" not in st.session_state:
    st.session_state.proyectos = {}
if "proyecto_activo" not in st.session_state:
    st.session_state.proyecto_activo = None

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-logo">📊 GanttAI</div>', unsafe_allow_html=True)
    st.markdown("---")

    pagina = st.radio("Navegación", [
        "🏠 Inicio",
        "➕ Nuevo Proyecto",
        "📅 Ver Gantt",
        "📊 Dashboard",
        "🧠 Análisis IA",
    ], label_visibility="collapsed")

    # ── Cargar proyecto demo ──────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        "<span class='demo-badge'>Demo</span> "
        "<span style='color:#E2E8F0;font-size:0.85rem;font-weight:600;"
        "margin-left:6px;'>Proyectos de ejemplo</span>",
        unsafe_allow_html=True
    )
    st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)

    DEMOS = {
        "Demo Minería":  ("demo_mineria",  "Optimización Operacional Mina Subterránea Norte", "Carlos Romero",    "Operaciones",        "01/04/2026", "30/06/2026", "Alta",  "Mejora del ciclo de extracción y modernización SCADA."),
        "Demo Retail":   ("demo_retail",   "Renovación Temporada Invierno 2026",               "Valentina Torres", "Comercial / Ventas", "05/04/2026", "30/04/2026", "Media", "Reconfiguración de tiendas y lanzamiento campaña invierno."),
        "Demo Salud":    ("demo_medicina", "Digitalización Clínica y Acreditación 2026",       "Dra. Paula Soto",  "Salud / Medicina",   "01/04/2026", "30/06/2026", "Alta",  "Implementación HIS y preparación acreditación Joint Commission."),
    }

    demo_opcion = st.selectbox(
        "demo",
        ["— Selecciona —"] + list(DEMOS.keys()),
        key="demo_selector",
        label_visibility="collapsed"
    )

    if st.button("⚡ Cargar demo", use_container_width=True):
        if demo_opcion == "— Selecciona —":
            st.warning("Selecciona un demo primero.")
        else:
            archivo_csv, nombre_proy, responsable, area, fi, ff, prioridad, desc = DEMOS[demo_opcion]

            from datetime import datetime
            import io

            fi_date = datetime.strptime(fi, "%d/%m/%Y").date()
            ff_date = datetime.strptime(ff, "%d/%m/%Y").date()

            df  = cargar_demo(archivo_csv)
            raw = io.BytesIO(df.to_csv(index=False).encode("utf-8"))
            tareas, errores = importar_csv(raw)

            if tareas:
                # 🔥 Cambio: ahora SIEMPRE sobreescribe (permite recargar limpio)
                st.session_state.proyectos[nombre_proy] = {
                    "info": {
                        "nombre":       nombre_proy,
                        "responsable":  responsable,
                        "area":         area,
                        "fecha_inicio": fi_date,
                        "fecha_fin":    ff_date,
                        "prioridad":    prioridad,
                        "descripcion":  desc,
                    },
                    "tareas": tareas,
                }

                st.session_state.proyecto_activo = nombre_proy

                st.success(f"✅ {demo_opcion} cargado.")
                st.toast(f"{demo_opcion} listo 🚀", icon="✅")
                st.rerun()
            else:
                st.error("Error al cargar el demo.")
                for e in errores:
                    st.warning(e)

    # ── Selector de proyecto activo ───────────────────────────────────────────
    proyectos_lista = list(st.session_state.proyectos.keys())
    if proyectos_lista:
        st.markdown("---")
        st.markdown(
            "<span style='color:#A0AEC0;font-size:0.75rem;text-transform:uppercase;"
            "letter-spacing:0.5px;'>Proyecto activo</span>",
            unsafe_allow_html=True
        )

        seleccion = st.selectbox(
            "proyecto",
            proyectos_lista,
            index=proyectos_lista.index(st.session_state.proyecto_activo)
                  if st.session_state.proyecto_activo in proyectos_lista else 0,
            label_visibility="collapsed"
        )

        st.session_state.proyecto_activo = seleccion

    st.markdown("---")
    st.caption("v1.0 · Carta Gantt Inteligente")
    st.markdown(
        "<div style='color:#718096;font-size:0.72rem;padding:4px 0;'>"
        "by Iván Arancibia Bruna · "
        "<a href='https://www.linkedin.com/in/ivan-arancibia-bruna/' target='_blank' "
        "style='color:#718096;text-decoration:underline;'>LinkedIn ↗</a>"
        "</div>",
        unsafe_allow_html=True
    )

# ── Enrutador de páginas ──────────────────────────────────────────────────────
if pagina == "🏠 Inicio":
    from data import pagina_inicio
    pagina_inicio()

elif pagina == "➕ Nuevo Proyecto":
    from data import pagina_nuevo_proyecto
    pagina_nuevo_proyecto()

elif pagina == "📅 Ver Gantt":
    from gantt import pagina_gantt
    pagina_gantt()

elif pagina == "📊 Dashboard":
    from dashboard import pagina_dashboard
    pagina_dashboard()

elif pagina == "🧠 Análisis IA":
    from storytelling import pagina_storytelling
    pagina_storytelling()