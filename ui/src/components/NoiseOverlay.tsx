const textureUrl = `${import.meta.env.BASE_URL}textures/texture-light-noise-512.png`;

export function NoiseOverlay() {
  return (
    <div
      className="noise-overlay pointer-events-none fixed inset-0 z-10"
      aria-hidden="true"
      style={{
        backgroundImage: `url("${textureUrl}")`,
        backgroundSize: "512px 512px",
        backgroundRepeat: "repeat"
      }}
    />
  );
}
