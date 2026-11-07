"""Exámenes de MACGYVER, uno por curso.

Para agregar un curso nuevo: copia un bloque de EXAMENES_TEXTO, cambia la clave por el
nombre del curso (el mismo que pusiste en la columna `curso` de Supabase) y pega las
preguntas con el mismo formato. No hace falta tocar app.py.
"""
import re

INDUCCION = """
1. ¿Qué es un peligro?
a) Un evento que siempre causa lesiones.
b) Una fuente, situación o acto con potencial de causar daño.
c) Una medida de control implementada en el trabajo.
Respuesta correcta: b

2. ¿Qué es el IPERC de línea base?
a) Un registro de asistencia a las capacitaciones.
b) La identificación de peligros, evaluación de riesgos y determinación de controles para las actividades.
c) Un documento exclusivo para registrar accidentes.
Respuesta correcta: b

3. ¿Qué significa PETS?
a) Programa de Evaluación Técnica de Seguridad.
b) Permiso Especial de Trabajo Seguro.
c) Procedimiento Escrito de Trabajo Seguro.
Respuesta correcta: c

4. ¿Cuál es la finalidad de los equipos de protección personal (EPP)?
a) Reemplazar todos los controles de seguridad.
b) Evitar que se realicen inspecciones de seguridad.
c) Permitir trabajar sin identificar los peligros.
d) Proteger al trabajador frente a los riesgos para los cuales fueron seleccionados.
Respuesta correcta: d

5. ¿Qué información contienen las hojas de datos de seguridad (SDS/HDS)?
a) Únicamente el precio de los productos químicos.
b) Los peligros de los productos químicos y las medidas de prevención y respuesta ante emergencias.
c) Solo el nombre comercial del producto.
Respuesta correcta: b

6. ¿Cuál es el objetivo de las brigadas de emergencia?
a) Organizar la respuesta ante emergencias mediante funciones como lucha contra incendios, primeros auxilios y evacuación.
b) Reemplazar al personal médico en todas las situaciones.
c) Autorizar cualquier trabajo de alto riesgo.
Respuesta correcta: a

7. ¿Qué debe conocer el trabajador sobre los riesgos de su actividad?
a) Solamente el nombre de su supervisor.
b) Únicamente el horario de trabajo.
c) Los peligros identificados, los riesgos asociados y las medidas de control.
Respuesta correcta: c

8. ¿Cómo deben manejarse los residuos en el proyecto?
a) Mezclándolos en un solo recipiente.
b) Dejándolos en cualquier área disponible.
c) Entregándolos sin segregación.
d) Segregándolos por tipo y utilizando los recipientes establecidos según el procedimiento.
Respuesta correcta: d

9. ¿Cuál es la finalidad de los sistemas de protección contra caídas, como barandas y redes?
a) Facilitar el almacenamiento de materiales.
b) Prevenir caídas o reducir sus consecuencias, según el sistema utilizado.
c) Reemplazar la capacitación del trabajador.
Respuesta correcta: b

10. ¿Qué debe verificarse antes de iniciar las labores?
a) Únicamente la asistencia del trabajador.
b) Solo la disponibilidad de herramientas.
c) Inducción aprobada, examen médico ocupacional y SCTR vigentes, EPP adecuado, difusión del IPERC/PETS y capacitaciones y autorizaciones requeridas.
Respuesta correcta: c

11. Durante una operación, una excavadora está trabajando y un compañero se encuentra demasiado cerca de su zona de movimiento. ¿Qué debes hacer?
a) Acercarte para ayudar al operador.
b) Pasar rápidamente detrás de la excavadora.
c) Continuar trabajando porque el operador puede verte.
d) Advertir al compañero, mantenerte fuera de la zona de operación y comunicar la situación.
Respuesta correcta: d

12. Antes de comenzar una tarea, un trabajador manifiesta que no conoce los controles establecidos en el IPERC. ¿Qué corresponde hacer?
a) Solicitar la explicación de los peligros, riesgos y controles antes de iniciar el trabajo.
b) Empezar la tarea y consultar después.
c) Copiar los controles de otra actividad sin verificarlos.
Respuesta correcta: a

13. Un trabajador debe realizar una actividad, pero no conoce el PETS correspondiente. ¿Qué debe hacer?
a) Realizar el trabajo según su experiencia personal.
b) Pedir a un compañero que lo observe mientras trabaja.
c) Solicitar la difusión y explicación del PETS antes de ejecutar la actividad.
Respuesta correcta: c

14. Durante la inspección, un trabajador detecta que sus lentes de seguridad están rotos. ¿Qué debe hacer?
a) Continuar trabajando si el daño parece pequeño.
b) Solicitar el reemplazo de los lentes y no realizar la tarea sin la protección ocular requerida.
c) Utilizar lentes oscuros convencionales.
Respuesta correcta: b

15. Un trabajador debe utilizar un solvente, pero desconoce sus peligros y las medidas de protección necesarias. ¿Qué corresponde hacer?
a) Utilizarlo con las ventanas abiertas, sin más verificaciones.
b) Mezclarlo con otro producto para reducir su peligrosidad.
c) Utilizarlo en pequeñas cantidades sin consultar.
d) Revisar la SDS/HDS, recibir instrucciones y verificar los controles y EPP necesarios.
Respuesta correcta: d

16. Un trabajador debe realizar labores en una plataforma elevada y observa que falta la protección colectiva contra caídas en el borde. ¿Qué debe hacer?
a) No iniciar o detener la actividad y reportar la condición para implementar la protección requerida.
b) Continuar con cuidado y evitar acercarse al borde.
c) Colocar materiales en el borde como barrera provisional sin autorización.
Respuesta correcta: a

17. Durante la jornada, un trabajador observa que un compañero ha sufrido una lesión. ¿Cuál es la actuación correcta?
a) Mover al lesionado inmediatamente, sin evaluar su condición.
b) Comunicar el incidente al supervisor o SSOMA, activar la respuesta de emergencia y gestionar la atención médica.
c) Esperar hasta finalizar el turno para informar.
Respuesta correcta: b

18. Durante un trabajo de soldadura se generan chispas cerca de materiales combustibles y no se han verificado los controles contra incendios. ¿Qué corresponde hacer?
a) Continuar mientras no se observe fuego.
b) Pedir a otro trabajador que vigile, sin detener la actividad.
c) Detener el trabajo, controlar el peligro de incendio y verificar las medidas preventivas antes de reiniciar.
Respuesta correcta: c

19. Un equipo debe instalar una estructura metálica sobre una plataforma elevada. Durante la inspección se identifica que falta una baranda en el borde, un trabajador no puede acreditar la capacitación requerida, el sistema personal de protección contra caídas no ha sido inspeccionado, el ATS no considera las condiciones reales de la tarea y debajo de la plataforma circulan otros trabajadores sin restricción de acceso. ¿Qué decisión corresponde tomar?
a) Iniciar el trabajo utilizando únicamente el sistema personal de protección contra caídas.
b) Permitir que el trabajador sin capacitación participe bajo supervisión.
c) Actualizar el ATS después de finalizar la instalación y continuar con precaución.
d) No iniciar hasta implementar la protección colectiva, verificar la capacitación y autorización, inspeccionar el sistema anticaídas, actualizar el ATS y restringir el acceso al área inferior.
Respuesta correcta: d

20. Antes de iniciar una excavación cercana a instalaciones eléctricas y tuberías enterradas, el equipo no ha confirmado la ubicación de los servicios, no ha evaluado la estabilidad del terreno, el ATS no contempla todos los peligros y se pretende utilizar una excavadora mientras hay trabajadores realizando labores manuales dentro de la excavación. ¿Qué debe hacerse?
a) Iniciar la excavación lentamente y detenerse si aparece alguna tubería.
b) Suspender el inicio hasta localizar los servicios enterrados, evaluar la estabilidad del terreno, definir la protección contra derrumbes, asegurar accesos, delimitar el área, controlar la interacción entre maquinaria y trabajadores, verificar los permisos aplicables y actualizar el ATS.
c) Permitir el ingreso de los trabajadores mientras el operador mantenga contacto visual.
d) Continuar con la excavación y completar los documentos al finalizar.
Respuesta correcta: b
"""

EXCAVACIONES = """
1. ¿Cuál es la distancia máxima longitudinal establecida para considerar la instalación de una escalera adicional en una excavación extensa?
a) Cada 6.00 metros de longitud.
b) Cada 7.00 metros de longitud.
c) Cada 7.60 metros de longitud.
d) Cada 8.00 metros de longitud.
Respuesta correcta: c

2. ¿Cuánto debe sobresalir una escalera por encima del nivel superior de apoyo de la excavación?
a) Como mínimo 0.80 metros.
b) Como mínimo 1.00 metro.
c) Como mínimo 1.20 metros.
d) Como mínimo 1.50 metros.
Respuesta correcta: b

3. ¿Qué relación de inclinación debe respetarse al instalar una escalera apoyada contra una superficie vertical?
a) 1 metro de separación horizontal por cada 3 metros de altura.
b) 1 metro de separación horizontal por cada 4 metros de altura.
c) 1 metro de separación horizontal por cada 5 metros de altura.
d) 1 metro de separación horizontal por cada 6 metros de altura.
Respuesta correcta: b

4. Si una excavación tiene una profundidad de 4 metros, ¿a qué distancia horizontal de su borde deben mantenerse los materiales, herramientas y equipos, aplicando el criterio H/2?
a) 1.00 metro.
b) 1.50 metros.
c) 2.00 metros.
d) 2.50 metros.
Respuesta correcta: c

5. ¿A partir de qué profundidad se recomienda implementar una malla de protección en la excavación, según la capacitación?
a) Mayor a 1.00 metro.
b) Mayor a 1.20 metros.
c) Mayor a 1.50 metros.
d) Mayor a 1.80 metros.
Respuesta correcta: c

6. ¿Cuál es la principal limitación de la malla Raschel cuando se utiliza como protección superficial en una excavación?
a) No permite delimitar áreas de trabajo ni controlar la dispersión de polvo.
b) No tiene capacidad para soportar cargas del terreno ni reemplazar un sistema de sostenimiento.
c) No puede instalarse en excavaciones que tengan presencia de material particulado.
d) No permite proteger contra la caída de partículas pequeñas desde la superficie.
Respuesta correcta: b

7. Una excavación presenta una profundidad de 6 metros. Aplicando el criterio H/2, ¿a qué distancia mínima deben ubicarse los materiales, herramientas y equipos respecto al borde?
a) 2.00 metros.
b) 2.50 metros.
c) 3.00 metros.
d) 3.50 metros.
Respuesta correcta: c

8. ¿Cuál es el rango de concentración de oxígeno indicado en la capacitación para considerar que la atmósfera se encuentra dentro de los valores establecidos?
a) De 18.5 % a 23.5 %.
b) De 19.0 % a 23.0 %.
c) De 19.5 % a 23.5 %.
d) De 20.0 % a 24.0 %.
Respuesta correcta: c

9. Si durante la evaluación atmosférica se obtiene una concentración de oxígeno de 19.0 %, ¿qué decisión corresponde adoptar según la capacitación?
a) Permitir el ingreso utilizando únicamente protección respiratoria.
b) Permitir el ingreso si la actividad tiene una duración menor a 15 minutos.
c) No permitir el ingreso y evaluar las condiciones de la atmósfera.
d) Permitir el ingreso si existe un vigía permanente en superficie.
Respuesta correcta: c

10. ¿Qué equipo se presenta en la capacitación como referencia para realizar mediciones de gases y condiciones atmosféricas peligrosas?
a) Detector multigás ALTAIR 4XR de MSA.
b) Detector multigás ALTAIR 5X de MSA.
c) Detector multigás ALTAIR 2X de MSA.
d) Detector multigás ALTAIR 6X de MSA.
Respuesta correcta: b

11. ¿Cuál es la finalidad principal de realizar un sondaje de interferencias antes de ejecutar una excavación?
a) Determinar la resistencia mecánica del terreno y seleccionar el equipo de excavación.
b) Identificar redes subterráneas de electricidad, agua, telecomunicaciones y otras instalaciones.
c) Establecer la profundidad máxima de excavación y la distancia de las escaleras.
d) Identificar exclusivamente las redes eléctricas que atraviesan el área de trabajo.
Respuesta correcta: b

12. ¿Cuál de las siguientes condiciones describe correctamente la función de una persona competente durante los trabajos de excavación?
a) Autorizar el trabajo únicamente después de verificar la disponibilidad de EPP.
b) Evaluar las condiciones de la excavación y validar las medidas de control correspondientes.
c) Supervisar exclusivamente el uso de maquinaria y la circulación de volquetes.
d) Aprobar el ingreso de trabajadores cuando exista una escalera instalada.
Respuesta correcta: b

13. ¿En qué situación debe evaluarse la necesidad de realizar mediciones de oxígeno, gases y vapores en una excavación?
a) Únicamente cuando la excavación supera los 3 metros de profundidad.
b) Cuando exista la posibilidad de presencia de una atmósfera peligrosa.
c) Exclusivamente cuando se desarrollen trabajos de soldadura en superficie.
d) Solo cuando se detecten olores extraños durante la jornada laboral.
Respuesta correcta: b

14. ¿Cuál de las siguientes situaciones representa una condición de exposición a la línea de fuego durante el uso de maquinaria?
a) Permanecer fuera del radio de operación, detrás de una barrera física.
b) Ubicarse debajo de un cucharón elevado durante una maniobra de equipo.
c) Mantener comunicación visual con el operador desde una zona segregada.
d) Permanecer en un área señalizada fuera de la trayectoria de desplazamiento.
Respuesta correcta: b

15. ¿Qué característica debe cumplir el vigía o cuadrador asignado para apoyar las maniobras de equipos?
a) Tener experiencia general en construcción y conocer las rutas de tránsito.
b) Ser competente, estar capacitado y conocer las señales de comunicación establecidas.
c) Contar con autorización del operador, aunque no conozca las señales de maniobra.
d) Permanecer en la zona de operación y comunicarse únicamente mediante silbatos.
Respuesta correcta: b

16. ¿Cuál es el control adecuado cuando vehículos o equipos pesados se encuentran próximos al borde de una excavación?
a) Mantenerlos a una distancia fija de 1 metro, independientemente de la profundidad.
b) Evaluar su proximidad, considerando las cargas y vibraciones que pueden favorecer un colapso.
c) Permitir su circulación siempre que el terreno se encuentre visualmente compactado.
d) Mantenerlos a una distancia equivalente a un cuarto de la profundidad de excavación.
Respuesta correcta: b

17. Para una excavación de 2 metros de profundidad, ¿qué distancia corresponde aplicar como criterio H/2 para ubicar materiales y equipos respecto al borde?
a) 0.50 metros.
b) 0.75 metros.
c) 1.00 metro.
d) 1.50 metros.
Respuesta correcta: c

18. Según los controles críticos presentados, ¿a partir de qué profundidad se indica gestionar el PETAR de trabajos en altura para las actividades relacionadas con excavaciones?
a) Excavaciones mayores a 1.50 metros.
b) Excavaciones mayores a 1.60 metros.
c) Excavaciones mayores a 1.80 metros.
d) Excavaciones mayores a 2.00 metros.
Respuesta correcta: c

19. ¿Qué medida de control se establece para reducir la generación de polvo durante las actividades de movimiento de tierras?
a) Regar las vías para disminuir la suspensión de material particulado.
b) Humedecer únicamente el área de excavación al finalizar la jornada.
c) Regar las vías solamente cuando la visibilidad del operador sea inferior a 10 metros.
d) Utilizar protección respiratoria como único control frente al polvo generado.
Respuesta correcta: a

20. ¿Cuál de las siguientes combinaciones reúne correctamente los criterios de instalación y aseguramiento de una escalera en una excavación?
a) Instalación cada 7.60 m, inclinación 1:4, sobresalir 0.80 m y asegurarla al terreno.
b) Instalación cada 7.60 m, inclinación 1:4, sobresalir 1.00 m y asegurarla al soporte.
c) Instalación cada 8.00 m, inclinación 1:5, sobresalir 1.00 m y asegurarla al soporte.
d) Instalación cada 7.00 m, inclinación 1:4, sobresalir 1.20 m y asegurarla al terreno.
Respuesta correcta: b
"""


def leer_examen(texto):
    """Convierte el texto de un examen en [{'p': pregunta, 'o': [opciones], 'c': índice}]."""
    preguntas, actual = [], None
    for linea in texto.splitlines():
        l = linea.strip()
        if not l:
            continue
        m_preg = re.match(r"^(\d+)\.\s+(.*)$", l)
        m_opc = re.match(r"^([a-h])\)\s+(.*)$", l)
        m_res = re.match(r"^Respuesta correcta:\s*([a-h])\s*$", l, flags=re.I)
        if m_res and actual:
            actual["c"] = "abcdefgh".index(m_res.group(1).lower())
        elif m_opc and actual:
            actual["o"].append(m_opc.group(2).strip())
        elif m_preg:
            actual = {"p": m_preg.group(2).strip(), "o": [], "c": None}
            preguntas.append(actual)
        elif actual and not actual["o"]:
            actual["p"] += " " + l
    for i, q in enumerate(preguntas, 1):
        if q["c"] is None or q["c"] >= len(q["o"]) or len(q["o"]) < 2:
            raise ValueError(f"La pregunta {i} está mal escrita: {q['p'][:60]}")
    return preguntas


# Clave = valor de la columna `curso` en Supabase.
EXAMENES = {
    "induccion_ssoma": {
        "titulo": "EVALUACIÓN DE INDUCCIÓN DE SEGURIDAD, SALUD OCUPACIONAL Y MEDIO AMBIENTE",
        "corto": "EVALUACIÓN DE INDUCCIÓN",
        "nota_min": 70,
        "preguntas": leer_examen(INDUCCION),
    },
    "excavaciones": {
        "titulo": "EVALUACIÓN – CAPACITACIÓN DE EXCAVACIONES Y ZANJAS",
        "corto": "EVALUACIÓN DE EXCAVACIONES Y ZANJAS",
        "nota_min": 70,
        "preguntas": leer_examen(EXCAVACIONES),
    },
}


# ---------------------------------------------------------------------------
# Catálogo del botón CAPACITACIONES. (clave del curso, nombre en el botón)
# La clave debe coincidir con la columna `curso` de Supabase.
# Un botón se activa solo cuando su clave existe en EXAMENES (arriba).
# ---------------------------------------------------------------------------
ESPECIFICAS = [
    ("trabajos_altura", "Trabajos en altura"),
    ("excavaciones", "Excavación de zanjas"),
    ("espacio_confinado", "Trabajos en espacio confinado"),
    ("izaje", "Operaciones de izaje"),
    ("trabajos_caliente", "Trabajos en caliente"),
    ("temperaturas_extremas", "Trabajos en temperaturas extremas"),
    ("energia_electrica", "Trabajos con energía eléctrica"),
    ("loto", "Sistema de bloqueo, rotulado o etiquetado (LOTO)"),
    ("ergonomia", "Ergonomía"),
]

OTRAS = [
    ("interaccion_hombre_maquina", "Interacción hombre-máquina"),
    ("iperc", "IPERC"),
    ("icam", "Investigación de accidentes metodología ICAM"),
    ("mapa_riesgos_evacuacion", "Mapa de riesgos y evacuación"),
    ("codigo_colores_senales", "Código de colores y señales"),
    ("manejo_defensivo", "Manejo defensivo"),
    ("liderazgo_visible_vfl", "Liderazgo visible en seguridad (VFL)"),
    ("higiene_ocupacional", "Higiene ocupacional"),
    ("uso_mantenimiento_epp", "Uso y mantenimiento de EPP"),
    ("sbc", "Seguridad basada en el comportamiento (SBC)"),
    ("segregacion_residuos", "Segregación de residuos sólidos"),
    ("aspectos_ambientales", "Aspectos ambientales significativos"),
    ("gestion_rcd", "Gestión de RCD en obras"),
    ("materiales_peligrosos", "Materiales peligrosos"),
    ("brigada_primeros_auxilios", "Formación de brigadista de primeros auxilios"),
    ("brigada_incendios", "Formación de brigadista de lucha contra incendios"),
    ("brigada_evacuacion_rescate", "Formación de brigadista de evacuación y rescate"),
    ("brigada_materiales_peligrosos", "Formación de brigadista de materiales peligrosos"),
    ("funciones_comite_sst", "Funciones del Comité/Supervisor de SST"),
    ("funciones_comite_tecnico", "Funciones del Comité Técnico de Coordinación de SST"),
]
