// Paint, pass 1: structure tensor (Sobel).
// Input 0: the image (already over its background, at the processing size)
// Output: (Jxx, Jyy, Jxy, 1). It is blurred afterwards so brush strokes follow smooth flow lines.

out vec4 fragColor;

vec3 px(vec2 uv, vec2 o) { return texture(sTD2DInputs[0], uv + o * uTD2DInfos[0].res.xy).rgb; }

void main() {
    vec2 uv = vUV.st;
    vec3 a = px(uv, vec2(-1, -1)), b = px(uv, vec2(0, -1)), c = px(uv, vec2(1, -1));
    vec3 d = px(uv, vec2(-1, 0)),                            f = px(uv, vec2(1, 0));
    vec3 g = px(uv, vec2(-1, 1)),  h = px(uv, vec2(0, 1)),  i = px(uv, vec2(1, 1));

    vec3 sx = (c + 2.0 * f + i) - (a + 2.0 * d + g);
    vec3 sy = (g + 2.0 * h + i) - (a + 2.0 * b + c);
    sx *= 0.25;
    sy *= 0.25;
    fragColor = TDOutputSwizzle(vec4(dot(sx, sx), dot(sy, sy), dot(sx, sy), 1.0));
}
