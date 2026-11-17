---
name: biomarcadores-calidad
description: Verificar etapas de esta aplicación con pruebas funcionales, integridad científica y revisión real de interfaz.
---

# Pruebas y revisión de calidad

## Propósito y aplicación
Aplicar al cerrar etapas y corregir errores. Crear skills o pasar tests aislados no valida la aplicación.

## Pasos
1. Probar adaptadores con respuestas controladas y malformadas, filtros, IDs y fechas; fixtures no son evidencia real.
2. Probar caché fresca/caducada, persistencia, actualización y fallo de ambas fuentes. Confirmar búsqueda real por fuente y registrar resultado.
3. Revisar fuentes de cada afirmación editorial y su alcance. No sumar cifras incompatibles ni ordenar modelos distintos en una escala común.
4. Recorrer búsqueda, filtros, detalle, glosario, comparación, conexiones, tesis y actualización en navegador, con teclado, móvil y escritorio.
5. Corregir fallos y repetir checks afectados. Registrar comandos, resultados y límites en VALIDACION.md, separando simulado, integración real e inspección visual.

## Aceptación
- Servidor arranca en loopback; rutas privadas rechazadas.
- Dos conceptos se comparan por dimensiones, con advertencia sobre contextos/unidades.
- Fuentes enlazadas y fechadas; metadatos no se presentan como texto completo revisado.
- Informe indica qué se comprobó y qué no.

## Ejemplo y errores
Timeout simulado conserva artículos y fecha de descarga y muestra aviso; una consulta real verifica además la API. Evitar confundir mock con búsqueda real, 200 vacío con éxito científico o presencia de citas con revisión independiente.
