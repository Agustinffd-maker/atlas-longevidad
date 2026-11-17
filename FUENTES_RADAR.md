# Fuentes del radar científico

Revisión técnica: 10 de noviembre de 2026. Las consultas automáticas usan interfaces oficiales, biblioteca estándar Python y términos públicos elegidos por el usuario. No se conectan cuentas ni servicios de pago. Este documento describe recuperación de registros; no acredita la calidad de los estudios recuperados.

## Canales automáticos

| Canal | Función y procedencia | Fecha y límite de interpretación |
| --- | --- | --- |
| [PubMed / NCBI](https://www.ncbi.nlm.nih.gov/books/NBK25497/) | ESearch/EFetch: literatura biomédica, PMID, tipos, MeSH y resumen si existe | Publicación informada por el índice; no equivale a lectura crítica. Los tipos de retractación se señalan cuando están presentes. |
| [Europe PMC](https://europepmc.org/RestfulWebService) | REST, canal MED: vía alternativa para registros bibliográficos | Primera publicación informada. Se solapa con PubMed: dos índices no son dos confirmaciones del mismo estudio. |
| [Europe PMC · preprints](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=SRC%3APPR&format=json&pageSize=1) | REST, canal PPR: manuscritos tempranos de repositorios indexados | Primera publicación del preprint; no se presume revisión por pares ni se aplica un cuartil de revista. Revisar versiones y posible publicación posterior. |
| [Crossref](https://www.crossref.org/documentation/retrieve-metadata/rest-api/) | Metadatos DOI depositados por editoriales y otras organizaciones; este canal filtra `journal-article` | Fecha publicada con precisión original. DOI y tipo no certifican revisión por pares, rigor o pertinencia. |
| [ClinicalTrials.gov](https://clinicaltrials.gov/data-api/api) | API v2: estudios registrados, fase, estado, tamaño previsto/registrado y disponibilidad declarada de resultados | `LastUpdatePostDate`: cambió el registro, no necesariamente hay un hallazgo nuevo. Registro, reclutamiento y resultados depositados no demuestran eficacia. |

La interfaz del radar recupera hasta 12 registros por fuente, sin paginación en esta versión; los adaptadores admiten como máximo 20 y el buscador bibliográfico anterior mantiene su límite de 20. La ausencia de resultados no demuestra ausencia de evidencia. No se traduce, sintetiza ni evalúa críticamente el contenido automáticamente. Los resúmenes y registros mantienen sus condiciones de origen y solo se guardan en caché local.

Los operadores y la expansión de términos no son idénticos entre servicios. **Crossref es búsqueda textual bibliográfica, no un motor booleano equivalente a PubMed.** Se ordena por relevancia dentro del intervalo solicitado: ordenar únicamente por fecha en una prueba amplia recuperó incluso publicaciones de envejecimiento de objetos astronómicos. Se informa esta diferencia y se exige revisar pertinencia. La app no convierte una coincidencia textual en una relación biológica con longevidad.

Los ISSN se cotejan con el registro histórico de cuartiles existente, sin inferencia por nombre. Fuera de esa instantánea se mantiene «cuartil no verificado». Los preprints y registros de estudios no reciben cuartil. Véase `EVIDENCIA_REVISION.md` para año, categoría, fuente y límites.

El tipo informado prima sobre el canal: si PubMed o Europe PMC MED incluyen `Preprint` en sus metadatos, ese registro se clasifica como preprint y no hereda un cuartil de revista. Si además hay un tipo de retractación, se conserva la advertencia más fuerte. En ClinicalTrials.gov, ausencia del campo `hasResults` se muestra como información no disponible (`null`), sin convertirla en «sin resultados»; cuando existe debe ser un booleano válido.

## Patentes: búsquedas preparadas, consulta manual

Se generan términos y enlaces a formularios oficiales, con consulta copiable y la indicación de que **no se recuperaron resultados automáticamente**. Se evita inventar una API o un enlace que supuestamente haya ejecutado la búsqueda.

- [Espacenet](https://www.epo.org/en/searching-for-patents/technical/espacenet) ofrece búsqueda mundial. Su documentación indica que no admite búsquedas automáticas por robots; [OPS](https://www.epo.org/en/searching-for-patents/data/web-services/ops) es la interfaz automatizada y requiere registro y OAuth. No se configuraron credenciales.
- [PATENTSCOPE / WIPO](https://www.wipo.int/en/web/patentscope) permite explorar solicitudes PCT y otras colecciones. Se prepara `EN_ALL:(consulta)` para la búsqueda avanzada, respetando los [campos con idioma](https://www.wipo.int/en/web/patentscope/w/news/2022/news_0002).
- [USPTO Patent Public Search](https://www.uspto.gov/patents/search/patent-public-search) es una entrada oficial para búsqueda estadounidense. La [API del Open Data Portal](https://data.uspto.gov/apis/bulk-data/search) requiere una clave y registro; no está integrada sin autorización o credenciales.

La revisión de una patente requiere documento original, prioridad, familia, jurisdicción, reivindicaciones y estado legal actual. Una solicitud no equivale a concesión ni demuestra eficacia o seguridad. La búsqueda preparada no constituye análisis de patentabilidad ni libertad de operación.

## Ecosistemas sociales

Se prepara un enlace de búsqueda pública en [Bluesky](https://bsky.app/search), con sus [interfaces documentadas](https://docs.bsky.app/docs/api/app-bsky-feed-search-posts). Es exploración manual: puede requerir sesión. No hay conexión de cuentas, scraping, importación de perfiles, publicación ni seguimiento de personas.

Una conversación sirve para descubrir términos, autores o enlaces. Debe rastrearse a DOI, preprint, registro o documento primario antes de considerar una afirmación. Popularidad, número de seguidores y anuncio de una empresa no son medidas de calidad científica. No se mezclan señales sociales con resultados de ensayos o artículos.

## Comprobaciones

`tests/test_radar_sources.py` usa fixtures claramente sintéticas y separadas del producto. Prueba validación antes de red, metadatos y fechas, estado de preprints/estudios, cuartiles por ISSN, alertas de retractación de PubMed, respuesta vacía/malformada y enlaces manuales sin fingir resultados.

La comprobación real se ejecutó con la consulta pública `cellular senescence`, intervalo 2026-01-01 a 2026-11-10 y límite de dos registros por canal. **Los cinco canales respondieron y entregaron dos registros normalizados cada uno**. Identificadores de ejemplo: PubMed `42914653`; Europe PMC `42994808`; preprint `PPR1358913`; Crossref `10.65649/9t6t6458`; estudio `NCT07796373`. Los recuentos no son comparables entre índices y no se evaluaron críticamente esos resultados. Una respuesta correcta no garantiza disponibilidad futura ni cobertura exhaustiva. El contrato y la semántica también se cotejaron con el [OpenAPI oficial de ClinicalTrials.gov](https://clinicaltrials.gov/api/oas/v2) y la [documentación oficial de Crossref](https://github.com/CrossRef/rest-api-doc).
