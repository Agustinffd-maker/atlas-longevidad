---
name: biomarcadores-ux
description: Diseñar y revisar recorridos, estados y accesibilidad de esta aplicación local de biomarcadores.
---

# Interacción y experiencia de usuario

## Propósito y aplicación
Aplicar al crear o cambiar búsqueda, fichas, comparación, filtros, navegación o glosario. La tarea principal es aprender y contrastar evidencia.

## Pasos
1. Recorrer buscar → abrir ficha → profundizar → consultar fuente → seleccionar → comparar. Conservar búsqueda y selección al volver.
2. Mostrar una explicación sencilla primero; desplegar métodos, límites y fuentes. Los términos técnicos abren una definición accesible.
3. Distinguir búsqueda local de consulta externa e indicar qué se enviará. No enviar datos privados por defecto.
4. Diseñar carga, error recuperable, cero resultados y caché sin conexión. Conservar resultados válidos si falla la actualización.
5. Probar teclado, foco visible, etiquetas, anuncios de estado y anchos de 390 y 1440 px.

## Aceptación
- Buscar, filtrar, abrir, volver y comparar dos fichas funciona con teclado.
- Un error ofrece reintentar; un vacío ofrece limpiar filtros.
- Selección y cantidad coinciden; todos los controles cumplen su etiqueta.
- Los diálogos cierran con Escape y devuelven foco. Nada depende solo de hover.

## Ejemplo y errores
Buscar «biología computacional» permite comparar modelos unicelulares y célula virtual y regresar conservando filtros. Evitar Enter que recarga la página, iconos sin etiqueta y confundir «sin conexión» con «sin evidencia».
