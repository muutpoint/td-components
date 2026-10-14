# Builds the Halftone component. Run inside TouchDesigner:
#   exec(open('/Users/davidmayzenberg/Code/td-components/tools/build_halftone.py').read())
# Creates /project1/halftone2 by default (the old COMP is called halftone). Set TARGET / NAME / POS to change.

exec(open('/Users/davidmayzenberg/Code/td-components/tools/common.py', encoding='utf-8').read())

TARGET = globals().get('TARGET', '/project1')
NAME = globals().get('NAME', 'halftone2')
POS = globals().get('POS', (600, -700))

c = fresh_comp(op(TARGET), NAME, *POS)
c.par.parentshortcut = 'Halftone'

# ---------------------------------------------------------------- parameters
P = Pars(c, 'Halftone')
P.menu('Mode', 'Mode', ['rgb', 'cmyk', 'mono'], ['RGB Light (glowing dots)', 'CMYK Ink', 'Mono Ink'])
P.float('Cellsize', 'Cell Size', 12, 3, 60, clamp=(1, None), help='Dot spacing in pixels.')
P.float('Scale', 'Dot Size', 1.4, 0.2, 2.5, clamp=(0, None), help='Dot diameter at full value, in cells.')
P.float('Zoomadd', 'Zoom', 1.0, 0.25, 4, clamp=(0.05, None), help='Scales the grid and the dots together.')
P.toggle('Areacorrect', 'Area-correct Tone', False, help='Dot area (not radius) follows the value.')
P.section().int('Circlepoints', 'Dot Sides', 20, 3, 24, clamp=(3, 64), help='24 or more = circle.')
P.float('Dotrotate', 'Dot Rotate', 0, -180, 180)
P.toggle('Circleopen', 'Rings', False, help='Outlined dots instead of filled ones.')
P.float('Ringwidth', 'Ring Width', 0.3, 0.02, 1)
P.float('Softness', 'Edge Softness', 0.75, 0.25, 4, help='Anti-aliasing in pixels.')
P.section().float('Rotater', 'Angle R / C', 0, -180, 180)
P.float('Rotateg', 'Angle G / M', 137, -180, 180)
P.float('Rotateb', 'Angle B / Y', 62, -180, 180)
P.float('Rotatebl', 'Angle K / Mono', 0, -180, 180)
P.float('Offset', 'Misregistration', 0, -10, 10, help='Pixels each plate is pushed out of register.')
P.float('Platerotate', 'Rotate Plates', 0, 0, 1, help='Turns each plate\'s picture with its screen angle (1 = the v1 look).')
P.float('Platespread', 'Plate Scale Spread', 0, -0.2, 0.2, help='Each plate a little bigger than the last.')
P.section().toggle('Red', 'R / C', True)
P.toggle('Green', 'G / M', True)
P.toggle('Blue', 'B / Y', True)
P.toggle('Black', 'K / Mono', True)

P = Pars(c, 'Color')
P.float('Color', 'Saturation', 1.0, 0, 3, help='Applied to the result.')
P.float('Insaturation', 'Input Saturation', 1.0, 0, 3)
P.float('Gamma', 'Input Gamma', 1.0, 0.2, 3)
P.float('Contrast', 'Input Contrast', 1.0, 0, 3)
P.float('Blackgen', 'Black Generation', 1.0, 0, 1, help='CMYK: how much grey goes to the K plate.')
P.toggle('Invert', 'Invert (Mono)', False)
P.section().rgb('Bgcolor', 'Background (RGB)', (0, 0, 0))
P.rgb('Papercolor', 'Paper (Ink)', (0.97, 0.96, 0.93))
P.toggle('Custominks', 'Custom Inks', False)
P.rgb('Ink1', 'Ink R / C', (0, 0.62, 0.89))
P.rgb('Ink2', 'Ink G / M', (0.9, 0.0, 0.5))
P.rgb('Ink3', 'Ink B / Y', (1.0, 0.93, 0.0))
P.rgb('Ink4', 'Ink K / Mono', (0.1, 0.1, 0.12))

P = Pars(c, 'Glow')
P.float('Glow', 'Glow', 0.33, 0, 2)
P.float('Glowsize', 'Glow Size', 24, 0, 100, clamp=(0, None))
P.float('Trails', 'Trails', 0.0, 0, 0.99, clamp=(0, 0.995), help='Glow that lingers between frames.')
P.pulse('Resettrails', 'Reset Trails')

P = Pars(c, 'Output')
P.toggle('Useinputres', 'Use Input Resolution', True)
P.wh('Resolution', 'Resolution', (1920, 1080))
c.par.Resolutionw.enableExpr = "not me.par.Useinputres"
c.par.Resolutionh.enableExpr = "not me.par.Useinputres"

about_page(c, 'Halftone', 'Halftone screen for TOPs: rotated dot grids per channel, RGB light / CMYK / mono, polygon or ring dots, glow.')

R = "parent().par"
MODE = "parent().par.Mode.menuIndex"
RGB_INKS = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (0, 0, 0)]
CMYK_INKS = [(0, 0.62, 0.89), (0.9, 0.0, 0.5), (1.0, 0.93, 0.0), (0.1, 0.1, 0.12)]


def ink(i):
    out = []
    for j, comp in enumerate('rgb'):
        out.append(E("parent().par.Ink%d%s if parent().par.Custominks else (%r if %s == 0 else %r)"
                     % (i + 1, comp, RGB_INKS[i][j], MODE, CMYK_INKS[i][j])))
    return out + [1]


# ---------------------------------------------------------------- input
mk(c, moviefileinTOP, 'demo_image', -400, 0, file=E("app.samplesFolder + '/Map/Jellybeans.1.jpg'"))
c.op('demo_image').comment = 'Default input from the TouchDesigner samples, shown when nothing is wired in.'
mk(c, inTOP, 'in1', -200, 0, ['demo_image'])
mk(c, fitTOP, 'fit_res', 0, 0, ['in1'], fit='fitoutside', outputresolution='custom',
   resolutionw=E("op('in1').width if parent().par.Useinputres else parent().par.Resolutionw"),
   resolutionh=E("op('in1').height if parent().par.Useinputres else parent().par.Resolutionh"),
   outputaspect='resolution')
mk(c, nullTOP, 'null_src', 175, 0, ['fit_res'])

# ---------------------------------------------------------------- screen
glsl(c, 'glsl_halftone', 400, 0, 'halftone.glsl', ['null_src'],
     uniforms=[
         ('uGrid', [B(R + '.Cellsize'), B(R + '.Scale'), B(R + '.Circlepoints'), B(R + '.Zoomadd')]),
         ('uAngles', [B(R + '.Rotater'), B(R + '.Rotateg'), B(R + '.Rotateb'), B(R + '.Rotatebl')]),
         ('uOn', [B(R + '.Red'), B(R + '.Green'), B(R + '.Blue'), B(R + '.Black')]),
         ('uShape', [B(R + '.Circleopen'), B(R + '.Ringwidth'), B(R + '.Dotrotate'), B(R + '.Softness')]),
         ('uMode', [E(MODE), B(R + '.Offset'), B(R + '.Blackgen'), B(R + '.Invert')]),
         ('uTone', [B(R + '.Gamma'), B(R + '.Contrast'), B(R + '.Insaturation'), B(R + '.Areacorrect')]),
         ('uInk0', ink(0)), ('uInk1', ink(1)), ('uInk2', ink(2)), ('uInk3', ink(3)),
         ('uPaper', [E("parent().par.Bgcolor%s if %s == 0 else parent().par.Papercolor%s" % (ch, MODE, ch))
                     for ch in 'rgb'] + [1]),
         ('uPlate', [B(R + '.Platerotate'), B(R + '.Platespread'), 0, 0]),
     ],
     inputfiltertype='mipmap', inputextenduv='mirror')

# ---------------------------------------------------------------- glow + trails
mk(c, blurTOP, 'blur_glow', 600, -250, ['glsl_halftone'], preshrink=2,
   size=E("parent().par.Glowsize / 4"))
mk(c, feedbackTOP, 'feedback_trail', 775, -400, ['blur_glow'])
glsl(c, 'glsl_trail', 775, -250, 'halftone_trail.glsl', ['blur_glow', 'feedback_trail'],
     uniforms=[('uTrail', [B(R + '.Trails'), 0, 0, 0])], format='rgba16float')
c.op('feedback_trail').par.top = 'glsl_trail'
mk(c, levelTOP, 'level_glow', 950, -250, ['glsl_trail'], brightness1=B(R + '.Glow'))
mk(c, compositeTOP, 'comp_glow', 1125, 0, ['glsl_halftone', 'level_glow'], operand='add')
mk(c, switchTOP, 'switch_glow', 1300, 0, ['glsl_halftone', 'comp_glow'], index=E("1 if parent().par.Glow > 0 else 0"))
mk(c, hsvadjustTOP, 'hsv_color', 1475, 0, ['switch_glow'], saturationmult=B(R + '.Color'))
mk(c, nullTOP, 'null_out', 1650, 0, ['hsv_color'])
mk(c, outTOP, 'out1', 1825, 0, ['null_out'])

pe = mk(c, parameterexecuteDAT, 'parexec_reset', 775, -550, pars='Resettrails', valuechange=False, onpulse=True)
pe.par.op.expr = 'parent()'
pe.text = '''# Reset Trails pulse.
def onPulse(par):
    par.owner.op('feedback_trail').par.resetpulse.pulse()
    return
'''

finish(c, (0.25, 0.4, 0.55))
print('built', c.path)
