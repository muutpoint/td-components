// Paint, pass 2: anisotropic Kuwahara filter.
// Input 0: smoothed structure tensor (pass 1, blurred)
// Input 1: the image
// Eight sectors are sampled along an ellipse that follows the local stroke direction.
// Each sector's mean colour is weighted by how flat (low variance) it is: Sharpness 0 averages
// all sectors (soft), high Sharpness picks the flattest one (hard, flat paint).

uniform vec4 uKernel;   // x radius (px at processing size), y anisotropy alpha, z sharpness, w max radial steps

out vec4 fragColor;

#define SECTORS 8
#define TAU 6.2831853

float polyWeight(float x, float y) {
    const float eta = 0.1;
    const float lambda = 0.5;
    float v = (x + eta) - lambda * (y * y);
    return max(0.0, v * v);
}

void main() {
    vec2 uv = vUV.st;
    vec2 texel = uTD2DInfos[1].res.xy;
    vec4 t = texture(sTD2DInputs[0], uv);
    float Jxx = t.r, Jyy = t.g, Jxy = t.b;

    float tr = Jxx + Jyy;
    float det = Jxx * Jyy - Jxy * Jxy;
    float disc = sqrt(max(0.0, tr * tr * 0.25 - det));
    float l1 = tr * 0.5 + disc;
    float l2 = tr * 0.5 - disc;

    // gradient direction (the brush runs across it)
    vec2 g = vec2(Jxy, l1 - Jxx);
    vec2 dir = dot(g, g) > 1e-12 ? normalize(g) : vec2(1.0, 0.0);
    float A = (l1 + l2) > 1e-9 ? (l1 - l2) / (l1 + l2) : 0.0;

    float alpha = max(uKernel.y, 1e-3);
    float sx = alpha / (A + alpha);
    float sy = (A + alpha) / alpha;
    mat2 M = mat2(dir.x, dir.y, -dir.y, dir.x) * mat2(sx, 0.0, 0.0, sy);

    float radius = max(uKernel.x, 1.0);
    float steps = clamp(radius, 1.0, max(uKernel.w, 1.0));
    float dr = radius / steps;

    vec3 col[SECTORS];
    float var[SECTORS];
    for (int k = 0; k < SECTORS; k++) {
        float ang = float(k) * TAU / float(SECTORS);
        vec3 s1 = vec3(0.0), s2 = vec3(0.0);
        float ws = 0.0;
        for (float r = 1.0; r <= steps + 0.5; r += 1.0) {
            float rr = r * dr;
            for (int a = -2; a <= 2; a++) {
                float th = ang + float(a) * 0.19635;      // +-22.5 degrees in 5 steps
                vec2 o = M * (rr * vec2(cos(th), sin(th)));
                vec3 c = texture(sTD2DInputs[1], uv + o * texel).rgb;
                float w = polyWeight(o.x, o.y);
                s1 += c * w;
                s2 += c * c * w;
                ws += w;
            }
        }
        ws = max(ws, 1e-6);
        col[k] = s1 / ws;
        vec3 v = s2 / ws - col[k] * col[k];
        var[k] = max(dot(v, vec3(0.299, 0.587, 0.114)), 0.0);
    }

    // sharpness: soft weighting by flatness; at the top end pick the flattest sector outright
    vec3 outc = vec3(0.0);
    float wsum = 0.0;
    float q = uKernel.z;
    if (q >= 32.0) {
        float best = var[0];
        outc = col[0];
        for (int k = 1; k < SECTORS; k++)
            if (var[k] < best) { best = var[k]; outc = col[k]; }
    } else {
        for (int k = 0; k < SECTORS; k++) {
            float w = 1.0 / (1.0 + pow(255.0 * sqrt(var[k]), q));
            outc += col[k] * w;
            wsum += w;
        }
        outc /= max(wsum, 1e-6);
    }
    fragColor = TDOutputSwizzle(vec4(outc, 1.0));
}
