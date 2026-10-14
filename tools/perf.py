# Steady-state cook cost of a component, averaged over N frames.
# Loaded into a text DAT so run() can call back into it (see tests.py):
#   m = op('/project1/td_components_test/perf').module
#   m.perf_start('/project1/flipbook', 60)   ... N frames later ...   print(m.perf_result('/project1/flipbook'))

def perf_start(path, frames=60):
    c = op(path)
    c.store('_perf', {'n': 0, 'frames': frames, 'cpu': {}, 'gpu': {}})
    run("op(%r).module.perf_tick(%r)" % (me.path, path), delayFrames=1)


def _ops(c):
    return [o for o in c.findChildren() if not o.isCOMP or o.isObject]


def perf_tick(path):
    c = op(path)
    st = c.fetch('_perf')
    # pull the outputs, as a viewer or a downstream op would
    for o in c.findChildren(depth=1, type=outTOP):
        o.cook()
    for o in _ops(c):
        if getattr(o, 'cookAbsFrame', -1) < absTime.frame - 1:   # only ops that cooked this or last frame
            continue
        st['cpu'][o.path] = st['cpu'].get(o.path, 0.0) + o.cpuCookTime
        st['gpu'][o.path] = st['gpu'].get(o.path, 0.0) + getattr(o, 'gpuCookTime', 0.0)
    st['n'] += 1
    c.store('_perf', st)
    if st['n'] < st['frames']:
        run("op(%r).module.perf_tick(%r)" % (me.path, path), delayFrames=1)


def perf_result(path, top=8):
    st = op(path).fetch('_perf', None)
    if not st or st['n'] == 0:
        return 'no data'
    n = st['n']
    tot_cpu = sum(st['cpu'].values()) / n
    tot_gpu = sum(st['gpu'].values()) / n
    rows = sorted(st['gpu'].items(), key=lambda kv: -(kv[1] + st['cpu'][kv[0]]))[:top]
    lines = ['%s: %d frames, avg cpu %.3f ms, gpu %.3f ms per frame' % (path, n, tot_cpu, tot_gpu)]
    for p, g in rows:
        lines.append('  %-50s cpu %.3f  gpu %.3f' % (p.split('/')[-1], st['cpu'][p] / n, g / n))
    return '\n'.join(lines)
