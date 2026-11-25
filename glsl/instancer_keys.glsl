// Texture Instancer: copies the attributes picked on the parameter pages into fixed names (GLSL POP).
// The #defines above this line are written by InstancerExt.UpdateShader().
// Writes Keys (x sort, y scale, z rotate, w cull), Keys2 (x colour), Face, Upv, Cin, Uvin.

uint pcg(uint v) {
    uint s = v * 747796405u + 2891336453u;
    uint w = ((s >> ((s >> 28u) + 4u)) ^ s) * 277803737u;
    return (w >> 22u) ^ w;
}
float rnd(uint a, uint b) { return float(pcg(a * 1664525u + pcg(b))) / 4294967295.0; }

void main() {
    const uint id = TDIndex();
    if (id >= TDNumElements())
        return;
    Keys[id] = vec4(KEY_SORT, KEY_SCALE, KEY_ROT, KEY_CULL);
    Keys2[id] = vec4(KEY_COLOR, 0.0, 0.0, 0.0);
    Face[id] = VEC_FACE;
    Upv[id] = VEC_UP;
    Cin[id] = COL_IN;
    Uvin[id] = UV_IN;
}
