// FlipBook, pass 2: the page-flip ghost.
// Input 0: the page (pass 1)
// Input 1: the page blurred along the flip direction
// Right after a flip, a tilted, smeared copy of the page sits on top and fades out,
// like the corner of the page that was just let go.

uniform vec4 uGhost;   // x on, y opacity, z fade time (s), w time since the flip (s)
uniform vec4 uGhostXf; // x offset x, y offset y, z rotate (degrees), w flip index

out vec4 fragColor;

vec2 rot2(vec2 p, float a) {
    float c = cos(a), s = sin(a);
    return vec2(c * p.x - s * p.y, s * p.x + c * p.y);
}

void main() {
    vec2 uv = vUV.st;
    vec4 page = texture(sTD2DInputs[0], uv);
    if (uGhost.x < 0.5) {
        fragColor = TDOutputSwizzle(page);
        return;
    }
    vec2 res = uTDOutputInfo.res.zw;
    float aspect = res.x / res.y;
    // alternate the direction of the flip on every page so it reads as motion, not as a fixed overlay
    float side = mod(uGhostXf.w, 2.0) < 1.0 ? 1.0 : -1.0;
    vec2 c = (uv - 0.5) * vec2(aspect, 1.0);
    vec2 guv = rot2(c, radians(uGhostXf.z) * side) / vec2(aspect, 1.0) + 0.5 - uGhostXf.xy * vec2(side, 1.0);
    vec4 ghost = texture(sTD2DInputs[1], guv);
    float inside = step(0.0, guv.x) * step(guv.x, 1.0) * step(0.0, guv.y) * step(guv.y, 1.0);
    float k = 1.0 - smoothstep(0.0, max(uGhost.z, 1e-3), uGhost.w);
    fragColor = TDOutputSwizzle(mix(page, ghost, inside * k * uGhost.y));
}
