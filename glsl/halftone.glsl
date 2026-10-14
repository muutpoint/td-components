// Halftone: one rotated dot grid per channel.
// Input 0: the image (mipmapped, so each dot reads the average of its cell)
// Modes: 0 RGB light (additive coloured dots on black, the original look),
//        1 CMYK ink (subtractive dots on paper), 2 Mono ink.
// Dot size follows the channel value. Dots can overlap their cell, so each pixel checks the
// neighbouring cells too and keeps the strongest coverage (a max blend, like the old instanced version).

uniform vec4 uGrid;     // x cell size (px), y dot size (diameter / cell at full value), z polygon sides, w zoom
uniform vec4 uAngles;   // degrees for R/C, G/M, B/Y, K
uniform vec4 uOn;       // channel on/off: R/C, G/M, B/Y, K
uniform vec4 uShape;    // x shape (0 dot, 1 ring), y ring width (fraction of radius), z shape rotation (deg), w edge softness (px)
uniform vec4 uMode;     // x mode, y misregistration (px), z black generation (CMYK), w invert (mono)
uniform vec4 uTone;     // x gamma, y contrast, z saturation, w area-correct size (0/1)
uniform vec4 uInk0;     // ink colour for R/C
uniform vec4 uInk1;     // ink colour for G/M
uniform vec4 uInk2;     // ink colour for B/Y
uniform vec4 uInk3;     // ink colour for K / mono
uniform vec4 uPaper;    // paper colour (ink modes) / background (RGB mode)
uniform vec4 uPlate;    // x plate rotation (0 = true halftone, 1 = each plate's image turns with its screen angle), y plate scale spread

out vec4 fragColor;

#define PI 3.14159265

vec2 rot2(vec2 p, float a) {
    float c = cos(a), s = sin(a);
    return vec2(c * p.x - s * p.y, s * p.x + c * p.y);
}

// distance to a regular polygon of radius 1 (circumradius), n sides; n >= 24 is a circle
float polyDist(vec2 p, float n, float spin) {
    if (n >= 24.0)
        return length(p);
    p = rot2(p, spin);
    float a = atan(p.y, p.x);
    float seg = 2.0 * PI / n;
    float d = cos(floor(0.5 + a / seg) * seg - a) * length(p);
    return d / cos(PI / n);    // scale so the polygon touches the same radius as the circle
}

vec3 grade(vec3 c) {
    c = pow(max(c, 0.0), vec3(max(uTone.x, 0.01)));
    c = (c - 0.5) * uTone.y + 0.5;
    float l = dot(c, vec3(0.299, 0.587, 0.114));
    return clamp(mix(vec3(l), c, uTone.z), 0.0, 1.0);
}

// the value a channel's dot represents, read from the image at a point in pixels
float channelValue(vec2 px, int ch, float lod, float angle) {
    vec2 res = uTD2DInfos[0].res.zw;
    // rotated plates: the picture itself turns with the screen (the v1 look)
    px = rot2(px - res * 0.5, angle * uPlate.x) * (1.0 + uPlate.y * float(ch)) + res * 0.5;
    vec2 uv = px / res;
    if (uPlate.x > 0.0 && (any(lessThan(uv, vec2(0.0))) || any(greaterThan(uv, vec2(1.0)))))
        return 0.0;
    vec3 c = grade(textureLod(sTD2DInputs[0], uv, lod).rgb);
    float mode = uMode.x;
    if (mode < 0.5)                       // RGB light
        return ch == 0 ? c.r : ch == 1 ? c.g : ch == 2 ? c.b : 0.0;
    if (mode < 1.5) {                     // CMYK with grey component replacement
        vec3 cmy = 1.0 - c;
        float k = min(cmy.r, min(cmy.g, cmy.b)) * uMode.z;
        cmy = (cmy - k) / max(1.0 - k, 1e-3);
        return ch == 0 ? cmy.r : ch == 1 ? cmy.g : ch == 2 ? cmy.b : k;
    }
    float l = dot(c, vec3(0.299, 0.587, 0.114));    // Mono
    return uMode.w > 0.5 ? l : 1.0 - l;
}

float coverage(vec2 px, int ch, float angle, vec2 shift) {
    float cs = max(uGrid.x, 1.0);
    vec2 res = uTD2DInfos[0].res.zw;
    vec2 ctr = res * 0.5;
    float lod = log2(max(cs / uGrid.w, 1.0));
    vec2 q = rot2((px - ctr - shift) / uGrid.w, -angle);     // grid space (unzoomed px)
    vec2 cell = floor(q / cs);
    float best = 0.0;
    float aa = max(uShape.w, 0.5) / uGrid.w;
    for (int j = -1; j <= 1; j++)
        for (int i = -1; i <= 1; i++) {
            vec2 cc = (cell + vec2(i, j) + 0.5) * cs;               // cell centre, grid space
            vec2 cpx = rot2(cc, angle) * uGrid.w + ctr + shift;     // back to image px
            float v = channelValue(cpx, ch, lod, angle);
            if (uTone.w > 0.5)
                v = sqrt(max(v, 0.0));
            float r = 0.5 * cs * uGrid.y * v;
            if (r <= 0.0)
                continue;
            float d = polyDist((q - cc) / r, uGrid.z, radians(uShape.z)) * r;
            float cov;
            if (uShape.x > 0.5) {
                float w = max(uShape.y * r, aa);
                cov = 1.0 - smoothstep(w * 0.5 - aa, w * 0.5 + aa, abs(d - r + w * 0.5));
            } else {
                cov = 1.0 - smoothstep(r - aa, r + aa, d);
            }
            best = max(best, cov);
        }
    return best;
}

void main() {
    vec2 res = uTDOutputInfo.res.zw;
    vec2 px = vUV.st * uTD2DInfos[0].res.zw;
    float m = uMode.y;
    vec2 shifts[4] = vec2[4](vec2(m, 0.0), vec2(0.0, m), vec2(-m, 0.0), vec2(-m, 0.0) * 0.5);
    vec4 cov = vec4(0.0);
    for (int ch = 0; ch < 4; ch++) {
        if (uOn[ch] < 0.5)
            continue;
        if (uMode.x > 1.5 && ch != 3)     // mono uses the K screen only
            continue;
        cov[ch] = coverage(px, ch, radians(uAngles[ch]), shifts[ch]);
    }

    vec3 col;
    if (uMode.x < 0.5) {
        // light: coloured dots add up on the background
        col = uPaper.rgb;
        col = max(col, uInk0.rgb * cov.x);
        col = max(col, uInk1.rgb * cov.y);
        col = max(col, uInk2.rgb * cov.z);
        col = col + uInk3.rgb * cov.w;
    } else {
        // ink: each dot filters the paper
        col = uPaper.rgb;
        col *= mix(vec3(1.0), uInk0.rgb, cov.x);
        col *= mix(vec3(1.0), uInk1.rgb, cov.y);
        col *= mix(vec3(1.0), uInk2.rgb, cov.z);
        col *= mix(vec3(1.0), uInk3.rgb, cov.w);
    }
    fragColor = TDOutputSwizzle(vec4(clamp(col, 0.0, 1.0), 1.0));
}
