"""Módulo CHECKLIST PREOPERACIONAL (MACGYVER)."""
from datetime import date, datetime

import streamlit as st

from checklist_data import CRITICOS, ITEMS, NA_IDS, NA_NUMERALES, PANTALLAS, TITULOS
from checklist_pdf import dias_habiles, evaluar, generar_informe_pdf

REGIMENES = ["Nuevo RUS", "Régimen Especial (RER)", "Régimen MYPE Tributario", "Régimen General"]
OPC = {"Cumple": "ok", "No cumple": "no", "No aplica": "na"}
INV = {v: k for k, v in OPC.items()}


def _num(iid):
    return int(iid.split(".")[0])


def _na_ok(iid):
    return str(_num(iid)) in NA_NUMERALES or iid in NA_IDS


def _items_pantalla(p):
    nums = PANTALLAS[p][1]
    return [i for i in ITEMS if _num(i[0]) in nums]


def _guardar(sb, extra=None):
    ss = st.session_state
    datos = {"respuestas": ss.cl_ans, "pantalla": ss.cl_pant}
    if extra:
        datos.update(extra)
    sb.table("checklists").update(datos).eq("codigo", ss.cl_codigo).execute()


# ---------------------------------------------------------------- datos
def _datos(sb):
    ss = st.session_state
    st.markdown("Completa los datos de tu empresa para comenzar. Son **142 criterios** en "
                f"**{len(PANTALLAS)} pantallas**. Tu avance se guarda al continuar: si cierras la página, "
                "vuelve a entrar con tu código y tu RUC.")
    codigo = st.text_input("Código de acceso").strip().upper()
    empresa = st.text_input("Empresa").strip()
    ruc = st.text_input("RUC").strip()
    proyecto = st.text_input("Proyecto").strip()
    trab = st.text_input("Cantidad de trabajadores").strip()
    regimen = st.selectbox("Régimen tributario", REGIMENES)
    responsable = st.text_input("Responsable que llena el checklist").strip()
    cargo = st.text_input("Cargo").strip()
    whatsapp = st.text_input("Número de WhatsApp").strip()

    if not st.button("Comenzar checklist"):
        return
    if not all([codigo, empresa, ruc, proyecto, trab, responsable, cargo, whatsapp]):
        st.warning("Completa todos los campos.")
        return
    if not (ruc.isdigit() and len(ruc) == 11):
        st.warning("El RUC debe tener 11 números.")
        return
    if not (trab.isdigit() and int(trab) > 0):
        st.warning("La cantidad de trabajadores debe ser un número mayor que cero.")
        return

    cod = sb.table("codigos").select("*").eq("codigo", codigo).execute().data
    if not cod:
        st.error("Código no válido.")
        return
    fila = sb.table("checklists").select("*").eq("codigo", codigo).execute().data
    if fila:
        fila = fila[0]
        if str(fila["ruc"]) != ruc:
            st.error("Este código ya fue usado por otra empresa.")
            return
    else:
        if cod[0]["usado"]:
            st.error("Este código ya fue usado.")
            return
        sb.table("checklists").insert({
            "codigo": codigo, "ruc": ruc, "empresa": empresa, "proyecto": proyecto,
            "trabajadores": int(trab), "regimen": regimen, "responsable": responsable,
            "cargo": cargo, "whatsapp": whatsapp, "respuestas": {}, "pantalla": 0,
        }).execute()
        sb.table("codigos").update({
            "usado": True, "alumno": empresa, "dni": ruc, "empresa": empresa,
            "proyecto": proyecto, "cargo": cargo, "whatsapp": whatsapp,
        }).eq("codigo", codigo).execute()
        fila = {"respuestas": {}, "pantalla": 0, "finalizado": False}

    ss.cl_codigo = codigo
    ss.cl_ans = dict(fila.get("respuestas") or {})
    ss.cl_pant = min(int(fila.get("pantalla") or 0), len(PANTALLAS) - 1)
    ss.cl_etapa = "fin" if fila.get("finalizado") else "check"
    st.rerun()


# ---------------------------------------------------------------- pantallas
def _pantalla(sb, ahora):
    ss = st.session_state
    p = ss.cl_pant
    nombre, _ = PANTALLAS[p]
    st.progress(p / len(PANTALLAS))
    st.caption(f"Pantalla {p + 1} de {len(PANTALLAS)}")
    st.markdown(f"### {nombre}")
    if p > 0 and st.button("← Pantalla anterior"):
        ss.cl_pant -= 1
        st.rerun()

    vals, actual = {}, None
    with st.form(f"cl_form_{p}"):
        for iid, texto, norma in _items_pantalla(p):
            if _num(iid) != actual:
                actual = _num(iid)
                st.markdown(f"**{actual}. {TITULOS[actual]}**")
            opciones = ["Cumple", "No cumple"] + (["No aplica"] if _na_ok(iid) else [])
            previo = INV.get(ss.cl_ans.get(iid))
            idx = opciones.index(previo) if previo in opciones else None
            etiqueta = f"**{iid}** · {texto}" + ("  :red[**CRÍTICO**]" if iid in CRITICOS else "")
            vals[iid] = st.radio(etiqueta, opciones, index=idx, horizontal=True,
                                 key=f"cl_{iid}", help="Requisito normativo: " + norma)
        ultimo = p == len(PANTALLAS) - 1
        enviar = st.form_submit_button("Finalizar y generar informe" if ultimo else "Guardar y continuar")

    if not enviar:
        return
    faltan = [i for i, v in vals.items() if v is None]
    if faltan:
        st.warning(f"Faltan {len(faltan)} criterios por responder: {', '.join(faltan)}")
        return
    ss.cl_ans.update({i: OPC[v] for i, v in vals.items()})
    if not ultimo:
        ss.cl_pant = p + 1
        _guardar(sb)
        st.rerun()
    ev = evaluar(ss.cl_ans)
    hoy = ahora()
    _guardar(sb, {
        "finalizado": True, "porcentaje": ev["pct"], "veredicto": ev["ver"],
        "informe_codigo": f"PRE-{ss.cl_codigo.replace('-', '')}-{hoy.strftime('%d%m')}",
        "fecha_limite": dias_habiles(hoy.date(), 7).isoformat() if ev["ver"] == "REG" else None,
        "finalizado_en": hoy.isoformat(timespec="seconds"),
    })
    ss.cl_etapa = "fin"
    st.rerun()


# ---------------------------------------------------------------- resultado
def _final(sb, base_url):
    ss = st.session_state
    r = sb.table("checklists").select("*").eq("codigo", ss.cl_codigo).execute().data[0]
    fl = r.get("fecha_limite")
    dat = {
        "empresa": r["empresa"], "ruc": r["ruc"], "proyecto": r["proyecto"],
        "trabajadores": r["trabajadores"], "regimen": r["regimen"],
        "responsable": r["responsable"], "cargo": r["cargo"],
        "fecha": datetime.fromisoformat(str(r["finalizado_en"])[:19]),
        "codigo_informe": r["informe_codigo"],
        "fecha_limite": date.fromisoformat(str(fl)[:10]) if fl else None,
    }
    if ss.get("cl_pdf_cod") != r["informe_codigo"]:
        ss.cl_pdf, ss.cl_ev = generar_informe_pdf(dat, r["respuestas"] or {}, base_url)
        ss.cl_pdf_cod = r["informe_codigo"]
    ev = ss.cl_ev
    st.progress(1.0)
    st.markdown(f"### Resultado: {ev['pct']:.1f} % de cumplimiento".replace(".", ","))
    if ev["ver"] == "NO":
        st.error("**NO INICIAR TRABAJOS.** " + (
            "Existe al menos un criterio crítico incumplido." if ev["crit"]
            else "El cumplimiento es menor al 80 %."))
    elif ev["ver"] == "REG":
        st.warning("**PUEDE INICIAR TRABAJOS, REGULARIZANDO EN 7 DÍAS HÁBILES.** "
                   f"Fecha límite: {dat['fecha_limite'].strftime('%d/%m/%Y')}.")
    else:
        st.success("**CONFORME.** Cumple todos los criterios aplicables.")
    st.write(f"{ev['ok']} de {ev['ap']} criterios aplicables cumplen. Por regularizar: {len(ev['fallas'])}.")
    st.download_button("Descargar informe de inspección pre-operativa (PDF)", data=ss.cl_pdf,
                       file_name=f"informe_preoperacional_{r['informe_codigo']}.pdf",
                       mime="application/pdf")
    st.caption("Diagnóstico elaborado por MACGYVER SEGURIDAD EN CONSTRUCCIÓN. "
               "Basado en información declarada por el usuario.")


# ---------------------------------------------------------------- entrada
def mostrar_checklist(sb, ahora, base_url):
    ss = st.session_state
    for k, v in {"cl_etapa": "datos", "cl_pant": 0, "cl_ans": {}, "cl_codigo": None}.items():
        ss.setdefault(k, v)
    if st.query_params.get("m") == "menu" and st.button("← Volver al menú"):
        ss.vista = "portada"
        st.rerun()
    st.subheader("Checklist preoperacional")
    st.caption("Verifica si tienes lo necesario para empezar tu proyecto")
    if ss.cl_etapa == "datos":
        _datos(sb)
    elif ss.cl_etapa == "check":
        _pantalla(sb, ahora)
    else:
        _final(sb, base_url)


def verificar_informe(sb, cod):
    r = (sb.table("checklists").select("empresa,proyecto,porcentaje,veredicto,finalizado_en,informe_codigo")
         .eq("informe_codigo", cod).eq("finalizado", True).limit(1).execute().data)
    if not r:
        st.error("Informe no válido o no encontrado.")
        return
    r = r[0]
    ver = {"NO": "No iniciar trabajos", "REG": "Puede iniciar, regularizando en 7 días hábiles", "OK": "Conforme"}
    st.success("✅ ESTE DIAGNÓSTICO FUE ELABORADO POR MACGYVER SEGURIDAD EN CONSTRUCCIÓN")
    st.markdown(f"**Empresa:** {r['empresa']}")
    st.markdown(f"**Proyecto:** {r['proyecto']}")
    st.markdown(f"**Cumplimiento:** {float(r['porcentaje']):.1f} %")
    st.markdown(f"**Resultado:** {ver.get(r['veredicto'], '')}")
    st.markdown(f"**Fecha:** {datetime.fromisoformat(str(r['finalizado_en'])[:19]).strftime('%d/%m/%Y')}")
    st.markdown(f"**Código de informe:** {r['informe_codigo']}")
