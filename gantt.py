import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import date, timedelta
from data import get_proyecto, calcular_estado_tarea, calcular_duracion, avance_total_proyecto


# ─────────────────────────────────────────────────────────────────────────────
# COLORES POR ESTADO
# ─────────────────────────────────────────────────────────────────────────────
COLORES_ESTADO = {
    "Completada":  "#4ade80",
    "En Progreso": "#38bdf8",
    "Atrasada":    "#f87171",
    "Pendiente":   "#64748b",
}

COLORES_AREA = {
    "Operaciones":             "#818cf8",
    "Logística / Supply Chain":"#34d399",
    "TI / Tecnología":         "#22d3ee",
    "Ingeniería / Proyectos":  "#fb923c",
    "Salud / Medicina":        "#f472b6",
    "Comercial / Ventas":      "#facc15",
    "Mantenimiento":           "#a78bfa",
    "RRHH / Administración":   "#94a3b8",
    "Otro":                    "#475569",
}


def build_gantt_figure(tareas: list, nombre_proyecto: str) -> go.Figure:
    """Construye la figura Plotly del Gantt."""
    hoy = date.today()
    fig = go.Figure()

    tareas_ord = sorted(tareas, key=lambda t: t["fecha_inicio"])

    for i, tarea in enumerate(tareas_ord):
        estado    = calcular_estado_tarea(tarea, hoy)
        duracion  = calcular_duracion(tarea)
        color_est = COLORES_ESTADO[estado]
        avance    = tarea.get("avance", 0)

        # Barra de planificación (fondo)
        fig.add_trace(go.Bar(
            x=[duracion],
            y=[tarea["nombre"]],
            base=[tarea["fecha_inicio"].isoformat()],
            orientation="h",
            marker=dict(
                color=color_est,
                opacity=0.25,
                line=dict(color=color_est, width=1.5)
            ),
            showlegend=False,
            hoverinfo="skip",
        ))

        # Barra de avance real
        dias_avance = duracion * avance / 100
        if dias_avance > 0:
            fig.add_trace(go.Bar(
                x=[dias_avance],
                y=[tarea["nombre"]],
                base=[tarea["fecha_inicio"].isoformat()],
                orientation="h",
                marker=dict(color=color_est, opacity=0.9),
                showlegend=False,
                customdata=[[
                    tarea["nombre"],
                    tarea.get("recurso", "—"),
                    tarea["fecha_inicio"].strftime("%d/%m/%Y"),
                    tarea["fecha_fin"].strftime("%d/%m/%Y"),
                    avance,
                    estado,
                    duracion,
                ]],
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Recurso: %{customdata[1]}<br>"
                    "Inicio: %{customdata[2]}  |  Fin: %{customdata[3]}<br>"
                    "Duración: %{customdata[6]} días<br>"
                    "Avance: %{customdata[4]}%<br>"
                    "Estado: %{customdata[5]}<extra></extra>"
                ),
            ))

        # Etiqueta de avance
        fig.add_annotation(
            x=tarea["fecha_inicio"] + timedelta(days=duracion / 2),
            y=tarea["nombre"],
            text=f"{avance}%",
            showarrow=False,
            font=dict(color="white", size=11, family="JetBrains Mono"),
            xref="x", yref="y",
        )

    # ── Fix Bug 1: rango del eje X explícito con padding ─────────────────────
    todas_fechas_inicio = [t["fecha_inicio"] for t in tareas_ord]
    todas_fechas_fin    = [t["fecha_fin"]    for t in tareas_ord]
    x_min = min(todas_fechas_inicio) - timedelta(days=2)
    x_max = max(todas_fechas_fin) + timedelta(days=10)  # era +5

    # Línea de hoy
    fig.add_shape(
        type="line",
        x0=hoy.isoformat(), x1=hoy.isoformat(),
        y0=0, y1=1,
        xref="x", yref="paper",
        line=dict(color="#facc15", width=2, dash="dash"),
    )
    fig.add_annotation(
        x=hoy.isoformat(), y=1.01,
        xref="x", yref="paper",
        text="Hoy",
        showarrow=False,
        font=dict(color="#facc15", size=11, family="Space Grotesk"),
        yanchor="bottom",
    )

    fig.update_layout(
        title=dict(
            text=f"Carta Gantt: {nombre_proyecto}",
            font=dict(color="#f0f9ff", size=18, family="Space Grotesk"),
        ),
        barmode="overlay",
        xaxis=dict(
            type="date",
            # ── Fix Bug 1: rango explícito ────────────────────────────────
            range=[x_min.isoformat(), x_max.isoformat()],
            title="Línea de tiempo",
            title_font=dict(color="#94a3b8"),
            tickfont=dict(color="#94a3b8"),
            tickformat="%d %b",        # "05 Apr" en lugar de timestamp
            dtick="M0.5",              # tick cada ~2 semanas
            gridcolor="#1e3a5f",
            showgrid=True,
        ),
        yaxis=dict(
            title="",
            tickfont=dict(color="#e2e8f0", size=12),
            gridcolor="#1e3a5f",
        ),
        plot_bgcolor="#0a0f1e",
        paper_bgcolor="#0a0f1e",
        height=max(350, 60 * len(tareas) + 80),
        margin=dict(l=10, r=30, t=60, b=30),
        hoverlabel=dict(
            bgcolor="#0d1b2a",
            bordercolor="#38bdf8",
            font_color="#e2e8f0",
        ),
    )
    return fig


def leyenda_estados():
    cols = st.columns(4)
    for i, (estado, color) in enumerate(COLORES_ESTADO.items()):
        cols[i].markdown(
            f"<span style='display:inline-block;width:12px;height:12px;"
            f"background:{color};border-radius:2px;margin-right:6px;'></span>"
            f"<span style='color:#94a3b8;font-size:0.85rem;'>{estado}</span>",
            unsafe_allow_html=True
        )


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA GANTT
# ─────────────────────────────────────────────────────────────────────────────
def pagina_gantt():
    st.markdown("## 📅 Carta Gantt")

    proyecto = get_proyecto()
    if not proyecto:
        st.markdown("""
<div class="card" style="text-align:center; padding: 2.5rem;">
<div style="font-size:3rem; margin-bottom:1rem;">📅</div>
<h3 style="color:#f0f9ff !important;">No hay proyecto seleccionado</h3>
<p style="color:#94a3b8;">Para ver la Carta Gantt necesitas tener un proyecto activo.</p>
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

    avance      = avance_total_proyecto(tareas)
    atrasadas   = sum(1 for t in tareas if calcular_estado_tarea(t, hoy) == "Atrasada")
    completadas = sum(1 for t in tareas if calcular_estado_tarea(t, hoy) == "Completada")

    st.markdown(
    f"<p style='color:#94a3b8; font-size:0.8rem; margin:0 0 0.2rem 0;'>Proyecto</p>"
    f"<p style='color:#f0f9ff; font-size:0.95rem; font-weight:600; margin:0 0 1rem 0;'>"
    f"{info['nombre']}</p>",
    unsafe_allow_html=True
)
    col1, col2, col3 = st.columns(3)
    col1.metric("📈 Avance total",   f"{avance}%")
    col2.metric("⚠️ Atrasadas",      atrasadas)
    col3.metric("✅ Completadas",    f"{completadas}/{len(tareas)}")

    st.markdown("---")

    if not tareas:
        st.markdown("""
<div class="card" style="text-align:center; padding: 2rem;">
<div style="font-size:2.5rem; margin-bottom:0.75rem;">🗂️</div>
<h4 style="color:#f0f9ff !important;">Este proyecto no tiene tareas</h4>
<p style="color:#94a3b8;">Agrega tareas desde <strong style="color:#38bdf8;">➕ Nuevo Proyecto</strong>.</p>
</div>
""", unsafe_allow_html=True)
        return

    leyenda_estados()
    fig = build_gantt_figure(tareas, info["nombre"])
    st.plotly_chart(fig, use_container_width=True)

    st.markdown(f"**Progreso general del proyecto: {avance}%**")
    st.progress(avance / 100)

    st.markdown("---")

    # ── Tabla de estado ───────────────────────────────────────────────────────
    st.markdown("### 📋 Estado de tareas")

    df = pd.DataFrame([{
        "Tarea":    t["nombre"],
        "Recurso":  t.get("recurso", "—"),
        "Área":     t.get("area", "—"),
        "Inicio":   t["fecha_inicio"].strftime("%d/%m/%Y"),
        "Fin":      t["fecha_fin"].strftime("%d/%m/%Y"),
        "Duración": f"{calcular_duracion(t)} días",
        "Avance":   f"{t['avance']}%",
        "Estado":   calcular_estado_tarea(t, hoy),
    } for t in tareas])

    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── Actualizar avance ─────────────────────────────────────────────────────
    st.markdown("### ✏️ Actualizar avance de tareas")
    st.caption("Selecciona una tarea y actualiza su porcentaje de avance.")

    nombre_activo  = st.session_state.proyecto_activo
    tareas_nombres = [t["nombre"] for t in st.session_state.proyectos[nombre_activo]["tareas"]]

    col_sel, col_av, col_btn = st.columns([3, 2, 1])
    with col_sel:
        tarea_sel = st.selectbox("Tarea a actualizar", tareas_nombres, key="tarea_upd")
    with col_av:
        idx           = tareas_nombres.index(tarea_sel)
        avance_actual = st.session_state.proyectos[nombre_activo]["tareas"][idx]["avance"]
        nuevo_avance  = st.slider("Nuevo avance (%)", 0, 100, avance_actual, key="nav_upd")
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💾 Guardar"):
            st.session_state.proyectos[nombre_activo]["tareas"][idx]["avance"] = nuevo_avance
            st.success(f"✅ **{tarea_sel}** actualizado a {nuevo_avance}%.")
            st.rerun()

    # ── Fix Bug 4: expanded=True para que sea visible ─────────────────────────
    with st.expander("📥 Actualización masiva de avances", expanded=False):
        st.caption("Ajusta todos los avances de una vez.")
        cambios = {}
        for t in st.session_state.proyectos[nombre_activo]["tareas"]:
            cambios[t["nombre"]] = st.slider(
                t["nombre"], 0, 100, t["avance"], key=f"mass_{t['nombre']}"
            )
        if st.button("💾 Guardar todos los cambios"):
            for tarea in st.session_state.proyectos[nombre_activo]["tareas"]:
                tarea["avance"] = cambios[tarea["nombre"]]
            st.success("✅ Todos los avances actualizados.")
            st.rerun()

    st.markdown("---")

    # ── Fix Bug 2: filtro siempre renderiza ───────────────────────────────────
    st.markdown("### 🔍 Filtrar por área")
    areas_disponibles = sorted(set(t.get("area", "Otro") for t in tareas))
    area_filtro = st.multiselect(
        "Selecciona área(s)",
        options=areas_disponibles,
        default=areas_disponibles,
        key="filtro_area"
    )

    tareas_filtradas = [t for t in tareas if t.get("area", "Otro") in area_filtro]

    if not area_filtro:
        st.info("Selecciona al menos un área para visualizar el Gantt filtrado.")
    elif len(area_filtro) == len(areas_disponibles):
        # Todas seleccionadas → no repetir el Gantt principal
        st.caption("✅ Mostrando todas las áreas — ver Gantt principal arriba.")
    else:
        # ── Fix Bug 2: siempre renderiza cuando hay selección parcial ─────
        st.plotly_chart(
            build_gantt_figure(
                tareas_filtradas,
                f"{info['nombre']} — {', '.join(area_filtro)}"
            ),
            use_container_width=True
        )
        st.caption(f"Mostrando {len(tareas_filtradas)} de {len(tareas)} tareas.")