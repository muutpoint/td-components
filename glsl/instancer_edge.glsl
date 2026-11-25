// Texture Instancer: outline around each texture's alpha shape (GLSL TOP, 2D texture array in and out).
// Runs once per layer when the textures or the edge settings change, not every frame.
// uEdge.x mode (1 outline behind the texture, 2 outline only), y width (fraction of the texture), z softness (0-1)
// uAspect: per-layer image aspect (w / h), so the ring is even after the quad is stretched back to the image shape.

uniform vec4 uEdge;
uniform vec4 uEdgeColor;
uniform samplerBuffer uAspect;

out vec4 fragColor;

void main() {
    float layer = float(uTDCurrentDepth);
    vec2 uv = vUV.st;
    vec4 c = texture(sTD2DArrayInputs[0], vec3(uv, layer));
    float aspect = max(texelFetch(uAspect, int(uTDCurrentDepth)).x, 1e-3);
    // the quad is (1, 1/aspect) or (aspect, 1): a ring of even width needs these uv radii
    vec2 r = uEdge.y * (aspect >= 1.0 ? vec2(1.0, aspect) : vec2(1.0 / aspect, 1.0));

    const int ANGLES = 16;
    const int RINGS = 4;
    float hard = 0.0, softSum = 0.0;
    for (int k = 1; k <= RINGS; k++) {
        float ringMax = 0.0;
        for (int i = 0; i < ANGLES; i++) {
            float a = 6.2831853 * (float(i) + 0.5 * float(k & 1)) / float(ANGLES);
            vec2 o = vec2(cos(a), sin(a)) * r * float(k) / float(RINGS);
            ringMax = max(ringMax, texture(sTD2DArrayInputs[0], vec3(uv + o, layer)).a);
        }
        hard = max(hard, ringMax);
        softSum += ringMax;
    }
    float m = mix(hard, softSum / float(RINGS), clamp(uEdge.z, 0.0, 1.0));
    float ring = clamp(m - c.a, 0.0, 1.0);
    vec4 oc = vec4(uEdgeColor.rgb * uEdgeColor.a, uEdgeColor.a) * ring;   // premultiplied
    fragColor = TDOutputSwizzle(uEdge.x < 1.5 ? c + oc * (1.0 - c.a) : oc);
}
