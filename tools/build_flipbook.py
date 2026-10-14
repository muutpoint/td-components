# Builds the FlipBook component. Run inside TouchDesigner:
#   exec(open('/Users/davidmayzenberg/Code/td-components/tools/build_flipbook.py').read())
# Creates /project1/flipbook (replacing it if it exists). Set TARGET / NAME before exec to build elsewhere.

exec(open('/Users/davidmayzenberg/Code/td-components/tools/common.py', encoding='utf-8').read())

TARGET = globals().get('TARGET', '/project1')
NAME = globals().get('NAME', 'flipbook')
POS = globals().get('POS', (0, -700))

c = fresh_comp(op(TARGET), NAME, *POS)
c.par.parentshortcut = 'Flipbook'

# ---------------------------------------------------------------- parameters
P = Pars(c, 'Flip Book')
P.toggle('Play', 'Play', True, help='Flip pages. Off holds the current page.')
P.float('Speed', 'Flips per Second', 10, 0.5, 30, clamp=(0.01, None))
P.pulse('Reset', 'Reset', help='Restart from page 0.')
P.section().wh('Resolution', 'Resolution', (1080, 1920))
P.menu('Fit', 'Fit Input', ['fitbest', 'fitoutside', 'fill', 'fithorz', 'fitvert'],
       ['Fit Inside', 'Fit Outside', 'Stretch', 'Fit Width', 'Fit Height'])
P.float('Zoom', 'Zoom', 1.0, 0.25, 3, clamp=(0.01, None))
P.xy('Offset', 'Offset', (0, 0), -0.5, 0.5)
P.section().float('Imagejitter', 'Image Jitter', 0.003, 0, 0.02, help='Offset of the drawing on each page (fraction of the frame).')
P.float('Shake', 'Page Shake', 0.012, 0, 0.05, help='Offset of the sheet on each page.')
P.float('Shakerotate', 'Page Rotate', 0.6, 0, 5, help='Degrees.')
P.float('Shakescale', 'Page Scale', 0.01, 0, 0.1)
P.float('Flicker', 'Flicker', 0.03, 0, 0.2, help='Brightness change per page.')

P = Pars(c, 'Style')
P.menu('Blendmode', 'Blend', ['over', 'multiply', 'darken'], ['Over', 'Multiply (ink)', 'Darken'],
       help='How the drawing sits on the sheet. Over uses the input alpha; Multiply suits opaque footage on white.')
P.toggle('Paper', 'Paper', True)
P.float('Paperstrength', 'Paper Texture', 1.0, 0, 2)
P.float('Paperdisplace', 'Paper Displace', 0.05, 0, 0.2)
P.toggle('Randompaper', 'Random Paper Order', False)
P.rgb('Papercolor', 'Paper Color', (1, 1, 1))
P.section().toggle('Notebook', 'Notebook', True)
P.float('Notebookopacity', 'Notebook Opacity', 0.5, 0, 1)
P.float('Notebookdisplace', 'Notebook Displace', 0.002, 0, 0.02)
P.section().toggle('Grain', 'Grain', True)
P.float('Grainamount', 'Grain Amount', 0.8, 0, 1)
P.float('Grainscale', 'Grain Size', 24, 4, 200, clamp=(1, None), help='Size of the blotches in pixels (detail goes down to ~1 px).')
P.float('Grainspace', 'Grain Density', 0.3, 0, 1, help='How much of the ink is missing.')
P.section().float('Brightness', 'Brightness', 1.0, 0, 2)
P.float('Contrast', 'Contrast', 1.0, 0, 2)
P.rgb('Inkcolor', 'Ink Tint', (1, 1, 1))
P.float('Inktint', 'Ink Tint Amount', 0.0, 0, 1)
P.section().toggle('Pageflipeffect', 'Page Flip Ghost', True)
P.float('Ghostopacity', 'Ghost Opacity', 0.5, 0, 1)
P.float('Ghostfade', 'Ghost Fade', 0.05, 0.01, 0.5, help='Seconds.')
P.float('Ghostrotate', 'Ghost Rotate', 9, -45, 45)
P.xy('Ghostoffset', 'Ghost Offset', (-0.1, -0.01), -0.5, 0.5)
P.toggle('Ghostalternate', 'Alternate Sides', False)

P = Pars(c, 'Blur')
P.int('Preshrink', 'Pre-Shrink', 0, 0, 4, clamp=(0, 6))
P.float('Filtersize', 'Softness', 3, 0, 40, clamp=(0, None), help='Blur of the drawing in pixels.')
P.section().toggle('Lensblur', 'Lens Blur', True)
P.int('Lensblursize', 'Lens Blur Size', 46, 0, 100, clamp=(0, None))
P.float('Vignette', 'Sharp Area', 1.0, 0.1, 2, help='Size of the sharp middle (1 = 60% of the frame).')
P.float('Vignettesoft', 'Falloff', 0.8, 0.05, 2)

P = Pars(c, 'Paper Files')
P.file('Paperatlas', 'Paper Atlas', help='Optional: your own paper atlas image (grid of paper frames). Empty = built-in.')
P.int('Papercols', 'Atlas Columns', 5, 1, 10, clamp=(1, None))
P.int('Paperrows', 'Atlas Rows', 2, 1, 10, clamp=(1, None))
P.int('Papercount', 'Paper Frames', 10, 1, 100, clamp=(1, None))
P.file('Notebookfile', 'Notebook Image', help='Optional: your own notebook/background sheet. Empty = built-in.')

about_page(c, 'FlipBook', 'Turns a TOP into a hand-flipped book: stop-motion timing, paper, notebook, grain, page-flip ghost, lens blur.')

R = "parent().par"

# ---------------------------------------------------------------- input
X = 0
mk(c, circleTOP, 'demo_ball', X - 200, -300, outputresolution='custom', resolutionw=540, resolutionh=960,
   radiusunit='fractionaspect', radiusx=E("0.18 * (1 + 0.15 * (1 - abs(math.sin(me.time.seconds * 2.5))))"),
   radiusy=E("0.18 * (1 - 0.15 * (1 - abs(math.sin(me.time.seconds * 2.5))))"),
   centerunit='fractionaspect', centery=E("-0.3 + 0.6 * abs(math.sin(me.time.seconds * 2.5))"),
   fillcolorr=0.05, fillcolorg=0.05, fillcolorb=0.08, bgalpha=0)
c.op('demo_ball').comment = 'Default input: a bouncing ball, shown when nothing is wired in.'
mk(c, inTOP, 'in1', X, -300, ['demo_ball'])
mk(c, fitTOP, 'fit_input', X + 175, -300, ['in1'], fit=B(R + '.Fit'), outputresolution='custom',
   resolutionw=B(R + '.Resolutionw'), resolutionh=B(R + '.Resolutionh'), outputaspect='resolution')
mk(c, transformTOP, 'transform_zoom', X + 350, -300, ['fit_input'], sx=B(R + '.Zoom'), sy=B(R + '.Zoom'),
   tx=B(R + '.Offsetx'), ty=B(R + '.Offsety'), extend='zero')

# ---------------------------------------------------------------- clock
mk(c, constantCHOP, 'constant_rate', X, 0, const0name='page',
   const0value=E("parent().par.Speed * parent().par.Play"))
mk(c, speedCHOP, 'speed_clock', X + 175, 0, ['constant_rate'], resetonstart=True)
mk(c, mathCHOP, 'math_floor', X + 350, 0, ['speed_clock'], integer='floor')
mk(c, slopeCHOP, 'slope_flip', X + 525, 0, ['math_floor'])
mk(c, nullCHOP, 'null_clock', X + 525, 150, ['speed_clock'])
mk(c, nullCHOP, 'null_flip', X + 700, 0, ['slope_flip'])

pe = mk(c, parameterexecuteDAT, 'parexec_reset', X, 200, pars='Reset', valuechange=False, onpulse=True)
pe.par.op.expr = 'parent()'
pe.text = '''# Reset pulse: page 0, fresh capture.
def onPulse(par):
    c = par.owner
    c.op('speed_clock').par.resetpulse.pulse()
    c.op('cache_hold').par.resetpulse.pulse()
    c.op('cache_hold').par.activepulse.pulse()
    return
'''

# ---------------------------------------------------------------- hold (stop motion)
mk(c, cacheTOP, 'cache_hold', X + 525, -300, ['transform_zoom'], cachesize=1, cacheonce=True,
   active=E("op('null_flip')['page'] != 0"))
mk(c, blurTOP, 'blur_soft', X + 700, -300, ['cache_hold'], preshrink=B(R + '.Preshrink'), size=B(R + '.Filtersize'))
mk(c, nullTOP, 'null_frame', X + 875, -300, ['blur_soft'])

# ---------------------------------------------------------------- paper + notebook
paper = mk(c, moviefileinTOP, 'paper_atlas', X + 700, -600)
lock_image(paper, REPO + '/assets/flipbook/paper_atlas.png')
nbk = mk(c, moviefileinTOP, 'notebook_tex', X + 700, -750)
lock_image(nbk, REPO + '/assets/flipbook/notebook.png')
mk(c, moviefileinTOP, 'paper_user', X + 525, -600, file=B(R + '.Paperatlas'), format='mono8fixed')
mk(c, moviefileinTOP, 'notebook_user', X + 525, -750, file=B(R + '.Notebookfile'), format='mono8fixed')
mk(c, switchTOP, 'switch_paper', X + 875, -600, ['paper_atlas', 'paper_user'],
   index=E("1 if parent().par.Paperatlas.eval() else 0"))
mk(c, switchTOP, 'switch_notebook', X + 875, -750, ['notebook_tex', 'notebook_user'],
   index=E("1 if parent().par.Notebookfile.eval() else 0"))

# ---------------------------------------------------------------- page
glsl(c, 'glsl_page', X + 1100, -300, 'flipbook_page.glsl', ['null_frame', 'switch_paper', 'switch_notebook'],
     uniforms=[
         ('uFlip', [E("op('math_floor')['page']"), E("parent().par.Papercount if parent().par.Paperatlas.eval() else 10"),
                    B(R + '.Randompaper'), 0]),
         ('uPaperGrid', [E("parent().par.Papercols if parent().par.Paperatlas.eval() else 5"),
                         E("parent().par.Paperrows if parent().par.Paperatlas.eval() else 2"), 0, 0]),
         ('uJitter', [B(R + '.Imagejitter'), B(R + '.Shake'), B(R + '.Shakerotate'), B(R + '.Shakescale')]),
         ('uGrain', [B(R + '.Grain'), B(R + '.Grainamount'), B(R + '.Grainscale'), B(R + '.Grainspace')]),
         ('uPaper', [B(R + '.Paper'), B(R + '.Paperdisplace'), B(R + '.Paperstrength'),
                     E("parent().par.Blendmode.menuIndex")]),
         ('uNotebook', [B(R + '.Notebook'), B(R + '.Notebookopacity'), B(R + '.Notebookdisplace'), 0]),
         ('uTone', [B(R + '.Flicker'), B(R + '.Brightness'), B(R + '.Contrast'), 0]),
         ('uPaperColor', [B(R + '.Papercolorr'), B(R + '.Papercolorg'), B(R + '.Papercolorb'), 1]),
         ('uInkColor', [B(R + '.Inkcolorr'), B(R + '.Inkcolorg'), B(R + '.Inkcolorb'), B(R + '.Inktint')]),
     ],
     outputresolution='custom', resolutionw=B(R + '.Resolutionw'), resolutionh=B(R + '.Resolutionh'),
     outputaspect='resolution')

# ---------------------------------------------------------------- page-flip ghost
mk(c, blurTOP, 'blur_ghost', X + 1275, -450, ['glsl_page'], type='bartlette', preshrink=3, size=32,
   filterscalex=0, filterscaley=1)
glsl(c, 'glsl_flip', X + 1450, -300, 'flipbook_flip.glsl', ['glsl_page', 'blur_ghost'],
     uniforms=[
         ('uGhost', [B(R + '.Pageflipeffect'), B(R + '.Ghostopacity'), B(R + '.Ghostfade'),
                     E("(op('null_clock')['page'] % 1) / max(parent().par.Speed.eval(), 0.001)")]),
         ('uGhostXf', [B(R + '.Ghostoffsetx'), B(R + '.Ghostoffsety'), B(R + '.Ghostrotate'),
                       E("op('math_floor')['page'] if parent().par.Ghostalternate else 0")]),
     ])

# ---------------------------------------------------------------- lens blur
glsl(c, 'glsl_vignette', X + 1450, -550, 'flipbook_vignette.glsl',
     uniforms=[('uVignette', [B(R + '.Vignette'), B(R + '.Vignettesoft'), 0, 0])],
     outputresolution='custom', resolutionw=E("int(parent().par.Resolutionw / 4)"),
     resolutionh=E("int(parent().par.Resolutionh / 4)"), outputaspect='resolution', format='mono8fixed')
mk(c, lumablurTOP, 'lumablur_lens', X + 1625, -300, ['glsl_flip', 'glsl_vignette'], blackvalue=0.15,
   whitevalue=1, blackwidth=0, whitewidth=B(R + '.Lensblursize'), extend='mirror')
mk(c, switchTOP, 'switch_lens', X + 1800, -300, ['glsl_flip', 'lumablur_lens'], index=B(R + '.Lensblur'))
mk(c, nullTOP, 'null_out', X + 1975, -300, ['switch_lens'])
mk(c, outTOP, 'out1', X + 2150, -300, ['null_out'])

finish(c, (0.55, 0.45, 0.3))
print('built', c.path)
