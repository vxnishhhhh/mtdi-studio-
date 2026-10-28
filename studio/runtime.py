"""Lifecycle, transport and persistence integration for the instrument."""
from collections import OrderedDict, deque
from pathlib import Path
import functools
import hashlib
import json
import logging
import math
import os
import re
import queue
import socket
import sys
import threading
import time
from urllib.parse import urlsplit

from flask import Response, redirect, request, session
from .analysis import AnalysisEngine
from .d4live import D4Service
from . import d4 as d4mod
from .devices import CameraService, TelemetryService
from .audition import FieldAudition

LOG = logging.getLogger('studio')


def clean_text(value):
    return str(value).replace('\u2014', ' · ').replace('\u2013', ' to ')


def stream_changes(previous, current):
    """Describe changed fields while preserving explicit nulls and removals."""
    changes, removed = [], []

    def visit(old, new, path):
        if isinstance(old, dict) and isinstance(new, dict):
            removed.extend(path + [key] for key in old if key not in new)
            for key, value in new.items():
                if key not in old:
                    changes.append([path + [key], value])
                else:
                    visit(old[key], value, path + [key])
        elif old != new:
            changes.append([path, new])

    visit(previous, current, [])
    return {'base': previous['sequence'], 'sequence': current['sequence'],
            'changes': changes, 'removed': removed}


class Runtime:
    """Own deferred services and share bounded snapshots across browser clients."""

    def __init__(self, ns):
        self.ns = ns
        self.state_dir = Path(os.environ.get('STUDIO_STATE_DIR', str(Path.home() / '.local/share/mtdi-studio'))).expanduser()
        self.engine = AnalysisEngine(self.state_dir / 'calibration.json')
        self.d4 = D4Service(ns, self.engine)
        self.camera = CameraService(state_dir=self.state_dir)
        self.audition = FieldAudition(channel_state=lambda: self.engine.channels['ch2']['state'],
                                      c1_state=lambda: self.engine.channels['ch1']['state'])
        ns['_v238_audio_feed'] = self.audition.sources['ch2f'].feed
        ns['_v238_c1_feed'] = self.audition.sources['c1'].feed_value
        ns['_v238_audio_active'] = lambda: self.audition.sources['ch2f'].state['enabled']
        self.telemetry = TelemetryService(ns['APP_VERSION'], camera=self.camera,
                                          calibration_provider=lambda: {key: self.engine.calibrations.get(key) for key in self.engine.channels})
        try:
            saved = json.loads((self.state_dir / 'mode.json').read_text()).get('mode')
            if saved in ('online', 'offline'):
                ns['INSTRUMENT_MODE']['mode'] = saved
        except (OSError, ValueError, AttributeError):
            pass
        self.started = False
        self.deferred = False
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.sequence = 0
        self.last_payload = None
        self._stream_json = None
        self.stream_packet = None
        self.stream_patch_json = None
        self.stream_patch_base = None
        self.stream_signature = None
        self.stream_sequence = 0
        self.snapshot_at = 0
        self.events = deque(maxlen=256)
        self.metrics = deque(maxlen=40)
        self.browser_cache = OrderedDict()
        self.cloud_state = {'state': 'idle', 'error': None}
        self.cloud_thread = None
        self.previous_switch_interval = None
        self._original_start = ns['LIFECYCLE'].start
        self._original_stop = ns['LIFECYCLE'].stop

    def start_local_https(self):
        """Serve the same app over TLS on STUDIO_HTTPS_PORT with a self signed certificate.

        Browsers only expose getUserMedia in a secure context, so hand tracking from a
        phone or laptop on the LAN needs this. The certificate is generated once into
        the state directory; the browser asks to trust it the first time.
        """
        port = int(os.environ.get('STUDIO_HTTPS_PORT', '8443'))
        if port <= 0:
            return
        try:
            from cryptography import x509
            from cryptography.x509.oid import NameOID
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
            import datetime, ipaddress
            from werkzeug.serving import make_server
        except ImportError as exc:
            LOG.warning('Local HTTPS unavailable: %s', exc)
            return
        cert_path = self.state_dir / 'local_https.crt'
        key_path = self.state_dir / 'local_https.key'
        ca_cert_path = self.state_dir / 'studio_ca.crt'
        ca_key_path = self.state_dir / 'studio_ca.key'
        host = socket.gethostname().split('.')[0]
        try:
            lan_ip = self.ns['_local_ip']()
        except Exception:
            lan_ip = '127.0.0.1'
        try:
            self.state_dir.mkdir(parents=True, exist_ok=True)
            if not (cert_path.exists() and key_path.exists() and ca_cert_path.exists() and ca_key_path.exists()):
                # One local certificate authority, trusted once per device, signs the server
                # certificate; browsers then stop asking at every visit.
                ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
                ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'MTDI Studio Local CA'),
                                     x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'MTDI Studio')])
                now = datetime.datetime.now(datetime.timezone.utc)
                ca_cert = (x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name)
                           .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
                           .not_valid_before(now - datetime.timedelta(days=1)).not_valid_after(now + datetime.timedelta(days=3650))
                           .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
                           .add_extension(x509.KeyUsage(digital_signature=True, key_cert_sign=True, crl_sign=True, content_commitment=False,
                                                        key_encipherment=False, data_encipherment=False, key_agreement=False,
                                                        encipher_only=False, decipher_only=False), critical=True)
                           .sign(ca_key, hashes.SHA256()))
                ca_key_path.write_bytes(ca_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption()))
                ca_cert_path.write_bytes(ca_cert.public_bytes(serialization.Encoding.PEM))
                os.chmod(ca_key_path, 0o600)
                key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
                name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, host + '.local')])
                alt_names = [x509.DNSName(host + '.local'), x509.DNSName('studio.local'), x509.DNSName('localhost')]
                try:
                    alt_names.append(x509.IPAddress(ipaddress.ip_address(lan_ip)))
                except ValueError:
                    pass
                now = datetime.datetime.now(datetime.timezone.utc)
                cert = (x509.CertificateBuilder().subject_name(name).issuer_name(ca_name)
                        .public_key(key.public_key()).serial_number(x509.random_serial_number())
                        .not_valid_before(now - datetime.timedelta(days=1))
                        .not_valid_after(now + datetime.timedelta(days=825))
                        .add_extension(x509.SubjectAlternativeName(alt_names), critical=False)
                        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
                        .add_extension(x509.ExtendedKeyUsage([x509.ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
                        .sign(ca_key, hashes.SHA256()))
                key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM,
                                                       serialization.PrivateFormat.TraditionalOpenSSL,
                                                       serialization.NoEncryption()))
                cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
                os.chmod(key_path, 0o600)
            httpd = make_server('0.0.0.0', port, self.ns['server'], threaded=True,
                                ssl_context=(str(cert_path), str(key_path)))
        except Exception as exc:
            LOG.warning('Local HTTPS listener failed: %s', exc)
            return
        self.https_server = httpd
        threading.Thread(target=httpd.serve_forever, name='studio-https', daemon=True).start()
        print(f'Camera capable HTTPS https://{host}.local:{port} and https://{lan_ip}:{port} (self signed; accept the browser warning once)', flush=True)

    def start(self):
        with self.lock:
            if self.started:
                return
            self.stop_event.clear()
            self.telemetry.start()
            self.started = True
            if getattr(self, 'https_server', None) is None:
                self.https_server = None
                threading.Thread(target=self.start_local_https, name='studio-https-setup', daemon=True).start()
        # Headless operation: acquisition must not depend on a browser connecting.
        # A browser first paint still starts it earlier when one is present.
        def auto_start():
            if not self.stop_event.wait(5.0) and self.started and not self.deferred:
                try:
                    self.start_deferred()
                except Exception as exc:
                    LOG.warning('Automatic acquisition start failed: %s', exc)
        threading.Thread(target=auto_start, name='studio-autostart', daemon=True).start()

    def start_deferred(self):
        self.start()
        with self.lock:
            if self.deferred:
                return
            self.deferred = True
            # Shorter interpreter turns reduce contention with timed sensor reads.
            self.previous_switch_interval = sys.getswitchinterval()
            sys.setswitchinterval(min(self.previous_switch_interval, .001))
            self._original_start()
            if self.camera.saved_enabled:
                self.camera.set_enabled(True)
            self.cloud_thread = threading.Thread(target=self.restore_local, name='studio-state', daemon=True)
            self.cloud_thread.start()
            self.note('system', 'Acquisition started after browser first paint')

    def restore_local(self):
        try:
            offline = self.ns['INSTRUMENT_MODE']['mode'] == 'offline'
            restore = '_load_local_cloud_state' if (offline or os.environ.get('STUDIO_RESTORE_CLOUD', '1') == '0') else '_restore_notion_state'
            self.ns[restore]()
        except Exception as exc:
            LOG.warning('Saved state restoration unavailable: %s', exc)

    def stop(self, join_timeout=15):
        self.stop_event.set()
        self.camera.stop()
        self.audition.stop()
        self.telemetry.stop()
        https_server = getattr(self, 'https_server', None)
        if https_server is not None:
            try:
                https_server.shutdown()
            except Exception:
                pass
            self.https_server = None
        self._original_stop(join_timeout=join_timeout)
        if self.previous_switch_interval is not None:
            sys.setswitchinterval(self.previous_switch_interval)
            self.previous_switch_interval = None
        with self.lock:
            self.started = False
            self.deferred = False
            self.last_payload = None
            self.snapshot_at = 0

    def note(self, source, message):
        row = {'timestamp': time.time(), 'source': source, 'message': clean_text(message)}
        self.events.append(row)
        if self.deferred:
            self.ns['ARCHIVE'].put('event', {'t': row['timestamp'], 'source': source,
                                             'message': row['message'], 'severity': 'info'})

    def snapshot(self):
        with self.lock:
            now = time.monotonic()
            if self.last_payload is not None and now - self.snapshot_at < .2:
                return self.last_payload
            data = self.engine.snapshot()
            # Baseline auto relocks are engine decisions; surface each one as an event exactly once.
            relocks = getattr(self.engine, 'relock_log', None)
            while relocks:
                row = relocks.popleft()
                self.note('baseline', f"{row['channel']} baseline re-learned automatically: the quiet level sat "
                                      f"{row['offset']:.2f} {row['unit']} away from the lock for {row['stale_for']:.0f} s")
            self.sequence += 1
            data.update({'version': self.ns['APP_VERSION'], 'sequence': self.sequence,
                         'timestamp': time.time(), 'source': 'simulation' if self.ns['RUNTIME']['demo'] else 'hardware',
                         'startup': {'server': True, 'acquisition': self.deferred},
                         'camera': self.camera.snapshot(), 'telemetry': self.telemetry.snapshot(),
                         'audition': self.audition.snapshot(),
                         'mode': {'mode': self.ns['INSTRUMENT_MODE']['mode'], 'internet': self.ns['internet_reachable'](),
                                  'local_ai': self.ns['local_ai_status']()},
                         'events': sorted(data.get('events', []) + list(self.events), key=lambda e: e.get('timestamp') or 0)[-256:], 'cloud': dict(self.cloud_state),
                         'archive': {'queue': self.ns['ARCHIVE'].items.qsize(),
                                     'dropped': getattr(self.ns['ARCHIVE'], 'dropped_records', 0),
                                     'written': getattr(self.ns['ARCHIVE'], 'written_records', 0),
                                     'error': self.ns['ARCHIVE'].last_error}})
            self.last_payload = data
            compact = dict(data)
            compact['channels'] = {key: {k: v for k, v in channel.items() if k not in ('history', 'raw', 'metadata', 'corrected_raw')}
                                   for key, channel in data['channels'].items()}
            compact.pop('sequence', None)
            compact.pop('timestamp', None)
            if compact != self.stream_signature:
                self.stream_sequence += 1
                self.stream_signature = compact.copy()
                compact.update(sequence=self.stream_sequence, timestamp=time.time())
                if self.stream_packet is not None:
                    patch = stream_changes(self.stream_packet, compact)
                    self.stream_patch_base = self.stream_packet['sequence']
                    self.stream_patch_json = json.dumps(patch, separators=(',', ':'), allow_nan=False)
                self.stream_packet = compact
                self._stream_json = None
            self.snapshot_at = now
            return data

    @property
    def stream_json(self):
        with self.lock:
            if self._stream_json is None and self.stream_packet is not None:
                self._stream_json = json.dumps(self.stream_packet, separators=(',', ':'), allow_nan=False)
            return self._stream_json

    def stream_frame(self, previous=None, delta=False):
        with self.lock:
            self.snapshot()
            sequence = self.stream_sequence
            if previous == sequence:
                return None, sequence
            if delta and previous is not None and previous == self.stream_patch_base:
                event, payload = 'sensor_patch', self.stream_patch_json
            else:
                event, payload = 'sensor', self.stream_json
            return f'id: {sequence}\nevent: {event}\ndata: {payload}\n\n', sequence

    def control(self, data):
        action = data.get('action')
        if action == 'start':
            self.start_deferred()
        elif action == 'camera':
            if not isinstance(data.get('enabled'), bool):
                raise ValueError('Camera enabled must be a boolean')
            self.camera.set_enabled(data['enabled'])
        elif action == 'baseline':
            self.engine.baseline(channel=data.get('channel'), window=data.get('window'),
                                 freeze=data.get('freeze'), relock=bool(data.get('relock', False)))
            self.note('Baseline Lock', 'Baseline control updated')
        elif action == 'calibrate':
            self.engine.calibrate(**{key: data.get(key) for key in
                                     ('channel', 'raw_reference', 'known_reference', 'uncertainty', 'unit', 'method')})
            self.note('calibration', 'Calibration profile saved with history')
        elif action == 'reset_calibration':
            self.engine.reset_calibration(data.get('channel'))
            self.note('calibration', 'Calibration reset recorded')
        elif action == 'mode':
            mode = data.get('mode')
            if mode not in ('online', 'offline'):
                raise ValueError('Mode must be online or offline')
            self.ns['INSTRUMENT_MODE']['mode'] = mode
            try:
                self.state_dir.mkdir(parents=True, exist_ok=True)
                (self.state_dir / 'mode.json').write_text(json.dumps({'mode': mode}))
            except OSError:
                pass
            self.note('mode', 'Instrument mode set to ' + mode)
        elif action == 'elevenlabs_key':
            key = str(data.get('key', '')).strip()
            path = self.state_dir / 'elevenlabs.key'
            self.state_dir.mkdir(parents=True, exist_ok=True)
            if key:
                problem = self.ns.get('elevenlabs_key_check', lambda k: None)(key) if not self.ns.get('instrument_offline', lambda: False)() else None
                if problem:
                    raise ValueError(problem)
                path.write_text(key)
                os.chmod(path, 0o600)
                self.note('voice', 'ElevenLabs voice key saved and verified')
            elif path.exists():
                path.unlink()
                self.note('voice', 'ElevenLabs voice key removed')
        elif action == 'ai_engine':
            kid = re.sub(r'[^A-Za-z0-9_-]', '', str(data.get('id', '')))[:40]
            if kid:
                self.ns['nvtra_set_active'](kid)
                self.note('NVTRA', 'Engine set to ' + ('local model' if kid == 'local' else kid))
        elif action == 'elevenlabs_voice':
            voice = re.sub(r'[^A-Za-z0-9_-]', '', str(data.get('voice', '')))[:40]
            path = self.state_dir / 'elevenlabs.voice'
            self.state_dir.mkdir(parents=True, exist_ok=True)
            if voice:
                path.write_text(voice)
                self.ns['_elevenlabs_blocked'].pop(voice, None)
                self.note('voice', 'NVTRA voice set to ' + voice)
            elif path.exists():
                path.unlink()
        elif action == 'audition':
            self.audition.control(data)
            self.note('Field Audition', 'Listen mode control updated')
        elif action == 'marker':
            message = str(data.get('message', '')).strip()
            if not message or len(message) > 240:
                raise ValueError('Annotation must contain 1 to 240 characters')
            self.note('operator', message)
        elif action == 'cloud_report':
            if self.ns['INSTRUMENT_MODE']['mode'] == 'offline':
                raise ValueError('Offline mode: cloud upload is disabled. Use the local PDF download.')
            if not self.ns['_notion_setting']('NOTION_API_KEY') or not self.ns['_notion_setting']('NOTION_REPORT_PAGE_ID'):
                raise ValueError('Notion configuration is unavailable')
            if self.cloud_state['state'] == 'uploading':
                return dict(self.cloud_state)
            self.cloud_state = {'state': 'uploading', 'error': None}
            threading.Thread(target=self.upload_report, name='studio-cloud-report', daemon=True).start()
        else:
            raise ValueError('Unknown instrument action')
        self.snapshot_at = 0
        return self.snapshot()

    def upload_report(self):
        try:
            blocks = self.ns['_gather_report_blocks']()
            payload = self.ns['_pdf_bytes'](blocks)
            name = f'studio_{time.strftime("%Y%m%d_%H%M%S")}.pdf'
            if len(payload) <= 4_750_000:
                self.ns['_notion_upload_pdf'](payload, name)
            else:
                self.ns['_notion_upload_pdf_volumes'](blocks, name[:-4])
            self.cloud_state = {'state': 'complete', 'error': None}
        except Exception as exc:
            self.cloud_state = {'state': 'error', 'error': clean_text(exc)}


def batch_archive(ns):
    """Commit bounded batches while keeping producers independent of storage latency."""
    store = ns['ARCHIVE']
    store.dropped_records = 0
    store.written_records = 0
    original_open, original_write = store._open, store._write
    def open_with_raw():
        con = original_open()
        con.execute('CREATE TABLE IF NOT EXISTS raw_samples(id INTEGER PRIMARY KEY, session_id INTEGER, captured_at REAL, channel TEXT, payload_json TEXT NOT NULL)')
        con.execute('CREATE INDEX IF NOT EXISTS raw_samples_time ON raw_samples(captured_at)')
        con.commit()
        return con
    def write_with_raw(con, kind, payload):
        if kind == 'current':
            # Conducted Path samples live only in raw_samples; the base schema predates the clamp.
            pass
        else:
            original_write(con, kind, payload)
        if kind in ('c1', 'ch2f', 'ch3', 'current'):
            con.execute('INSERT INTO raw_samples(session_id,captured_at,channel,payload_json) VALUES(?,?,?,?)',
                        (store.session_id, payload.get('t', payload.get('completed_at', time.time())), kind,
                         json.dumps(payload, separators=(',', ':'), allow_nan=False)))
    store._open, store._write = open_with_raw, write_with_raw

    def put(kind, payload):
        try:
            store.items.put_nowait((kind, payload))
        except queue.Full:
            store.dropped_records += 1
            store.last_error = 'Archive queue full; record loss counted'
            if store.dropped_records == 1 or store.dropped_records % 100 == 0:
                LOG.error('%s: %s', store.last_error, store.dropped_records)

    def worker():
        con = None
        try:
            con = store._open()
            while not ns['ARCHIVE_STOP_EVENT'].is_set() or not store.items.empty():
                try:
                    batch = [store.items.get(timeout=.25)]
                except queue.Empty:
                    continue
                deadline = time.monotonic() + .05
                while len(batch) < 64:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    try:
                        batch.append(store.items.get(timeout=remaining))
                    except queue.Empty:
                        break
                try:
                    for kind, payload in batch:
                        store._write(con, kind, payload)
                    con.commit()
                    store.written_records += len(batch)
                    store.last_write = time.time()
                    store.last_error = None
                except Exception as exc:
                    con.rollback()
                    store.last_error = clean_text(exc)
                    for kind, payload in batch:
                        try:
                            store._write(con, kind, payload)
                            con.commit()
                            store.written_records += 1
                        except Exception:
                            con.rollback()
                            store.dropped_records += 1
                    LOG.exception('Archive batch failed; individual records retried')
                finally:
                    for _ in batch:
                        store.items.task_done()
        except Exception as exc:
            store.last_error = clean_text(exc)
            LOG.exception('Archive storage is unavailable')
        finally:
            if con is not None:
                try:
                    con.execute('UPDATE sessions SET ended_at=? WHERE id=?', (time.time(), store.session_id))
                    con.commit()
                finally:
                    con.close()
    store.put = put
    store.worker = worker


def memoize_figures(ns):
    for name in ('make_line_chart', 'fig_axis', 'fig_pie', 'fig_gauge', 'fig_bar', 'fig_2d_scatter',
                 'fig_2d_delta', 'fig_3d_surface', 'fig_3d_terrain', 'fig_3d_error_plane',
                 'fig_3d_dipolch2f', 'fig_c2_gauge', 'fig_c2_bullet', 'fig_c2_basebar',
                 'fig_c2_b_correlation', 'fig_c2_induction_proxy', 'fig_p1_overlay',
                 'fig_p1_normalized_overlay', 'fig_sweep3', 'fig_waterfall', 'fig_ch3_trend', 'fig_ch3_bands'):
        original = ns.get(name)
        if original is None:
            continue
        def decorate(fn):
            cache = OrderedDict()
            lock = threading.Lock()
            @functools.wraps(fn)
            def cached(*args, **kwargs):
                key = repr((args, sorted(kwargs.items())))
                with lock:
                    if key in cache:
                        return cache[key]
                result = fn(*args, **kwargs)
                with lock:
                    cache[key] = result
                    while len(cache) > 2:
                        cache.popitem(last=False)
                return result
            return cached
        ns[name] = decorate(original)


def install_reports(ns, runtime):
    """Keep the complete archive while reporting calibrated baseline deviations."""
    original = ns['_gather_report_blocks']

    def gather(row_cap=None):
        # The wrapper must pass the caller's row cap through, or the bound report
        # silently reverts to the module default and the ?rows= control does nothing.
        blocks = original() if row_cap is None else original(row_cap=row_cap)
        snapshot = runtime.engine.snapshot()
        # The live channel sections run from channel 1's (named by the project, so found by its source)
        # to the wireless survey. Matching 'CH1PROBE' found the archive appendix instead, and on an
        # empty archive nothing: the report crashed (StopIteration).
        first = next(i for i, b in enumerate(blocks) if b[0] == 'h' and b[1].endswith('(Source 1 @ bus 0x2C)'))
        last = next(i for i, b in enumerate(blocks) if b[0] == 'h' and b[1].startswith('WIRELESS SURVEY'))
        measured = [('h', 'MEASUREMENT DEFINITIONS'),
                    ('dim', 'Live values are deviations from Baseline Lock. Raw records below are diagnostic observations.'),
                    ('dim', 'Channel 2 probe voltage is relative until reference calibration. Confidence is evidence quality, not diagnostic probability.')]
        for channel in snapshot['channels'].values():
            value = channel['deviation']
            measured.extend([
                ('h', channel['label'].upper()),
                ('kv', 'State', channel['state']),
                ('kv', 'Baseline deviation', 'Unavailable' if value is None else f"{value:.3g} {channel['unit']}"),
                ('kv', 'Uncertainty', channel['uncertainty']),
                ('kv', 'Calibration timestamp', str(channel['calibration'].get('timestamp') or 'Never')),
                ('kv', 'Calibration method', channel['calibration'].get('method', 'None')),
                ('kv', 'Baseline state', 'Settling' if channel['baseline']['settling'] else 'Frozen' if channel['baseline']['frozen'] else 'Tracking'),
                ('kv', 'Transient Watch', channel['transient']['state']),
                ('kv', 'Last observation', str(channel['last_rx'] or 'Never')),
            ])
        fusion = snapshot['fusion']
        measured.extend([('h', 'Page 3'), ('kv', 'Condition', fusion['condition']),
                         ('kv', 'Evidence quality', f"{fusion['confidence']:.0f}%"),
                         ('line', fusion['interpretation'])])
        measured.extend(('line', str(evidence)) for evidence in fusion['evidence'])
        blocks[first:last] = measured
        host_start = next(i for i, b in enumerate(blocks) if b[0] == 'h' and b[1].startswith('HOST TELEMETRY'))
        host_end = next(i for i in range(host_start + 1, len(blocks)) if blocks[i][0] == 'page')
        host = runtime.telemetry.snapshot()
        host_rows = [('h', 'ACTUAL HOST TELEMETRY')]
        for label, key, unit in [('Host type', 'host_kind', ''), ('CPU load', 'cpu_usage', '%'),
                                 ('CPU temperature', 'cpu_temp', 'C'), ('Memory used', 'ram_used_mb', 'MB'),
                                 ('Disk used', 'disk_used_gb', 'GB'), ('Uptime', 'uptime_str', ''),
                                 ('LAN address', 'wifi_ip', '')]:
            value = host.get(key)
            host_rows.append(('kv', label, 'Unavailable' if value is None else f'{value} {unit}'.strip()))
        blocks[host_start:host_end] = host_rows
        for i, block in enumerate(blocks):
            if block[0] == 'kv' and block[1] == 'Instrument':
                blocks[i] = ('kv', 'Instrument', 'SRC1 + SRC2 + src3 Ultra; host identified in live telemetry')
            elif block[0] == 'h' and block[1] == 'HOST TELEMETRY   (host computer)':
                blocks[i] = ('h', 'ACTUAL HOST TELEMETRY')
            elif block[0] == 'h' and block[1].endswith((' SIGNAL ARCHIVE', ' PEAK ARCHIVE')):   # named by the project (S1-06)
                blocks[i] = ('h', block[1] + '   RAW DIAGNOSTICS')
        blocks = [(b[0], clean_text(b[1]), *b[2:]) if b[0] in ('band', 'h', 'sub', 'dim') and isinstance(b[1], str) else b for b in blocks]
        return blocks

    ns['_gather_report_blocks'] = gather

    # ── live dashboard ────────────────────────────────────────────────────────
    # The cloud page only ever received appended records, so it was a filing
    # cabinet rather than a dashboard: an empty paragraph, three PDFs and one chat
    # record, last edited two months ago. This keeps a single page CURRENT instead.
    #
    # It runs in its own thread because every sync is several HTTPS round trips to
    # Notion and snapshot() is on the path of every page refresh - a slow or
    # unreachable Notion must never hold up the instrument. Failures are logged and
    # retried on the next tick; nothing here can raise into acquisition.
    def dashboard_loop():
        while not ns['ARCHIVE_STOP_EVENT'].is_set():
            try:
                configured = (ns['_notion_setting']('NOTION_API_KEY')
                              and ns['_notion_setting']('NOTION_REPORT_PAGE_ID'))
                online = ns['INSTRUMENT_MODE']['mode'] != 'offline'
                # runtime.deferred is True once acquisition is running (the name is
                # historical). Publishing before that puts a red 'no channel is
                # reporting' on the page for the first ~40 s of every restart.
                if ns['RUNTIME'].get('demo'):
                    ns['ARCHIVE_STOP_EVENT'].wait(30.0)
                    continue
                if configured and online and runtime.started and runtime.deferred:
                    ns['_notion_dashboard_sync'](runtime.snapshot())
            except Exception:
                LOG.debug('Notion dashboard tick failed', exc_info=True)
            ns['ARCHIVE_STOP_EVENT'].wait(5.0)
    threading.Thread(target=dashboard_loop, name='notion-dashboard', daemon=True).start()


def install(ns):
    from .acquisition import install as install_acquisition
    from .selftest import run as run_selftest
    runtime = Runtime(ns)
    from . import common as _common
    _common.INSTRUMENT_RUNTIME = runtime  # lets earlier modules (NVTRA context) read the event log lazily
    serverless = bool(os.environ.get('STUDIO_SERVERLESS'))
    if not serverless:
        threading.Timer(20.0, lambda: ns['_local_whisper']()).start()   # warm the local Whisper model
    batch_archive(ns)
    install_acquisition(ns, runtime.engine)
    from .sdr import install as install_sdr
    install_sdr(ns)
    install_reports(ns, runtime)
    memoize_figures(ns)
    def system_loop():
        while not ns['STOP_EVENT'].is_set():
            snapshot = runtime.telemetry.snapshot()
            if snapshot.get('last_rx') is not None:
                with ns['sys_lock']:
                    ns['sys_data'].update(snapshot)
                ns['ARCHIVE'].put('system', {'t': time.time(), 'payload': snapshot})
            ns['STOP_EVENT'].wait(5)
    ns['sys_loop'] = system_loop
    ns['_system_snapshot'] = runtime.telemetry.collect
    def pi_grid():
        sd = runtime.telemetry.snapshot()
        h = ns['html']
        def value(key, unit=''):
            v = sd.get(key)
            if v is None:
                return 'Unavailable'
            return clean_text(v) + ((' ' + unit) if unit else '')
        entries = [('Host', value('host_kind'), value('host_model')),
                   ('CPU usage', value('cpu_usage', '%'), 'Operating system counter'),
                   ('CPU temperature', value('cpu_temp', '°C'), value('temperature_uncertainty')),
                   ('RAM used', value('ram_used_mb', 'MiB'), value('ram_total_mb', 'MiB total')),
                   ('Disk used', value('disk_used_gb', 'GiB'), value('disk_total_gb', 'GiB total')),
                   ('Uptime', value('uptime_str'), value('os')),
                   ('LAN address', value('lan_address'), value('hostname')),
                   ('Process memory', value('py_mem_mb', 'MiB'), 'Measured resident memory'),
                   ('Application', ns['APP_VERSION'], value('kernel')),
                   ('Archive', str(ns['ARCHIVE'].written_records) + ' records',
                    str(ns['ARCHIVE'].dropped_records) + ' lost records')]
        return [h.Div([h.Div(title, className='sys-name'), h.Div(val, className='sys-value'),
                       h.Div(note, className='sys-sub')], className='sys-card') for title, val, note in entries]
    ns['_pi_grid'] = pi_grid
    ns['LIFECYCLE'].start = runtime.start
    ns['LIFECYCLE'].stop = runtime.stop
    ns['run_self_test'] = lambda: run_selftest(ns, runtime)
    server = ns['server']
    server.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024
    server.config['SESSION_COOKIE_NAME'] = 'studio_session'

    def print_access(url):
        host = socket.gethostname().split('.')[0]
        address = ns['_local_ip']()
        print(f'MTDI Studio {ns["APP_VERSION"]}', flush=True)
        print(f'LAN http://{address}:{ns["RUNTIME"]["port"]}', flush=True)
        print(f'Hostname http://{host}.local:{ns["RUNTIME"]["port"]}', flush=True)
        try:
            import qrcode
            code = qrcode.QRCode(border=1, error_correction=qrcode.constants.ERROR_CORRECT_L)
            code.add_data(f'http://{address}:{ns["RUNTIME"]["port"]}')
            code.make(fit=True)
            print('Scan to open on a phone:', flush=True)
            code.print_ascii(invert=True)
        except Exception as exc:
            print(f'QR unavailable ({exc}); install with: python -m pip install qrcode', flush=True)
        def report_mdns():
            alias = os.environ.get('STUDIO_HOSTNAME', 'studio.local')
            try:
                resolved = socket.gethostbyname(alias)
                print(f'mDNS http://{alias}:{ns["RUNTIME"]["port"]} resolves to {resolved}', flush=True)
            except OSError:
                print(f'mDNS {alias} not resolvable from this host yet; the studio-alias service publishes it once the network is up', flush=True)
        threading.Thread(target=report_mdns, name='mdns_resolution', daemon=True).start()
        print(url, flush=True)
    ns['_print_access_link'] = print_access
    ns['_dashboard_url'] = lambda host, port: f'http://{("localhost" if host in {"127.0.0.1", "::1", "localhost"} else ns["_local_ip"]())}:{port}'

    @server.before_request
    def secure_redirect():
        """LAN browsers land on the secure listener automatically (camera and microphone
        need it). Localhost, the kiosk, health probes and the API stay on http."""
        if os.environ.get('STUDIO_FORCE_HTTPS', '1') in ('0', 'false', 'no'):
            return None
        if request.is_secure or getattr(runtime, 'https_server', None) is None:
            return None
        host = request.host.split(':')[0]
        if host in ('localhost', '127.0.0.1', '::1') or request.path.startswith('/api/') or request.path.startswith('/_dash'):
            return None
        port = int(os.environ.get('STUDIO_HTTPS_PORT', '8443'))
        return redirect(f'https://{host}:{port}{request.full_path.rstrip("?")}', code=302)

    @server.before_request
    def control_origin_and_session():
        if 'browser' not in session:
            session['browser'] = os.urandom(12).hex()
        if request.method == 'POST' and request.path.startswith('/api/'):
            origin = request.headers.get('Origin')
            if origin and urlsplit(origin).netloc != request.host:
                return {'error': 'Request origin does not match this instrument'}, 403
            if not request.is_json and request.path != '/api/transcribe':
                return {'error': 'JSON request body required'}, 415
        return None

    static_gzip_cache = {}
    mediapipe_dir = Path(__file__).resolve().parent.parent / 'public' / 'assets' / 'mediapipe'

    def precompress_mediapipe():
        import gzip as _gzip
        for path in sorted(mediapipe_dir.glob('*')):
            # .part files belong to a compression in progress (this or another instance on the
            # same tree) and can vanish between the glob and the stat
            if path.suffix in ('.gz', '.part') or path.name == 'README.md':
                continue
            try:
                if path.stat().st_size < 1024:
                    continue
            except OSError:
                continue
            gz = path.with_name(path.name + '.gz')
            if gz.exists() and gz.stat().st_mtime >= path.stat().st_mtime and gz.stat().st_size > 0:
                continue
            # Write to a temporary name and rename: a service restart mid-write used to leave a
            # 0-byte .gz that the server then served (Content-Length 0) for a year.
            tmp = gz.with_name(gz.name + '.part')
            try:
                with open(path, 'rb') as src, _gzip.open(tmp, 'wb', compresslevel=6) as dst:
                    while True:
                        chunk = src.read(1 << 20)
                        if not chunk:
                            break
                        dst.write(chunk)
                tmp.replace(gz)
            except OSError:
                tmp.unlink(missing_ok=True)
                gz.unlink(missing_ok=True)
    if mediapipe_dir.is_dir() and not serverless:
        threading.Thread(target=precompress_mediapipe, name='studio-gz', daemon=True).start()

    @server.after_request
    def compress_static(response):
        """Gzip the large component bundles once and serve them from memory.

        The base hook compresses JSON and HTML but skips streamed static files, so
        Plotly (4.8 MB) crossed a Wi Fi link uncompressed on every cold load.
        """
        if (request.path.startswith('/assets/parallax/') or request.path.startswith('/assets/airlock/') or request.path.startswith('/assets/lunar/')) and response.status_code in (200, 206):
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
            if request.path.endswith('.js') and response.status_code == 200 and 'gzip' in request.headers.get('Accept-Encoding', '').lower() and 'Content-Encoding' not in response.headers:
                # three.min.js is 650 KB raw; gzip it once and keep it in memory like the Dash bundles.
                key = request.path
                cached = static_gzip_cache.get(key)
                if cached is None:
                    import gzip as _gzip
                    response.direct_passthrough = False
                    cached = _gzip.compress(response.get_data(), compresslevel=6)
                    static_gzip_cache[key] = cached
                response.direct_passthrough = False
                response.set_data(cached)
                response.headers['Content-Encoding'] = 'gzip'
                response.headers['Vary'] = 'Accept-Encoding'
            return response
        if request.path.startswith('/assets/mediapipe/') and response.status_code == 200:
            # The hand model is ~12 MB; serve the precompressed copy and let the browser keep it.
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
            gz = mediapipe_dir / (request.path.rsplit('/', 1)[-1] + '.gz')
            if gz.exists() and gz.stat().st_size > 0 and 'gzip' in request.headers.get('Accept-Encoding', '').lower() and 'Content-Encoding' not in response.headers:
                from flask import send_file
                mimetype = response.mimetype
                response = send_file(str(gz), mimetype=mimetype, conditional=True, max_age=31536000)
                response.headers['Content-Encoding'] = 'gzip'
                response.headers['Vary'] = 'Accept-Encoding'
                response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
            return response
        if not request.path.startswith('/_dash-component-suites/') or response.status_code != 200:
            return response
        if 'gzip' not in request.headers.get('Accept-Encoding', '').lower() or 'Content-Encoding' in response.headers:
            return response
        key = request.full_path
        cached = static_gzip_cache.get(key)
        if cached is None:
            response.direct_passthrough = False
            raw = response.get_data()
            if len(raw) < 1024:
                return response
            import gzip as _gzip
            cached = _gzip.compress(raw, compresslevel=6)
            if len(static_gzip_cache) > 64:
                static_gzip_cache.clear()
            static_gzip_cache[key] = cached
        response.direct_passthrough = False
        response.set_data(cached)
        response.headers['Content-Encoding'] = 'gzip'
        response.headers['Vary'] = 'Accept-Encoding'
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        return response

    # A previous build answered repeated callbacks with HTTP 204 to save bandwidth. Dash
    # reports 204 as a failed callback and re queues it, so that hook was removed.

    # ── D4 analysis engine (MTDI 2.0) ────────────────────────────────────────
    @server.get('/api/d4')
    def d4_snapshot():
        try:
            return Response(json.dumps(runtime.d4.snapshot(force=request.args.get('force') == '1'), allow_nan=False),
                            mimetype='application/json', headers={'Cache-Control': 'no-store'})
        except Exception as exc:
            LOG.exception('D4 snapshot failed')
            return {'error': f'D4 engine failed: {exc}'}, 500

    @server.get('/api/d4/config')
    def d4_config_get():
        cfg, err = runtime.d4.config, runtime.d4.config_error
        return {'config': cfg, 'error': err, 'path': str(d4mod.config_path())}

    @server.post('/api/d4/config')
    def d4_config_post():
        """Accepts a full or partial i3_config.json (as exported by MATLAB) and stores it."""
        body = request.get_json(silent=True) or {}
        patch = body.get('config', body)
        try:
            path = runtime.d4.update_config(patch)
        except Exception as exc:
            return {'error': f'config rejected: {exc}'}, 400
        cfg, err = runtime.d4.config, runtime.d4.config_error
        if err:
            return {'error': err, 'config': cfg}, 400
        runtime.note('d4', f'i3_config.json updated ({", ".join(sorted(k for k in patch if k in cfg))})')
        return {'ok': True, 'path': path, 'config': cfg}

    @server.post('/api/d4/calibrate')
    def d4_calibrate():
        """Ellipsoid fit over the raw ch1probe ring (rotate the instrument first).
        With apply=true the offsets and soft iron matrix go into i3_config.json."""
        body = request.get_json(silent=True) or {}
        seconds = max(10, min(600, int(body.get('seconds', 120))))
        result, patch = runtime.d4.calibrate_ch1probe(seconds)
        if result is None:
            return {'error': patch}, 422
        applied = None
        if body.get('apply'):
            applied = runtime.d4.update_config(patch)
            runtime.note('d4', f"channel 1 calibration applied: offsets {result['offsets_val']} unit, quality {result['quality']} %")
        out = dict(result); out.pop('raw', None); out.pop('corrected', None)
        return {'calibration': out, 'export': patch, 'applied_to': applied,
                'plots': {'raw': result['raw'], 'corrected': result['corrected']},
                'simulated': bool(runtime.ns['RUNTIME'].get('demo'))}

    @server.post('/api/d4/burst')
    def d4_burst():
        body = request.get_json(silent=True) or {}
        n = max(860, min(8600, int(body.get('samples', 3440))))
        runtime.d4.request_burst(n, body.get('channel', 'ch2f') if body.get('channel') in ('ch2f', 'current') else 'ch2f')
        return {'ok': True, 'samples': n, 'note': 'the next Ch2 block is read contiguously at 860 SPS; the linefreq analysis refreshes within a few seconds'}

    @server.post('/api/d4/fingerprint')
    def d4_fingerprint():
        ref = runtime.d4.set_fingerprint_reference()
        runtime.note('d4', 'environmental fingerprint reference taken')
        return {'reference': ref}

    @server.post('/api/d4/validate')
    def d4_validate():
        """Validation statistics for a list of trial values and (predicted, actual) pairs."""
        body = request.get_json(silent=True) or {}
        try:
            values = [float(v) for v in body.get('values') or []]
            det = [(bool(p), bool(a)) for p, a in body.get('detections') or []]
        except (TypeError, ValueError) as exc:
            return {'error': f'bad input: {exc}'}, 400
        out = d4mod.validation_stats(values, det)
        if body.get('reference') is not None and values:
            ref = body['reference']
            refs = [float(v) for v in ref] if isinstance(ref, list) else [float(ref)] * len(values)
            out['error'] = d4mod.sensor_error(values, refs)
            m = out['measurements']
            out['uncertainty'] = d4mod.uncertainty(m['mean'], float(body.get('reference_error', 0.0)), m['std'],
                                                   float(body.get('noise_rms', 0.0)), float(body.get('calibration_error', 0.0)))
        return out

    @server.post('/api/d4/filters')
    def d4_filters():
        """Design a Butterworth/notch and compare filters on the live ch1 magnitude ring
        (or a supplied series)."""
        body = request.get_json(silent=True) or {}
        x = body.get('x'); fs = body.get('fs')
        if not x:
            rows = runtime.d4._ring('ch1', 60)
            if len(rows) < 32:
                return {'error': 'need 32 channel 1 samples'}, 422
            import numpy as np
            x = np.linalg.norm(np.array([r[1:4] for r in rows], dtype=float), axis=1).tolist()
            fs = (len(rows) - 1) / max(1e-6, rows[-1][0] - rows[0][0])
        try:
            cmp = d4mod.compare_filters(x, float(fs), cutoff_hz=body.get('cutoff_hz'))
            if body.get('apply') and 'butterworth' in cmp:
                f = dict(runtime.d4.config['filter']); f.update(cmp['butterworth'], fs=cmp['fs'], type='butterworth', kind='low')
                runtime.d4.update_config({'filter': f})
                cmp['applied'] = True
            if body.get('notch_hz'):
                b, a = d4mod.notch(float(body['notch_hz']), float(fs))
                cmp['notch'] = {'hz': float(body['notch_hz']), 'b': b, 'a': a}
            return cmp
        except Exception as exc:
            return {'error': str(exc)}, 400

    def _sdr_export():
        """The RTL-SDR slice, waterfall and last sweep, shaped for iv.sdr_analysis in MATLAB.

        Levels are dBFS, not dBm: the dongle has no absolute calibration, so the MATLAB
        side is told the unit explicitly and never presents these as field strengths.
        """
        snap = runtime.ns.get('sdr_snapshot')
        if snap is None:
            return {'present': False, 'note': 'CH 4 module not installed'}
        try:
            # Deliberately does NOT count as interest. Waking the receiver for every
            # dataset pull was measured to cost the sensors: the Ch2 block rate fell
            # from 1.49 to 0.98 per second and the longest contiguous block - which the
            # linefreq harmonic analysis needs 256 samples of - fragmented to 100. A dataset
            # is not worth degrading the measurement it describes, so the export reports
            # how old the receiver's last frame is and lets the reader judge.
            # Pass ?sdr=live to ask for a fresh burst instead.
            data = snap(include_trace=True, viewing=request.args.get('sdr') == 'live')
        except Exception as exc:                                  # pragma: no cover - defensive
            return {'present': False, 'note': f'snapshot failed: {exc}'}
        if not data.get('present'):
            return {'present': False, 'note': data.get('error') or data.get('status')}
        sweep = data.get('sweep') or {}
        return {
            'present': True, 'unit': 'dBFS', 'calibrated': False,
            'tuner': data.get('tuner'), 'serial': data.get('serial'),
            'trusted': bool(data.get('trusted')), 'untrusted_reason': data.get('untrusted_reason'),
            'centre_hz': data.get('centre_hz'), 'rate_hz': data.get('rate_hz'),
            'span_hz': data.get('span_hz'), 'bin_hz': (data.get('limits') or {}).get('bin_hz'),
            'gain_db': data.get('gain_db'), 'gain_mode': data.get('gain_mode'),
            'clip_fraction': data.get('clip_fraction'), 'dc_offset': data.get('dc_offset'),
            'rms_fullscale': data.get('rms_fullscale'),
            'bursts': data.get('bursts'), 'short_reads': data.get('short_reads'),
            'megabytes': data.get('megabytes'), 'age_s': data.get('age_s'),
            'streaming': bool(data.get('watched')),
            'freshness_note': ('live: a burst was taken while this dataset was built'
                               if data.get('watched') else
                               'the receiver dozes when nobody is watching it, so this frame may '
                               'be up to 30 s old; see age_s, or request the export with ?sdr=live'),
            'freqs': [round(f, 1) for f in (data.get('freqs') or [])],
            'levels_dbfs': [round(v, 2) for v in (data.get('levels_dbfs') or [])],
            'floor_dbfs': data.get('floor_dbfs'),
            'peaks': data.get('peaks') or [],
            'waterfall_freqs': [round(f, 1) for f in (data.get('waterfall_freqs') or [])],
            'waterfall': [[round(v, 2) for v in row] for row in (data.get('waterfall') or [])],
            'waterfall_times': [round(t, 3) for t in (data.get('waterfall_times') or [])],
            'sweep': {'start_hz': sweep.get('start_hz'), 'stop_hz': sweep.get('stop_hz'),
                      'freqs': [round(f, 1) for f in (sweep.get('freqs') or [])],
                      'levels_dbfs': [round(v, 2) for v in (sweep.get('levels_dbfs') or [])],
                      'floor_dbfs': sweep.get('floor_dbfs'), 'slices': sweep.get('slices'),
                      'measured_points': sweep.get('measured_points'),
                      'peaks': sweep.get('peaks') or [], 'finished': sweep.get('finished')} if sweep else None,
        }

    @server.get('/api/d4/export')
    def d4_export():
        """Pi → MATLAB dataset: the raw rings and recent channel histories as JSON."""
        seconds = max(5, min(600, int(request.args.get('seconds', 120))))
        rings = {k: runtime.d4._ring(k, seconds) for k in ('ch1_raw', 'ch1', 'ch2f')}
        hist = runtime.d4._histories()
        sp = runtime.d4._sweep3() or {}
        payload = {'exported_at': time.time(), 'seconds': seconds, 'simulated': bool(runtime.ns['RUNTIME'].get('demo')),
                   'ch1_raw': [[round(v, 4) for v in r] for r in rings['ch1_raw']],
                   'ch1': [[round(v, 4) for v in r] for r in rings['ch1']],
                   'ch2f_codes': [[round(r[0], 5), round(r[1], 2)] for r in rings['ch2f']],
                   'channel_history': {k: [[round(t, 3), v, n] for t, v, n in rows] for k, rows in hist.items()},
                   'sweep3': {'freqs': sp.get('freqs', []), 'levels': sp.get('levels', []), 'trusted': sp.get('trusted')},
                   'sdr': _sdr_export(),
                   'config': runtime.d4.config}
        return Response(json.dumps(payload, allow_nan=False), mimetype='application/json',
                        headers={'Content-Disposition': 'attachment; filename="i3_dataset.json"'})

    @server.route('/api/d4/reference', methods=['GET', 'POST', 'DELETE'])
    def d4_reference():
        """Source comparison database: record the current feature vector under a device name."""
        if request.method == 'GET':
            return {'references': runtime.d4.references, 'feature_names': d4mod.FEATURE_NAMES}
        body = request.get_json(silent=True) or {}
        name = re.sub(r'[^A-Za-z0-9 _.\-]', '', str(body.get('name') or ''))[:40].strip()
        if not name:
            return {'error': 'name required'}, 400
        if request.method == 'DELETE':
            runtime.d4.delete_reference(name)
            return {'ok': True}
        ref = runtime.d4.record_reference(name, str(body.get('note') or '')[:120])
        runtime.note('d4', f'reference profile recorded: {name}')
        return {'ok': True, 'reference': ref}

    @server.route('/api/d4/trials', methods=['GET', 'POST', 'DELETE'])
    def d4_trials():
        """Validation trials: distance, measured value, reference, detected/actual, source."""
        if request.method == 'GET':
            return {'trials': runtime.d4.trials, 'recommendations': d4mod.test_recommendations(runtime.d4.trials)}
        if request.method == 'DELETE':
            runtime.d4.clear_trials()
            return {'ok': True}
        body = request.get_json(silent=True) or {}
        try:
            trial = {'distance_cm': None if body.get('distance_cm') in (None, '') else float(body['distance_cm']),
                     'source': body.get('source'), 'value': None if body.get('value') in (None, '') else float(body['value']),
                     'reference': None if body.get('reference') in (None, '') else float(body['reference']),
                     'detected': bool(body.get('detected')), 'actual': bool(body.get('actual', True)), 'note': body.get('note')}
        except (TypeError, ValueError) as exc:
            return {'error': f'bad trial: {exc}'}, 400
        row = runtime.d4.add_trial(trial)
        return {'ok': True, 'trial': row, 'count': len(runtime.d4.trials)}

    @server.get('/api/d4/trials/stats')
    def d4_trial_stats():
        trials = runtime.d4.trials
        values = [t['value'] for t in trials if t.get('value') is not None]
        det = [(t['detected'], t['actual']) for t in trials]
        out = d4mod.validation_stats(values, det)
        refs = [(t['value'], t['reference']) for t in trials if t.get('value') is not None and t.get('reference') is not None]
        if refs:
            out['error'] = d4mod.sensor_error([v for v, _ in refs], [r for _, r in refs])
            m = out.get('measurements') or {}
            if m:
                out['uncertainty'] = d4mod.uncertainty(m['mean'], 0.0, m['std'], (runtime.d4.snapshot().get('noise_ch1') or {}).get('rms') or 0.0,
                                                       abs(out['error']['bias'] or 0.0))
        by_source = {}
        for t in trials:
            by_source.setdefault(t['source'], []).append(t)
        out['by_source'] = {k: d4mod.validation_stats([t['value'] for t in v if t.get('value') is not None], [(t['detected'], t['actual']) for t in v]) for k, v in by_source.items()}
        out['recommendations'] = d4mod.test_recommendations(trials)
        cfg = runtime.d4.config
        d3 = cfg.get('d3_reference') or {}
        det_stats = out.get('detection') or {}
        out['comparison'] = [
            {'metric': 'Detection rate', 'd3': d3.get('detection_rate_pct'), 'd4': det_stats.get('detection_rate_pct'), 'unit': '%'},
            {'metric': 'False positives', 'd3': d3.get('false_positive_rate_pct'), 'd4': det_stats.get('false_positive_rate_pct'), 'unit': '%'},
            {'metric': 'Calibration error', 'd3': d3.get('calibration_error_pct'), 'd4': (out.get('error') or {}).get('mean_pct_error'), 'unit': '%'},
            {'metric': 'MTDI accuracy', 'd3': d3.get('mtdi_accuracy_pct'), 'd4': det_stats.get('accuracy_pct'), 'unit': '%'},
            {'metric': 'Analysis time', 'd3': d3.get('analysis_time_s'), 'd4': runtime.d4.compute_seconds, 'unit': 's'},
        ]
        return out

    @server.route('/api/d4/repeatability', methods=['GET', 'POST'])
    def d4_repeatability():
        """GET the state of the current or last run; POST to start one.

        Body: {"channel": "ch1"|"ch2", "runs": 3-30, "window_s": 1-10}.
        The run takes runs x window_s of wall-clock time because each reading is a
        fresh window of live data, so this returns immediately and the caller polls.
        """
        if request.method == 'GET':
            return {'repeat_run': getattr(runtime.d4, 'repeat_run', None)}
        body = request.get_json(silent=True) or {}
        try:
            started = runtime.d4.start_repeatability(body.get('channel', 'ch1'),
                                                     body.get('runs', 10),
                                                     body.get('window_s', 3))
        except (TypeError, ValueError) as exc:
            return {'error': str(exc)}, 400
        return {'ok': True, 'started': started}

    @server.post('/api/d4/train')
    def d4_train():
        model, counts = runtime.d4.train_model()
        if model is None:
            return {'ok': False, 'note': 'Not trained: needs at least 2 sources with 5 labelled trials each', 'labelled': counts}
        runtime.note('d4', f"classifier trained on {model['n']} labelled trials")
        return {'ok': True, 'n': model['n'], 'classes': {k: v['n'] for k, v in model['classes'].items()}}

    @server.get('/api/d4/export.csv')
    def d4_export_csv():
        """Pi → MATLAB/Excel: a zip with one CSV per stream (HDF5 needs h5py, which this host does not have)."""
        import csv, io, zipfile
        seconds = max(5, min(600, int(request.args.get('seconds', 120))))
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
            for name, header in (('ch1_raw', ['t', 'x_val', 'y_val', 'z_val']), ('ch1', ['t', 'x_val', 'y_val', 'z_val']),
                                 ('ch2f', ['t', 'code']), ('current', ['t', 'code'])):
                sio = io.StringIO(); w = csv.writer(sio); w.writerow(header)
                for row in runtime.d4._ring(name, seconds):
                    w.writerow([round(v, 6) for v in row])
                z.writestr(f'{name}.csv', sio.getvalue())
            hist = runtime.d4._histories()
            sio = io.StringIO(); w = csv.writer(sio); w.writerow(['channel', 't_monotonic', 'deviation', 'noise'])
            for ch, rows in hist.items():
                for t, v, n in rows:
                    w.writerow([ch, round(t, 3), v, n])
            z.writestr('channel_history.csv', sio.getvalue())
            sp = runtime.d4._sweep3() or {}
            sio = io.StringIO(); w = csv.writer(sio); w.writerow(['freq_hz', 'level_dbm'])
            for f, l in zip(sp.get('freqs', []), sp.get('levels', [])):
                w.writerow([f, l])
            z.writestr('sweep3.csv', sio.getvalue())
            z.writestr('i3_config.json', json.dumps(runtime.d4.config, indent=2))
            z.writestr('validation_trials.json', json.dumps(runtime.d4.trials, indent=1))
        buf.seek(0)
        return Response(buf.read(), mimetype='application/zip', headers={'Content-Disposition': 'attachment; filename="i3_dataset.zip"'})

    @server.get('/api/d4/stream')
    def d4_stream():
        """Live link (27): server sent events with the D4 packet every 2 s. MATLAB polls
        /api/d4 (iv.live_link); browsers and Python can use this stream directly."""
        def gen():
            last = None
            for _ in range(1800):
                packet = runtime.d4.snapshot()
                if packet is not last:
                    yield 'data: ' + json.dumps(packet, allow_nan=False) + '\n\n'
                    last = packet
                time.sleep(2.0)
        return Response(gen(), mimetype='text/event-stream', headers={'Cache-Control': 'no-store', 'X-Accel-Buffering': 'no'})

    @server.get('/api/d4/report.pdf')
    def d4_report():
        """Automated technical report (24): matplotlib PdfPages, generated from the live packet,
        trials and stores. Nothing is written into it that was not measured."""
        try:
            from .d4report import build_report
            pdf = build_report(runtime)
        except Exception as exc:
            LOG.exception('D4 report failed')
            return {'error': f'report failed: {exc}'}, 500
        return Response(pdf, mimetype='application/pdf', headers={'Content-Disposition': 'attachment; filename="I3_D4_Validation_Report.pdf"'})

    @server.get('/api/instrument')
    def instrument():
        if request.args.get('compact') == '1':
            # Boot and reconnect use the same bounded packet as the live stream.
            runtime.snapshot()
            payload = runtime.stream_json or '{}'
        else:
            payload = json.dumps(runtime.snapshot(), allow_nan=False)
        return Response(payload, mimetype='application/json', headers={'Cache-Control': 'no-store'})

    def _clean_hand_profile(profile):
        if not isinstance(profile, dict) or len(profile) > 40:
            return None
        clean = {}
        for key, value in profile.items():
            if isinstance(key, str) and len(key) <= 24 and isinstance(value, (int, float, bool)) and (isinstance(value, bool) or abs(value) < 1e4):
                clean[key] = value
        return clean

    def _hand_store():
        """Named hand calibrations: {'profiles': {name: thresholds}, 'active': name|None}."""
        path = runtime.state_dir / 'hand_profiles.json'
        try:
            data = json.loads(path.read_text())
            if isinstance(data, dict) and isinstance(data.get('profiles'), dict):
                return path, data
        except (OSError, ValueError):
            pass
        data = {'profiles': {}, 'active': None}
        legacy = runtime.state_dir / 'hand_profile.json'
        try:
            old = json.loads(legacy.read_text()).get('profile')
            if isinstance(old, dict) and old.get('calibrated'):
                data['profiles']['Profile 1'] = old
                data['active'] = 'Profile 1'
        except (OSError, ValueError, AttributeError):
            pass
        return path, data

    def _hand_store_write(path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + '.part')
        tmp.write_text(json.dumps(data))
        tmp.replace(path)
        return {'profiles': data['profiles'], 'active': data['active'],
                'profile': data['profiles'].get(data['active']) if data['active'] else None}

    @server.route('/api/hand-profile', methods=['GET', 'POST'])
    def hand_profile():
        """Active hand calibration (thresholds only; never landmarks or images)."""
        path, data = _hand_store()
        if request.method == 'GET':
            active = data['profiles'].get(data['active']) if data['active'] else None
            return Response(json.dumps({'profile': active, 'active': data['active']}), mimetype='application/json', headers={'Cache-Control': 'no-store'})
        body = request.get_json(silent=True) or {}
        profile = body.get('profile')
        if profile is None:
            data['active'] = None
            return _hand_store_write(path, data)
        clean = _clean_hand_profile(profile)
        if clean is None:
            return {'error': 'profile must be a small JSON object'}, 400
        name = clean_text(str(body.get('name') or data['active'] or 'Profile 1'))[:40]
        data['profiles'][name] = clean
        data['active'] = name
        return _hand_store_write(path, data)

    @server.route('/api/hand-profiles', methods=['GET', 'POST'])
    def hand_profiles():
        """Named calibrations: list, save-as, rename, delete, select."""
        path, data = _hand_store()
        if request.method == 'GET':
            return Response(json.dumps({'profiles': data['profiles'], 'active': data['active']}), mimetype='application/json', headers={'Cache-Control': 'no-store'})
        body = request.get_json(silent=True) or {}
        op = body.get('op')
        name = clean_text(str(body.get('name') or ''))[:40]
        if op == 'save':
            clean = _clean_hand_profile(body.get('profile'))
            if clean is None or not name:
                return {'error': 'name and profile required'}, 400
            if len(data['profiles']) >= 24 and name not in data['profiles']:
                return {'error': 'too many profiles'}, 400
            data['profiles'][name] = clean
            data['active'] = name
        elif op == 'rename':
            to = clean_text(str(body.get('to') or ''))[:40]
            if name not in data['profiles'] or not to:
                return {'error': 'unknown profile'}, 404
            if to != name:
                data['profiles'][to] = data['profiles'].pop(name)
                if data['active'] == name:
                    data['active'] = to
        elif op == 'delete':
            if name not in data['profiles']:
                return {'error': 'unknown profile'}, 404
            del data['profiles'][name]
            if data['active'] == name:
                data['active'] = next(iter(data['profiles']), None)
        elif op == 'select':
            if name and name not in data['profiles']:
                return {'error': 'unknown profile'}, 404
            data['active'] = name or None
        else:
            return {'error': 'op must be save, rename, delete or select'}, 400
        return _hand_store_write(path, data)

    @server.get('/api/events')
    def events():
        delta = request.args.get('delta') == '1'

        # A serverless function cannot hold a stream open indefinitely (and may buffer
        # it). There the stream sends what it has for a few seconds and ends; the
        # browser's EventSource reconnects on its own after the retry delay.
        limit = float(os.environ.get('STUDIO_STREAM_SECONDS', '4' if os.environ.get('STUDIO_SERVERLESS') else '0'))

        def generate():
            previous = None
            started = time.monotonic()
            if limit:
                yield 'retry: 3000\n\n'
            while not runtime.stop_event.is_set():
                frame, previous = runtime.stream_frame(previous, delta)
                if frame is not None:
                    yield frame
                if limit and time.monotonic() - started >= limit:
                    return
                runtime.stop_event.wait(.2)
        return Response(generate(), mimetype='text/event-stream',
                        headers={'Cache-Control': 'no-store', 'X-Accel-Buffering': 'no'})

    def ingest_allowed():
        """Feeding the studio changes what every viewer sees, so a public deployment
        needs a shared token. Locally (no STUDIO_SERVERLESS) the token is optional."""
        token = os.environ.get('STUDIO_INGEST_TOKEN', '').strip()
        given = request.headers.get('Authorization', '').removeprefix('Bearer ').strip() or \
            request.headers.get('X-Studio-Token', '').strip()
        if token:
            import hmac
            return hmac.compare_digest(token, given)
        return not os.environ.get('STUDIO_SERVERLESS')

    def ingest_one(sample, default_source):
        source = str(sample.get('source') or default_source)[:40] or 'EXTERNAL'
        units = sample.get('unit') if isinstance(sample.get('unit'), dict) else {}
        done = []
        if 'ch1' in sample:
            ns['feed_ch1'](sample['ch1'], unit=units.get('ch1'), source=source, now=sample.get('t'))
            done.append('ch1')
        if 'ch2' in sample:
            ns['feed_ch2'](sample['ch2'], unit=units.get('ch2', 'mV RMS relative'), source=source, now=sample.get('t'))
            done.append('ch2')
        if 'ch3' in sample:
            sweep = sample['ch3']
            if not isinstance(sweep, dict):
                raise ValueError('ch3 must be {"x": [...], "y": [...]}')
            ns['feed_ch3'](sweep.get('x') or [], sweep.get('y') or [], source=source, now=sample.get('t'))
            done.append('ch3')
        return done

    @server.post('/api/ingest')
    def ingest():
        """Drive the studio's channels from any program.

        Body: {"ch1": [x, y, z] or n, "ch2": n, "ch3": {"x": [...], "y": [...]}, "source": "label", "t": unix}
        or {"samples": [ ...the same objects... ]}. Auth: Authorization: Bearer $STUDIO_INGEST_TOKEN."""
        if not ingest_allowed():
            return {'ok': False, 'error': 'ingest needs Authorization: Bearer <STUDIO_INGEST_TOKEN>; '
                                          'set that variable on the server to enable it'}, 403
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return {'ok': False, 'error': 'JSON object required'}, 400
        samples = body.get('samples') if isinstance(body.get('samples'), list) else [body]
        if len(samples) > 2000:
            return {'ok': False, 'error': 'at most 2000 samples per request'}, 413
        updated = 0
        try:
            for sample in samples:
                if not isinstance(sample, dict):
                    raise ValueError('each sample must be an object')
                updated += len(ingest_one(sample, body.get('source', 'EXTERNAL')))
        except (TypeError, ValueError, KeyError) as exc:
            return {'ok': False, 'error': clean_text(exc), 'accepted': updated}, 400
        if not runtime.deferred:
            try:
                runtime.start_deferred()
            except Exception:
                LOG.debug('deferred start after ingest failed', exc_info=True)
        return {'ok': True, 'accepted': updated}

    @server.post('/api/control')
    def control():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return {'error': 'JSON object required'}, 400
        try:
            return runtime.control(data)
        except (ValueError, TypeError, KeyError) as exc:
            return {'error': clean_text(exc)}, 400
        except RuntimeError as exc:
            # Hardware absent or busy: an expected condition, reported without a traceback.
            return {'error': clean_text(exc)}, 409
        except Exception as exc:
            LOG.exception('Instrument control failed')
            return {'error': clean_text(exc)}, 503

    @server.get('/api/camera/frame')
    def frame():
        data = runtime.camera.jpeg()
        if not data:
            return {'state': runtime.camera.snapshot().get('state'), 'error': 'Camera frame unavailable'}, 503
        return Response(data, mimetype='image/jpeg', headers={'Cache-Control': 'no-store'})

    @server.get('/api/tracking')
    def tracking():
        def generate():
            previous = None
            while not runtime.stop_event.is_set():
                status = runtime.camera.snapshot()
                item = status.get('tracking', {})
                payload = json.dumps(item, separators=(',', ':'), allow_nan=False)
                if payload != previous:
                    yield 'data: ' + payload + '\n\n'
                    previous = payload
                if not status.get('enabled'):
                    return
                runtime.stop_event.wait(1 / 30)
        return Response(generate(), mimetype='text/event-stream', headers={'Cache-Control': 'no-store'})

    @server.get('/api/camera/stream')
    def camera_stream():
        def generate():
            previous = None
            while not runtime.stop_event.is_set():
                status = runtime.camera.snapshot()
                if not status.get('enabled') or status.get('state') not in ('connected', 'initialising'):
                    return
                data = runtime.camera.jpeg()
                stamp = status.get('last_frame')
                if data and stamp != previous:
                    yield b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: ' + str(len(data)).encode() + b'\r\n\r\n' + data + b'\r\n'
                    previous = stamp
                runtime.stop_event.wait(.1)
        return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame', headers={'Cache-Control': 'no-store'})

    consent_path = runtime.state_dir / 'camera_consent.json'

    def camera_consent():
        # None until the operator answers once; then that answer holds until they change it.
        try:
            share = json.loads(consent_path.read_text()).get('share')
            return share if isinstance(share, bool) else None
        except (OSError, ValueError, AttributeError):
            return None

    @server.get('/api/camera-consent')
    def camera_consent_get():
        return {'share': camera_consent()}

    @server.post('/api/camera-consent')
    def camera_consent_set():
        body = request.get_json(silent=True)
        share = body.get('share') if isinstance(body, dict) else 'invalid'
        if share is not None and not isinstance(share, bool):
            return {'error': 'share must be true, false or null'}, 400
        runtime.state_dir.mkdir(parents=True, exist_ok=True)
        if share is None:
            consent_path.unlink(missing_ok=True)
        else:
            consent_path.write_text(json.dumps({'share': share}))
        return {'share': camera_consent()}

    @server.get('/api/system-check')
    def system_check():
        # The studio's view of `mtdi doctor`, `mtdi capabilities` and `mtdi registry` (P-01): run on request.
        from mtdi import capabilities, doctor, registry
        host = capabilities.detect_host()
        targets = capabilities.load_targets()
        picks = capabilities.matrix(profiles=['hybrid'], targets={**targets, 'host': host})
        snap = registry.snapshot()
        return {'doctor': [{'name': n, 'status': st, 'detail': d} for n, st, d in doctor.run(quick=True)],
                'host': {k: host.get(k) for k in ('name', 'memory_mb', 'languages')},
                'targets': [{'target': t, 'runtime': row['hybrid'][0], 'why': row['hybrid'][1]} for t, row in picks.items()],
                'integrations': [{k: r[k] for k in ('id', 'provider', 'area', 'status', 'cost')} for r in snap['integrations']],
                'modules': [{'module': m['module'], 'ok': m['ok']} for m in snap['modules']]}

    @server.post('/api/agent')
    def agent():
        data = request.get_json(silent=True) or {}
        try:
            image = data.get('image')
            if camera_consent() is not True:
                image = None   # no frame leaves the studio without the operator's yes
            elif isinstance(image, str) and image.startswith('data:image/jpeg;base64,'):
                image = image.split(',', 1)[1]
            elif not isinstance(image, str) or len(image) > 2_500_000:
                image = None
            return runtime.ns['nvtra_agent'](data.get('text'), image_b64=image)
        except (ValueError, TypeError) as exc:
            return {'error': clean_text(exc)}, 400
        except Exception as exc:
            LOG.exception('Agent request failed')
            return {'error': clean_text(exc)}, 503

    @server.get('/api/sdr')
    def sdr_state():
        trace = request.args.get('trace', '1') not in ('0', 'false', 'no')
        return runtime.ns['sdr_snapshot'](include_trace=trace, viewing=True)

    @server.post('/api/sdr')
    def sdr_control():
        data = request.get_json(silent=True) or {}
        sweep = data.get('sweep')
        if sweep is not None:
            if not (isinstance(sweep, (list, tuple)) and len(sweep) == 2):
                return {'error': 'sweep must be [start_hz, stop_hz]'}, 400
        try:
            return runtime.ns['sdr_command'](centre_hz=data.get('centre_hz'), gain=data.get('gain'),
                                             sweep=sweep, cancel_sweep=bool(data.get('cancel_sweep')))
        except (ValueError, TypeError) as exc:
            return {'error': clean_text(exc)}, 400

    @server.post('/api/speak')
    def speak():
        data = request.get_json(silent=True) or {}
        audio, reason = runtime.ns['elevenlabs_speech'](str(data.get('text', ''))[:600], voice=str(data.get('voice') or '')[:40] or None)
        if audio is None:
            return {'error': reason}, 404
        return Response(audio, mimetype='audio/mpeg', headers={'Cache-Control': 'no-store'})

    @server.post('/api/transcribe')
    def transcribe():
        data = request.get_data(cache=False)
        if len(data) > 8_000_000:
            return {'error': 'audio too long'}, 413
        text_out, engine = runtime.ns['transcribe_audio'](data, request.headers.get('Content-Type', 'audio/wav').split(';')[0] or 'audio/wav')
        if text_out is None:
            return {'error': engine}, 503
        return {'text': text_out, 'engine': engine}

    @server.get('/api/transcribe')
    def transcribe_status():
        st = runtime.ns['local_whisper_status']()
        if not st['available'] and not st['loading'] and not st['error']:
            runtime.ns['_local_whisper']()   # start loading on first interest
            st = runtime.ns['local_whisper_status']()
        keys = [p for p in ('groq', 'gemini', 'openai') if runtime.ns['_credential_for'](p)]
        return {'local': st, 'cloud': keys, 'offline': runtime.ns['instrument_offline']()}

    @server.get('/api/engines')
    def engines():
        return {'engines': runtime.ns['nvtra_engines'](), 'offline': runtime.ns['instrument_offline']()}

    @server.get('/api/voices')
    def voices():
        return {'voices': runtime.ns['elevenlabs_voices'](request.args.get('refresh') == '1'), 'active': runtime.ns['elevenlabs_voice_id']()}

    @server.get('/api/ca.crt')
    def local_ca():
        """The local certificate authority, for one time trust on a phone or laptop."""
        path = runtime.state_dir / 'studio_ca.crt'
        if not path.exists():
            return {'error': 'Local certificate authority not generated yet'}, 404
        return Response(path.read_bytes(), mimetype='application/x-x509-ca-cert',
                        headers={'Content-Disposition': 'attachment; filename="mtdi-studio-ca.crt"'})

    @server.get('/api/audition/<key>.wav')
    def audition_stream(key):
        if key not in runtime.audition.sources:
            return {'error': 'Unknown audio source'}, 404
        source = runtime.audition.sources[key]
        if not source.snapshot().get('enabled'):
            return {'error': 'Audio source is not running'}, 409
        return Response(runtime.audition.stream(key, runtime.stop_event), mimetype='audio/wav',
                        headers={'Cache-Control': 'no-store', 'X-Accel-Buffering': 'no'})

    @server.get('/api/export/<kind>.<fmt>')
    def export_channels(kind, fmt):
        """Session export: recent channel histories as JSON or CSV."""
        if kind != 'session' or fmt not in ('json', 'csv'):
            return {'error': 'Unknown export'}, 404
        data = runtime.engine.snapshot()
        rows = []
        for channel, item in data['channels'].items():
            for point in item.get('history', []):
                rows.append({'channel': channel, 'monotonic': point['t'], 'deviation': point['deviation'], 'unit': item['unit']})
        rows.sort(key=lambda row: row['monotonic'])
        stamp = time.strftime('%Y%m%d_%H%M%S')
        if fmt == 'json':
            payload = json.dumps({'version': ns['APP_VERSION'], 'exported_at': time.time(), 'events': data['events'],
                                  'calibration': {key: value['calibration'] for key, value in data['channels'].items()},
                                  'samples': rows}, allow_nan=False)
            return Response(payload, mimetype='application/json',
                            headers={'Content-Disposition': f'attachment; filename="studio_session_{stamp}.json"'})
        lines = ['channel,monotonic_s,deviation,unit'] + [f"{r['channel']},{r['monotonic']:.3f},{r['deviation']},{r['unit']}" for r in rows]
        return Response('\n'.join(lines) + '\n', mimetype='text/csv',
                        headers={'Content-Disposition': f'attachment; filename="studio_session_{stamp}.csv"'})

    @server.get('/api/history')
    def history():
        """Downsampled archive history for the last N minutes (default 10, max 24 h).

        Longer than the ~30 s engine histories: read from the SQLite archive, bucketed into
        `points` slots with mean/min/max per bucket, plus CH3 sweep summaries and events.
        """
        try:
            minutes = float(request.args.get('minutes', 10))
            points = int(request.args.get('points', 240))
        except (TypeError, ValueError):
            return {'error': 'minutes and points must be numbers'}, 400
        data = ns['ARCHIVE'].history(minutes, points)
        data['live_events'] = [row for row in runtime.events if row['timestamp'] >= data['since']]
        data['source'] = 'simulation' if ns['RUNTIME']['demo'] else 'hardware'
        return Response(json.dumps(data, allow_nan=False), mimetype='application/json',
                        headers={'Cache-Control': 'no-store'})

    @server.post('/api/log')
    def log_event():
        """Interface-side events (gesture mode changes, judge mode, calibration) join the
        timestamped event log so they line up with sensor events in the export."""
        body = request.get_json(silent=True) or {}
        source = clean_text(str(body.get('source', 'interface')))[:32] or 'interface'
        message = clean_text(str(body.get('message', '')))[:240]
        if not message:
            return {'error': 'message required'}, 400
        runtime.note(source, message)
        return {'logged': True, 'events': len(runtime.events)}

    @server.get('/api/export/events.<fmt>')
    def export_events(fmt):
        """Timestamped event log (alerts, relocks, gesture/judge-mode triggers) as CSV or JSON."""
        if fmt not in ('csv', 'json'):
            return {'error': 'Unknown export'}, 404
        try:
            minutes = float(request.args.get('minutes', 24 * 60))
        except (TypeError, ValueError):
            minutes = 24 * 60
        archived = ns['ARCHIVE'].history(minutes, 10).get('events', [])
        seen = set()
        rows = []
        for row in archived:
            key = (round(row['t'], 3), row['message'])
            seen.add(key)
            rows.append({'timestamp': row['t'], 'severity': row['severity'], 'source': row['source'], 'message': row['message']})
        for row in runtime.events:
            key = (round(row['timestamp'], 3), row['message'])
            if key not in seen:
                rows.append({'timestamp': row['timestamp'], 'severity': 'info', 'source': row['source'], 'message': row['message']})
        rows.sort(key=lambda row: row['timestamp'])
        stamp = time.strftime('%Y%m%d_%H%M%S')
        if fmt == 'json':
            return Response(json.dumps({'version': ns['APP_VERSION'], 'exported_at': time.time(), 'events': rows}, allow_nan=False),
                            mimetype='application/json',
                            headers={'Content-Disposition': f'attachment; filename="studio_events_{stamp}.json"'})

        def cell(value):
            text = str(value).replace('"', '""')
            return f'"{text}"' if any(ch in text for ch in ',"\n') else text
        lines = ['timestamp,iso_time,severity,source,message']
        for row in rows:
            iso = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(row['timestamp']))
            lines.append(','.join([f"{row['timestamp']:.3f}", iso, cell(row['severity']), cell(row['source']), cell(row['message'])]))
        return Response('\n'.join(lines) + '\n', mimetype='text/csv',
                        headers={'Content-Disposition': f'attachment; filename="studio_events_{stamp}.csv"'})

    @server.post('/api/performance')
    def performance():
        body = request.get_json(silent=True) or {}
        allowed = ('first_meaningful_paint_ms', 'fps', 'frame_work_p95_ms', 'long_tasks', 'samples_dropped',
                   'refresh_hz', 'dpr', 'viewport_w', 'viewport_h')
        row = {'timestamp': time.time()}
        for key in allowed:
            value = body.get(key)
            if isinstance(value, (int, float)) and math.isfinite(value) and value >= 0:
                row[key] = value
        agent = body.get('agent')
        if isinstance(agent, str) and agent.strip():
            # Browser identity travels with the frame numbers: a 60 fps report from Safari and a
            # 120 fps report from Chromium on the same Mac are a browser difference, not a site one.
            row['agent'] = clean_text(agent)[:160]
        runtime.metrics.append(row)
        return {'stored': True}

    @server.get('/api/performance')
    def performance_history():
        return {'measurements': list(runtime.metrics), 'host': runtime.telemetry.snapshot()}

    @server.get('/api/diagnostics')
    def diagnostics():
        return {'events': list(runtime.events), 'archive': runtime.snapshot()['archive'],
                'calibration': runtime.engine.snapshot()['channels'], 'camera': runtime.camera.snapshot(),
                'nvtra_context': ns['_nvtra_context']()}

    def local_pdf():
        # ?rows=N raises or lowers the per-table cap for one download. The ceiling is
        # not politeness: the archive on this host holds 12.6 million ch1probe rows,
        # and an unbounded report would take the service down rather than return a
        # file. A caller who genuinely wants everything should take the JSON export
        # or the archive database.
        cap_default = ns['REPORT_ROW_CAP']
        cap_max = ns['REPORT_ROW_CAP_MAX']
        try:
            row_cap = int(request.args.get('rows', cap_default))
        except (TypeError, ValueError):
            return Response('rows must be a whole number', status=400, mimetype='text/plain')
        if row_cap < 1 or row_cap > cap_max:
            return Response(f'rows must be between 1 and {cap_max}', status=400,
                            mimetype='text/plain')
        try:
            started = time.monotonic()
            blocks = ns['_gather_report_blocks'](row_cap=row_cap)
            payload = ns['_pdf_bytes'](blocks)
            LOG.info('PDF report: %d blocks, %.1f kB, %.1f s (row cap %d)',
                     len(blocks), len(payload) / 1024, time.monotonic() - started, row_cap)
            return Response(payload, mimetype='application/pdf', headers={
                'Content-Disposition': 'attachment; filename="studio_report.pdf"', 'Cache-Control': 'no-store'})
        except Exception as exc:
            LOG.exception('Local PDF generation failed')
            return Response(clean_text(exc), status=503, mimetype='text/plain')
    server.view_functions['download_complete_pdf'] = local_pdf
    return runtime
