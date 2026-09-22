"""Atskiras mokymo procesas su laiko ir atminties ribomis."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path
import joblib
import psutil
from .models import create_model

def worker(request_path):
    req = joblib.load(request_path)
    model = create_model(req['kind'], req['params'], req['seed'], req['threads'])
    kwargs = {} if req['weights'] is None else {'model__sample_weight': req['weights']}
    start = time.perf_counter()
    model.fit(req['X'], req['y'], **kwargs)
    joblib.dump(model, req['destination'], compress=3)
    Path(str(req['destination']) + '.json').write_text(json.dumps({'fit_seconds': time.perf_counter()-start}), encoding='utf-8')

def fit_limited(kind, params, X, y, destination, cfg, seed=42, weights=None, deadline=None):
    destination = Path(destination)
    request = destination.with_suffix('.request')
    log_path = destination.with_suffix('.log')
    joblib.dump(dict(kind=kind, params=params, X=X, y=y, destination=destination,
                     threads=cfg['threads'], seed=seed, weights=weights), request)
    env = dict(os.environ, OMP_NUM_THREADS=str(cfg['threads']), OPENBLAS_NUM_THREADS=str(cfg['threads']),
               MKL_NUM_THREADS=str(cfg['threads']), PYTHONIOENCODING='utf-8')
    started, peak, status = time.monotonic(), 0, 'complete'
    with log_path.open('w', encoding='utf-8') as log:
        process = subprocess.Popen([sys.executable, '-m', 'airquality.train', str(request)],
                                   stdout=log, stderr=log, env=env)
        while process.poll() is None:
            try:
                proc = psutil.Process(process.pid)
                rss = proc.memory_info().rss + sum(p.memory_info().rss for p in proc.children(recursive=True))
                peak = max(peak, rss)
            except psutil.Error:
                pass
            if time.monotonic()-started > cfg['fit_timeout_seconds']:
                status = 'fit_timeout'
            if deadline is not None and time.monotonic() > deadline:
                status = 'total_timeout'
            if peak > cfg['memory_limit_gb'] * 1024**3:
                status = 'memory_limit'
            if status != 'complete':
                process.kill()
                process.wait()
                break
            time.sleep(.1)
    request.unlink(missing_ok=True)
    if process.returncode and status == 'complete':
        status = 'error'
    result = dict(status=status, wall_seconds=time.monotonic()-started, peak_rss_mb=peak/1024**2)
    if status == 'complete':
        result.update(json.loads(Path(str(destination)+'.json').read_text()))
        result['model_bytes'] = destination.stat().st_size
        return joblib.load(destination), result
    result['log'] = str(log_path)
    return None, result

if __name__ == '__main__':
    worker(sys.argv[1])
