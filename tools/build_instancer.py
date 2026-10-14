# Builds the Texture Instancer component. Run inside TouchDesigner:
#   exec(open('/Users/davidmayzenberg/Code/td-components/tools/build_instancer.py').read())
# Creates /project1/texture_instancer2 by default (the old COMP is texture_instancer).
# The orbit camera is TouchDesigner's own cameraViewport (/sys/TDTox/cameraViewport), cloned like the palette does.

exec(open('/Users/davidmayzenberg/Code/td-components/tools/common.py', encoding='utf-8').read())

TARGET = globals().get('TARGET', '/project1')
NAME = globals().get('NAME', 'texture_instancer2')
POS = globals().get('POS', (900, -700))

c = fresh_comp(op(TARGET), NAME, *POS)
c.par.parentshortcut = 'Instancer'

# ---------------------------------------------------------------- parameters
P = Pars(c, 'Textures')
P.file('Texturefolder', 'Texture Folder', folder=True, help='Images or movies. Empty = the built-in shapes.')
P.int('Maximumtextures', 'Maximum Textures', 256, 1, 1024, clamp=(1, 2048))
P.int('Cellsize', 'Texture Size', 256, 32, 1024, clamp=(8, 4096), help='Each texture is fitted into a square of this size.')
P.toggle('Animate', 'Play Movies / GIFs', False)
P.pulse('Updatereset', 'Reload Folder')
P.section().toggle('Blending', 'Blending', True)
P.float('Alphathreshold', 'Alpha Threshold', 0.6, 0, 1, help='Pixels below this alpha are discarded.')
P.section().menu('Edge', 'Edges', ['off', 'only', 'over'], ['Off', 'Edges Only', 'Edges Over Texture'])
P.float('Edgestrength', 'Edge Strength', 1.27, 0, 5)
P.rgba('Edgecolor', 'Edge Color', (1, 1, 1, 1))

P = Pars(c, 'Sorting')
P.menu('Sortmode', 'Texture Order', ['sequential', 'random', 'x', 'y', 'z', 'centre'],
       ['Sequential (point number)', 'Random', 'Along X', 'Along Y', 'Along Z', 'From Centre'], default='random')
P.int('Seed', 'Seed', 0, 0, 100)
P.pulse('Pulse', 'Shuffle', help='New random order (bumps the seed).')
P.toggle('Randomloop', 'Auto Shuffle', False)
P.float('Loopinterval', 'Shuffle Every (s)', 1.0, 0.05, 10, clamp=(0.01, None))
P.float('Cyclespeed', 'Cycle Speed', 0.0, 0, 30, help='Textures advanced per second.')

P = Pars(c, 'Scale and animation')
P.float('Scalesize', 'Size', 0.25, 0, 2, clamp=(0, None), help='Instance size in point units.')
P.menu('Scalemode', 'Size Mode', ['constant', 'noise', 'wave'], ['Constant', 'Noise', 'Wave'], default='noise')
P.float('Sizevariance', 'Random Variance', 0.0, 0, 1)
P.float('Noisefreq', 'Noise Frequency', 0.8, 0, 5)
P.float('Noisespeed', 'Noise Speed', 0.3, 0, 3)
P.float('Rampspeed', 'Wave Speed', 0.98, -5, 5, help='Cycles per second.')
P.menu('Waveaxis', 'Wave Axis', ['x', 'y', 'z', 'radial'], ['X', 'Y', 'Z', 'Radial'], default='radial')
P.float('Wavelength', 'Wavelength', 0.5, 0.05, 2)
P.float('Wavemin', 'Wave Minimum', 0.1, 0, 1)
P.section().float('Drift', 'Drift', 0.0, 0, 1, help='Points wander with noise (point units).')
P.float('Driftfreq', 'Drift Frequency', 0.5, 0, 5)
P.section().toggle('Facecamera', 'Face Camera', True)
P.float('Randomrotate', 'Random Rotate', 0, 0, 180)
P.float('Spin', 'Spin', 0, -180, 180, help='Degrees per second (alternating direction).')

P = Pars(c, 'Color')
P.menu('Colormode', 'Color Mode', ['off', 'random', 'pertexture', 'image'],
       ['Off', 'Random from Palette', 'One per Texture', 'Image at Point XY'])
P.top('Colorpalletetop', 'Palette / Image TOP', help='Empty = built-in rainbow ramp.')
P.float('Tint', 'Tint Amount', 1.0, 0, 1)
P.toggle('Pointcolor', 'Use Point Color', False, help='Multiply by the points\' own Color attribute.')

P = Pars(c, 'Scene')
P.wh('Resolution', 'Resolution', (1920, 1080))
P.rgb('Backgroundcolor', 'Background Color', (0, 0, 0))
P.float('Backgroundalpha', 'Background Alpha', 1.0, 0, 1)
P.comp('Camera', 'Camera', help='Optional: render with your own camera. Empty = the built-in orbit camera.')
P.menu('Antialias', 'Anti-Alias', ['aa1', 'aa2', 'aa4', 'aa8'], ['1x', '2x', '4x', '8x'], default='aa4')

about_page(c, 'Texture Instancer', 'Instances a folder of textures on POP points: order, size, drift, spin, colour, face-camera.')

R = "parent().par"

# ---------------------------------------------------------------- textures
tx = fresh_comp(c, 'textures', 0, 600)
tx.par.parentshortcut = 'Textures'
fd = mk(tx, folderDAT, 'folder_files', 0, 0, rootfolder=E("parent.Instancer.par.Texturefolder.eval()"),
        imageextensions=True, movieextensions=True, pathcol=True, namecol=True)
fd.par.allextensions = False
mk(tx, nullDAT, 'files', 175, 0, ['folder_files'])
mf = mk(tx, moviefileinTOP, 'tex_master', 0, -200, hwdecode=False,
        file=E("parent.Textures.op('files')[me.digits, 'path'] if me.digits is not None else ''"),
        play=E("parent.Instancer.par.Animate"),
        playmode=E("'locked' if parent.Instancer.par.Animate else 'specify'"), index=0)
mf.par.alwaysloadinitial = True
mf.bypass = False
mf.display = False
mk(tx, replicatorCOMP, 'replicator1', 175, -200, method='bynum',
   numreplicants=E("min(parent.Textures.op('files').numRows - 1, parent.Instancer.par.Maximumtextures)"),
   master='tex_master', opprefix='tex', layout='grid', domaxops=False)
tx.op('replicator1').par.layoutorigin1 = 400
tx.op('replicator1').par.layoutorigin2 = 0

# built-in textures, used when the folder is empty
demo = [
    ('demo0', circleTOP, dict(radiusx=0.42, radiusy=0.42, radiusunit='fraction', bgalpha=0)),
    ('demo1', circleTOP, dict(radiusx=0.42, radiusy=0.42, radiusunit='fraction', borderwidth=0.08,
                              borderwidthunit='fraction', fillalpha=0, bgalpha=0)),
    ('demo2', rectangleTOP, dict(sizex=0.7, sizey=0.7, bgalpha=0)),
    ('demo3', textTOP, dict(text='✦', fontsizex=200, bgalpha=0)),
]
for i, (n, t, kw) in enumerate(demo):
    o = mk(tx, t, n, -400, -400 - 120 * i, outputresolution='custom', resolutionw=256, resolutionh=256)
    for k, v in kw.items():
        try:
            setp(o, **{k: v})
        except Exception:
            pass

mk(tx, constantCHOP, 'constant_count', 0, -650, const0name='count',
   const0value=E("len(parent.Textures.findChildren(name='tex[0-9]*', depth=1, type=TOP)) "
                 "if parent.Textures.op('files').numRows > 1 else 4"))
mk(tx, nullCHOP, 'null_count', 175, -650, ['constant_count'])
COUNT = "parent.Textures.op('null_count')['count']"
GRID = "math.ceil(math.sqrt(max(%s, 1)))" % COUNT
ROWS = "math.ceil(max(%s, 1) / %s)" % (COUNT, GRID)
lay = mk(tx, layoutTOP, 'layout_atlas', 400, -650, align='gridrows', fit='fitbest', numcols=E(GRID), numrows=E(ROWS),
         outputresolution='custom', resolutionw=E("int(%s * parent.Instancer.par.Cellsize)" % GRID),
         resolutionh=E("int(%s * parent.Instancer.par.Cellsize)" % ROWS),
         bgcolorr=0, bgcolorg=0, bgcolorb=0, bgcolora=0)
lay.par.tops.expr = ("' '.join('tex%d' % (i + 1) for i in range(int(op('null_count')['count']))) "
                     "if op('files').numRows > 1 else 'demo0 demo1 demo2 demo3'")
mk(tx, edgeTOP, 'edge1', 575, -800, ['layout_atlas'], strength=B("parent.Instancer.par.Edgestrength"),
   edgecolorr=B("parent.Instancer.par.Edgecolorr"), edgecolorg=B("parent.Instancer.par.Edgecolorg"),
   edgecolorb=B("parent.Instancer.par.Edgecolorb"), edgecolora=B("parent.Instancer.par.Edgecolora"))
mk(tx, compositeTOP, 'comp_edge', 750, -800, ['edge1', 'layout_atlas'], operand='over')
mk(tx, switchTOP, 'switch_edge', 925, -650, ['layout_atlas', 'edge1', 'comp_edge'],
   index=E("parent.Instancer.par.Edge.menuIndex"))
glsl(tx, 'glsl_array', 1100, -650, 'instancer_array.glsl', ['switch_edge'],
     uniforms=[('uGrid', [E(GRID), E(ROWS), 0, 0])],
     type='texture2darray', depth='custom', customdepth=E("int(max(%s, 1))" % COUNT),
     outputresolution='custom', resolutionw=B("parent.Instancer.par.Cellsize"),
     resolutionh=B("parent.Instancer.par.Cellsize"), format='rgba8fixed')
mk(tx, nullTOP, 'null_array', 1275, -650, ['glsl_array'])
mk(tx, outTOP, 'out_array', 1450, -650, ['null_array'])

# ---------------------------------------------------------------- points
X = 0
mk(c, spherePOP, 'demo_points', X - 400, 0, type='geodesic', freq=5, radx=1.6, rady=1.6, radz=1.6)
try:
    c.op('demo_points').par.geodesictype = 'point'
except Exception:
    pass
c.op('demo_points').comment = 'Default points (a geodesic sphere), used when nothing is wired into input 1.'
mk(c, inPOP, 'in_points', X - 200, 0, ['demo_points'])
ap = mk(c, attributePOP, 'attr_color', X, 0, ['in_points'], overrideifexists=False, notificationifexists='ignore')
ap.par.attr0name = 'color'
for k, v in enumerate((1, 1, 1, 1)):
    try:
        setattr(ap.par, 'attr0value%d' % k, v)
    except Exception:
        pass
mk(c, analyzePOP, 'analyze_bounds', X + 175, -150, ['attr_color'], inputattrs='P', min=True, max=True, avg=False)

mk(c, rampTOP, 'ramp_palette', X, -350, outputresolution='custom', resolutionw=256, resolutionh=1, type='horizontal')
keys = c.op('ramp_palette').par.dat.eval()
if keys is not None:
    keys.text = ('pos\tr\tg\tb\ta\n0\t1\t0\t0\t1\n0.268\t1\t0.744\t0.268\t1\n0.485\t0.0102\t0.681\t0.139\t1\n'
                 '0.767\t0\t0.6\t1\t1\n0.914\t0.783\t0\t1\t1\n1\t1\t0\t0\t1\n')
mk(c, selectTOP, 'select_palette', X + 175, -350,
   top=E("parent().par.Colorpalletetop.eval() or op('ramp_palette')"))

gp = mk(c, glslPOP, 'glsl_attribs', X + 400, 0, ['attr_color', 'analyze_bounds'])
cd = c.op('glsl_attribs_compute')
cd.text = src('glsl', 'instancer_attribs.glsl')
cd.nodeX, cd.nodeY = X + 400, -150
attrs = [('TexW', 'float', 1), ('Iscale', 'float', 1), ('Icolor', 'color', 4), ('Irot', 'float', 1), ('Facing', 'dir', 3)]
gp.seq.attr.numBlocks = len(attrs)
for i, (n, t, nc) in enumerate(attrs):
    setp(gp, **{'attr%dname' % i: 'custom', 'attr%dcustomname' % i: n, 'attr%dtype' % i: t})
    try:
        setattr(gp.par, 'attr%dnumcomps' % i, str(nc))
    except Exception:
        setattr(gp.par, 'attr%dnumcomps' % i, nc)
gp.par.outputattrs = 'P TexW Iscale Icolor Irot Facing'
CAM = "(parent().par.Camera.eval() or op('cameraViewport'))"
uniforms = [
    ('uTex', [E(COUNT.replace('parent.Textures', "op('textures')")),
              E("parent().par.Sortmode.menuIndex"),
              E("parent().par.Seed + (int(me.time.seconds / max(parent().par.Loopinterval.eval(), 0.01)) if parent().par.Randomloop else 0)"),
              E("int(me.time.seconds * parent().par.Cyclespeed)")]),
    ('uScale', [E("parent().par.Scalemode.menuIndex"), B(R + '.Scalesize'), B(R + '.Sizevariance'), B(R + '.Noisefreq')]),
    ('uAnim', [E("me.time.seconds"), B(R + '.Noisespeed'), B(R + '.Drift'), B(R + '.Driftfreq')]),
    ('uWave', [E("parent().par.Waveaxis.menuIndex"), E("me.time.seconds * parent().par.Rampspeed"),
               B(R + '.Wavelength'), B(R + '.Wavemin')]),
    ('uColor', [E("parent().par.Colormode.menuIndex"), B(R + '.Tint'), B(R + '.Seed'), B(R + '.Pointcolor')]),
    ('uCam', [E(CAM + ".worldTransform.decompose()[2][0]"), E(CAM + ".worldTransform.decompose()[2][1]"),
              E(CAM + ".worldTransform.decompose()[2][2]"), B(R + '.Facecamera')]),
    ('uRot', [B(R + '.Randomrotate'), B(R + '.Spin'), B(R + '.Seed'), 0]),
]
gp.seq.vec.numBlocks = len(uniforms)
for i, (n, vals) in enumerate(uniforms):
    setp(gp, **{'vec%dname' % i: n, 'vec%dtype' % i: 'vec4'})
    for j, v in enumerate(vals):
        setp(gp, **{'vec%dvalue%s' % (i, 'xyzw'[j]): v})
gp.seq.sampler.numBlocks = 1
gp.par.sampler0name = 'sPalette'
gp.par.sampler0top = 'select_palette'
mk(c, nullPOP, 'null_attribs', X + 575, 0, ['glsl_attribs'])
mk(c, outPOP, 'out_points', X + 750, 150, ['null_attribs'])
c.op('out_points').comment = 'The points with their instance attributes, for your own render.'

# ---------------------------------------------------------------- shape + geometry
mk(c, rectanglePOP, 'demo_shape', X + 175, -600)
c.op('demo_shape').comment = 'Default shape (a unit quad), used when nothing is wired into input 2.'
mk(c, inPOP, 'in_shape', X + 350, -600, ['demo_shape'])
mk(c, nullPOP, 'null_shape', X + 525, -600, ['in_shape'])

mat = mk(c, constantMAT, 'mat_instances', X + 750, -450, blending=B(R + '.Blending'), alphatest=True,
         alphafunc='greater', alphathreshold=B(R + '.Alphathreshold'), applypointcolor=True, cullface='neither',
         depthwriting=E("not parent().par.Blending"))

geo = mk(c, geometryCOMP, 'geo_instances', X + 750, -600)
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
     instancetx='P(0)', instancety='P(1)', instancetz='P(2)',
     instancesx='Iscale', instancesy='Iscale', instancesz='Iscale',
     instancerz='Irot',
     instancerottoop=E("%s if parent.Instancer.par.Facecamera else None" % I),
     instancerottox='Facing(0)', instancerottoy='Facing(1)', instancerottoz='Facing(2)',
     instancerottoforward='posz', instancerottoorder='rotaterotto',
     instancecolorop=E(I), instancecolormode='replace',
     instancer='Icolor(0)', instanceg='Icolor(1)', instanceb='Icolor(2)', instancea='Icolor(3)',
     instancetexmode='transform', instancetexcoordop=E(I), instancew='TexW',
     instancetexs=E("parent.Instancer.op('textures/out_array')"), instancetexfilter='mipmaplinear')

# ---------------------------------------------------------------- camera + render
src_cam = op.TDTox.op('cameraViewport') if op.TDTox else None
if src_cam is not None:
    cam = c.copy(src_cam, name='cameraViewport')
    cam.par.clone.expr = "op.TDTox.op('cameraViewport')"
    cam.par.enablecloning = True
else:
    cam = c.create(cameraCOMP, 'cameraViewport')
    cam.par.tz = 6
cam.nodeX, cam.nodeY = X + 950, -300
cam.par.render = False
cam.par.fov = 45
if hasattr(cam.par, 'Reset'):
    cam.par.Reset.pulse()

mk(c, renderTOP, 'render1', X + 1100, -600, camera=E(CAM), geometry='geo_instances',
   outputresolution='custom', resolutionw=B(R + '.Resolutionw'), resolutionh=B(R + '.Resolutionh'),
   outputaspect='resolution', antialias=B(R + '.Antialias'),
   bgcolorr=B(R + '.Backgroundcolorr'), bgcolorg=B(R + '.Backgroundcolorg'), bgcolorb=B(R + '.Backgroundcolorb'),
   bgcolora=B(R + '.Backgroundalpha'), format='rgba16float')
mk(c, nullTOP, 'null_out', X + 1275, -600, ['render1'])
mk(c, outTOP, 'out1', X + 1450, -600, ['null_out'])
mk(c, outTOP, 'out_textures', X + 1450, -800, [tx])
c.op('out_textures').comment = 'The texture array (one layer per texture).'

# ---------------------------------------------------------------- pulses
pe = mk(c, parameterexecuteDAT, 'parexec_pulses', X + 400, 400, pars='Pulse Updatereset', valuechange=False, onpulse=True)
pe.par.op.expr = 'parent()'
pe.text = '''# Shuffle bumps the seed; Reload Folder rescans the folder and rebuilds the textures.
def onPulse(par):
    c = par.owner
    if par.name == 'Pulse':
        c.par.Seed = c.par.Seed.eval() + 1
    elif par.name == 'Updatereset':
        t = c.op('textures')
        t.op('folder_files').par.refreshpulse.pulse()
        t.op('replicator1').par.recreateall.pulse()
    return
'''

finish(c, (0.3, 0.45, 0.3))
print('built', c.path)
