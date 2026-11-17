#!/usr/bin/env python3
"""QA opcional: Playwright + axe en entorno aislado; no son dependencias del atlas.

Requiere servidor propio en localhost:8767 y .cache/qa/axe.min.js.
Los resultados, capturas y respuestas controladas quedan solo en .cache/qa.
"""
import json
import os
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / ".cache/qa"
BASE = os.environ.get("ATLAS_QA_BASE_URL", "http://127.0.0.1:8767")


def tab_to(page, selector, limit=90):
    """Alcanzar un control mediante Tab real, sin enfocar el elemento con JS."""
    for _ in range(limit):
        page.keyboard.press("Tab")
        if page.locator(selector).evaluate("element => element === document.activeElement"):
            return
    raise AssertionError("No se alcanzó con Tab: " + selector)


def inspect(page, label, report, capture=False):
    page.wait_for_function("document.querySelector('#main h1') !== null")
    result = page.evaluate("""async () => {
        const result = await axe.run(document, {runOnly: {
            type: 'tag', values: ['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa','best-practice']
        }});
        return {violations: result.violations, incomplete: result.incomplete,
            passes: result.passes.length, inapplicable: result.inapplicable.length};
    }""")
    geometry = page.evaluate("""() => ({width: innerWidth,
        documentWidth: document.documentElement.scrollWidth,
        horizontalOverflow: document.documentElement.scrollWidth > innerWidth + 1,
        clippedFixedControls: [...document.querySelectorAll('#compare-tray:not([hidden]) a, #compare-tray:not([hidden]) button')]
            .filter(e => e.getClientRects().length && (e.getBoundingClientRect().right > innerWidth + 1 || e.getBoundingClientRect().left < 0))
            .map(e => e.textContent.trim()),
        headings: [...document.querySelectorAll('main h1')].map(node=>node.textContent),
        focus: document.activeElement?.tagName})""")
    report["states"].append(dict(label=label, geometry=geometry, **result))
    (OUTPUT/report.get('output_name', 'ui-report.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2))
    if capture:
        page.screenshot(path=str(OUTPUT / "screenshots" / (label + ".png")), full_page=True)


def keyboard_journey(page, report):
    page.goto(BASE)
    page.reload()  # Un cambio de hash por sí solo conserva el estado de la SPA.
    page.wait_for_selector('.topic-card')
    page.keyboard.press('Tab')
    expect(page.locator('.skip-link')).to_be_focused()
    page.keyboard.press('Enter')
    expect(page.locator('#main')).to_be_focused()
    page.keyboard.press('/')
    expect(page.locator('#catalog-search')).to_be_focused()
    page.keyboard.type('biologia computacional')
    expect(page.locator('.topic-card')).to_have_count(2)
    tab_to(page, '[data-compare="modelo-unicelular"]')
    page.keyboard.press('Space')
    tab_to(page, '[data-compare="celula-virtual"]')
    page.keyboard.press('Space')
    tab_to(page, '#compare-tray a')
    page.keyboard.press('Enter')
    expect(page.locator('.compare-table')).to_be_visible()
    expect(page.locator('.compare-table thead th')).to_have_count(3)
    expect(page.locator('#main')).to_be_focused()
    inspect(page,'compare-two-'+str(page.viewport_size['width']),report)
    tab_to(page, '.compare-table a[href="#/ficha/modelo-unicelular"]')
    page.keyboard.press('Enter')
    expected = next(topic['name'] for topic in json.loads((ROOT/'data/catalog.json').read_text())['topics'] if topic['id'] == 'modelo-unicelular')
    expect(page.locator('h1')).to_have_text(expected)
    tab_to(page, '[data-term="Validación externa"]')
    page.keyboard.press('Enter')
    expect(page.locator('#glossary-dialog')).to_be_visible()
    expect(page.locator('#close-dialog')).to_be_focused()
    inspect(page,'glossary-dialog-'+str(page.viewport_size['width']),report)
    # El foco queda dentro del diálogo al avanzar y retroceder.
    for _ in range(5):
        page.keyboard.press('Tab')
        assert page.evaluate("document.querySelector('#glossary-dialog').contains(document.activeElement)")
        page.keyboard.press('Shift+Tab')
        assert page.evaluate("document.querySelector('#glossary-dialog').contains(document.activeElement)")
    page.keyboard.press('Escape')
    expect(page.locator('[data-term="Validación externa"]')).to_be_focused()
    tab_to(page, '.back-link')
    page.keyboard.press('Enter')
    expect(page.locator('#catalog-search')).to_have_value('biologia computacional')
    expect(page.locator('.topic-card')).to_have_count(2)
    report['keyboard_journey'] = 'passed: skip link, search, selection, comparison, detail, dialog trap, Escape and focus return'


def controlled_evidence(page, report):
    """Metadatos reales reutilizados solo como fixture; ninguna llamada a proveedores."""
    refs = json.loads((ROOT/'data/reference_seed.json').read_text())
    articles = list(refs.values())[:2]
    payload = dict(articles=articles,total=2,query='PUBLIC TEST QUERY',provider='pubmed',
                   fetched_at='2026-11-10T12:00:00+00:00',last_attempt_at='2026-11-10T12:00:00+00:00',
                   stale=False,cached=False,error=None)
    requests = []
    def response(route):
        requests.append(route.request.url)
        route.fulfill(status=200, content_type='application/json', body=json.dumps(payload))
    page.route('**/api/search?*', response)
    page.route('**/api/refresh', response)
    page.goto(BASE+'/#/fuentes')
    page.locator('#evidence-query').fill('PUBLIC TEST QUERY')
    page.locator('#kind').select_option('review')
    page.locator('#model').select_option('humans')
    page.locator('#start').fill('2020-01-01')
    page.locator('#search-evidence-button').click()
    expect(page.locator('.article-item')).to_have_count(2)
    sent = parse_qs(urlparse(requests[0]).query)
    assert sent['q'] == ['PUBLIC TEST QUERY']
    assert sent['kind'] == ['review'] and sent['model'] == ['humans']
    assert sent['start'] == ['2020-01-01']
    report['controlled_filters'] = 'passed: date, publication type, model and rendered results; controlled response, not provider validation'
    inspect(page,'evidence-results-'+str(page.viewport_size['width']),report)
    payload.update(stale=True,cached=True,error='TEST: fuente sin conexión')
    page.locator('#refresh-button').click()
    expect(page.locator('.alert.error')).to_contain_text('TEST: fuente sin conexión')
    expect(page.locator('.article-item')).to_have_count(2)
    inspect(page,'evidence-offline-'+str(page.viewport_size['width']),report,capture=True)
    payload.update(articles=[],total=0,stale=False,error=None)
    page.locator('#refresh-button').click()
    expect(page.locator('#evidence-results')).to_contain_text('No se encontraron artículos')
    inspect(page,'evidence-empty-'+str(page.viewport_size['width']),report)
    page.unroute('**/api/search?*')
    page.unroute('**/api/refresh')


def error_and_loading_states(page, report):
    """Fallo de proveedor y de transporte local separados, sin cortar la red del equipo."""
    width = str(page.viewport_size['width'])
    page.goto(BASE+'/#/fuentes')
    page.reload()
    page.locator('#evidence-query').fill('PUBLIC TEST QUERY')
    pending = []
    page.route('**/api/search?*', lambda route: pending.append(route))
    page.locator('#search-evidence-button').click()
    expect(page.locator('#search-evidence-button')).to_be_disabled()
    expect(page.locator('#refresh-button')).to_be_disabled()
    expect(page.locator('#evidence-results')).to_have_attribute('aria-busy', 'true')
    expect(page.locator('#evidence-results [role="status"]')).to_be_visible()
    inspect(page,'evidence-loading-'+width,report)
    assert len(pending) == 1
    payload = dict(articles=[],total=None,query='PUBLIC TEST QUERY',provider='pubmed',
                   fetched_at=None,last_attempt_at='2026-11-10T12:00:00+00:00',
                   stale=True,cached=False,error='TEST: proveedor inaccesible')
    pending[0].fulfill(status=200, content_type='application/json', body=json.dumps(payload))
    expect(page.locator('.alert.error')).to_contain_text('No hay una copia guardada')
    expect(page.locator('.article-item')).to_have_count(0)
    inspect(page,'evidence-no-cache-'+width,report)
    page.unroute('**/api/search?*')
    page.context.set_offline(True)
    try:
        page.locator('#navigation a[href="#/explorar"]').click()
        expect(page.locator('.topic-card')).to_have_count(9)
        page.locator('#catalog-search').fill('biologia computacional')
        expect(page.locator('.topic-card')).to_have_count(2)
        page.locator('#navigation a[href="#/fuentes"]').click()
        page.locator('#search-evidence-button').click()
        expect(page.locator('.alert.error').first).to_contain_text('servidor local')
        inspect(page,'local-transport-offline-'+width,report)
    finally:
        page.context.set_offline(False)
    page.route('**/api/catalog', lambda route: route.fulfill(status=503,content_type='application/json',body='{}'))
    page.goto(BASE)
    page.reload()
    expect(page.locator('h1')).to_have_text('No se pudo abrir la biblioteca.')
    inspect(page,'catalog-load-error-'+width,report)
    page.unroute('**/api/catalog')
    page.locator('#reload').click()
    expect(page.locator('.topic-card')).to_have_count(9)
    report['error_and_loading_states'] = 'passed: loading, provider failure without cache, offline local filtering, local transport failure and catalog retry'


def visual_checks(page, report):
    width = str(page.viewport_size['width'])
    page.goto(BASE)
    page.reload()
    page.wait_for_selector('.topic-card')
    page.screenshot(path=str(OUTPUT/'screenshots'/('viewport-'+width+'.png')))
    # Navegación móvil completa visible, sin enlaces fuera de un contenedor recortado.
    if page.viewport_size['width'] < 700:
        assert page.locator('#navigation').evaluate('e => e.scrollWidth <= e.clientWidth + 1')
    page.goto(BASE+'/#/ficha/modelo-unicelular')
    page.wait_for_selector('.detail-header')
    page.locator('[data-term="Validación externa"]').click()
    page.screenshot(path=str(OUTPUT/'screenshots'/('dialog-viewport-'+width+'.png')))
    report.setdefault('dialog_colors', {})[width] = page.locator('#glossary-definition').evaluate('e => ({foreground: getComputedStyle(e).color, background: getComputedStyle(e.parentElement).backgroundColor})')
    page.keyboard.press('Escape')
    page.goto(BASE+'/#/comparar')
    page.wait_for_selector('.compare-table')
    if page.viewport_size['width'] < 768:
        table = page.locator('.compare-scroll')
        table.focus()
        page.keyboard.press('ArrowRight')
        page.wait_for_function("() => document.querySelector('.compare-scroll').scrollLeft > 0")
        page.screenshot(path=str(OUTPUT/'screenshots'/('compare-scroll-'+width+'.png')))


def focus_coverage(page, report):
    """Detectar foco tapado por elementos fijos; usar el primer rectángulo de enlaces multilínea."""
    page.goto(BASE)
    page.reload()
    page.wait_for_selector('.topic-card')
    for _ in range(45):
        page.keyboard.press('Tab')
        row = page.evaluate('''() => {
            const e = document.activeElement, r = e.getClientRects()[0];
            if (!r || !r.width || !r.height || e === document.body) return null;
            const x = r.x + r.width / 2, y = r.y + r.height / 2;
            const top = document.elementFromPoint(x,y);
            return {width: innerWidth, name: e.getAttribute('aria-label') || e.textContent.trim().slice(0,70),
                obscured: !top || !(e === top || e.contains(top)),
                visible: x >= 0 && x <= innerWidth && y >= 0 && y <= innerHeight};
        }''')
        if row: report.setdefault('focus_checks', []).append(row)


def main():
    (OUTPUT/'screenshots').mkdir(parents=True,exist_ok=True)
    report=dict(engine='Chromium',axe_version=json.loads((OUTPUT/'axe-version.json').read_text())['version'],
                widths=[320,390,768,1440],states=[],console_errors=[],external_requests=[])
    catalog=json.loads((ROOT/'data/catalog.json').read_text())
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(headless=True)
        for width in report['widths']:
            context=browser.new_context(viewport={'width':width,'height':900},locale='es-CL',timezone_id='America/Santiago',
                                        reduced_motion='reduce',has_touch=width<768)
            context.add_init_script(path=str(OUTPUT / "axe.min.js"))
            page=context.new_page()
            page.on('pageerror',lambda error: report['console_errors'].append(str(error)))
            page.on('request',lambda request: report['external_requests'].append(request.url) if not request.url.startswith(BASE) else None)
            for route in ['explorar','novedades','comparar','conexiones','tesis','innovacion','fuentes','guia']:
                page.goto(BASE+'/#/'+route)
                inspect(page,route+'-'+str(width),report,capture=route in ['explorar','tesis'])
            for topic in catalog['topics']:
                page.goto(BASE+'/#/ficha/'+topic['id'])
                page.wait_for_selector('.detail-header')
                for disclosure in page.locator('main details').all():
                    if not disclosure.evaluate('element => element.open'):
                        disclosure.locator(':scope > summary').click()
                inspect(page,'ficha-'+topic['id']+'-'+str(width),report)
            page.goto(BASE+'/#/explorar')
            page.wait_for_selector('.topic-card')
            page.get_by_role('button',name='Biología computacional',exact=True).click()
            expect(page.locator('.topic-card')).to_have_count(2)
            page.locator('#catalog-search').fill('TEST NO RESULT XYZ')
            expect(page.locator('.topic-card')).to_have_count(0)
            inspect(page,'catalog-empty-'+str(width),report)
            page.get_by_role('button',name='Limpiar búsqueda y filtros').click()
            page.locator('[data-compare]').first.check()
            inspect(page,'compare-one-tray-'+str(width),report)
            for control in page.locator('[data-compare]').all(): control.check()
            page.locator('#compare-tray a').click()
            expect(page.locator('.compare-table thead th')).to_have_count(10)
            inspect(page,'compare-nine-'+str(width),report,capture=True)
            # Empezar el recorrido con contexto limpio sin selección persistida.
            page.evaluate('localStorage.clear()')
            keyboard_journey(page,report)
            controlled_evidence(page,report)
            error_and_loading_states(page,report)
            visual_checks(page,report)
            focus_coverage(page,report)
            context.close()
        browser.close()
    report['violations']=sum(len(state['violations']) for state in report['states'])
    report['overflows']=[state['label'] for state in report['states'] if state['geometry']['horizontalOverflow'] or state['geometry']['clippedFixedControls']]
    report['focus_obscured']=[row for row in report.get('focus_checks', []) if row['obscured'] or not row['visible']]
    (OUTPUT/'ui-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({key:report[key] for key in ('axe_version','widths','violations','overflows','console_errors','external_requests')},ensure_ascii=False))
    print('Estados auditados:',len(report['states']))
    print('Paradas de foco comprobadas:',len(report.get('focus_checks', [])), 'Problemas:',len(report['focus_obscured']))
    if report['violations'] or report['overflows'] or report['console_errors'] or report['focus_obscured']:
        raise SystemExit(1)


if __name__=='__main__': main()
