// Halftone: glow trails. Keeps the brighter of the new glow and the faded previous frame.
// Input 0: blurred halftone (the glow)
// Input 1: feedback (this shader's previous output)

uniform vec4 uTrail;   // x persistence (0 = no trails)

out vec4 fragColor;

void main() {
    vec4 glow = texture(sTD2DInputs[0], vUV.st);
    vec4 prev = texture(sTD2DInputs[1], vUV.st);
    fragColor = TDOutputSwizzle(max(glow, prev * uTrail.x));
}
