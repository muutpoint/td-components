# Renders the README preview images. Run inside TouchDesigner after the components are built:
#   exec(open('/Users/davidmayzenberg/Code/td-components/tools/make_previews.py').read())
# Each component is shown with settings that show it off, then put back to its defaults.
# Inputs are TouchDesigner sample images, so the previews contain no third-party artwork.

import os

REPO = '/Users/davidmayzenberg/Code/td-components'
HOME = '/project1'
TEST = HOME + '/td_components_test'
SAMPLES = app.samplesFolder + '/Map/'

t = op(TEST) or op(HOME).create(baseCOMP, TEST.split('/')[-1])
prev = t.op('previews') or t.create(baseCOMP, 'previews')

SHOTS = {
    # comp: (input image or None, {par: value}, frames to wait)
    'flipbook': ('Butterfly1.tif', {'Zoom': 0.8}, 20),
    'paint': ('Trillium.jpg', {'Outline': 0.5}, 5),
    'halftone': ('Jellybeans.1.jpg', {'Mode': 'cmyk', 'Rotater': 15, 'Rotateg': 75, 'Rotateb': 0, 'Rotatebl': 45,
                                      'Cellsize': 9, 'Glow': 0}, 5),
    'texture_instancer': (None, {'Colormode': 'random', 'Sizevariance': 0.5, 'Randomrotate': 30, 'Scalesize': 0.35,
                                 'Drift': 0.05, 'Backgroundcolorr': 0.04, 'Backgroundcolorg': 0.04,
                                 'Backgroundcolorb': 0.06}, 10),
}
FOLDERS = {'flipbook': 'flipbook', 'paint': 'paint', 'halftone': 'halftone', 'texture_instancer': 'texture-instancer'}


def _input_for(name, image):
    # the source has to live next to the components (a wire cannot cross network levels)
    m = t.op('img_' + name) or t.create(moviefileinTOP, 'img_' + name)
    m.par.file = SAMPLES + image
    o = t.op('out_' + name) or t.create(outTOP, 'out_' + name)
    o.inputConnectors[0].connect(m)
    return [oc for oc in t.outputConnectors if oc.outOP == o][0]


def shoot():
    for name, (image, pars, wait) in SHOTS.items():
        c = op(HOME + '/' + name)
        if image:
            c.inputConnectors[0].connect(_input_for(name, image))
        for k, v in pars.items():
            getattr(c.par, k).val = v
    run("exec(op(%r).text); _save()" % prev.op('script').path, delayFrames=max(w for _, _, w in SHOTS.values()))


def _save():
    for name, (image, pars, wait) in SHOTS.items():
        c = op(HOME + '/' + name)
        f = prev.op('fit_' + name) or prev.create(fitTOP, 'fit_' + name)
        sel = prev.op('sel_' + name) or prev.create(selectTOP, 'sel_' + name)
        sel.par.top = c.op('out1').path
        f.inputConnectors[0].connect(sel)
        f.par.outputresolution = 'limit'
        f.par.resolutionw, f.par.resolutionh = 960, 960
        f.cook(force=True)
        f.save(os.path.join(REPO, FOLDERS[name], 'preview.jpg'))
        for k in pars:
            p = getattr(c.par, k)
            p.val = p.default
        for ic in c.inputConnectors:
            ic.disconnect()
    print('previews saved')


# --- run ---
s = prev.op('script') or prev.create(textDAT, 'script')
s.par.language = 'python'
s.text = open(os.path.join(REPO, 'tools', 'make_previews.py'), encoding='utf-8').read().split('# --- run ---')[0]
shoot()
