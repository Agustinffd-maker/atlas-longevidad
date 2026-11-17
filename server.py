#!/usr/bin/env python3
"""Servidor exclusivamente local, sin paquetes externos."""
import argparse
import json
import mimetypes
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from cache import EvidenceCache
from sources import EvidenceService, OfficialClient, validate_params
from journal_metrics import enrich_article
from radar_service import RadarService, validate_radar_params
from research_profile import load_profile, save_profile, delete_profile, validate_profile
from research_api import radar_metadata, research_plan

ROOT = Path(__file__).resolve().parent


def make_handler(service, radar=None, profile_path=None):
    radar = radar or RadarService(EvidenceCache(ROOT / '.cache/radar.json', 21600, records_key='items'),
                                  client=getattr(service, 'client', None))
    profile_path = profile_path or ROOT / '.cache/thesis-profile.json'
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            # Evita que consultas escritas por el usuario terminen en logs.
            pass

        def local_request(self):
            host = self.headers.get("Host", "")
            allowed = {"127.0.0.1:" + str(self.server.server_port), "localhost:" + str(self.server.server_port)}
            origin = self.headers.get("Origin")
            return host in allowed and (not origin or origin in {"http://" + value for value in allowed}) and self.headers.get("Sec-Fetch-Site") not in {"cross-site"}

        def send(self, code, data, mime="application/json; charset=utf-8"):
            raw = json.dumps(data, ensure_ascii=False).encode() if not isinstance(data, bytes) else data
            try:
                self.send_response(code)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(len(raw)))
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(raw)
            except (BrokenPipeError, ConnectionResetError):
                # Una navegación o AbortController puede cerrar el cliente antes de responder.
                return

        def do_GET(self):
            if not self.local_request():
                return self.send(403, {"error": "Solo se permite el origen local."})
            parsed = urlparse(self.path)
            try:
                if parsed.path == "/api/catalog":
                    catalog = json.loads((ROOT / "data/catalog.json").read_text(encoding="utf-8"))
                    catalog["references"] = json.loads((ROOT / "data/reference_seed.json").read_text(encoding="utf-8"))
                    reviews = json.loads((ROOT / "data/reference_review.json").read_text(encoding="utf-8"))
                    for pmid, notes in reviews.items():
                        if pmid in catalog["references"]:
                            catalog["references"][pmid].update(notes)
                    catalog['references'] = {pmid: enrich_article(article) for pmid, article in catalog['references'].items()}
                    return self.send(200, catalog)
                if parsed.path == "/api/search":
                    values = {key: val[-1] for key, val in parse_qs(parsed.query).items()}
                    return self.send(200, service.search(validate_params(values)))
                if parsed.path == '/api/profile':
                    return self.send(200, load_profile(profile_path))
                if parsed.path == '/api/research-plan':
                    values = parse_qs(parsed.query)
                    query = values.get('q', [None])[-1]
                    if query is not None:
                        query = validate_radar_params({'q': query})['q']
                    return self.send(200, research_plan(profile_path, query))
                if parsed.path == '/api/radar/meta':
                    return self.send(200, radar_metadata())
                if parsed.path == '/api/radar':
                    values = {key: val[-1] for key, val in parse_qs(parsed.query).items()}
                    return self.send(200, radar.search(validate_radar_params(values)))
                if parsed.path == "/api/status":
                    return self.send(200, {"ttl_hours": 24, "interval_hours": 6, "local_only": True,
                        "cached_queries": len(service.cache.parameters()), 'radar_ttl_hours': 6,
                        'radar_cached_queries': len(radar.cache.parameters()),
                        'thesis_enabled': load_profile(profile_path)['enabled']})
                files = {"/": "index.html", "/index.html": "index.html", "/app.js": "app.js", "/style.css": "style.css", "/favicon.svg": "favicon.svg"}
                name = files.get(parsed.path)
                if not name:
                    return self.send(404, {"error": "Ruta no disponible."})
                path = ROOT / "static" / name
                return self.send(200, path.read_bytes(), (mimetypes.guess_type(name)[0] or "application/octet-stream") + "; charset=utf-8")
            except ValueError as exc:
                return self.send(400, {"error": str(exc)})
            except (OSError, KeyError):
                return self.send(500, {"error": "No se pudo leer el recurso local."})

        def do_POST(self):
            if not self.local_request() or self.headers.get("X-Local-Request") != "1":
                return self.send(403, {"error": "Actualización permitida solo desde esta aplicación local."})
            route = urlparse(self.path).path
            if route not in {'/api/refresh', '/api/profile', '/api/radar/refresh'}:
                return self.send(404, {"error": "Ruta no disponible."})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length < (16384 if route == '/api/profile' else 4096):
                    raise ValueError("Tamaño de solicitud inválido.")
                values = json.loads(self.rfile.read(length))
                if not isinstance(values, dict):
                    raise ValueError("Se esperaba un objeto JSON.")
                if route == '/api/profile':
                    profile = validate_profile(values)
                    with radar.lock:
                        radar.clear()
                        profile = save_profile(profile_path, profile)
                    return self.send(200, profile)
                if route == '/api/radar/refresh':
                    return self.send(200, radar.search(validate_radar_params(values), force=True))
                return self.send(200, service.search(validate_params(values), force=True))
            except (ValueError, TypeError) as exc:
                return self.send(400, {"error": str(exc)})
            except OSError:
                return self.send(500, {'error': 'No se pudo guardar el archivo local. Comprueba el espacio y los permisos.'})

        def do_DELETE(self):
            if not self.local_request() or self.headers.get('X-Local-Request') != '1':
                return self.send(403, {'error': 'Solo se permite cambiar el perfil desde esta aplicación local.'})
            if urlparse(self.path).path != '/api/profile':
                return self.send(404, {'error': 'Ruta no disponible.'})
            try:
                with radar.lock:
                    profile = delete_profile(profile_path)
                    radar.clear()
                return self.send(200, profile)
            except OSError:
                return self.send(500, {'error': 'No se pudo borrar el perfil local.'})
    return Handler


def periodic_refresh(service, stopped, radar=None):
    # Revisa caducidad cada 6 h; renueva consultas de las últimas 100 búsquedas.
    while not stopped.wait(6 * 3600):
        for params in service.cache.parameters():
            if stopped.is_set():
                return
            service.search(params)
        if radar is not None:
            radar.refresh_saved(stopped)


def main():
    parser = argparse.ArgumentParser(description="Biomarcadores: servidor solo en este computador")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Usa un puerto entre 1024 y 65535.")
    client = OfficialClient()
    service = EvidenceService(EvidenceCache(ROOT / ".cache/evidence.json"), client=client)
    radar = RadarService(EvidenceCache(ROOT / '.cache/radar.json', 21600, records_key='items'), client=client)
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(service, radar=radar))
    except OSError:
        parser.exit(1, "No se pudo abrir el puerto local. Comprueba si ya está abierto o usa --port 8766.\n")
    server.daemon_threads = True
    stopped = threading.Event()
    threading.Thread(target=periodic_refresh, args=(service, stopped, radar), daemon=True).start()
    print("Biomarcadores · http://localhost:" + str(args.port), flush=True)
    print("Solo este computador. Detener: Ctrl+C. Caché bibliográfica: 24 h; radar: 6 h. Revisión cada 6 h con el servidor abierto.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.", flush=True)
    finally:
        stopped.set()
        server.server_close()


if __name__ == "__main__":
    main()
