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
    div[data-testid="stButton"] {width: 100%;}
    div[data-testid="stButton"] > button {
        width: 100%;
        min-height: 3.4rem;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
    }
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
    ("comite", "COMITÉ DE SST (Libro de actas inteligente)",
