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
if "demo_cargado" not in st.session_state:
    st.session_state.demo_cargado = False
 
# ── Auto-carga demo minería en primera visita ─────────────────────────────────
DEMO_MINERIA = {
    "archivo":      "demo_mineria",
    "nombre":       "Optimización Operacional Mina Subterránea Norte",
    "responsable":  "Carlos Romero",
    "area":         "Operaciones",
    "fecha_inicio": "01/04/2026",
    "fecha_fin":    "30/06/2026",
    "prioridad":    "Alta",
    "descripcion":  "Mejora del ciclo de extracción y modernización SCADA.",
}
 
if not st.session_state.proyectos and not st.session_state.demo_cargado:
    from datetime import datetime
    import io
 
    fi_date = datetime.strptime(DEMO_MINERIA["fecha_inicio"], "%d/%m/%Y").date()
    ff_date = datetime.strptime(DEMO_MINERIA["fecha_fin"],    "%d/%m/%Y").date()
 
    df  = cargar_demo(DEMO_MINERIA["archivo"])
    raw = io.BytesIO(df.to_csv(index=False).encode("utf-8"))
    tareas, _ = importar_csv(raw)
 
    if tareas:
        nombre_proy = DEMO_MINERIA["nombre"]
        st.session_state.proyectos[nombre_proy] = {
            "info": {
                "nombre":       nombre_proy,
                "responsable":  DEMO_MINERIA["responsable"],
                "area":         DEMO_MINERIA["area"],
                "fecha_inicio": fi_date,
                "fecha_fin":    ff_date,
                "prioridad":    DEMO_MINERIA["prioridad"],
                "descripcion":  DEMO_MINERIA["descripcion"],
            },
            "tareas": tareas,
        }
        st.session_state.proyecto_activo = nombre_proy
        st.session_state.demo_cargado    = True
 
# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-logo">📊 GanttAI</div>', unsafe_allow_html=True)
    st.markdown("---")
 
    # #7 — ocultar "Nuevo Proyecto" mientras el demo esté activo
    opciones_nav = ["🏠 Inicio", "📅 Ver Gantt", "📊 Dashboard", "🧠 Análisis IA"]
    if not st.session_state.demo_cargado:
        opciones_nav.insert(1, "➕ Nuevo Proyecto")
 
    pagina = st.radio("Navegación", opciones_nav, label_visibility="collapsed")
 
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
 
    # #8 — minería pre-seleccionada por defecto, sin opción vacía
    demo_opcion = st.selectbox(
        "demo",
        list(DEMOS.keys()),
        index=0,
        key="demo_selector",
        label_visibility="collapsed"
    )
 
    if st.button("⚡ Cargar demo", use_container_width=True):
        archivo_csv, nombre_proy, responsable, area, fi, ff, prioridad, desc = DEMOS[demo_opcion]
 
        from datetime import datetime
        import io
 
        fi_date = datetime.strptime(fi, "%d/%m/%Y").date()
        ff_date = datetime.strptime(ff, "%d/%m/%Y").date()
 
        df  = cargar_demo(archivo_csv)
        raw = io.BytesIO(df.to_csv(index=False).encode("utf-8"))
        tareas, errores = importar_csv(raw)
 
        if tareas:
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
            st.session_state.demo_cargado    = True
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
 
# ── Banner demo (visible en todas las páginas mientras sea demo activo) ────────
if st.session_state.demo_cargado:
    proyecto_activo = st.session_state.get("proyecto_activo", "")
    nombre_demo_mineria = DEMO_MINERIA["nombre"]
    if proyecto_activo == nombre_demo_mineria:
        st.markdown(
            """
            <div style="
                background: linear-gradient(90deg, rgba(56,189,248,0.08), rgba(56,189,248,0.03));
                border: 1px solid rgba(56,189,248,0.25);
                border-radius: 8px;
                padding: 0.65rem 1.1rem;
                margin-bottom: 1rem;
                display: flex;
                align-items: center;
                gap: 0.6rem;
            ">
                <span style="font-size:1.1rem;">⛏️</span>
                <span style="color:#7dd3fc; font-size:0.85rem;">
                    <strong style="color:#38bdf8;">Modo demo activo</strong>
                    — Estás viendo un proyecto minero realista con análisis automático de IA.
                    Puedes interactuar con todos los módulos.
                </span>
            </div>
            """,
            unsafe_allow_html=True,
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
 