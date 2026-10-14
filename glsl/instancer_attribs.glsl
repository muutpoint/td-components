// Texture Instancer: per-point instance attributes (GLSL POP, compute).
// Input 0: the points (with Color, added upstream if missing)
// Input 1: analyze POP, one point with Min / Max of P (the bounds)
// Writes: P (with optional noise drift), TexW (texture layer), Iscale, Icolor, Irot, Facing.
// Uniforms are vec4s declared on the Vectors page (auto-declared, do not redeclare):
//   uTex    x texture count, y order mode, z seed, w cycle (textures advanced so far)
//   uScale  x mode, y size, z random variance, w noise frequency
//   uAnim   x time (s), y noise speed, z drift amount, w drift frequency
//   uWave   x axis (0 x, 1 y, 2 z, 3 radial), y phase (cycles), z wavelength, w minimum
//   uColor  x mode, y tint amount, z seed, w use point colour (0/1)
//   uCam    xyz camera position, w face camera (0/1)
//   uRot    x random rotation (deg), y spin (deg/s), z jitter seed, w 0
// Sampler sPalette: palette / colour image.

uint pcg(uint v) {
    uint s = v * 747796405u + 2891336453u;
    uint w = ((s >> ((s >> 28u) + 4u)) ^ s) * 277803737u;
    return (w >> 22u) ^ w;
}
float rnd(uint a, uint b) { return float(pcg(a * 1664525u + pcg(b))) / 4294967295.0; }

float hash3(ivec3 q, uint seed) {
    return float(pcg(uint(q.x) * 73856093u ^ uint(q.y) * 19349663u ^ uint(q.z) * 83492791u ^ pcg(seed))) / 4294967295.0;
}
float vnoise(vec3 p, uint seed) {
    ivec3 i = ivec3(floor(p));
    vec3 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    float n000 = hash3(i, seed), n100 = hash3(i + ivec3(1, 0, 0), seed);
    float n010 = hash3(i + ivec3(0, 1, 0), seed), n110 = hash3(i + ivec3(1, 1, 0), seed);
    float n001 = hash3(i + ivec3(0, 0, 1), seed), n101 = hash3(i + ivec3(1, 0, 1), seed);
    float n011 = hash3(i + ivec3(0, 1, 1), seed), n111 = hash3(i + ivec3(1, 1, 1), seed);
    return mix(mix(mix(n000, n100, f.x), mix(n010, n110, f.x), f.y),
               mix(mix(n001, n101, f.x), mix(n011, n111, f.x), f.y), f.z);
}
float fbm(vec3 p, uint seed) {
    return (vnoise(p, seed) * 0.6 + vnoise(p * 2.1 + 7.7, seed + 9u) * 0.3 + vnoise(p * 4.3 + 3.1, seed + 17u) * 0.1);
}

void main() {
    const uint id = TDIndex();
    if (id >= TDNumElements())
        return;

    uint n = TDNumElements();
    vec3 p = TDIn_P();
    vec3 bmin = TDIn_Min(1, 0);
    vec3 bmax = TDIn_Max(1, 0);
    vec3 bsize = max(bmax - bmin, vec3(1e-6));
    vec3 pn = (p - bmin) / bsize;                  // 0..1 inside the bounds
    uint seed = uint(uTex.z);
    float t = uAnim.x;

    // ---------------------------------------------------------------- texture order
    float count = max(uTex.x, 1.0);
    int order = int(uTex.y + 0.5);
    float key;
    if (order == 0)       key = float(id) / float(max(n, 1u));               // sequential (by point number)
    else if (order == 1)  key = rnd(id, seed);                               // random
    else if (order == 2)  key = pn.x;
    else if (order == 3)  key = pn.y;
    else if (order == 4)  key = pn.z;
    else                  key = clamp(length(pn - 0.5) * 2.0 / 1.7320508, 0.0, 1.0);  // distance from the centre
    float layer;
    if (order == 0)
        layer = mod(float(id) + uTex.w, count);
    else
        layer = mod(floor(min(key, 0.99999) * count) + uTex.w, count);

    // ---------------------------------------------------------------- scale
    int smode = int(uScale.x + 0.5);
    float s = 1.0;
    if (smode == 1) {                                                          // animated noise
        s = fbm(p * uScale.w + vec3(0.0, 0.0, t * uAnim.y), seed + 31u);
        s = smoothstep(0.25, 0.75, s);
    } else if (smode == 2) {                                                   // travelling wave
        int ax = int(uWave.x + 0.5);
        float d = ax == 0 ? pn.x : ax == 1 ? pn.y : ax == 2 ? pn.z : length(pn - 0.5) * 2.0;
        s = 0.5 + 0.5 * sin(6.2831853 * (d / max(uWave.z, 1e-3) - uWave.y));
        s = mix(uWave.w, 1.0, s);
    }
    s *= 1.0 + (rnd(id, seed + 101u) * 2.0 - 1.0) * uScale.z;
    s = max(s, 0.0) * uScale.y;

    // ---------------------------------------------------------------- drift
    if (uAnim.z > 0.0) {
        vec3 q = p * uAnim.w + vec3(t * uAnim.y);
        vec3 off = vec3(fbm(q, seed + 51u), fbm(q + 19.1, seed + 52u), fbm(q + 37.3, seed + 53u)) - 0.5;
        p += off * 2.0 * uAnim.z;
    }

    // ---------------------------------------------------------------- colour
    int cmode = int(uColor.x + 0.5);
    vec4 col = vec4(1.0);
    if (cmode == 1)
        col = textureLod(sPalette, vec2(rnd(id, uint(uColor.z) + 7u), 0.5), 0.0);           // random from palette
    else if (cmode == 2)
        col = textureLod(sPalette, vec2((layer + 0.5) / count, 0.5), 0.0);                 // one colour per texture
    else if (cmode == 3)
        col = textureLod(sPalette, pn.xy, 0.0);                                             // image at the point's XY
    if (uColor.w > 0.5)
        col *= TDIn_Color();
    col.rgb = mix(vec3(1.0), col.rgb, uColor.y);

    // ---------------------------------------------------------------- orientation
    vec3 facing = vec3(0.0, 0.0, 1.0);
    if (uCam.w > 0.5) {
        vec3 d = uCam.xyz - p;
        facing = dot(d, d) > 1e-10 ? normalize(d) : facing;
    }
    float rot = (rnd(id, uint(uRot.z) + 77u) * 2.0 - 1.0) * uRot.x + t * uRot.y * (rnd(id, 5u) < 0.5 ? -1.0 : 1.0);

    P[id] = p;
    TexW[id] = layer;
    Iscale[id] = s;
    Icolor[id] = col;
    Irot[id] = rot;
    Facing[id] = facing;
}
