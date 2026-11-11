import base64
import glob
import io
import unicodedata
from datetime import datetime, timezone, timedelta
from urllib.parse import quote

import qrcode
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from supabase import create_client

from checklist import mostrar_checklist, verificar_informe
from examen_pdf import paginas_examen
from examenes import EXAMENES, ESPECIFICAS, OTRAS

st.set_page_config(
    page_title="MACGYVER | Seguridad en Construcción",
    page_icon="logo.png",
    layout="centered",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@500;800;900&display=swap');
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
    .stButton > button:disabled, .stButton > button:disabled:hover {
        background-color: #2A2A2A; color: #8A8A8A; cursor: not-allowed;
    }
    .stButton > button p {font-size: 0.9rem; line-height: 1.35;}
    .stButton > button p, .stFormSubmitButton > button p, .stDownloadButton > button p {
        font-family: 'Montserrat', sans-serif; font-weight: 800;
    }
    .wsp {
        display: flex; align-items: center; justify-content: center; gap: 10px;
        margin-top: 1.4rem; padding: 0.95rem 1rem; border-radius: 6px;
        background: #25D366; color: #0A0A0A !important;
        font-family: 'Montserrat', sans-serif; font-weight: 800; font-size: 0.95rem;
        text-transform: uppercase; text-decoration: none !important; text-align: center;
    }
    .wsp:hover {background: #FFFFFF;}
    div[data-testid="stButton"] {width: 100%;}
    div[data-testid="stButton"] > button {
        width: 100%;
        min-height: 3.4rem;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
    }
    .stApp h1, .stApp h2, .stApp h3 {
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 900 !important;
        letter-spacing: -0.01em;
    }
    h2 {border-left: 6px solid #FFD600; padding-left: 12px;}
    div[role="radiogroup"] {gap: 0.7rem;}
    div[role="radiogroup"] > label {
        background-color: #1A1A1A;
        border: 1px solid #333333;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        line-height: 1.5;
        width: 100%;
    }
    div[role="radiogroup"] > label:hover {border-color: #FFD600;}
    div[role="radiogroup"] > label:has(input:checked) {
        border-color: #FFD600;
        background-color: #2A2500;
    }
    div[data-testid="stRadio"] {
        margin-bottom: 1.8rem;
        padding-bottom: 1.2rem;
        border-bottom: 1px solid #2A2A2A;
    }
</style>
""", unsafe_allow_html=True)

BASE_URL = "https://macgyver-app-vvqmwfmp9utwfx5cpxzrak.streamlit.app"
# WhatsApp: código de país + número, sin "+" ni espacios. Ejemplo: 51987654321
WHATSAPP_NUMERO = "51943372518"
WHATSAPP_MENSAJE = "Hola MACGYVER, vengo desde la plataforma SSOMA 4.0 y quisiera más información."
TITULO_DEFECTO = "INDUCCIÓN SSOMA"
DURACION_DEFECTO = "2 horas lectivas"
DS = "D.S. 011-2019-TR"

LIMA = timezone(timedelta(hours=-5))

def ahora():
    return datetime.now(LIMA).replace(tzinfo=None)

# ---------- Módulos de la portada ----------
# (clave, texto del botón, ¿activo?)
MODULOS = [
    ("induccion", f"INDUCCIÓN SSOMA (Art. 52 del {DS})", True),
    ("checklist_pre", "CHECKLIST PREOPERACIONAL (Verifica si tienes lo necesario para empezar tu proyecto)", True),
    ("capacitaciones", f"CAPACITACIONES (Art. 54 del {DS})", True),
    ("competencias", "COMPETENCIAS: Herramientas de poder / Equipos menores / Línea amarilla-blanca", False),
    ("emergencias", f"PREPARACIÓN Y RESPUESTA A EMERGENCIAS (Art. 47 del {DS})", False),
    ("charlas", "CHARLAS / DIFUSIONES: Registro inteligente", False),
    ("ats", "ATS Inteligente", False),
    ("checklist", "CHECKLIST Inteligente", True),
    ("petar", "PETAR Inteligente", False),
    ("horario", "HORARIO EXTENDIDO Inteligente", False),
    ("comite", "COMITÉ DE SST (Libro de actas inteligente)", False),
    ("controles", "CONTROLES DE INGENIERÍA (Trazabilidad)", False),
    ("informes", "INFORMES SSOMA INTELIGENTES", False),
    ("epp", "Entrega de EPP (inteligente)", False),
    ("dashboard", "DASHBOARD (Ejemplo para tu empresa)", True),
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
# (x_inicio, y_de_la_linea, x_fin, tamaño_letra) sobre plantilla de 1623 px
REF_W = 1623
CAMPOS = {
    "tema":     (528, 627, 1512, 34),
    "duracion": (528, 726, 1512, 44),
    "empresa":  (528, 829, 1512, 44),
    "proyecto": (528, 933, 1512, 36),
    "nombre":   (626, 1042, 1512, 44),
    "dni":      (528, 1153, 1512, 44),
    "cargo":    (530, 1254, 1512, 44),
    "nota":     (528, 1367, 1512, 44),
    "fecha":    (298, 1545, 795, 34),
    "cert":     (1010, 1545, 1503, 28),
}
SUBIDA = 12
QR_CAJA = (262, 1587, 533, 1836)
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
    escribir("proyecto", dat.get("proyecto") or "-", dos_lineas=True)
    draw.text((219.5 * s, 922.9 * s), "PROYECTO:", font=fuente(int(32 * s)),
              fill=(10, 10, 10), anchor="ls")
    escribir("nombre", dat["nombre"].upper())
    escribir("dni", dat["dni"])
    escribir("cargo", dat["cargo"].upper())
    escribir("nota", dat["nota"])
    escribir("fecha", dat["fecha"])
    escribir("cert", dat["cert"])

    qr = qrcode.QRCode(box_size=10, border=1)
    qr.add_data(f"{BASE_URL}/?v={dat['cert']}")
    qr.make(fit=True)
    qimg = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    qimg = qimg.resize((int(QR_TAM * s), int(QR_TAM * s)), Image.NEAREST)
    draw.rectangle([c * s for c in QR_CAJA], fill="white")
    img.paste(qimg, (int(QR_POS[0] * s), int(QR_POS[1] * s)))

    extra = paginas_examen(W, H, dat, dat["preguntas"])
    buf = io.BytesIO()
    img.save(buf, "PDF", resolution=W / 8.27, save_all=True, append_images=extra)
    return buf.getvalue()

@st.cache_resource
def conectar():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

sb = conectar()

for clave, valor in {"acceso": False, "ya_vio": False, "resultado": None}.items():
    if clave not in st.session_state:
        st.session_state[clave] = valor

# Link de siempre -> Inducción. ?m=menu -> portada. ?m=checklist -> checklist.
# ?m=capacitacion -> menú de capacitaciones.
# ?m=capacitacion&c=excavaciones -> ingreso directo a ese curso.
if "vista" not in st.session_state:
    _m = st.query_params.get("m")
    st.session_state.vista = ("portada" if _m == "menu"
                              else "checklist_pre" if _m == "checklist"
                              else "capacitaciones" if _m == "capacitacion"
                              else "induccion")

if "cap_curso" not in st.session_state:
    _c = st.query_params.get("c")
    _validos = {k for k, _ in ESPECIFICAS + OTRAS} & set(EXAMENES)
    st.session_state.cap_curso = _c if _c in _validos else None

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
cod_inf = st.query_params.get("i")
if cod_inf:
    verificar_informe(sb, cod_inf)
    st.stop()

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

# ---------- PORTADA ----------
LOGOS_EN_BLANCO = True

def logo_cliente_b64(ruta):
    img = Image.open(ruta).convert("RGBA")
    if LOGOS_EN_BLANCO:
        alfa = img.split()[3]
        blanco = Image.new("RGBA", img.size, (255, 255, 255, 255))
        blanco.putalpha(alfa)
        img = blanco
    img.thumbnail((400, 200))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()

def logos_clientes():
    archivos = sorted(glob.glob("cliente_*.png"))
    if not archivos:
        return
    fondo = "transparent" if LOGOS_EN_BLANCO else "#FFFFFF"
    celdas = ""
    for a in archivos:
        celdas += f'<div class="celda"><img src="data:image/png;base64,{logo_cliente_b64(a)}"></div>'
    html = (
        '<style>'
        '.logos-caja{margin-top:2.2rem;}'
        '.logos-texto{text-align:center;font-family:Montserrat,sans-serif;font-weight:800;font-size:1.05rem;margin-bottom:1rem;}'
        f'.logos-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:12px;background:{fondo};border-radius:10px;padding:14px;}}'
        '.celda{height:80px;display:flex;align-items:center;justify-content:center;}'
        '.celda img{max-height:70px;max-width:100%;object-fit:contain;}'
        '</style>'
        '<div class="logos-caja">'
        '<div class="logos-texto">Ellos ya comparten nuestra experiencia</div>'
        f'<div class="logos-grid">{celdas}</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)

NOMBRES_CAP = dict(ESPECIFICAS + OTRAS)

def _botones_cap(lista):
    for clave, nombre in lista:
        activo = clave in EXAMENES
        etiqueta = nombre if activo else f"🔒 {nombre} · Próximamente"
        if st.button(etiqueta, key=f"cap_{clave}", disabled=not activo,
                     use_container_width=True):
            st.session_state.cap_curso = clave
            st.rerun()

def menu_capacitaciones():
    if st.button("← Volver al menú"):
        st.session_state.vista = "portada"
        st.rerun()
    st.subheader("Capacitaciones (Art. 54 del D.S. 011-2019-TR)")
    st.header("CAPACITACIONES ESPECÍFICAS")
    st.caption("Elige la capacitación que vas a rendir. Las marcadas con 🔒 se activarán pronto.")
    _botones_cap(ESPECIFICAS)
    st.divider()
    st.header("OTRAS CAPACITACIONES QUE PUEDEN COMPLEMENTAR")
    st.caption("Capacitaciones adicionales que no establece la ley.")
    _botones_cap(OTRAS)

# Checklists de inspección. (clave, nombre). Se activan cuando estén desarrollados.
CHECKLISTS = [
    ("herramientas_manuales", "Checklist Herramientas manuales"),
    ("herramientas_poder", "Checklist Herramientas de poder"),
    ("linea_amarilla", "Checklist Equipos de línea amarilla"),
    ("linea_blanca", "Checklist Equipos de línea blanca"),
    ("equipos_menores", "Checklist Equipos menores"),
    ("vehiculos", "Checklist Vehículos"),
    ("estacion_emergencia", "Checklist Estación de emergencia"),
    ("botiquines", "Checklist Botiquines"),
    ("extintores", "Checklist Extintores"),
    ("kit_antiderrames", "Checklist Kit antiderrames"),
    ("escaleras", "Checklist Escaleras"),
    ("andamios", "Checklist Andamios"),
    ("proteccion_caidas", "Checklist Sistema de protección contra caídas"),
    ("oficina", "Checklist Oficina"),
    ("vestuario", "Checklist Vestuario"),
    ("comedor", "Checklist Comedor"),
    ("servicios_higienicos", "Checklist Servicios higiénicos"),
    ("epp", "Checklist de EPP"),
]
CHECKLISTS_ACTIVOS = set()

def menu_checklists():
    if st.button("← Volver al menú"):
        st.session_state.vista = "portada"
        st.rerun()
    st.subheader("Checklist inteligente")
    st.caption("Elige el checklist que vas a realizar. Las marcadas con 🔒 se activarán pronto.")
    for clave, nombre in CHECKLISTS:
        activo = clave in CHECKLISTS_ACTIVOS
        etiqueta = nombre if activo else f"🔒 {nombre} · Próximamente"
        if st.button(etiqueta, key=f"chk_{clave}", disabled=not activo,
                     use_container_width=True):
            st.session_state.chk_sel = clave
            st.rerun()

def boton_whatsapp():
    if not WHATSAPP_NUMERO.isdigit():
        return
    url = f"https://wa.me/{WHATSAPP_NUMERO}?text={quote(WHATSAPP_MENSAJE)}"
    st.caption("¿Tienes dudas o quieres cotizar? Conversa con nosotros.")
    st.markdown(f'<a class="wsp" href="{url}" target="_blank" rel="noopener">💬 Escríbenos por WhatsApp</a>',
                unsafe_allow_html=True)

if st.session_state.vista == "portada":
    st.subheader("Programación y automatización para SSOMA 4.0")
    st.caption("Elige un módulo. Los marcados con 🔒 se activarán pronto.")
    for clave, texto, activo in MODULOS:
        etiqueta = texto if activo else f"🔒 {texto} · Próximamente"
        if st.button(etiqueta, key=f"mod_{clave}", disabled=not activo,
                     use_container_width=True):
            st.session_state.vista = clave
            st.rerun()
    boton_whatsapp()
    logos_clientes()
    st.markdown(
        '<p style="text-align:center; color:#8A8A8A; font-size:0.85rem; margin-top:2rem;">'
        'Full Stack Developer: Ing. CIP A.M. (Macgyver)</p>',
        unsafe_allow_html=True,
    )
    st.stop()

if st.session_state.vista == "checklist_pre":
    mostrar_checklist(sb, ahora, BASE_URL)
    st.stop()

if st.session_state.vista == "dashboard":
    import streamlit.components.v1 as components
    st.markdown(
        "<style>.block-container{max-width:1100px !important;}"
        ".block-container img{max-width:360px !important;}</style>",
        unsafe_allow_html=True,
    )
    if st.button("← Volver al menú"):
        st.session_state.vista = "portada"
        st.rerun()
    with open("dashboard.html", encoding="utf-8") as f:
        components.html(f.read(), height=2600, scrolling=True)
    st.stop()

if st.session_state.vista == "checklist":
    menu_checklists()
    st.stop()

if st.session_state.vista == "capacitaciones" and not st.session_state.cap_curso:
    menu_capacitaciones()
    st.stop()

if st.session_state.vista not in ("induccion", "capacitaciones"):
    st.info("Este módulo estará disponible pronto.")
    if st.button("← Volver al menú"):
        st.session_state.vista = "portada"
        st.rerun()
    st.stop()

# ---------- Resultado (aprobado / desaprobado) ----------
def mostrar_resultado(r, duracion, titulo):
    if r.get("aprobo"):
        st.success("🎉 ¡FELICITACIONES! UD. HA APROBADO LA EVALUACIÓN.")
        ex = EXAMENES[r["curso"]]
        total = len(ex["preguntas"])
        correctas = round(r["nota"] * total / 100)
        fecha = datetime.fromisoformat(str(r["fecha_fin"])[:19]).strftime("%d/%m/%Y")
        pdf = generar_certificado({
            "tema": titulo,
            "duracion": duracion,
            "empresa": r["empresa"],
            "proyecto": r.get("proyecto") or st.session_state.get("proyecto", ""),
            "nombre": r["nombre"],
            "dni": r["dni"],
            "cargo": r["cargo"],
            "nota": f"{correctas}/{total} ({r['nota']}%)",
            "fecha": fecha,
            "cert": r["cert_codigo"],
            "respuestas": r.get("respuestas"),
            "preguntas": ex["preguntas"],
            "titulo_examen": ex["titulo"],
            "titulo_examen_corto": ex["corto"],
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
    if st.session_state.vista == "capacitaciones":
        if st.button("← Volver a capacitaciones"):
            st.session_state.cap_curso = None
            st.rerun()
        st.subheader("Ingreso a Capacitación")
        st.markdown(f"**{NOMBRES_CAP.get(st.session_state.cap_curso, '')}**")
    else:
        if st.query_params.get("m") == "menu":
            if st.button("← Volver al menú"):
                st.session_state.vista = "portada"
                st.rerun()
        st.subheader("Ingreso a Inducción")
    empresa = st.text_input("Empresa").strip()
    proyecto = st.text_input("Proyecto").strip()
    nombre = st.text_input("Apellidos y Nombres (completos)").strip()
    dni = st.text_input("DNI").strip()
    cargo = st.text_input("Cargo").strip()
    whatsapp = st.text_input("Número de WhatsApp").strip()
    correo = st.text_input("Correo electrónico").strip().lower()
    codigo = st.text_input("Código de acceso").strip().upper()

    if st.button("Ingresar"):
        if not all([empresa, proyecto, nombre, dni, cargo, whatsapp, correo, codigo]):
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
                elif (st.session_state.vista == "capacitaciones"
                      and fila["curso"] != st.session_state.cap_curso):
                    st.error("Este código no corresponde a esta capacitación.")
                else:
                    if not usado:
                        sb.table("codigos").update({
                            "usado": True,
                            "alumno": nombre,
                            "correo": correo,
                            "dni": dni,
                            "empresa": empresa,
                            "proyecto": proyecto,
                            "cargo": cargo,
                            "whatsapp": whatsapp,
                        }).eq("codigo", codigo).execute()

                    previo = (sb.table("resultados").select("*")
                              .eq("codigo", codigo).order("id", desc=True)
                              .limit(1).execute().data)

                    st.session_state.acceso = True
                    st.session_state.resultado = previo[0] if previo else None
                    st.session_state.empresa = empresa
                    st.session_state.proyecto = proyecto
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
    duracion = (videos[0].get("duracion_texto") if videos else None) or DURACION_DEFECTO
    titulo = (videos[0].get("titulo_certificado") if videos else None) or TITULO_DEFECTO

    ex = EXAMENES.get(st.session_state.curso)
    if ex is None:
        st.error("Este curso todavía no tiene examen configurado. "
                 "Comunícate con tu operador de contrato.")
        st.stop()
    PREGUNTAS = ex["preguntas"]
    NOTA_MINIMA = ex["nota_min"]

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
                    "proyecto": st.session_state.proyecto,
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
