# TouchDesigner components

Four drop-in `.tox` components for TouchDesigner: three TOP effects and a texture instancer. Each one is a
single self-contained COMP with its parameters on custom pages. Images it needs are embedded and its
shaders are inside the component, so nothing has to sit next to the file.

| | Component | What it does |
|---|---|---|
| ![](flipbook/preview.jpg) | [**FlipBook**](#flipbook) | Turns a TOP into a hand-flipped book: stop-motion timing, paper, notebook, grain, page-flip ghost, lens blur. |
| ![](paint/preview.jpg) | [**Paint**](#paint) | Painterly filter: anisotropic Kuwahara brush strokes, tone steps, paper, ink outline, mask. |
| ![](halftone/preview.jpg) | [**Halftone**](#halftone) | Halftone screen: rotated dot grids per channel, RGB light / CMYK ink / mono, polygon or ring dots, glow. |
| ![](texture-instancer/preview.jpg) | [**Texture Instancer**](#texture-instancer) | Instances a folder of images or movies on POP points, with ordering, size, drift, spin and colour controls. |

These are version 2 of components first made in 2025. Each one keeps the old parameters and look and adds to
them; the changes are listed per component below.

## Use

TouchDesigner 2025 with POPs (built and tested on 2025.32820). Drag a `.tox` into a network, wire the input, and use the custom
parameter pages. With nothing wired in, each component shows a built-in demo input, so you can see it work
straight away. The *About* page has the version.

## FlipBook

`flipbook/flipbook.tox` · input: TOP · output: TOP

The input is held and only updated on each "flip" (*Flips per Second*), like a drawing redrawn on every page.
On every flip the sheet shifts a little, the paper texture changes, new grain appears, the brightness flickers,
and a smeared, tilted copy of the page flashes over it and fades (*Page Flip Ghost*). The edges of the frame
get a lens blur. Drawings with alpha sit on the notebook; for opaque footage use *Blend = Multiply*.

- **Flip Book**: Play, Flips per Second, Reset, Resolution, Fit Input, Zoom, Offset, Image Jitter, Page Shake / Rotate / Scale, Flicker
- **Style**: Blend (Over / Multiply / Darken), Paper (texture, displace, random order, colour), Notebook (opacity, displace), Grain (amount, size, density), Brightness, Contrast, Ink Tint, Page Flip Ghost (opacity, fade, rotate, offset, alternate sides)
- **Blur**: Pre-Shrink, Softness, Lens Blur (size, sharp area, falloff)
- **Paper Files**: your own paper atlas (grid of frames) and notebook image; empty = the built-in ones

Changes from v1: the paper frames and notebook are embedded (v1 needed a `files/` folder next to the project and
broke when it was missing); Play no longer depends on a keyboard CHOP and the timing doesn't reference
parameters outside the component; the image chain is now two shaders instead of dozens of operators; any output
resolution (v1 was fixed at 2048 × 2048); new: blend modes, own paper/notebook files, ink tint,
brightness/contrast, ghost and vignette controls, Reset.

## Paint

`paint/paint.tox` · inputs: TOP, mask TOP (optional) · output: TOP

A structure tensor finds the direction of the strokes, a Gaussian blur smooths that flow, and an anisotropic
Kuwahara filter paints along it: each pixel takes the flattest of eight elliptical sectors. The result is then
quantised into tone steps, saturated, tone-mapped and multiplied with paper.

- **Stroke**: Brush Size, Stroke Stretch, Sharpness (32 = hard pick, lower = softer), Flow Smoothing, Process Scale, Quality
- **Color and Paper**: Tone Steps, Shadow / Highlight Level, Saturation, Tone Map, Exposure, Gamma, Paper Strength / Scale / Contrast / Image, Paper Reveal, Paper Colour, Background, Mix Original
- **Outline**: ink line along strong edges (amount, threshold, softness, colour)
- **Mask**: Use Mask, Invert. Input 2's alpha cuts the result out, and the output carries that alpha.

Changes from v1: the stroke field is smoothed (strokes follow the image more calmly) and the orientation maths
is fixed; *Sharpness* blends sectors instead of always picking one; *Process Scale* (default 0.5) paints at a
lower resolution with the same brush size; the paper is a 2048 px mono texture (v1 locked a 3600 × 4800 image
into the file); no black border at the frame edge; new: outline, paper reveal, exposure/gamma, mix, mask invert,
shadow/highlight levels, own paper image.

## Halftone

`halftone/halftone.tox` · input: TOP · output: TOP

One shader draws a rotated dot grid per channel. Each dot reads the average of its cell (from a mipmap) and
is sized by it; overlapping dots keep the strongest coverage. Dots can be polygons (3 to 24 sides) or rings.

- **Halftone**: Mode (RGB light, CMYK ink, Mono ink), Cell Size, Dot Size, Zoom, Area-correct Tone, Dot Sides, Dot Rotate, Rings, Ring Width, Edge Softness, Angles per channel, Misregistration, Rotate Plates, Plate Scale Spread, channel on/off
- **Color**: Saturation, Input Saturation / Gamma / Contrast, Black Generation, Invert (mono), Background, Paper, Custom Inks
- **Glow**: Glow, Glow Size, Trails, Reset Trails
- **Output**: Use Input Resolution or a custom Resolution

*Rotate Plates = 1* brings back v1's look, where each channel's picture turns with its screen angle.

Changes from v1: v1 instanced dots into four 4096 × 4096 renders (about 70 ms CPU + 40 ms GPU per frame on Ro's
Mac); v2 is one pass at the input resolution (about 1.5 ms GPU). New: CMYK and mono modes, ring and
polygon dots without geometry, area-correct tone, misregistration in pixels, custom inks, glow trails. The
unused *Edge* parameters are gone.

## Texture Instancer

`texture-instancer/texture_instancer.tox` · inputs: points POP, shape POP (optional) · outputs: render TOP, texture array TOP, points POP

Point it at a folder (*Texture Folder*). The images are loaded a few per frame (*Load Budget*) into one 2D
texture array, one layer per image, and each one is measured once (aspect, brightness, hue, saturation, alpha
coverage). The set is put in an order (*Texture Order*), and each point picks its place in that order by
*Assign By*: point number, random, any point attribute, a noise field, or a guide image (photo-mosaic). One
GLSL POP writes every instance's layer, size, rotation, facing, position and colour, so it all runs on the
GPU. Every parameter that names an attribute is a menu of the input's attributes and components (`P.y`,
`N.x`, `P length`, plus Point Index and Random); value ranges are found automatically. The render uses the
built-in orbit camera (TouchDesigner's `cameraViewport`) or your own (*Camera*); render `geo_instances`
yourself for your own lighting.

- **Textures**: Texture Folder, Include Subfolders, Name Filter, Maximum Textures, Texture Size, Fit (keep image aspect / crop / stretch), Load Budget, Reload Folder, Texture Order (name, date, random, brightness, hue, saturation, coverage, aspect), Order Seed, Reverse, Use Range, Outline (off / outline / outline only) with width, softness and colour, Textures Loaded, Status
- **Sorting**: Assign By (sequential, random, attribute, noise field, photo-mosaic), Attribute, Auto / Manual Range, Noise Frequency / Speed, Guide Image, Map Image By (bounds XY / XZ / ZY, point Tex), Match (brightness / hue), Stretch to Set, Offset, Repeat, Steps, Jitter, Seed, Shuffle, Auto Shuffle, Flip Speed, Flip Offset per Instance
- **Scale**: Size, Stretch X / Y, Random Variance, Scale By (attribute, noise, wave along an attribute), Size at Min / Max, Wavelength, Speed, Reveal (0-1 grow-in along texture key, point index, random or the scale attribute), Reveal Softness, Reverse
- **Rotate**: Facing (camera, along an attribute such as N or a world axis, random), Up Attribute, Push Along Facing Attribute, Random Rotate, Rotate by Attribute (degrees across its range), Spin, Random Spin Direction, Random Tilt
- **Position**: Distribution (input points, scatter on surface, scatter in volume), Scatter Count / Seed, Offset, Random Offset, Drift (amount, frequency, speed), Density, Cull by Attribute (keep above / below a threshold)
- **Color**: Color Mode (off, random from palette, one per texture, palette by attribute, image at point, point colour), Palette / Image TOP, Color Amount, Tint, Opacity, Blend (cutout, soft and depth sorted, additive), Alpha Threshold
- **Scene**: Resolution, Background Colour / Alpha, Camera, Anti-Alias

Changes from v2 (v3): loading no longer makes one Movie File In per file plus an atlas: images go straight
into the texture array (281 PNGs in about 7 s, 157 3464 px JPEGs in about 16 s, without freezing TouchDesigner),
memory is count × size² × 4 bytes (157 at 256 px = 41 MB); attribute-driven texture choice, size, rotation,
facing, reveal, culling and colour are new, as are brightness / hue ordering, the photo-mosaic, the flip
book, scatter on surface or volume, the soft depth-sorted blend and the outline; quads keep the image's shape
without padding; animation uses speed-integrated clocks, so a still setup does not recook (5184 instances:
about 1 ms CPU per frame, almost all of it the render). Movies and GIFs load their first frame only (v2's
*Play Movies / GIFs* rebuilt the atlas every frame).

Changes from v1 (v2): input is a POP (v1 took a SOP and went through CHOPs); the ffmpeg palette step is
replaced by sampling a TOP directly; v1's broken instance setup (mismatched instance counts, hard-coded
`/project1` paths, render size taken from parameters that didn't exist) is gone.

## Repo layout

| File | What it is |
|---|---|
| `flipbook/flipbook.tox` | FlipBook component. |
| `flipbook/preview.jpg` | Preview (TouchDesigner sample image `Butterfly1.tif`). |
| `paint/paint.tox` | Paint component. |
| `paint/preview.jpg` | Preview (`Trillium.jpg`, outline on). |
| `halftone/halftone.tox` | Halftone component. |
| `halftone/preview.jpg` | Preview (`Jellybeans.1.jpg`, CMYK). |
| `texture-instancer/texture_instancer.tox` | Texture Instancer component. |
| `texture-instancer/preview.jpg` | Preview (built-in shapes scattered on the demo sphere, ordered and sized by height, coloured by X). |
| `glsl/flipbook_page.glsl` | FlipBook pass 1: one page (paper, notebook, jitter, grain, blend). |
| `glsl/flipbook_flip.glsl` | FlipBook pass 2: the page-flip ghost. |
| `glsl/flipbook_vignette.glsl` | FlipBook lens-blur mask. |
| `glsl/paint_tensor.glsl` | Paint pass 1: structure tensor. |
| `glsl/paint_kuwahara.glsl` | Paint pass 2: anisotropic Kuwahara. |
| `glsl/paint_grade.glsl` | Paint pass 3: tone steps, colour, outline, paper, mask. |
| `glsl/halftone.glsl` | Halftone screen. |
| `glsl/halftone_trail.glsl` | Halftone glow trails (feedback). |
| `glsl/instancer_keys.glsl` | Texture Instancer GLSL POP 1: copies the picked attributes into fixed names (the pickers write `#define`s on top). |
| `glsl/instancer_attribs.glsl` | Texture Instancer GLSL POP 2: per-point layer, size, rotation, facing, position, reveal, culling, colour. |
| `glsl/instancer_edge.glsl` | Texture Instancer: outline around each layer's alpha shape. |
| `py/instancer_ext.py` | Texture Instancer extension: folder loading, measuring, texture order, attribute menus. |
| `assets/flipbook/paper_atlas.png` | The ten paper frames (5 × 2 grid, mono). Embedded in `flipbook.tox`. |
| `assets/flipbook/notebook.png` | Notebook sheet (mono). Embedded in `flipbook.tox`. |
| `assets/paint/paper.png` | Paper texture (2048 px, mono). Embedded in `paint.tox`. |
| `tools/common.py` | Helpers shared by the build scripts (operators, shaders, parameter pages, embedding images). |
| `tools/build_flipbook.py` | Builds FlipBook from the files above. |
| `tools/build_paint.py` | Builds Paint. |
| `tools/build_halftone.py` | Builds Halftone. |
| `tools/build_instancer.py` | Builds Texture Instancer. |
| `tools/test_all.py` | Rebuilds all four, checks them, exports the `.tox` files and re-imports them. |
| `tools/perf.py` | Measures a component's average cook time over N frames. |
| `tools/make_previews.py` | Renders the preview images. |

## Rebuilding

The `.tox` files are built from `glsl/`, `assets/` and `tools/`. To change a component, edit those and run
in TouchDesigner (Textport or a Text DAT; the scripts use absolute paths at the top, so change `REPO` if the
repo is somewhere else):

```python
exec(open('/path/to/td-components/tools/test_all.py').read())
# a few seconds later:
print(op('/project1/td_components_test/tests').module.report())
```

That rebuilds `/project1/flipbook`, `/paint`, `/halftone` and `/texture_instancer` (replacing COMPs with
those names), then checks each one: no errors, every shader compiles, the output isn't empty, it changes when
an input is wired and when a key parameter changes, the exported `.tox` reloads without errors, gives the same
output and still holds its embedded images.

© Ro Mayz 2026. All rights reserved.
