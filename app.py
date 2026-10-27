import streamlit as st
from datetime import datetime
from supabase import create_client

st.set_page_config(
    page_title="MACGYVER | Seguridad en Construcción",
    page_icon="logo.png",
    layout="centered",
)

st.markdown("""
<style>
    #MainMenu, footer, header {visibility: hidden;}
    .block-container {padding-top: 2rem; max-width: 760px;}
    .franja {
        height: 14px; margin: 8px 0 24px 0; border-radius: 3px;
        background: repeating-linear-gradient(
            -45deg, #FFD600, #FFD600 14px, #0A0A0A 14px, #0A0A0A 28px);
    }
    .stButton > button, .stFormSubmitButton > button {
        background-color: #FFD600; color: #0A0A0A; font-weight: 800;
        border: none; border-radius: 6px; padding: 0.6rem 1.4rem;
        text-transform: uppercase; width: 100%;
    }
    .stButton > button:hover, .stFormSubmitButton > button:hover {
        background-color: #FFFFFF; color: #0A0A0A;
    }
    h1, h2, h3 {font-weight: 800;}
    h2 {border-left: 6px solid #FFD600; padding-left: 12px;}
</style>
""", unsafe_allow_html=True)

NOTA_MINIMA = 70

PREGUNTAS = [
    {"p": "¿Qué significa SSOMA?",
     "o": ["Seguridad, Salud Ocupacional y Medio Ambiente",
           "Sistema de Salud y Obras",
           "Seguro Social de Obras"], "c": 0},
    {"p": "¿Cuál es el EPP básico obligatorio en obra?",
     "o": ["Solo guantes", "Casco, lentes y zapatos de seguridad", "Ninguno"], "c": 1},
    {"p": "Si ves un acto inseguro, ¿qué haces?",
     "o": ["Lo ignoro", "Lo reporto a mi supervisor", "Se lo cuento a un amigo"], "c": 1},
    {"p": "¿Para qué sirve el IPERC?",
     "o": ["Identificar peligros y evaluar riesgos", "Calcular sueldos", "Pedir materiales"], "c": 0},
    {"p": "En una emergencia, debes dirigirte a:",
     "o": ["El almacén", "El punto de reunión", "Tu casa"], "c": 1},
]

@st.cache_resource
def conectar():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

sb = conectar()

for clave, valor in {"acceso": False, "ya_vio": False, "enviado": False}.items():
    if clave not in st.session_state:
        st.session_state[clave] = valor

st.image("logo.png", use_container_width=True)
st.markdown('<div class="franja"></div>', unsafe_allow_html=True)

# ---------- Pantalla 1: Ingreso ----------
if not st.session_state.acceso:
    st.subheader("Ingreso al curso")
    nombre = st.text_input("Nombre completo").strip()
    correo = st.text_input("Correo").strip().lower()
    codigo = st.text_input("Código de acceso").strip().upper()

    if st.button("Ingresar"):
        if not nombre or not correo or not codigo:
            st.warning("Completa todos los campos.")
        else:
            res = sb.table("codigos").select("*").eq("codigo", codigo).execute().data
            if not res:
                st.error("Código no válido.")
            else:
                fila = res[0]
                usado = bool(fila["usado"])
                correo_guardado = str(fila.get("correo") or "").strip().lower()

                if usado and correo_guardado != correo:
                    st.error("Este código ya fue usado por otra persona.")
                else:
                    if not usado:
                        sb.table("codigos").update(
                            {"usado": True, "alumno": nombre, "correo": correo}
                        ).eq("codigo", codigo).execute()

                    previo = (sb.table("resultados").select("id")
                              .eq("codigo", codigo).execute().data)

                    st.session_state.acceso = True
                    st.session_state.enviado = bool(previo)
                    st.session_state.nombre = nombre
                    st.session_state.correo = correo
                    st.session_state.codigo = codigo
                    st.session_state.curso = fila["curso"]
                    st.session_state.inicio = datetime.now().isoformat(timespec="seconds")
                    st.rerun()

# ---------- Pantalla 2: Video + Examen ----------
else:
    st.success(f"Bienvenido, {st.session_state.nombre}")

    if st.session_state.enviado:
        st.success("Tu examen fue enviado. Será revisado y recibirás tu certificado.")
        st.stop()

    videos = (sb.table("cursos").select("*")
              .eq("curso", st.session_state.curso).order("modulo").execute().data)
    for v in videos:
        if len(videos) > 1:
            st.subheader(f"Módulo {v['modulo']}")
        st.video(v["url_video"])

    st.divider()

    if not st.session_state.ya_vio:
        st.info("Cuando termines de ver el video completo, pulsa el botón.")
        if st.button("Ya terminé el video"):
            st.session_state.ya_vio = True
            st.rerun()
    else:
        st.header("Evaluación")
        with st.form("examen"):
            respuestas = []
            for i, q in enumerate(PREGUNTAS):
                r = st.radio(f"{i+1}. {q['p']}", q["o"], index=None, key=f"p{i}")
                respuestas.append(r)
            enviar = st.form_submit_button("Enviar examen")

        if enviar:
            if None in respuestas:
                st.warning("Responde todas las preguntas.")
            else:
                correctas = sum(1 for q, r in zip(PREGUNTAS, respuestas)
                                if q["o"].index(r) == q["c"])
                nota = round(correctas * 100 / len(PREGUNTAS))
                detalle = [{"pregunta": q["p"], "respuesta": r}
                           for q, r in zip(PREGUNTAS, respuestas)]

                sb.table("resultados").insert({
                    "fecha_inicio": st.session_state.inicio,
                    "fecha_fin": datetime.now().isoformat(timespec="seconds"),
                    "nombre": st.session_state.nombre,
                    "correo": st.session_state.correo,
                    "curso": st.session_state.curso,
                    "codigo": st.session_state.codigo,
                    "nota": nota,
                    "aprobo": nota >= NOTA_MINIMA,
                    "respuestas": detalle,
                    "corregido": False,
                }).execute()

                st.session_state.enviado = True
                st.rerun()