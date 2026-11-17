# Revisión de privacidad del conjunto público

Fecha: 10 de noviembre de 2026. Revisión de la versión demostrativa de biomedicina e IA.

## Resultado y alcance

Se revisaron los **44 archivos propios públicos** enumerados al final. No se detectaron datos personales del propietario, rutas personales absolutas, credenciales, secretos, datos clínicos individuales ni resultados experimentales propios en ese conjunto. El material científico y los ejemplos actuales utilizan publicaciones públicas, modelos biomédicos de IA y datos de prueba identificados como sintéticos.

Se combinaron lectura de código, datos y documentación con búsquedas de vocabulario, identificadores bibliográficos, nombres, correos, rutas locales, claves y URLs con credenciales. El contraste de sustitución no encontró referencias residuales del conjunto excluido. Los archivos públicos son texto UTF-8, sin enlaces simbólicos ni binarios. Las comprobaciones describen lo observado; no garantizan ausencia de cualquier información sensible desconocida ni certifican la calidad científica.

## Configuración y comunicaciones

El perfil de uso está desactivado y sin conceptos guardados. Su etiqueta es local y no se añade a consultas ni enlaces de búsqueda; esta separación se comprobó también en memoria, sin red ni archivos temporales. Los conceptos que se envíen a fuentes deben ser públicos. Una búsqueda explícita y la renovación de una consulta ya guardada sí contactan proveedores; guardar un perfil o preparar consultas no lo hace.

El servidor escucha solo en loopback, rechaza orígenes ajenos y no publica el directorio del proyecto, su configuración o la caché. La aplicación no registra URLs de consulta. Los errores de cliente desconectado durante el envío se manejan sin imprimir trazas. No se conectan cuentas, publican mensajes ni envían etiquetas locales a buscadores externos.

La selección del navegador se filtra contra el catálogo actual y se persiste al cargar la aplicación. La migración se ejecuta al recargar; no se inspeccionó el navegador personal. El proceso anterior ya no estaba activo en la comprobación final.

## Artefactos locales y exclusiones

En la comprobación final no existían perfil real ni cachés de uso bibliográfico o del radar. Los directorios de copias científicas y temporales de consulta estaban ausentes. Se inventariaron **48 derivados propios actuales** en `.cache/qa`: dos informes JSON y 46 capturas regeneradas. Los textos no conservaron coincidencias del conjunto excluido; se inspeccionó una muestra de capturas que muestra el ejemplo actual. Las 46 PNG solo contienen bloques de imagen estándar, sin EXIF ni bloques de texto embebidos.

Los informes de interfaz registran 116 y 48 estados, respectivamente, con cero violaciones detectadas y cero desbordamientos. Esos resultados son evidencia de QA, no una garantía de accesibilidad completa ni una revisión de cada afirmación recuperada de internet.

`.cache/`, herramientas, entornos, variantes de archivos de entorno, configuración local y derivados del sistema siguen excluidos mediante `.gitignore`. No se auditaron ni modificaron paquetes o binarios de terceros del entorno QA, navegador, caché de instalación o axe. Esas herramientas no integran el conjunto público enumerado. No se inspeccionaron otros proyectos ni archivos personales externos.

## Límite para compartir

No existe `.git` en la raíz: no se auditó un historial local ni un repositorio remoto, y no se publicó contenido. La revisión cubre estos archivos actuales; debe repetirse si se añaden otros. No se atribuye borrado forense del almacenamiento, ni limpieza de copias externas o del historial del navegador.

Compartir solo el inventario revisado. **`.gitignore` no filtra ZIP ni subidas manuales**, y no elimina un archivo ya versionado. Mantener `.cache`, entornos, informes, capturas y configuración personal fuera de la carga pública.

## Inventario revisado

```text
.agents/skills/biomarcadores-arquitectura/SKILL.md
.agents/skills/biomarcadores-calidad/SKILL.md
.agents/skills/biomarcadores-diseno/SKILL.md
.agents/skills/biomarcadores-evidencia/SKILL.md
.agents/skills/biomarcadores-ux/SKILL.md
.gitignore
AGENTS.md
CONCEPTOS_TESIS.md
DESIGN.md
EVIDENCIA_REVISION.md
FUENTES_RADAR.md
PRIVACIDAD_REVISION.md
PRODUCT.md
README.md
VALIDACION.md
cache.py
data/catalog.json
data/journal_metrics.json
data/radar_sources.json
data/reference_review.json
data/reference_seed.json
data/research_concepts.json
journal_guide.py
journal_metrics.py
radar_service.py
radar_sources.py
research_api.py
research_profile.py
scripts/audit_platform.py
scripts/audit_ui.py
scripts/check_local.py
scripts/check_sources.py
server.py
sources.py
static/app.js
static/favicon.svg
static/index.html
static/style.css
tests/test_app.py
tests/test_journal_metrics.py
tests/test_radar_service.py
tests/test_radar_sources.py
tests/test_research_http.py
tests/test_research_profile.py
```
