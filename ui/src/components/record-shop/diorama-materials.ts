import type * as Three from "three";

type DioramaMaterialKind = "paint" | "wood" | "roof" | "metal";

// Neutral, fine surface grain. Roof membranes have no painted construction
// grid: their outline and highlights come from the actual edge geometry.
export function createDioramaMaterial(THREE: typeof Three, color: string, kind: DioramaMaterialKind = "paint") {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 256;
  const ctx = canvas.getContext("2d")!;
  ctx.fillStyle = color;
  ctx.fillRect(0, 0, 256, 256);
  let seed = 71;
  const random = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
  for (let i = 0; i < 4800; i++) {
    ctx.fillStyle = i % 2 ? "rgba(255,255,255,.025)" : "rgba(0,0,0,.025)";
    const x = random() * 256, y = random() * 256;
    ctx.fillRect(x, y, kind === "wood" ? 8 + random() * 48 : 1, kind === "wood" ? .45 : 1);
  }
  if (kind === "wood") {
    ctx.strokeStyle = "rgba(59,31,12,.07)";
    ctx.lineWidth = .65;
    for (let y = 4; y < 256; y += 7) {
      ctx.beginPath(); ctx.moveTo(0, y);
      ctx.bezierCurveTo(70, y - 5, 170, y + 6, 256, y - 2); ctx.stroke();
    }
  }
  const map = new THREE.CanvasTexture(canvas);
  map.colorSpace = THREE.SRGBColorSpace;
  map.minFilter = THREE.LinearMipmapLinearFilter;
  map.magFilter = THREE.LinearFilter;
  map.anisotropy = 4;
  const material = new THREE.MeshStandardMaterial({
    map,
    // These are powder-coated miniature parts, not black mirrors. Keeping the
    // metal response mostly diffuse preserves hue and value in the unlit faces.
    roughness: kind === "wood" ? .73 : kind === "roof" ? .72 : kind === "metal" ? .56 : .8,
    metalness: kind === "metal" ? .18 : kind === "roof" ? .08 : 0
  });
  if (kind === "metal" || kind === "roof") {
    // A restrained painted-material lift holds blue-grey construction detail
    // in cast shadow; it is not a glow and remains below the direct lights.
    material.emissive.set(color);
    material.emissiveIntensity = kind === "metal" ? .055 : .022;
  }
  return material;
}

export function createDioramaGlass(THREE: typeof Three, night: boolean) {
  // One transparent pass: no cubemap, screen-space reflection or refraction
  // target. The static view-dependent tint provides enough physical evidence
  // for glazing while preserving the room behind it.
  return new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, side: THREE.DoubleSide, forceSinglePass: true,
    uniforms: {
      tint: { value: new THREE.Color(night ? "#7188ba" : "#799ab3") },
      reflection: { value: new THREE.Color(night ? "#c4d1ea" : "#d8e8f3") },
      baseAlpha: { value: night ? .155 : .135 },
      edgeAlpha: { value: night ? .39 : .36 }
    },
    vertexShader: `varying vec3 vNormal; varying vec3 vView; varying vec3 vWorld;
      void main() { vec4 p = modelViewMatrix * vec4(position, 1.0);
        vWorld = (modelMatrix * vec4(position, 1.0)).xyz;
        vNormal = normalize(normalMatrix * normal); vView = normalize(-p.xyz);
        gl_Position = projectionMatrix * p; }`,
    fragmentShader: `uniform vec3 tint; uniform vec3 reflection; uniform float baseAlpha; uniform float edgeAlpha;
      varying vec3 vNormal; varying vec3 vView; varying vec3 vWorld;
      void main() {
        float grazing = 1.0 - abs(dot(normalize(vNormal), normalize(vView)));
        float fresnel = pow(clamp(grazing, 0.0, 1.0), 1.72);
        float vertical = smoothstep(-.65, 3.9, vWorld.y);
        // A pair of broad, uneven environmental bands makes a pane legible
        // without sampling a cubemap or introducing a second reflection pass.
        float broadBand = .5 + .5 * sin(vWorld.y * 1.85 + vWorld.x * .34 - vWorld.z * .21);
        float fineVariation = .5 + .5 * sin(vWorld.x * 2.15 + vWorld.z * 1.12);
        float reflected = clamp(.16 + fresnel * .84 + vertical * .14 + broadBand * .14, 0.0, 1.0);
        vec3 glassColor = mix(tint, reflection, reflected);
        float alpha = baseAlpha + fresnel * edgeAlpha + broadBand * .072 + fineVariation * .026;
        gl_FragColor = vec4(glassColor, alpha);
        #include <colorspace_fragment>
      }`
  });
}

export function createDioramaWorldMaterial(THREE: typeof Three, night: boolean) {
  // This is a closed, cheap backdrop bowl rather than a background image plus
  // an unrelated floor. The same continuous field is visible above, beside,
  // and below the miniature at every permitted orbit angle.
  return new THREE.ShaderMaterial({
    side: THREE.BackSide,
    depthWrite: false,
    uniforms: {
      sky: { value: new THREE.Color(night ? "#3c4567" : "#c8d3e4") },
      horizon: { value: new THREE.Color(night ? "#222942" : "#e9e5e6") },
      ground: { value: new THREE.Color(night ? "#0c1228" : "#d1cdd6") }
    },
    vertexShader: `varying vec3 vLocalDirection;
      void main() {
        vLocalDirection = normalize(position);
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }`,
    fragmentShader: `uniform vec3 sky; uniform vec3 horizon; uniform vec3 ground;
      varying vec3 vLocalDirection;
      void main() {
        float height = clamp(vLocalDirection.y * .5 + .5, 0.0, 1.0);
        float skyMix = smoothstep(.48, .96, height);
        float groundMix = smoothstep(.08, .52, height);
        vec3 lowerField = mix(ground, horizon, groundMix);
        vec3 color = mix(lowerField, sky, skyMix);
        float horizonLift = exp(-pow(vLocalDirection.y * 3.25, 2.0)) * .055;
        color += horizonLift;
        gl_FragColor = vec4(color, 1.0);
        #include <colorspace_fragment>
      }`
  });
}
