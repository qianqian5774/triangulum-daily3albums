const noiseSvg =
  "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160' viewBox='0 0 160 160'><filter id='noise'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/></filter><rect width='160' height='160' filter='url(%23noise)' opacity='0.35'/></svg>";

export function NoiseOverlay() {
  return (
    <div
      className="pointer-events-none fixed inset-0 z-10 opacity-20 mix-blend-overlay"
      aria-hidden="true"
      style={{
        backgroundImage: `url("${noiseSvg}")`,
        backgroundSize: "160px 160px",
        backgroundRepeat: "repeat"
      }}
    />
  );
}
