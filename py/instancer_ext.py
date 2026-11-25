# Texture Instancer extension (the 'InstancerExt' DAT inside the component).
# - Loads a folder of images into one 2D texture array, one layer per image, a few images per frame.
# - Measures every image once (aspect, brightness, hue, saturation, alpha coverage) for ordering.
# - Writes the texture order table the GLSL POP reads (layer + aspect + brightness + hue per entry).
# - Turns the attribute pickers into #defines at the top of the 'keys' GLSL POP.

import os
import re
import time
import random
import colorsys

FIT = {'aspect': 'fill', 'crop': 'fitoutside', 'stretch': 'fill'}
MAX_LAYERS = 2048
DEMO = ['demo0', 'demo1', 'demo2', 'demo3']

# parameter name -> what a change triggers
RELOAD = {'Texturefolder', 'Subfolders', 'Filter', 'Maximumtextures', 'Cellsize', 'Fit', 'Updatereset'}
REORDER = {'Textureorder', 'Orderseed', 'Reverseorder', 'Sortmode', 'Imagematch'}
SHADER = {'Sortattr', 'Scaleattr', 'Rotateattr', 'Cullattr', 'Colorattr', 'Faceattr', 'Upattr', 'Distribution'}


def natkey(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]


class Menu:
    def __init__(self, names, labels):
        self.menuNames = names
        self.menuLabels = labels


class InstancerExt:
    def __init__(self, ownerComp):
        self.c = ownerComp
        self.job = 0
        self.sources = []
        self.info = []
        self.note = ''
        self.attrsig = None
        # the texture array is not saved with the file, so every start reloads it
        run(self.Reload, delayFrames=1)

    # ------------------------------------------------------------------ parameters
    def OnPar(self, par):
        n = par.name
        if n == 'Pulse':
            self.c.par.Seed = self.c.par.Seed.eval() + 1
        elif n in RELOAD:
            self.Reload()
        elif n in REORDER:
            self.Reorder()
            if n == 'Sortmode':
                self.UpdateShader()
        elif n in SHADER:
            self.UpdateShader()

    def _status(self, msg):
        self.c.par.Status = msg

    # ------------------------------------------------------------------ loading
    def Reload(self):
        c = self.c
        t = c.op('textures')
        self.job += 1
        self.info = []
        self.note = ''
        folder = c.par.Texturefolder.eval()
        srcs = []
        if folder:
            if os.path.isdir(folder):
                fd = t.op('folder_files')
                fd.par.refreshpulse.pulse()
                fd.cook(force=True)
                for r in range(1, fd.numRows):
                    srcs.append((fd[r, 'path'].val, float(fd[r, 'datemodified'].val or 0)))
                srcs.sort(key=lambda s: natkey(os.path.relpath(s[0], folder)))
                if not srcs:
                    self.note = 'no images match in that folder, showing the built-in shapes'
            else:
                self.note = 'folder not found, showing the built-in shapes'
        if not srcs:
            srcs = [(n, 0.0) for n in DEMO]
        cap = c.par.Maximumtextures.eval() or MAX_LAYERS
        self.sources = srcs[:min(cap, MAX_LAYERS)]

        res = int(c.par.Cellsize.eval())
        fit = t.op('fit')
        fit.par.resolutionw = res
        fit.par.resolutionh = res
        fit.par.fit = FIT[c.par.Fit.eval()]
        arr = t.op('texarray')
        arr.par.cachesize = len(self.sources)
        arr.par.replacesingle = True
        arr.par.resetpulse.pulse()  # a new cache size only takes effect on reset
        arr.cook(force=True)
        c.par.Loaded = 0
        self._status('loading 0 / %d' % len(self.sources))
        run(self._step, self.job, 0, delayFrames=1)

    def _step(self, job, i):
        if job != self.job:
            return  # a newer Reload took over
        budget = self.c.par.Loadms.eval() / 1000.0
        t0 = time.perf_counter()
        n = len(self.sources)
        while i < n:
            self._load_one(i)
            i += 1
            if budget > 0 and time.perf_counter() - t0 > budget:
                break
        self.c.par.Loaded = len(self.info)
        if i < n:
            self._status('loading %d / %d' % (i, n))
            run(self._step, job, i, delayFrames=1)
        else:
            self._done()

    def _load_one(self, k):
        t = self.c.op('textures')
        src, date = self.sources[k]
        sel, fit, arr, an = t.op('select_src'), t.op('fit'), t.op('texarray'), t.op('measure')
        if src in DEMO:
            o = t.op(src)
        else:
            o = t.op('loader')
            o.par.file = src
        sel.par.top = o.name
        o.cook(force=True)
        w, h = o.width, o.height
        if w < 2 or h < 2 or (src not in DEMO and o.errors()):
            return  # unreadable file: its layer stays empty and is never used
        fit.cook(force=True)
        arr.par.replaceindex = k
        arr.cook(force=True)
        an.cook(force=True)
        r, g, b, a = [float(v) for v in an.numpyArray()[0, 0][:4]]
        inv = 1.0 / max(a, 1e-4)  # colours are premultiplied: divide by coverage
        rr, gg, bb = min(r * inv, 1.0), min(g * inv, 1.0), min(b * inv, 1.0)
        hue, sat, _ = colorsys.rgb_to_hsv(rr, gg, bb)
        self.info.append({'layer': k, 'name': os.path.basename(src), 'date': date, 'aspect': w / h,
                          'luma': 0.2126 * rr + 0.7152 * gg + 0.0722 * bb, 'hue': hue, 'sat': sat, 'cover': a})

    def _done(self):
        c = self.c
        c.op('textures/texarray').par.replacesingle = False  # freeze the layers
        self.Reorder()
        self.UpdateShader()
        res = int(c.par.Cellsize.eval())
        mb = len(self.sources) * res * res * 4 / 1e6
        msg = '%d textures, %d MB' % (len(self.info), mb)
        self._status(msg + ('  (%s)' % self.note if self.note else ''))

    # ------------------------------------------------------------------ order
    def Reorder(self):
        c = self.c
        key = c.par.Textureorder.eval()
        image = c.par.Sortmode.eval() == 'image'
        if image:  # the photo-mosaic match needs the set sorted by what it matches
            key = 'hue' if c.par.Imagematch.eval() == 'hue' else 'luma'
        items = list(self.info)
        if key == 'random':
            random.Random(c.par.Orderseed.eval()).shuffle(items)
        elif key != 'name':
            items.sort(key=lambda d: d[key])
        if c.par.Reverseorder.eval() and not image:
            items.reverse()
        keep = c.par.Fit.eval() == 'aspect'
        tab = c.op('textures/info')
        tab.clear()
        tab.appendRow(['layer', 'aspect', 'luma', 'hue'])
        for d in items:
            tab.appendRow([d['layer'], round(d['aspect'] if keep else 1.0, 5), round(d['luma'], 5), round(d['hue'], 5)])
        if not items:
            tab.appendRow([0, 1, 0, 0])  # keeps the array uniform valid; the shader sees a count of 0
        # per-layer aspect (by layer, not by order) for the edge shader
        asp = c.op('textures/layer_aspect')
        asp.clear()
        asp.appendRow(['aspect'])
        by_layer = {d['layer']: d['aspect'] for d in self.info}
        for k in range(max(len(self.sources), 1)):
            asp.appendRow([round(by_layer.get(k, 1.0) if keep else 1.0, 5)])

    # ------------------------------------------------------------------ attribute pickers
    def _attrs(self):
        pts = self.c.op('null_points_in')
        return [(a.name, a.size) for a in pts.pointAttributes] if pts else []

    def AttrMenu(self, kind='scalar'):
        if kind == 'vector':
            names, labels = ['_worldz', '_worldy', '_worldx'], ['World Z (XY plane)', 'World Y (XZ plane)', 'World X (YZ plane)']
        else:
            names, labels = ['_none', '_index', '_random'], ['None', 'Point Index', 'Random']
        for name, size in self._attrs():
            if kind == 'vector':
                if size >= 3:
                    names.append(name)
                    labels.append(name)
            elif size == 1:
                names.append(name)
                labels.append(name)
            else:
                for i in range(min(size, 4)):
                    names.append('%s.%s' % (name, 'xyzw'[i]))
                    labels.append('%s %s' % (name, 'xyzw'[i]))
                names.append(name + '.len')
                labels.append(name + ' length')
        return Menu(names, labels)

    def UpdateShader(self):
        c = self.c
        attrs = dict(self._attrs())
        self.attrsig = tuple(sorted(attrs.items()))
        missing = []

        def scalar(sel):
            if sel in ('', '_none'):
                return '0.0'
            if sel == '_index':
                return 'float(id) / float(max(TDNumElements(), 2u) - 1u)'
            if sel == '_random':
                return 'rnd(id, 991u)'
            name, _, comp = sel.partition('.')
            if name not in attrs:
                missing.append(name)
                return '0.0'
            n = attrs[name]
            if n == 1:
                return 'float(TDIn_%s())' % name
            if comp == 'len':
                return 'length(vec%d(TDIn_%s()))' % (min(n, 4), name)
            return 'float(TDIn_%s()[%d])' % (name, 'xyzw'.index(comp or 'x'))

        def vector(sel, fallback):
            axes = {'_worldx': 'vec3(1.0, 0.0, 0.0)', '_worldy': 'vec3(0.0, 1.0, 0.0)', '_worldz': 'vec3(0.0, 0.0, 1.0)'}
            if sel in axes:
                return axes[sel]
            if attrs.get(sel, 0) >= 3:
                return 'vec3(TDIn_%s().xyz)' % sel
            if sel:
                missing.append(sel)
            return fallback

        p = c.par
        defs = [
            '// written by InstancerExt.UpdateShader() from the attribute pickers: do not edit',
            '#define KEY_SORT (%s)' % scalar(p.Sortattr.eval()),
            '#define KEY_SCALE (%s)' % scalar(p.Scaleattr.eval()),
            '#define KEY_ROT (%s)' % scalar(p.Rotateattr.eval()),
            '#define KEY_CULL (%s)' % scalar(p.Cullattr.eval()),
            '#define KEY_COLOR (%s)' % scalar(p.Colorattr.eval()),
            '#define VEC_FACE (%s)' % vector(p.Faceattr.eval(), 'vec3(0.0, 0.0, 1.0)'),
            '#define VEC_UP (%s)' % vector(p.Upattr.eval(), 'vec3(0.0, 1.0, 0.0)'),
            '#define COL_IN (%s)' % ('vec4(TDIn_Color())' if attrs.get('Color', 0) == 4 else 'vec4(1.0)'),
            '#define UV_IN (%s)' % ('vec2(TDIn_Tex().xy)' if attrs.get('Tex', 0) >= 2 else 'vec2(0.0)'),
            '',
        ]
        text = '\n'.join(defs) + c.op('glsl_keys_template').text
        dat = c.op('glsl_keys_compute')
        if dat.text != text:
            dat.text = text
        if missing:
            self._status('attribute not on the input: ' + ', '.join(sorted(set(missing))))

    def CheckAttrs(self):
        """Called every 30 frames: re-writes the shader when the input's attributes change."""
        if tuple(sorted(self._attrs())) != self.attrsig:
            self.UpdateShader()
