import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import date, timedelta
from styles import aplicar_estilos, COLORES, COLORES_ESTADO, PLOTLY_LAYOUT, kpi_card
from data import (   get_proyecto,
    calcular_estado_tarea,
    calcular_duracion,
    avance_total_proyecto,
    calcular_avance_tarea)


# ─────────────────────────────────────────────────────────────────────────────
# COLORES DE ÁREA
# ─────────────────────────────────────────────────────────────────────────────
COLORES_AREA = {
    "Operaciones":              "#6F42C1",
    "Logística / Supply Chain": "#007BFF",
    "TI / Tecnología":          "#00CCCC",
    "Ingeniería / Proyectos":   "#FD7E14",
    "Salud / Medicina":         "#E83E8C",
    "Comercial / Ventas":       "#FFC107",
    "Mantenimiento":            "#8B5CF6",
    "RRHH / Administración":    "#17A2B8",
    "Otro":                     "#6C757D",
}


# ─────────────────────────────────────────────────────────────────────────────
# GANTT
# ─────────────────────────────────────────────────────────────────────────────
def build_gantt_figure(tareas: list, nombre_proyecto: str) -> go.Figure:
    hoy = date.today()
    fig = go.Figure()

    tareas_ord = sorted(
        tareas,
        key=lambda t: (calcular_estado_tarea(t, hoy), t["fecha_inicio"])
    )

    for tarea in tareas_ord:
        estado   = calcular_estado_tarea(tarea, hoy)
        duracion = calcular_duracion(tarea)
        color    = COLORES_ESTADO.get(estado, COLORES["text_secondary"])
        avance   = calcular_avance_tarea(tarea)

        fecha_inicio = tarea["fecha_inicio"]
        fecha_fin    = tarea["fecha_fin"]

        area    = tarea.get("area", "")
        label_y = f"{area}  |  {tarea['nombre']}" if area else tarea["nombre"]

        # ── Hito (1 día) ──────────────────────────────────────────────────
        if duracion <= 1:
            fig.add_trace(go.Scatter(
                x=[fecha_inicio],
                y=[label_y],
                mode="markers+text",
                marker=dict(size=14, color=color, symbol="diamond",
                            line=dict(color="white", width=1.5)),
                text=[f" {'✓ 100%' if avance == 100 else f'{avance}%'}"],
                textposition="middle right",
                textfont=dict(color=COLORES["text_primary"], size=10),
                showlegend=False,
                customdata=[[tarea["nombre"], tarea.get("recurso", "—"),
                             fecha_inicio.strftime("%d/%m/%Y"),
                             fecha_fin.strftime("%d/%m/%Y"),
                             avance, estado, duracion]],
                hovertemplate=(
                    "<b>🔹 HITO: %{customdata[0]}</b><br>"
                    "👤 %{customdata[1]}<br>"
                    "📅 %{customdata[2]}<br>"
                    "📊 Avance: %{customdata[4]}%<br>"
                    "🚨 Estado: <b>%{customdata[5]}</b><extra></extra>"
                ),
            ))
            continue

        # ── Cálculos ──────────────────────────────────────────────────────
        dias_esperados = max(0, min((hoy - fecha_inicio).days, duracion))
        pct_esperado   = (dias_esperados / duracion * 100) if duracion else 0
        dias_avance    = duracion if avance == 100 else max(int(duracion * avance / 100), 1 if avance > 0 else 0)
        color_texto    = "white" if avance > 40 else "#212529"


        # ── Barra fondo ───────────────────────────────────────────────────
        if avance < 100:
            fig.add_trace(go.Bar(
                x=[fecha_fin.isoformat()],          # ← fecha fin, no número de días
                y=[label_y],
                base=[fecha_inicio.isoformat()],
                orientation="h",
                marker=dict(color=color, opacity=0.35,
                            line=dict(color=color, width=1)),
                showlegend=False,
                hoverinfo="skip",
            ))

        # ── Barra roja atraso ─────────────────────────────────────────────
        if avance < pct_esperado and dias_esperados > 0 and avance < 100:
            fecha_esperada = (fecha_inicio + timedelta(days=dias_esperados)).isoformat()
            fig.add_trace(go.Bar(
                x=[fecha_esperada],                 # ← fecha hasta donde debería ir
                y=[label_y],
                base=[fecha_inicio.isoformat()],
                orientation="h",
                marker=dict(color="rgba(220,38,38,0.25)",
                            line=dict(color="rgba(220,38,38,0.7)", width=1)),
                showlegend=False,
                hoverinfo="skip",
            ))

        # ── Barra avance real ─────────────────────────────────────────────
        if dias_avance > 0:
            fecha_avance = (fecha_inicio + timedelta(days=dias_avance)).isoformat()
            fig.add_trace(go.Bar(
                x=[fecha_avance],                   # ← fecha hasta donde llegó
                y=[label_y],
                base=[fecha_inicio.isoformat()],
                orientation="h",
                marker=dict(color=color, opacity=1.0,
                            line=dict(color="white", width=0.5)),
                showlegend=False,
                customdata=[[
                    tarea["nombre"], tarea.get("recurso", "—"),
                    fecha_inicio.strftime("%d/%m/%Y"),
                    fecha_fin.strftime("%d/%m/%Y"),
                    avance, estado, duracion,
                    round(pct_esperado, 1),
                ]],
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "👤 %{customdata[1]}<br>"
                    "📅 %{customdata[2]} → %{customdata[3]}<br>"
                    "⏱ %{customdata[6]} días totales<br>"
                    "📊 Avance real: <b>%{customdata[4]}%</b><br>"
                    "🎯 Avance esperado: %{customdata[7]}%<br>"
                    "🚨 Estado: <b>%{customdata[5]}</b><extra></extra>"
                ),
            ))

        # ── Etiqueta % ────────────────────────────────────────────────────
        mid       = fecha_inicio + timedelta(days=duracion / 2)
        if avance > 0:
            fig.add_annotation(
                x=mid, y=label_y,
                text="✓ 100%" if avance == 100 else f"{avance}%",
                showarrow=False,
                font=dict(color=color_texto, size=11),
            )

    # ── Rango eje X ───────────────────────────────────────────────────────

    x_min = min(t["fecha_inicio"] for t in tareas_ord) - timedelta(days=2)
    x_max = max(t["fecha_fin"] for t in tareas_ord) + timedelta(days=10)

    # ── Línea HOY ─────────────────────────────────────────────────────────
    fig.add_shape(
        type="line",
        x0=hoy.isoformat(), x1=hoy.isoformat(),
        y0=0, y1=1, xref="x", yref="paper",
        line=dict(color="#DC2626", width=2.5, dash="dash"),
    )
    fig.add_annotation(
        x=hoy.isoformat(), y=1.02, xref="x", yref="paper",
        text="HOY", showarrow=False, yanchor="bottom",
        font=dict(color="#DC2626", size=11, family="DM Sans"),
        bgcolor="rgba(220,38,38,0.08)",
        bordercolor="#DC2626",
        borderwidth=1.5, borderpad=3,
    )

    layout = {**PLOTLY_LAYOUT}
    layout.pop("xaxis", None)
    layout.pop("yaxis", None)

    layout.update(dict(
        title=dict(
            text=f"<b>{nombre_proyecto}</b>",
            font=dict(color=COLORES["text_primary"], size=15, family="DM Sans"),
            x=0,
            xanchor="left",
        ),
        barmode="overlay",
        xaxis=dict(
            type="date",
            range=[x_min.isoformat(), x_max.isoformat()],
            tickformat="%d %b",
            dtick=86400000 * 3,
            showgrid=True,
            zeroline=False,
            gridcolor=COLORES["border"],
            tickfont=dict(color=COLORES["text_secondary"], size=10),
            tickangle=-45,
        ),
        yaxis=dict(
            tickfont=dict(color=COLORES["text_primary"], size=11),
            gridcolor=COLORES["border"],
        ),
        height=max(360, 52 * len(tareas) + 80),
        margin=dict(l=10, r=30, t=55, b=60),
    ))

    fig.update_layout(**layout)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# LEYENDA DE ESTADOS
# ─────────────────────────────────────────────────────────────────────────────
def leyenda_estados():
    cols = st.columns(len(COLORES_ESTADO))
    for i, (estado, color) in enumerate(COLORES_ESTADO.items()):
        cols[i].markdown(
            f"<span style='display:inline-flex;align-items:center;gap:6px;'>"
            f"<span style='width:10px;height:10px;background:{color};"
            f"border-radius:3px;display:inline-block;'></span>"
            f"<span style='color:#6C757D;font-size:0.82rem;'>{estado}</span></span>",
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA GANTT
# ─────────────────────────────────────────────────────────────────────────────
def pagina_gantt():
    aplicar_estilos()
    st.markdown("## 📅 Carta Gantt")
    proyecto = get_proyecto()
    if not proyecto:
        st.markdown("""
        <div class="card" style="text-align:center; padding:2.5rem;">
            <div style="font-size:3rem; margin-bottom:1rem;">📅</div>
            <h3>No hay proyecto seleccionado</h3>
            <p>Para ver la Carta Gantt necesitas tener un proyecto activo.</p>
            <br>
            <p style="font-size:0.85rem;">
                1. Usa <strong>⚡ Cargar proyecto demo</strong> en el menú lateral.<br>
                2. O ve a <strong>➕ Nuevo Proyecto</strong> para crear uno.
            </p>
        </div>
        """, unsafe_allow_html=True)
        return

    info   = proyecto["info"]
    tareas = proyecto["tareas"]
    hoy    = date.today()
    # ── Métricas ──────────────────────────────────────────────────────────────
    avance        = avance_total_proyecto(tareas)
    atrasadas_n   = sum(1 for t in tareas if calcular_estado_tarea(t, hoy) == "Atrasada")
    en_riesgo_n   = sum(1 for t in tareas if calcular_estado_tarea(t, hoy) == "En Riesgo")
    completadas_n = sum(1 for t in tareas if calcular_estado_tarea(t, hoy) == "Completada")

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(
        f"<p style='color:#ADB5BD;font-size:0.75rem;text-transform:uppercase;"
        f"letter-spacing:0.5px;margin:0 0 2px 0;'>Proyecto</p>"
        f"<p style='color:#212529;font-size:1.05rem;font-weight:700;"
        f"margin:0 0 1rem 0;'>{info['nombre']}</p>",
        unsafe_allow_html=True,
    )

    # ── KPIs ──────────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(kpi_card(f"{avance}%",                 "Avance total", "kpi-purple", "📈"), unsafe_allow_html=True)
    c2.markdown(kpi_card(atrasadas_n,                  "Atrasadas",    "kpi-red",    "⚠️"), unsafe_allow_html=True)
    c3.markdown(kpi_card(en_riesgo_n,                  "En riesgo",    "kpi-yellow", "🟡"), unsafe_allow_html=True)
    c4.markdown(kpi_card(f"{completadas_n}/{len(tareas)}", "Completadas", "kpi-green", "✅"), unsafe_allow_html=True)

    # ── Insight automático ────────────────────────────────────────────────────
    atrasadas_lst = [t for t in tareas if calcular_estado_tarea(t, hoy) == "Atrasada"]
    if atrasadas_lst:
        nombres = ", ".join(t["nombre"] for t in atrasadas_lst[:2])
        extra   = f" y {len(atrasadas_lst) - 2} más" if len(atrasadas_lst) > 2 else ""
        st.error(
            f"⚠️ **{len(atrasadas_lst)} tarea(s) atrasada(s)** pueden afectar el plazo: "
            f"*{nombres}{extra}.*"
        )
    elif en_riesgo_n:
        st.warning(f"🟡 **{en_riesgo_n} tarea(s) en riesgo.** Monitorear de cerca.")
    else:
        st.success("✅ Todas las tareas van dentro del plan.")

    # ── Barra de progreso global ──────────────────────────────────────────────
    st.progress(avance / 100)
    st.caption(f"Progreso general del proyecto · {avance}% completado")

    st.markdown("---")

    if not tareas:
        st.info("Este proyecto no tiene tareas. Agrega tareas desde ➕ Nuevo Proyecto.")
        return

    # ── Gantt ─────────────────────────────────────────────────────────────────
    leyenda_estados()
    st.plotly_chart(build_gantt_figure(tareas, info["nombre"]), use_container_width=True)

    st.markdown("---")

    # ── Tabla de estado ───────────────────────────────────────────────────────
    st.markdown("### 📋 Estado de tareas")

    df = pd.DataFrame([{
        "Tarea":    t["nombre"],
        "Recurso":  t.get("recurso", "—"),
        "Área":     t.get("area", "—"),
        "Inicio":   t["fecha_inicio"].strftime("%d/%m/%Y"),
        "Fin":      t["fecha_fin"].strftime("%d/%m/%Y"),
        "Duración": f"{calcular_duracion(t)}d",
        "Avance": f"{calcular_avance_tarea(t)}%",
        "Estado":   calcular_estado_tarea(t, hoy),
    } for t in tareas])

    def _color_estado(val):
        m = {
            "Completada":  "background-color:rgba(40,167,69,0.1);color:#28A745;font-weight:600",
            "En Progreso": "background-color:rgba(0,123,255,0.1);color:#007BFF;font-weight:600",
            "En Riesgo":   "background-color:rgba(255,193,7,0.1);color:#D39E00;font-weight:600",
            "Atrasada":    "background-color:rgba(220,53,69,0.1);color:#DC3545;font-weight:600",
            "Pendiente":   "background-color:rgba(108,117,125,0.08);color:#6C757D",
        }
        return m.get(val, "")

    st.dataframe(
        df.style.map(_color_estado, subset=["Estado"]),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("---")

    # ── Actualizar avance ─────────────────────────────────────────────────────

    st.markdown("### ✏️ Actualizar avance")
    st.caption("Marca los hitos completados de cada tarea.")

    nombre_activo = st.session_state.proyecto_activo
    tareas_edit   = st.session_state.proyectos[nombre_activo]["tareas"]

    tarea_sel = st.selectbox(
        "Selecciona tarea",
        [t["nombre"] for t in tareas_edit],
        key="tarea_hitos_sel"
    )

    idx   = next(i for i, t in enumerate(tareas_edit) if t["nombre"] == tarea_sel)
    tarea = tareas_edit[idx]
    hitos = tarea.get("hitos", [])

    if not hitos:
        # Sin hitos → mantener slider manual
        nuevo_avance = st.slider("Avance (%)", 0, 100, tarea.get("avance", 0), key="nav_upd")
        if st.button("💾 Guardar"):
            tareas_edit[idx]["avance"] = nuevo_avance
            st.success(f"✅ {tarea_sel} → {nuevo_avance}%")
            st.rerun()
    else:
        # Con hitos → checkboxes
        st.markdown(f"**{len(hitos)} hitos** — cada uno vale `{round(100/len(hitos), 1)}%`")
        cambios = {}
        for j, hito in enumerate(hitos):
            cambios[j] = st.checkbox(
                hito["nombre"],
                value=hito.get("completado", False),
                key=f"hito_{idx}_{j}"
            )
        avance_calc = round(sum(cambios.values()) / len(hitos) * 100)
        st.info(f"📊 Avance calculado: **{avance_calc}%**")

        if st.button("💾 Guardar hitos"):
            for j, completado in cambios.items():
                tareas_edit[idx]["hitos"][j]["completado"] = completado
            tareas_edit[idx]["avance"] = avance_calc  # sincronizar
            st.success(f"✅ {tarea_sel} → {avance_calc}%")
            st.rerun()
    st.markdown("---")

    # ── Filtro por área ───────────────────────────────────────────────────────
    st.markdown("### 🔍 Filtrar por área")
    areas_disponibles = sorted(set(t.get("area", "Otro") for t in tareas))
    area_filtro = st.multiselect(
        "Área(s)", options=areas_disponibles,
        default=areas_disponibles, key="filtro_area"
    )

    if not area_filtro:
        st.info("Selecciona al menos un área.")
    elif len(area_filtro) < len(areas_disponibles):
        tareas_filtradas = [t for t in tareas if t.get("area", "Otro") in area_filtro]
        st.plotly_chart(
            build_gantt_figure(
                tareas_filtradas,
                f"{info['nombre']} — {', '.join(area_filtro)}"
            ),
            use_container_width=True,
        )
        st.caption(f"Mostrando {len(tareas_filtradas)} de {len(tareas)} tareas.")
    else:
        st.caption("✅ Mostrando todas las áreas — ver Gantt principal arriba.")