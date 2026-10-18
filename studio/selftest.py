"""Portable software checks that never claim physical sensor validation."""
import json
import math
from pathlib import Path
import tempfile
import threading
import time
from .analysis import AnalysisEngine


def run(ns, runtime):
    failures = []
    def check(condition, label):
        if not condition:
            failures.append(label)
    with tempfile.TemporaryDirectory() as directory:
        engine = AnalysisEngine(Path(directory) / 'calibration.json', window=2)
        for i in range(120):
            t = 1 + i * .025
            engine.ingest('ch1', 0, timestamp=t, vector=[0, 0, 0], metadata={'monotonic': t})
        engine.ingest('ch1', 13, timestamp=5, vector=[3, 4, 12], metadata={'monotonic': 5})
        data = engine.snapshot(now=5)
        check(math.isclose(data['fusion']['axial']['magnitude'], 13), 'Triaxial magnitude')
        check(data['fusion']['axial']['unit'] == 'unit', 'Channel 1 unit')
        check(data['channels']['ch2']['deviation'] is None, 'Offline channels have no numeric reading')
        for i in range(120):
            t = 1 + i * .12
            engine.ingest('current', 0.5, timestamp=t, unit='A', metadata={'monotonic': t})
        engine.ingest('current', 4.5, timestamp=16, unit='A', metadata={'monotonic': 16})
        cond = engine.snapshot(now=16)
        from .audition import PcmProcessor, wav_header
        import struct as _struct
        processor = PcmProcessor()
        processor.gain = 4.0
        encoded, level, peak, clipped = processor.process(_struct.pack('<%dh' % 64, *([12000, -12000] * 32)))
        check(len(encoded) == 128 and clipped and max(abs(v) for v in _struct.unpack('<64h', encoded)) <= 32767, 'Audio soft limiter bounds output')
        check(wav_header()[:4] == b'RIFF' and len(wav_header()) == 44, 'Streaming WAV header')
        engine.calibrate('ch2', [0, 10], [0, 100], 2, 'V/m', 'Software fixture')
        restored = AnalysisEngine(Path(directory) / 'calibration.json')
        check(restored.calibrations.get('ch2')['scale'] == 10, 'Calibration persistence')
        check(engine.snapshot(now=100)['channels']['ch1']['state'] == 'stale', 'Stale channel state')
        json.dumps(data, allow_nan=False)
    for raw in ('100000 -90.0\n200000 -88.5\n300000 -91.0\n',
                'scan 100000 300000 3 3\n100000 -90.0 0\n200000 -88.5 0\n300000 -91.0 0\nch>'):
        f, levels = ns['parse_text_scan'](raw)
        ns['validate_sweep'](f, levels, 100000, 300000, 3)
    try:
        ns['validate_sweep']([100000, 200000], [-90, -89], 100000, 300000, 3)
        failures.append('Partial CH 3 sweep was accepted')
    except ns['Src3ProtocolError']:
        check(True, 'Partial CH 3 rejection')
    client = ns['server'].test_client()
    for route in ('/', '/page-1', '/page-2', '/mtdi', '/settings', '/page-3', '/api/instrument', '/api/diagnostics'):
        response = client.get(route)
        check(response.status_code == 200, f'Route {route}')
    for route, builder in ns['PAGES'].items():
        try:
            ids = list(ns['_component_ids'](builder()))
            check(len(ids) == len(set(ids)), f'Unique component identities at {route}')
        except Exception as exc:
            failures.append(f'Page {route}: {exc}')
    check(client.post('/api/control', json={'action': 'unknown'}).status_code == 400, 'Invalid controls rejected')
    check(client.post('/api/control', json={'action': 'baseline', 'window': 0}).status_code == 400, 'Invalid baseline rejected')
    check(client.post('/api/control', json={'action': 'camera', 'enabled': 'false'}).status_code == 400, 'Camera boolean validation')
    check(client.post('/api/control', json={'action': 'audition', 'source': 'nothing'}).status_code == 400, 'Unknown audio source rejected')
    check(client.post('/api/control', json={'action': 'mode', 'mode': 'sideways'}).status_code == 400, 'Invalid mode rejected')
    check(client.post('/api/control', json={'action': 'mode', 'mode': 'offline'}).status_code == 200 and ns['INSTRUMENT_MODE']['mode'] == 'offline', 'Offline mode applies')
    client.post('/api/control', json={'action': 'mode', 'mode': 'online'})
    check(client.get('/api/audition/coil.wav').status_code == 409, 'Audio stream refuses when the source is stopped')
    check(client.get('/api/export/session.csv').status_code == 200, 'Session CSV export')
    check(client.get('/api/export/session.json').status_code == 200, 'Session JSON export')
    check(not runtime.deferred, 'Checks do not start hardware workers')
    result = {'passed': not failures, 'version': ns['APP_VERSION'],
              'scope': 'Software checks only; no physical sensor verification', 'failures': failures}
    print(json.dumps(result, indent=2))
    return int(bool(failures))
