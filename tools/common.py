# Shared helpers for the build scripts. Run inside TouchDesigner:
#   exec(open('/Users/davidmayzenberg/Code/td-components/tools/build_flipbook.py').read())
# Each build script execs this file first.

import os

REPO = '/Users/davidmayzenberg/Code/td-components'
VERSION = '2.0'
CREDIT = '© Ro Mayz'


class E:
    """Parameter expression."""
    def __init__(self, s):
        self.s = s


class B:
    """Parameter bind."""
    def __init__(self, s):
        self.s = s


def src(*parts):
    with open(os.path.join(REPO, *parts), encoding='utf-8') as f:
        return f.read()


def setp(o, **pars):
    for k, v in pars.items():
        p = getattr(o.par, k)
        if isinstance(v, E):
            p.expr = v.s
        elif isinstance(v, B):
            p.bindExpr = v.s
            p.mode = ParMode.BIND
        else:
            p.val = v
    return o


def mk(comp, optype, name, x, y, inputs=(), **pars):
    old = comp.op(name)
    if old:
        old.destroy()
    o = comp.create(optype, name)
    o.nodeX, o.nodeY = x, y
    for i, s in enumerate(inputs):
        if s is None:
            continue
        s = comp.op(s) if isinstance(s, str) else s
        o.inputConnectors[i].connect(s.outputConnectors[0] if s.isCOMP else s)
    return setp(o, **pars)


def fresh_comp(parent_comp, name, x=0, y=0, optype=None):
    old = parent_comp.op(name)
    if old:
        old.destroy()
    c = parent_comp.create(optype or baseCOMP, name)
    c.nodeX, c.nodeY = x, y
    return c


def glsl(comp, name, x, y, shader_file, inputs=(), uniforms=(), **pars):
    """glslmultiTOP whose pixel shader is embedded from glsl/<shader_file>.
    uniforms: [(name, [v0, v1, v2, v3])] where each v is a number, E() or B()."""
    g = mk(comp, glslmultiTOP, name, x, y, inputs)
    pix = comp.op(name + '_pixel')
    if pix is None:
        pix = comp.create(textDAT, name + '_pixel')
        g.par.pixeldat = pix.name
    pix.par.language = 'glsl'
    pix.text = src('glsl', shader_file)
    pix.nodeX, pix.nodeY = x, y - 150
    for suffix in ('_compute',):
        d = comp.op(name + suffix)
        if d:
            d.destroy()
    info = comp.op(name + '_info')
    if info:
        info.nodeX, info.nodeY = x + 100, y - 150
    g.seq.vec.numBlocks = max(1, len(uniforms))
    for i, (uname, vals) in enumerate(uniforms):
        setattr(g.par, 'vec%dname' % i, uname)
        for j, v in enumerate(vals):
            setp(g, **{'vec%dvalue%s' % (i, 'xyzw'[j]): v})
    return setp(g, **pars)


class Pars:
    """Small builder for custom parameter pages."""
    def __init__(self, comp, page):
        self.c = comp
        self.pg = comp.appendCustomPage(page)
        self._section = False

    def section(self):
        self._section = True
        return self

    def _fin(self, p, help=None):
        if self._section:
            p.startSection = True
            self._section = False
        if help:
            p.help = help
        return p

    def float(self, name, label, default, lo=0.0, hi=1.0, clamp=None, help=None):
        p = self.pg.appendFloat(name, label=label)[0]
        p.normMin, p.normMax = lo, hi
        if clamp:
            p.clampMin, p.min = True, clamp[0]
            if clamp[1] is not None:
                p.clampMax, p.max = True, clamp[1]
        p.default = default
        p.val = default
        return self._fin(p, help)

    def int(self, name, label, default, lo=0, hi=10, clamp=None, help=None):
        p = self.pg.appendInt(name, label=label)[0]
        p.normMin, p.normMax = lo, hi
        if clamp:
            p.clampMin, p.min = True, clamp[0]
            if clamp[1] is not None:
                p.clampMax, p.max = True, clamp[1]
        p.default = default
        p.val = default
        return self._fin(p, help)

    def toggle(self, name, label, default, help=None):
        p = self.pg.appendToggle(name, label=label)[0]
        p.default = default
        p.val = default
        return self._fin(p, help)

    def pulse(self, name, label, help=None):
        return self._fin(self.pg.appendPulse(name, label=label)[0], help)

    def menu(self, name, label, names, labels, default=None, help=None):
        p = self.pg.appendMenu(name, label=label)[0]
        p.menuNames = names
        p.menuLabels = labels
        p.default = default or names[0]
        p.val = p.default
        return self._fin(p, help)

    def str(self, name, label, default='', help=None):
        p = self.pg.appendStr(name, label=label)[0]
        p.default = default
        p.val = default
        return self._fin(p, help)

    def file(self, name, label, help=None, folder=False):
        p = (self.pg.appendFolder if folder else self.pg.appendFile)(name, label=label)[0]
        return self._fin(p, help)

    def top(self, name, label, help=None):
        return self._fin(self.pg.appendTOP(name, label=label)[0], help)

    def comp(self, name, label, help=None):
        return self._fin(self.pg.appendCOMP(name, label=label)[0], help)

    def rgb(self, name, label, default=(1, 1, 1), help=None):
        ps = self.pg.appendRGB(name, label=label)
        for p, v in zip(ps, default):
            p.default = v
            p.val = v
            p.normMin, p.normMax = 0, 1
        self._fin(ps[0], help)
        return ps

    def rgba(self, name, label, default=(1, 1, 1, 1), help=None):
        ps = self.pg.appendRGBA(name, label=label)
        for p, v in zip(ps, default):
            p.default = v
            p.val = v
            p.normMin, p.normMax = 0, 1
        self._fin(ps[0], help)
        return ps

    def wh(self, name, label, default=(1920, 1080), help=None):
        ps = self.pg.appendWH(name, label=label)
        for p, v in zip(ps, default):
            p.default = v
            p.val = v
            p.normMin, p.normMax = 1, 4096
            p.clampMin, p.min = True, 1
        self._fin(ps[0], help)
        return ps

    def xy(self, name, label, default=(0, 0), lo=-1, hi=1, help=None):
        ps = self.pg.appendXY(name, label=label)
        for p, v in zip(ps, default):
            p.default = v
            p.val = v
            p.normMin, p.normMax = lo, hi
        self._fin(ps[0], help)
        return ps


def about_page(comp, title, blurb):
    a = Pars(comp, 'About')
    v = a.str('Version', 'Version', VERSION)
    v.readOnly = True
    c = a.str('Credit', 'Credit', CREDIT)
    c.readOnly = True
    h = a.str('Help', 'Help', blurb)
    h.readOnly = True
    comp.comment = '%s %s. %s' % (title, VERSION, blurb)


def lock_image(top, path, fmt='mono8fixed'):
    """Load an image into a TOP, lock it so the pixels are stored in the .tox, clear the path."""
    top.lock = False
    top.par.file = path
    top.par.format = fmt
    top.par.reloadpulse.pulse()
    top.cook(force=True)
    top.lock = True
    top.par.file = ''


def finish(comp, color=(0.25, 0.35, 0.5)):
    comp.color = color
    comp.viewer = True
    for o in comp.children:
        o.viewer = False
