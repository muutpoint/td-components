// Texture Instancer: per-point instance attributes (GLSL POP, compute).
// Input 0: the points from glsl_keys (P, Keys, Keys2, Face, Upv, Cin, Uvin)
// Input 1: analyze POP, one point with MinKeys/MaxKeys, MinKeys2/MaxKeys2, MinP/MaxP
// Array uInfo (texture buffer, one vec4 per texture in texture order): x layer, y aspect, z brightness, w hue
// Writes: P, TexW (array layer), Iscale (xyz), Irot (deg), Facing, Upd, Icolor, Iactive.
//
// Uniforms (vec4, declared on the Vectors page, do not redeclare):
//   uTex   x textures loaded, y assign mode (0 seq, 1 random, 2 attribute, 3 noise, 4 image), z seed, w cycle clock
//   uSort  x offset (fraction of the set), y repeat, z steps, w jitter
//   uSort2 x range start, y range end (0-1 of the set), z auto range, w cycle offset per instance
//   uSortR x manual min, y manual max, z noise frequency, w noise clock
//   uImg   x map (0 XY, 1 XZ, 2 ZY, 3 point Tex), y match (0 brightness, 1 hue), z stretch to set, w unused
//   uScale x size, y random variance, z stretch X, w stretch Y
//   uScl2  x scale by (0 off, 1 attribute, 2 noise, 3 wave), y auto range, z manual min, w manual max
//   uScl3  x size at min, y size at max, z noise frequency or wavelength, w clock (noise time or wave cycles)
//   uRev   x reveal, y reveal by (0 assign key, 1 index, 2 random, 3 scale key), z softness, w invert
//   uRot   x facing (0 camera, 1 attribute, 2 random), y random rotate (deg), z spin clock (deg), w random spin direction
//   uRot2  x degrees across the attribute range, y auto range, z manual min, w manual max
//   uRot3  x random tilt (deg), y push along the facing attribute, zw unused
//   uCam   xyz camera position
//   uPos   xyz offset, w jitter
//   uPos2  x drift amount, y drift frequency, z drift clock, w unused
//   uCull  x density (0-1 kept), y mode (0 off, 1 keep above, 2 keep below), z threshold, w unused
//   uCol   x mode (0 off, 1 random, 2 per texture, 3 attribute, 4 image, 5 point colour), y tint amount, z opacity, w unused
//   uTint  rgba tint
// Samplers: sPalette (palette or colour image), sGuide (the image the photo-mosaic matches)

uint pcg(uint v) {
    uint s = v * 747796405u + 2891336453u;
    uint w = ((s >> ((s >> 28u) + 4u)) ^ s) * 277803737u;
    return (w >> 22u) ^ w;
}
float rnd(uint a, uint b) { return float(pcg(a * 1664525u + pcg(b))) / 4294967295.0; }

float norm01(float v, float lo, float hi) {
    return abs(hi - lo) > 1e-9 ? clamp((v - lo) / (hi - lo), 0.0, 1.0) : 0.5;
}
float key01(float v, float lo, float hi, float autoRange, float mlo, float mhi) {
    return autoRange > 0.5 ? norm01(v, lo, hi) : norm01(v, mlo, mhi);
}
float noise01(vec4 q) { return clamp(0.5 + 0.7 * TDSimplexNoise(q), 0.0, 1.0); }
vec4 info(int i) { return texelFetch(uInfo, i); }

void main() {
    const uint id = TDIndex();
    if (id >= TDNumElements())
        return;

    uint np = TDNumElements();
    uint seed = uint(uTex.z);
    vec3 p = TDIn_P();
    vec4 K = TDIn_Keys();
    vec4 kmin = TDIn_MinKeys(1, 0);
    vec4 kmax = TDIn_MaxKeys(1, 0);
    vec3 bmin = TDIn_MinP(1, 0);
    vec3 bmax = TDIn_MaxP(1, 0);
    vec3 pn = (p - bmin) / max(bmax - bmin, vec3(1e-6));   // 0..1 inside the bounds

    // ------------------------------------------------------------ which texture
    int count = int(uTex.x + 0.5);
    int last = max(count, 1) - 1;
    int lo = int(floor(clamp(min(uSort2.x, uSort2.y), 0.0, 1.0) * float(last) + 0.5));
    int hi = int(floor(clamp(max(uSort2.x, uSort2.y), 0.0, 1.0) * float(last) + 0.5));
    int n = hi - lo + 1;
    float fn = float(n);

    int mode = int(uTex.y + 0.5);
    vec2 iuv = uImg.x < 0.5 ? pn.xy : uImg.x < 1.5 ? pn.xz : uImg.x < 2.5 ? pn.zy : TDIn_Uvin();
    float t;     // 0..1 position in the set, before offset / repeat (also the reveal key)
    float rk;    // rank inside the range
    if (mode == 4 && count > 0) {
        // photo-mosaic: the texture whose brightness (or hue) is nearest to the guide image here
        vec4 g = textureLod(sGuide, iuv, 0.0);
        bool byHue = uImg.y > 0.5;
        float target = byHue ? TDRGBToHSV(g.rgb).x : dot(g.rgb, vec3(0.2126, 0.7152, 0.0722));
        float vlo = byHue ? info(lo).w : info(lo).z;
        float vhi = byHue ? info(hi).w : info(hi).z;
        if (uImg.z > 0.5)
            target = mix(vlo, vhi, target);
        int a = lo, b = hi;
        while (a < b) {                       // first entry >= target (the set is sorted by it)
            int m = (a + b) / 2;
            float v = byHue ? info(m).w : info(m).z;
            if (v < target) a = m + 1; else b = m;
        }
        if (a > lo) {
            float va = byHue ? info(a).w : info(a).z;
            float vb = byHue ? info(a - 1).w : info(a - 1).z;
            if (abs(vb - target) < abs(va - target)) a -= 1;
        }
        rk = float(a - lo) + floor((rnd(id, seed + 3u) - 0.5) * uSort.w * fn + 0.5);
        rk = clamp(rk, 0.0, fn - 1.0);
        t = rk / max(fn - 1.0, 1.0);
    } else {
        if (mode == 0)      t = float(id) / fn;                                    // one texture per point
        else if (mode == 1) t = rnd(id, seed);
        else if (mode == 2) t = key01(K.x, kmin.x, kmax.x, uSort2.z, uSortR.x, uSortR.y);
        else                t = noise01(vec4(p * uSortR.z, uSortR.w));
        if (uSort.z >= 1.0 && mode != 0)
            t = min(floor(t * uSort.z) / uSort.z, 1.0);
        rk = floor(min(t, 0.99999) * fn * uSort.y + uSort.x * fn + 1e-4);
        rk += floor(uSort.w * rnd(id, seed + 3u) * fn);
        if (mode == 0) t = float(id) / float(max(np, 2u) - 1u);
    }
    rk += floor(uTex.w + uSort2.w * rnd(id, seed + 5u) * fn);     // flip book: step through the set
    int rank = lo + int(mod(rk, fn));
    vec4 inf = count > 0 ? info(rank) : vec4(0.0, 1.0, 0.0, 0.0);

    // ------------------------------------------------------------ size
    float aspect = max(inf.y, 1e-4);
    vec2 asp = aspect >= 1.0 ? vec2(1.0, 1.0 / aspect) : vec2(aspect, 1.0);   // longest side = Size
    float s = uScale.x * max(0.0, 1.0 + (rnd(id, seed + 7u) * 2.0 - 1.0) * uScale.y);
    int sby = int(uScl2.x + 0.5);
    float sk = key01(K.y, kmin.y, kmax.y, uScl2.y, uScl2.z, uScl2.w);
    if (sby == 1)
        s *= mix(uScl3.x, uScl3.y, sk);
    else if (sby == 2)
        s *= mix(uScl3.x, uScl3.y, smoothstep(0.15, 0.85, noise01(vec4(p * uScl3.z, uScl3.w))));
    else if (sby == 3)
        s *= mix(uScl3.x, uScl3.y, 0.5 + 0.5 * sin(6.2831853 * (sk / max(uScl3.z, 1e-3) - uScl3.w)));

    // reveal: instances grow in along a key as Reveal goes 0 -> 1
    int rby = int(uRev.y + 0.5);
    float rkey = rby == 0 ? t : rby == 1 ? float(id) / float(max(np, 2u) - 1u) : rby == 2 ? rnd(id, seed + 13u) : sk;
    if (uRev.w > 0.5)
        rkey = 1.0 - rkey;
    float soft = max(uRev.z, 1e-4);
    float rv = clamp((uRev.x * (1.0 + soft) - rkey) / soft, 0.0, 1.0);
    rv = rv * rv * (3.0 - 2.0 * rv);
    s *= rv;
    vec3 scl = vec3(asp.x * uScale.z, asp.y * uScale.w, 1.0) * s;

    // ------------------------------------------------------------ orientation
    int face = int(uRot.x + 0.5);
    vec3 attrFace = TDIn_Face();
    vec3 fwd;
    if (face == 0)
        fwd = uCam.xyz - p;
    else if (face == 1)
        fwd = attrFace;
    else
        fwd = vec3(rnd(id, seed + 17u), rnd(id, seed + 19u), rnd(id, seed + 23u)) * 2.0 - 1.0;
    fwd = dot(fwd, fwd) > 1e-12 ? normalize(fwd) : vec3(0.0, 0.0, 1.0);
    if (uRot3.x > 0.0) {
        vec3 side = cross(fwd, vec3(rnd(id, seed + 29u), rnd(id, seed + 31u), rnd(id, seed + 37u)) - 0.5);
        if (dot(side, side) > 1e-10)
            fwd = TDRotateOnAxis(radians(uRot3.x) * (rnd(id, seed + 41u) * 2.0 - 1.0), normalize(side)) * fwd;
    }
    vec3 up = TDIn_Upv();
    if (length(cross(fwd, up)) < 1e-4)
        up = abs(fwd.y) < 0.95 ? vec3(0.0, 1.0, 0.0) : vec3(0.0, 0.0, 1.0);
    float dir = (uRot.w > 0.5 && rnd(id, seed + 43u) < 0.5) ? -1.0 : 1.0;
    float rot = (rnd(id, seed + 47u) * 2.0 - 1.0) * uRot.y + uRot.z * dir
              + key01(K.z, kmin.z, kmax.z, uRot2.y, uRot2.z, uRot2.w) * uRot2.x;

    // ------------------------------------------------------------ position
    if (dot(attrFace, attrFace) > 1e-12)
        p += normalize(attrFace) * uRot3.y;
    p += uPos.xyz;
    p += (vec3(rnd(id, seed + 53u), rnd(id, seed + 59u), rnd(id, seed + 61u)) * 2.0 - 1.0) * uPos.w;
    if (uPos2.x > 0.0) {
        vec3 q = TDIn_P() * uPos2.y;
        p += vec3(TDSimplexNoise(vec4(q, uPos2.z)), TDSimplexNoise(vec4(q + 17.3, uPos2.z)),
                  TDSimplexNoise(vec4(q + 41.7, uPos2.z))) * uPos2.x;
    }

    // ------------------------------------------------------------ culling
    float act = (rv > 0.0 && rnd(id, seed + 67u) < uCull.x) ? 1.0 : 0.0;
    int cm = int(uCull.y + 0.5);
    float ck = norm01(K.w, kmin.w, kmax.w);
    if ((cm == 1 && ck < uCull.z) || (cm == 2 && ck > uCull.z))
        act = 0.0;

    // ------------------------------------------------------------ colour
    int cmode = int(uCol.x + 0.5);
    vec4 col = vec4(1.0);
    if (cmode == 1)
        col = textureLod(sPalette, vec2(rnd(id, seed + 71u), 0.5), 0.0);
    else if (cmode == 2)
        col = textureLod(sPalette, vec2((float(rank) + 0.5) / float(max(count, 1)), 0.5), 0.0);
    else if (cmode == 3)
        col = textureLod(sPalette, vec2(norm01(TDIn_Keys2().x, TDIn_MinKeys2(1, 0).x, TDIn_MaxKeys2(1, 0).x), 0.5), 0.0);
    else if (cmode == 4)
        col = textureLod(sPalette, iuv, 0.0);
    else if (cmode == 5)
        col = TDIn_Cin();
    col.rgb = mix(vec3(1.0), col.rgb, uCol.y);
    col *= uTint;
    col.a *= uCol.z;

    P[id] = p;
    TexW[id] = inf.x;
    Iscale[id] = scl;
    Irot[id] = rot;
    Facing[id] = fwd;
    Upd[id] = up;
    Icolor[id] = col;
    Iactive[id] = act;
}
