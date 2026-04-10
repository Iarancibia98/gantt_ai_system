"""
styles.py — Módulo de estilos compartidos para GanttAI
Paleta inspirada en CoreUI / Azia: sidebar oscuro, fondo blanco, cards coloridas.
Uso:
    from styles import aplicar_estilos, COLORES, PLOTLY_LAYOUT, COLORES_ESTADO, COLORES_ESTADO_EXT
"""

import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# TOKENS DE COLOR
# ─────────────────────────────────────────────────────────────────────────────
COLORES = {
    # Primarios
    "primary":        "#6F42C1",   # púrpura Azia
    "primary_light":  "#8B5CF6",
    "secondary":      "#007BFF",   # azul eléctrico
    "secondary_light":"#38BDF8",

    # Supporting
    "teal":           "#00CCCC",
    "aqua":           "#0DCAF0",
    "steel":          "#17A2B8",

    # Semánticos
    "success":        "#28A745",
    "warning":        "#FFC107",
    "danger":         "#DC3545",
    "info":           "#17A2B8",

    # Neutros
    "text_primary":   "#212529",
    "text_secondary": "#6C757D",
    "border":         "#E9ECEF",
    "bg_page":        "#F4F6F9",
    "bg_card":        "#FFFFFF",
    "bg_sidebar":     "#2D3748",
    "bg_sidebar_dark":"#1A202C",
}

# ─────────────────────────────────────────────────────────────────────────────
# COLORES DE ESTADO (para Gantt y Dashboard)
# ─────────────────────────────────────────────────────────────────────────────
COLORES_ESTADO = {
    "Completada":  COLORES["success"],   # #28A745
    "En Progreso": COLORES["secondary"], # #007BFF
    "En Riesgo":   COLORES["warning"],   # #FFC107  ← agregar esta línea
    "Atrasada":    COLORES["danger"],    # #DC3545
    "Pendiente":   COLORES["text_secondary"], # #6C757D
}

COLORES_ESTADO_EXT = {
    **COLORES_ESTADO,
    "En Riesgo":   COLORES["warning"],
}

# ─────────────────────────────────────────────────────────────────────────────
# PLOTLY LAYOUT BASE (tema claro Azia)
# ─────────────────────────────────────────────────────────────────────────────
PLOTLY_LAYOUT = dict(
    plot_bgcolor  = "#FFFFFF",
    paper_bgcolor = "#FFFFFF",
    font          = dict(color=COLORES["text_secondary"], family="DM Sans, sans-serif", size=12),
    margin        = dict(l=20, r=20, t=45, b=20),
    hoverlabel    = dict(
        bgcolor    = "#FFFFFF",
        bordercolor= COLORES["primary"],
        font_color = COLORES["text_primary"],
        font_size  = 12,
    ),
    xaxis = dict(
        gridcolor   = COLORES["border"],
        linecolor   = COLORES["border"],
        tickfont    = dict(color=COLORES["text_secondary"], size=11),
        title_font  = dict(color=COLORES["text_secondary"]),
    ),
    yaxis = dict(
        gridcolor   = COLORES["border"],
        linecolor   = COLORES["border"],
        tickfont    = dict(color=COLORES["text_secondary"], size=11),
    ),
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS GLOBAL
# ─────────────────────────────────────────────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

/* ── Reset base ─────────────────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 14px;
}

/* ── Fondo página ───────────────────────────────────────────────────── */
.stApp {
    background: #F4F6F9 !important;
}

/* ── Sidebar oscuro estilo CoreUI ───────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #2D3748 0%, #1A202C 100%) !important;
    border-right: none !important;
}

section[data-testid="stSidebar"] * {
    color: #A0AEC0 !important;
}

section[data-testid="stSidebar"] .stRadio label {
    color: #A0AEC0 !important;
    font-size: 0.875rem !important;
    padding: 8px 12px !important;
    border-radius: 6px;
    transition: all 0.2s;
    display: block;
}

section[data-testid="stSidebar"] .stRadio label:hover {
    color: #FFFFFF !important;
    background: rgba(111,66,193,0.2) !important;
}

section[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.1) !important;
}

section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stMarkdown p {
    color: #A0AEC0 !important;
    font-size: 0.8rem !important;
}

/* ── Títulos ────────────────────────────────────────────────────────── */
h1, h2, h3, h4, h5 {
    font-family: 'DM Sans', sans-serif !important;
    color: #212529 !important;
    font-weight: 700 !important;
    letter-spacing: -0.3px;
}

h1 { font-size: 1.6rem !important; }
h2 { font-size: 1.3rem !important; }
h3 { font-size: 1.1rem !important; }

/* ── Texto ──────────────────────────────────────────────────────────── */
p, li, .stMarkdown {
    color: #6C757D !important;
    font-size: 0.875rem !important;
}

/* ── Cards ──────────────────────────────────────────────────────────── */
.card {
    background: #FFFFFF;
    border: 1px solid #E9ECEF;
    border-radius: 10px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

/* ── KPI Cards coloridas estilo CoreUI ──────────────────────────────── */
.kpi-card {
    border-radius: 10px;
    padding: 1.25rem 1.5rem;
    color: white !important;
    position: relative;
    overflow: hidden;
    box-shadow: 0 4px 15px rgba(0,0,0,0.12);
}
.kpi-card::after {
    content: '';
    position: absolute;
    right: -10px; bottom: -10px;
    width: 80px; height: 80px;
    border-radius: 50%;
    background: rgba(255,255,255,0.1);
}
.kpi-purple  { background: linear-gradient(135deg, #6F42C1, #8B5CF6); }
.kpi-blue    { background: linear-gradient(135deg, #007BFF, #38BDF8); }
.kpi-teal    { background: linear-gradient(135deg, #00CCCC, #0DCAF0); }
.kpi-green   { background: linear-gradient(135deg, #28A745, #20C997); }
.kpi-orange  { background: linear-gradient(135deg, #FD7E14, #FFC107); }
.kpi-red     { background: linear-gradient(135deg, #DC3545, #F87171); }
.kpi-yellow  { background: linear-gradient(135deg, #D39E00, #FFC107); }
.kpi-value   { font-size: 2rem; font-weight: 700; font-family: 'DM Mono', monospace; line-height: 1; }
.kpi-label   { font-size: 0.8rem; opacity: 0.85; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px; }

/* ── Métricas Streamlit ─────────────────────────────────────────────── */
[data-testid="metric-container"] {
    background: #FFFFFF !important;
    border: 1px solid #E9ECEF !important;
    border-radius: 10px !important;
    padding: 1rem 1.25rem !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06) !important;
}

[data-testid="stMetricValue"] {
    color: #6F42C1 !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 1.6rem !important;
    font-weight: 600 !important;
}

[data-testid="stMetricLabel"] {
    color: #6C757D !important;
    font-size: 0.75rem !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* ── Botones ────────────────────────────────────────────────────────── */
.stButton > button {
    background: linear-gradient(135deg, #6F42C1, #007BFF) !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 7px !important;
    padding: 0.5rem 1.25rem !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.875rem !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 2px 8px rgba(111,66,193,0.25) !important;
    text-shadow: 0 1px 2px rgba(0,0,0,0.4) !important;
    letter-spacing: 0.2px !important;
}

.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 5px 15px rgba(111,66,193,0.4) !important;
}
.stButton > button p {
    color: #FFFFFF !important;
    font-weight: 700 !important;
}

/* ── Inputs ─────────────────────────────────────────────────────────── */
.stTextInput input,
.stNumberInput input,
.stDateInput input,
.stTextArea textarea {
    background: #FFFFFF !important;
    border: 1px solid #E9ECEF !important;
    border-radius: 7px !important;
    color: #212529 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.875rem !important;
    transition: border-color 0.2s !important;
}

.stTextInput input:focus,
.stDateInput input:focus {
    border-color: #6F42C1 !important;
    box-shadow: 0 0 0 3px rgba(111,66,193,0.1) !important;
}

/* ── Selectbox ──────────────────────────────────────────────────────── */
.stSelectbox > div > div {
    background: #FFFFFF !important;
    border: 1px solid #E9ECEF !important;
    border-radius: 7px !important;
    color: #212529 !important;
}

/* ── Multiselect tags ───────────────────────────────────────────────── */
span[data-baseweb="tag"] {
    background: rgba(111,66,193,0.1) !important;
    color: #6F42C1 !important;
    border: 1px solid rgba(111,66,193,0.25) !important;
    border-radius: 20px !important;
}

/* ── Slider ─────────────────────────────────────────────────────────── */
[data-testid="stSlider"] [role="slider"] {
    background: #6F42C1 !important;
    border-color: #6F42C1 !important;
}

/* ── Progress bar ───────────────────────────────────────────────────── */
.stProgress > div > div > div > div {
    background: linear-gradient(90deg, #6F42C1, #007BFF) !important;
    border-radius: 4px !important;
}

/* ── DataFrames ─────────────────────────────────────────────────────── */
.stDataFrame {
    border: 1px solid #E9ECEF !important;
    border-radius: 10px !important;
    overflow: hidden !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06) !important;
}

/* ── Expanders ──────────────────────────────────────────────────────── */
details {
    background: #FFFFFF !important;
    border: 1px solid #E9ECEF !important;
    border-radius: 10px !important;
    overflow: hidden;
}

details summary {
    color: #212529 !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    padding: 0.75rem 1rem !important;
}

/* ── Alertas ────────────────────────────────────────────────────────── */
[data-testid="stAlert"] {
    border-radius: 8px !important;
    font-size: 0.875rem !important;
}

/* ── Separador ──────────────────────────────────────────────────────── */
hr {
    border: none !important;
    border-top: 1px solid #E9ECEF !important;
    margin: 1.25rem 0 !important;
}

/* ── Caption ────────────────────────────────────────────────────────── */
.stCaption, small {
    color: #ADB5BD !important;
    font-size: 0.78rem !important;
}

/* ── Sidebar logo ───────────────────────────────────────────────────── */
.sidebar-logo {
    font-family: 'DM Sans', sans-serif;
    color: #FFFFFF !important;
    font-size: 1.2rem;
    font-weight: 700;
    padding: 0.5rem 0 1rem 0;
    letter-spacing: -0.5px;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* ── Sidebar demo badge ─────────────────────────────────────────────── */
.demo-badge {
    display: inline-block;
    background: linear-gradient(135deg, #6F42C1, #007BFF);
    color: white !important;
    font-size: 0.7rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 20px;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}

/* ── Tags de estado ─────────────────────────────────────────────────── */
.tag {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.4px;
}
.tag-ok     { background: rgba(40,167,69,0.1);   color: #28A745; border: 1px solid rgba(40,167,69,0.2);   }
.tag-warn   { background: rgba(255,193,7,0.12);  color: #D39E00; border: 1px solid rgba(255,193,7,0.25);  }
.tag-danger { background: rgba(220,53,69,0.1);   color: #DC3545; border: 1px solid rgba(220,53,69,0.2);   }
.tag-risk   { background: rgba(253,126,20,0.1);  color: #FD7E14; border: 1px solid rgba(253,126,20,0.2);  }
.tag-idle   { background: rgba(108,117,125,0.1); color: #6C757D; border: 1px solid rgba(108,117,125,0.2); }

/* ── Scrollbar ──────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #F4F6F9; }
::-webkit-scrollbar-thumb { background: #CBD5E0; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #6F42C1; }
</style>
"""


def aplicar_estilos():
    """Llama esta función al inicio de cada página para aplicar los estilos."""
    st.markdown(CSS, unsafe_allow_html=True)


def kpi_card(valor, label, variante="kpi-purple", icono="📊"):
    """
    Renderiza una KPI card colorida estilo CoreUI.
    variante: kpi-purple | kpi-blue | kpi-teal | kpi-green | kpi-orange | kpi-red
    """
    return f"""
    <div class="kpi-card {variante}">
        <div style="font-size:1.5rem; margin-bottom:6px;">{icono}</div>
        <div class="kpi-value">{valor}</div>
        <div class="kpi-label">{label}</div>
    </div>
    """