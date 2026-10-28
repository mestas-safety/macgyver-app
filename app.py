import base64
import glob
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
    .stButton > button:disabled, .stButton > button:disabled:hover {
        background-color: #2A2A2A; color: #8A8A8A; cursor: not-allowed;
    }
    .stButton > button p {font-size: 0.92rem; line-height: 1.35;}
    h1, h2, h3 {font-weight: 800;}
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

NOTA_MINIMA = 70
BASE_URL = "https://macgyver-app-vvqmwfmp9utwfx5cpxzrak.streamlit.app"
TITULO_DEFECTO = "INDUCCIÓN SSOMA"
DS = "D.S. 011-2019-TR"

LIMA = timezone(timedelta(hours=-5))

def ahora():
    return datetime.now(LIMA).replace(tzinfo=None)

# ---------- Módulos de la portada ----------
# (clave, texto del botón, ¿activo?)
MODULOS = [
    ("induccion", f"INDUCCIÓN SSOMA (Art. 52 del {DS})", True),
    ("capacitaciones", f"CAPACITACIONES (Art. 54 del {DS})", False),
    ("competencias", "COMPETENCIAS: Herramientas de poder / Equipos menores / Línea amarilla-blanca", False),
    ("emergencias", f"PREPARACIÓN Y RESPUESTA A EMERGENCIAS (Art. 47 del {DS})", False),
    ("charlas", "CHARLAS / DIFUSIONES: Registro inteligente", False),
    ("ats", "ATS Inteligente", False),
    ("checklist", "CHECKLIST Inteligente", False),
    ("petar", "PETAR Inteligente", False),
    ("horario", "HORARIO EXTENDIDO Inteligente", False),
    ("comite", "COMITÉ DE SST (Libro de actas inteligente)", False),
    ("controles", "CONTROLES DE INGENIERÍA (Trazabilidad)", False),
    ("informes", "INFORMES SSOMA INTELIGENTES", False),
    ("dashboard", "DASHBOARD", False),
]

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
