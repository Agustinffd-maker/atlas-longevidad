'use strict';

const $ = (selector, root = document) => root.querySelector(selector);
const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const today = () => { const date = new Date(); return [date.getFullYear(), String(date.getMonth()+1).padStart(2,'0'), String(date.getDate()).padStart(2,'0')].join('-'); };
const daysAgo = days => { const date = new Date(); date.setDate(date.getDate() - days); return [date.getFullYear(), String(date.getMonth()+1).padStart(2,'0'), String(date.getDate()).padStart(2,'0')].join('-'); };
const state = {
  catalog: null, search: '', category: 'Todas', selected: new Set(), evidence: null,
  evidenceParams: {q: 'biomedical AND artificial intelligence', provider: 'pubmed', start: '2020-01-01', end: today(), kind: 'all', model: 'all'},
  busy: false, requestId: 0, localError: '', previousFocus: null,
  radarMeta: null, researchPlan: null, profile: null, profileDraft: null,
  workspaceLoading: false, workspaceError: '', workspaceGeneration: 0, profileBusy: false, profileError: '', profileNotice: '',
  radarParams: {provider:'pubmed',q:'(longevity OR aging OR ageing OR healthspan)',start:daysAgo(90),end:today()},
  radar: null, radarBusy: false, radarError: '', radarContext: 'Longevidad', radarRequestId: 0, radarController: null,
  innovationQuery: '', innovationBusy: false, innovationNotice: '', innovationRequestId: 0
};
try { state.selected = new Set(JSON.parse(localStorage.getItem('atlas-selection') || '[]')); } catch (_) { /* El atlas funciona sin almacenamiento del navegador. */ }

const paths = {
  explore: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  compare: '<path d="M8 3v18M16 3v18M3 8h10M11 16h10M5 5 2 8l3 3m14 2 3 3-3 3"/>',
  connections: '<circle cx="5" cy="12" r="3"/><circle cx="19" cy="5" r="3"/><circle cx="19" cy="19" r="3"/><path d="m8 10 8-4M8 14l8 4"/>',
  thesis: '<path d="M4 3h13l3 3v15H4V3Zm11 0v5h5M8 12h8M8 16h6"/>',
  book: '<path d="M3 4c4-1 6-1 9 1 3-2 5-2 9-1v15c-4-1-6-1-9 1-3-2-5-2-9-1V4Zm9 1v15"/>',
  search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
  leaf: '<path d="M20 4C7 2 2 8 6 15c6 7 15 0 14-11ZM5 20 16 9"/>',
  cell: '<circle cx="12" cy="12" r="9"/><circle cx="11" cy="11" r="3"/><path d="M7 16h.01M16 8h.01M16 16h.01"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',
  arrow: '<path d="M5 12h14m-5-5 5 5-5 5"/>',
  back: '<path d="M19 12H5m5-5-5 5 5 5"/>',
  source: '<path d="M14 3h7v7M21 3l-9 9M10 5H4v15h15v-6"/>'
};
function icon(name, extra = '') { return `<svg class="${extra}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.cell}</svg>`; }
function announce(message) { $('#announcer').textContent = message; }
function dateLabel(value) {
  if (!value) return 'Sin fecha disponible';
  if (/^\d{4}-\d{2}-\d{2}T/.test(value)) return new Date(value).toLocaleString('es-CL', {dateStyle:'medium', timeStyle:'short'});
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return new Date(value + 'T12:00:00').toLocaleDateString('es-CL', {dateStyle:'medium'});
  return value;
}
function safeExternal(url) {
  try {
    const parsed = new URL(url);
    return parsed.protocol === 'https:' && !parsed.username && !parsed.password && ['pubmed.ncbi.nlm.nih.gov','pmc.ncbi.nlm.nih.gov','doi.org','www.ncbi.nlm.nih.gov','europepmc.org','www.ebi.ac.uk','www.cnfis.ro','www.repository.cam.ac.uk','www.jci.org','orbi.uliege.be','clinicaltrials.gov','api.crossref.org','search.crossref.org','www.crossref.org','search.epo.org','worldwide.espacenet.com','www.epo.org','patentscope.wipo.int','www.wipo.int','ppubs.uspto.gov','www.uspto.gov','bsky.app','docs.bsky.app','www.biorxiv.org','www.medrxiv.org','meshb.nlm.nih.gov','www.nlm.nih.gov','clarivate.libguides.com'].includes(parsed.hostname) ? escapeHTML(parsed.href) : '#';
  } catch (_) { return '#'; }
}
function citations(ids) {
  return `<div class="citations">${ids.map(id => {
    const ref = state.catalog.references[id];
    return ref ? `<a class="citation" href="${safeExternal(ref.url)}" target="_blank" rel="noopener noreferrer" title="${escapeHTML(ref.title)}">PMID ${escapeHTML(id)} ${icon('source')}</a>` : '';
  }).join('')}</div>`;
}
function categoryStyle(category) { return ({Inflamación:'inflammation',Senescencia:'senescence',Metabolismo:'metabolism'})[category] || ''; }
function topicById(id) { return state.catalog.topics.find(topic => topic.id === id); }
function selectedTopics() { return state.catalog.topics.filter(topic => state.selected.has(topic.id)); }
function checkbox(topic) {
  return `<label class="compare-check"><input type="checkbox" data-compare="${escapeHTML(topic.id)}" ${state.selected.has(topic.id) ? 'checked' : ''} aria-label="Comparar ${escapeHTML(topic.name)}">Comparar</label>`;
}
function renderNav(active) {
  const items = [['novedades','clock','Novedades'],['explorar','explore','Biblioteca'],['tesis','thesis','Mi investigación'],['innovacion','leaf','Innovación'],['comparar','compare','Comparar'],['conexiones','connections','Conexiones'],['fuentes','book','Evidencia y fuentes']];
  $('#navigation').innerHTML = items.map(([route, image, title]) => `<a class="nav-link ${active === route ? 'active' : ''}" href="#/${route}" ${active === route ? 'aria-current="page"' : ''}>${icon(image)}<span>${title}</span>${route === 'comparar' && state.selected.size ? `<span class="nav-count">${state.selected.size}</span>` : ''}</a>`).join('');
}
function renderTray() {
  const tray = $('#compare-tray');
  tray.hidden = !state.selected.size || location.hash.startsWith('#/comparar');
  tray.innerHTML = `<div><span class="tray-label">${state.selected.size} concepto${state.selected.size === 1 ? '' : 's'} seleccionado${state.selected.size === 1 ? '' : 's'}</span><div class="toast-detail">Compara lo que miden y lo que no.</div></div><button class="quiet" data-action="clear-selection">Limpiar</button><a href="#/comparar" class="button">${state.selected.size < 2 ? 'Elegir otro concepto' : 'Ver comparación'} ${icon('arrow')}</a>`;
}
function saveSelection() {
  try { localStorage.setItem('atlas-selection', JSON.stringify([...state.selected])); } catch (_) { /* Selección continúa en memoria. */ }
}
function toggleSelection(id, selected) {
  if (!topicById(id)) return;
  if (selected) state.selected.add(id); else state.selected.delete(id);
  saveSelection();
  document.querySelectorAll('[data-compare]').forEach(input => { input.checked = state.selected.has(input.dataset.compare); });
  renderNav(activeRoute()); renderTray();
  announce(`${state.selected.size} conceptos seleccionados para comparar.`);
}
function activeRoute() {
  const part = (location.hash.split('/')[1] || 'explorar');
  return ['ficha','guia'].includes(part) ? 'explorar' : part;
}
function scaleGuide() {
  return `<div class="scale-guide"><h2>De los datos a la utilidad</h2><div class="scale-row">${icon('book')}<div><strong>Datos</strong><span>Origen, modalidades y etiquetas</span></div></div><div class="scale-row">${icon('connections')}<div><strong>Modelo</strong><span>Predicciones, errores e incertidumbre</span></div></div><div class="scale-row">${icon('clock')}<div><strong>Evaluación</strong><span>Validación externa y desenlaces de salud</span></div></div></div>`;
}
function renderExplore() {
  const categories = ['Todas', ...new Set(state.catalog.topics.map(topic => topic.category))];
  return `<section class="hero"><div><h1>Entender el tiempo,<br>desde la biología.</h1><p>Explora biomedicina e IA, comprende qué evalúa cada modelo y conecta la evidencia con tus preguntas de investigación.</p></div>${scaleGuide()}</section>
  <div class="intro-note">${icon('info')}<span>Un modelo no es una conclusión. Su utilidad depende de los datos, la tarea y la evaluación.</span><a href="#/fuentes">Nuestro criterio ${icon('arrow')}</a></div>
  <section aria-label="Explorar biblioteca"><label class="search-box" for="catalog-search">${icon('search')}<span class="sr-only">Buscar conceptos de biomedicina e IA en la biblioteca local</span><input id="catalog-search" type="search" autocomplete="off" placeholder="Busca un modelo, un método o una pregunta…" value="${escapeHTML(state.search)}"><span class="search-shortcut" aria-hidden="true">/</span></label><p class="local-hint">Búsqueda en tu biblioteca · No se envía a internet</p>
  <div class="categories" role="group" aria-label="Filtrar por categoría">${categories.map(category => `<button class="category-chip ${state.category === category ? 'selected' : ''}" data-category="${escapeHTML(category)}" aria-pressed="${state.category === category}">${escapeHTML(category)}</button>`).join('')}</div>
  <div class="section-heading"><h2>Tu biblioteca de conceptos</h2><small id="result-count"></small></div><div id="catalog-results"></div></section>`;
}
function filteredTopics() {
  const normalize = value => value.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  const query = normalize(state.search.trim());
  return state.catalog.topics.filter(topic => (state.category === 'Todas' || state.category === topic.category) && normalize([topic.name, topic.short, topic.category, topic.summary, topic.context, ...topic.terms].join(' ')).includes(query));
}
function updateCards() {
  const result = $('#catalog-results');
  if (!result) return;
  const topics = filteredTopics();
  $('#result-count').textContent = `${topics.length} de ${state.catalog.topics.length} conceptos · Selecciona para comparar`;
  if (!topics.length) {
    result.innerHTML = `<div class="empty-state"><h2>Probemos otra pregunta</h2><p>No hay conceptos para esta búsqueda o categoría. La biblioteca inicial es acotada; puedes buscar artículos en Evidencia y fuentes.</p><button class="button secondary" data-action="clear-filters">Limpiar búsqueda y filtros</button></div>`;
  } else {
    result.innerHTML = `<div class="catalog-grid">${topics.map(topic => `<article class="topic-card"><div class="topic-top"><span class="category-label ${categoryStyle(topic.category)}">${escapeHTML(topic.category)}</span>${icon(topic.id.includes('modelo') || topic.id === 'ia-multimodal' ? 'connections' : 'cell','topic-symbol')}</div><h3><a href="#/ficha/${topic.id}">${escapeHTML(topic.name)}</a></h3><div class="abbreviation">${escapeHTML(topic.short)}</div><p>${escapeHTML(topic.summary)}</p><div class="card-spacer"></div><div class="card-bottom"><span class="source-count">${icon('book')}${topic.refs.length} fuente${topic.refs.length > 1 ? 's' : ''} de base</span>${checkbox(topic)}</div><div class="evidence-line">${escapeHTML(topic.kind)} · ${escapeHTML(topic.context)}</div></article>`).join('')}</div>`;
  }
}
function sectionContent(section) {
  const type = section.status?.includes('Hipótesis') ? 'hypothesis' : section.status?.includes('Pendiente') ? 'pending' : '';
  return `${section.status ? `<span class="label ${type}">${escapeHTML(section.status)}</span>` : ''}<p>${escapeHTML(section.text)}</p>${citations(section.refs)}`;
}
function renderDetail(id) {
  const topic = topicById(id);
  if (!topic) return renderNotFound();
  return `<a class="back-link" href="#/explorar">${icon('back')}Volver a la biblioteca</a><section class="detail-header"><span class="category-label ${categoryStyle(topic.category)}">${escapeHTML(topic.category)}</span><h1>${escapeHTML(topic.name)}</h1><div class="abbreviation">${escapeHTML(topic.short)} · ${escapeHTML(topic.kind)}</div><p class="lead">${escapeHTML(topic.summary)}</p>${citations(topic.refs)}${checkbox(topic)}</section><p class="editorial-info">Explicación editorial · Revisión: ${dateLabel(state.catalog.reviewed_on)} · No se reescribe con la actualización automática</p><div class="detail-layout"><div class="detail-copy"><section class="info-section"><h2>¿Por qué se estudia?</h2>${sectionContent(topic.why)}</section><details><summary>Cómo se mide</summary><div class="details-body"><span class="label">Orientación metodológica · Verificar protocolo</span><dl class="measurement-list"><div><dt>Muestra</dt><dd>${escapeHTML(topic.sample)}</dd></div><div><dt>Método</dt><dd>${escapeHTML(topic.method)}</dd></div><div><dt>Unidades</dt><dd>${escapeHTML(topic.units)}</dd></div></dl><p>Estas opciones no sustituyen un protocolo validado. Una etiqueta de datos, una predicción y un desenlace clínico responden preguntas distintas; revisa cómo se validó cada uno.</p>${citations(topic.refs)}</div></details><details><summary>Qué se ha observado y con qué evidencia</summary><div class="details-body"><span class="label">${escapeHTML(topic.evidence)}</span>${sectionContent(topic.findings)}<p class="editorial-info">Alcance: ${escapeHTML(topic.context)}. ${escapeHTML(topic.clinical)}.</p></div></details><details><summary>Limitaciones y factores que pueden cambiar la lectura</summary><div class="details-body">${sectionContent(topic.limits)}</div></details><details><summary>Aplicación a una investigación: una pregunta para explorar</summary><div class="details-body">${sectionContent(topic.thesis)}</div></details><details><summary>Fuentes de esta ficha (${topic.refs.length})</summary><div class="details-body">${topic.refs.map(id => referenceHTML(state.catalog.references[id])).join('')}</div></details><div class="comparison-actions"><button class="button secondary" data-search-topic="${topic.id}">Buscar evidencia reciente ${icon('source')}</button><a class="button secondary" href="#/conexiones">Explorar conexiones</a></div></div><aside class="aside-note"><h2>Detente en los conceptos</h2><p>Selecciona un término para entenderlo sin perder el hilo.</p><div class="term-links">${topic.terms.map(term => `<button class="term-button" data-term="${escapeHTML(term)}">${escapeHTML(term)}</button>`).join('')}</div><p>Recuerda: una predicción, una decisión clínica y un cambio en longevidad son desenlaces diferentes.</p></aside></div>`;
}
function renderCompare() {
  const topics = selectedTopics();
  const head = `<div class="page-heading"><div><h1>Mirarlos lado a lado.</h1><p>Compara preguntas y métodos. La similitud de una cifra no significa que dos mediciones sean equivalentes.</p></div><span class="heading-side">${topics.length} conceptos seleccionados</span></div>`;
  if (topics.length < 2) return head + `<div class="empty-state"><h2>Una buena comparación empieza con dos preguntas</h2><p>${topics.length ? 'Ya tienes un concepto. Selecciona al menos uno más en la biblioteca.' : 'Selecciona al menos dos conceptos con la casilla Comparar de cada ficha.'}</p><a class="button" href="#/explorar">Elegir conceptos ${icon('arrow')}</a></div>`;
  const rows = [['Qué refleja', t => t.summary],['Muestra',t => t.sample],['Método',t => t.method],['Unidades',t => t.units],['Modelo / contexto',t => t.context],['Utilidad y evidencia',t => t.evidence + '. ' + t.clinical],['Limitaciones',t => t.limits.text]];
  return head + `<div class="alert">Comparación conceptual, sin puntuación de «mejor modelo». No se agregan ni ordenan cifras de métodos, poblaciones o unidades incompatibles. Los métodos son orientación; consulta el protocolo original.</div><div class="compare-scroll" role="region" aria-label="Tabla comparativa de conceptos; desplaza horizontalmente para ver más columnas" tabindex="0"><table class="compare-table compare-${topics.length}"><caption class="sr-only">Comparación cualitativa de ${topics.map(t => t.name).join(', ')}</caption><thead><tr><th scope="col">Dimensión</th>${topics.map(topic => `<th scope="col"><a href="#/ficha/${topic.id}">${escapeHTML(topic.name)}</a><button class="quiet remove-compare" data-remove="${topic.id}">Quitar ${escapeHTML(topic.short)}</button></th>`).join('')}</tr></thead><tbody>${rows.map(([label, getter]) => `<tr><th scope="row">${label}</th>${topics.map(topic => `<td>${escapeHTML(getter(topic))}</td>`).join('')}</tr>`).join('')}<tr><th scope="row">Fuentes de base</th>${topics.map(topic => `<td>${citations(topic.refs)}</td>`).join('')}</tr></tbody></table></div><div class="comparison-actions"><a class="button secondary" href="#/explorar">Añadir otro concepto</a><button class="quiet" data-action="clear-selection">Limpiar selección</button></div>`;
}
function renderConnections() {
  return `<div class="page-heading"><div><h1>Conectar sin dar saltos.</h1><p>Un mapa de relaciones para entender qué conecta los procesos y dónde empieza una hipótesis.</p></div></div><div class="alert">Las líneas relacionan preguntas. No representan causalidad universal ni eficacia clínica.</div><div class="connection-list">${state.catalog.connections.map(connection => `<article class="connection"><div class="connection-nodes"><a class="node-link" href="#/ficha/${connection.from}">${escapeHTML(topicById(connection.from).name)}</a><span class="relation-mark" aria-hidden="true">—</span><span class="sr-only">se relaciona con</span><a class="node-link" href="#/ficha/${connection.to}">${escapeHTML(topicById(connection.to).name)}</a></div><span class="label ${connection.status.includes('Hipótesis') ? 'hypothesis' : ''}">${escapeHTML(connection.status)}</span><h2>${escapeHTML(connection.label)}</h2><p>${escapeHTML(connection.text)}</p>${citations(connection.refs)}</article>`).join('')}</div>`;
}
function renderThesisExample() {
  const topics = ['modelos-fundacionales','ia-multimodal','celula-virtual'].map(topicById).filter(Boolean);
  const validation = topicById('validacion-externa');
  return `<p class="editorial-info">Ejemplo público de biomedicina e IA, independiente del perfil local.</p><section class="thesis-intro"><h3>Separa predicción, validación y utilidad.</h3><p>Un resultado computacional, una mejora en una decisión clínica y un cambio en salud o longevidad son desenlaces distintos. Estas preguntas ayudan a revisar un proyecto; no describen resultados propios.</p>${validation ? citations(validation.refs) : ''}</section><div class="scale-comparison"><section><h3>Aprender una representación</h3><p>¿Qué datos y modalidades utiliza el modelo? ¿Qué tarea se evaluó y qué información queda fuera de sus entradas?</p>${topics[0] ? citations(topics[0].refs) : ''}</section><section><h3>Validar en otro contexto</h3><p>¿Se separaron personas, centros o sistemas entre entrenamiento y prueba? ¿Se evaluaron calibración, errores y diferencias entre grupos?</p>${validation ? citations(validation.refs) : ''}</section><section><h3>Medir utilidad</h3><p>¿Se midió desempeño computacional, utilidad clínica o un desenlace de salud? Un benchmark no convierte esos objetivos en equivalentes.</p>${validation ? citations(validation.refs) : ''}</section></div><h3>Preguntas para un ejemplo de investigación</h3>${topics.map((topic,index) => `<details class="thesis-question" ${index === 0 ? 'open' : ''}><summary>${escapeHTML(topic.name)}</summary><p>${escapeHTML(topic.thesis.text)}</p><div class="editorial-info"><span class="label hypothesis">Pregunta de investigación; requiere evaluación</span></div>${citations(topic.thesis.refs)}<a class="button secondary compact" href="#/ficha/${topic.id}">Revisar la ficha completa</a></details>`).join('')}<div class="alert">La plataforma no entrena modelos ni analiza datos de pacientes. Un buen resultado predictivo no prueba beneficio clínico ni aumento de longevidad.</div>`;
}
function options(values, current) { return values.map(([value,label]) => `<option value="${value}" ${current === value ? 'selected' : ''}>${label}</option>`).join(''); }
function renderEvidence() {
  const params = state.evidenceParams;
  return `<div class="page-heading"><div><h1>Volver siempre a la fuente.</h1><p>Consulta literatura científica pública y examina el contexto de cada estudio. Encontrar un artículo es el comienzo de la revisión.</p></div></div><form id="evidence-form" class="search-form"><div class="provider-pick" role="group" aria-label="Fuente de búsqueda">${[['pubmed','PubMed / NCBI'],['europepmc','Europe PMC']].map(([value,label]) => `<label><input type="radio" name="provider" value="${value}" ${params.provider === value ? 'checked' : ''}>${label}</label>`).join('')}</div><label class="field-label" for="evidence-query">Consulta pública que se enviará a la fuente seleccionada</label><div class="evidence-query"><input id="evidence-query" name="q" type="search" minlength="2" maxlength="250" required value="${escapeHTML(params.q)}" aria-describedby="privacy-note" placeholder="Por ejemplo: biomedical AND artificial intelligence"><button class="button" type="submit" id="search-evidence-button">${icon('search')}Buscar artículos</button></div><p class="local-hint" id="privacy-note">No incluyas datos privados ni blancos confidenciales. Usa términos científicos en inglés; AND / OR ayudan a precisar.</p><div class="filter-row"><div class="field"><label class="field-label" for="start">Publicado desde</label><input id="start" name="start" type="date" min="1900-01-01" max="${today()}" required value="${escapeHTML(params.start)}"></div><div class="field"><label class="field-label" for="end">Publicado hasta</label><input id="end" name="end" type="date" min="1900-01-01" max="${today()}" required value="${escapeHTML(params.end)}"></div><div class="field"><label class="field-label" for="kind">Tipo de publicación</label><select id="kind" name="kind">${options([['all','Todos los tipos'],['review','Revisiones'],['trial','Ensayos clínicos'],['original','Excluir revisión, editorial y carta']],params.kind)}</select></div><div class="field"><label class="field-label" for="model">Modelo / población</label><select id="model" name="model">${options([['all','Todos los modelos'],['humans','Humanos (indexación)'],['animals','Animales (indexación)'],['cells','Células (términos de búsqueda)'],['computational','Computacional (términos)']],params.model)}</select></div></div><p class="filter-note">Los filtros dependen de la indexación disponible. Excluir revisiones no certifica un estudio original. Europe PMC se limita a registros de PubMed (MED); las búsquedas y fechas pueden diferir por proveedor. Máximo 20 artículos por consulta. Actualizar respeta el intervalo; amplía «Publicado hasta» para incluir nuevos días.</p></form><section aria-label="Resultados de evidencia"><div id="evidence-results"></div></section>${renderMethodology()}${renderJournalGuide()}`;
}
function referenceHTML(ref) {
  if (!ref) return '';
    return `<article class="reference-item"><h3><a href="${safeExternal(ref.url)}" target="_blank" rel="noopener noreferrer">${escapeHTML(ref.title)}</a></h3><p>${escapeHTML(ref.journal)} · Publicación: ${escapeHTML(dateLabel(ref.published))} · PMID ${escapeHTML(ref.pmid)}${ref.doi ? ` · <a href="${safeExternal('https://doi.org/' + ref.doi)}" target="_blank" rel="noopener noreferrer">DOI ${escapeHTML(ref.doi)}</a>` : ''}</p><p>Consulta de metadatos: ${escapeHTML(dateLabel(ref.fetched_at))} · ${escapeHTML(ref.access)} · ${escapeHTML(quartileLabel(ref))}</p>${journalContext(ref)}${ref.review_access ? `<p>Revisión editorial: ${escapeHTML(ref.review_access)}. ${ref.review_note ? escapeHTML(ref.review_note) : ''}${ref.review_url ? ` <a href="${safeExternal(ref.review_url)}" target="_blank" rel="noopener noreferrer">Consultar versión revisada</a>` : ''}</p>` : ''}</article>`;
}

function quartileLabel(article) {
  return article.quartile_details ? `${article.quartile} · JIF ${article.quartile_details.metric_year} (histórico)` : 'cuartil no verificado';
}
function quartileDetails(article) {
  const value = article.quartile_details;
  if (!value) return '';
  return `<p class="quartile-note">Cuartil de la revista: <strong>${escapeHTML(value.quartile)}</strong> · ${escapeHTML(value.category)} · ISSN ${escapeHTML(value.issns.join(' / '))}. Datos JIF ${escapeHTML(value.metric_year)}, edición de junio de 2024. <a href="${safeExternal(value.source_url)}" target="_blank" rel="noopener noreferrer">CNFIS, reproducción pública de JCR, p. ${escapeHTML(value.pdf_page)}</a>. Verificado el ${escapeHTML(dateLabel(value.verified_on))}. Es una instantánea histórica, no el cuartil actual ni una evaluación del artículo.</p>`;
}
function renderMethodology() {
  return `<section class="methodology" id="metodo"><h2>Cómo leer esta evidencia</h2><details><summary>Qué se actualiza y qué se conserva</summary><p>PubMed utiliza E-utilities de NCBI para buscar y recuperar metadatos y resúmenes. Europe PMC usa su API REST oficial como consulta alternativa a registros MED. Una fuente no sustituye silenciosamente a la otra. La biblioteca inicial incluye referencias descargadas realmente; no son ejemplos.</p><p>Caché local de 24 horas. El servidor revisa las consultas guardadas cada 6 horas y renueva las caducadas. Actualizar evidencia solicita de nuevo la consulta visible, con un intervalo mínimo de un minuto para evitar repeticiones. Las fechas de descarga se conservan si falla.</p><p>No hay actualizaciones con el servidor detenido. Cerrar la pestaña no detiene el servidor. La síntesis educativa tiene una fecha de revisión independiente y no se reescribe automáticamente.</p></details><details><summary>Cuartiles, calidad y límites de la clasificación</summary><p>Q1 y Q2 clasifican revistas según año, categoría y fuente. Solo se aplica una métrica cuando el ISSN coincide con una revista cotejada en la reproducción institucional pública de JCR/JIF: datos de 2023, edición de junio de 2024. Cuando existe esa coincidencia, la referencia muestra fuente, categoría, año y página. No es una consulta directa a JCR ni una clasificación vigente de 2026. Para revistas fuera de esa instantánea se conserva «cuartil no verificado».</p><p>La biblioteca prioriza pertinencia científica y método. Estar en un índice o tener DOI no verifica un cuartil. La instantánea local no constituye una búsqueda exhaustiva Q1/Q2 ni verifica cuartiles del año de cada artículo. No se accede a fuentes de pago. El cuartil tampoco garantiza la calidad de un estudio.</p><p>El tipo de publicación procede de metadatos. Las etiquetas de modelo basadas en palabras son orientativas. «No determinado» significa que debes revisar el artículo. No se asigna automáticamente un nivel de certeza ni se hace una evaluación de riesgo de sesgo.</p></details><details><summary>Resumen, texto completo e interpretación</summary><p>${escapeHTML(state.catalog.editorial_note)} Revisión editorial: ${dateLabel(state.catalog.reviewed_on)}.</p><p>Los resultados nuevos muestran el título, los metadatos y, si existe, el resumen original sin traducir. No se genera una síntesis automática ni se confirma el resultado experimental por leer el título. Los detalles metodológicos de las fichas son orientación y deben contrastarse con el texto completo y el protocolo.</p><p>Una asociación no demuestra causalidad. Un hallazgo en animales o células no demuestra eficacia humana. «Hipótesis» y «Pendiente» identifican propuestas y vacíos, no resultados obtenidos.</p></details><details><summary>Biblioteca inicial: ${Object.keys(state.catalog.references).length} referencias verificadas</summary>${Object.values(state.catalog.references).map(referenceHTML).join('')}</details><details><summary>Fuentes oficiales, privacidad y condiciones de uso</summary><p>La interfaz y las fuentes tipográficas son locales. No se usan analítica, modelos de IA, CDN ni cuentas externas. El buscador clásico consulta NCBI o EMBL-EBI; el radar permite además Crossref y ClinicalTrials.gov. Solo se envían consultas explícitas y las renovaciones de búsquedas ya guardadas. La selección de fichas permanece en tu navegador y la caché en este proyecto.</p><p>Fuentes técnicas: <a href="https://www.ncbi.nlm.nih.gov/books/NBK25497/" target="_blank" rel="noopener noreferrer">documentación NCBI E-utilities</a> y <a href="https://europepmc.org/RestfulWebService" target="_blank" rel="noopener noreferrer">documentación Europe PMC REST</a>. Máximo global configurado: 2 solicitudes/segundo; sin claves.</p><p>Artículos, resúmenes y metadatos conservan las condiciones de sus autores y proveedores. Revisa el <a href="https://www.ncbi.nlm.nih.gov/About/disclaimer.html" target="_blank" rel="noopener noreferrer">aviso de NCBI y derechos de autor</a>. PubMed es un índice, no una certificación de las conclusiones.</p></details></section>`;
}
function renderEvidenceResults() {
  const target = $('#evidence-results');
  if (!target) return;
  const result = state.evidence;
  const feedback = state.localError ? `<div class="alert error" role="alert">${escapeHTML(state.localError)}</div>` : '';
  if (!result) {
    target.innerHTML = feedback + (state.busy ? '<p class="evidence-status" role="status">Consultando la fuente oficial… Esto puede tardar unos segundos.</p>' : `<div class="empty-state"><h2>La pregunta la eliges tú.</h2><p>Usa la consulta pública propuesta o escribe otra y pulsa Buscar artículos. Las explicaciones de la biblioteca ya funcionan sin conexión.</p></div>`);
    return;
  }
  const provider = result.provider === 'pubmed' ? 'PubMed / NCBI' : 'Europe PMC';
  const warning = result.error ? `<div class="alert error" role="alert">${escapeHTML(result.error)} ${result.fetched_at ? 'Se conservan los últimos resultados de esta consulta, que pueden estar desactualizados.' : 'No hay una copia guardada para esta consulta. La biblioteca inicial sigue disponible.'}<button class="quiet" data-action="retry-evidence">Reintentar</button></div>` : '';
  const status = `<div class="section-heading"><h2>${result.stale ? 'Últimos datos disponibles' : 'Resultados de la consulta'}</h2><small>${escapeHTML(provider)} · ${result.cached ? 'Copia local' : 'Consulta a la fuente'}</small></div><p class="evidence-status">Consulta: <strong>${escapeHTML(result.query)}</strong><br>${result.total == null ? 'Cantidad no disponible' : `${result.total.toLocaleString('es-CL')} coincidencias; se muestran ${result.articles.length}`} · ${result.fetched_at ? `Última descarga: ${escapeHTML(dateLabel(result.fetched_at))}` : 'Sin descarga previa'}<br>Último intento: ${escapeHTML(dateLabel(result.last_attempt_at))}${state.busy ? ' · Actualizando…' : ''}</p>`;
  const articles = result.articles.length ? `<ol class="article-list">${result.articles.map(article => `<li class="article-item"><span class="label">Datos automáticos · Sin evaluación crítica</span><h3><a href="${safeExternal(article.url)}" target="_blank" rel="noopener noreferrer">${escapeHTML(article.title)}</a></h3><p class="article-meta">${escapeHTML(article.journal)} · Publicación: ${escapeHTML(dateLabel(article.published))}<br>PMID ${escapeHTML(article.pmid)}${article.doi ? ` · <a href="${safeExternal('https://doi.org/' + article.doi)}" target="_blank" rel="noopener noreferrer">DOI ${escapeHTML(article.doi)}</a>` : ''}<br>${escapeHTML(article.model)} · ${escapeHTML(quartileLabel(article))}<br>Consultado: ${escapeHTML(dateLabel(article.fetched_at))} · ${escapeHTML(article.access)}</p>${quartileDetails(article)}<p class="article-type">Tipo en metadatos: ${escapeHTML(article.types.join(' · '))}</p>${article.abstract ? `<details><summary>Leer resumen original (sin interpretación automática)</summary><p class="abstract" lang="en">${escapeHTML(article.abstract)}</p></details>` : '<p class="article-meta">Sin resumen disponible. No se infieren resultados del título.</p>'}</li>`).join('')}</ol>` : result.error ? '' : '<div class="empty-state"><h2>No se encontraron artículos</h2><p>Amplía las fechas, quita filtros o reformula la consulta. Cero coincidencias no demuestra ausencia de evidencia.</p><button class="button secondary" data-action="reset-evidence-filters">Quitar filtros de estudios</button></div>';
  target.innerHTML = feedback + warning + status + articles;
}
function renderGuide() {
  return `<a class="back-link" href="#/explorar">${icon('back')}Volver a la biblioteca</a><div class="page-heading"><div><h1>Aprender, una pregunta a la vez.</h1><p>El atlas combina una biblioteca educativa y un buscador de literatura. Cada uno tiene un propósito y una fecha de revisión distintos.</p></div></div><div class="guide-steps"><section><h2>Explora</h2><p>Busca un concepto en español y elige una categoría. Abre la ficha para leer el resumen y despliega métodos, resultados y límites cuando quieras profundizar.</p></section><section><h2>Contrasta</h2><p>Marca Comparar en dos o más fichas. Compara qué miden y en qué contexto; el atlas no convierte esas diferencias en una puntuación universal.</p></section><section><h2>Vuelve a la fuente</h2><p>Busca literatura en Evidencia y fuentes. Selecciona un PMID o DOI para abrir el artículo; revisa el resumen y el texto completo antes de adoptar una conclusión.</p></section></div><div class="alert">El buscador de conceptos es local. Solo el formulario de literatura envía su consulta pública a la fuente. Con el servidor detenido no hay actualizaciones.</div><section class="methodology"><h2>Glosario a mano</h2><p class="editorial-info">También encontrarás estos términos seleccionables dentro de las fichas.</p><div class="glossary-index">${state.catalog.glossary.map(entry => `<button class="term-button" data-term="${escapeHTML(entry.term)}">${escapeHTML(entry.term)}</button>`).join('')}</div></section>`;
}
// El radar recupera registros; el perfil y sus consultas se preparan siempre en local.
const DEFAULT_THESIS_CONCEPTS = 'modelos fundacionales biomédicos | biomedical foundation models\nIA multimodal | multimodal artificial intelligence\ncélula virtual | virtual cell';
function textValue(value) { return typeof value === 'string' ? value : ''; }
function externalLink(url, label, className = '') {
  const href = safeExternal(url);
  return href === '#' ? `<span>${escapeHTML(label)} · enlace no disponible</span>` : `<a class="${className}" href="${href}" target="_blank" rel="noopener noreferrer">${escapeHTML(label)} ${icon('source')}</a>`;
}
function workspaceFeedback() {
  if (state.workspaceLoading && !state.radarMeta) return '<p class="evidence-status" role="status">Abriendo la configuración y las fuentes locales…</p>';
  return state.workspaceError ? `<div class="alert error" role="alert">${escapeHTML(state.workspaceError)} <button class="quiet" data-action="retry-workspace">Reintentar carga local</button></div>` : '';
}
function profileDraft(profile) {
  const concepts = Array.isArray(profile?.concepts) ? profile.concepts : [];
  return {
    title: textValue(profile?.title), enabled: profile?.enabled === true,
    conceptText: concepts.length ? concepts.map(term => {
      const synonyms = profile.synonyms?.[term];
      return term + (Array.isArray(synonyms) && synonyms.length ? ' | ' + synonyms.join('; ') : '');
    }).join('\n') : DEFAULT_THESIS_CONCEPTS
  };
}
function renderThesis() {
  const draft = state.profileDraft || profileDraft(state.profile);
  const enabled = state.profile?.enabled === true;
  const disabled = !state.profile || state.profileBusy;
  const feedback = state.profileError ? `<p class="alert error" role="alert">${escapeHTML(state.profileError)}</p>` : '';
  return `<div class="page-heading"><div><span class="eyebrow">Seguimiento de investigación</span><h1>Tu investigación, tus conceptos.</h1><p>Define qué quieres seguir. El mismo módulo sirve para modelos fundacionales biomédicos, IA multimodal, célula virtual u otra pregunta de investigación.</p></div><span class="label ${enabled ? '' : 'pending'}">${enabled ? 'Perfil habilitado' : 'Sin seguimiento de investigación activo'}</span></div>
    ${workspaceFeedback()}
    <section class="profile-panel" aria-labelledby="profile-heading"><div class="section-heading"><h2 id="profile-heading">Configurar mi línea de investigación</h2>${state.profile?.updated_at ? `<small>Guardado: ${escapeHTML(dateLabel(state.profile.updated_at))}</small>` : ''}</div>
      <p class="section-intro">Los términos de ejemplo son editables. Guardar prepara el plan en este computador. La primera consulta requiere pulsar Buscar; después el servidor puede renovar las búsquedas guardadas cada 6 horas mientras siga abierto, respetando las fechas elegidas.</p>
      <form id="profile-form"><fieldset class="plain-fieldset" ${disabled ? 'disabled' : ''}>
        <label class="field-label" for="profile-title">Etiqueta local de tu proyecto (opcional)</label><input id="profile-title" name="title" type="text" maxlength="100" value="${escapeHTML(draft.title)}" placeholder="Por ejemplo: mi línea de investigación" aria-describedby="profile-privacy">
        <label class="field-label" for="profile-concepts">¿Qué conceptos quieres seguir?</label><textarea id="profile-concepts" name="concepts" rows="5" maxlength="3600" required aria-describedby="concept-format profile-privacy">${escapeHTML(draft.conceptText)}</textarea>
        <p class="field-help" id="concept-format">Hasta 6 conceptos, uno por línea. Puedes añadir sinónimos públicos tras <strong>|</strong>, separados por <strong>;</strong>. Ejemplo: <code>IA multimodal | multimodal artificial intelligence</code>. Escribe términos, no una consulta booleana.</p>
        <label class="profile-toggle"><input type="checkbox" id="profile-enabled" ${draft.enabled ? 'checked' : ''}> Habilitar el seguimiento específico de este proyecto</label>
        <p class="local-hint" id="profile-privacy">El perfil queda en la caché local, excluida de Git. La etiqueta del proyecto no se envía a fuentes. Usa solo conceptos públicos: al buscar, la consulta visible sí se enviará al proveedor elegido. Guardar cambios o eliminar el perfil borra las consultas guardadas del radar; no revoca consultas ya enviadas.</p>
        ${feedback}<div class="profile-actions"><button type="submit" class="button" id="save-profile">${state.profileBusy ? 'Guardando…' : 'Guardar configuración local'}</button><button type="button" class="quiet" data-action="delete-profile">Eliminar perfil y consultas guardadas del radar</button></div>
      </fieldset></form><p id="profile-notice" class="evidence-status" role="status">${escapeHTML(state.profileNotice)}</p>
    </section>
    <section class="workspace-section" aria-labelledby="thesis-plan-heading"><h2 id="thesis-plan-heading">Tu plan de actualización</h2>${enabled ? `<p class="section-intro">${state.profile.concepts.map(term => `<span class="concept-pill">${escapeHTML(term)}</span>`).join('')} Revisa cada consulta antes de usarla.</p>${renderQueryPlan()}` : '<div class="empty-state compact-empty"><h3>Primero elige tus conceptos</h3><p>Guarda y habilita el perfil para preparar consultas de investigación. El radar general de longevidad funciona de forma independiente.</p><a href="#/novedades" class="button secondary">Abrir novedades de longevidad</a></div>'}</section>
    ${renderSuggestions()}
    <details class="workspace-disclosure"><summary>Ver el ejemplo público: biomedicina e IA</summary><div class="details-body">${renderThesisExample()}</div></details>`;
}
function renderQueryPlan() {
  const queries = Array.isArray(state.researchPlan?.queries) ? state.researchPlan.queries : [];
  if (!queries.length) return '<p class="evidence-status">No hay consultas preparadas. Revisa los conceptos y vuelve a cargar la configuración local.</p>';
  const bridges = Array.isArray(state.researchPlan?.bridges) ? state.researchPlan.bridges : [];
  return renderQueryCards(queries,'use-query') + (bridges.length ? `<details class="workspace-disclosure"><summary>Cruzar mis conceptos con longevidad</summary><div class="details-body"><p>El seguimiento específico de tu investigación no exige que todos sus trabajos mencionen envejecimiento. Estas consultas adicionales buscan el puente cuando quieras explorarlo.</p>${renderQueryCards(bridges,'use-bridge')}</div></details>` : '');
}
function renderQueryCards(queries, action) {
  return `<div class="query-grid">${queries.map((entry,index) => `<article class="query-card"><h3>${escapeHTML(entry.label || 'Consulta de investigación')}</h3><p class="query-preview"><code>${escapeHTML(entry.query)}</code></p><p class="field-help">${escapeHTML(entry.relation_note || 'Expansión de búsqueda; no demuestra una relación causal.')}</p><button type="button" class="button secondary compact" data-${action}="${index}">Preparar esta búsqueda ${icon('arrow')}</button></article>`).join('')}</div>`;
}
function renderSuggestions() {
  const suggestions = Array.isArray(state.researchPlan?.suggestions) ? state.researchPlan.suggestions : [];
  if (!state.profile?.enabled || !suggestions.length) return '';
  const kinds = {synonym:'Otra forma de nombrarlo',broader:'Ampliar el campo',method:'Método para explorar',control:'Control o contraste',adjacent:'Concepto vecino'};
  return `<section class="workspace-section" aria-labelledby="suggestions-heading"><h2 id="suggestions-heading">Quizás también conviene buscar…</h2><p class="section-intro">Términos para descubrir puntos ciegos. Son sugerencias de búsqueda, no relaciones biológicas comprobadas ni afirmaciones sobre tu investigación.</p><div class="suggestion-grid">${suggestions.map((entry,index) => `<article class="suggestion-card"><span class="label">${escapeHTML(kinds[entry.relation_type] || 'Ampliar la búsqueda')}</span><h3>${escapeHTML(entry.label || entry.term)}</h3><p>${escapeHTML(entry.reason)}</p>${entry.source_url ? `<p class="field-help">${externalLink(entry.source_url,entry.source_label || 'Vocabulario de referencia')}</p>` : ''}<button type="button" class="quiet" data-add-concept="${index}">Añadir al borrador de conceptos</button></article>`).join('')}</div><p class="field-help">Añadir modifica el borrador; recuerda guardarlo. No se envía una consulta ni se activa un tema automáticamente.</p></section>`;
}
function radarSources() { return (state.radarMeta?.sources || []).filter(source => source.automatic !== false && ['pubmed','europepmc','crossref','preprints','trials'].includes(source.id)); }
function renderRadarForm(innovation = false) {
  const params = state.radarParams;
  const sources = radarSources();
  const source = innovation ? sources.find(item => item.id === 'trials') : sources.find(item => item.id === params.provider);
  const disabled = !sources.length || state.radarBusy;
  const isTrial = innovation || params.provider === 'trials';
  return `<form class="search-form radar-form" id="radar-form"><fieldset class="plain-fieldset" ${disabled ? 'disabled' : ''}>
    <div class="radar-form-top"><div class="field">${innovation ? '<p class="field-label">Fuente del registro clínico</p><input type="hidden" name="provider" value="trials"><p class="source-name">ClinicalTrials.gov</p>' : `<label class="field-label" for="radar-provider">Fuente para esta consulta</label><select name="provider" id="radar-provider">${sources.map(entry => `<option value="${escapeHTML(entry.id)}" ${params.provider === entry.id ? 'selected' : ''}>${escapeHTML(entry.label)}</option>`).join('')}</select>`}</div><p class="field-help">${escapeHTML(source?.description || 'Selecciona una fuente para conocer su función y sus límites.')}</p></div>
    <label class="field-label" for="radar-query">Consulta pública que se enviará</label><textarea id="radar-query" name="q" rows="3" minlength="2" maxlength="1000" required aria-describedby="radar-privacy">${escapeHTML(params.q)}</textarea>
    <p class="local-hint" id="radar-privacy">${innovation ? 'Buscar consulta el registro oficial; no busca resultados de eficacia ni importa patentes.' : 'No se envía nada hasta pulsar Buscar. No incluyas datos privados, resultados propios ni blancos confidenciales.'}</p>
    <div class="radar-date-row"><div class="field"><label class="field-label" for="radar-start">${isTrial ? 'Actualizado desde' : 'Publicado desde'}</label><input id="radar-start" name="start" type="date" min="1900-01-01" max="${today()}" value="${escapeHTML(params.start)}" required></div><div class="field"><label class="field-label" for="radar-end">${isTrial ? 'Actualizado hasta' : 'Publicado hasta'}</label><input id="radar-end" name="end" type="date" min="1900-01-01" max="${today()}" value="${escapeHTML(params.end)}" required></div><button type="submit" class="button" id="search-radar-button">${state.radarBusy ? 'Consultando…' : innovation ? 'Buscar registros' : 'Buscar novedades'} ${icon('search')}</button></div>
    <p class="field-help">Ventana inicial de 90 días, editable. La fecha del artículo o de actualización del registro es distinta de la fecha de consulta. Crossref busca por relevancia dentro del período; los operadores no funcionan igual en todas las fuentes.</p><details class="radar-cache-note"><summary>Actualización y uso sin conexión</summary><p>Las consultas que ya enviaste se guardan 6 horas. Mientras el servidor esté abierto, revisa la caché cada 6 horas y renueva lo caducado, respetando las fechas elegidas. Amplía «Hasta» o usa «Últimos 90 días» para incluir días nuevos. Cerrar la pestaña no detiene el servidor; con el servidor detenido no se actualiza nada. Un fallo conserva la última copia y su fecha, con aviso.</p></details>
  </fieldset></form>`;
}
function renderRadar() {
  return `<div class="page-heading"><div><span class="eyebrow">Radar científico</span><h1>Lo nuevo, con contexto.</h1><p>Publicaciones recientes, preprints y registros para seguir longevidad. La novedad abre una pregunta; los métodos y los datos determinan cuánto puedes concluir.</p></div><span class="label">${escapeHTML(state.radarContext)}</span></div>
    ${workspaceFeedback()}<div class="radar-shortcuts"><button class="button secondary compact" data-action="longevity-query">Preparar longevidad</button><button class="quiet" data-action="radar-recent-dates">Últimos 90 días</button><a class="button secondary compact" href="#/tesis">${state.profile?.enabled ? 'Ver consultas de mi investigación' : 'Configurar mi investigación'}</a><a href="#/innovacion" class="button secondary compact">Explorar innovación ${icon('arrow')}</a></div>
    ${renderRadarForm()}<section aria-label="Resultados del radar"><div id="radar-results"></div></section>
    ${renderLongevityReading()}${renderSourceGuide()}${renderJournalGuide()}`;
}
function renderLongevityReading() {
  return `<details class="workspace-disclosure"><summary>¿Cómo conectar una novedad con longevidad?</summary><div class="details-body"><p>La coincidencia con «aging», «longevity» o tus conceptos es una estrategia de recuperación. Para interpretar un registro, distingue estas preguntas:</p><div class="reading-questions"><section><h3>¿En qué escala?</h3><p>Estado celular, tejido, salud funcional y supervivencia del organismo son desenlaces diferentes.</p><a href="#/conexiones">Revisar conexiones con fuentes</a></section><section><h3>¿Qué se midió?</h3><p>Identifica modelo, muestra, comparación, método y tiempo de seguimiento. Un mecanismo propuesto no demuestra una intervención efectiva.</p><a href="#/explorar">Volver a los conceptos</a></section><section><h3>¿Qué falta contrastar?</h3><p>Busca limitaciones, resultados contrarios, replicación y correcciones en la publicación original. Un título o un cuartil no resuelven esas preguntas.</p><a href="#/fuentes">Leer el criterio científico</a></section></div></div></details>`;
}
function renderSourceGuide() {
  const sources = state.radarMeta?.sources || [];
  if (!sources.length) return '';
  return `<details class="workspace-disclosure"><summary>Qué aporta cada fuente</summary><div class="details-body"><p>PubMed y Europe PMC comparten registros. Encontrar el mismo estudio en ambos no es una replicación independiente. Crossref es un registro de metadatos; un preprint, un ensayo registrado y una patente responden preguntas diferentes.</p><div class="source-guide-grid">${sources.map(source => `<section><h3>${escapeHTML(source.label)}</h3><span class="label ${source.automatic === false ? 'pending' : ''}">${source.automatic === false ? 'Búsqueda externa guiada' : 'Consulta oficial integrada'}</span><p>${escapeHTML(source.description)}</p>${source.docs_url ? externalLink(source.docs_url,'Documentación de la fuente') : ''}</section>`).join('')}</div></div></details>`;
}
function renderJournalGuide() {
  const guide = state.radarMeta?.journal_guide;
  const assessment = Array.isArray(guide?.assessment) ? guide.assessment : [];
  return `<details class="workspace-disclosure journal-guide"><summary>Entender la revista y sus cuartiles</summary><div class="details-body"><h3>${escapeHTML(guide?.title || 'Revista, plataforma y calidad del estudio')}</h3><p>${escapeHTML(textValue(guide?.explanation) || 'La revista publica el trabajo. PubMed, Europe PMC y Crossref ayudan a encontrarlo o describirlo; no son revistas ni tienen un cuartil editorial que se pueda atribuir a todos sus registros.')}</p><p>${escapeHTML(textValue(guide?.quartiles) || 'Q1 y Q2 describen la posición de una revista en una categoría, fuente y año. La instantánea verificada aquí es JIF 2023, edición de junio de 2024. No es el cuartil actual ni un nivel de certeza del artículo.')}</p><h4>Antes de confiar en una conclusión</h4><ul>${(assessment.length ? assessment : ['Pertinencia para la pregunta y el modelo.','Diseño, muestra, controles, métodos y limitaciones.','Datos y métodos disponibles, replicaciones, correcciones y retractaciones.']).map(item => `<li>${escapeHTML(typeof item === 'string' ? item : item.text || item.description || item.label || '')}</li>`).join('')}</ul><p>Un cuartil ayuda a contextualizar la revista; no certifica revisión por pares de cada registro, ausencia de sesgo o eficacia. Una revista fuera de la instantánea conserva «cuartil no verificado» y puede contener un estudio pertinente.</p>${Array.isArray(guide?.sources) ? `<div class="source-links">${guide.sources.map(source => externalLink(source.url,source.label)).join('')}</div>` : ''}</div></details>`;
}
function journalContext(article) {
  if (!article.journal || article.kind === 'preprint' || article.kind === 'trial') return '';
  return `<details class="journal-context"><summary>Conocer la revista: ${escapeHTML(article.journal)}</summary><div class="details-body"><p>Revista: <strong>${escapeHTML(article.journal)}</strong>${Array.isArray(article.issns) && article.issns.length ? ` · ISSN ${escapeHTML(article.issns.join(' / '))}` : ' · ISSN no informado en este registro'}.</p>${quartileDetails(article) || '<p>No hay un cruce de cuartil comprobado para esta revista en la instantánea local. No se infiere por nombre ni prestigio.</p>'}<p>Para decidir si este trabajo te sirve, revisa su diseño, muestra, controles, métodos, datos y limitaciones. El cuartil caracteriza una revista en un contexto histórico; no evalúa este estudio.</p><a href="#/fuentes">Cómo evaluar revista y artículo</a></div></details>`;
}
function renderExternalSearches(entries, label, note, group = 'patent') {
  const links = Array.isArray(entries) ? entries : [];
  if (!links.length) return `<p class="evidence-status">No hay búsquedas preparadas. Carga la configuración local o configura los conceptos de tu investigación.</p>`;
  return `<p class="section-intro">${escapeHTML(note)}</p><div class="external-search-grid">${links.map((entry,index) => `<article class="external-search-card"><span class="label pending">${escapeHTML(label)}</span><h3>${escapeHTML(entry.label)}</h3>${entry.scope ? `<p class="field-help">Ámbito: ${escapeHTML(entry.scope)}</p>` : ''}${entry.prefilled === false ? `<p class="field-help">La consulta no se rellena automáticamente en esta base. Cópiala y pégala en su buscador oficial; revisa la sintaxis y las fechas allí.</p><p class="query-preview"><code>${escapeHTML(entry.query)}</code></p><button type="button" class="quiet" data-copy-search="${index}" data-copy-group="${group}" aria-label="Copiar consulta para ${escapeHTML(entry.label)}">Copiar consulta</button>` : ''}<details><summary>Ver ${entry.prefilled === false ? 'alcance y límites' : 'consulta y alcance'}</summary><div class="details-body">${entry.prefilled === false ? '' : `<p class="query-preview"><code>${escapeHTML(entry.query)}</code></p>`}<p>${escapeHTML(entry.note || '')}</p></div></details>${externalLink(entry.url,entry.prefilled === false ? 'Abrir base oficial' : 'Abrir búsqueda externa','button secondary compact')}</article>`).join('')}</div>`;
}
function renderInnovation() {
  return `<div class="page-heading"><div><span class="eyebrow">De la idea a la investigación</span><h1>Innovación, sin confundir señales.</h1><p>Explora registros clínicos, búsquedas de patentes y conversaciones científicas. Ninguno sustituye la evaluación de resultados y métodos.</p></div></div>${workspaceFeedback()}
    <section class="workspace-section" aria-labelledby="trials-heading"><h2 id="trials-heading">Qué se está investigando en humanos</h2><p class="section-intro">ClinicalTrials.gov describe estudios registrados. Que un estudio exista, reclute participantes o se actualice no demuestra que una intervención funcione ni que prolongue la vida.</p>${renderRadarForm(true)}<div id="radar-results" role="region" aria-label="Registros recuperados"></div></section>
    <section class="workspace-section" aria-labelledby="patents-heading"><h2 id="patents-heading">Patentes: seguir la actividad inventiva</h2><form id="innovation-plan-form" class="innovation-query-form"><label class="field-label" for="innovation-query">Conceptos públicos para preparar búsquedas de patentes y conversaciones</label><textarea id="innovation-query" rows="2" minlength="2" maxlength="1000" required>${escapeHTML(state.innovationQuery || state.researchPlan?.patent_links?.[0]?.query || state.researchPlan?.longevity_query || state.radarParams.q)}</textarea><p class="field-help">Este paso construye enlaces en local. El sitio externo recibirá la consulta cuando abras el enlace. Puedes cambiarla sin editar el perfil de investigación.</p><button class="button secondary compact" type="submit" ${state.innovationBusy ? 'disabled' : ''}>${state.innovationBusy ? 'Preparando…' : 'Preparar enlaces de búsqueda'}</button><p class="evidence-status" role="status">${escapeHTML(state.innovationNotice)}</p></form>${renderExternalSearches(state.researchPlan?.patent_links,'Búsqueda externa · sin resultados importados','Estas consultas abren bases oficiales. Revisa familias, reivindicaciones, prioridad, estado legal y cobertura; una patente o solicitud no demuestra eficacia científica, seguridad ni disponibilidad clínica.')}</section>
    <details class="workspace-disclosure"><summary>Señales sociales para descubrir términos y autores</summary><div class="details-body">${renderExternalSearches(state.researchPlan?.social_links,'Señal social · sin evaluación de evidencia','Úsalas para encontrar vocabulario, laboratorios o debates que luego contrastarás en las fuentes originales. La popularidad no mide calidad. No se leen cuentas ni se importan publicaciones sociales automáticamente.','social')}</div></details>
    ${renderSuggestions()}${renderLongevityReading()}`;
}
function radarItemHTML(item) {
  const kinds = {paper:'Publicación · revisión crítica pendiente',preprint:'Preprint · sin revisión por pares confirmada',trial:'Registro de estudio · no demuestra eficacia'};
  const retraction = Array.isArray(item.flags) && item.flags.includes('retraction');
  const titleLink = externalLink(item.url,item.title);
  return `<li class="radar-item"><div class="radar-item-labels"><span class="label ${retraction || item.kind === 'trial' ? 'pending' : item.kind === 'preprint' ? 'hypothesis' : ''}">${escapeHTML(retraction ? 'Retractación señalada en metadatos' : kinds[item.kind] || 'Registro automático · sin evaluación crítica')}</span><span class="source-tag">${escapeHTML(item.source_label || item.source || '')}</span></div><h3>${titleLink}</h3>
    <p class="article-meta">${escapeHTML(item.journal || (item.kind === 'trial' ? 'Registro clínico' : 'Revista no informada'))}<br>${escapeHTML(item.kind === 'trial' ? 'Fecha de actualización del registro' : 'Fecha de publicación')}: ${escapeHTML(dateLabel(item.published))}${item.date_label ? ` · ${escapeHTML(item.date_label)}` : ''}<br>${item.pmid ? `PMID ${escapeHTML(item.pmid)} · ` : ''}${item.doi ? `${externalLink('https://doi.org/' + item.doi,'DOI ' + item.doi)} · ` : ''}${escapeHTML(item.id || '')}</p>
    ${item.evidence_status ? `<p class="${retraction ? 'alert error' : 'field-help'}">${escapeHTML(item.evidence_status)}</p>` : ''}${item.model ? `<p class="field-help">Modelo informado: ${escapeHTML(item.model)}</p>` : ''}${item.trial_phase || item.study_type ? `<p class="field-help">${escapeHTML([item.study_type,item.trial_phase].filter(Boolean).join(' · '))}</p>` : ''}
    ${item.kind === 'paper' ? `<p class="article-meta">${escapeHTML(quartileLabel(item))}</p>${journalContext(item)}` : ''}
    ${item.summary ? `<details><summary>${item.kind === 'trial' ? 'Descripción del registro original' : 'Leer texto original del proveedor'}</summary><div class="details-body"><p class="abstract" lang="en">${escapeHTML(item.summary)}</p><p class="field-help">Texto del proveedor, sin síntesis automática ni evaluación metodológica.</p></div></details>` : '<p class="field-help">Solo metadatos disponibles en esta respuesta. No se infieren resultados del título.</p>'}
    <details><summary>Cómo leer su relación con longevidad</summary><div class="details-body"><p>Este registro se recuperó por la consulta visible, no por una evaluación de eficacia. Identifica si mide una señal celular, función de un tejido, salud o supervivencia del organismo; revisa el modelo, los controles y el seguimiento antes de relacionarlo con tu investigación.</p></div></details></li>`;
}
function renderRadarResults() {
  const target = $('#radar-results');
  if (!target) return;
  target.setAttribute('aria-busy',String(state.radarBusy));
  const result = activeRoute() === 'innovacion' && state.radar?.provider !== 'trials' ? null : state.radar;
  const localError = state.radarError ? `<div class="alert error" role="alert">${escapeHTML(state.radarError)} <button class="quiet" data-action="retry-radar">Reintentar</button></div>` : '';
  if (!result) {
    target.innerHTML = localError + (state.radarBusy ? '<p class="evidence-status" role="status">Consultando la fuente elegida…</p>' : '<div class="empty-state compact-empty"><h2>Elige una pregunta y una fuente</h2><p>Los resultados aparecerán al buscar. Abrir esta vista no envía tus conceptos a internet.</p></div>');
    return;
  }
  const source = radarSources().find(item => item.id === result.provider);
  const warning = result.error ? `<div class="alert error" role="alert">${escapeHTML(result.error)} ${result.fetched_at ? 'Se conserva la última copia de esta consulta; puede estar desactualizada.' : 'No hay una descarga previa de esta consulta.'}<button class="quiet" data-action="retry-radar">Reintentar</button></div>` : '';
  target.innerHTML = localError + warning + `<div class="section-heading"><h2>${result.stale ? 'Última copia disponible' : 'Registros recuperados'}</h2><small>${escapeHTML(source?.label || result.provider)} · ${result.cached ? 'Copia local' : 'Consulta a la fuente'}</small></div><p class="evidence-status">Consulta: <strong>${escapeHTML(result.query)}</strong><br>${typeof result.total === 'number' ? `${result.total.toLocaleString('es-CL')} coincidencias; ` : ''}se muestran ${result.items.length} · Descarga: ${escapeHTML(dateLabel(result.fetched_at))}<br>Último intento: ${escapeHTML(dateLabel(result.last_attempt_at))}${state.radarBusy ? ' · Actualizando…' : ''}</p>${result.date_basis || result.query_semantics ? `<details class="search-semantics"><summary>Cómo buscó esta fuente</summary><div class="details-body"><p>${escapeHTML(result.date_basis || '')}</p><p>${escapeHTML(result.query_semantics || '')}</p></div></details>` : ''}
    ${result.items.length ? `<ol class="radar-list">${result.items.map(radarItemHTML).join('')}</ol>` : result.error ? '' : '<div class="empty-state compact-empty"><h3>No se encontraron registros</h3><p>Amplía el período, prueba sinónimos o cambia de fuente. Un resultado vacío no demuestra ausencia de investigación.</p><button class="button secondary compact" data-action="radar-reset-dates">Ampliar a un año</button></div>'}`;
}
async function localJSON(url, options = {}) {
  const response = await fetch(url,options);
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'No se pudo leer la configuración local.');
  return result;
}
async function loadResearchWorkspace() {
  const generation = state.workspaceGeneration;
  state.workspaceLoading = true;
  state.workspaceError = '';
  const results = await Promise.allSettled(['/api/radar/meta','/api/profile','/api/research-plan'].map(url => localJSON(url)));
  if (generation !== state.workspaceGeneration) return;
  const errors = [];
  results.forEach((result,index) => {
    if (result.status !== 'fulfilled') { errors.push(index); return; }
    if (index === 0) state.radarMeta = result.value;
    if (index === 1) { state.profile = result.value.profile || result.value; if (!state.profileDraft) state.profileDraft = profileDraft(state.profile); }
    if (index === 2) state.researchPlan = result.value;
  });
  if (errors.length) state.workspaceError = 'No se pudieron cargar todos los módulos locales. Comprueba que el servidor esté abierto y reinícialo si acabas de actualizar el código.';
  state.workspaceLoading = false;
  if (['novedades','tesis','innovacion','fuentes'].includes(activeRoute())) {
    const evidenceForm = $('#evidence-form');
    if (evidenceForm) state.evidenceParams = Object.fromEntries(new FormData(evidenceForm));
    render();
  }
}
function readProfileForm() {
  const form = $('#profile-form');
  if (!form || !form.reportValidity()) return null;
  const title = $('#profile-title').value.trim();
  const lines = $('#profile-concepts').value.split('\n').map(line => line.trim()).filter(Boolean);
  if (!lines.length || lines.length > 6) throw new Error('Elige entre 1 y 6 conceptos, uno por línea.');
  const concepts = [], synonyms = {};
  for (const line of lines) {
    const [rawTerm,...rest] = line.split('|');
    const term = rawTerm.trim();
    const aliases = rest.join('|').split(';').map(value => value.trim()).filter(Boolean);
    if (term.length < 2 || term.length > 80 || aliases.length > 5 || aliases.some(value => value.length < 2 || value.length > 80)) throw new Error('Cada término debe tener 2 a 80 caracteres y hasta 5 sinónimos.');
    if (concepts.some(value => value.toLocaleLowerCase() === term.toLocaleLowerCase())) throw new Error('Hay conceptos repetidos. Combina sus sinónimos en una sola línea.');
    concepts.push(term);
    if (aliases.length) synonyms[term] = aliases;
  }
  return {title,concepts,synonyms,enabled:$('#profile-enabled').checked};
}
async function saveResearchProfile(remove = false) {
  if (state.profileBusy) return;
  state.profileError = ''; state.profileNotice = '';
  let values;
  try { values = remove ? null : readProfileForm(); if (!remove && !values) return; }
  catch (error) { state.profileError = error.message; render(); $('#profile-concepts')?.focus(); return; }
  resetResearchPreviews();
  state.profileBusy = true; render();
  try {
    const result = await localJSON('/api/profile',{method:remove ? 'DELETE' : 'POST',headers:{'Content-Type':'application/json','X-Local-Request':'1'},...(remove ? {} : {body:JSON.stringify(values)})});
    state.profile = result.profile || result;
    state.radar = null;
    state.profileDraft = profileDraft(state.profile);
    state.profileNotice = remove ? 'Perfil y consultas guardadas del radar eliminados. Puedes volver a buscar longevidad cuando quieras.' : state.profile.enabled ? 'Perfil guardado y habilitado. El plan está preparado. Este guardado no inicia una consulta externa; las búsquedas del radar se envían aparte.' : 'Perfil guardado sin seguimiento activo. Puedes habilitarlo cuando quieras.';
    state.researchPlan = await localJSON('/api/research-plan');
    announce(state.profileNotice);
  } catch (error) { state.profileError = error.message; announce(state.profileError); }
  finally { state.profileBusy = false; render(); (remove ? $('#profile-concepts') : $('#save-profile'))?.focus({preventScroll:true}); }
}
function readRadarForm() {
  const form = $('#radar-form');
  if (!form || !form.reportValidity()) return null;
  const params = Object.fromEntries(new FormData(form));
  params.q = params.q.replace(/\s+/g,' ').trim();
  $('#radar-query').value = params.q;
  if (params.q.trim().length < 2 || params.q.length > 1000) throw new Error('La consulta debe tener entre 2 y 1000 caracteres. Acorta los sinónimos si es necesario.');
  if (params.start > params.end) throw new Error('La fecha inicial debe ser anterior o igual a la final.');
  return params;
}
async function runRadar(force = false) {
  if (state.radarBusy) return;
  let params;
  try { params = readRadarForm(); if (!params) return; }
  catch (error) { state.radarError = error.message; renderRadarResults(); announce(error.message); return; }
  state.radarParams = params; state.radarBusy = true; state.radarError = '';
  setBusyControls(); renderRadarResults();
  const requestId = ++state.radarRequestId, controller = new AbortController();
  state.radarController = controller;
  const timeout = setTimeout(() => controller.abort(),60000);
  announce('Consultando la fuente elegida del radar.');
  try {
    const result = await localJSON(force ? '/api/radar/refresh' : '/api/radar?' + new URLSearchParams(params),force ? {method:'POST',headers:{'Content-Type':'application/json','X-Local-Request':'1'},body:JSON.stringify(params),signal:controller.signal} : {signal:controller.signal});
    if (!Array.isArray(result.items)) throw new Error('El radar recibió una respuesta con formato inesperado.');
    if (requestId === state.radarRequestId) { state.radar = result; announce(result.error || `${result.items.length} registros recuperados; revisión crítica pendiente.`); }
  } catch (error) { if (requestId === state.radarRequestId) { state.radarError = error.name === 'AbortError' ? 'La consulta tardó demasiado. Puedes reintentar; la copia anterior se conserva.' : 'No se pudo completar la consulta. ' + error.message; announce(state.radarError); } }
  finally { clearTimeout(timeout); if (requestId === state.radarRequestId) { state.radarBusy = false; state.radarController = null; } setBusyControls(); renderRadarResults(); }
}
function useResearchQuery(index, bridge = false) {
  const entry = (bridge ? state.researchPlan?.bridges : state.researchPlan?.queries)?.[index];
  if (!entry || typeof entry.query !== 'string') return;
  state.radarParams.q = entry.query;
  state.radarContext = entry.label || 'Mi investigación';
  state.radarError = '';
  location.hash = '#/novedades'; render(true); $('#radar-query')?.focus();
  announce('Consulta preparada. Revísala y pulsa Buscar para enviarla a la fuente.');
}
async function prepareInnovationLinks() {
  const form = $('#innovation-plan-form');
  if (state.innovationBusy || !form?.reportValidity()) return;
  state.innovationQuery = $('#innovation-query').value.replace(/\s+/g,' ').trim();
  const requestId = ++state.innovationRequestId, generation = state.workspaceGeneration;
  state.innovationBusy = true; state.innovationNotice = ''; render();
  try {
    const result = await localJSON('/api/research-plan?' + new URLSearchParams({q:state.innovationQuery}));
    if (requestId !== state.innovationRequestId || generation !== state.workspaceGeneration) return;
    state.researchPlan = result;
    state.innovationNotice = 'Enlaces preparados en local. No se importaron patentes ni publicaciones sociales.';
  } catch (error) { if (requestId === state.innovationRequestId && generation === state.workspaceGeneration) state.innovationNotice = 'No se pudieron preparar los enlaces. ' + error.message; }
  finally { if (requestId === state.innovationRequestId && generation === state.workspaceGeneration) { state.innovationBusy = false; render(); announce(state.innovationNotice); } }
}
function resetResearchPreviews() {
  state.workspaceGeneration += 1;
  state.innovationRequestId += 1;
  state.radarRequestId += 1;
  state.radarController?.abort();
  state.radarController = null; state.radarBusy = false; state.radarError = ''; state.radar = null;
  state.radarParams = {provider:'pubmed',q:'(longevity OR aging OR ageing OR healthspan)',start:daysAgo(90),end:today()};
  state.radarContext = 'Longevidad';
  state.innovationQuery = ''; state.innovationBusy = false; state.innovationNotice = '';
  state.researchPlan = null; state.workspaceLoading = false; state.workspaceError = '';
}
async function copyExternalQuery(index, group) {
  const entries = group === 'social' ? state.researchPlan?.social_links : state.researchPlan?.patent_links;
  const entry = entries?.[index];
  if (!entry?.query) return;
  try { await navigator.clipboard.writeText(entry.query); announce('Consulta copiada. Pégala en el buscador oficial y revisa su sintaxis.'); }
  catch (_) { announce('No se pudo copiar automáticamente. Selecciona el texto visible de la consulta y cópialo.'); }
}
function addSuggestedConcept(index) {
  const entry = state.researchPlan?.suggestions?.[index];
  if (!entry?.term) return;
  const draft = state.profileDraft || profileDraft(state.profile);
  const lines = draft.conceptText.split('\n').filter(line => line.trim());
  if (lines.some(line => line.split('|')[0].trim().toLocaleLowerCase() === entry.term.toLocaleLowerCase())) { announce('Ese concepto ya está en el borrador.'); return; }
  if (lines.length >= 6) { state.profileError = 'El borrador ya tiene 6 conceptos. Edita o reemplaza alguno para añadir este término.'; location.hash = '#/tesis'; render(); $('#profile-concepts')?.focus(); return; }
  draft.conceptText = [...lines,entry.term].join('\n'); state.profileDraft = draft;
  state.profileNotice = 'Concepto añadido al borrador. Guarda para actualizar el plan local.';
  location.hash = '#/tesis'; render(); $('#profile-concepts')?.focus(); announce(state.profileNotice);
}
function renderNotFound() { return '<div class="empty-state"><h1>Esta página no está en el atlas.</h1><p>Vuelve a la biblioteca para seguir explorando.</p><a class="button" href="#/explorar">Abrir biblioteca</a></div>'; }
function render(focus = false) {
  if (!state.catalog) return;
  const [pathRoute, id] = location.hash.replace(/^#\/?/, '').split('/');
  const route = pathRoute || 'explorar';
  const active = activeRoute();
  renderNav(active);
  const headings = {novedades:'Actualización en longevidad',explorar:'Biblioteca de conceptos',ficha:'Biblioteca / Ficha de estudio',comparar:'Comparación de conceptos',conexiones:'Relaciones y procesos',tesis:'Mi línea de investigación',innovacion:'Innovación y descubrimiento',fuentes:'Literatura y criterios de evidencia',guia:'Guía del atlas'};
  $('#breadcrumb').textContent = headings[route] || 'Atlas de longevidad';
  document.title = `${headings[route] || 'Atlas'} · Atlas de longevidad`;
  const views = {novedades:renderRadar,explorar:renderExplore,comparar:renderCompare,conexiones:renderConnections,tesis:renderThesis,innovacion:renderInnovation,fuentes:renderEvidence,guia:renderGuide};
  $('#main').innerHTML = route === 'ficha' ? renderDetail(id) : (views[route] || renderNotFound)();
  updateCards(); renderEvidenceResults(); renderRadarResults(); renderTray(); setBusyControls();
  if (focus) { $('#main').focus({preventScroll:true}); window.scrollTo(0,0); }
}
function setBusyControls() {
  const radarView = ['novedades','innovacion'].includes(activeRoute());
  $('#refresh-button').disabled = state.busy || state.radarBusy;
  $('#refresh-button').innerHTML = `${icon('clock')}${radarView ? 'Actualizar radar' : activeRoute() === 'tesis' ? 'Preparar seguimiento' : 'Actualizar evidencia'}`;
  const search = $('#search-evidence-button');
  if (search) { search.disabled = state.busy; search.textContent = state.busy ? 'Consultando…' : 'Buscar artículos'; }
  const results = $('#evidence-results');
  if (results) results.setAttribute('aria-busy', String(state.busy));
  const radarForm = $('#radar-form fieldset');
  if (radarForm) radarForm.disabled = state.radarBusy || !radarSources().length;
  const radarSearch = $('#search-radar-button');
  if (radarSearch) radarSearch.textContent = state.radarBusy ? 'Consultando…' : activeRoute() === 'innovacion' ? 'Buscar registros' : 'Buscar novedades';
}
function readEvidenceForm() {
  const form = $('#evidence-form');
  if (!form) return true;
  if (!form.reportValidity()) return false;
  state.evidenceParams = Object.fromEntries(new FormData(form));
  return true;
}
async function runEvidence(force = false) {
  if (state.busy || !readEvidenceForm()) return;
  const params = {...state.evidenceParams};
  if (params.start > params.end) { state.localError = 'La fecha inicial debe ser anterior o igual a la final.'; renderEvidenceResults(); announce(state.localError); return; }
  state.busy = true; state.localError = ''; setBusyControls(); renderEvidenceResults();
  announce('Consultando la fuente oficial.');
  const requestId = ++state.requestId;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 60000);
  try {
    const response = await fetch(force ? '/api/refresh' : '/api/search?' + new URLSearchParams(params), force ? {method:'POST',headers:{'Content-Type':'application/json','X-Local-Request':'1'},body:JSON.stringify(params),signal:controller.signal} : {signal:controller.signal});
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'No se pudo completar la consulta.');
    if (!Array.isArray(result.articles)) throw new Error('La respuesta no tiene el formato esperado.');
    if (requestId === state.requestId) state.evidence = result;
    announce(result.error || `${result.articles.length} artículos recuperados de ${result.provider === 'pubmed' ? 'PubMed' : 'Europe PMC'}.`);
  } catch (error) {
    state.localError = error.name === 'AbortError' ? 'La consulta tardó demasiado. Reintenta y revisa el estado del servidor.' : `No se pudo contactar el servidor local. Comprueba que siga abierto. ${error.message}`;
    // Los resultados anteriores conservan su consulta y fecha originales.
    announce(state.localError);
  } finally {
    clearTimeout(timeout); state.busy = false; setBusyControls(); renderEvidenceResults();
  }
}
function openTerm(term) {
  const entry = state.catalog.glossary.find(item => item.term === term);
  if (!entry) return;
  state.previousFocus = document.activeElement;
  $('#glossary-title').textContent = entry.term;
  $('#glossary-definition').textContent = entry.definition;
  $('#glossary-sources').innerHTML = citations(entry.refs);
  $('#glossary-dialog').showModal();
  $('#close-dialog').focus();
}
document.addEventListener('input', event => {
  if (event.target.id === 'catalog-search') { state.search = event.target.value; updateCards(); announce(`${filteredTopics().length} conceptos encontrados.`); }
  if (['profile-title','profile-concepts','profile-enabled'].includes(event.target.id)) {
    state.profileDraft = {title:$('#profile-title').value,conceptText:$('#profile-concepts').value,enabled:$('#profile-enabled').checked};
  }
  if (event.target.matches('#radar-form [name]')) state.radarParams[event.target.name] = event.target.value;
  if (event.target.id === 'innovation-query') state.innovationQuery = event.target.value;
});
document.addEventListener('change', event => {
  if (event.target.matches('[data-compare]')) toggleSelection(event.target.dataset.compare, event.target.checked);
  if (event.target.id === 'radar-provider') { state.radarParams.provider = event.target.value; render(); $('#radar-provider')?.focus(); }
});
document.addEventListener('submit', event => {
  if (event.target.id === 'evidence-form') { event.preventDefault(); runEvidence(); }
  if (event.target.id === 'radar-form') { event.preventDefault(); runRadar(); }
  if (event.target.id === 'profile-form') { event.preventDefault(); saveResearchProfile(); }
  if (event.target.id === 'innovation-plan-form') { event.preventDefault(); prepareInnovationLinks(); }
});
document.addEventListener('click', event => {
  const target = event.target.closest('button, a');
  if (!target) return;
  if (target.matches('.skip-link')) { event.preventDefault(); $('#main').focus(); return; }
  if (target.dataset.category) {
    state.category = target.dataset.category;
    document.querySelectorAll('[data-category]').forEach(button => { const selected = button.dataset.category === state.category; button.classList.toggle('selected', selected); button.setAttribute('aria-pressed', String(selected)); });
    updateCards(); announce(`${filteredTopics().length} conceptos en ${state.category}.`);
  }
  if (target.dataset.term) openTerm(target.dataset.term);
  if (target.dataset.remove) { toggleSelection(target.dataset.remove, false); render(); $('#main').focus(); }
  if (target.dataset.searchTopic) {
    state.evidenceParams.q = topicById(target.dataset.searchTopic).search;
    location.hash = '#/fuentes'; // No enviar hasta pulsar Buscar artículos.
  }
  if (target.hasAttribute('data-use-query')) useResearchQuery(Number(target.dataset.useQuery));
  if (target.hasAttribute('data-use-bridge')) useResearchQuery(Number(target.dataset.useBridge),true);
  if (target.hasAttribute('data-add-concept')) addSuggestedConcept(Number(target.dataset.addConcept));
  if (target.hasAttribute('data-copy-search')) copyExternalQuery(Number(target.dataset.copySearch),target.dataset.copyGroup);
  const action = target.dataset.action;
  if (action === 'clear-selection') { state.selected.clear(); saveSelection(); render(); announce('Selección limpiada.'); }
  if (action === 'clear-filters') { state.search = ''; state.category = 'Todas'; render(); $('#catalog-search').focus(); }
  if (action === 'retry-evidence') runEvidence(true);
  if (action === 'retry-workspace') loadResearchWorkspace();
  if (action === 'retry-radar') runRadar(true);
  if (action === 'delete-profile') saveResearchProfile(true);
  if (action === 'longevity-query') {
    state.radarParams.q = state.researchPlan?.longevity_query || '(longevity OR aging OR ageing OR healthspan)';
    state.radarContext = 'Longevidad'; render(); $('#radar-query')?.focus(); announce('Consulta general preparada. Pulsa Buscar para enviarla.');
  }
  if (['radar-reset-dates','radar-recent-dates'].includes(action)) {
    state.radarParams.start = daysAgo(action === 'radar-recent-dates' ? 90 : 365); state.radarParams.end = today();
    render(); $('#radar-start')?.focus(); announce('Fechas preparadas; pulsa Buscar para actualizar.');
  }
  if (action === 'reset-evidence-filters') {
    state.evidenceParams = {...state.evidenceParams, start:'1900-01-01', end:today(), kind:'all', model:'all'};
    render(); $('#evidence-query').focus();
  }
});
$('#guide-button').addEventListener('click', () => { location.hash = '#/guia'; });
$('#refresh-button').addEventListener('click', () => {
  if (['novedades','innovacion'].includes(activeRoute())) { runRadar(true); return; }
  if (activeRoute() === 'tesis') {
    if (state.profile?.enabled && state.researchPlan?.queries?.length) useResearchQuery(0);
    else { location.hash = '#/novedades'; render(true); announce('Configura tu investigación o revisa la consulta general antes de buscar.'); }
    return;
  }
  if (activeRoute() !== 'fuentes') { location.hash = '#/fuentes'; render(); }
  runEvidence(true);
});
$('#close-dialog').addEventListener('click', () => $('#glossary-dialog').close());
$('#glossary-dialog').addEventListener('close', () => state.previousFocus?.focus());
$('#glossary-dialog').addEventListener('keydown', event => {
  if (event.key !== 'Tab') return;
  const controls = [...$('#glossary-dialog').querySelectorAll('button, a[href], input, select, textarea, [tabindex="0"]')].filter(element => !element.disabled && element.getClientRects().length);
  const first = controls[0], last = controls[controls.length - 1];
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
});
window.addEventListener('hashchange', () => render(true));
document.addEventListener('keydown', event => {
  if (event.key === '/' && !/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName) && !$('#glossary-dialog').open) {
    const search = $('#catalog-search');
    if (search) { event.preventDefault(); search.focus(); }
  }
});
async function start() {
  try {
    const response = await fetch('/api/catalog');
    if (!response.ok) throw new Error('No se pudo leer la biblioteca del proyecto.');
    state.catalog = await response.json();
    state.selected = new Set([...state.selected].filter(id => topicById(id)));
    saveSelection(); // Retira de la selección persistida IDs que ya no pertenecen a la biblioteca.
    render();
    loadResearchWorkspace();
  } catch (_) {
    $('#main').innerHTML = '<div class="empty-state"><h1>No se pudo abrir la biblioteca.</h1><p>Inicia el servidor con python3 server.py desde la carpeta del proyecto y vuelve a cargar esta página.</p><button class="button" id="reload">Reintentar</button></div>';
    $('#reload').addEventListener('click', () => location.reload());
  }
}
start();
