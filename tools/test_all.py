# Test suite: rebuild, check, export and re-import every component.
# Runs inside TouchDesigner. It needs frames to pass (outputs cook, movies load), so it is loaded into a
# text DAT and steps itself with run():
#
#   exec(open('/Users/davidmayzenberg/Code/td-components/tools/test_all.py').read())
#   ... about 10 s later ...
#   print(op('/project1/td_components_test/tests').module.report())
#
# Set EXPORT = False (before exec) to skip writing the .tox files.

import os, json

REPO = '/Users/davidmayzenberg/Code/td-components'
HOME = '/project1'
TEST = HOME + '/td_components_test'

COMPONENTS = [
    # name, folder in the repo, build script, a parameter change that must change the output
    ('flipbook', 'flipbook', 'build_flipbook.py', ('Notebook', False)),
    ('paint', 'paint', 'build_paint.py', ('Numcolors', 0)),
    ('halftone', 'halftone', 'build_halftone.py', ('Mode', 'cmyk')),
    ('texture_instancer', 'texture-instancer', 'build_instancer.py', ('Sortmode', 'sequential')),
]


def _stats(top):
    import numpy as np
    a = top.numpyArray(delayed=False)
    if a is None:
        return None
    return {'w': top.width, 'h': top.height, 'mean': float(np.nanmean(a[..., :3])),
            'std': float(np.nanstd(a[..., :3])), 'nan': bool(np.isnan(a).any()),
            'alpha': float(np.nanmean(a[..., 3]))}


def _shaders_ok(comp):
    bad = []
    for d in comp.findChildren(type=DAT, name='*_info'):
        if d.OPType != 'infoDAT':
            continue
        t = d.text
        if 'Compiled Successfully' not in t or 'ERROR' in t.upper().replace('ERRORS', ''):
            bad.append(d.path)
    return bad


def _log(msg):
    st = op(TEST).fetch('test_log', [])
    st.append(msg)
    op(TEST).store('test_log', st)


def start(export=True):
    t = op(TEST)
    t.store('test_log', [])
    t.store('test_results', {})
    t.store('test_export', export)
    for name, folder, script, _ in COMPONENTS:
        g = {'TARGET': HOME, 'NAME': name}
        try:
            exec(open(os.path.join(REPO, 'tools', script), encoding='utf-8').read(), g)
            _log('built %s' % name)
        except Exception as e:
            _log('BUILD FAILED %s: %r' % (name, e))
    run("op(%r).module.step_check()" % me.path, delayFrames=30)


def step_check():
    res = op(TEST).fetch('test_results', {})
    src = op(TEST + '/img_mettler')
    for name, folder, script, (par, val) in COMPONENTS:
        c = op(HOME + '/' + name)
        r = {}
        r['errors'] = c.errors(recurse=True)
        r['warnings'] = c.warnings(recurse=True)
        r['shaders_bad'] = _shaders_ok(c)
        out = c.op('out1')
        out.cook(force=True)
        r['default'] = _stats(out)
        res[name] = r
    op(TEST).store('test_results', res)
    # parameter response
    for name, folder, script, (par, val) in COMPONENTS:
        c = op(HOME + '/' + name)
        p = getattr(c.par, par)
        c.store('_test_restore', (par, p.eval()))
        p.val = val
    run("op(%r).module.step_par()" % me.path, delayFrames=10)


def step_par():
    res = op(TEST).fetch('test_results', {})
    for name, folder, script, (par, val) in COMPONENTS:
        c = op(HOME + '/' + name)
        out = c.op('out1')
        out.cook(force=True)
        s = _stats(out)
        d = res[name]['default']
        res[name]['par_change'] = {'par': par, 'value': val, 'stats': s,
                                   'changed': bool(s and d and (abs(s['mean'] - d['mean']) > 1e-3 or abs(s['std'] - d['std']) > 1e-3))}
        p, v = c.fetch('_test_restore')
        getattr(c.par, p).val = v
        c.unstore('_test_restore')
    # input response (TOP components get a photo; the instancer gets a grid of points)
    t = op(TEST)
    grid = t.op('grid_points') or t.create(gridPOP, 'grid_points')
    grid.par.cols, grid.par.rows = 12, 8
    grid.par.sizex, grid.par.sizey = 4, 2.6
    gout = t.op('out_points') or t.create(outPOP, 'out_points')
    gout.inputConnectors[0].connect(grid)
    def conn(o):
        return [oc for oc in t.outputConnectors if oc.outOP == o][0]
    for name in ('flipbook', 'paint', 'halftone'):
        op(HOME + '/' + name).inputConnectors[0].connect(conn(t.op('out2')))
    op(HOME + '/texture_instancer').inputConnectors[0].connect(conn(gout))
    op(TEST).store('test_results', res)
    run("op(%r).module.step_input()" % me.path, delayFrames=20)


def step_input():
    res = op(TEST).fetch('test_results', {})
    for name, folder, script, _ in COMPONENTS:
        c = op(HOME + '/' + name)
        out = c.op('out1')
        out.cook(force=True)
        s = _stats(out)
        d = res[name]['default']
        res[name]['with_input'] = {'stats': s, 'changed': bool(s and d and abs(s['mean'] - d['mean']) > 1e-3),
                                   'errors': c.errors(recurse=True)}
        try:
            out.save(os.path.join(REPO, folder, 'preview.jpg'))
        except Exception as e:
            res[name]['preview_error'] = repr(e)
        for i in range(len(c.inputConnectors)):
            c.inputConnectors[i].disconnect()
    op(TEST).store('test_results', res)
    if op(TEST).fetch('test_export', True):
        run("op(%r).module.step_export()" % me.path, delayFrames=5)
    else:
        _log('done (no export)')


def step_export():
    res = op(TEST).fetch('test_results', {})
    rt = op(TEST + '/roundtrip')
    if rt:
        rt.destroy()
    rt = op(TEST).create(baseCOMP, 'roundtrip')
    rt.nodeY = -800
    for name, folder, script, _ in COMPONENTS:
        c = op(HOME + '/' + name)
        path = os.path.join(REPO, folder, name + '.tox')
        c.save(path)
        res[name]['tox'] = {'path': path, 'bytes': os.path.getsize(path)}
        loaded = rt.loadTox(path)
        loaded.nodeX = len(rt.children) * 200
        res[name]['tox']['loaded_as'] = loaded.path
    op(TEST).store('test_results', res)
    run("op(%r).module.step_roundtrip()" % me.path, delayFrames=30)


def step_roundtrip():
    res = op(TEST).fetch('test_results', {})
    for name, folder, script, _ in COMPONENTS:
        l = op(res[name]['tox']['loaded_as'])
        out = l.op('out1')
        out.cook(force=True)
        s = _stats(out)
        d = res[name]['default']
        locked = [o.path for o in l.findChildren(type=TOP) if o.lock]
        res[name]['roundtrip'] = {
            'errors': l.errors(recurse=True), 'shaders_bad': _shaders_ok(l), 'stats': s,
            'locked_tops': {o.split('/')[-1]: (op(o).width, op(o).height) for o in locked},
            'close_to_original': bool(s and d and abs(s['mean'] - d['mean']) < 0.05),
        }
    op(TEST).store('test_results', res)
    _log('done')


def report():
    log = op(TEST).fetch('test_log', [])
    res = op(TEST).fetch('test_results', {})
    lines = list(log)
    ok_all = True
    for name, folder, script, _ in COMPONENTS:
        r = res.get(name)
        if not r:
            lines.append('%s: no results yet' % name)
            ok_all = False
            continue
        checks = [
            ('no errors', not r['errors']),
            ('shaders compile', not r['shaders_bad']),
            ('output not empty / NaN', bool(r['default'] and not r['default']['nan'] and r['default']['std'] > 1e-3)),
        ]
        if 'par_change' in r:
            checks.append(('%s=%r changes output' % (r['par_change']['par'], r['par_change']['value']), r['par_change']['changed']))
        if 'with_input' in r:
            checks.append(('responds to input', r['with_input']['changed'] and not r['with_input']['errors']))
        if 'roundtrip' in r:
            rt = r['roundtrip']
            checks.append(('tox reloads clean', not rt['errors'] and not rt['shaders_bad']))
            checks.append(('reloaded output matches', rt['close_to_original']))
        ok = all(v for _, v in checks)
        ok_all &= ok
        size = ('%.1f MB' % (r['tox']['bytes'] / 1e6)) if 'tox' in r else '-'
        lines.append('%s %s (tox %s)' % ('PASS' if ok else 'FAIL', name, size))
        for label, v in checks:
            lines.append('    [%s] %s' % ('x' if v else ' ', label))
        if r['warnings']:
            lines.append('    warnings: ' + r['warnings'].strip().replace('\n', ' | ')[:300])
        if 'roundtrip' in r and r['roundtrip']['locked_tops']:
            lines.append('    embedded textures: %s' % r['roundtrip']['locked_tops'])
    lines.append('ALL PASS' if ok_all else 'SOME CHECKS FAILED')
    return '\n'.join(lines)


def results_json():
    return json.dumps(op(TEST).fetch('test_results', {}), indent=1, default=str)


# when exec'd from the textport / MCP: install this file as a module DAT and start
if __name__ == '__main__' or 'TEST_INSTALLED' not in globals():
    _t = op(TEST) or op(HOME).create(baseCOMP, TEST.split('/')[-1])
    _d = _t.op('tests') or _t.create(textDAT, 'tests')
    _d.par.language = 'python'
    _d.text = open(os.path.join(REPO, 'tools', 'test_all.py'), encoding='utf-8').read().replace(
        "'TEST_INSTALLED' not in globals()", 'False')
    _d.module.start(globals().get('EXPORT', True))
