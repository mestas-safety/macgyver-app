"""Evaluación e Informe de Inspección Pre-operativa (MACGYVER)."""
import io
from datetime import timedelta

from PIL import Image, ImageDraw

from checklist_data import ITEMS, PANTALLAS, TITULOS, CRITICOS
from examen_pdf import _fuente, _wrap, RUTAS_NEGRITA, RUTAS_NORMAL

W, H = 1240, 1754
M = 60
NEGRO, GRIS, AMARILLO = (20, 20, 20), (105, 105, 105), (255, 214, 0)
ROJO, VERDE, AMBAR = (198, 40, 40), (31, 157, 85), (255, 214, 0)
POR_ID = {i[0]: i for i in ITEMS}


def dias_habiles(desde, n):
    d, c = desde, 0
    while c < n:
        d += timedelta(days=1)
        if d.weekday() < 5:
            c += 1
    return d


def evaluar(resp):
    """resp: {id: 'ok' | 'no' | 'na'}"""
    ok = ap = 0
    fallas, crit = [], False
    por_pant = []
    for nombre, nums in PANTALLAS:
        pok = pap = 0
        for iid, _, _ in ITEMS:
            if int(iid.split(".")[0]) not in nums:
                continue
            a = resp.get(iid)
            if a == "na" or a is None:
                continue
            pap += 1
            if a == "ok":
                pok += 1
            else:
                fallas.append(iid)
                if iid in CRITICOS:
                    crit = True
        ok, ap = ok + pok, ap + pap
        por_pant.append((nombre, pok, pap))
    pct = round(ok / ap * 100, 1) if ap else 0.0
    if crit or pct < 80:
        ver = "NO"
    elif pct < 100:
        ver = "REG"
    else:
        ver = "OK"
    return dict(pct=pct, ok=ok, ap=ap, fallas=fallas, crit=crit, pant=por_pant, ver=ver)


def _fit(d, texto, rutas, tam, ancho):
    f = _fuente(rutas, tam)
    while d.textlength(texto, font=f) > ancho and tam > 10:
        tam -= 1
        f = _fuente(rutas, tam)
    return f


def _logo():
    try:
        lg = Image.open("logo.png").convert("RGBA")
        h = 84
        return lg.resize((int(lg.width * h / lg.height), h), Image.LANCZOS)
    except Exception:
        return None


def _franja(d, y):
    d.rectangle([M, y, W - M, y + 14], fill=NEGRO)
    for x in range(M - 20, W - M, 28):
        d.polygon([(x, y + 14), (x + 14, y + 14), (x + 28, y), (x + 14, y)], fill=AMARILLO)
    d.rectangle([0, y, M - 1, y + 14], fill="white")
    d.rectangle([W - M + 1, y, W, y + 14], fill="white")


def generar_informe_pdf(dat, resp, base_url):
    ev = evaluar(resp)
    paginas = []
    logo = _logo()
    fb = lambda t: _fuente(RUTAS_NEGRITA, t)
    fn = lambda t: _fuente(RUTAS_NORMAL, t)

    def nueva(primera):
        im = Image.new("RGB", (W, H), "white")
        d = ImageDraw.Draw(im)
        if logo:
            im.paste(logo, (M, 36), logo)
        if primera:
            d.text((W - M, 50), f"Código de informe  {dat['codigo_informe']}", font=fb(18), fill=NEGRO, anchor="ra")
            d.text((W - M, 80), dat["fecha"].strftime("%d/%m/%Y  %H:%M"), font=fn(18), fill=GRIS, anchor="ra")
        else:
            d.text((W - M, 56), f"{dat['empresa']}  ·  {dat['codigo_informe']}", font=fn(17), fill=GRIS, anchor="ra")
        paginas.append(im)
        return im, d

    # ---------------- Página 1 ----------------
    im, d = nueva(True)
    d.text((W // 2, 168), "INFORME DE INSPECCIÓN PRE-OPERATIVA", font=_fit(d, "INFORME DE INSPECCIÓN PRE-OPERATIVA", RUTAS_NEGRITA, 38, W - 2 * M), fill=NEGRO, anchor="mm")
    d.text((W // 2, 206), "Checklist preoperacional – inicio de proyecto", font=fn(20), fill=GRIS, anchor="mm")
    _franja(d, 232)

    y0, fila = 268, 50
    filas = [[("Empresa", dat["empresa"]), ("RUC", dat["ruc"])],
             [("Proyecto", dat["proyecto"])],
             [("N° de trabajadores", dat["trabajadores"]), ("Régimen tributario", dat["regimen"])],
             [("Responsable", dat["responsable"]), ("Cargo", dat["cargo"])]]
    cw = (W - 2 * M) // 2
    d.rectangle([M, y0, W - M, y0 + 4 * fila], outline=NEGRO, width=2)
    for k in range(1, 4):
        d.line([M, y0 + k * fila, W - M, y0 + k * fila], fill=(190, 190, 190), width=1)
    for r, celdas in enumerate(filas):
        if len(celdas) == 2:
            d.line([M + cw, y0 + r * fila, M + cw, y0 + (r + 1) * fila], fill=NEGRO, width=2)
        for c, (et, val) in enumerate(celdas):
            ancho = cw if len(celdas) == 2 else 2 * cw
            fx, fy = M + c * cw, y0 + r * fila + fila // 2
            d.text((fx + 12, fy), et + ":", font=fb(17), fill=NEGRO, anchor="lm")
            xv = fx + 12 + int(d.textlength(et + ":", font=fb(17))) + 8
            d.text((xv, fy), str(val), font=_fit(d, str(val), RUTAS_NORMAL, 18, fx + ancho - xv - 10), fill=NEGRO, anchor="lm")

    yb = y0 + 4 * fila + 34
    d.text((M, yb + 54), f"{ev['pct']:.1f} %".replace(".", ","), font=fb(100), fill=NEGRO, anchor="lm")
    d.text((W - M, yb + 30), f"{ev['ok']} de {ev['ap']} criterios aplicables cumplen", font=fn(20), fill=NEGRO, anchor="ra")
    d.text((W - M, yb + 62), f"{len(ev['fallas'])} por regularizar", font=fb(20), fill=NEGRO, anchor="ra")

    cols = {"NO": (ROJO, "white"), "REG": (AMBAR, NEGRO), "OK": (VERDE, "white")}
    fondo, tx = cols[ev["ver"]]
    if ev["ver"] == "NO":
        tit = "NO INICIAR TRABAJOS"
        sub = ("Existe al menos un criterio crítico incumplido, aunque el cumplimiento supera el 80 %." if ev["crit"] and ev["pct"] >= 80
               else "Hay criterios críticos incumplidos y el cumplimiento es menor al 80 %." if ev["crit"]
               else "El cumplimiento es menor al 80 %. No se deben iniciar trabajos hasta regularizar.")
    elif ev["ver"] == "REG":
        tit = "PUEDE INICIAR TRABAJOS, REGULARIZANDO EN 7 DÍAS HÁBILES"
        sub = f"Fecha límite de regularización: {dat['fecha_limite'].strftime('%d/%m/%Y')}. Todos los criterios listados en este informe deben quedar subsanados."
    else:
        tit, sub = "CONFORME", "Cumple todos los criterios aplicables."
    yv = yb + 120
    d.rounded_rectangle([M, yv, W - M, yv + 150], radius=12, fill=fondo)
    d.text((W // 2, yv + 42), tit, font=_fit(d, tit, RUTAS_NEGRITA, 34, W - 2 * M - 40), fill=tx, anchor="mm")
    for k, l in enumerate(_wrap(d, sub, fn(20), W - 2 * M - 60)[:3]):
        d.text((W // 2, yv + 92 + k * 28), l, font=fn(20), fill=tx, anchor="mm")

    yt = yv + 190
    d.text((M, yt), "Cumplimiento por sección", font=fb(22), fill=NEGRO, anchor="lm")
    yt += 26
    for nombre, pok, pap in ev["pant"]:
        p = (pok / pap * 100) if pap else 100
        d.text((M, yt + 22), nombre, font=_fit(d, nombre, RUTAS_NORMAL, 18, 520), fill=NEGRO, anchor="lm")
        d.text((M + 580, yt + 22), f"{pok} de {pap}", font=fn(18), fill=GRIS, anchor="lm")
        bx = M + 700
        d.rounded_rectangle([bx, yt + 12, bx + 300, yt + 32], radius=8, fill=(230, 230, 230))
        if p > 0:
            d.rounded_rectangle([bx, yt + 12, bx + int(300 * p / 100), yt + 32], radius=8, fill=VERDE if p >= 80 else (ROJO if p < 50 else (230, 150, 0)))
        d.text((W - M, yt + 22), f"{p:.0f} %", font=fb(18), fill=NEGRO, anchor="rm")
        yt += 42
    nota = ("Criterio de evaluación: menos de 80 % de cumplimiento, o un criterio crítico incumplido, implica no iniciar trabajos. "
            "De 80 % a 99 %, se puede iniciar regularizando todo en 7 días hábiles. Los criterios marcados como «No aplica» no se cuentan.")
    for k, l in enumerate(_wrap(d, nota, fn(16), W - 2 * M)):
        d.text((M, yt + 20 + k * 22), l, font=fn(16), fill=GRIS, anchor="lm")
    try:
        import qrcode
        q = qrcode.QRCode(box_size=6, border=1)
        q.add_data(f"{base_url}/?i={dat['codigo_informe']}")
        q.make(fit=True)
        qi = q.make_image(fill_color="black", back_color="white").convert("RGB").resize((130, 130), Image.NEAREST)
        im.paste(qi, (W - M - 130, H - 250))
        d.text((W - M - 65, H - 112), "Verifica este informe", font=fn(13), fill=GRIS, anchor="mm")
    except Exception:
        pass

    # ---------------- Páginas siguientes: criterios por regularizar ----------------
    if ev["fallas"]:
        im, d = nueva(False)
        y = 150
        d.text((M, y), f"Criterios por regularizar ({len(ev['fallas'])})", font=fb(30), fill=NEGRO, anchor="lm")
        y += 36
        _franja(d, y)
        y += 36
        actual = None
        for iid in ev["fallas"]:
            _, texto, norma = POR_ID[iid]
            num = int(iid.split(".")[0])
            pant = next(n for n, ns in PANTALLAS if num in ns)
            lt = _wrap(d, texto, fn(19), W - 2 * M - 110)
            ln = _wrap(d, "Requisito normativo: " + norma, fn(15), W - 2 * M - 110)
            alto = len(lt) * 26 + len(ln) * 20 + 20
            if iid in CRITICOS:
                alto = max(alto, 66)
            extra = 46 if pant != actual else 0
            if y + extra + alto > H - 130:
                im, d = nueva(False)
                y, actual, extra = 150, None, 46
            if pant != actual:
                d.rectangle([M, y, W - M, y + 36], fill=(245, 245, 245))
                d.rectangle([M, y, M + 8, y + 36], fill=AMARILLO)
                d.text((M + 20, y + 18), pant, font=fb(20), fill=NEGRO, anchor="lm")
                y, actual = y + 46, pant
            d.text((M, y + 2), iid, font=fb(19), fill=NEGRO)
            if iid in CRITICOS:
                d.rounded_rectangle([M, y + 32, M + 84, y + 54], radius=6, fill=ROJO)
                d.text((M + 42, y + 43), "CRÍTICO", font=fb(12), fill="white", anchor="mm")
            ty = y + 2
            for l in lt:
                d.text((M + 110, ty), l, font=fn(19), fill=NEGRO)
                ty += 26
            for l in ln:
                d.text((M + 110, ty + 2), l, font=fn(15), fill=GRIS)
                ty += 20
            y += alto
            d.line([M, y - 6, W - M, y - 6], fill=(225, 225, 225), width=1)

    # ---------------- Pie en todas las hojas ----------------
    n = len(paginas)
    for k, pg in enumerate(paginas):
        d = ImageDraw.Draw(pg)
        d.line([M, H - 96, W - M, H - 96], fill=NEGRO, width=2)
        d.text((M, H - 70), "Diagnóstico elaborado por MACGYVER SEGURIDAD EN CONSTRUCCIÓN", font=fb(19), fill=NEGRO, anchor="lm")
        d.text((M, H - 42), "Basado en información declarada por el usuario. No constituye una auditoría en campo.", font=fn(14), fill=GRIS, anchor="lm")
        d.text((W - M, H - 70), f"Página {k + 1} de {n}", font=fn(16), fill=GRIS, anchor="rm")

    buf = io.BytesIO()
    paginas[0].save(buf, "PDF", resolution=150, save_all=True, append_images=paginas[1:])
    return buf.getvalue(), ev
