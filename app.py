import streamlit as st
 
st.set_page_config(
    page_title="Carta Gantt Inteligente",
    page_icon="📊",
    layout="wide"
)
 
# ── Estilos globales ──────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
 
html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
}
 
/* Fondo oscuro con textura */
.stApp {
    background: linear-gradient(135deg, #0a0f1e 0%, #0d1b2a 50%, #0a0f1e 100%);
    min-height: 100vh;
}
 
/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1b2a 0%, #111827 100%);
    border-right: 1px solid #1e3a5f;
}
 
section[data-testid="stSidebar"] .stRadio label {
    color: #94a3b8 !important;
    font-size: 0.9rem;
    padding: 6px 0;
    cursor: pointer;
    transition: color 0.2s;
}
 
section[data-testid="stSidebar"] .stRadio label:hover {
    color: #38bdf8 !important;
}
 
/* Títulos */
h1, h2, h3 {
    color: #f0f9ff !important;
    font-weight: 700 !important;
}
 
/* Texto general */
p, li, .stMarkdown {
    color: #cbd5e1 !important;
}
 
/* Cards */
.card {
    background: rgba(30, 58, 95, 0.3);
    border: 1px solid rgba(56, 189, 248, 0.2);
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    backdrop-filter: blur(10px);
}
 
/* Botones primarios */
.stButton > button {
    background: linear-gradient(135deg, #0ea5e9, #6366f1);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 0.6rem 1.5rem;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 600;
    font-size: 0.9rem;
    transition: all 0.3s ease;
    box-shadow: 0 4px 15px rgba(14, 165, 233, 0.3);
}
 
.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(14, 165, 233, 0.5);
}
 
/* Inputs */
.stTextInput input, .stNumberInput input, .stSelectbox select, .stDateInput input {
    background: rgba(15, 30, 50, 0.8) !important;
    border: 1px solid #1e3a5f !important;
    border-radius: 8px !important;
    color: #e2e8f0 !important;
}
 
/* Métricas */
[data-testid="metric-container"] {
    background: rgba(30, 58, 95, 0.3);
    border: 1px solid rgba(56, 189, 248, 0.15);
    border-radius: 10px;
    padding: 1rem;
}
 
[data-testid="stMetricValue"] {
    color: #38bdf8 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 1.8rem !important;
}
 
[data-testid="stMetricLabel"] {
    color: #94a3b8 !important;
}
 
/* DataFrames */
.stDataFrame {
    border: 1px solid #1e3a5f !important;
    border-radius: 8px;
}
 
/* Alertas info */
.stAlert {
    background: rgba(14, 165, 233, 0.1) !important;
    border: 1px solid rgba(14, 165, 233, 0.3) !important;
    border-radius: 8px !important;
    color: #bae6fd !important;
}
 
/* Separador */
hr {
    border-color: #1e3a5f !important;
}
 
/* Logo sidebar */
.sidebar-logo {
    font-family: 'JetBrains Mono', monospace;
    color: #38bdf8;
    font-size: 1.1rem;
    font-weight: 600;
    padding: 1rem 0;
    letter-spacing: -0.5px;
}
 
/* Tag estado */
.tag {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.5px;
}
.tag-ok     { background: rgba(34,197,94,0.15); color: #4ade80; border: 1px solid #4ade8040; }
.tag-warn   { background: rgba(250,204,21,0.15); color: #facc15; border: 1px solid #facc1540; }
.tag-danger { background: rgba(239,68,68,0.15);  color: #f87171; border: 1px solid #f8717140; }
.tag-idle   { background: rgba(148,163,184,0.15);color: #94a3b8; border: 1px solid #94a3b840; }
</style>
""", unsafe_allow_html=True)
 
# ── Estado global ─────────────────────────────────────────────────────────────
if "proyectos" not in st.session_state:
    st.session_state.proyectos = {}   # { nombre: {info, tareas} }
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
 
    # Selector de proyecto activo
    proyectos_lista = list(st.session_state.proyectos.keys())
    if proyectos_lista:
        st.markdown("---")
        st.markdown("**Proyecto activo**")
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
 