import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import date
from data import get_proyecto, calcular_estado_tarea, calcular_duracion, avance_total_proyecto


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS DE GRÁFICOS
# ─────────────────────────────────────────────────────────────────────────────
PLOTLY_LAYOUT = dict(
    plot_bgcolor="#0a0f1e",
    paper_bgcolor="#0a0f1e",
    font=dict(color="#94a3b8", family="Space Grotesk"),
    margin=dict(l=20, r=20, t=40, b=20),
)

# ── Fix Bug 1: solo 4 estados reales ─────────────────────────────────────────
COLORES_ESTADO = {
    "Completada":  "#4ade80",
    "En Progreso": "#38bdf8",
    "Atrasada":    "#f87171",
    "Pendiente":   "#64748b",
}


def _calcular_estado_riesgo(t: dict, hoy: date) -> str:
    """
    Extiende calcular_estado_tarea con un estado 'En Riesgo':
    tarea En Progreso cuyo avance real < avance esperado por tiempo transcurrido.
    """
    estado = calcular_estado_tarea(t, hoy)
    if estado != "En Progreso":
        return estado

    try:
        duracion     = (t["fecha_fin"] - t["fecha_inicio"]).days or 1
        transcurrido = (hoy - t["fecha_inicio"]).days
        esperado     = round((transcurrido / duracion) * 100)
        real         = t.get("avance", 0)
        # En riesgo si avance real está 20+ puntos por debajo del esperado
        if real < esperado - 20:
            return "En Riesgo"
    except Exception:
        pass

    return estado


COLORES_ESTADO_EXT = {
    **COLORES_ESTADO,
    "En Riesgo": "#fb923c",
}


def gauge_avance(avance: float) -> go.Figure:
    color = "#4ade80" if avance >= 80 else "#facc15" if avance >= 40 else "#f87171"
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=avance,
        number={"suffix": "%", "font": {"color": color, "size": 36, "family": "JetBrains Mono"}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#334155",
                     "tickfont": {"color": "#64748b"}},
            "bar": {"color": color, "thickness": 0.25},
            "bgcolor": "#1e3a5f",
            "borderwidth": 0,
            "steps": [
                {"range": [0,  33], "color": "rgba(248,113,113,0.1)"},
                {"range": [33, 66], "color": "rgba(250,204,21,0.1)"},
                {"range": [66,100], "color": "rgba(74,222,128,0.1)"},
            ],
        },
        title={"text": "Avance total", "font": {"color": "#94a3b8", "size": 14}},
    ))
    fig.update_layout(**PLOTLY_LAYOUT, height=220)
    return fig


def pie_estados(conteo: dict) -> go.Figure:
    labels = list(conteo.keys())
    values = list(conteo.values())
    colors = [COLORES_ESTADO_EXT.get(l, "#94a3b8") for l in labels]

    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=0.55,
        marker=dict(colors=colors, line=dict(color="#0a0f1e", width=2)),
        textfont=dict(color="white", size=12),
        hovertemplate="%{label}: %{value} tarea(s)<extra></extra>",
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT, height=260,
        title=dict(text="Distribución de estados",
                   font=dict(color="#f0f9ff", size=14))
    )
    return fig


def bar_avance_por_tarea(tareas: list) -> go.Figure:
    hoy = date.today()
    nombres = [t["nombre"][:25] + "…" if len(t["nombre"]) > 25
               else t["nombre"] for t in tareas]
    avances = [t.get("avance", 0) for t in tareas]
    colores = [COLORES_ESTADO_EXT.get(
        _calcular_estado_riesgo(t, hoy), "#94a3b8") for t in tareas]

    fig = go.Figure(go.Bar(
        x=avances, y=nombres, orientation="h",
        marker=dict(color=colores, opacity=0.85),
        text=[f"{a}%" for a in avances],
        textposition="inside",
        textfont=dict(color="white", size=11),
        hovertemplate="%{y}: %{x}%<extra></extra>",
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=max(250, 40 * len(tareas) + 60),
        xaxis=dict(range=[0, 100], title="% Avance",
                   gridcolor="#1e3a5f", tickfont=dict(color="#64748b")),
        yaxis=dict(tickfont=dict(color="#e2e8f0")),
        title=dict(text="Avance por tarea",
                   font=dict(color="#f0f9ff", size=14)),
    )
    return fig


def bar_por_area(tareas: list) -> go.Figure:
    df = pd.DataFrame([{
        "area":   t.get("area", "Otro"),
        "avance": t.get("avance", 0),
    } for t in tareas])

    df_grp = df.groupby("area")["avance"].mean().reset_index()
    df_grp.columns = ["Área", "Avance promedio"]
    df_grp = df_grp.sort_values("Avance promedio", ascending=True)

    fig = go.Figure(go.Bar(
        x=df_grp["Avance promedio"],
        y=df_grp["Área"],
        orientation="h",
        marker=dict(
            color=df_grp["Avance promedio"],
            colorscale=[[0, "#f87171"], [0.5, "#facc15"], [1, "#4ade80"]],
            showscale=False,
        ),
        text=[f"{v:.0f}%" for v in df_grp["Avance promedio"]],
        textposition="inside",
        textfont=dict(color="white"),
        hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=max(200, 50 * len(df_grp) + 60),
        xaxis=dict(range=[0, 100], title="Avance promedio (%)",
                   gridcolor="#1e3a5f", tickfont=dict(color="#64748b")),
        yaxis=dict(tickfont=dict(color="#e2e8f0")),
        title=dict(text="Avance promedio por área",
                   font=dict(color="#f0f9ff", size=14)),
    )
    return fig


def timeline_carga_recursos(tareas: list) -> go.Figure:
    df_rows = []
    for t in tareas:
        recurso = t.get("recurso") or "Sin asignar"
        dias    = calcular_duracion(t)
        df_rows.append({"Recurso": recurso, "Días": dias, "Tarea": t["nombre"]})

    df     = pd.DataFrame(df_rows)
    df_grp = (df.groupby("Recurso")["Días"].sum()
               .reset_index()
               .sort_values("Días", ascending=True))

    fig = go.Figure(go.Bar(
        x=df_grp["Días"],
        y=df_grp["Recurso"],
        orientation="h",
        marker=dict(
            color=df_grp["Días"],
            colorscale=[[0, "#1e3a5f"], [1, "#38bdf8"]],
            showscale=False,
        ),
        text=df_grp["Días"].astype(str) + " días",
        textposition="inside",
        textfont=dict(color="white"),
        hovertemplate="%{y}: %{x} días asignados<extra></extra>",
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=max(200, 45 * len(df_grp) + 60),
        xaxis=dict(title="Días totales asignados",
                   gridcolor="#1e3a5f", tickfont=dict(color="#64748b")),
        yaxis=dict(tickfont=dict(color="#e2e8f0")),
        title=dict(text="Carga por recurso (días)",
                   font=dict(color="#f0f9ff", size=14)),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
def pagina_dashboard():
    st.markdown("## 📊 Dashboard del Proyecto")

    proyecto = get_proyecto()
    if not proyecto:
        st.markdown("""
<div class="card" style="text-align:center; padding: 2.5rem;">
<div style="font-size:3rem; margin-bottom:1rem;">📊</div>
<h3 style="color:#f0f9ff !important;">No hay proyecto seleccionado</h3>
<p style="color:#94a3b8;">El dashboard mostrará los KPIs una vez que selecciones un proyecto.</p>
<br>
<p style="color:#64748b; font-size:0.85rem;">
  1. Ve a <strong style="color:#38bdf8;">➕ Nuevo Proyecto</strong> para crear uno.<br>
  2. O selecciona un proyecto existente desde el <strong style="color:#38bdf8;">menú lateral</strong>.
</p>
</div>
""", unsafe_allow_html=True)
        return

    info   = proyecto["info"]
    tareas = proyecto["tareas"]
    hoy    = date.today()

    if not tareas:
        st.markdown("""
<div class="card" style="text-align:center; padding: 2rem;">
<div style="font-size:2.5rem; margin-bottom:0.75rem;">📉</div>
<h4 style="color:#f0f9ff !important;">Sin tareas registradas</h4>
<p style="color:#94a3b8;">Agrega tareas al proyecto para ver los indicadores.</p>
</div>
""", unsafe_allow_html=True)
        return

    # ── KPIs: usar _calcular_estado_riesgo para detectar "En Riesgo" ─────────
    avance  = avance_total_proyecto(tareas)
    estados = {e: 0 for e in
               ["Completada", "En Progreso", "En Riesgo", "Atrasada", "Pendiente"]}
    for t in tareas:
        estados[_calcular_estado_riesgo(t, hoy)] += 1

    # ── Fix Bug 2: días restantes con manejo de negativos ─────────────────────
    if isinstance(info.get("fecha_fin"), date):
        dias_restantes = (info["fecha_fin"] - hoy).days
        if dias_restantes < 0:
            dias_label = f"⚠️ Vencido hace {abs(dias_restantes)}d"
        elif dias_restantes == 0:
            dias_label = "⚠️ Vence hoy"
        else:
            dias_label = f"{dias_restantes} días"
    else:
        dias_label = "—"

    salud = (
        "🟢 Saludable" if estados["Atrasada"] == 0 and estados["En Riesgo"] == 0 else
        "🟠 En riesgo"  if estados["Atrasada"] == 0 and estados["En Riesgo"] > 0  else
        "🟡 Riesgo"     if estados["Atrasada"] <= 2                                else
        "🔴 Crítico"
    )

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("📈 Avance total",  f"{avance}%")
    c2.metric("✅ Completadas",    estados["Completada"])
    c3.metric("🔄 En progreso",    estados["En Progreso"])
    c4.metric("🟠 En riesgo",      estados["En Riesgo"])
    c5.metric("⚠️ Atrasadas",      estados["Atrasada"])
    c6.metric("📅 Días restantes", dias_label, help=f"Hasta {info['fecha_fin'].strftime('%d/%m/%Y')}")

    st.markdown("---")

    col_prog, col_info = st.columns([3, 1])
    with col_prog:
        st.markdown(f"**Progreso del proyecto:** {avance}%")
        st.progress(avance / 100)
    with col_info:
        st.markdown(f"**Estado de salud:** {salud}")
        st.caption(f"Responsable: {info.get('responsable', '—')}")
        st.caption(f"Prioridad: {info.get('prioridad', '—')}")

    st.markdown("---")

    # ── Fila 1: Gauge + Pie ───────────────────────────────────────────────────
    col_g, col_p = st.columns(2)
    with col_g:
        st.plotly_chart(gauge_avance(avance), use_container_width=True)
    with col_p:
        estados_con_datos = {k: v for k, v in estados.items() if v > 0}
        st.plotly_chart(pie_estados(estados_con_datos), use_container_width=True)

    st.markdown("---")

    # ── Fila 2: Avance por tarea ──────────────────────────────────────────────
    st.plotly_chart(bar_avance_por_tarea(tareas), use_container_width=True)

    st.markdown("---")

    # ── Fila 3: Por área + Recursos ───────────────────────────────────────────
    # ── Fix Bug 3: siempre mostrar ambos gráficos ─────────────────────────────
    col_a, col_r = st.columns(2)
    with col_a:
        st.plotly_chart(bar_por_area(tareas), use_container_width=True)
    with col_r:
        st.plotly_chart(timeline_carga_recursos(tareas), use_container_width=True)

    st.markdown("---")

    # ── Tabla detalle ─────────────────────────────────────────────────────────
    st.markdown("### 📋 Detalle de tareas")

    df = pd.DataFrame([{
        "Tarea":    t["nombre"],
        "Recurso":  t.get("recurso", "—"),
        "Área":     t.get("area", "—"),
        "Inicio":   t["fecha_inicio"].strftime("%d/%m/%Y"),
        "Fin":      t["fecha_fin"].strftime("%d/%m/%Y"),
        "Duración": calcular_duracion(t),
        "Avance %": t.get("avance", 0),
        "Estado":   _calcular_estado_riesgo(t, hoy),  # usa estado extendido
    } for t in tareas])

    def color_estado(val):
        m = {
            "Completada":  "background-color:#052e1640;color:#4ade80",
            "En Progreso": "background-color:#0c283840;color:#38bdf8",
            "En Riesgo":   "background-color:#431a0040;color:#fb923c",
            "Atrasada":    "background-color:#2d0a0a40;color:#f87171",
            "Pendiente":   "background-color:#1e293b40;color:#94a3b8",
        }
        return m.get(val, "")

    st.dataframe(
        df.style.map(color_estado, subset=["Estado"]),
        use_container_width=True,
        hide_index=True
    )

    # ── Alertas atrasadas ─────────────────────────────────────────────────────
    atrasadas_lista = [t for t in tareas
                       if _calcular_estado_riesgo(t, hoy) == "Atrasada"]
    if atrasadas_lista:
        st.markdown("---")
        st.markdown("### 🚨 Alertas de atraso")
        for t in atrasadas_lista:
            dias_atras = (hoy - t["fecha_fin"]).days
            st.error(
                f"**{t['nombre']}** — atrasada {dias_atras} día(s) "
                f"| Avance: {t.get('avance', 0)}% "
                f"| Recurso: {t.get('recurso', '—')}"
            )

    # ── Alertas en riesgo ─────────────────────────────────────────────────────
    en_riesgo_lista = [t for t in tareas
                       if _calcular_estado_riesgo(t, hoy) == "En Riesgo"]
    if en_riesgo_lista:
        if not atrasadas_lista:
            st.markdown("---")
        st.markdown("### ⚠️ Tareas en riesgo de atraso")
        for t in en_riesgo_lista:
            duracion        = (t["fecha_fin"] - t["fecha_inicio"]).days or 1
            transcurrido    = (hoy - t["fecha_inicio"]).days
            avance_esperado = round((transcurrido / duracion) * 100)
            brecha          = avance_esperado - t.get("avance", 0)
            st.warning(
                f"**{t['nombre']}** — real: {t.get('avance', 0)}% "
                f"vs esperado: {avance_esperado}% "
                f"| Brecha: **{brecha} puntos** "
                f"| Recurso: {t.get('recurso', '—')} "
                f"| Fin: {t['fecha_fin'].strftime('%d/%m/%Y')}"
            )

    # ── Exportar ──────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📥 Exportar datos")
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Descargar tabla como CSV",
        data=csv,
        file_name=f"gantt_{info['nombre'].replace(' ', '_')}.csv",
        mime="text/csv",
    )