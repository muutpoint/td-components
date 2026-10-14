// FlipBook: lens blur mask. Black = sharp, white = fully blurred.
uniform vec4 uVignette;  // x sharp area (1 = default), y softness

out vec4 fragColor;

void main() {
    vec2 d2 = (vUV.st - 0.5) * 2.0;           // -1..1 on both axes, so the mask follows the frame shape
    float d = length(d2);
    float inner = 0.6 * uVignette.x;
    float m = smoothstep(inner, inner + max(uVignette.y, 0.01), d);
    fragColor = TDOutputSwizzle(vec4(vec3(m), 1.0));
}
