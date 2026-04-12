import os
import requests
import streamlit as st
from datetime import date, datetime
import time
from data import get_proyecto, calcular_estado_tarea, avance_total_proyecto, calcular_avance_tarea
from dotenv import load_dotenv
load_dotenv()
 
# ─────────────────────────────────────────────────────────────────────────────
# CONFIG GEMINI
# ─────────────────────────────────────────────────────────────────────────────
try:
    GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
except Exception:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_BASE    = "https://generativelanguage.googleapis.com/v1beta/models/"
GEMINI_MODELS  = [
    "gemini-2.5-flash:generateContent",
    "gemini-2.5-flash-lite:generateContent",
    "gemini-3-flash-preview:generateContent",
]
 
 
def _llamar_gemini(prompt: str, max_tokens: int = 2000) -> str | None:
    if not GEMINI_API_KEY:
        st.warning("⚠️ No hay GEMINI_API_KEY cargada")
        return None
 
    for model in GEMINI_MODELS:
        url = GEMINI_BASE + model
        for intento in range(3):
            try:
                resp = requests.post(
                    url,
                    params={"key": GEMINI_API_KEY},
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "temperature": 0.4,
                            "maxOutputTokens": max_tokens,
                            "topP": 0.9,
                            "topK": 40,
                        },
                    },
                    timeout=30,
                )
                if resp.status_code == 503:
                    espera = 2 ** intento
                    st.toast(f"⏳ Gemini ocupado, reintentando en {espera}s... ({intento+1}/3)")
                    time.sleep(espera)
                    continue
                if resp.status_code != 200:
                    st.error(f"❌ Error HTTP {resp.status_code}: {resp.text}")
                    break
                data = resp.json()
                if not data.get("candidates"):
                    st.warning(f"⚠️ Respuesta sin candidates: {data}")
                    break
                partes = data["candidates"][0].get("content", {}).get("parts", [])
                if not partes:
                    st.warning(f"⚠️ Respuesta sin contenido: {data}")
                    break
                finish = data["candidates"][0].get("finishReason", "STOP").upper()
                if finish not in ("STOP", "", "MAX_TOKENS"):
                    st.warning(f"⚠️ Respuesta incompleta (finishReason: {finish})")
                    break
                return partes[0].get("text", None)
            except requests.exceptions.Timeout:
                st.error("⏱️ Timeout al conectar con Gemini")
                break
            except Exception as e:
                st.error(f"🔥 Error Gemini: {e}")
                break
    st.warning("⚠️ Gemini no disponible — usando análisis local.")
    return None
 
 
# ─────────────────────────────────────────────────────────────────────────────
# MOTOR DE ANÁLISIS BASE
# ─────────────────────────────────────────────────────────────────────────────
def analizar_proyecto(proyecto: dict) -> dict:
    hoy    = date.today()
    tareas = proyecto["tareas"]
    avance = avance_total_proyecto(tareas)
 
    atrasadas, en_progreso, completadas, pendientes = [], [], [], []
    carga_recursos: dict[str, list] = {}
    carga_areas: dict[str, list]    = {}
 
    for t in tareas:
        estado = calcular_estado_tarea(t, hoy)
        if estado == "Atrasada":         atrasadas.append(t)
        elif estado == "En Progreso":    en_progreso.append(t)
        elif estado == "Completada":     completadas.append(t)
        else:                            pendientes.append(t)
 
        carga_recursos.setdefault(t.get("recurso", "—"), []).append(t)
        carga_areas.setdefault(t.get("area", "—"), []).append(t)
 
    recurso_critico = max(carga_recursos, key=lambda r: len(carga_recursos[r]))
    area_critica    = max(carga_areas,    key=lambda a: len(carga_areas[a]))
 
    if len(atrasadas) >= 3 or avance < 40:
        riesgo = "🔴 Alto"
    elif len(atrasadas) > 0 or avance < 70:
        riesgo = "🟡 Medio"
    else:
        riesgo = "🟢 Bajo"
 
    dias_restantes = proyecto["info"].get("dias_restantes", None)
    if dias_restantes is not None:
        ritmo_requerido = (100 - avance) / max(dias_restantes, 1)
        proyeccion = "⚠️ Plazo en riesgo" if ritmo_requerido > 5 else "✅ Plazo alcanzable"
    else:
        proyeccion = "⚠️ Plazo en riesgo" if (avance < 50 and atrasadas) else "✅ Plazo alcanzable"
 
    rendimiento_trabajadores = {}
    for recurso, tareas_r in carga_recursos.items():
        total         = len(tareas_r)
        completadas_r = sum(1 for t in tareas_r if calcular_estado_tarea(t, hoy) == "Completada")
        atrasadas_r   = sum(1 for t in tareas_r if calcular_estado_tarea(t, hoy) == "Atrasada")
        avance_prom   = sum(calcular_avance_tarea(t) for t in tareas_r) / total if total else 0
        rendimiento_trabajadores[recurso] = {
            "total": total,
            "completadas": completadas_r,
            "atrasadas": atrasadas_r,
            "avance_promedio": round(avance_prom, 1),
            "tareas": [t["nombre"] for t in tareas_r],
        }
 
    rendimiento_areas = {}
    for area, tareas_a in carga_areas.items():
        total       = len(tareas_a)
        avance_prom = sum(calcular_avance_tarea(t) for t in tareas_a) / total if total else 0
        atrasadas_a = sum(1 for t in tareas_a if calcular_estado_tarea(t, hoy) == "Atrasada")
        rendimiento_areas[area] = {
            "total": total,
            "avance_promedio": round(avance_prom, 1),
            "atrasadas": atrasadas_a,
        }
 
    return {
        "avance": avance,
        "atrasadas": atrasadas,
        "en_progreso": en_progreso,
        "completadas": completadas,
        "pendientes": pendientes,
        "recurso_critico": recurso_critico,
        "area_critica": area_critica,
        "riesgo": riesgo,
        "proyeccion": proyeccion,
        "carga_recursos": carga_recursos,
        "rendimiento_trabajadores": rendimiento_trabajadores,
        "rendimiento_areas": rendimiento_areas,
    }
 
 
# ─────────────────────────────────────────────────────────────────────────────
# CONTEXTO ESTRUCTURADO PARA GEMINI
# ─────────────────────────────────────────────────────────────────────────────
def _dias_restantes(t: dict, hoy: date) -> str:
    try:
        fin   = datetime.strptime(str(t["fecha_fin"]), "%d/%m/%Y").date()
        delta = (fin - hoy).days
        return f"{abs(delta)}d VENCIDA" if delta < 0 else f"{delta}d restantes"
    except Exception:
        return "sin fecha"
 
 
def _resumen_hitos(t: dict) -> str:
    hitos = t.get("hitos", [])
    if not hitos:
        return ""
    comp = sum(1 for h in hitos if h.get("completado"))
    return f" | 🏁 {comp}/{len(hitos)} hitos"
 
 
def _construir_contexto(proyecto: dict, analisis: dict) -> str:
    info     = proyecto["info"]
    hoy_date = date.today()

    def dias_rest(t):
        return (t["fecha_fin"] - hoy_date).days

    def resumen_hitos(t):
        hitos = t.get("hitos", [])
        if not hitos:
            return ""
        comp = sum(1 for h in hitos if h.get("completado"))
        return f"{comp}/{len(hitos)} hitos"

    tareas_criticas = sorted(
        proyecto["tareas"],
        key=lambda t: (
            calcular_estado_tarea(t, hoy_date) != "Atrasada",
            dias_rest(t)
        )
    )[:8]

    tareas_txt = "\n".join([
        f"- {t['nombre']} | Resp: {t.get('recurso','—')} | "
        f"Av: {calcular_avance_tarea(t)}% | "
        f"Fin: {t['fecha_fin']} | "
        f"Días: {dias_rest(t)} | "
        f"Estado: {calcular_estado_tarea(t, hoy_date)}"
        + (f" | Hitos: {resumen_hitos(t)}" if t.get("hitos") else "")
        for t in tareas_criticas
    ])

    trabajadores_txt = "\n".join([
        f"- {n}: {d['total']} tareas | Av: {d['avance_promedio']}% | "
        f"Atrasadas: {d['atrasadas']}"
        for n, d in analisis["rendimiento_trabajadores"].items()
    ])

    return f"""
PROYECTO:
- Nombre: {info['nombre']}
- Avance total: {analisis['avance']}%
- Riesgo: {analisis['riesgo']}
- Proyección: {analisis['proyeccion']}
- Días restantes: {(info['fecha_fin'] - hoy_date).days}

TAREAS CRÍTICAS:
{tareas_txt}

RENDIMIENTO EQUIPO:
{trabajadores_txt}
""".strip()
 
 
# ─────────────────────────────────────────────────────────────────────────────
# STORYTELLING CON GEMINI (+ fallback local)
# ─────────────────────────────────────────────────────────────────────────────
def generar_storytelling(proyecto: dict) -> tuple[str, bool]:
    analisis = analizar_proyecto(proyecto)
    ctx      = _construir_contexto(proyecto, analisis)
 
    # ── PROMPT EJECUTIVO: formato fijo + contexto experto minero ─────────────
    prompt = f"""Eres consultor senior especializado en planificación y control de proyectos mineros.
Analiza los datos y responde en español con criterio operacional y económico.

PRINCIPIOS DE ANÁLISIS MINERO (aplicar siempre):
- Prioriza el impacto operacional y económico por sobre la descripción de datos.
- Identifica cuellos de botella en la cadena productiva: tronadura, carga, transporte, procesamiento.
- Evalúa cómo los atrasos afectan la continuidad operacional y el cumplimiento de producción.
- Detecta desalineamiento entre planificación y ejecución cuando exista evidencia.
- Enfócate solo en indicadores críticos — no todos los datos tienen el mismo peso.
- Prioriza la urgencia: destaca lo que requiere acción inmediata.
- Propón acciones concretas, no generales.
- Relaciona el estado del proyecto con impacto en costos, producción o plazos.
- Analiza el proyecto como un sistema interdependiente: una tarea atrasada afecta a otras.
- Actúa como consultor que debe tomar decisiones, no como analista que describe datos.

{ctx}

Genera el análisis con EXACTAMENTE este formato. Sé conciso y usa datos concretos del proyecto.
No uses lenguaje informal. Cada sección respeta el límite indicado.

## 📋 RESUMEN EJECUTIVO
[3 líneas máximo. Estado actual: % avance, tareas completadas/total, días restantes, nivel de riesgo y tendencia operacional.]

## ⚡ IMPACTO OPERACIONAL Y ECONÓMICO
[2–3 bullets. Consecuencias concretas sobre producción, costos o plazo si no se actúa.
Nombra tareas y responsables específicos. Relaciona cada atraso con su efecto en la cadena productiva.]

## ⚠️ RIESGOS CRÍTICOS
[2–3 bullets. Solo los riesgos que pueden detener la operación o comprometer el plazo.
Indica severidad estimada. Incluye hitos pendientes si aplica.]

## ✅ ACCIONES RECOMENDADAS
[4 bullets priorizados por urgencia. Formato estricto:
Responsable — Acción específica — Resultado esperado — Plazo concreto.]

Proyección de cierre: [En plazo / En riesgo / Crítico] — [razón en 1 frase con datos del proyecto.]
"""
    respuesta_ia = _llamar_gemini(prompt, max_tokens=2000)
    if respuesta_ia:
        respuesta = respuesta_ia.strip()

        if len(respuesta) > 4000:
            respuesta = respuesta[:4000] + "\n\n⚠️ Respuesta resumida por límite de longitud."

        info = proyecto["info"]
        encabezado = (
            f"## 🗂️ ANÁLISIS EJECUTIVO — {info['nombre'].upper()}\n\n"
            f"**Fecha:** {date.today().strftime('%d/%m/%Y')}  |  "
            f"**Avance:** {analisis['avance']}%  |  "
            f"**Riesgo:** {analisis['riesgo']}  |  "
            f"**Proyección:** {analisis['proyeccion']}\n\n---\n\n"
        )
        return encabezado + respuesta, True
 
    return _generar_storytelling_local(proyecto, analisis), False
 
 
# ─────────────────────────────────────────────────────────────────────────────
# CHAT CON GEMINI (+ fallback local)
# ─────────────────────────────────────────────────────────────────────────────
def responder_pregunta(proyecto: dict, pregunta: str, historial: list | None = None) -> tuple[str, bool]:
    analisis = analizar_proyecto(proyecto)
    ctx      = _construir_contexto(proyecto, analisis)
 
    historial_texto = ""
    if historial:
        for msg in historial[-6:]:
            rol = "Usuario" if msg["rol"] == "usuario" else "Asistente"
            historial_texto += f"{rol}: {msg['texto']}\n"
 
    # ── PROMPT PROFESIONAL: contexto experto minero + formato ejecutivo ──────
    prompt = f"""Eres Jefe de Planificación con experiencia en operaciones mineras de alta complejidad.
Integras análisis de proyectos con lógica estratégica basada en principios de planificación y control operacional.

PRINCIPIOS DE ANÁLISIS MINERO (aplicar siempre):
- Prioriza el impacto operacional y económico por sobre la descripción de datos.
- Identifica cuellos de botella en la cadena productiva: tronadura, carga, transporte, procesamiento.
- Evalúa cómo los atrasos afectan la continuidad operacional y el cumplimiento de producción.
- Detecta desalineamiento entre planificación y ejecución cuando exista evidencia.
- Enfócate solo en indicadores críticos — no todos los datos tienen el mismo peso.
- Prioriza la urgencia: lo que requiere acción inmediata va primero.
- Propón acciones concretas, no generales.
- Relaciona el estado del proyecto con impacto en costos, producción o plazos.
- Analiza el proyecto como un sistema interdependiente: una tarea atrasada afecta a otras.
- Actúa como consultor que debe tomar decisiones, no como analista que describe datos.
- Cuando sea posible, indica si el proyecto es recuperable o no en el plazo actual
- Si existe una tarea crítica atrasada, destácala explícitamente como riesgo principal
- Cuando sea posible, indica si el proyecto es recuperable en el plazo actual

REGLAS DE CÁLCULO:
- Usa exclusivamente los datos del proyecto (%, fechas, responsables)
- Calcula cuando corresponda: avance requerido diario = (100 - avance_actual) / días_restantes
- Si días_restantes <= 0 → tarea inviable en plazo actual
- Si hay hitos → calcula % real basado en hitos completados
- Si existe una tarea crítica atrasada, destácala explícitamente como riesgo principal

FORMATO DE RESPUESTA (obligatorio):
1. Situación actual — datos concretos, máximo 3 líneas
2. Impacto operacional/económico — qué ocurre si no se actúa
3. Acciones recomendadas — máximo 4, ordenadas por criticidad (de mayor a menor impacto)
4. Decisión recomendada — una acción concreta e inmediata de nivel ejecutivo

ESTILO:
- Lenguaje técnico y profesional
- Sin frases de relleno ni introductorias
- Responde directo a la consulta formulada
- Usa bullets solo cuando mejore la claridad
- Sé breve y directo: prioriza claridad sobre detalle
- Evita redundancias y explicaciones innecesarias
---

{ctx}

{"=== HISTORIAL ===" + chr(10) + historial_texto if historial_texto else ""}

=== CONSULTA ===
{pregunta}
"""
    respuesta_ia = _llamar_gemini(prompt, max_tokens=4000)
    if respuesta_ia:
        respuesta = respuesta_ia.strip()

        if len(respuesta) > 4000:
            respuesta = respuesta[:4000] + "\n\n⚠️ Respuesta resumida por límite de longitud."

        return respuesta, True
 
    return _responder_local(proyecto, analisis, pregunta), False
 
 
# ─────────────────────────────────────────────────────────────────────────────
# FALLBACK LOCAL — STORYTELLING
# ─────────────────────────────────────────────────────────────────────────────
def _generar_storytelling_local(proyecto: dict, analisis: dict) -> str:
    a      = analisis
    info   = proyecto["info"]
    avance = a["avance"]
 
    texto = (
        f"## 🗂️ ANÁLISIS EJECUTIVO — {info['nombre'].upper()}\n\n"
        f"**Fecha:** {date.today().strftime('%d/%m/%Y')}  |  "
        f"**Avance:** {avance}%  |  **Riesgo:** {a['riesgo']}  |  "
        f"**Proyección:** {a['proyeccion']}\n\n---\n\n"
    )
 
    texto += "## 📋 RESUMEN\n"
    texto += (
        f"El proyecto registra **{avance}% de avance** sobre {len(proyecto['tareas'])} tareas totales. "
        f"{len(a['completadas'])} completadas, {len(a['en_progreso'])} en ejecución y "
        f"{len(a['atrasadas'])} con retraso. Nivel de riesgo: **{a['riesgo']}**.\n\n"
    )

    texto += "## ⚡ IMPACTO\n"
    if a["atrasadas"]:
        for t in a["atrasadas"][:3]:
            hitos_txt = _resumen_hitos(t).replace(" | ", " · ") if t.get("hitos") else ""
            texto += f"- **{t['nombre']}** ({t.get('recurso','—')}, {calcular_avance_tarea(t)}%{hitos_txt}) — retraso activo con impacto en plazo.\n"
    criticas = [t for t in a["en_progreso"] if calcular_avance_tarea(t) < 40]
    for t in criticas[:2]:
        texto += f"- **{t['nombre']}** con {calcular_avance_tarea(t)}% de avance — riesgo de convertirse en tarea crítica.\n"
    if not a["atrasadas"] and not criticas:
        texto += "- Sin impactos críticos identificados en el período actual.\n"
    texto += "\n"

    texto += "## ⚠️ RIESGOS\n"
    texto += f"- Recurso con mayor carga: **{a['recurso_critico']}** — riesgo de sobrecarga operacional.\n"
    texto += f"- Área crítica: **{a['area_critica']}** — concentración de tareas pendientes.\n"
    for area, datos in a["rendimiento_areas"].items():
        if datos["atrasadas"] > 0:
            texto += f"- Área **{area}**: {datos['atrasadas']} tarea(s) atrasada(s), avance promedio {datos['avance_promedio']}%.\n"
    texto += "\n"

    texto += "## ✅ ACCIONES\n"
    if a["riesgo"] == "🔴 Alto":
        texto += (
            f"- **{a['recurso_critico']}** — Revisar y redistribuir carga de tareas críticas — Reducir retrasos activos — Esta semana.\n"
            "- **Jefatura** — Convocar reunión de seguimiento de emergencia — Alinear al equipo sobre estado real — Hoy.\n"
            "- **Planificación** — Evaluar reducción de alcance en tareas no críticas — Liberar capacidad operacional — 48 horas.\n"
            "- **Equipo** — Activar reporte diario de avance por tarea — Visibilidad en tiempo real — Inmediato.\n\n"
        )
    elif a["riesgo"] == "🟡 Medio":
        texto += (
            f"- **{a['recurso_critico']}** — Revisar distribución de tareas asignadas — Equilibrar carga de trabajo — Esta semana.\n"
            f"- **Jefatura de {a['area_critica']}** — Realizar seguimiento cada 48 horas — Prevenir nuevos retrasos — Inmediato.\n"
            "- **Planificación** — Adelantar inicio de tareas sin dependencias bloqueantes — Ganar margen de plazo — Esta semana.\n"
            "- **Equipo** — Definir hitos intermedios para las próximas 2 semanas — Mayor control de avance — 3 días.\n\n"
        )
    else:
        texto += (
            "- **Equipo** — Mantener ritmo de ejecución actual — Consolidar avance — Continuo.\n"
            "- **Planificación** — Anticipar inicio de tareas pendientes sin dependencias — Reducir riesgo futuro — Esta semana.\n"
            "- **Jefatura** — Confirmar fechas de entrega con cada responsable — Asegurar cumplimiento — 48 horas.\n"
            "- **Comunicaciones** — Informar estado positivo del proyecto a stakeholders — Alinear expectativas — Esta semana.\n\n"
        )

    texto += f"**Proyección de cierre:** {a['proyeccion']}.\n\n"
    texto += "---\n_⚠️ Análisis local — configura `GEMINI_API_KEY` en `.env` para activar análisis con IA._\n"
    return texto
 
 
# ─────────────────────────────────────────────────────────────────────────────
# FALLBACK LOCAL — CHAT
# ─────────────────────────────────────────────────────────────────────────────
def _responder_local(proyecto: dict, analisis: dict, pregunta: str) -> str:
    p = pregunta.lower().strip()
    a = analisis
 
    if any(x in p for x in ["riesgo", "peligro", "crítico", "critico", "alerta", "mayor riesgo"]):
        detalle = (f" Tareas atrasadas: {', '.join(t['nombre'] for t in a['atrasadas'])}."
                   if a["atrasadas"] else "")
        return f"Riesgo **{a['riesgo']}**.{detalle} Avance: {a['avance']}%."
 
    if any(x in p for x in ["avance", "progreso", "porcentaje", "cuánto", "cuanto"]):
        return (f"**{a['avance']}% de avance**. "
                f"{len(a['completadas'])} completadas · {len(a['en_progreso'])} en progreso · "
                f"{len(a['atrasadas'])} atrasadas · {len(a['pendientes'])} pendientes.")
 
    if any(x in p for x in ["proyecc", "plazo", "terminar", "fecha", "cierre", "llegamos", "llegamos a tiempo"]):
        return f"Proyección: **{a['proyeccion']}**. Avance actual: {a['avance']}%."
 
    if any(x in p for x in ["atras", "retras", "vencid", "demor"]):
        if a["atrasadas"]:
            return "Tareas atrasadas:\n" + "\n".join(
                f"- **{t['nombre']}** ({t.get('recurso','—')}, {calcular_avance_tarea(t)}%)"
                for t in a["atrasadas"])
        return "✅ No hay tareas atrasadas."
 
    if any(x in p for x in ["hito", "milestone", "checkpoint"]):
        tareas_h = [t for t in proyecto["tareas"] if t.get("hitos")]
        if not tareas_h:
            return "ℹ️ Este proyecto no tiene tareas con hitos definidos."
        lineas = []
        for t in tareas_h:
            comp  = sum(1 for h in t["hitos"] if h.get("completado"))
            total = len(t["hitos"])
            pct   = round(comp / total * 100)
            lineas.append(f"- **{t['nombre']}**: {comp}/{total} hitos ({pct}%)")
        return "**Estado de hitos por tarea:**\n" + "\n".join(lineas)

    if any(x in p for x in ["tarea", "crítica", "critica", "importante", "prioridad"]):
        if a["atrasadas"]:
            t = a["atrasadas"][0]
            return (f"Tarea más crítica: **{t['nombre']}** — {t.get('recurso','—')}, "
                    f"{calcular_avance_tarea(t)}% de avance, estado: Atrasada.")
        if a["en_progreso"]:
            candidatas = sorted(a["en_progreso"], key=calcular_avance_tarea)
            t = candidatas[0]
            return (f"Tarea con menor avance en ejecución: **{t['nombre']}** — "
                    f"{t.get('recurso','—')}, {calcular_avance_tarea(t)}%.")
        return "✅ No hay tareas en estado crítico."

    for w, d in a["rendimiento_trabajadores"].items():
        if w.lower() in p:
            estado = ("🔴 con retrasos" if d["atrasadas"] > 0
                      else ("🟢 al día" if d["avance_promedio"] >= 75 else "🟡 en progreso"))
            return (f"**{w}**: {d['total']} tarea(s) · avance {d['avance_promedio']}% · {estado}. "
                    f"Tareas: {', '.join(d['tareas'])}.")
 
    if any(x in p for x in ["trabajador", "equipo", "recurso", "rendimiento", "persona", "quien", "quién"]):
        lineas = []
        for w, d in a["rendimiento_trabajadores"].items():
            icono = "🔴" if d["atrasadas"] > 0 else ("🟢" if d["avance_promedio"] >= 75 else "🟡")
            lineas.append(f"{icono} **{w}**: {d['avance_promedio']}% · {d['total']} tareas"
                          + (f" · ⚠️ {d['atrasadas']} atrasada(s)" if d["atrasadas"] > 0 else ""))
        return "**Equipo:**\n" + "\n".join(lineas)
 
    if any(x in p for x in ["cuello", "bloqueo", "bottleneck", "sobrecarg"]):
        n = len(a["carga_recursos"].get(a["recurso_critico"], []))
        return (f"Cuello de botella: área **{a['area_critica']}** · "
                f"recurso más cargado **{a['recurso_critico']}** ({n} tareas).")
 
    if any(x in p for x in ["hacer", "recomiend", "acción", "accion", "prior", "siguiente"]):
        if a["riesgo"] == "🔴 Alto":
            return "🔴 Convocar reunión de seguimiento, reasignar recursos críticos y activar reporte diario de avance."
        elif a["riesgo"] == "🟡 Medio":
            return f"🟡 Apoyar a **{a['recurso_critico']}**, monitorear **{a['area_critica']}** con seguimiento cada 48 horas."
        return "🟢 Mantener ritmo de ejecución y anticipar inicio de tareas pendientes."
 
    sugerencias = [
        "¿Cuál es el riesgo del proyecto?",
        "¿Cómo va el avance?",
        "¿Qué tareas están atrasadas?",
        "¿Llegamos a tiempo?",
        "¿Qué tarea es más crítica?",
        "¿Dónde está el mayor riesgo?",
        "¿Cómo está el rendimiento del equipo?",
    ]
    return "Puedo responder sobre:\n" + "\n".join(f"- *{s}*" for s in sugerencias)
 
 
# ─────────────────────────────────────────────────────────────────────────────
# HELPER: CAJA DE ALERTA DINÁMICA
# ─────────────────────────────────────────────────────────────────────────────
def _render_alerta_ejecutiva(analisis: dict, proyecto: dict) -> None:
    """Muestra una caja de alerta interpretativa en el dashboard."""
    a = analisis

    if a["riesgo"] == "🔴 Alto":
        tarea_nombre = a["atrasadas"][0]["nombre"] if a["atrasadas"] else "múltiples tareas"
        responsable  = a["atrasadas"][0].get("recurso", a["recurso_critico"]) if a["atrasadas"] else a["recurso_critico"]
        color, icono, titulo = "#ef4444", "🔴", "PROYECTO EN RIESGO CRÍTICO"
        mensaje = (
            f"El atraso en <strong>{tarea_nombre}</strong> "
            f"(resp. {responsable}) compromete el plazo de entrega. "
            f"Avance actual: <strong>{a['avance']}%</strong> — se requiere intervención inmediata."
        )
    elif a["riesgo"] == "🟡 Medio":
        tarea_nombre = a["atrasadas"][0]["nombre"] if a["atrasadas"] else a["area_critica"]
        color, icono, titulo = "#f59e0b", "🟡", "PROYECTO CON ALERTAS ACTIVAS"
        mensaje = (
            f"<strong>{tarea_nombre}</strong> presenta desviación respecto al plan base. "
            f"Avance: <strong>{a['avance']}%</strong> — monitoreo estrecho recomendado."
        )
    else:
        color, icono, titulo = "#22c55e", "🟢", "PROYECTO EN PLAZO"
        mensaje = (
            f"Ejecución dentro de parámetros esperados. "
            f"Avance: <strong>{a['avance']}%</strong> — {len(a['completadas'])} tareas completadas."
        )

    st.markdown(
        f"""
        <div style="
            border-left: 4px solid {color};
            background: rgba(255,255,255,0.04);
            border-radius: 6px;
            padding: 0.85rem 1.1rem;
            margin-bottom: 1rem;
        ">
            <div style="font-weight:700; color:{color}; font-size:0.8rem; letter-spacing:0.05em; margin-bottom:0.3rem;">
                {icono} {titulo}
            </div>
            <div style="color:#141414; font-size:0.9rem; line-height:1.5;">
                {mensaje}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA STREAMLIT
# ─────────────────────────────────────────────────────────────────────────────
def pagina_storytelling():
    # ── Encabezado con mensaje de valor ──────────────────────────────────────
    st.markdown("## 🧠 Análisis Inteligente con IA")
    st.markdown(
        "> **Detecta riesgos, atrasos y toma decisiones en proyectos automáticamente con IA.**"
    )

    proyecto = get_proyecto()
 
    if not proyecto:
        st.markdown("""
            <div class="card" style="text-align:center; padding: 2.5rem;">
                <div style="font-size:3rem; margin-bottom:1rem;">🧠</div>
                <h3 style="color:#f0f9ff !important;">No hay proyecto seleccionado</h3>
                <p style="color:#94a3b8;">El análisis IA necesita un proyecto activo con tareas para generar insights.</p>
                <br>
                <p style="color:#64748b; font-size:0.85rem;">
                    1. Ve a <strong style="color:#38bdf8;">➕ Nuevo Proyecto</strong> para crear uno.<br>
                    2. O selecciona un proyecto existente desde el <strong style="color:#38bdf8;">menú lateral</strong>.
                </p>
            </div>
        """, unsafe_allow_html=True)
        return
 
    if not proyecto["tareas"]:
        st.markdown("""
            <div class="card" style="text-align:center; padding: 2rem;">
                <div style="font-size:2.5rem; margin-bottom:0.75rem;">🤖</div>
                <h4 style="color:#f0f9ff !important;">Sin tareas para analizar</h4>
                <p style="color:#94a3b8;">La IA necesita al menos una tarea registrada para generar el análisis.</p>
                <p style="color:#64748b; font-size:0.85rem;">Ve a <strong style="color:#38bdf8;">➕ Nuevo Proyecto</strong> y agrega tareas primero.</p>
            </div>
        """, unsafe_allow_html=True)
        return
 
    st.markdown("---")

    # ── Métricas + alerta ejecutiva ───────────────────────────────────────────
    analisis = analizar_proyecto(proyecto)

    _render_alerta_ejecutiva(analisis, proyecto)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📊 Avance total", f"{analisis['avance']}%")
    col2.metric("✅ Completadas",  len(analisis["completadas"]))
    col3.metric("⚠️ Atrasadas",    len(analisis["atrasadas"]))
    col4.metric("🔮 Proyección",   analisis["proyeccion"].split(" ", 1)[-1])
 
    st.markdown("---")
 
    # ── Análisis ejecutivo ────────────────────────────────────────────────────
    st.markdown("### 📋 Análisis ejecutivo")
    tiene_key = bool(GEMINI_API_KEY)
    if tiene_key:
        st.success("✨ Modo IA activo — análisis generado con Gemini 2.5 Flash", icon="🤖")
    else:
        st.warning(
            "⚠️ Modo local activo — agrega `GEMINI_API_KEY` en tu `.env` para activar IA real.",
            icon="🔑"
        )
 
    if st.button("🚀 Generar análisis", use_container_width=True, type="primary"):
        with st.spinner("Consultando Gemini AI..." if tiene_key else "Analizando proyecto..."):
            texto, usado_ia = generar_storytelling(proyecto)
        st.session_state["ultimo_analisis"]    = texto
        st.session_state["ultimo_analisis_ia"] = usado_ia
 
    if "ultimo_analisis" in st.session_state:
        if st.session_state.get("ultimo_analisis_ia"):
            st.info("🤖 Generado con Gemini AI", icon="✨")
        else:
            st.caption("📋 Análisis generado localmente")
        st.markdown(st.session_state["ultimo_analisis"])
        if st.button("🔄 Regenerar análisis"):
            del st.session_state["ultimo_analisis"]
            del st.session_state["ultimo_analisis_ia"]
            st.rerun()
 
    st.markdown("---")
 
    # ── Chat con IA ───────────────────────────────────────────────────────────
    st.markdown("### 💬 Consulta al asistente")
    st.markdown(
        "Realiza consultas sobre el estado del proyecto, tareas críticas, "
        "equipo o recomendaciones de acción."
    )
 
    if "chat_historial" not in st.session_state:
        st.session_state["chat_historial"] = []
 
    # ── Botones de preguntas rápidas (actualizados) ───────────────────────────
    st.markdown("**💡 Consultas frecuentes:**")
    sugerencias = [
        "¿Qué tarea es más crítica?",
        "¿Llegamos a tiempo?",
        "¿Dónde está el mayor riesgo?",
        "¿Quién está más retrasado?",
        "¿Cómo van los hitos?",
        "¿Qué debo hacer primero?",
    ]
    # Primera fila: 3 botones
    cols1 = st.columns(3)
    for i in range(3):
        if cols1[i].button(sugerencias[i], key=f"sug_{i}", use_container_width=True):
            st.session_state["pregunta_rapida"] = sugerencias[i]
    # Segunda fila: 3 botones
    cols2 = st.columns(3)
    for i in range(3, 6):
        if cols2[i - 3].button(sugerencias[i], key=f"sug_{i}", use_container_width=True):
            st.session_state["pregunta_rapida"] = sugerencias[i]

    st.markdown("")
 
    for msg in st.session_state["chat_historial"]:
        with st.chat_message("user" if msg["rol"] == "usuario" else "assistant"):
            st.markdown(msg["texto"])
            if msg.get("usado_ia") is False:
                st.caption("📋 Respuesta local")
 
    pregunta_a_procesar = None
    if "pregunta_rapida" in st.session_state:
        pregunta_a_procesar = st.session_state.pop("pregunta_rapida")
 
    if pregunta_input := st.chat_input("Ej: ¿Cuál es la tarea más crítica? ¿Llegamos a tiempo?"):
        pregunta_a_procesar = pregunta_input
 
    if pregunta_a_procesar:
        with st.chat_message("user"):
            st.markdown(pregunta_a_procesar)
        st.session_state["chat_historial"].append({
            "rol": "usuario",
            "texto": pregunta_a_procesar,
        })
        with st.chat_message("assistant"):
            with st.spinner("Consultando Gemini..." if tiene_key else "Procesando..."):
                respuesta, usado_ia = responder_pregunta(
                    proyecto,
                    pregunta_a_procesar,
                    historial=st.session_state["chat_historial"][:-1],
                )
            st.markdown(respuesta)
            if not usado_ia:
                st.caption("📋 Respuesta local")
        st.session_state["chat_historial"].append({
            "rol": "asistente",
            "texto": respuesta,
            "usado_ia": usado_ia,
        })
        st.rerun()
 
    if st.session_state["chat_historial"]:
        st.markdown("")
        if st.button("🗑️ Limpiar conversación"):
            st.session_state["chat_historial"] = []
            st.rerun()