#!/usr/bin/env python3
"""QA opcional con Playwright/axe aislados y fuentes SINTÉTICAS, nunca evidencia real.

Usa servidor local, configuración temporal propia y ningún proveedor externo.
El informe y las capturas quedan únicamente en .cache/qa.
"""
import json
import sys
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import sync_playwright, expect
from audit_ui import BASE, OUTPUT, inspect

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research_api import radar_metadata, research_plan
from research_profile import load_profile, save_profile, delete_profile


def fixture(params):
    provider = params['provider']
    kind = 'trial' if provider == 'trials' else 'preprint' if provider == 'preprints' else 'paper'
    item = dict(id='SYNTHETIC-UI-TEST', title='SYNTHETIC UI TEST: not scientific evidence',
                url='https://clinicaltrials.gov/search' if kind == 'trial' else 'https://europepmc.org/search',
                published='2026-11-01', journal='SYNTHETIC TEST JOURNAL' if kind == 'paper' else '',
                kind=kind, evidence_status='Fixture de interfaz; no evidencia científica.',
                summary='SYNTHETIC UI TEST ONLY', source=provider, source_label=provider,
                metadata_only=False, quartile='cuartil no verificado', has_results=None)
    return dict(items=[item], total=1, query=params['q'], provider=provider,
                fetched_at='2026-11-10T12:00:00+00:00', last_attempt_at='2026-11-10T12:00:00+00:00',
                stale=False, cached=False, error=None, date_basis='Fecha del registro de prueba.',
                query_semantics='Respuesta controlada, no validación de proveedor.')


def main():
    (OUTPUT/'screenshots').mkdir(parents=True, exist_ok=True)
    report = dict(output_name='platform-ui-report.json', states=[], console_errors=[], external_requests=[],
                  search_requests=[], scenarios=[], widths=[320,390,768,1440])
    with sync_playwright() as playwright, tempfile.TemporaryDirectory(dir=OUTPUT) as folder:
        browser = playwright.chromium.launch()
        for width in report['widths']:
            profile_path = Path(folder)/('profile-'+str(width)+'.json')
            context = browser.new_context(viewport={'width':width,'height':900}, reduced_motion='reduce', locale='es-CL')
            context.add_init_script(path=str(OUTPUT/'axe.min.js'))
            context.add_init_script("Object.defineProperty(navigator, 'clipboard', {value: {writeText: async text => { window.__qaCopied = text; }}});")
            page = context.new_page()
            page.on('pageerror', lambda error: report['console_errors'].append(str(error)))
            page.on('request', lambda req: report['external_requests'].append(req.url) if not req.url.startswith(BASE) else None)

            def fulfill(route, value):
                route.fulfill(content_type='application/json', body=json.dumps(value))

            page.route('**/api/radar/meta', lambda route: fulfill(route, radar_metadata()))
            def profile_route(route):
                if route.request.method == 'POST':
                    result = save_profile(profile_path, route.request.post_data_json)
                elif route.request.method == 'DELETE':
                    result = delete_profile(profile_path)
                else:
                    result = load_profile(profile_path)
                fulfill(route, result)
            page.route('**/api/profile', profile_route)
            delayed_plans = []
            delay_innovation = False
            def plan_route(route):
                query = parse_qs(urlparse(route.request.url).query).get('q', [None])[0]
                payload = research_plan(profile_path, query)
                if delay_innovation and query is not None:
                    delayed_plans.append((route, payload))
                else:
                    fulfill(route, payload)
            page.route('**/api/research-plan*', plan_route)

            mode = 'result'
            pending = []
            def radar_route(route):
                params = route.request.post_data_json if route.request.method == 'POST' else {
                    key:values[0] for key,values in parse_qs(urlparse(route.request.url).query).items()}
                report['search_requests'].append(params)
                value = fixture(params)
                if mode == 'loading':
                    pending.append((route,value))
                    return
                if mode == 'empty':
                    value.update(items=[],total=0)
                elif mode == 'offline':
                    value.update(stale=True,cached=True,error='TEST: proveedor inaccesible')
                fulfill(route, value)
            page.route('**/api/radar?*', radar_route)
            page.route('**/api/radar/refresh', radar_route)

            def audit(label, capture=False):
                inspect(page,'platform-'+label+'-'+str(width),report,capture)

            page.goto(BASE+'/#/novedades')
            expect(page.locator('#radar-provider option')).to_have_count(5)
            before = len(report['search_requests'])
            audit('news',True)
            for disclosure in page.locator('main details').all():
                if not disclosure.evaluate('element => element.open'):
                    disclosure.locator('summary').first.click()
            audit('source-and-journal-guides')
            page.locator('#navigation a[href="#/tesis"]').click()
            expect(page.locator('#profile-concepts')).to_be_enabled()
            audit('onboarding',True)
            page.locator('#profile-title').fill('SYNTHETIC LOCAL LABEL')
            page.locator('#profile-concepts').fill('modelos fundacionales biomédicos | biomedical foundation models\nIA multimodal | multimodal AI\ncélula virtual | virtual cell')
            page.locator('#profile-enabled').check()
            page.locator('#save-profile').click()
            expect(page.locator('#profile-notice')).to_contain_text('guardado')
            expect(page.locator('#save-profile')).to_be_focused()
            expect(page.locator('[data-use-query]')).to_have_count(3)
            assert len(report['search_requests']) == before
            audit('configured',True)
            page.locator('[data-use-query]').first.click()
            expect(page.locator('#radar-query')).to_contain_text('biomedical foundation models')
            assert len(report['search_requests']) == before
            page.locator('#radar-query').fill('medical\nAI')
            page.locator('#search-radar-button').click()
            expect(page.locator('.radar-item')).to_have_count(1)
            assert report['search_requests'][-1]['q'] == 'medical AI'
            assert 'SYNTHETIC LOCAL LABEL' not in json.dumps(report['search_requests'])
            audit('paper',True)
            page.locator('#radar-provider').select_option('preprints')
            page.locator('#search-radar-button').click()
            expect(page.locator('.radar-item .label')).to_contain_text('Preprint')
            audit('preprint')
            mode = 'offline'
            page.locator('#refresh-button').click()
            expect(page.locator('#radar-results .alert.error')).to_contain_text('TEST: proveedor')
            expect(page.locator('.radar-item')).to_have_count(1)
            audit('offline')
            mode = 'empty'
            page.locator('#refresh-button').click()
            expect(page.locator('#radar-results')).to_contain_text('No se encontraron registros')
            audit('empty')
            mode = 'loading'
            page.locator('#refresh-button').click()
            expect(page.locator('#search-radar-button')).to_be_disabled()
            expect(page.locator('#radar-results')).to_have_attribute('aria-busy','true')
            audit('loading')
            route, value = pending.pop()
            fulfill(route, value)
            expect(page.locator('#search-radar-button')).to_be_enabled()
            mode = 'result'
            page.locator('#navigation a[href="#/innovacion"]').click()
            expect(page.locator('#radar-results .radar-item')).to_have_count(0)
            page.locator('#search-radar-button').click()
            expect(page.locator('.radar-item .label')).to_contain_text('Registro')
            expect(page.locator('[data-copy-search]')).to_have_count(3)
            page.locator('[data-copy-search]').first.click()
            assert page.evaluate("typeof window.__qaCopied === 'string' && window.__qaCopied.length > 0")
            assert page.locator('a[href="https://worldwide.espacenet.com/patent/search"]').count() >= 1
            audit('innovation',True)
            before = len(report['search_requests'])
            page.locator('#innovation-query').fill('autophagy longevity')
            page.locator('#innovation-plan-form button').click()
            expect(page.locator('#innovation-plan-form [role="status"]')).to_contain_text('Enlaces preparados')
            assert len(report['search_requests']) == before
            page.locator('#navigation a[href="#/tesis"]').click()
            draft_before = page.locator('#profile-concepts').input_value()
            page.locator('[data-add-concept]').first.click()
            expect(page.locator('#profile-concepts')).not_to_have_value(draft_before)
            assert len(load_profile(profile_path)['concepts']) == 3
            audit('suggestion-draft')

            # Respuesta local antigua de enlaces no debe reinstalar conceptos tras borrar.
            page.locator('#navigation a[href="#/innovacion"]').click()
            delay_innovation = True
            page.locator('#innovation-query').fill('TEST OLD CONCEPT')
            page.locator('#innovation-plan-form button').click()
            page.locator('#navigation a[href="#/tesis"]').click()
            page.locator('[data-action="delete-profile"]').click()
            expect(page.locator('#profile-notice')).to_contain_text('eliminados')
            expect(page.locator('#profile-concepts')).to_be_focused()
            assert not profile_path.exists()
            for route, payload in delayed_plans:
                fulfill(route, payload)
            delay_innovation = False
            page.locator('#navigation a[href="#/innovacion"]').click()
            expect(page.locator('#innovation-query')).not_to_have_value('TEST OLD CONCEPT')
            expect(page.locator('#main')).not_to_contain_text('TEST OLD CONCEPT')
            assert len(report['search_requests']) == before
            audit('deleted-profile-no-old-preview')
            report['scenarios'].append(dict(width=width,profile='temporary, no real user profile changed',
                late_response='discarded after delete',no_automatic_search=True))
            context.close()
        browser.close()
    report['violations'] = sum(len(state['violations']) for state in report['states'])
    report['overflows'] = [state['label'] for state in report['states'] if state['geometry']['horizontalOverflow'] or state['geometry']['clippedFixedControls']]
    (OUTPUT/report['output_name']).write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({key:report[key] for key in ('violations','overflows','console_errors','external_requests')},ensure_ascii=False))
    print('Estados plataforma:',len(report['states']))
    if report['violations'] or report['overflows'] or report['console_errors'] or report['external_requests']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
