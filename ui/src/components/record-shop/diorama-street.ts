import type * as Three from "three";
import { createDioramaMaterial } from "./diorama-materials";

type Box = (w: number, h: number, d: number, m: Three.Material, p: [number, number, number], parent?: Three.Object3D) => Three.Mesh;
type Cylinder = (r: number, h: number, m: Three.Material, p: [number, number, number], rotation?: [number, number, number], parent?: Three.Object3D) => Three.Mesh;

// Pavement and asphalt share one continuous, grounded plinth.
export const DIORAMA_SITE = {
  width: 16.2, back: -7.1, pavementFront: 7.1, front: 8.6,
  bottom: -.505, baseTop: -.15, roadTop: -.08
} as const;

export function addStreetDetails(THREE: typeof Three, scene: Three.Scene, box: Box, cylinder: Cylinder, night: boolean) {
  const ink = createDioramaMaterial(THREE, "#292c3b");
  const wood = createDioramaMaterial(THREE, "#c99f73", "wood");
  const paper = createDioramaMaterial(THREE, "#e8e0d4");
  const rust = createDioramaMaterial(THREE, "#c65d45");
  const blue = createDioramaMaterial(THREE, "#5f6480");
  const metal = createDioramaMaterial(THREE, "#aaa5a3");
  const moss = ["#66745b", "#889066", "#4d6351"].map(c => createDioramaMaterial(THREE, c));
  const light = new THREE.MeshStandardMaterial({ color: "#e1d2b8", emissive: "#d69c55", emissiveIntensity: night ? 2 : .25, roughness: .6 });
  // A bounded fragment of street: curb, gutter, asphalt and two worn lane marks.
  const site = DIORAMA_SITE;
  box(site.width, site.roadTop - site.baseTop, site.front - site.pavementFront,
    createDioramaMaterial(THREE, "#5a5d6c", "roof"),
    [0, (site.roadTop + site.baseTop) / 2, (site.front + site.pavementFront) / 2]);
  const curbCount = Math.floor((site.width - .3) / 1.55);
  for (let i = 0; i < curbCount; i++) box(1.53, .19, .3, i % 3 ? paper : metal, [-site.width / 2 + .92 + i * 1.55, site.roadTop + .095, 7.06]);
  box(site.width - .5, .04, .12, ink, [0, site.roadTop + .02, 7.34]);
  for (const x of [-5.5, -1.8, 1.9, 5.6]) box(1.35, .018, .12, paper, [x, -.07, 8.16]);
  for (const x of [-6.1, -2.1, 2.1, 6.1]) {
    box(.64, .022, .45, ink, [x, site.roadTop + .011, 7.5]);
    for (let i = 0; i < 6; i++) box(.035, .012, .35, metal, [x - .25 + i * .1, site.roadTop + .028, 7.5]);
  }
  // Bench, bag of records and a cup: everyday use, with feet on paving.
  for (const x of [3.1, 4.4]) for (const z of [5.95, 6.37]) box(.095, .47, .095, ink, [x, .46, z]);
  for (let i = 0; i < 3; i++) box(1.65, .09, .17, wood, [3.75, .72, 5.97 + i * .2]);
  for (const x of [3.1, 4.4]) box(.07, .75, .07, ink, [x, .90, 5.92]);
  for (let i = 0; i < 2; i++) box(1.65, .14, .065, wood, [3.75, 1.02 + i * .2, 5.92]);
  box(.5, .48, .23, paper, [4.12, 1.005, 6.12]);
  box(.19, .07, .25, ink, [4.12, 1.24, 6.12]);
  cylinder(.07, .15, rust, [3.3, .84, 6.12]);
  // A parked bicycle with a record in its basket. The front door's approach
  // stays clear; this small action belongs to a visitor to this record shop.
  const bike = new THREE.Group(); bike.position.set(-3.9, .235, 6.28); bike.rotation.y = .07; scene.add(bike);
  const bikePaint = createDioramaMaterial(THREE, "#cb6547");
  const tube = (a: [number, number, number], b: [number, number, number], radius: number, material: Three.Material, parent: Three.Object3D = bike) => {
    const start = new THREE.Vector3(...a), end = new THREE.Vector3(...b);
    const direction = end.clone().sub(start);
    const mesh = cylinder(radius, direction.length(), material, [0, 0, 0], [0, 0, 0], parent);
    mesh.position.copy(start.add(end).multiplyScalar(.5));
    mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction.normalize());
  };
  for (const x of [-.67, .67]) {
    const tyre = new THREE.Mesh(new THREE.TorusGeometry(.39, .043, 8, 32), ink); tyre.position.set(x, .43, 0); bike.add(tyre);
    const rim = new THREE.Mesh(new THREE.TorusGeometry(.348, .012, 6, 32), metal); rim.position.copy(tyre.position); bike.add(rim);
    for (let i = 0; i < 12; i++) {
      const a = i * Math.PI / 6;
      tube([x, .43, 0], [x + Math.cos(a) * .345, .43 + Math.sin(a) * .345, 0], .006, metal);
    }
    cylinder(.052, .095, ink, [x, .43, 0], [Math.PI / 2, 0, 0], bike);
  }
  const frame: [number, number, number][] = [[-.67, .43, .035], [-.15, .36, .035], [-.31, .94, .035], [.43, .92, .035], [.67, .43, .035]];
  for (const [a, b] of [[0,1],[0,2],[1,2],[1,3],[2,3],[3,4]]) tube(frame[a], frame[b], .025, bikePaint);
  tube([-.31,.94,.035],[-.35,1.11,.035],.019,metal);
  box(.3,.06,.17,ink,[-.35,1.13,.035],bike);
  tube([.43,.92,.035],[.36,1.19,.035],.02,metal);
  tube([.36,1.19,-.19],[.36,1.19,.22],.02,metal);
  for(const z of [-.19,.22]) tube([.36,1.19,z],[.23,1.19,z],.027,ink);
  cylinder(.095,.045,metal,[-.15,.36,.055],[Math.PI / 2,0,0],bike);
  tube([-.15,.36,.095],[-.03,.24,.095],.014,ink);
  box(.15,.04,.11,ink,[-.03,.24,.095],bike);
  box(.37,.28,.34,wood,[.72,1.02,0],bike);
  box(.27,.30,.085,paper,[.72,1.17,0],bike);
  box(.22,.22,.03,ink,[.72,1.34,-.015],bike);
  tube([-.4,.62,-.035],[-.32,.02,-.24],.018,metal);
  // A modest street lamp and its base, rather than an illuminated backdrop.
  cylinder(.17, .13, ink, [6.62, .29, 5.95]);
  cylinder(.046, 3.6, ink, [6.62, 2.12, 5.95]);
  box(.6, .08, .36, ink, [6.42, 3.95, 5.95]);
  box(.4, .06, .24, light, [6.37, 3.88, 5.95]);
  const lamp = new THREE.PointLight("#d9a363", night ? 5 : .25, 5, 2);
  lamp.position.set(6.37, 3.7, 5.95); scene.add(lamp);

  const printedFace = (w: number, h: number, position: [number, number, number], headline: string, subline: string, background = "#d7c8ae", rotation = 0) => {
    const canvas = document.createElement("canvas"); canvas.width = 512; canvas.height = 640;
    const ctx = canvas.getContext("2d")!;
    ctx.fillStyle = background; ctx.fillRect(0, 0, 512, 640);
    ctx.fillStyle = "#292c3b"; ctx.fillRect(28, 28, 456, 584);
    ctx.fillStyle = "#d6b273"; ctx.textAlign = "center";
    ctx.font = "bold 42px sans-serif"; ctx.fillText(headline, 256, 110);
    ctx.strokeStyle = "#a84d36"; ctx.lineWidth = 14; ctx.beginPath(); ctx.arc(256, 302, 106, 0, Math.PI * 2); ctx.stroke();
    ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(82, 358); ctx.lineTo(362, 192); ctx.lineTo(354, 440); ctx.closePath(); ctx.stroke();
    ctx.fillStyle = "#dfd5c3"; ctx.font = "25px monospace"; ctx.fillText(subline, 256, 520);
    ctx.font = "21px monospace"; ctx.fillText("TRIANGULUM DAILY", 256, 566);
    const texture = new THREE.CanvasTexture(canvas); texture.colorSpace = THREE.SRGBColorSpace; texture.anisotropy = 4;
    const face = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ map: texture, toneMapped: false }));
    face.position.set(...position); face.rotation.y = rotation; scene.add(face); return face;
  };
  // A-frame rests beside the entrance and repeats the interior's print palette.
  const board = box(.85, 1.12, .10, wood, [-2.15, .98, 6.15]); board.rotation.x = -.12;
  const brace = box(.85, 1.12, .10, wood, [-2.15, .98, 5.95]); brace.rotation.x = .24;
  for (const x of [-2.55, -1.75]) box(.065, .27, .075, ink, [x, .36, 6.21]);
  const print = printedFace(.73, .96, [-2.15, .98, 6.216], "DAILY NINE", "08 / 12:30 / 16"); print.rotation.x = -.12;
  // Service-side notice board, away from the main glazing.
  printedFace(1.35, 1.7, [-6.185, 2.05, -.7], "LISTEN", "SOUND / MIND / BODY", "#9d4b38", -Math.PI / 2);
  box(.14, .72, .56, metal, [-6.23, 1.25, -3.8]);
  box(.14, .48, .4, ink, [-6.23, 1.13, -2.97]);
  cylinder(.03, 1.45, metal, [-6.24, 2.32, -3.8]);
  for (let row = 0; row < 3; row++) for (let i = 0; i < 4 - row; i++) {
    box(.032, .15, .48, row % 2 ? rust : wood, [-6.18, .43 + row * .19, -.1 + i * .53 + (row % 2) * .22]);
  }
  // Rear service alley: stacked return crates, a wall light and rain pipe.
  for (let i = 0; i < 2; i++) {
    box(1.12, .44, .64, wood, [-3.7, .45 + i * .47, -6.1]);
    box(.38, .085, .02, ink, [-3.7, .48 + i * .47, -6.431]);
  }
  box(.45, .18, .16, ink, [2.85, 3.28, -5.62]);
  box(.33, .075, .14, light, [2.85, 3.19, -5.62]);
  for (let i = 0; i < 7; i++) box(.72, .065, .035, metal, [-1.1, 2.15 + i * .13, -5.58]);
  // The equipment stays legible against the plain charcoal membrane.
  const leafGeometry = new THREE.SphereGeometry(.11, 7, 5);
  const plant = (x: number, z: number) => {
    cylinder(.27, .48, blue, [x, .465, z]);
    cylinder(.285, .07, ink, [x, .71, z]);
    for (let branch = 0; branch < 5; branch++) {
      const angle = branch * 2.4;
      for (let i = 0; i < 5; i++) {
        const leaf = new THREE.Mesh(leafGeometry, moss[(branch + i) % 3]);
        leaf.scale.set(.65, 1.65, .65); leaf.rotation.z = Math.cos(angle) * .65;
        leaf.position.set(x + Math.cos(angle) * i * .07, .79 + i * .12, z + Math.sin(angle) * i * .07); scene.add(leaf);
      }
    }
  };
  plant(5.72, 6.22); plant(-6.66, -2.15);
  // Warm shop light and an actual open/quiet sign share the release clock.
  box(.6, .46, .13, ink, [-1.35, 2.25, 5.16]);
  const sign = printedFace(.54, .4, [-1.35, 2.25, 5.235], "OPEN", "09 RECORDS");
  const signMap = (sign.material as Three.MeshBasicMaterial).map as Three.CanvasTexture;
  const ctx = (signMap.image as HTMLCanvasElement).getContext("2d")!;
  const windowLights = [-3.5, 3.5].map(x => {
    const glow = new THREE.PointLight("#e8b575", 3, 6, 2); glow.position.set(x, 2.7, 3.6); scene.add(glow); return glow;
  });
  return (count: number) => {
    ctx.fillStyle = "#292c3b"; ctx.fillRect(0, 0, 512, 640);
    ctx.textAlign = "center"; ctx.fillStyle = count ? "#d3aa68" : "#a0a39d";
    ctx.font = "bold 112px sans-serif"; ctx.fillText(count ? "OPEN" : "QUIET", 256, 270);
    ctx.font = "58px monospace"; ctx.fillText(count ? `${count} / 9` : "08:00", 256, 402);
    signMap.needsUpdate = true;
    windowLights.forEach(l => { l.intensity = count ? (night ? 4 : 1.5) : .35; });
  };
}
