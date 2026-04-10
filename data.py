import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def get_proyecto():
    """Devuelve el proyecto activo o None."""
    nombre = st.session_state.get("proyecto_activo")
    if nombre and nombre in st.session_state.proyectos:
        return st.session_state.proyectos[nombre]
    return None


def cargar_demo(nombre):
    return pd.read_csv(f"data/{nombre}.csv")


# ── 1. Calcula el avance real (hitos o manual) ────────────────────────────────
def calcular_avance_tarea(tarea: dict) -> int:
    """
    Si la tarea tiene hitos: avance = hitos completados / total * 100.
    Si no tiene hitos: usa el avance manual guardado.
    """
    hitos = tarea.get("hitos", [])
    if hitos:
        completados = sum(1 for h in hitos if h.get("completado"))
        return round((completados / len(hitos)) * 100)
    return tarea.get("avance", 0)


# ── 2. Usa calcular_avance_tarea internamente ─────────────────────────────────
def calcular_estado_tarea(tarea: dict, hoy: date) -> str:
    """Retorna el estado: Completada / En Progreso / En Riesgo / Atrasada / Pendiente."""
    avance = calcular_avance_tarea(tarea)
    fin    = tarea.get("fecha_fin")
    inicio = tarea.get("fecha_inicio")

    if avance >= 100:
        return "Completada"
    if isinstance(fin, date) and fin < hoy and avance < 100:
        return "Atrasada"
    if avance > 0:
        if isinstance(inicio, date) and isinstance(fin, date):
            duracion     = (fin - inicio).days or 1
            transcurrido = (hoy - inicio).days
            if transcurrido > 0:
                avance_esperado = (transcurrido / duracion) * 100
                if avance < avance_esperado - 30:
                    return "En Riesgo"
        return "En Progreso"
    return "Pendiente"


def calcular_duracion(tarea: dict) -> int:
    """Días entre inicio y fin (inclusive)."""
    try:
        return (tarea["fecha_fin"] - tarea["fecha_inicio"]).days + 1
    except Exception:
        return 0


def avance_total_proyecto(tareas: list) -> float:
    total_hitos = 0
    hitos_completados = 0

    for t in tareas:
        hitos = t.get("hitos", [])

        if hitos:
            total_hitos += len(hitos)
            hitos_completados += sum(1 for h in hitos if h.get("completado"))
        else:
            # fallback si no hay hitos
            total_hitos += 1
            hitos_completados += t.get("avance", 0) / 100

    if total_hitos == 0:
        return 0

    return round((hitos_completados / total_hitos) * 100, 1)


# ─────────────────────────────────────────────────────────────────────────────
# IMPORTAR CSV
# ─────────────────────────────────────────────────────────────────────────────
COLUMNAS_REQUERIDAS = {"nombre", "recurso", "area", "fecha_inicio", "fecha_fin", "avance"}
AREAS_VALIDAS = [
    "Operaciones",
    "Logística / Supply Chain",
    "TI / Tecnología",
    "Ingeniería / Proyectos",
    "Salud / Medicina",
    "Comercial / Ventas",
    "Mantenimiento",
    "RRHH / Administración",
    "Otro",
]
FORMATOS_FECHA = ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]


def _parsear_fecha(valor: str) -> date | None:
    for fmt in FORMATOS_FECHA:
        try:
            return datetime.strptime(str(valor).strip(), fmt).date()
        except ValueError:
            continue
    return None


def _normalizar_area(valor: str) -> str:
    valor = str(valor).strip()
    for area in AREAS_VALIDAS:
        if area.lower() == valor.lower():
            return area
    return "Otro"


def _parsear_hitos(valor) -> list[dict]:
    """
    Convierte 'Hito 1, Hito 2, Hito 3' en lista de dicts.
    Retorna [] si el valor está vacío o es NaN.
    """
    if not valor or str(valor).strip() in ("", "nan", "NaN"):
        return []
    return [
        {"nombre": h.strip(), "completado": False}
        for h in str(valor).split(",")
        if h.strip()
    ]


def importar_csv(archivo) -> tuple[list[dict], list[str]]:
    """
    Lee un archivo CSV y retorna (tareas_validas, errores).
    Acepta encoding utf-8, utf-8-sig y latin-1.
    Columna opcional: hitos (separados por coma).
    """
    tareas  = []
    errores = []

    df = None
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            archivo.seek(0)
            df = pd.read_csv(archivo, encoding=enc, dtype=str)
            df.columns = df.columns.str.strip().str.lower()
            break
        except Exception:
            continue

    if df is None:
        return [], ["No se pudo leer el archivo. Verifica que sea un CSV válido."]

    faltantes = COLUMNAS_REQUERIDAS - set(df.columns)
    if faltantes:
        return [], [
            f"Faltan columnas obligatorias: **{', '.join(sorted(faltantes))}**. "
            f"Las columnas requeridas son: {', '.join(sorted(COLUMNAS_REQUERIDAS))}."
        ]

    for i, row in df.iterrows():
        fila = i + 2

        nombre = str(row.get("nombre", "")).strip()
        if not nombre:
            errores.append(f"Fila {fila}: nombre vacío, se omite.")
            continue

        fecha_inicio = _parsear_fecha(row.get("fecha_inicio", ""))
        if not fecha_inicio:
            errores.append(f"Fila {fila} ({nombre}): fecha_inicio inválida — '{row.get('fecha_inicio')}'. Use DD/MM/YYYY.")
            continue

        fecha_fin = _parsear_fecha(row.get("fecha_fin", ""))
        if not fecha_fin:
            errores.append(f"Fila {fila} ({nombre}): fecha_fin inválida — '{row.get('fecha_fin')}'. Use DD/MM/YYYY.")
            continue

        if fecha_fin < fecha_inicio:
            errores.append(f"Fila {fila} ({nombre}): fecha_fin anterior a fecha_inicio, se omite.")
            continue

        # ── Hitos: columna opcional ───────────────────────────────────────────
        hitos = _parsear_hitos(row.get("hitos", ""))
        avance = 0

        # ── Avance: ignorado si hay hitos (se calcula por checkboxes) ─────────
        if hitos:
            try:
                avance_csv = int(float(str(row.get("avance", 0)).replace("%", "").strip()))
            except:
                avance_csv = 0

            # 🔥 Si venía en 100%, marcar todos los hitos automáticamente
            if avance_csv == 100:
                for h in hitos:
                    h["completado"] = True
                avance = 100
            else:
                avance = 0
        # ── Caso 2: SIN hitos ────────────────────────────────────────────────
        else:
            raw_avance = row.get("avance", 0)

            try:
                if raw_avance is None or str(raw_avance).strip() == "":
                    raise ValueError

                avance = int(float(str(raw_avance).replace("%", "").strip()))
                avance = max(0, min(100, avance))

            except:
                errores.append(
                    f"Fila {fila} ({nombre}): avance inválido — '{raw_avance}', se asigna 0."
                )
                avance = 0

        tareas.append({
            "nombre":       nombre,
            "recurso":      str(row.get("recurso", "")).strip(),
            "area":         _normalizar_area(row.get("area", "Otro")),
            "fecha_inicio": fecha_inicio,
            "fecha_fin":    fecha_fin,
            "avance":       avance,
            "descripcion":  str(row.get("descripcion", "")).strip(),
            "hitos":        hitos,
        })

    return tareas, errores


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA INICIO
# ─────────────────────────────────────────────────────────────────────────────
def pagina_inicio():
    st.markdown("## 🏠 Bienvenido a **Carta Gantt Inteligente**")
    st.markdown("Sistema integrado de planificación, seguimiento y análisis de proyectos.")
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)
    n_proyectos = len(st.session_state.proyectos)
    n_tareas    = sum(len(p["tareas"]) for p in st.session_state.proyectos.values())

    atrasadas = 0
    hoy = date.today()
    for p in st.session_state.proyectos.values():
        atrasadas += sum(1 for t in p["tareas"]
                         if calcular_estado_tarea(t, hoy) == "Atrasada")

    avance_prom = 0.0
    if st.session_state.proyectos:
        avance_prom = round(
            sum(avance_total_proyecto(p["tareas"])
                for p in st.session_state.proyectos.values()) / n_proyectos, 1
        )

    col1.metric("📁 Proyectos",        n_proyectos)
    col2.metric("📋 Tareas totales",   n_tareas)
    col3.metric("⚠️ Tareas atrasadas", atrasadas)
    col4.metric("📈 Avance promedio",  f"{avance_prom}%")

    st.markdown("---")

    if not st.session_state.proyectos:
        st.info("No tienes proyectos aún. Ve a **➕ Nuevo Proyecto** para comenzar.")
        return

    st.markdown("### 📋 Proyectos registrados")
    hoy = date.today()
    for nombre, datos in st.session_state.proyectos.items():
        info   = datos["info"]
        tareas = datos["tareas"]
        avance = avance_total_proyecto(tareas)

        with st.expander(f"**{nombre}** — {avance}% completado"):
            c1, c2, c3 = st.columns(3)
            c1.write(f"**Responsable:** {info.get('responsable','—')}")
            c2.write(f"**Inicio:** {info.get('fecha_inicio','—')}")
            c3.write(f"**Fin estimado:** {info.get('fecha_fin','—')}")
            st.write(f"**Descripción:** {info.get('descripcion','—')}")
            st.progress(avance / 100)

    st.markdown("---")
    st.markdown("### 🗺️ ¿Cómo usar el sistema?")
    st.markdown("""
1. **➕ Nuevo Proyecto** → Crea el proyecto e ingresa las tareas manualmente o importa un CSV
2. **📅 Ver Gantt** → Visualiza la carta Gantt y actualiza el avance
3. **📊 Dashboard** → Revisa KPIs y estado general
4. **🧠 Análisis IA** → Obtén interpretación automática con recomendaciones
""")


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA NUEVO PROYECTO
# ─────────────────────────────────────────────────────────────────────────────
def pagina_nuevo_proyecto():
    st.markdown("## ➕ Nuevo Proyecto")
    st.markdown("Completa la información del proyecto y agrega las tareas.")
    st.markdown("---")

    # ── Información general ───────────────────────────────────────────────────
    with st.expander("📁 Información general del proyecto", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            nombre_proyecto = st.text_input("Nombre del proyecto *",
                                             placeholder="Ej: Distribución Zona Norte")
            responsable     = st.text_input("Responsable *", placeholder="Ej: Juan Pérez")
            area            = st.selectbox("Área / Departamento", AREAS_VALIDAS)
        with col2:
            fecha_inicio_proy = st.date_input("Fecha de inicio", value=date.today())
            fecha_fin_proy    = st.date_input("Fecha de término estimada",
                                               value=date.today() + timedelta(days=30))
            prioridad         = st.selectbox("Prioridad", ["Alta", "Media", "Baja"])

        descripcion = st.text_area("Descripción del proyecto",
                                    placeholder="Describe brevemente el objetivo del proyecto...")

    st.markdown("---")
    st.markdown("### 📋 Tareas del proyecto")

    if "tareas_form" not in st.session_state:
        st.session_state.tareas_form = []

    # ── Importar desde CSV ────────────────────────────────────────────────────
    with st.expander("📂 Importar tareas desde CSV", expanded=False):
        st.markdown("""
**Formato requerido** — columnas obligatorias:

| columna | ejemplo | notas |
|---|---|---|
| `nombre` | Instalación de estanterías | Nombre de la tarea |
| `recurso` | Jorge Muñoz | Persona asignada |
| `area` | Operaciones | Operaciones, Logística, TI, etc. |
| `fecha_inicio` | 05/04/2026 | Formato DD/MM/YYYY |
| `fecha_fin` | 11/04/2026 | Formato DD/MM/YYYY |
| `avance` | 60 | Número entre 0 y 100 |

Columnas opcionales: `descripcion`, `hitos` (separados por coma).
""")
        plantilla = pd.DataFrame([{
            "nombre":       "Ejemplo tarea 1",
            "recurso":      "Juan Pérez",
            "area":         "Operaciones",
            "fecha_inicio": "05/04/2026",
            "fecha_fin":    "11/04/2026",
            "avance":       "0",
            "descripcion":  "Descripción opcional",
            "hitos":        "Diseño, Desarrollo, Pruebas, Entrega",
        }])
        st.download_button(
            label="⬇️ Descargar plantilla CSV",
            data=plantilla.to_csv(index=False).encode("utf-8-sig"),
            file_name="plantilla_tareas.csv",
            mime="text/csv",
        )

        archivo_csv = st.file_uploader("Selecciona tu archivo CSV",
                                        type=["csv"], key="csv_upload")
        if archivo_csv:
            tareas_importadas, errores_csv = importar_csv(archivo_csv)

            if errores_csv:
                st.markdown("**⚠️ Advertencias:**")
                for e in errores_csv:
                    st.warning(e)

            if tareas_importadas:
                hoy = date.today()
                df_prev = pd.DataFrame([{
                    "Tarea":   t["nombre"],
                    "Recurso": t["recurso"],
                    "Área":    t["area"],
                    "Inicio":  t["fecha_inicio"].strftime("%d/%m/%Y"),
                    "Fin":     t["fecha_fin"].strftime("%d/%m/%Y"),
                    "Hitos":   len(t.get("hitos", [])) or "—",
                    "Avance":  f"{calcular_avance_tarea(t)}%",
                    "Estado":  calcular_estado_tarea(t, hoy),
                } for t in tareas_importadas])

                st.success(f"✅ {len(tareas_importadas)} tarea(s) listas para importar.")
                st.dataframe(df_prev, use_container_width=True, hide_index=True)

                if st.button("✅ Confirmar importación", type="primary",
                              use_container_width=True):
                    nombres_existentes = {t["nombre"] for t in st.session_state.tareas_form}
                    nuevas     = [t for t in tareas_importadas
                                  if t["nombre"] not in nombres_existentes]
                    duplicadas = len(tareas_importadas) - len(nuevas)
                    st.session_state.tareas_form.extend(nuevas)
                    msg = f"✅ {len(nuevas)} tarea(s) importadas."
                    if duplicadas:
                        msg += f" {duplicadas} omitida(s) por nombre duplicado."
                    st.success(msg)
                    st.rerun()
            elif not errores_csv:
                st.error("El CSV no contiene tareas válidas.")

    # ── Agregar manualmente ───────────────────────────────────────────────────
    with st.expander("➕ Agregar tarea manualmente",
                      expanded=len(st.session_state.tareas_form) == 0):
        c1, c2, c3 = st.columns(3)
        with c1:
            nombre_tarea = st.text_input("Nombre de la tarea *", key="nt")
            recurso      = st.text_input("Recurso / Persona asignada", key="rec",
                                          placeholder="Ej: María González")
        with c2:
            fecha_ini_t  = st.date_input("Fecha inicio tarea", value=date.today(), key="fi")
            fecha_fin_t  = st.date_input("Fecha fin tarea",
                                          value=date.today() + timedelta(days=7), key="ff")
        with c3:
            area_tarea   = st.selectbox("Área de la tarea", AREAS_VALIDAS, key="at")
            avance_tarea = st.slider("% Avance inicial", 0, 100, 0, key="av")

        hitos_input = st.text_input(
            "Hitos (separados por coma) — opcional",
            placeholder="Ej: Diseño, Desarrollo, Pruebas, Entrega",
            key="hitos_t",
            help="Si defines hitos, el avance se calculará automáticamente según los que marques.",
        )
        if hitos_input.strip():
            hitos_preview = [h.strip() for h in hitos_input.split(",") if h.strip()]
            st.caption(
                f"✅ {len(hitos_preview)} hito(s) detectados — "
                f"cada uno valdrá **{round(100 / len(hitos_preview), 1)}%**"
            )

        descripcion_t = st.text_input("Descripción de la tarea (opcional)", key="dt")

        if st.button("✅ Agregar tarea"):
            if not nombre_tarea:
                st.error("El nombre de la tarea es obligatorio.")
            elif fecha_fin_t < fecha_ini_t:
                st.error("La fecha de fin no puede ser anterior al inicio.")
            else:
                hitos_parseados = _parsear_hitos(hitos_input)
                avance_final    = 0 if hitos_parseados else avance_tarea

                if avance_final > 0 and fecha_ini_t > date.today():
                    st.warning(
                        f"⚠️ La tarea tiene {avance_final}% de avance pero su inicio "
                        f"es {fecha_ini_t.strftime('%d/%m/%Y')} (fecha futura). "
                        "Verifica si las fechas o el avance son correctos."
                    )

                st.session_state.tareas_form.append({
                    "nombre":       nombre_tarea,
                    "recurso":      recurso,
                    "area":         area_tarea,
                    "fecha_inicio": fecha_ini_t,
                    "fecha_fin":    fecha_fin_t,
                    "avance":       avance_final,
                    "descripcion":  descripcion_t,
                    "hitos":        hitos_parseados,
                })
                st.success(
                    f"Tarea **{nombre_tarea}** agregada"
                    + (f" con {len(hitos_parseados)} hitos." if hitos_parseados else ".")
                )
                st.rerun()

    # ── Lista de tareas cargadas ──────────────────────────────────────────────
    if st.session_state.tareas_form:
        st.markdown(f"**{len(st.session_state.tareas_form)} tarea(s) cargada(s):**")
        hoy = date.today()

        df_preview = pd.DataFrame([{
            "Tarea":    t["nombre"],
            "Recurso":  t["recurso"],
            "Área":     t["area"],
            "Inicio":   t["fecha_inicio"].strftime("%d/%m/%Y"),
            "Fin":      t["fecha_fin"].strftime("%d/%m/%Y"),
            "Duración": f"{calcular_duracion(t)} días",
            "Hitos":    len(t.get("hitos", [])) or "—",
            "Avance":   f"{calcular_avance_tarea(t)}%",
            "Estado":   calcular_estado_tarea(t, hoy),
        } for t in st.session_state.tareas_form])

        st.dataframe(df_preview, use_container_width=True, hide_index=True)

        col_del1, col_del2 = st.columns([3, 1])
        with col_del1:
            tarea_a_eliminar = st.selectbox(
                "Eliminar tarea",
                [t["nombre"] for t in st.session_state.tareas_form],
                key="del_t",
            )
        with col_del2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑️ Eliminar"):
                st.session_state.tareas_form = [
                    t for t in st.session_state.tareas_form
                    if t["nombre"] != tarea_a_eliminar
                ]
                st.rerun()

    st.markdown("---")

    # ── Guardar proyecto ──────────────────────────────────────────────────────
    col_s1, col_s2 = st.columns([3, 1])
    with col_s2:
        guardar = st.button("💾 Guardar proyecto", type="primary")

    if guardar:
        if not nombre_proyecto:
            st.error("El nombre del proyecto es obligatorio.")
        elif nombre_proyecto in st.session_state.proyectos:
            st.error(f"Ya existe un proyecto con el nombre **{nombre_proyecto}**.")
        elif not st.session_state.tareas_form:
            st.error("Debes agregar al menos una tarea.")
        else:
            st.session_state.proyectos[nombre_proyecto] = {
                "info": {
                    "nombre":       nombre_proyecto,
                    "responsable":  responsable,
                    "area":         area,
                    "fecha_inicio": fecha_inicio_proy,
                    "fecha_fin":    fecha_fin_proy,
                    "prioridad":    prioridad,
                    "descripcion":  descripcion,
                },
                "tareas": list(st.session_state.tareas_form),
            }
            st.session_state.proyecto_activo = nombre_proyecto
            st.session_state.tareas_form = []
            st.success(f"✅ Proyecto **{nombre_proyecto}** guardado exitosamente.")
            st.info("Ve a **📅 Ver Gantt** para visualizar tu proyecto.")
            st.rerun()

    # ── Agregar tarea a proyecto existente ────────────────────────────────────
    if st.session_state.proyectos:
        st.markdown("---")
        st.markdown("### ✏️ Agregar tarea a proyecto existente")

        proy_editar = st.selectbox(
            "Selecciona el proyecto",
            list(st.session_state.proyectos.keys()),
            key="proy_ed",
        )

        # Importar CSV a proyecto existente
        with st.expander("📂 Importar tareas desde CSV al proyecto existente"):
            archivo_csv2 = st.file_uploader("Selecciona tu archivo CSV",
                                             type=["csv"], key="csv_upload2")
            if archivo_csv2:
                tareas_imp2, errores_csv2 = importar_csv(archivo_csv2)

                if errores_csv2:
                    for e in errores_csv2:
                        st.warning(e)

                if tareas_imp2:
                    hoy = date.today()
                    df_prev2 = pd.DataFrame([{
                        "Tarea":   t["nombre"],
                        "Recurso": t["recurso"],
                        "Inicio":  t["fecha_inicio"].strftime("%d/%m/%Y"),
                        "Fin":     t["fecha_fin"].strftime("%d/%m/%Y"),
                        "Hitos":   len(t.get("hitos", [])) or "—",
                        "Avance":  f"{calcular_avance_tarea(t)}%",
                        "Estado":  calcular_estado_tarea(t, hoy),
                    } for t in tareas_imp2])
                    st.success(f"✅ {len(tareas_imp2)} tarea(s) listas para importar.")
                    st.dataframe(df_prev2, use_container_width=True, hide_index=True)

                    if st.button("✅ Confirmar importación al proyecto",
                                  type="primary", use_container_width=True):
                        existentes  = {t["nombre"] for t in
                                       st.session_state.proyectos[proy_editar]["tareas"]}
                        nuevas2     = [t for t in tareas_imp2
                                       if t["nombre"] not in existentes]
                        duplicadas2 = len(tareas_imp2) - len(nuevas2)
                        st.session_state.proyectos[proy_editar]["tareas"].extend(nuevas2)
                        msg = f"✅ {len(nuevas2)} tarea(s) importadas a **{proy_editar}**."
                        if duplicadas2:
                            msg += f" {duplicadas2} omitida(s) por nombre duplicado."
                        st.success(msg)
                        st.rerun()

        # Formulario manual a proyecto existente
        with st.expander("➕ Agregar tarea manualmente al proyecto seleccionado"):
            c1, c2, c3 = st.columns(3)
            with c1:
                nt2  = st.text_input("Nombre tarea", key="nt2")
                rec2 = st.text_input("Recurso", key="rec2")
            with c2:
                fi2  = st.date_input("Inicio", value=date.today(), key="fi2")
                ff2  = st.date_input("Fin", value=date.today() + timedelta(days=7), key="ff2")
            with c3:
                at2  = st.selectbox("Área", AREAS_VALIDAS, key="at2")
                av2  = st.slider("% Avance", 0, 100, 0, key="av2")

            hitos_input2 = st.text_input(
                "Hitos (separados por coma) — opcional",
                placeholder="Ej: Diseño, Desarrollo, Pruebas, Entrega",
                key="hitos_t2",
                help="Si defines hitos, el avance se calculará automáticamente.",
            )
            if hitos_input2.strip():
                hitos_prev2 = [h.strip() for h in hitos_input2.split(",") if h.strip()]
                st.caption(
                    f"✅ {len(hitos_prev2)} hito(s) — "
                    f"cada uno valdrá **{round(100 / len(hitos_prev2), 1)}%**"
                )

            if st.button("✅ Agregar al proyecto"):
                if not nt2:
                    st.error("Nombre obligatorio.")
                elif ff2 < fi2:
                    st.error("Fecha fin anterior al inicio.")
                else:
                    hitos_parseados2 = _parsear_hitos(hitos_input2)
                    avance_final2    = 0 if hitos_parseados2 else av2

                    if avance_final2 > 0 and fi2 > date.today():
                        st.warning(
                            f"⚠️ La tarea tiene {avance_final2}% de avance pero su inicio "
                            f"es {fi2.strftime('%d/%m/%Y')} (fecha futura)."
                        )

                    st.session_state.proyectos[proy_editar]["tareas"].append({
                        "nombre":       nt2,
                        "recurso":      rec2,
                        "area":         at2,
                        "fecha_inicio": fi2,
                        "fecha_fin":    ff2,
                        "avance":       avance_final2,
                        "descripcion":  "",
                        "hitos":        hitos_parseados2,
                    })
                    st.success(
                        f"Tarea **{nt2}** agregada a **{proy_editar}**"
                        + (f" con {len(hitos_parseados2)} hitos."
                           if hitos_parseados2 else ".")
                    )
                    st.rerun()