# Perfil configurable de investigación

Configuración local separada del contenido científico compartido. Empieza desactivada y vacía. La interfaz ofrece una plantilla pública editable de **modelos fundacionales biomédicos, IA multimodal y célula virtual**; no representa el trabajo personal de quien use la plataforma.

## Uso

Hasta seis conceptos y cinco variantes por concepto. Se pueden introducir términos que no estén en el catálogo. Guardar no consulta internet. La etiqueta es solo local; las búsquedas y enlaces externos contienen únicamente la consulta pública elegida.

Cada tema se busca por separado con variantes OR. Los puentes con longevidad añaden una intersección explícita, sin obligar a que todos los temas aparezcan juntos. Las consultas tienen un máximo de 1000 caracteres y se previsualizan antes de buscar. Si se recortan variantes por longitud, se indica.

Las sugerencias son propuestas editoriales de vocabulario, métodos, controles o temas adyacentes. Explican su motivo y enlazan su procedencia; no confirman relaciones biológicas ni se autoañaden. Para temas desconocidos se propone revisar modelos y reproducibilidad.

`data/research_concepts.json` contiene el catálogo público y sus fuentes. No es una ontología completa ni un sistema que descubra conexiones nuevas automáticamente. Una frase de búsqueda no equivale a un término MeSH validado: se distingue vocabulario oficial de ejemplos editoriales.

## Criterio educativo

Distinguir representación aprendida, rendimiento de una tarea, calibración, generalización, evaluación prospectiva y beneficio clínico. Una buena métrica interna no demuestra que un modelo funcione en otro hospital o que mejore salud o longevidad. Los ejemplos plantean preguntas que requieren datos, controles y evaluación apropiados.

## Persistencia

El servidor guarda el perfil en `.cache/thesis-profile.json` mediante sustitución atómica y permisos privados. Un fallo conserva el perfil anterior; un archivo corrupto se desactiva con aviso sin sobrescribirlo al leer. Cambiar o eliminar el perfil también vacía las búsquedas del radar y revoca respuestas pendientes. No retira consultas ya enviadas a terceros; la caché bibliográfica clásica está separada.

No incluir perfiles, consultas, resultados, informes o capturas en el código público. No guardar información personal o confidencial como términos de búsqueda. Las rutas internas conservan compatibilidad con la API de perfiles existente; no codifican un proyecto individual.
