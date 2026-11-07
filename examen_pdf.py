"""Hojas de examen para el PDF del certificado (MACGYVER).

paginas_examen() devuelve 1 o 2 imágenes del mismo tamaño que el certificado:
preguntas en dos columnas, con TODAS las opciones; la opción marcada va en
verde (✓) si acertó y en rojo (✗) si se equivocó. No muestra la respuesta correcta.
"""
from PIL import Image, ImageDraw, ImageFont

REF_W = 1623
VERDE = ((217, 244, 226), (31, 157, 85), (10, 70, 35))
ROJO = ((253, 226, 226), (214, 48, 49), (140, 20, 20))
TINTA = (25, 25, 25)
GRIS = (110, 110, 110)

RUTAS_NEGRITA = ["fuente.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                 "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]
RUTAS_NORMAL = ["fuente_regular.ttf", "fuente.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]


def _fuente(rutas, tam):
    for r in rutas:
        try:
            return ImageFont.truetype(r, tam)
        except OSError:
            continue
    return ImageFont.load_default(tam)


def _wrap(draw, texto, f, ancho):
    lineas, act = [], ""
    for p in str(texto).split():
        t = (act + " " + p).strip()
        if draw.textlength(t, font=f) <= ancho:
            act = t
        else:
            if act:
                lineas.append(act)
            act = p
    if act:
        lineas.append(act)
    return lineas or [""]


def _marcas(dat, preguntas):
    """Índice de la opción que marcó el alumno en cada pregunta (None si no se sabe)."""
    det = dat.get("respuestas") or []
    out = []
    for i, q in enumerate(preguntas):
        sel = None
        if i < len(det) and isinstance(det[i], dict):
            try:
                sel = q["o"].index(det[i].get("respuesta"))
            except ValueError:
                sel = None
        out.append(sel)
    return out


def _bloques(draw, preguntas, tam, colw):
    fb, fn = _fuente(RUTAS_NEGRITA, tam), _fuente(RUTAS_NORMAL, tam)
    lh = int(tam * 1.28)
    sangria, marca_w = int(tam * 1.5), int(tam * 1.6)
    sep_o, sep_p = int(tam * 0.25), int(tam * 0.9)
    bloques = []
    for i, q in enumerate(preguntas):
        ql = _wrap(draw, f"{i + 1}. {q['p']}", fb, colw)
        ops = [_wrap(draw, f"{'abcdefgh'[k]}) {t}", fn, colw - sangria - marca_w)
               for k, t in enumerate(q["o"])]
        h = len(ql) * lh + sep_o + sum(len(o) * lh + sep_o for o in ops) + sep_p
        bloques.append((ql, ops, h))
    geo = dict(lh=lh, sangria=sangria, marca_w=marca_w, sep_o=sep_o, fb=fb, fn=fn)
    return bloques, geo


def _paginar(bloques, tops, bottom):
    pos, pag, col, y = [], 0, 0, tops[0]
    for b in bloques:
        h = b[2]
        if y + h > bottom:
            col += 1
            if col == 2:
                pag, col = pag + 1, 0
                if pag >= len(tops):
                    return None
            y = tops[pag]
            if y + h > bottom:
                return None
        pos.append((pag, col, y))
        y += h
    return pos


def _ajustar(draw, texto, rutas, tam, ancho):
    f = _fuente(rutas, tam)
    while draw.textlength(texto, font=f) > ancho and tam > 10:
        tam -= 1
        f = _fuente(rutas, tam)
    return f


def paginas_examen(W, H, dat, preguntas):
    s = W / REF_W
    marcas = _marcas(dat, preguntas)
    mar = int(40 * s)
    gap = int(30 * s)
    pad = int(14 * s)
    colw = (W - 2 * mar - gap - 2 * pad) // 2
    top0 = int(392 * s)
    top1 = mar + int(80 * s)
    bottom = H - mar - int(50 * s)
    medidor = ImageDraw.Draw(Image.new("RGB", (10, 10)))

    pos = None
    for ref in range(26, 11, -1):
        tam = max(int(ref * s), 8)
        bloques, geo = _bloques(medidor, preguntas, tam, colw)
        pos = _paginar(bloques, [top0, top1], bottom)
        if pos:
            break
    if not pos:  # último recurso: no debería ocurrir
        pos = []
        y = top0
        for b in bloques:
            pos.append((0, 0, y))
            y += b[2]

    n = max(p[0] for p in pos) + 1
    imgs = [Image.new("RGB", (W, H), "white") for _ in range(n)]
    dr = [ImageDraw.Draw(im) for im in imgs]
    lh, sangria, marca_w, sep_o = geo["lh"], geo["sangria"], geo["marca_w"], geo["sep_o"]
    fb, fn = geo["fb"], geo["fn"]
    trazo = max(2, int(tam * 0.18))

    for pg in range(n):
        d = dr[pg]
        top = top0 if pg == 0 else top1
        d.rectangle([mar - 6, top - 10, W - mar + 6, bottom + 10], outline=TINTA, width=3)
        d.line([mar + pad + colw + gap // 2, top - 10, mar + pad + colw + gap // 2, bottom + 10], fill=TINTA, width=2)
        pie = f"{dat.get('cert', '')}  ·  MACGYVER Seguridad en Construcción  ·  Hoja {pg + 1} de {n} del examen"
        fp = _fuente(RUTAS_NORMAL, int(15 * s))
        d.text((W // 2, H - mar - int(22 * s)), pie, font=fp, fill=GRIS, anchor="mm")

    # ---------- Encabezado hoja 1 ----------
    d = dr[0]
    titulo = dat.get("titulo_examen") or "EVALUACIÓN DE INDUCCIÓN DE SEGURIDAD, SALUD OCUPACIONAL Y MEDIO AMBIENTE"
    ft = _ajustar(d, titulo, RUTAS_NEGRITA, int(30 * s), W - 2 * mar)
    d.text((W // 2, mar + int(30 * s)), titulo, font=ft, fill=TINTA, anchor="mm")
    bx0, by0, bx1 = mar, int(100 * s), W - mar
    fila = int(46 * s)
    by1 = by0 + 5 * fila
    div = bx1 - int(330 * s)
    d.rectangle([bx0, by0, bx1, by1], outline=TINTA, width=3)
    d.line([div, by0, div, by1], fill=TINTA, width=3)
    for k in range(1, 5):
        d.line([bx0, by0 + k * fila, div, by0 + k * fila], fill=TINTA, width=2)
    tam_c = int(20 * s)
    lb = _fuente(RUTAS_NEGRITA, tam_c)

    def campo(x, fila_i, etiqueta, valor, x_fin):
        cy = by0 + fila_i * fila + fila // 2
        d.text((x, cy), etiqueta, font=lb, fill=TINTA, anchor="lm")
        xv = x + int(d.textlength(etiqueta, font=lb)) + int(10 * s)
        fv = _ajustar(d, str(valor), RUTAS_NORMAL, tam_c, x_fin - xv - 8)
        d.text((xv, cy), str(valor), font=fv, fill=TINTA, anchor="lm")

    campo(bx0 + 10, 0, "APELLIDOS Y NOMBRES:", str(dat.get("nombre", "")).upper(), div)
    campo(bx0 + 10, 1, "EMPRESA:", str(dat.get("empresa", "")).upper(), div)
    mitad = bx0 + (div - bx0) // 2
    campo(bx0 + 10, 2, "PROYECTO:", str(dat.get("proyecto") or "-").upper(), div)
    campo(bx0 + 10, 3, "DNI:", dat.get("dni", ""), mitad)
    d.line([mitad, by0 + 3 * fila, mitad, by0 + 4 * fila], fill=TINTA, width=2)
    campo(mitad + 10, 3, "CARGO:", str(dat.get("cargo", "")).upper(), div)
    campo(bx0 + 10, 4, "FECHA:", dat.get("fecha", ""), div)
    d.text(((div + bx1) // 2, by0 + int(44 * s)), "NOTA", font=lb, fill=TINTA, anchor="mm")
    fnota = _ajustar(d, str(dat.get("nota", "")), RUTAS_NEGRITA, int(34 * s), bx1 - div - 20)
    d.text(((div + bx1) // 2, by0 + int(118 * s)), str(dat.get("nota", "")), font=fnota, fill=VERDE[2], anchor="mm")
    d.text(((div + bx1) // 2, by0 + int(188 * s)), "APROBADO", font=lb, fill=VERDE[1], anchor="mm")

    # leyenda
    ly = by1 + int(14 * s)
    fl = _fuente(RUTAS_NORMAL, int(16 * s))
    d.rectangle([mar, ly, mar + int(22 * s), ly + int(16 * s)], fill=VERDE[0], outline=VERDE[1], width=2)
    d.text((mar + int(30 * s), ly + int(8 * s)), "Respuesta marcada y correcta", font=fl, fill=TINTA, anchor="lm")
    x2 = mar + int(380 * s)
    d.rectangle([x2, ly, x2 + int(22 * s), ly + int(16 * s)], fill=ROJO[0], outline=ROJO[1], width=2)
    d.text((x2 + int(30 * s), ly + int(8 * s)), "Respuesta marcada e incorrecta", font=fl, fill=TINTA, anchor="lm")

    # ---------- Encabezado hoja 2 ----------
    if n > 1:
        d = dr[1]
        t2 = f"{dat.get('titulo_examen_corto') or 'EVALUACIÓN DE INDUCCIÓN'} (continuación)  ·  {str(dat.get('nombre', '')).upper()}  ·  DNI {dat.get('dni', '')}"
        f2 = _ajustar(d, t2, RUTAS_NEGRITA, int(22 * s), W - 2 * mar)
        d.text((W // 2, mar + int(30 * s)), t2, font=f2, fill=TINTA, anchor="mm")

    # ---------- Preguntas ----------
    for i, ((pg, col, y), (ql, ops, _)) in enumerate(zip(pos, bloques)):
        d = dr[pg]
        x0 = mar + pad + col * (colw + gap)
        for l in ql:
            d.text((x0, y), l, font=fb, fill=TINTA)
            y += lh
        y += sep_o
        for k, ol in enumerate(ops):
            alto = len(ol) * lh
            sel = marcas[i]
            color = TINTA
            if sel == k:
                ok = (k == preguntas[i]["c"])
                fondo, borde, color = VERDE if ok else ROJO
                d.rectangle([x0 + sangria - 8, y - 2, x0 + colw, y + alto + 2],
                            fill=fondo, outline=borde, width=2)
                cx, cy, r = x0 + colw - marca_w // 2, y + lh // 2 + 2, int(tam * 0.42)
                if ok:
                    d.line([(cx - r, cy), (cx - r // 3, cy + int(r * 0.7)), (cx + r, cy - int(r * 0.7))],
                           fill=borde, width=trazo, joint="curve")
                else:
                    d.line([(cx - r, cy - r), (cx + r, cy + r)], fill=borde, width=trazo)
                    d.line([(cx - r, cy + r), (cx + r, cy - r)], fill=borde, width=trazo)
            for l in ol:
                d.text((x0 + sangria, y), l, font=fn, fill=color)
                y += lh
            y += sep_o
    return imgs
