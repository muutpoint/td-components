// Texture Instancer: turns the atlas into a 2D texture array, one layer per texture.
// Input 0: atlas (uGrid.x columns, uGrid.y rows, filled from the top left, row by row)
// The instanced quads pick their layer through the W texture coordinate.

uniform vec4 uGrid;   // x columns, y rows

out vec4 fragColor;

void main() {
    float i = float(uTDCurrentDepth);
    vec2 grid = max(uGrid.xy, vec2(1.0));
    vec2 cell = vec2(mod(i, grid.x), floor(i / grid.x));
    vec2 uv = (vec2(cell.x, grid.y - 1.0 - cell.y) + vUV.st) / grid;
    fragColor = TDOutputSwizzle(texture(sTD2DInputs[0], uv));
}
