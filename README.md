# Atlas de longevidad

Plataforma científica local, en español, para explorar evidencia, seguir conceptos de investigación y descubrir novedades. La biblioteca y la plantilla públicas utilizan **biomedicina e inteligencia artificial**: modelos fundacionales, IA multimodal, modelos unicelulares, célula virtual, modelos genómicos, estructura de proteínas y evaluación de modelos. Son ejemplos educativos, independientes de investigaciones personales.

## Abrir y detener

Requiere Python 3.9 o posterior y un navegador moderno. La aplicación usa únicamente biblioteca estándar Python y HTML/CSS/JavaScript; no necesita cuentas, claves ni servicios de IA. Internet solo es necesario para consultar proveedores o abrir enlaces externos.

Dentro de esta carpeta:

```sh
python3 -B server.py
```

Abre [http://localhost:8765](http://localhost:8765). Para detener, pulsa Ctrl+C en esa terminal. Si el puerto está ocupado, comprueba primero si ya ejecutas el servidor o usa `--port 8766`. Tras actualizar módulos Python, reinicia el servidor y recarga la página.

Escucha exclusivamente en **127.0.0.1**. No se publica, no hay túneles y no se debe cambiar a `0.0.0.0`. No abrir el HTML por doble clic ni usar otro servidor estático: las API y la caché requieren este servidor.

## Recorridos

- **Biblioteca:** nueve conceptos de IA biomédica con diez referencias reales. Busca, filtra por categoría, abre una ficha y despliega métodos, hallazgos y límites. Compara dimensiones; las métricas de problemas distintos no se suman en una escala universal.
- **Novedades:** consulta PubMed, Europe PMC MED, preprints PPR, Crossref o ClinicalTrials.gov. Revisa la consulta pública y las fechas antes de buscar. El intervalo inicial es de 90 días y se muestran hasta 12 registros por fuente.
- **Mi investigación:** configura hasta seis conceptos y cinco variantes por concepto. La plantilla pública de modelos fundacionales biomédicos, IA multimodal y célula virtual se puede reemplazar por cualquier tema. El perfil empieza desactivado; guardarlo no consulta internet. La etiqueta del proyecto es local y no se incorpora a consultas ni enlaces externos.
- **Descubrir conceptos:** sugerencias editoriales con motivo y procedencia. Añadirlas modifica un borrador; no guarda ni busca. Las consultas de cada tema funcionan por separado y los cruces con longevidad se ofrecen aparte. Una coincidencia de palabras no prueba una relación biológica.
- **Innovación:** registros de estudios, consultas copiables para EPO/Espacenet, WIPO/PATENTSCOPE y USPTO, y exploración manual de pistas en Bluesky. No se importan patentes o publicaciones sociales automáticamente.
- **Evidencia y fuentes:** buscador bibliográfico clásico con fechas, tipo y modelo. Ejemplo público: `"artificial intelligence" AND medicine`. Los enlaces originales abren otra pestaña.

Un resultado computacional, una validación externa, un beneficio clínico y una mejora de longevidad son conclusiones distintas. Los ejemplos plantean preguntas; no ejecutan modelos ni ofrecen decisiones médicas.

## Procedencia y calidad

Cada referencia muestra PMID/DOI cuando existe, fecha, fuente y alcance editorial. La semilla contiene metadatos y disponibilidad de resumen; no redistribuye resúmenes completos. Consultar literatura nueva no modifica las explicaciones de la biblioteca ni verifica sus conclusiones.

Q1/Q2 describen revistas según clasificación, categoría y año. Solo se muestran métricas históricas verificadas: **JIF 2023, edición JCR de junio de 2024**, mediante reproducción institucional pública de CNFIS. No son cuartiles actuales ni del año de cada artículo. Las revistas sin cruce legítimo por ISSN mantienen «cuartil no verificado». La guía explica diseño, muestra, controles, calibración, validación externa, sesgo y correcciones; el cuartil no sustituye esos criterios.

PubMed y Europe PMC se solapan. Crossref registra metadatos DOI y busca por relevancia textual, sin ejecutar los booleanos de PubMed de la misma manera. Un DOI no acredita revisión por pares. Los preprints se identifican como preliminares incluso si aparecen en un índice bibliográfico. La fecha de ClinicalTrials.gov es actualización de un registro, no descubrimiento ni prueba de eficacia.

Véanse [EVIDENCIA_REVISION.md](EVIDENCIA_REVISION.md), [FUENTES_RADAR.md](FUENTES_RADAR.md) y [CONCEPTOS_TESIS.md](CONCEPTOS_TESIS.md).

## Caché y privacidad

Las consultas solo salen al proveedor cuando se busca o se renueva una consulta ya enviada. Usa términos públicos. Guardar un perfil no envía su contenido. Mientras el servidor está abierto, revisa cada seis horas sus consultas guardadas: caché bibliográfica de 24 horas y radar de seis horas. Las fechas elegidas se mantienen; amplía el campo final o prepara un período reciente para incluir días nuevos.

Un fallo conserva la copia de la misma consulta y su fecha, con aviso. Sin copia no se inventan resultados. No hay renovación con el servidor detenido ni se garantiza ejecución durante suspensión. Cerrar la pestaña no detiene el proceso.

Perfil y cachés están en `.cache`, excluida de Git. Las escrituras de consultas y perfil usan archivos 0600. Cambiar o eliminar el perfil vacía las consultas del radar; la caché clásica está separada. No se puede retirar una petición ya enviada. La selección del navegador contiene solo IDs de conceptos; al cargar se descartan IDs que ya no existen.

El navegador solo consulta el servidor local; este usa endpoints oficiales fijos. No hay analítica, tipografías remotas, CDN, cuentas, publicación o servicios de IA. Los enlaces externos requieren una acción del usuario. No se sirven la caché, las skills ni el resto del directorio por HTTP.

Antes de compartir, revisa el inventario en [PRIVACIDAD_REVISION.md](PRIVACIDAD_REVISION.md). `.gitignore` no filtra un ZIP o una subida manual, ni elimina archivos previamente versionados.

## Estructura y skills

La interfaz está en `static/`; `sources.py` y `radar_sources.py` acceden a fuentes; `cache.py` y `radar_service.py` gestionan consultas; `research_profile.py` y `research_api.py` preparan el perfil y sus planes; `data/` contiene únicamente ejemplos y referencias públicos. Los fixtures sintéticos están separados en `tests/`.

Las cinco guías del proyecto están en `.agents/skills`: UX, diseño, evidencia, arquitectura y calidad. Se pueden invocar por su nombre. Se crearon siguiendo las instrucciones de `skill-creator`; sus ejemplos actuales también son públicos y genéricos. No modifican instrucciones globales ni certifican la aplicación.

## Verificar

```sh
python3 -B -m unittest discover -s tests -v
python3 -B scripts/check_local.py
python3 -B scripts/check_sources.py
```

La comprobación HTTP requiere el servidor abierto; admite `--port`. La de fuentes requiere internet y usa una consulta pública de IA médica. `check_sources.py --write-seed` renueva los metadatos de los PMID actuales de la semilla, sin incorporar resúmenes íntegros ni modificar la síntesis editorial.

Las auditorías opcionales `scripts/audit_ui.py` y `scripts/audit_platform.py` usan Playwright/Chromium y axe-core aislados en `.cache/qa`, no como dependencias del atlas. Informes y capturas quedan allí excluidos. La segunda usa perfiles temporales y respuestas sintéticas interceptadas.

[VALIDACION.md](VALIDACION.md) registra las comprobaciones actuales y sus límites. No se declara certificación WCAG, revisión sistemática, validación clínica ni cobertura exhaustiva de novedades.
