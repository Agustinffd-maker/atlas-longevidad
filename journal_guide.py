"""Alfabetización editorial: las métricas de revista no puntúan un artículo."""

JOURNAL_GUIDE = {
    'title': 'Entender la revista antes de interpretar el artículo',
    'explanation': 'Una revista publica artículos bajo una política editorial; PubMed y Europe PMC son índices, Crossref registra metadatos de DOI. Estar indexado o tener DOI no certifica el resultado de un artículo.',
    'quartiles': 'Q1 es el tramo superior de la clasificación por citas de una categoría; Q2 es el siguiente tramo. Como orientación corresponden al primer y segundo cuarto del rango, con reglas para empates. En JCR se basan en Journal Impact Factor y dependen del año y categoría; no son notas de rigor de cada artículo ni se comparan sin contexto entre disciplinas. Aquí solo se conservan datos históricos comprobados de 2023, edición 2024.',
    'assessment': [
        'Pertinencia: ¿la pregunta y el modelo del artículo responden a la investigación o a longevidad? Una palabra coincidente solo propone una lectura.',
        'Diseño y muestra: separar revisión, estudio observacional, experimento celular, animal y ensayo humano; comprobar controles, tamaño y representatividad.',
        'Métodos y resultados: leer protocolo, unidades, normalización, incertidumbre, datos y limitaciones; distinguir asociación, mecanismo propuesto y causalidad.',
        'Transparencia: revisar conflictos de interés, políticas editoriales, acceso a datos/código, correcciones y retractaciones en la fuente.',
        'Convergencia: contrastar replicaciones y resultados contradictorios. Una patente, un registro de ensayo o un preprint no demuestra eficacia clínica.',
    ],
    'sources': [
        {'label': 'Clarivate: fundamentos de JCR y cuartiles', 'url': 'https://clarivate.libguides.com/jcr/basics'},
        {'label': 'NLM: evaluación de revistas para MEDLINE', 'url': 'https://www.nlm.nih.gov/medline/medline_how_to_include.html'},
        {'label': 'NCBI: inclusión no significa respaldo de las conclusiones', 'url': 'https://www.ncbi.nlm.nih.gov/pmc/about/disclaimer/'},
    ],
}
