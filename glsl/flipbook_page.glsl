// FlipBook, pass 1: draws one page.
// Input 0: the held frame (fitted to the output size and softened)
// Input 1: paper atlas (mono, uPaperGrid.x columns by uPaperGrid.y rows, row 0 at the top)
// Input 2: notebook (mono)
// Every random value is seeded by the flip index, so a page stays still until the next flip.

uniform vec4 uFlip;       // x flip index, y paper frame count, z random paper order (0/1)
uniform vec4 uPaperGrid;  // x columns, y rows
uniform vec4 uJitter;     // x image offset, y page shake, z page rotate (degrees), w page scale
uniform vec4 uGrain;      // x on, y amount, z blotch size (px), w density (0-1)
uniform vec4 uPaper;      // x on, y displace, z texture strength, w blend mode (0 over, 1 multiply, 2 darken)
uniform vec4 uNotebook;   // x on, y opacity, z displace
uniform vec4 uTone;       // x flicker, y brightness, z contrast
uniform vec4 uPaperColor;
uniform vec4 uInkColor;   // rgb tint, a = tint amount

out vec4 fragColor;

uint pcg(uint v) {
    uint s = v * 747796405u + 2891336453u;
    uint w = ((s >> ((s >> 28u) + 4u)) ^ s) * 277803737u;
    return (w >> 22u) ^ w;
}
float rnd(uint a, uint b) { return float(pcg(a * 1664525u + pcg(b))) / 4294967295.0; }
float srnd(uint a, uint b) { return rnd(a, b) * 2.0 - 1.0; }

float hash2(ivec2 q, uint seed) {
    return float(pcg(uint(q.x) * 73856093u ^ uint(q.y) * 19349663u ^ pcg(seed))) / 4294967295.0;
}
float vnoise(vec2 p, uint seed) {
    ivec2 i = ivec2(floor(p));
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    float a = hash2(i, seed), b = hash2(i + ivec2(1, 0), seed);
    float c = hash2(i + ivec2(0, 1), seed), d = hash2(i + ivec2(1, 1), seed);
    return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}
float fbm(vec2 p, uint seed) {
    float s = 0.0, a = 0.5, n = 0.0;
    for (int o = 0; o < 6; o++) {
        s += a * vnoise(p, seed + uint(o) * 101u);
        n += a;
        p = p * 2.07 + 17.3;
        a *= 0.55;
    }
    return s / n;
}

vec2 rot2(vec2 p, float a) {
    float c = cos(a), s = sin(a);
    return vec2(c * p.x - s * p.y, s * p.x + c * p.y);
}

float samplePaper(vec2 uv, uint frame) {
    float count = max(uFlip.y, 1.0);
    float idx = uFlip.z > 0.5 ? floor(rnd(frame, 11u) * count) : mod(float(frame), count);
    vec2 grid = max(uPaperGrid.xy, vec2(1.0));
    vec2 cell = vec2(mod(idx, grid.x), floor(idx / grid.x));
    // half a texel inset so a cell never bleeds into its neighbour
    vec2 inset = 0.5 * uTD2DInfos[1].res.xy * grid;
    uv = clamp(uv, inset, 1.0 - inset);
    vec2 auv = vec2((cell.x + uv.x) / grid.x, 1.0 - (cell.y + 1.0 - uv.y) / grid.y);
    return texture(sTD2DInputs[1], auv).r;
}

void main() {
    vec2 uv = vUV.st;
    vec2 res = uTDOutputInfo.res.zw;
    float aspect = res.x / res.y;
    uint f = uint(uFlip.x);

    // the sheet moves a little on every flip (paper and notebook move together)
    vec2 shake = vec2(srnd(f, 1u), srnd(f, 2u)) * uJitter.y;
    float ang = srnd(f, 3u) * radians(uJitter.z);
    float scl = 1.0 + srnd(f, 4u) * uJitter.w;
    vec2 c = (uv - 0.5) * vec2(aspect, 1.0);
    // overscan so the moving sheet never shows its edge
    float over = 1.0 + 2.2 * uJitter.y + 0.6 * radians(uJitter.z) + uJitter.w;
    vec2 sheetUV = rot2(c, ang) / (scl * over) / vec2(aspect, 1.0) + 0.5 + shake;

    float paperTex = uPaper.x > 0.5 ? samplePaper(sheetUV, f) : 1.0;
    float nb = texture(sTD2DInputs[2], clamp(sheetUV, 0.0, 1.0)).r;

    // the drawing: a small jitter of its own, pushed around by the paper surface
    vec2 jit = vec2(srnd(f, 5u), srnd(f, 6u)) * uJitter.x;
    vec2 disp = vec2(0.0);
    if (uPaper.x > 0.5)
        disp += (paperTex - 1.0) * uPaper.y;
    if (uNotebook.x > 0.5)
        disp += (nb - 0.5) * uNotebook.z;
    vec4 img = texture(sTD2DInputs[0], uv + jit + disp);   // premultiplied

    // flicker, brightness and contrast (the colour, not the alpha)
    vec3 rgb = img.a > 0.0 ? img.rgb / img.a : vec3(0.0);
    rgb *= (1.0 + srnd(f, 7u) * uTone.x) * uTone.y;
    rgb = (rgb - 0.5) * uTone.z + 0.5;
    rgb = mix(rgb, rgb * uInkColor.rgb, uInkColor.a);
    rgb = clamp(rgb, 0.0, 1.0);

    // grain: specks where the ink did not take, new on every page
    float a = img.a;
    if (uGrain.x > 0.5) {
        vec2 gp = uv * res / max(uGrain.z, 1.0);
        float g = fbm(gp, f * 7u + 3u);
        float thr = mix(0.72, 0.38, clamp(uGrain.w, 0.0, 1.0));
        float holes = smoothstep(thr, thr + 0.04, g);
        a *= 1.0 - holes * uGrain.y;
    }

    // the sheet: paper colour, paper texture, optional notebook
    vec3 sheet = uPaperColor.rgb * mix(1.0, paperTex, uPaper.z);
    if (uNotebook.x > 0.5)
        sheet = mix(sheet, uPaperColor.rgb * nb, uNotebook.y);

    vec3 col;
    int mode = int(uPaper.w + 0.5);
    if (mode == 1)
        col = sheet * mix(vec3(1.0), rgb, a);            // multiply: ink soaks into the sheet
    else if (mode == 2)
        col = min(sheet, mix(sheet, rgb, a));             // darken
    else
        col = mix(sheet, rgb, a);                         // over
    // the paper's own texture always shows through the lightest parts
    col = min(col, uPaperColor.rgb * mix(1.0, paperTex, uPaper.z));

    fragColor = TDOutputSwizzle(vec4(col, 1.0));
}
