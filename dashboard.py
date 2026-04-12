import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import date
from styles import aplicar_estilos, COLORES, COLORES_ESTADO_EXT, PLOTLY_LAYOUT, kpi_card
from data import (
    get_proyecto,
    calcular_estado_tarea,
    calcular_duracion,
    avance_total_proyecto,
    calcular_avance_tarea,
)


# ─────────────────────────────────────────────────────────────────────────────
# ESTADO EXTENDIDO CON RIESGO
# ─────────────────────────────────────────────────────────────────────────────
def _calcular_estado_riesgo(t: dict, hoy: date) -> str:
    """
    Igual que calcular_estado_tarea pero agrega 'En Riesgo' cuando el avance
    real queda ≥20 pts por debajo del esperado. Respeta hitos via calcular_avance_tarea.
    """
    estado = calcular_estado_tarea(t, hoy)
    if estado != "En Progreso":
        return estado
    try:
        duracion     = (t["fecha_fin"] - t["fecha_inicio"]).days or 1
        transcurrido = (hoy - t["fecha_inicio"]).days
        esperado     = round((transcurrido / duracion) * 100)
        if calcular_avance_tarea(t) < esperado - 20:
            return "En Riesgo"
    except Exception:
        pass
    return estado


# ─────────────────────────────────────────────────────────────────────────────
# GRÁFICOS
# ─────────────────────────────────────────────────────────────────────────────
def gauge_avance(avance: float) -> go.Figure:
    if avance >= 80:
        color = COLORES["success"]
    elif avance >= 40:
        color = COLORES["warning"]
    else:
        color = COLORES["danger"]

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=avance,
        number={"suffix": "%", "font": {"color": color, "size": 38, "family": "DM Mono"}},
        gauge={
            "axis": {
                "range": [0, 100],
                "tickcolor": COLORES["border"],
                "tickfont": {"color": COLORES["text_secondary"], "size": 10},
            },
            "bar": {"color": color, "thickness": 0.22},
            "bgcolor": "#F4F6F9",
            "borderwidth": 0,
            "steps": [
                {"range": [0,  40], "color": "rgba(220,53,69,0.08)"},
                {"range": [40, 80], "color": "rgba(255,193,7,0.08)"},
                {"range": [80,100], "color": "rgba(40,167,69,0.08)"},
            ],
        },
        title={"text": "Avance total", "font": {"color": COLORES["text_secondary"], "size": 13}},
    ))
    layout = {**PLOTLY_LAYOUT}
    layout.update(height=230, margin=dict(l=20, r=20, t=30, b=10))
    fig.update_layout(**layout)
    return fig


def pie_estados(conteo: dict) -> go.Figure:
    labels = list(conteo.keys())
    values = list(conteo.values())
    colors = [COLORES_ESTADO_EXT.get(l, COLORES["text_secondary"]) for l in labels]

    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=0.6,
        marker=dict(colors=colors, line=dict(color="#FFFFFF", width=3)),
        textfont=dict(color=COLORES["text_primary"], size=12, family="DM Sans"),
        hovertemplate="%{label}: <b>%{value}</b> tarea(s)<extra></extra>",
    ))
    layout = {**PLOTLY_LAYOUT}
    layout.update(
        height=260,
        title=dict(
            text="<b>Distribución de estados</b>",
            font=dict(color=COLORES["text_primary"], size=13, family="DM Sans"),
            x=0, xanchor="left",
        ),
        legend=dict(font=dict(color=COLORES["text_secondary"], size=11), orientation="v"),
    )
    fig.update_layout(**layout)
    return fig


def bar_avance_por_tarea(tareas: list) -> go.Figure:
    hoy     = date.today()
    nombres = [t["nombre"][:28] + "…" if len(t["nombre"]) > 28 else t["nombre"] for t in tareas]
    avances = [calcular_avance_tarea(t) for t in tareas]
    colores = [
        COLORES_ESTADO_EXT.get(_calcular_estado_riesgo(t, hoy), COLORES["text_secondary"])
        for t in tareas
    ]

    fig = go.Figure(go.Bar(
        x=avances, y=nombres, orientation="h",
        marker=dict(color=colores, opacity=0.85, line=dict(color="white", width=0.5)),
        text=[f"  {a}%" for a in avances],
        textposition="inside",
        textfont=dict(color="white", size=11, family="DM Mono"),
        hovertemplate="<b>%{y}</b><br>Avance: %{x}%<extra></extra>",
    ))
    layout = {**PLOTLY_LAYOUT}
    layout.update(
        height=max(260, 38 * len(tareas) + 60),
        xaxis=dict(range=[0, 100], title="% Avance",
                   gridcolor=COLORES["border"],
                   tickfont=dict(color=COLORES["text_secondary"])),
        yaxis=dict(tickfont=dict(color=COLORES["text_primary"], size=11)),
        title=dict(text="<b>Avance por tarea</b>",
                   font=dict(color=COLORES["text_primary"], size=13), x=0, xanchor="left"),
    )
    fig.update_layout(**layout)
    return fig


def bar_hitos_por_tarea(tareas: list) -> go.Figure | None:
    """Barras apiladas hitos completados / pendientes. Retorna None si no hay hitos."""
    tareas_h = [t for t in tareas if t.get("hitos")]
    if not tareas_h:
        return None

    nombres     = [t["nombre"][:28] + "…" if len(t["nombre"]) > 28 else t["nombre"] for t in tareas_h]
    completados = [sum(1 for h in t["hitos"] if h.get("completado")) for t in tareas_h]
    totales     = [len(t["hitos"]) for t in tareas_h]
    pendientes  = [tot - comp for tot, comp in zip(totales, completados)]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=completados, y=nombres, orientation="h",
        name="Completados",
        marker=dict(color=COLORES["success"], opacity=0.85),
        text=[f"  {c}/{tot}" for c, tot in zip(completados, totales)],
        textposition="inside",
        textfont=dict(color="white", size=11, family="DM Mono"),
        hovertemplate="<b>%{y}</b><br>Completados: %{x}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=pendientes, y=nombres, orientation="h",
        name="Pendientes",
        marker=dict(color=COLORES.get("border", "#DEE2E6"), opacity=0.7),
        hovertemplate="<b>%{y}</b><br>Pendientes: %{x}<extra></extra>",
    ))

    layout = {**PLOTLY_LAYOUT}
    layout.update(
        barmode="stack",
        height=max(220, 38 * len(tareas_h) + 60),
        xaxis=dict(title="Número de hitos",
                   gridcolor=COLORES["border"],
                   tickfont=dict(color=COLORES["text_secondary"])),
        yaxis=dict(tickfont=dict(color=COLORES["text_primary"], size=11)),
        title=dict(text="<b>Hitos por tarea</b>",
                   font=dict(color=COLORES["text_primary"], size=13), x=0, xanchor="left"),
        legend=dict(font=dict(color=COLORES["text_secondary"], size=11),
                    orientation="h", y=-0.18),
    )
    fig.update_layout(**layout)
    return fig


def bar_por_area(tareas: list) -> go.Figure:
    df = pd.DataFrame([
        {"area": t.get("area", "Otro"), "avance": calcular_avance_tarea(t)}
        for t in tareas
    ])
    df_grp = (df.groupby("area")["avance"].mean()
                .reset_index()
                .rename(columns={"area": "Área", "avance": "Avance"})
                .sort_values("Avance", ascending=True))

    colors = []
    for v in df_grp["Avance"]:
        if v >= 80:   colors.append(COLORES["success"])
        elif v >= 50: colors.append(COLORES["secondary"])
        elif v >= 30: colors.append(COLORES["warning"])
        else:         colors.append(COLORES["danger"])

    fig = go.Figure(go.Bar(
        x=df_grp["Avance"], y=df_grp["Área"], orientation="h",
        marker=dict(color=colors, opacity=0.85, line=dict(color="white", width=0.5)),
        text=[f"  {v:.0f}%" for v in df_grp["Avance"]],
        textposition="inside",
        textfont=dict(color="white", size=11, family="DM Mono"),
        hovertemplate="<b>%{y}</b><br>Avance promedio: %{x:.1f}%<extra></extra>",
    ))
    layout = {**PLOTLY_LAYOUT}
    layout.update(
        height=max(220, 44 * len(df_grp) + 60),
        xaxis=dict(range=[0, 100], title="Avance promedio (%)",
                   gridcolor=COLORES["border"],
                   tickfont=dict(color=COLORES["text_secondary"])),
        yaxis=dict(tickfont=dict(color=COLORES["text_primary"], size=11)),
        title=dict(text="<b>Avance por área</b>",
                   font=dict(color=COLORES["text_primary"], size=13), x=0, xanchor="left"),
    )
    fig.update_layout(**layout)
    return fig


def bar_carga_recursos(tareas: list) -> go.Figure:
    rows = [{"Recurso": t.get("recurso") or "Sin asignar", "Días": calcular_duracion(t)}
            for t in tareas]
    df     = pd.DataFrame(rows)
    df_grp = (df.groupby("Recurso")["Días"].sum()
                .reset_index()
                .sort_values("Días", ascending=True))

    max_dias = df_grp["Días"].max() or 1
    colors   = [COLORES["primary"] if d / max_dias > 0.7 else COLORES["secondary"]
                for d in df_grp["Días"]]

    fig = go.Figure(go.Bar(
        x=df_grp["Días"], y=df_grp["Recurso"], orientation="h",
        marker=dict(color=colors, opacity=0.85, line=dict(color="white", width=0.5)),
        text=[f"  {d}d" for d in df_grp["Días"]],
        textposition="inside",
        textfont=dict(color="white", size=11, family="DM Mono"),
        hovertemplate="<b>%{y}</b><br>%{x} días asignados<extra></extra>",
    ))
    layout = {**PLOTLY_LAYOUT}
    layout.update(
        height=max(220, 42 * len(df_grp) + 60),
        xaxis=dict(title="Días asignados",
                   gridcolor=COLORES["border"],
                   tickfont=dict(color=COLORES["text_secondary"])),
        yaxis=dict(tickfont=dict(color=COLORES["text_primary"], size=11)),
        title=dict(text="<b>Carga por recurso</b>",
                   font=dict(color=COLORES["text_primary"], size=13), x=0, xanchor="left"),
    )
    fig.update_layout(**layout)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
def pagina_dashboard():
    aplicar_estilos()

    st.markdown("## 📊 Dashboard del Proyecto")

    proyecto = get_proyecto()
    if not proyecto:
        st.markdown("""
        <div class="card" style="text-align:center;padding:2.5rem;">
            <div style="font-size:3rem;margin-bottom:1rem;">📊</div>
            <h3>No hay proyecto seleccionado</h3>
            <p>Usa <strong>⚡ Cargar proyecto demo</strong> en el menú lateral.</p>
        </div>
        """, unsafe_allow_html=True)
        return

    info   = proyecto["info"]
    tareas = proyecto["tareas"]
    hoy    = date.today()

    if not tareas:
        st.info("Sin tareas registradas. Agrega tareas desde ➕ Nuevo Proyecto.")
        return

    # ── Conteo de estados ─────────────────────────────────────────────────────
    avance  = avance_total_proyecto(tareas)
    estados = {e: 0 for e in ["Completada", "En Progreso", "En Riesgo", "Atrasada", "Pendiente"]}
    for t in tareas:
        estados[_calcular_estado_riesgo(t, hoy)] += 1

    # ── Resumen de hitos ──────────────────────────────────────────────────────
    total_hitos       = sum(len(t.get("hitos", [])) for t in tareas)
    hitos_completados = sum(
        sum(1 for h in t.get("hitos", []) if h.get("completado"))
        for t in tareas
    )
    tareas_con_hitos  = sum(1 for t in tareas if t.get("hitos"))

    # ── Días restantes ────────────────────────────────────────────────────────
    if isinstance(info.get("fecha_fin"), date):
        dias_rest = (info["fecha_fin"] - hoy).days
        if dias_rest < 0:
            dias_label, dias_kpi = f"−{abs(dias_rest)}d", "kpi-red"
        elif dias_rest == 0:
            dias_label, dias_kpi = "Hoy", "kpi-orange"
        else:
            dias_label, dias_kpi = f"{dias_rest}d", "kpi-teal"
    else:
        dias_label, dias_kpi = "—", "kpi-teal"

    salud = (
        "🟢 Saludable" if estados["Atrasada"] == 0 and estados["En Riesgo"] == 0 else
        "🟠 En riesgo"  if estados["Atrasada"] == 0 else
        "🔴 Crítico"
    )

    # ── KPI cards principales ─────────────────────────────────────────────────
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.markdown(kpi_card(f"{avance}%",           "Avance total",   "kpi-purple", "📈"), unsafe_allow_html=True)
    c2.markdown(kpi_card(estados["Completada"],  "Completadas",    "kpi-green",  "✅"), unsafe_allow_html=True)
    c3.markdown(kpi_card(estados["En Progreso"], "En progreso",    "kpi-blue",   "🔄"), unsafe_allow_html=True)
    c4.markdown(kpi_card(estados["En Riesgo"],   "En riesgo",      "kpi-orange", "🟠"), unsafe_allow_html=True)
    c5.markdown(kpi_card(estados["Atrasada"],    "Atrasadas",      "kpi-red",    "⚠️"), unsafe_allow_html=True)
    c6.markdown(kpi_card(dias_label,             "Días restantes", dias_kpi,     "📅"), unsafe_allow_html=True)

    st.markdown("---")

    # ── Barra de progreso general ─────────────────────────────────────────────
    col_prog, col_info = st.columns([3, 1])
    with col_prog:
        st.markdown(f"**Progreso del proyecto:** {avance}%")
        st.progress(avance / 100)
    with col_info:
        st.markdown(f"**Salud:** {salud}")
        st.caption(f"👤 Responsable: {info.get('responsable','—')}")
        st.caption(f"🎯 Prioridad: {info.get('prioridad','—')}")

    # ── Bloque de hitos (solo si existen) ─────────────────────────────────────
    if total_hitos > 0:
        st.markdown("---")
        st.markdown("### 🏁 Resumen de hitos")

        h1, h2, h3, h4 = st.columns(4)
        h1.markdown(kpi_card(tareas_con_hitos,               "Tareas con hitos",  "kpi-blue",   "📋"), unsafe_allow_html=True)
        h2.markdown(kpi_card(total_hitos,                    "Hitos totales",     "kpi-purple", "🏁"), unsafe_allow_html=True)
        h3.markdown(kpi_card(hitos_completados,              "Completados",       "kpi-green",  "✅"), unsafe_allow_html=True)
        h4.markdown(kpi_card(total_hitos - hitos_completados,"Pendientes",        "kpi-orange", "⏳"), unsafe_allow_html=True)

        pct_hitos = round(hitos_completados / total_hitos * 100) if total_hitos else 0
        st.markdown(f"**Progreso de hitos:** {hitos_completados}/{total_hitos} ({pct_hitos}%)")
        st.progress(pct_hitos / 100)

    st.markdown("---")

    # ── Fila 1: Gauge + Pie ───────────────────────────────────────────────────
    col_g, col_p = st.columns(2)
    with col_g:
        st.plotly_chart(gauge_avance(avance), use_container_width=True)
    with col_p:
        st.plotly_chart(pie_estados({k: v for k, v in estados.items() if v > 0}),
                        use_container_width=True)

    st.markdown("---")

    # ── Avance por tarea ──────────────────────────────────────────────────────
    st.plotly_chart(bar_avance_por_tarea(tareas), use_container_width=True)

    # ── Hitos por tarea (condicional) ─────────────────────────────────────────
    fig_hitos = bar_hitos_por_tarea(tareas)
    if fig_hitos:
        st.plotly_chart(fig_hitos, use_container_width=True)

    st.markdown("---")

    # ── Área + Recursos ───────────────────────────────────────────────────────
    col_a, col_r = st.columns(2)
    with col_a:
        st.plotly_chart(bar_por_area(tareas), use_container_width=True)
    with col_r:
        st.plotly_chart(bar_carga_recursos(tareas), use_container_width=True)

    st.markdown("---")

    # ── Tabla detalle ─────────────────────────────────────────────────────────
    st.markdown("### 📋 Detalle de tareas")

    df = pd.DataFrame([{
        "Tarea":    t["nombre"],
        "Recurso":  t.get("recurso", "—"),
        "Área":     t.get("area", "—"),
        "Inicio":   t["fecha_inicio"].strftime("%d/%m/%Y"),
        "Fin":      t["fecha_fin"].strftime("%d/%m/%Y"),
        "Días":     calcular_duracion(t),
        "Hitos":    (
            f"{sum(1 for h in t['hitos'] if h.get('completado'))}/{len(t['hitos'])}"
            if t.get("hitos") else "—"
        ),
        "Avance %": calcular_avance_tarea(t),
        "Estado":   _calcular_estado_riesgo(t, hoy),
    } for t in tareas])

    def _color_estado(val):
        m = {
            "Completada":  "background-color:rgba(40,167,69,0.1);color:#28A745;font-weight:600",
            "En Progreso": "background-color:rgba(0,123,255,0.1);color:#007BFF;font-weight:600",
            "En Riesgo":   "background-color:rgba(255,193,7,0.12);color:#D39E00;font-weight:600",
            "Atrasada":    "background-color:rgba(220,53,69,0.1);color:#DC3545;font-weight:600",
            "Pendiente":   "background-color:rgba(108,117,125,0.08);color:#6C757D",
        }
        return m.get(val, "")

    st.dataframe(
        df.style.map(_color_estado, subset=["Estado"]),
        use_container_width=True,
        hide_index=True,
    )

    # ── Detalle expandible de hitos por tarea ─────────────────────────────────
    tareas_h = [t for t in tareas if t.get("hitos")]
    if tareas_h:
        st.markdown("---")
        st.markdown("### 🏁 Detalle de hitos por tarea")
        for t in tareas_h:
            hitos_t     = t["hitos"]
            comp        = sum(1 for h in hitos_t if h.get("completado"))
            avance_t    = calcular_avance_tarea(t)
            estado_t    = _calcular_estado_riesgo(t, hoy)
            with st.expander(
                f"**{t['nombre']}** — {comp}/{len(hitos_t)} hitos ({avance_t}%) · {estado_t}"
            ):
                for h in hitos_t:
                    st.markdown(f"{'✅' if h.get('completado') else '⬜'} {h['nombre']}")

    # ── Alertas ───────────────────────────────────────────────────────────────
    atrasadas_l = [t for t in tareas if _calcular_estado_riesgo(t, hoy) == "Atrasada"]
    en_riesgo_l = [t for t in tareas if _calcular_estado_riesgo(t, hoy) == "En Riesgo"]

    if atrasadas_l:
        st.markdown("---")
        st.markdown("### 🚨 Alertas de atraso")
        for t in atrasadas_l:
            dias_atras = (hoy - t["fecha_fin"]).days
            hitos_info = ""
            if t.get("hitos"):
                c = sum(1 for h in t["hitos"] if h.get("completado"))
                hitos_info = f" | 🏁 Hitos: {c}/{len(t['hitos'])}"
            st.error(
                f"**{t['nombre']}** — {dias_atras}d atrasada | "
                f"Avance: {calcular_avance_tarea(t)}%{hitos_info} | "
                f"👤 {t.get('recurso','—')}"
            )

    if en_riesgo_l:
        if not atrasadas_l:
            st.markdown("---")
        st.markdown("### ⚠️ Tareas en riesgo")
        for t in en_riesgo_l:
            dur      = (t["fecha_fin"] - t["fecha_inicio"]).days or 1
            trans    = (hoy - t["fecha_inicio"]).days
            esp      = round((trans / dur) * 100)
            avance_r = calcular_avance_tarea(t)
            brecha   = esp - avance_r
            hitos_info = ""
            if t.get("hitos"):
                c = sum(1 for h in t["hitos"] if h.get("completado"))
                hitos_info = f" | 🏁 Hitos: {c}/{len(t['hitos'])}"
            st.warning(
                f"**{t['nombre']}** — real: {avance_r}% vs esperado: {esp}% "
                f"| Brecha: **{brecha}pts**{hitos_info} | "
                f"👤 {t.get('recurso','—')} | "
                f"Fin: {t['fecha_fin'].strftime('%d/%m/%Y')}"
            )

    # ── Exportar ──────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📥 Exportar informe ejecutivo")
    st.download_button(
        label="⬇️ Descargar CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=f"dashboard_{info['nombre'].replace(' ','_')}.csv",
        mime="text/csv",
    )
    st.markdown("### 📄 Generar informe ejecutivo (PDF) [próximamente]")
