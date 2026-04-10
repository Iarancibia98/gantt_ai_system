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
    avance = avance_total_proyecto(tareas)   # ya usa calcular_avance_tarea internamente
 
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
        # ← calcular_avance_tarea respeta hitos si existen
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
        # ← calcular_avance_tarea respeta hitos si existen
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
    """Devuelve '2/4 hitos' si la tarea tiene hitos, cadena vacía si no."""
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

    # 🔥 SOLO tareas críticas (esto evita que Gemini se sature)
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
 
    prompt = f"""Eres consultor senior de proyectos. Analiza y responde en español.
 
{ctx}
 
Responde con estas 3 secciones. Sé directo, usa datos concretos, sin rodeos:
 
## 📍 SITUACIÓN
Estado actual en máximo 60 palabras. Incluye % avance global, tareas completadas/total y días restantes.
 
## ⚡ COMPLICACIÓN
Problemas reales con nombres de tareas/personas. Para cada tarea en riesgo calcula:
avance actual vs avance esperado (días transcurridos / días totales * 100).
Si hay tareas con hitos, menciona cuántos hitos pendientes quedan.
Máximo 60 palabras.
 
## 🎯 PLAN DE ACCIÓN
4 acciones concretas para esta semana (bullets con verbo imperativo).
Para cada acción indica: persona responsable + tarea + resultado esperado.
Al final agrega una línea: "Proyección de cierre: [En plazo / En riesgo / Crítico] porque [razón en 1 frase]."
"""
    respuesta_ia = _llamar_gemini(prompt, max_tokens=3000)
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
 
    prompt = f"""Actúa como JEFE DE PLANIFICACIÓN DE MINA en una operación activa.

Tu rol:
- Controlar cumplimiento del programa de producción
- Detectar desviaciones de avance
- Evaluar riesgos operacionales (ventilación, tronadura, transporte, mantenimiento)
- Tomar decisiones con números concretos

REGLAS TÉCNICAS (NO ROMPER):
- Usa datos reales del proyecto (%, fechas, responsables)
- Calcula cuando aplique:
  avance requerido diario = (100 - avance_actual) / días_restantes
- Si días_restantes <= 0 → tarea no viable
- Si hay hitos → usa el % real basado en hitos
- Prioriza continuidad operacional (producción > teoría)

REGLAS DE ESTILO (MUY IMPORTANTE):
- Responde como si estuvieras hablando con un jefe de turno o gerente
- Usa lenguaje natural, fluido, no formato tabla rígido
- Puedes usar bullets, pero que se lean como conversación
- Explica primero la situación, luego el impacto, luego qué hacer
- Usa frases como:
  "Mira", "Hoy tenemos un problema", "Si no hacemos esto", "Esto pega directo en..."
- Evita lenguaje robótico o excesivamente estructurado
- NO escribas títulos como "Explica la situación actual" o similares
- Integra todo como narrativa continua, como conversación real

FORMATO DE RESPUESTA:

1. Explica la situación actual (en lenguaje natural, con datos)
2. Explica qué va a pasar si no se actúa (impacto real en producción o seguridad)
3. Acciones concretas (máx 4–5, claras y directas)
4. Veredicto final en una línea
5. Termina SIEMPRE con una frase tipo decisión:
  "Decisión recomendada: ..."

REGLA FINAL:
- Si debes resumir, reduce análisis, NO las acciones

---

{ctx}

{"=== HISTORIAL ===" + chr(10) + historial_texto if historial_texto else ""}

=== PREGUNTA ===
{pregunta}

Responde directo, claro y como en una conversación de operación minera.


{ctx}

PREGUNTA:
{pregunta}
"""
    respuesta_ia = _llamar_gemini(prompt, max_tokens=6000)
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
 
    texto += "## 📍 ACTO 1 — SITUACIÓN\n"
    texto += (
        f"El proyecto tiene **{len(proyecto['tareas'])} tareas**: "
        f"{len(a['completadas'])} completadas, {len(a['en_progreso'])} en progreso, "
        f"{len(a['atrasadas'])} atrasadas y {len(a['pendientes'])} pendientes. "
        f"Avance global: **{avance}%** — Riesgo **{a['riesgo']}**.\n\n"
    )
    for area, datos in a["rendimiento_areas"].items():
        icono = "🔴" if datos["atrasadas"] > 0 else ("🟡" if datos["avance_promedio"] < 60 else "🟢")
        texto += f"- {icono} **{area}**: {datos['avance_promedio']}% avance"
        if datos["atrasadas"]:
            texto += f" · {datos['atrasadas']} atrasada(s)"
        texto += "\n"
    texto += "\n"
 
    texto += "## ⚡ ACTO 2 — COMPLICACIÓN\n"
    if a["atrasadas"]:
        texto += "**Tareas con retraso:**\n"
        for t in a["atrasadas"]:
            hitos_txt = _resumen_hitos(t).replace(" | ", " · ") if t.get("hitos") else ""
            texto += f"- 🔴 **{t['nombre']}** ({t.get('recurso','—')}, {calcular_avance_tarea(t)}%{hitos_txt})\n"
        texto += "\n"
    criticas = [t for t in a["en_progreso"] if calcular_avance_tarea(t) < 40]
    if criticas:
        texto += "**Avance lento (< 40%):**\n"
        for t in criticas:
            hitos_txt = _resumen_hitos(t).replace(" | ", " · ") if t.get("hitos") else ""
            texto += f"- 🟡 **{t['nombre']}** — {calcular_avance_tarea(t)}%{hitos_txt}\n"
        texto += "\n"
    texto += f"**Recurso más cargado:** {a['recurso_critico']} · **Área crítica:** {a['area_critica']}\n\n"
    texto += "**Rendimiento por trabajador:**\n"
    for w, d in a["rendimiento_trabajadores"].items():
        icono = "🔴" if d["atrasadas"] > 0 else ("🟢" if d["avance_promedio"] >= 75 else "🟡")
        texto += f"- {icono} **{w}**: {d['avance_promedio']}% · {d['total']} tareas"
        if d["atrasadas"]:
            texto += f" · ⚠️ {d['atrasadas']} atrasada(s)"
        texto += "\n"
    texto += "\n"
 
    texto += "## 🎯 ACTO 3 — PLAN DE ACCIÓN\n"
    if a["riesgo"] == "🔴 Alto":
        texto += (
            "1. 🚨 **Convocar reunión de crisis** con responsables de tareas atrasadas.\n"
            "2. 🔄 **Reasignar recursos** hacia tareas críticas inmediatamente.\n"
            "3. 📋 **Revisar alcance**: evaluar qué puede simplificarse o postergarse.\n"
            "4. 📊 **Activar reporte diario** de avance hasta estabilizar.\n\n"
        )
    elif a["riesgo"] == "🟡 Medio":
        texto += (
            f"1. ⚡ **Apoyar a {a['recurso_critico']}**: revisar y redistribuir su carga.\n"
            f"2. 🔍 **Check-in cada 2 días** en {a['area_critica']}.\n"
            "3. 📅 **Adelantar tareas pendientes** sin dependencias bloqueantes.\n"
            "4. 🎯 **Definir hitos intermedios** para las próximas 2 semanas.\n\n"
        )
    else:
        texto += (
            "1. ✅ **Mantener el ritmo** — el equipo está ejecutando bien.\n"
            "2. 📈 **Anticipar tareas pendientes** antes de su fecha.\n"
            "3. 🔭 **Confirmar fechas de entrega** con cada responsable.\n"
            "4. 📣 **Comunicar el buen estado** al equipo y stakeholders.\n\n"
        )
    texto += f"**Proyección:** {a['proyeccion']}.\n\n"
    texto += "---\n_⚠️ Análisis local — configura `GEMINI_API_KEY` en `.env` para IA real._\n"
    return texto
 
 
# ─────────────────────────────────────────────────────────────────────────────
# FALLBACK LOCAL — CHAT
# ─────────────────────────────────────────────────────────────────────────────
def _responder_local(proyecto: dict, analisis: dict, pregunta: str) -> str:
    p = pregunta.lower().strip()
    a = analisis
 
    if any(x in p for x in ["riesgo", "peligro", "crítico", "critico", "alerta"]):
        detalle = (f" Tareas atrasadas: {', '.join(t['nombre'] for t in a['atrasadas'])}."
                   if a["atrasadas"] else "")
        return f"Riesgo **{a['riesgo']}**.{detalle} Avance: {a['avance']}%."
 
    if any(x in p for x in ["avance", "progreso", "porcentaje", "cuánto", "cuanto"]):
        return (f"**{a['avance']}% de avance**. "
                f"{len(a['completadas'])} completadas · {len(a['en_progreso'])} en progreso · "
                f"{len(a['atrasadas'])} atrasadas · {len(a['pendientes'])} pendientes.")
 
    if any(x in p for x in ["proyecc", "plazo", "terminar", "fecha", "cierre"]):
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
            return "🔴 Reunión de crisis hoy, reasignar recursos y activar reporte diario."
        elif a["riesgo"] == "🟡 Medio":
            return f"🟡 Apoyar a **{a['recurso_critico']}**, monitorear **{a['area_critica']}** cada 2 días."
        return "🟢 Mantén el ritmo y anticipa tareas pendientes."
 
    sugerencias = [
        "¿Cuál es el riesgo del proyecto?",
        "¿Cómo va el avance?",
        "¿Qué tareas están atrasadas?",
        "¿Cuál es la proyección de cierre?",
        "¿Cómo está el rendimiento del equipo?",
        "¿Cómo van los hitos?",
        "¿Qué debería hacer primero?",
    ]
    return "Puedo responder sobre:\n" + "\n".join(f"- *{s}*" for s in sugerencias)
 
 
# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA STREAMLIT
# ─────────────────────────────────────────────────────────────────────────────
def pagina_storytelling():
    st.markdown("## 🧠 Análisis Inteligente con IA")
    st.markdown(
        "Obtén interpretación automática del estado de tu proyecto, "
        "riesgos y recomendaciones generadas con Gemini AI."
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
 
    analisis = analizar_proyecto(proyecto)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📊 Avance total", f"{analisis['avance']}%")
    col2.metric("✅ Completadas",  len(analisis["completadas"]))
    col3.metric("⚠️ Atrasadas",    len(analisis["atrasadas"]))
    col4.metric("🔮 Proyección",   analisis["proyeccion"].split(" ", 1)[-1])
 
    st.markdown("---")
 
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
 
    st.markdown("### 💬 Pregunta sobre tu proyecto")
    st.markdown(
        "Hazle preguntas al asistente sobre el estado del proyecto, "
        "trabajadores, tareas o recomendaciones."
    )
 
    if "chat_historial" not in st.session_state:
        st.session_state["chat_historial"] = []
 
    st.markdown("**💡 Preguntas frecuentes:**")
    sugerencias = [
        "¿Cuál es el riesgo del proyecto?",
        "¿Quién está más retrasado?",
        "¿Cómo van los hitos?",
        "¿Qué debo hacer primero?",
    ]
    cols = st.columns(len(sugerencias))
    for i, sug in enumerate(sugerencias):
        if cols[i].button(sug, key=f"sug_{i}", use_container_width=True):
            st.session_state["pregunta_rapida"] = sug
 
    st.markdown("")
 
    for msg in st.session_state["chat_historial"]:
        with st.chat_message("user" if msg["rol"] == "usuario" else "assistant"):
            st.markdown(msg["texto"])
            if msg.get("usado_ia") is False:
                st.caption("📋 Respuesta local")
 
    pregunta_a_procesar = None
    if "pregunta_rapida" in st.session_state:
        pregunta_a_procesar = st.session_state.pop("pregunta_rapida")
 
    if pregunta_input := st.chat_input("Ej: ¿Cómo va Jorge? ¿Cómo van los hitos?"):
        pregunta_a_procesar = pregunta_input
 
    if pregunta_a_procesar:
        with st.chat_message("user"):
            st.markdown(pregunta_a_procesar)
        st.session_state["chat_historial"].append({
            "rol": "usuario",
            "texto": pregunta_a_procesar,
        })
        with st.chat_message("assistant"):
            with st.spinner("Consultando Gemini..." if tiene_key else "Pensando..."):
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
 