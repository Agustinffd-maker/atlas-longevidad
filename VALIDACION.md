# Validación de la versión pública de biomedicina e IA

Fecha: 10 de noviembre de 2026. Este registro describe el contenido público actual. No reproduce ejemplos o contexto de investigaciones personales.

## Alcance

Biblioteca de nueve conceptos de IA biomédica, diez referencias, perfil de investigación configurable y radar de cinco canales oficiales. Se mantienen las funciones de búsqueda, comparación, glosario, novedades, innovación, patentes preparadas y sugerencias de conceptos.

Se aplicaron las cinco skills locales. Sus ejemplos se actualizaron siguiendo las instrucciones de `skill-creator`; no se modificaron instrucciones globales. Las herramientas opcionales PyYAML, Playwright/Chromium y axe-core se usan únicamente en `.cache/qa`, excluida de Git. La aplicación conserva Python estándar y HTML/CSS/JavaScript.

La revisión cubre código, datos, fixtures, scripts, skills y documentación. También se retiraron artefactos generados de ejemplos anteriores, sin conservar copias dentro del proyecto. El servidor se reinicia para que la memoria no reconstruya cachés retiradas; el navegador filtra y guarda únicamente IDs de selección válidos al volver a cargar.

## Evidencia

Diez referencias reales de modelos fundacionales, IA multimodal, modelos unicelulares, célula virtual, modelos genómicos, predicción estructural y evaluación clínica. Siete textos abiertos se revisaron por secciones; tres referencias usan metadatos/resumen. Las notas individuales y los límites están en [EVIDENCIA_REVISION.md](EVIDENCIA_REVISION.md).

El registro de revistas contiene cinco cruces por ISSN con JIF 2023, edición JCR junio de 2024. No se atribuyen cuartiles actuales ni calidad de un estudio por su revista. Las pruebas de cruce usan una clasificación sintética separada, para no depender de la selección científica de la biblioteca.

El radar identifica fuente, fecha y alcance. PubMed y Europe PMC se solapan; Crossref no ejecuta los booleanos de PubMed de la misma manera. La actualización de un registro de estudio no es una publicación de resultados. No se importan automáticamente patentes o conversación social.

## Comprobaciones

Resultado actual: **64 pruebas de código/API correctas, 13 comprobaciones HTTP correctas y cinco skills válidas mediante el validador oficial**. La identidad de las diez referencias nuevas se comprobó con metadatos oficiales. La consulta pública de IA médica respondió en PubMed y Europe PMC con 20 registros por proveedor; no se guardó en la caché ni se interpretó como evaluación de pertinencia. Los resultados y capturas técnicos se generaron de nuevo en `.cache/qa`, sin datos personales ni perfiles reales.

| Matriz de navegador | Estados | Resultado |
| --- | --- | --- |
| Biblioteca, navegación y regresión | 116 | Cero violaciones axe detectadas, desbordamientos o errores de página; 176 paradas de foco sin controles tapados |
| Plataforma y perfil temporal | 48 | Cero violaciones axe detectadas, desbordamientos, errores de página o solicitudes externas |

Se inspeccionaron capturas nuevas de móvil/escritorio y glosario. La matriz de biblioteca conserva 12 comprobaciones incompletas de contraste del diálogo/bandeja, revisadas mediante colores y capturas: texto `#213c34` sobre `#f8f9f5` (11,28:1), blanco sobre `#1b3e34` (11,76:1) y texto secundario `#d4e3d4` (8,82:1). No se presentan como pruebas automáticas superadas. La matriz de plataforma no dejó comprobaciones incompletas.

Pruebas de código y API:

```sh
python3 -B -m unittest discover -s tests -v
python3 -B scripts/check_local.py --port 8767
```

Las pruebas HTTP usan loopback y perfiles temporales. Cubren entrada/respuesta inválida, consultas, filtros, caché, actualización, errores, procedencia, preprints, retractaciones informadas, registros, perfil sin red, permisos privados, revocación y cliente desconectado. Los fixtures están marcados sintéticos y no se sirven como evidencia.

Auditorías opcionales con el entorno QA ya preparado y servidor local:

```sh
PLAYWRIGHT_BROWSERS_PATH="$PWD/.cache/qa/browsers" .cache/qa/env/bin/python -B scripts/audit_ui.py
PLAYWRIGHT_BROWSERS_PATH="$PWD/.cache/qa/browsers" .cache/qa/env/bin/python -B scripts/audit_platform.py
```

Incluyen 320, 390, 768 y 1440 CSS px; navegación, búsqueda sin tildes, filtro, detalle con despliegues anidados, comparación de dos/nueve conceptos, glosario con Tab/Shift+Tab/Escape y retorno, carga/vacío/error, perfil temporal y consultas preparadas sin envío. Las respuestas científicas de interfaz se interceptan; la integración real se comprueba por separado. El portapapeles se simula para no cambiar el personal.

## Privacidad y publicación

Perfil y cachés están excluidos de Git; sus escrituras usan archivos 0600 y directorios nuevos 0700. No hay analítica, cuentas, servicios de IA, despliegue ni acceso desde otros equipos. El servidor solo sirve rutas permitidas en loopback y no registra URLs de consultas.

Guardar o eliminar un perfil limpia las búsquedas del radar, cancela el estado anterior y revoca respuestas tardías. No retira consultas ya enviadas a terceros. La caché bibliográfica está separada. No se garantiza eliminación forense o borrado de copias fuera de este proyecto.

La auditoría independiente y el inventario final están en [PRIVACIDAD_REVISION.md](PRIVACIDAD_REVISION.md). Sin `.git` no existe historial local para revisar; no se publica ni se audita un remoto. El servidor anterior fue detenido tras confirmar su comando y carpeta; la versión actual quedó disponible en localhost:8765, solo en loopback. El puerto de pruebas 8767 se cerró. `.gitignore` no protege ZIP o subidas manuales.

## Límites

Cero violaciones detectadas por una herramienta no equivale a certificación WCAG. No se probó lector de pantalla, dispositivos físicos ni la matriz completa en todos los navegadores o con zoom real 200/400 %. Las comprobaciones de contraste incompletas se conservan y revisan manualmente.

No se evalúa automáticamente riesgo de sesgo, causalidad o eficacia, ni se ejecutan modelos biomédicos. Tampoco se garantiza vigilancia exhaustiva, disponibilidad permanente de fuentes o ejecución con el computador suspendido. Las consultas mantienen las fechas elegidas y necesitan ampliar el rango para nuevos días.


## Continuación en Codex · 11 de noviembre de 2026

Se copió el proyecto completo al espacio de este chat, conservando el original. Se verificó la igualdad SHA-256 de los 1363 archivos copiados y los destinos de enlaces simbólicos antes de ejecutar comprobaciones. Se incluyen código, datos, tests, scripts, documentación, las cinco skills y `.cache` local con informes y herramientas de QA. No se importó el historial del chat como contenido del proyecto.

En esta copia pasaron 64 pruebas de código/API y 13 comprobaciones HTTP. El entorno restringido impedía abrir puertos locales; las verificaciones se repitieron con permiso del entorno y un servidor temporal en 127.0.0.1:8768, detenido al terminar. No se repitieron las auditorías visuales, la integración con proveedores externos ni el validador de skills. No se publicaron archivos ni se modificó el código funcional.

Los entornos virtuales y herramientas descargadas de `.cache/qa` se conservaron como artefactos locales; copiarlos no garantiza que todas sus rutas internas sean reubicables. La aplicación principal sigue usando únicamente Python estándar y HTML/CSS/JavaScript.


## Preparación de repositorio público · 17 de noviembre de 2026

El usuario autorizó publicar el código de esta copia como Agustinffd-maker/atlas-longevidad para su entrega académica. Se conserva la exclusión de `.cache`, entornos y configuración local mediante `.gitignore`; el conjunto público contiene 44 archivos propios. Se revisaron patrones de credenciales, rutas personales y datos identificables sin coincidencias sensibles. Publicar el código no despliega el servidor ni cambia su aislamiento en loopback. Los resultados de pruebas anteriores conservan sus fechas; no se atribuye una nueva auditoría visual o científica.
