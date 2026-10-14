# Builds the Paint component. Run inside TouchDesigner:
#   exec(open('/Users/davidmayzenberg/Code/td-components/tools/build_paint.py').read())
# Creates /project1/paint (replacing it if it exists). Set TARGET / NAME / POS before exec to build elsewhere.

exec(open('/Users/davidmayzenberg/Code/td-components/tools/common.py', encoding='utf-8').read())

TARGET = globals().get('TARGET', '/project1')
NAME = globals().get('NAME', 'paint')
POS = globals().get('POS', (300, -700))

c = fresh_comp(op(TARGET), NAME, *POS)
c.par.parentshortcut = 'Paint'

# ---------------------------------------------------------------- parameters
P = Pars(c, 'Stroke')
P.float('Kernelsize', 'Brush Size', 27.3, 1, 60, clamp=(1, 200), help='Kuwahara radius in pixels.')
P.float('Alpha', 'Stroke Stretch', 0.733, 0.05, 4, clamp=(0.01, None),
        help='Anisotropy. Low = long strokes along edges, high = round dabs.')
P.float('Sharpness', 'Sharpness', 32, 0, 32, clamp=(0, 32),
        help='How hard the flattest sector wins. 32 = hard pick (flat paint), lower = softer blend.')
P.float('Smoothing', 'Flow Smoothing', 2, 0, 16, clamp=(0, None),
        help='Blur of the stroke direction field. Higher = longer, calmer strokes.')
P.section().float('Processscale', 'Process Scale', 0.5, 0.25, 1, clamp=(0.1, 1),
                  help='Paint at a lower resolution for speed. The brush size scales with it.')
P.int('Quality', 'Quality', 16, 4, 32, clamp=(2, 64), help='Radial samples per sector (cost).')

P = Pars(c, 'Color and Paper')
P.int('Numcolors', 'Tone Steps', 2, 0, 8, clamp=(0, 32), help='Brightness steps. 0 or 1 = off.')
P.float('Shadow', 'Shadow Level', 0.2, 0, 1)
P.float('Highlight', 'Highlight Level', 0.7, 0, 1)
P.float('Saturation', 'Saturation', 3.0, 0, 4)
P.toggle('Tonemap', 'Tone Map (ACES)', True)
P.float('Exposure', 'Exposure', 1.0, 0, 3)
P.float('Gamma', 'Gamma', 1.0, 0.2, 3)
P.section().float('Paperstrength', 'Paper Strength', 0.1, 0, 1)
P.float('Paperscale', 'Paper Scale', 1.0, 0.1, 4)
P.float('Papercontrast', 'Paper Contrast', 1.9, 0, 4)
P.file('Paperfile', 'Paper Image', help='Optional: your own paper texture. Empty = built-in.')
P.float('Paperreveal', 'Paper Reveal', 0.0, 0, 1, help='Brightness above which paint fades to bare paper (0 = off).')
P.float('Revealsoft', 'Reveal Softness', 0.05, 0.001, 0.5)
P.rgb('Papercolor', 'Paper Color', (0.95, 0.93, 0.88))
P.section().rgb('Bgcolor', 'Background', (1, 1, 1), help='The input is composited over this first.')
P.float('Mix', 'Mix Original', 0.0, 0, 1)

P = Pars(c, 'Outline')
P.float('Outline', 'Outline', 0.0, 0, 1, help='Ink line along strong edges.')
P.float('Outlinethreshold', 'Threshold', 0.08, 0, 0.5)
P.float('Outlinewidth', 'Softness', 0.08, 0.001, 0.5)
P.rgb('Outlinecolor', 'Color', (0.08, 0.06, 0.05))

P = Pars(c, 'Mask')
P.toggle('Mask', 'Use Mask', False, help='Input 2: the alpha of this TOP cuts the result out.')
P.toggle('Maskinvert', 'Invert Mask', False)

about_page(c, 'Paint', 'Painterly filter for TOPs: anisotropic Kuwahara strokes, tone steps, paper, outline, mask.')

R = "parent().par"

# ---------------------------------------------------------------- inputs
mk(c, moviefileinTOP, 'demo_image', -400, 0, file=E("app.samplesFolder + '/Map/Mettler.1.jpg'"))
c.op('demo_image').comment = 'Default input from the TouchDesigner samples, shown when nothing is wired in.'
mk(c, inTOP, 'in1', -200, 0, ['demo_image'])
mk(c, constantTOP, 'constant_white', -400, -250, colorr=1, colorg=1, colorb=1, alpha=1,
   outputresolution='custom', resolutionw=8, resolutionh=8)
mk(c, inTOP, 'mask', -200, -250, ['constant_white'])
mk(c, constantTOP, 'constant_bg', 0, 0, ['in1'], operand='over', swaporder=True, colorr=B(R + '.Bgcolorr'),
   colorg=B(R + '.Bgcolorg'), colorb=B(R + '.Bgcolorb'), alpha=1)
mk(c, nullTOP, 'null_src', 175, 0, ['constant_bg'])
mk(c, resolutionTOP, 'res_process', 350, 0, ['null_src'], outputresolution='custom',
   resolutionw=E("max(1, int(op('null_src').width * parent().par.Processscale))"),
   resolutionh=E("max(1, int(op('null_src').height * parent().par.Processscale))"), outputaspect='resolution')

# ---------------------------------------------------------------- strokes
glsl(c, 'glsl_tensor', 525, 0, 'paint_tensor.glsl', ['res_process'], format='rgba16float',
     inputextenduv='mirror')
mk(c, blurTOP, 'blur_tensor', 700, 0, ['glsl_tensor'], type='gaussian',
   size=E("parent().par.Smoothing * parent().par.Processscale"))
glsl(c, 'glsl_kuwahara', 875, 150, 'paint_kuwahara.glsl', ['blur_tensor', 'res_process'],
     uniforms=[('uKernel', [E("parent().par.Kernelsize * parent().par.Processscale"), B(R + '.Alpha'),
                            B(R + '.Sharpness'), B(R + '.Quality')])],
     format='rgba16float', inputextenduv='mirror')

# ---------------------------------------------------------------- paper
paper = mk(c, moviefileinTOP, 'paper_tex', 700, -400)
lock_image(paper, REPO + '/assets/paint/paper.png')
mk(c, moviefileinTOP, 'paper_user', 700, -550, file=B(R + '.Paperfile'), format='mono8fixed')
mk(c, switchTOP, 'switch_paper', 875, -450, ['paper_tex', 'paper_user'],
   index=E("1 if parent().par.Paperfile.eval() else 0"))

# ---------------------------------------------------------------- grade
glsl(c, 'glsl_grade', 1100, 0, 'paint_grade.glsl',
     ['glsl_kuwahara', 'switch_paper', 'blur_tensor', 'null_src', 'mask'],
     uniforms=[
         ('uTone', [B(R + '.Numcolors'), B(R + '.Shadow'), B(R + '.Highlight'), B(R + '.Saturation')]),
         ('uGrade', [B(R + '.Tonemap'), B(R + '.Exposure'), B(R + '.Mix'), B(R + '.Gamma')]),
         ('uPaper', [B(R + '.Paperstrength'), B(R + '.Paperscale'), B(R + '.Papercontrast'), B(R + '.Paperreveal')]),
         ('uOutline', [B(R + '.Outline'), B(R + '.Outlinewidth'), B(R + '.Outlinethreshold'), B(R + '.Revealsoft')]),
         ('uMask', [B(R + '.Mask'), B(R + '.Maskinvert'), 1, 0]),
         ('uOutlineColor', [B(R + '.Outlinecolorr'), B(R + '.Outlinecolorg'), B(R + '.Outlinecolorb'), 1]),
         ('uPaperColor', [B(R + '.Papercolorr'), B(R + '.Papercolorg'), B(R + '.Papercolorb'), 1]),
     ],
     outputresolution='custom', resolutionw=E("op('null_src').width"), resolutionh=E("op('null_src').height"),
     outputaspect='resolution', format='rgba8fixed', inputextenduv='mirror')
mk(c, nullTOP, 'null_out', 1275, 0, ['glsl_grade'])
mk(c, outTOP, 'out1', 1450, 0, ['null_out'])

finish(c, (0.45, 0.3, 0.45))
print('built', c.path)
