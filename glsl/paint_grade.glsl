// Paint, pass 3: tone steps, colour, ink outline, paper, mask.
// Input 0: Kuwahara result (processing size, upsampled here)
// Input 1: paper texture (mono)
// Input 2: smoothed structure tensor (for the outline)
// Input 3: the original image (for Mix)
// Input 4: mask (alpha is used)

uniform vec4 uTone;     // x tone steps (0 = off), y shadow level, z highlight level, w saturation
uniform vec4 uGrade;    // x tone map on, y exposure, z mix with original, w gamma
uniform vec4 uPaper;    // x strength, y scale, z contrast, w paper reveal threshold (0 = off)
uniform vec4 uOutline;  // x amount, y width (threshold softness), z threshold, w paper reveal softness
uniform vec4 uMask;     // x on, y invert, z input has mask (0/1)
uniform vec4 uOutlineColor;
uniform vec4 uPaperColor;

out vec4 fragColor;

vec3 sat(vec3 rgb, float s) {
    float l = dot(rgb, vec3(0.2125, 0.7154, 0.0721));
    return mix(vec3(l), rgb, s);
}

vec3 aces(vec3 x) {
    const float a = 2.51, b = 0.03, c = 2.43, d = 0.59, e = 0.14;
    return clamp((x * (a * x + b)) / (x * (c * x + d) + e), 0.0, 1.0);
}

void main() {
    vec2 uv = vUV.st;
    vec2 res = uTDOutputInfo.res.zw;
    vec3 color = texture(sTD2DInputs[0], uv).rgb * uGrade.y;

    // tone steps: quantise the brightness, then lean each step towards the shadow or the paper
    if (uTone.x >= 2.0) {
        float gray = dot(color, vec3(0.299, 0.587, 0.114));
        float n = uTone.x;
        float qn = floor(gray * (n - 1.0) + 0.5) / (n - 1.0);
        qn = clamp(qn, uTone.y, uTone.z);
        if (qn < 0.5)
            color = mix(vec3(0.1), color, qn * 2.0);
        else
            color = mix(color, vec3(1.0), (qn - 0.5) * 2.0);
    }

    color = sat(color, uTone.w);
    if (uGrade.x > 0.5)
        color = aces(color);
    color = pow(max(color, 0.0), vec3(1.0 / max(uGrade.w, 0.01)));

    // ink outline from the edge strength of the smoothed tensor
    if (uOutline.x > 0.0) {
        vec4 t = texture(sTD2DInputs[2], uv);
        float e = sqrt(max(t.r + t.g, 0.0));
        float line = smoothstep(uOutline.z, uOutline.z + max(uOutline.y, 1e-3), e);
        color = mix(color, uOutlineColor.rgb, line * uOutline.x);
    }

    // paper: the texture multiplies in, and light areas can fade to bare paper
    vec2 aspect = vec2(res.x / res.y, 1.0);
    vec2 puv = (uv - 0.5) * aspect / max(aspect.x, 1.0) / max(uPaper.y, 0.01) + 0.5;
    float paper = texture(sTD2DInputs[1], puv).r;
    paper = clamp((paper - 0.5) * uPaper.z + 0.5, 0.0, 1.0);
    color *= mix(1.0, paper, uPaper.x);
    if (uPaper.w > 0.0) {
        float b = dot(color, vec3(0.299, 0.587, 0.114));
        float reveal = smoothstep(uPaper.w - uOutline.w, uPaper.w + uOutline.w, b);
        color = mix(color, uPaperColor.rgb * mix(1.0, paper, uPaper.x), reveal);
    }

    // mix back towards the original
    vec4 orig = texture(sTD2DInputs[3], uv);
    color = mix(color, orig.rgb, uGrade.z);

    float a = 1.0;
    if (uMask.x > 0.5 && uMask.z > 0.5) {
        a = texture(sTD2DInputs[4], uv).a;
        if (uMask.y > 0.5)
            a = 1.0 - a;
    }
    fragColor = TDOutputSwizzle(vec4(color * a, a));
}
