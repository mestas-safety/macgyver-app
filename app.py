import base64
import io
import unicodedata
from datetime import datetime, timezone, timedelta

import qrcode
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
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
    .stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {
        background-color: #FFD600; color: #0A0A0A; font-weight: 800;
        border: none; border-radius: 6px; padding: 0.6rem 1.4rem;
        text-transform: uppercase; width: 100%;
    }
    .stButton > button:hover, .stFormSubmitButton > button:hover,
    .stDownloadButton > button:hover {
        background-color: #FFFFFF; color: #0A0A0A;
    }
    h1, h2, h3 {font-weight: 800;}
    h2 {border-left: 6px solid #FFD600; padding-left: 12px;}
</style>
""", unsafe_allow_html=True)

NOTA_MINIMA = 70
BASE_URL = "https://macgyver-app-vvqmwfmp9utwfx5cpxzrak.streamlit.app"
TITULO_DEFECTO = "INDUCCIÓN SSOMA"

LIMA = timezone(timedelta(hours=-5))

def ahora():
    return datetime.now(LIMA).replace(tzinfo=None)

PREGUNTAS = [
    {"p": "¿Qué es un peligro?",
     "o": ["Un evento que siempre causa lesiones.",
           "Una fuente, situación o acto con potencial de causar daño.",
           "Una medida de control implementada en el trabajo."], "c": 1},
    {"p": "¿Qué es el IPERC de línea base?",
     "o": ["Un registro de asistencia a las capacitaciones.",
           "La identificación de peligros, evaluación de riesgos y determinación de controles para las actividades.",
           "Un documento exclusivo para registrar accidentes."], "c": 1},
    {"p": "¿Qué significa PETS?",
     "o": ["Programa de Evaluación Técnica de Seguridad.",
           "Permiso Especial de Trabajo Seguro.",
           "Procedimiento Escrito de Trabajo Seguro."], "c": 2},
    {"p": "¿Cuál es la finalidad de los equipos de protección personal (EPP)?",
     "o": ["Reemplazar todos los controles de seguridad.",
           "Evitar que se realicen inspecciones de seguridad.",
           "Permitir trabajar sin identificar los peligros.",
           "Proteger al trabajador frente a los riesgos para los cuales fueron seleccionados."], "c": 3},
    {"p": "¿Qué información contienen las hojas de datos de seguridad (SDS/HDS)?",
     "o": ["Únicamente el precio de los productos químicos.",
           "Los peligros de los productos químicos y las medidas de prevención y respuesta ante emergencias.",
           "Solo el nombre comercial del producto."], "c": 1},
    {"p": "¿Cuál es el objetivo de las brigadas de emergencia?",
     "o": ["Organizar la respuesta ante emergencias mediante funciones como lucha contra incendios, primeros auxilios y evacuación.",
           "Reemplazar al personal médico en todas las situaciones.",
           "Autorizar cualquier trabajo de alto riesgo."], "c": 0},
    {"p": "¿Qué debe conocer el trabajador sobre los riesgos de su actividad?",
     "o": ["Solamente el nombre de su supervisor.",
           "Únicamente el horario de trabajo.",
           "Los peligros identificados, los riesgos asociados y las medidas de control."], "c": 2},
    {"p": "¿Cómo deben manejarse los residuos en el proyecto?",
     "o": ["Mezclándolos en un solo recipiente.",
           "Dejándolos en cualquier área disponible.",
           "Entregándolos sin segregación.",
           "Segregándolos por tipo y utilizando los recipientes establecidos según el procedimiento."], "c": 3},
    {"p": "¿Cuál es la finalidad de los sistemas de protección contra caídas, como barandas y redes?",
     "o": ["Facilitar el almacenamiento de materiales.",
           "Prevenir caídas o reducir sus consecuencias, según el sistema utilizado.",
           "Reemplazar la capacitación del trabajador."], "c": 1},
    {"p": "¿Qué debe verificarse antes de iniciar las labores?",
     "o": ["Únicamente la asistencia del trabajador.",
           "Solo la disponibilidad de herramientas.",
           "Inducción aprobada, examen médico ocupacional y SCTR vigentes, EPP adecuado, difusión del IPERC/PETS y capacitaciones y autorizaciones requeridas."], "c": 2},
    {"p": "Durante una operación, una excavadora está trabajando y un compañero se encuentra demasiado cerca de su zona de movimiento. ¿Qué debes hacer?",
     "o": ["Acercarte para ayudar al operador.",
           "Pasar rápidamente detrás de la excavadora.",
           "Continuar trabajando porque el operador puede verte.",
           "Advertir al compañero, mantenerte fuera de la zona de operación y comunicar la situación."], "c": 3},
    {"p": "Antes de comenzar una tarea, un trabajador manifiesta que no conoce los controles establecidos en el IPERC. ¿Qué corresponde hacer?",
     "o": ["Solicitar la explicación de los peligros, riesgos y controles antes de iniciar el trabajo.",
           "Empezar la tarea y consultar después.",
           "Copiar los controles de otra actividad sin verificarlos."], "c": 0},
    {"p": "Un trabajador debe realizar una actividad, pero no conoce el PETS correspondiente. ¿Qué debe hacer?",
     "o": ["Realizar el trabajo según su experiencia personal.",
           "Pedir a un compañero que lo observe mientras trabaja.",
           "Solicitar la difusión y explicación del PETS antes de ejecutar la actividad."], "c": 2},
    {"p": "Durante la inspección, un trabajador detecta que sus lentes de seguridad están rotos. ¿Qué debe hacer?",
     "o": ["Continuar trabajando si el daño parece pequeño.",
           "Solicitar el reemplazo de los lentes y no realizar la tarea sin la protección ocular requerida.",
           "Utilizar lentes oscuros convencionales."], "c": 1},
    {"p": "Un trabajador debe utilizar un solvente, pero desconoce sus peligros y las medidas de protección necesarias. ¿Qué corresponde hacer?",
     "o": ["Utilizarlo con las ventanas abiertas, sin más verificaciones.",
           "Mezclarlo con otro producto para reducir su peligrosidad.",
           "Utilizarlo en pequeñas cantidades sin consultar.",
           "Revisar la SDS/HDS, recibir instrucciones y verificar los controles y EPP necesarios."], "c": 3},
    {"p": "Un trabajador debe realizar labores en una plataforma elevada y observa que falta la protección colectiva contra caídas en el borde. ¿Qué debe hacer?",
     "o": ["No iniciar o detener la actividad y reportar la condición para implementar la protección requerida.",
           "Continuar con cuidado y evitar acercarse al borde.",
           "Colocar materiales en el borde como barrera provisional sin autorización."], "c": 0},
    {"p": "Durante la jornada, un trabajador observa que un compañero ha sufrido una lesión. ¿Cuál es la actuación correcta?",
     "o": ["Mover al lesionado inmediatamente, sin evaluar su condición.",
           "Comunicar el incidente al supervisor o SSOMA, activar la respuesta de emergencia y gestionar la atención médica.",
           "Esperar hasta finalizar el turno para informar."], "c": 1},
    {"p": "Durante un trabajo de soldadura se generan chispas cerca de materiales combustibles y no se han verificado los controles contra incendios. ¿Qué corresponde hacer?",
     "o": ["Continuar mientras no se observe fuego.",
           "Pedir a otro trabajador que vigile, sin detener la actividad.",
           "Detener el trabajo, controlar el peligro de incendio y verificar las medidas preventivas antes de reiniciar."], "c": 2},
    {"p": "Un equipo debe instalar una estructura metálica sobre una plataforma elevada. Durante la inspección se identifica que falta una baranda en el borde, un trabajador no puede acreditar la capacitación requerida, el sistema personal de protección contra caídas no ha sido inspeccionado, el ATS no considera las condiciones reales de la tarea y debajo de la plataforma circulan otros trabajadores sin restricción de acceso. ¿Qué decisión corresponde tomar?",
     "o": ["Iniciar el trabajo utilizando únicamente el sistema personal de protección contra caídas.",
           "Permitir que el trabajador sin capacitación participe bajo supervisión.",
           "Actualizar el ATS después de finalizar la instalación y continuar con precaución.",
           "No iniciar hasta implementar la protección colectiva, verificar la capacitación y autorización, inspeccionar el sistema anticaídas, actualizar el ATS y restringir el acceso al área inferior."], "c": 3},
    {"p": "Antes de iniciar una excavación cercana a instalaciones eléctricas y tuberías enterradas, el equipo no ha confirmado la ubicación de los servicios, no ha evaluado la estabilidad del terreno, el ATS no contempla todos los peligros y se pretende utilizar una excavadora mientras hay trabajadores realizando labores manuales dentro de la excavación. ¿Qué debe hacerse?",
     "o": ["Iniciar la excavación lentamente y detenerse si aparece alguna tubería.",
           "Suspender el inicio hasta localizar los servicios enterrados, evaluar la estabilidad del terreno, definir la protección contra derrumbes, asegurar accesos, delimitar el área, controlar la interacción entre maquinaria y trabajadores, verificar los permisos aplicables y actualizar el ATS.",
           "Permitir el ingreso de los trabajadores mientras el operador mantenga contacto visual.",
           "Continuar con la excavación y completar los documentos al finalizar."], "c": 1},
]

# ---------- Utilidades ----------
def solo_letras(texto):
    t = unicodedata.normalize("NFKD", str(texto))
    t = "".join(c for c in t if not unicodedata.combining(c))
    return "".join(c for c in t.upper() if c.isalpha())

def codigo_certificado(codigo, nombre, dni):
    partes = nombre.split()
    apellido = solo_letras(partes[0]) if partes else "X"
    return f"{codigo.replace('-', '')}-{apellido}-{dni[-4:]}"

def duracion_texto(valor):
    try:
        p = [int(x) for x in str(valor).split(":")]
        while len(p) < 3:
            p.insert(0, 0)
        horas = p[0] + p[1] / 60 + p[2] / 3600
        if horas <= 0:
            return ""
        return f"{horas:.1f} horas"
    except Exception:
        return ""

def fuente(tam):
    for ruta in ["fuente.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                 "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]:
        try:
            return ImageFont.truetype(ruta, tam)
        except OSError:
            continue
    return ImageFont.load_default(tam)

# ---------- POSICIONES DEL CERTIFICADO ----------
# Medidas sobre una plantilla de 1623 px de ancho (se escalan solas).
# (x_inicio, y_de_la_linea, x_fin, tamaño_letra)
REF_W = 1623
CAMPOS = {
    "tema":     (528, 650, 1512, 34),
    "duracion": (528, 759, 1512, 44),
    "empresa":  (528, 872, 1512, 44),
    "nombre":   (626, 992, 1512, 44),
    "dni":      (528, 1118, 1512, 44),
    "cargo":    (530, 1233, 1512, 44),
    "nota":     (528, 1361, 1512, 44),
    "fecha":    (298, 1545, 795, 34),
    "cert":     (1010, 1545, 1503, 28),
}
SUBIDA = 12          # píxeles que el texto flota sobre la línea
QR_CAJA = (262, 1587, 533, 1836)   # zona blanca del recuadro del QR
QR_TAM = 232
QR_POS = (281, 1595)

def partir_en_dos(texto):
    palabras = texto.split()
    if len(palabras) < 2:
        return [texto]
    mejor, dif = None, 10**9
    for i in range(1, len(palabras)):
        a, b = " ".join(palabras[:i]), " ".join(palabras[i:])
        d = abs(len(a) - len(b))
        if d < dif:
            mejor, dif = [a, b], d
    return mejor

def generar_certificado(dat):
    img = Image.open("certificado.png").convert("RGB")
    W, H = img.size
    s = W / REF_W
    draw = ImageDraw.Draw(img)

    def escribir(campo, texto, dos_lineas=False):
        x, y, x_fin, size = CAMPOS[campo]
        ancho = (x_fin - x - 8) * s
        lineas = [texto]
        if dos_lineas and draw.textlength(texto, font=fuente(int(size * s))) > ancho:
            lineas = partir_en_dos(texto)
        tam = int(size * s)
        f = fuente(tam)
        while max(draw.textlength(l, font=f) for l in lineas) > ancho and tam > 14:
            tam -= 2
            f = fuente(tam)
        base = (y - SUBIDA) * s
        paso = tam * 1.2
        for i, l in enumerate(reversed(lineas)):
            draw.text((x * s, base - i * paso), l, font=f,
                      fill=(10, 10, 10), anchor="ls")

    escribir("tema", dat["tema"], dos_lineas=True)
    escribir("duracion", dat["duracion"])
    escribir("empresa", dat["empresa"].upper())
    escribir("nombre", dat["nombre"].upper())
    escribir("dni", dat["dni"])
    escribir("cargo", dat["cargo"].upper())
    escribir("nota", dat["nota"])
    escribir("fecha", dat["fecha"])
    escribir("cert", dat["cert"])

    # QR de verificación dentro del recuadro vacío
    qr = qrcode.QRCode(box_size=10, border=1)
    qr.add_data(f"{BASE_URL}/?v={dat['cert']}")
    qr.make(fit=True)
    qimg = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    qimg = qimg.resize((int(QR_TAM * s), int(QR_TAM * s)), Image.NEAREST)
    draw.rectangle([c * s for c in QR_CAJA], fill="white")
    img.paste(qimg, (int(QR_POS[0] * s), int(QR_POS[1] * s)))

    buf = io.BytesIO()
    img.save(buf, "PDF", resolution=W / 8.27)
    return buf.getvalue()

@st.cache_resource
def conectar():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

sb = conectar()

for clave, valor in {"acceso": False, "ya_vio": False, "resultado": None}.items():
    if clave not in st.session_state:
        st.session_state[clave] = valor

# ---------- Logo ----------
with open("logo.png", "rb") as f:
    logo_b64 = base64.b64encode(f.read()).decode()

st.markdown(
    f'<div style="background:#FFFFFF; padding:18px; border-radius:10px; text-align:center;">'
    f'<img src="data:image/png;base64,{logo_b64}" style="max-width:100%; height:auto;">'
    f'</div>',
    unsafe_allow_html=True,
)
st.markdown('<div class="franja"></div>', unsafe_allow_html=True)

# ---------- Verificación por QR ----------
cod_qr = st.query_params.get("v")
if cod_qr:
    r = (sb.table("resultados").select("nombre,curso,fecha_fin")
         .eq("cert_codigo", cod_qr).eq("aprobo", True).limit(1).execute().data)
    if r:
        r = r[0]
        c = (sb.table("cursos").select("titulo_certificado")
             .eq("curso", r["curso"]).limit(1).execute().data)
        titulo = (c[0].get("titulo_certificado") if c else None) or TITULO_DEFECTO
        fecha = datetime.fromisoformat(str(r["fecha_fin"])[:19]).strftime("%d/%m/%Y")
        st.success("✅ ESTA CAPACITACIÓN ESTÁ AVALADA POR MACGYVER SEGURIDAD EN CONSTRUCCIÓN")
        st.markdown(f"**Participante:** {r['nombre'].upper()}")
        st.markdown(f"**Curso:** {titulo}")
        st.markdown(f"**Fecha de emisión:** {fecha}")
        st.markdown(f"**Código:** {cod_qr}")
    else:
        st.error("Certificado no válido o no encontrado.")
    st.stop()

# ---------- Resultado (aprobado / desaprobado) ----------
def mostrar_resultado(r, duracion, titulo):
    if r.get("aprobo"):
        st.success("🎉 ¡FELICITACIONES! UD. HA APROBADO LA EVALUACIÓN.")
        total = len(PREGUNTAS)
        correctas = round(r["nota"] * total / 100)
        fecha = datetime.fromisoformat(str(r["fecha_fin"])[:19]).strftime("%d/%m/%Y")
        pdf = generar_certificado({
            "tema": titulo,
            "duracion": duracion,
            "empresa": r["empresa"],
            "nombre": r["nombre"],
            "dni": r["dni"],
            "cargo": r["cargo"],
            "nota": f"{correctas}/{total} ({r['nota']}%)",
            "fecha": fecha,
            "cert": r["cert_codigo"],
        })
        st.download_button("Descargar mi certificado (PDF)", data=pdf,
                           file_name=f"certificado_{r['cert_codigo']}.pdf",
                           mime="application/pdf")
    else:
        st.error(
            "UD. HA DESAPROBADO, POR FAVOR COMUNÍQUESE CON SU OPERADOR DE CONTRATO "
            "PARA REPROGRAMARLO.\n\n"
            "Debe prestar más atención, la seguridad no es un juego."
        )

# ---------- Pantalla 1: Ingreso ----------
if not st.session_state.acceso:
    st.subheader("Ingreso al curso")
    empresa = st.text_input("Empresa").strip()
    nombre = st.text_input("Apellidos y Nombres (completos)").strip()
    dni = st.text_input("DNI").strip()
    cargo = st.text_input("Cargo").strip()
    whatsapp = st.text_input("Número de WhatsApp").strip()
    correo = st.text_input("Correo electrónico").strip().lower()
    codigo = st.text_input("Código de acceso").strip().upper()

    if st.button("Ingresar"):
        if not all([empresa, nombre, dni, cargo, whatsapp, correo, codigo]):
            st.warning("Completa todos los campos.")
        elif not dni.isdigit() or len(dni) != 8:
            st.warning("El DNI debe tener 8 números.")
        else:
            res = sb.table("codigos").select("*").eq("codigo", codigo).execute().data
            if not res:
                st.error("Código no válido.")
            else:
                fila = res[0]
                usado = bool(fila["usado"])
                dni_guardado = str(fila.get("dni") or "").strip()

                if usado and dni_guardado != dni:
                    st.error("Este código ya fue usado por otra persona.")
                else:
                    if not usado:
                        sb.table("codigos").update({
                            "usado": True,
                            "alumno": nombre,
                            "correo": correo,
                            "dni": dni,
                            "empresa": empresa,
                            "cargo": cargo,
                            "whatsapp": whatsapp,
                        }).eq("codigo", codigo).execute()

                    previo = (sb.table("resultados").select("*")
                              .eq("codigo", codigo).order("id", desc=True)
                              .limit(1).execute().data)

                    st.session_state.acceso = True
                    st.session_state.resultado = previo[0] if previo else None
                    st.session_state.empresa = empresa
                    st.session_state.nombre = nombre
                    st.session_state.dni = dni
                    st.session_state.cargo = cargo
                    st.session_state.whatsapp = whatsapp
                    st.session_state.correo = correo
                    st.session_state.codigo = codigo
                    st.session_state.curso = fila["curso"]
                    st.session_state.inicio = ahora().isoformat(timespec="seconds")
                    st.rerun()

# ---------- Pantalla 2: Video + Examen ----------
else:
    st.success(f"Bienvenido, {st.session_state.nombre}")

    videos = (sb.table("cursos").select("*")
              .eq("curso", st.session_state.curso).order("modulo").execute().data)
    duracion = "2 horas lectivas"
    titulo = (videos[0].get("titulo_certificado") if videos else None) or TITULO_DEFECTO

    if st.session_state.resultado:
        mostrar_resultado(st.session_state.resultado, duracion, titulo)
        st.stop()

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
                aprobo = nota >= NOTA_MINIMA
                detalle = [{"pregunta": q["p"], "respuesta": r}
                           for q, r in zip(PREGUNTAS, respuestas)]

                fila = {
                    "fecha_inicio": st.session_state.inicio,
                    "fecha_fin": ahora().isoformat(timespec="seconds"),
                    "nombre": st.session_state.nombre,
                    "correo": st.session_state.correo,
                    "empresa": st.session_state.empresa,
                    "dni": st.session_state.dni,
                    "cargo": st.session_state.cargo,
                    "whatsapp": st.session_state.whatsapp,
                    "curso": st.session_state.curso,
                    "codigo": st.session_state.codigo,
                    "nota": nota,
                    "aprobo": aprobo,
                    "respuestas": detalle,
                    "corregido": False,
                    "cert_codigo": codigo_certificado(
                        st.session_state.codigo,
                        st.session_state.nombre,
                        st.session_state.dni) if aprobo else None,
                }
                sb.table("resultados").insert(fila).execute()

                st.session_state.resultado = fila
                st.rerun()
