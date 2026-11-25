# Builds the Texture Instancer component (v3). Run inside TouchDesigner:
#   exec(open('/Users/davidmayzenberg/Code/td-components/tools/build_instancer.py').read())
# Creates /project1/texture_instancer2 by default (the old COMP is texture_instancer).
# Textures: one 2D texture array, filled by py/instancer_ext.py a few images per frame.
# Points: glsl_keys (attribute pickers) -> analyze (auto ranges) -> glsl_attribs (everything per instance).
# The orbit camera is TouchDesigner's own cameraViewport (/sys/TDTox/cameraViewport), cloned like the palette does.

exec(open('/Users/davidmayzenberg/Code/td-components/tools/common.py', encoding='utf-8').read())

TARGET = globals().get('TARGET', '/project1')
NAME = globals().get('NAME', 'texture_instancer2')
POS = globals().get('POS', (900, -700))
IVERSION = '3.0'

c = fresh_comp(op(TARGET), NAME, *POS)
c.par.parentshortcut = 'Instancer'
R = 'parent().par'
CLK = "op('null_clock')['%s']"


def strmenu(P, name, label, default, kind='scalar', help=None):
    p = P.pg.appendStrMenu(name, label=label)[0]
    p.menuSource = "me.AttrMenu('%s')" % kind
    p.default = default
    p.val = default
    return P._fin(p, help)


def xyz(P, name, label, default=(0, 0, 0), lo=-1, hi=1):
    ps = P.pg.appendXYZ(name, label=label)
    for p, v in zip(ps, default):
        p.default = v
        p.val = v
        p.normMin, p.normMax = lo, hi
    P._fin(ps[0])
    return ps


# ---------------------------------------------------------------- parameters
P = Pars(c, 'Textures')
P.file('Texturefolder', 'Texture Folder', folder=True, help='Images (movies use their first frame). Empty = the built-in shapes.')
P.toggle('Subfolders', 'Include Subfolders', False)
P.str('Filter', 'Name Filter', '*', help='File name patterns, e.g. "brush*" or "*.png *.jpg".')
P.int('Maximumtextures', 'Maximum Textures', 512, 1, 2048, clamp=(0, 2048), help='0 = all (up to 2048).')
P.int('Cellsize', 'Texture Size', 512, 64, 2048, clamp=(16, 4096), help='Each image is stored at this size (square). Memory = count x size x size x 4 bytes.')
P.menu('Fit', 'Fit', ['aspect', 'crop', 'stretch'], ['Keep Image Aspect', 'Crop to Square', 'Stretch to Square'],
       help='Keep Image Aspect stretches the image into the square and un-stretches the quad, so no texels are wasted.')
P.float('Loadms', 'Load Budget (ms/frame)', 25, 0, 100, clamp=(0, None), help='Time spent loading per frame. 0 = all in one frame.')
P.pulse('Updatereset', 'Reload Folder')
P.section().menu('Textureorder', 'Texture Order',
                 ['name', 'date', 'random', 'luma', 'hue', 'sat', 'cover', 'aspect'],
                 ['Name', 'Date Modified', 'Random', 'Brightness', 'Hue', 'Saturation', 'Coverage (alpha)', 'Aspect'],
                 help='Order of the set; Assign By then maps points onto this order. Changing it does not reload.')
P.int('Orderseed', 'Order Seed', 0, 0, 100)
P.toggle('Reverseorder', 'Reverse Order', False)
P.xy('Texrange', 'Use Range', (0, 1), 0, 1, help='Use only this part of the ordered set (0-1).')
P.section().menu('Edge', 'Outline', ['off', 'over', 'only'], ['Off', 'Outline', 'Outline Only'])
P.float('Edgewidth', 'Outline Width', 0.02, 0, 0.1, clamp=(0, 0.5))
P.float('Edgesoft', 'Outline Softness', 0.3, 0, 1)
P.rgba('Edgecolor', 'Outline Color', (1, 1, 1, 1))
P.section().int('Loaded', 'Textures Loaded', 0, 0, 2048).readOnly = True
P.str('Status', 'Status', '').readOnly = True

P = Pars(c, 'Sorting')
P.menu('Sortmode', 'Assign By', ['sequential', 'random', 'attribute', 'noise', 'image'],
       ['Sequential (point number)', 'Random', 'Attribute', 'Noise Field', 'Photo-Mosaic (Guide Image)'], default='random',
       help='How each point picks its texture from the ordered set.')
strmenu(P, 'Sortattr', 'Attribute', 'P.y', help='Low values get the start of the set, high values the end.')
P.toggle('Sortauto', 'Auto Range', True, help='Map the attribute\'s min..max onto the set. Off: use Manual Range.')
P.xy('Sortrange', 'Manual Range', (0, 1), -10, 10)
P.float('Sortnoisefreq', 'Noise Frequency', 1.0, 0, 5)
P.float('Sortnoisespeed', 'Noise Speed', 0.0, 0, 2)
P.section().top('Image', 'Guide Image', help='Photo-mosaic: each point gets the texture nearest in brightness (or hue) to this image.')
P.menu('Imagemap', 'Map Image By', ['xy', 'xz', 'zy', 'uv'], ['Bounds XY (front)', 'Bounds XZ (top)', 'Bounds ZY (side)', 'Point Tex (UV)'])
P.menu('Imagematch', 'Match', ['brightness', 'hue'], ['Brightness', 'Hue'])
P.toggle('Imagestretch', 'Stretch to Set', True, help='Spread the image\'s 0-1 over the darkest..brightest texture.')
P.section().float('Offset', 'Offset', 0.0, -1, 1, help='Scroll through the set (fraction of it). Animate it to slide textures.')
P.float('Repeat', 'Repeat', 1.0, 0, 10, clamp=(0, None), help='How many times the set repeats across the key range.')
P.int('Steps', 'Steps', 0, 0, 32, clamp=(0, None), help='Quantise the key into this many bands. 0 = smooth.')
P.float('Jitter', 'Jitter', 0.0, 0, 1, help='Random shift through the set per point.')
P.section().int('Seed', 'Seed', 0, 0, 100)
P.pulse('Pulse', 'Shuffle', help='New random order (bumps the seed).')
P.toggle('Randomloop', 'Auto Shuffle', False)
P.float('Loopinterval', 'Shuffle Every (s)', 1.0, 0.05, 10, clamp=(0.01, None))
P.section().float('Cyclespeed', 'Flip Speed', 0.0, 0, 30, help='Flip book: textures advanced per second.')
P.float('Cyclephase', 'Flip Offset per Instance', 0.0, 0, 1, help='0 = all flip together, 1 = every instance at its own place in the set.')

P = Pars(c, 'Scale')
P.float('Scalesize', 'Size', 0.25, 0, 2, clamp=(0, None), help='Longest side of each instance, in point units.')
P.xy('Stretch', 'Stretch X / Y', (1, 1), 0, 2)
P.float('Sizevariance', 'Random Variance', 0.0, 0, 1)
P.section().menu('Scaleby', 'Scale By', ['off', 'attribute', 'noise', 'wave'], ['Off', 'Attribute', 'Noise', 'Wave along Attribute'])
strmenu(P, 'Scaleattr', 'Attribute', 'P.y')
P.toggle('Scaleauto', 'Auto Range', True)
P.xy('Scalerange', 'Manual Range', (0, 1), -10, 10)
P.xy('Scaleout', 'Size at Min / Max', (0.2, 1.0), 0, 2, help='Multipliers on Size at the low and high end.')
P.float('Scalefreq', 'Noise Frequency', 1.0, 0, 5)
P.float('Wavelength', 'Wavelength', 0.5, 0.05, 2, clamp=(0.01, None), help='In 0-1 units of the attribute range.')
P.float('Scalespeed', 'Speed', 0.3, -3, 3, help='Noise drift or wave cycles per second.')
P.section().float('Reveal', 'Reveal', 1.0, 0, 1, help='0 -> 1 grows instances in along Reveal By.')
P.menu('Revealby', 'Reveal By', ['assign', 'index', 'random', 'scale'], ['Texture Key', 'Point Index', 'Random', 'Scale Attribute'])
P.float('Revealsoft', 'Reveal Softness', 0.2, 0, 1)
P.toggle('Revealinvert', 'Reveal Reverse', False)

P = Pars(c, 'Rotate')
P.menu('Facing', 'Facing', ['camera', 'attribute', 'random'], ['Face Camera', 'Along Attribute', 'Random'],
       help='Along Attribute with N lays the textures on the surface; World Z/Y/X gives flat planes.')
strmenu(P, 'Faceattr', 'Facing Attribute', 'N', kind='vector')
strmenu(P, 'Upattr', 'Up Attribute', '_worldy', kind='vector')
P.float('Pushout', 'Push Along Facing Attr', 0.0, -0.5, 0.5, help='Lift instances off the surface along the facing attribute.')
P.section().float('Randomrotate', 'Random Rotate', 0, 0, 180)
strmenu(P, 'Rotateattr', 'Rotate by Attribute', '_none')
P.float('Rotateamount', 'Degrees Across Range', 180, -360, 360)
P.toggle('Rotateauto', 'Auto Range', True)
P.xy('Rotaterange', 'Manual Range', (0, 1), -10, 10)
P.section().float('Spin', 'Spin', 0, -180, 180, help='Degrees per second.')
P.toggle('Spinrandomdir', 'Random Spin Direction', True)
P.float('Tilt', 'Random Tilt', 0, 0, 90)

P = Pars(c, 'Position')
P.menu('Distribution', 'Distribution', ['points', 'surface', 'volume'], ['Input Points', 'Scatter on Surface', 'Scatter in Volume'],
       help='Scatter needs a mesh (triangles or quads) on input 1.')
P.int('Scattercount', 'Scatter Count', 2000, 1, 20000, clamp=(1, None))
P.float('Scatterseed', 'Scatter Seed', 0, 0, 100)
P.section()
xyz(P, 'Translate', 'Offset')
P.float('Posjitter', 'Random Offset', 0.0, 0, 0.5)
P.float('Drift', 'Drift', 0.0, 0, 1, help='Points wander with noise (point units).')
P.float('Driftfreq', 'Drift Frequency', 0.5, 0, 5)
P.float('Driftspeed', 'Drift Speed', 0.3, 0, 3)
P.section().float('Density', 'Density', 1.0, 0, 1, help='Fraction of instances kept (random).')
P.menu('Cullmode', 'Cull by Attribute', ['off', 'above', 'below'], ['Off', 'Keep Above Threshold', 'Keep Below Threshold'])
strmenu(P, 'Cullattr', 'Cull Attribute', 'P.y')
P.float('Cullthreshold', 'Threshold', 0.5, 0, 1, help='In 0-1 of the attribute\'s range.')

P = Pars(c, 'Color')
P.menu('Colormode', 'Color Mode', ['off', 'random', 'pertexture', 'attribute', 'image', 'pointcolor'],
       ['Off', 'Random from Palette', 'One per Texture', 'Palette by Attribute', 'Image at Point', 'Point Color'])
P.top('Colorpalletetop', 'Palette / Image TOP', help='Empty = built-in rainbow ramp (Image at Point falls back to the Guide Image).')
strmenu(P, 'Colorattr', 'Color Attribute', 'P.y')
P.float('Tint', 'Color Amount', 1.0, 0, 1)
P.rgba('Tintcolor', 'Tint', (1, 1, 1, 1))
P.float('Opacity', 'Opacity', 1.0, 0, 1)
P.section().menu('Blend', 'Blend', ['cutout', 'soft', 'add'], ['Cutout (alpha test)', 'Soft (depth sorted)', 'Additive'],
                 help='Soft sorts instances back to front every frame for clean soft edges.')
P.float('Alphathreshold', 'Alpha Threshold', 0.5, 0, 1, help='Cutout: pixels below this alpha are discarded.')

P = Pars(c, 'Scene')
P.wh('Resolution', 'Resolution', (1920, 1080))
P.rgb('Backgroundcolor', 'Background Color', (0, 0, 0))
P.float('Backgroundalpha', 'Background Alpha', 1.0, 0, 1)
P.comp('Camera', 'Camera', help='Optional: render with your own camera. Empty = the built-in orbit camera.')
P.menu('Antialias', 'Anti-Alias', ['aa1', 'aa2', 'aa4', 'aa8'], ['1x', '2x', '4x', '8x'], default='aa4')

about_page(c, 'Texture Instancer', 'Instances a folder of textures on POP points, driven by point attributes: '
           'order, size, rotation, reveal, colour, photo-mosaic.')
c.par.Version = IVERSION
c.comment = c.comment.replace(VERSION, IVERSION, 1)

# ---------------------------------------------------------------- extension + callbacks
ext = mk(c, textDAT, 'InstancerExt', -600, 400)
ext.text = src('py', 'instancer_ext.py')
ext.par.language = 'python'
pe = mk(c, parameterexecuteDAT, 'parexec', -400, 400, pars='*', valuechange=True, onpulse=True)
pe.par.op.expr = 'parent()'
pe.text = '''# Every custom parameter goes to InstancerExt.OnPar, which decides: reload, reorder or rewrite the keys shader.
def onValueChange(par, prev):
    parent.Instancer.OnPar(par)
    return

def onPulse(par):
    parent.Instancer.OnPar(par)
    return
'''
fe = mk(c, executeDAT, 'frame_check', -200, 400, framestart=True)
fe.text = '''# Re-writes the keys shader when the input's attributes change (checked twice a second).
def onFrameStart(frame):
    if frame % 30 == 0:
        parent.Instancer.CheckAttrs()
    return
'''

# ---------------------------------------------------------------- textures
tx = fresh_comp(c, 'textures', 0, 700)
tx.par.parentshortcut = 'Textures'
I_ = 'parent.Instancer.par'
mk(tx, folderDAT, 'folder_files', 0, 0, rootfolder=E(I_ + '.Texturefolder.eval()'), subfolders=B(I_ + '.Subfolders'),
   names=B(I_ + '.Filter'), imageextensions=True, movieextensions=True, allextensions=False,
   pathcol=True, datemodifiedcol=True, dateformat='epoch')
mk(tx, moviefileinTOP, 'loader', 0, -200, hwdecode=False, playmode='specify', index=0, alwaysloadinitial=True)
demo = [
    ('demo0', circleTOP, dict(radiusx=0.42, radiusy=0.42, radiusunit='fraction', bgalpha=0)),
    ('demo1', circleTOP, dict(radiusx=0.42, radiusy=0.42, radiusunit='fraction', borderwidth=0.08,
                              borderwidthunit='fraction', borderr=1, borderg=1, borderb=1,
                              fillalpha=0, bgalpha=0)),
    ('demo2', rectangleTOP, dict(sizex=0.7, sizey=0.7, bgalpha=0)),
    ('demo3', textTOP, dict(text='✦', fontsizex=200, bgalpha=0)),
]
for i, (n, t, kw) in enumerate(demo):
    o = mk(tx, t, n, 0, -400 - 120 * i, outputresolution='custom', resolutionw=256, resolutionh=256)
    for k, v in kw.items():
        try:
            setp(o, **{k: v})
        except Exception:
            pass
mk(tx, selectTOP, 'select_src', 200, -200, top='demo0')
mk(tx, fitTOP, 'fit', 375, -200, ['select_src'], outputresolution='custom', resolutionw=512, resolutionh=512,
   outputaspect='resolution', fit='fill', format='rgba8fixed')
mk(tx, analyzeTOP, 'measure', 550, -350, ['fit'], op='average', analyzechannel='independent', format='rgba32float')
mk(tx, texture3dTOP, 'texarray', 550, -200, ['fit'], type='texture2darray', active=False, replacesingle=False,
   cachesize=4, prefill=False)
info = mk(tx, tableDAT, 'info', 375, 150)
info.clear()
info.appendRow(['layer', 'aspect', 'luma', 'hue'])
info.appendRow([0, 1, 0, 0])
mk(tx, dattoCHOP, 'info_chop', 550, 150, dat='info', output='chanpercol', firstrow='names', firstcolumn='values')
asp = mk(tx, tableDAT, 'layer_aspect', 375, 0)
asp.clear()
asp.appendRow(['aspect'])
asp.appendRow([1])
mk(tx, dattoCHOP, 'aspect_chop', 550, 0, dat='layer_aspect', output='chanpercol', firstrow='names', firstcolumn='values')
edge = glsl(tx, 'edge_fx', 750, -350, 'instancer_edge.glsl', ['texarray'],
            uniforms=[('uEdge', [E("parent.Instancer.par.Edge.menuIndex"), B(I_ + '.Edgewidth'), B(I_ + '.Edgesoft'), 0]),
                      ('uEdgeColor', [B(I_ + '.Edgecolorr'), B(I_ + '.Edgecolorg'), B(I_ + '.Edgecolorb'), B(I_ + '.Edgecolora')])],
            type='texture2darray', depth='custom', customdepth=E("op('texarray').par.cachesize"),
            outputresolution='useinput', format='rgba8fixed')
edge.seq.array.numBlocks = 1
setp(edge, array0name='uAspect', array0type='float', array0chop='aspect_chop', array0arraytype='texturebuffer')
mk(tx, selectTOP, 'null_array', 950, -200, top=E("'edge_fx' if parent.Instancer.par.Edge != 'off' else 'texarray'"))
mk(tx, outTOP, 'out_array', 1125, -200, ['null_array'])

# ---------------------------------------------------------------- points
X = 0
mk(c, spherePOP, 'demo_points', X - 600, 0, type='geodesic', freq=5, radx=1.6, rady=1.6, radz=1.6)
try:
    c.op('demo_points').par.geodesictype = 'triangles'
except Exception:
    pass
c.op('demo_points').comment = 'Default points (a geodesic sphere), used when nothing is wired into input 1.'
mk(c, inPOP, 'in_points', X - 425, 0, ['demo_points'])
mk(c, sprinklePOP, 'scatter', X - 250, -125, ['in_points'], numpoints=B(R + '.Scattercount'), seed=B(R + '.Scatterseed'),
   method=E("'vol' if parent().par.Distribution == 'volume' else 'perprim'"))
mk(c, switchPOP, 'switch_dist', X - 75, 0, ['in_points', 'scatter'], index=E("0 if parent().par.Distribution == 'points' else 1"))
mk(c, nullPOP, 'null_points_in', X + 100, 0, ['switch_dist'])

tmpl = mk(c, textDAT, 'glsl_keys_template', X + 275, -300)
tmpl.par.language = 'glsl'
tmpl.text = src('glsl', 'instancer_keys.glsl')
gk = mk(c, glslPOP, 'glsl_keys', X + 275, 0, ['null_points_in'], initoutputattrs=False)
kd = c.op('glsl_keys_compute')
kd.par.language = 'glsl'
kd.nodeX, kd.nodeY = X + 275, -150
keys_attrs = [('Keys', 'float', 4), ('Keys2', 'float', 4), ('Face', 'float', 3), ('Upv', 'float', 3),
              ('Cin', 'float', 4), ('Uvin', 'float', 2)]


def new_attrs(g, attrs):
    g.seq.attr.numBlocks = len(attrs)
    for i, (n, t, nc) in enumerate(attrs):
        setp(g, **{'attr%dname' % i: 'custom', 'attr%dcustomname' % i: n, 'attr%dtype' % i: t})
        try:
            setattr(g.par, 'attr%dnumcomps' % i, str(nc))
        except Exception:
            setattr(g.par, 'attr%dnumcomps' % i, nc)


new_attrs(gk, keys_attrs)
mk(c, analyzePOP, 'analyze_keys', X + 450, -150, ['glsl_keys'], inputattrs='Keys Keys2 P', min=True, max=True,
   avg=False, appendattrname=True)

gp = mk(c, glslPOP, 'glsl_attribs', X + 625, 0, ['glsl_keys', 'analyze_keys'], initoutputattrs=False)
cd = c.op('glsl_attribs_compute')
cd.par.language = 'glsl'
cd.text = src('glsl', 'instancer_attribs.glsl')
cd.nodeX, cd.nodeY = X + 625, -150
new_attrs(gp, [('TexW', 'float', 1), ('Iscale', 'float', 3), ('Irot', 'float', 1), ('Facing', 'float', 3),
               ('Upd', 'float', 3), ('Icolor', 'float', 4), ('Iactive', 'float', 1)])
gp.par.outputattrs = 'P'

# clocks: speeds integrate, so changing a speed never jumps
# a clock only runs while its feature is on, and the uniforms only read it then (see CLK uses below), so a still
# setup doesn't recook the GLSL POP every frame. Setting a speed to 0 returns that feature to its rest state.
rates = [('cycle', B(R + '.Cyclespeed')),
         ('sortnoise', E("parent().par.Sortnoisespeed.eval() if parent().par.Sortmode == 'noise' else 0")),
         ('scale', E("parent().par.Scalespeed.eval() if parent().par.Scaleby in ('noise', 'wave') else 0")),
         ('spin', B(R + '.Spin')),
         ('drift', E("parent().par.Driftspeed.eval() if parent().par.Drift > 0 else 0")),
         ('shuffle', E("1.0 / max(parent().par.Loopinterval.eval(), 0.01) if parent().par.Randomloop else 0"))]
cr = mk(c, constantCHOP, 'clock_rates', X + 275, -550)
cr.seq.const.numBlocks = len(rates)
for i, (n, v) in enumerate(rates):
    setp(cr, **{'const%dname' % i: n, 'const%dvalue' % i: v})
mk(c, speedCHOP, 'clock', X + 450, -550, ['clock_rates'])
mk(c, nullCHOP, 'null_clock', X + 625, -550, ['clock'])

CAM = "(parent().par.Camera.eval() or op('cameraViewport'))"
mk(c, objectCHOP, 'cam_pos', X + 450, -700, target=E(CAM), compute='transform', translate=True, rotate=False)

mk(c, rampTOP, 'ramp_palette', X + 275, -850, outputresolution='custom', resolutionw=256, resolutionh=1, type='horizontal')
keys = c.op('ramp_palette').par.dat.eval()
if keys is not None:
    keys.text = ('pos\tr\tg\tb\ta\n0\t1\t0\t0\t1\n0.268\t1\t0.744\t0.268\t1\n0.485\t0.0102\t0.681\t0.139\t1\n'
                 '0.767\t0\t0.6\t1\t1\n0.914\t0.783\t0\t1\t1\n1\t1\t0\t0\t1\n')
mk(c, selectTOP, 'select_palette', X + 450, -850,
   top=E("parent().par.Colorpalletetop.eval() or (parent().par.Image.eval() if parent().par.Colormode == 'image' else None) "
         "or op('ramp_palette')"))
mk(c, selectTOP, 'select_guide', X + 450, -1000,
   top=E("parent().par.Image.eval() or parent().par.Colorpalletetop.eval() or op('ramp_palette')"))

uniforms = [
    ('uTex', [B(R + '.Loaded'), E("parent().par.Sortmode.menuIndex"),
              E("parent().par.Seed + (int(%s) if parent().par.Randomloop else 0)" % (CLK % 'shuffle')),
              E("%s if parent().par.Cyclespeed else 0" % (CLK % 'cycle'))]),
    ('uSort', [B(R + '.Offset'), B(R + '.Repeat'), B(R + '.Steps'), B(R + '.Jitter')]),
    ('uSort2', [B(R + '.Texrangex'), B(R + '.Texrangey'), B(R + '.Sortauto'), B(R + '.Cyclephase')]),
    ('uSortR', [B(R + '.Sortrangex'), B(R + '.Sortrangey'), B(R + '.Sortnoisefreq'),
               E("%s if parent().par.Sortmode == 'noise' and parent().par.Sortnoisespeed else 0" % (CLK % 'sortnoise'))]),
    ('uImg', [E("parent().par.Imagemap.menuIndex"), E("parent().par.Imagematch.menuIndex"), B(R + '.Imagestretch'), 0]),
    ('uScale', [B(R + '.Scalesize'), B(R + '.Sizevariance'), B(R + '.Stretchx'), B(R + '.Stretchy')]),
    ('uScl2', [E("parent().par.Scaleby.menuIndex"), B(R + '.Scaleauto'), B(R + '.Scalerangex'), B(R + '.Scalerangey')]),
    ('uScl3', [B(R + '.Scaleoutx'), B(R + '.Scaleouty'),
               E("parent().par.Wavelength.eval() if parent().par.Scaleby == 'wave' else parent().par.Scalefreq.eval()"),
               E("%s if parent().par.Scaleby in ('noise', 'wave') and parent().par.Scalespeed else 0" % (CLK % 'scale'))]),
    ('uRev', [B(R + '.Reveal'), E("parent().par.Revealby.menuIndex"), B(R + '.Revealsoft'), B(R + '.Revealinvert')]),
    ('uRot', [E("parent().par.Facing.menuIndex"), B(R + '.Randomrotate'), E("%s if parent().par.Spin else 0" % (CLK % 'spin')), B(R + '.Spinrandomdir')]),
    ('uRot2', [E("0 if parent().par.Rotateattr == '_none' else parent().par.Rotateamount.eval()"), B(R + '.Rotateauto'),
               B(R + '.Rotaterangex'), B(R + '.Rotaterangey')]),
    ('uRot3', [B(R + '.Tilt'), B(R + '.Pushout'), 0, 0]),
    ('uCam', [E("op('cam_pos')['tx']"), E("op('cam_pos')['ty']"), E("op('cam_pos')['tz']"), 0]),
    ('uPos', [B(R + '.Translatex'), B(R + '.Translatey'), B(R + '.Translatez'), B(R + '.Posjitter')]),
    ('uPos2', [B(R + '.Drift'), B(R + '.Driftfreq'), E("%s if parent().par.Drift > 0 else 0" % (CLK % 'drift')), 0]),
    ('uCull', [B(R + '.Density'), E("parent().par.Cullmode.menuIndex"), B(R + '.Cullthreshold'), 0]),
    ('uCol', [E("parent().par.Colormode.menuIndex"), B(R + '.Tint'), B(R + '.Opacity'), 0]),
    ('uTint', [B(R + '.Tintcolorr'), B(R + '.Tintcolorg'), B(R + '.Tintcolorb'), B(R + '.Tintcolora')]),
]
gp.seq.vec.numBlocks = len(uniforms)
for i, (n, vals) in enumerate(uniforms):
    setp(gp, **{'vec%dname' % i: n, 'vec%dtype' % i: 'vec4'})
    for j, v in enumerate(vals):
        setp(gp, **{'vec%dvalue%s' % (i, 'xyzw'[j]): v})
gp.seq.sampler.numBlocks = 2
setp(gp, sampler0name='sPalette', sampler0top='select_palette', sampler1name='sGuide', sampler1top='select_guide')
gp.seq.array.numBlocks = 1
setp(gp, array0name='uInfo', array0type='vec4', array0chop='textures/info_chop', array0arraytype='texturebuffer')

mk(c, sortPOP, 'sort_depth', X + 800, 0, ['glsl_attribs'], ptmethod='prox', pointrev=True,
   pointproxx=E("op('cam_pos')['tx']"), pointproxy=E("op('cam_pos')['ty']"), pointproxz=E("op('cam_pos')['tz']"))
c.op('sort_depth').bypass = False
c.op('sort_depth').par.bypass.expr = "parent().par.Blend != 'soft'"
mk(c, nullPOP, 'null_attribs', X + 975, 0, ['sort_depth'])
mk(c, outPOP, 'out_points', X + 1150, 150, ['null_attribs'])
c.op('out_points').comment = 'The points with their instance attributes, for your own render.'

# ---------------------------------------------------------------- shape + geometry
mk(c, rectanglePOP, 'demo_shape', X + 625, -1150)
c.op('demo_shape').comment = 'Default shape (a unit quad), used when nothing is wired into input 2.'
mk(c, inPOP, 'in_shape', X + 800, -1150, ['demo_shape'])
mk(c, nullPOP, 'null_shape', X + 975, -1150, ['in_shape'])

mat = mk(c, constantMAT, 'mat_instances', X + 1150, -1000, blending=True, alphatest=E("parent().par.Blend == 'cutout'"),
         alphafunc='greater', alphathreshold=B(R + '.Alphathreshold'), applypointcolor=True, cullface='neither',
         depthwriting=E("parent().par.Blend == 'cutout'"),
         destblend=E("'one' if parent().par.Blend == 'add' else 'omsa'"))

geo = mk(c, geometryCOMP, 'geo_instances', X + 1150, -1150)
for ch in list(geo.children):
    ch.destroy()
gi = geo.create(inPOP, 'in1')
go = geo.create(outPOP, 'out1')
go.inputConnectors[0].connect(gi)
go.nodeX = 200
go.display = go.render = True
geo.inputConnectors[0].connect(c.op('null_shape'))
I = "parent.Instancer.op('null_attribs')"
setp(geo, material=E("parent.Instancer.op('mat_instances')"), instancing=True, instanceop=E(I),
     instanceactive='Iactive',
     instancetx='P(0)', instancety='P(1)', instancetz='P(2)',
     instancesx='Iscale(0)', instancesy='Iscale(1)', instancesz='Iscale(2)',
     instancerz='Irot',
     instancerottoop=E(I), instancerottox='Facing(0)', instancerottoy='Facing(1)', instancerottoz='Facing(2)',
     instancerotupop=E(I), instancerotupx='Upd(0)', instancerotupy='Upd(1)', instancerotupz='Upd(2)',
     instancerottoforward='posz', instancerottoorder='rotaterotto',
     instancecolorop=E(I), instancecolormode='replace',
     instancer='Icolor(0)', instanceg='Icolor(1)', instanceb='Icolor(2)', instancea='Icolor(3)',
     instancetexmode='transform', instancetexcoordop=E(I), instancew='TexW',
     instancetexs=E("parent.Instancer.op('textures/null_array')"), instancetexfilter='mipmaplinear',
     instancetexextendu='zero', instancetexextendv='zero')

# ---------------------------------------------------------------- camera + render
src_cam = op.TDTox.op('cameraViewport') if op.TDTox else None
if src_cam is not None:
    cam = c.copy(src_cam, name='cameraViewport')
    cam.par.clone.expr = "op.TDTox.op('cameraViewport')"
    cam.par.enablecloning = True
else:
    cam = c.create(cameraCOMP, 'cameraViewport')
    cam.par.tz = 6
cam.nodeX, cam.nodeY = X + 1350, -850
cam.par.render = False
cam.par.fov = 45
if hasattr(cam.par, 'Reset'):
    cam.par.Reset.pulse()

mk(c, renderTOP, 'render1', X + 1500, -1150, camera=E(CAM), geometry='geo_instances',
   outputresolution='custom', resolutionw=B(R + '.Resolutionw'), resolutionh=B(R + '.Resolutionh'),
   outputaspect='resolution', antialias=B(R + '.Antialias'),
   bgcolorr=B(R + '.Backgroundcolorr'), bgcolorg=B(R + '.Backgroundcolorg'), bgcolorb=B(R + '.Backgroundcolorb'),
   bgcolora=B(R + '.Backgroundalpha'), format='rgba16float')
mk(c, nullTOP, 'null_out', X + 1675, -1150, ['render1'])
mk(c, outTOP, 'out1', X + 1850, -1150, ['null_out'])
mk(c, outTOP, 'out_textures', X + 1850, -1350, [tx])
c.op('out_textures').comment = 'The texture array (one layer per texture).'

# ---------------------------------------------------------------- start
c.par.ext0object = "op('./InstancerExt').module.InstancerExt(me)"
c.par.ext0promote = True
c.par.ext0name = ''
c.initializeExtensions()
c.UpdateShader()
finish(c, (0.3, 0.45, 0.3))
print('built', c.path)
