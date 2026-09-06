import type * as Three from "three";
import { createDioramaMaterial } from "./diorama-materials";

type Box = (w: number, h: number, d: number, m: Three.Material, p: [number, number, number], parent?: Three.Object3D) => Three.Mesh;
type Cylinder = (r: number, h: number, m: Three.Material, p: [number, number, number], rotation?: [number, number, number], parent?: Three.Object3D) => Three.Mesh;

// A real, furnished volume behind the glazing. Front and right views see the
// same listening table, stock, counter and left wall, with open sightlines.
export function addShopInterior(THREE: typeof Three, scene: Three.Object3D, box: Box, cylinder: Cylinder, night: boolean) {
  const oak = createDioramaMaterial(THREE, "#c99f73", "wood");
  const edge = createDioramaMaterial(THREE, "#8d795a", "wood");
  const dark = createDioramaMaterial(THREE, "#282b39");
  const paper = createDioramaMaterial(THREE, "#efe7d9");
  const coral = createDioramaMaterial(THREE, "#c65d45");
  const brass = new THREE.MeshStandardMaterial({ color: "#dcae63", roughness: .48, metalness: .42 });
  const vinyl = new THREE.MeshStandardMaterial({ color: "#171a24", roughness: .36, metalness: .12 });
  const bulb = new THREE.MeshBasicMaterial({ color: "#f7d7a0", toneMapped: false });
  const dummy = new THREE.Object3D();
  const color = new THREE.Color();
  const sleeveGeometry = new THREE.BoxGeometry(.045, .48, .42);
  const spineGeometry = new THREE.BoxGeometry(.026, .012, .005);
  const sleeveMaterial = new THREE.MeshStandardMaterial({ roughness: .85 });
  const spineMaterial = new THREE.MeshBasicMaterial({ color: "#c9a66c" });
  const recordColors = ["#282b39", "#62677f", "#282b39", "#c65d45", "#282b39", "#e3d8c7", "#8b7184", "#282b39", "#c89d62"];

  const records = (count: number, x: number, y: number, z: number, step: number, parent: Three.Object3D) => {
    const stock = new THREE.InstancedMesh(sleeveGeometry, sleeveMaterial, count);
    const labels = new THREE.InstancedMesh(spineGeometry, spineMaterial, count * 2);
    for (let i = 0; i < count; i++) {
      const h = .94 + (i % 7) * .013;
      dummy.position.set(x + step * i, y, z);
      dummy.rotation.set(0, 0, (i % 19 === 0 ? -.07 : 0));
      dummy.scale.set(1, h, 1); dummy.updateMatrix(); stock.setMatrixAt(i, dummy.matrix);
      color.set(recordColors[(i * 7) % recordColors.length]); stock.setColorAt(i, color);
      for (let j = 0; j < 2; j++) {
        dummy.position.set(x + step * i, y + (j ? -.13 : .13), z + .215);
        dummy.rotation.set(0, 0, 0); dummy.scale.set(1, 1, 1); dummy.updateMatrix(); labels.setMatrixAt(i * 2 + j, dummy.matrix);
      }
    }
    stock.instanceMatrix.needsUpdate = true;
    labels.instanceMatrix.needsUpdate = true;
    if (stock.instanceColor) stock.instanceColor.needsUpdate = true;
    parent.add(stock, labels);
  };

  const covers = Array.from({ length: 8 }, (_, i) => {
    const canvas = document.createElement("canvas"); canvas.width = canvas.height = 256;
    const ctx = canvas.getContext("2d")!;
    ctx.fillStyle = ["#282b39", "#dcae63", "#c65d45", "#777b94", "#efe7d9", "#6d4b59", "#c99f73", "#62677f"][i];
    ctx.fillRect(0, 0, 256, 256);
    ctx.strokeStyle = i % 2 ? "#372c27" : "#c39759"; ctx.lineWidth = 2;
    ctx.strokeRect(9, 9, 238, 238);
    ctx.fillStyle = i % 2 ? "#312a29" : "#d1a464";
    ctx.font = "bold 14px sans-serif"; ctx.fillText("TRI / 0" + (i + 1), 22, 31);
    ctx.font = "10px monospace"; ctx.fillText(["AFTER HOURS", "BLUE ROOM", "SIDE A", "SLOW MORNING", "CITY NOTES", "EVENING AIR", "NINE RECORDS", "LISTEN AGAIN"][i], 22, 230);
    ctx.save(); ctx.translate(128, 126); ctx.rotate(i * .3);
    if (i % 3 === 0) {
      for (let r = 27; r <= 72; r += 15) { ctx.beginPath(); ctx.arc(0, 0, r, 0, Math.PI * 2); ctx.stroke(); }
      ctx.fillRect(-4, -78, 8, 156);
    } else if (i % 3 === 1) {
      ctx.beginPath(); ctx.moveTo(0, -78); ctx.lineTo(69, 42); ctx.lineTo(-69, 42); ctx.closePath(); ctx.stroke();
      ctx.beginPath(); ctx.arc(0, 0, 48, 0, Math.PI * 2); ctx.stroke();
    } else {
      for (let j = 0; j < 6; j++) { ctx.globalAlpha = .45 + j * .08; ctx.fillRect(-75 + j * 27, -63 + j * 7, 15, 116 - j * 7); }
    }
    ctx.restore();
    const map = new THREE.CanvasTexture(canvas); map.colorSpace = THREE.SRGBColorSpace; map.anisotropy = 4;
    return new THREE.MeshStandardMaterial({ map, roughness: .8, emissive: "#ffffff", emissiveMap: map, emissiveIntensity: night ? .12 : .03 });
  });
  const cover = (i: number, size: number, x: number, y: number, z: number, parent: Three.Object3D = scene) => {
    box(size + .05, size + .05, .045, edge, [x, y, z], parent);
    const face = new THREE.Mesh(new THREE.PlaneGeometry(size, size), covers[i % covers.length]);
    face.position.set(x, y, z + .024); parent.add(face);
  };
  const bookcase = (width: number, parent: Three.Object3D) => {
    // The back fits between the uprights. Previously their exposed end faces
    // occupied the same plane, producing a comb of z-fighting at camera zoom.
    box(width - .18, 2.85, .08, edge, [0, 1.81, -.27], parent);
    box(width - .20, 2.7, .02, dark, [0, 1.84, -.218], parent);
    for (const x of [-width / 2 + .045, width / 2 - .045]) box(.09, 2.87, .62, oak, [x, 1.81, 0], parent);
    box(.09, 2.87, .51, oak, [0, 1.81, .055], parent);
    for (let row = 0; row < 5; row++) {
      const y = .48 + row * .56;
      const span = (width - .27) / 2;
      for (const x of [-(width - .09) / 4, (width - .09) / 4]) box(span, .065, .51, oak, [x, y, .055], parent);
      if (row < 4) records(Math.floor((width - .2) / .065), -width / 2 + .13, y + .275, .03, .065, parent);
    }
    box(width + .08, .085, .66, oak, [0, 3.2875, 0], parent);
  };

  for (const z of [-3.5, -.6, 2.3]) {
    const group = new THREE.Group(); group.position.set(-5.43, 0, z); group.rotation.y = Math.PI / 2; scene.add(group);
    bookcase(2.82, group);
  }
  // Rear wall combines dense spine stock and a deliberate face-out selection.
  for (const x of [-3.7, 0, 3.7]) {
    const group = new THREE.Group(); group.position.set(x, 0, -4.83); scene.add(group); bookcase(3.58, group);
  }
  for (let i = 0; i < 9; i++) cover(i, .55, -4.75 + i * 1.16, 2.9, -4.46);

  const bin = (width: number, x: number, z: number, rotation = 0) => {
    const g = new THREE.Group(); g.position.set(x, 0, z); g.rotation.y = rotation; scene.add(g);
    box(width, .65, .78, oak, [0, .745, 0], g);
    box(width - .1, .06, .66, dark, [0, 1.08, 0], g);
    box(width, .15, .055, edge, [0, 1.12, -.36], g);
    for (const bx of [-width / 2 + .16, width / 2 - .16]) for (const bz of [-.27, .27]) box(.075, .09, .075, dark, [bx, .385, bz], g);
    const bays = Math.max(1, Math.round(width / .8));
    for (let bay = 0; bay < bays; bay++) {
      const bx = -width / 2 + (bay + .5) * width / bays;
      box(.22, .065, .016, dark, [bx, .91, .402], g);
      for (let row = 0; row < 6; row++) {
        const record = box(.52, .54, .035, row % 3 ? dark : paper, [bx, 1.30 + row * .008, -.23 + row * .082], g);
        record.rotation.x = -.13;
      }
      cover(bay + Math.round(x + 10), .47, bx, 1.3, .245, g);
    }
  };
  bin(2.25, -3.5, 3.65);
  bin(1.24, 4.95, 3.64);
  bin(2.75, 4.8, -.9, Math.PI / 2);

  // Listening island belongs to both front and right windows. Its open lower
  // shelf, turntable, CRT, amplifier and headphones communicate actual use.
  const island = new THREE.Group(); island.position.set(2.82, 0, 1.62); scene.add(island);
  for (const x of [-1.4, 1.4]) for (const z of [-.56, .56]) box(.1, .83, .1, dark, [x, .77, z], island);
  box(3.12, .1, 1.44, oak, [0, .48, 0], island);
  box(3.25, .13, 1.5, oak, [0, 1.20, 0], island);
  records(26, -1.36, .8, .1, .058, island);
  box(.85, .4, .8, dark, [.98, .77, .1], island);
  box(.77, .26, .035, createDioramaMaterial(THREE, "#46474c"), [.98, .8, .519], island);
  for (let i = 0; i < 3; i++) cylinder(.04, .045, brass, [.79 + i * .17, .79, .55], [Math.PI / 2, 0, 0], island);
  box(1.02, .11, .7, dark, [-.91, 1.315, .05], island);
  cylinder(.29, .03, vinyl, [-.96, 1.388, .06], [0, 0, 0], island);
  cylinder(.077, .035, coral, [-.96, 1.406, .06], [0, 0, 0], island);
  box(.026, .032, .43, brass, [-.58, 1.42, .02], island);
  box(.07, .045, .09, dark, [-.58, 1.415, .23], island);
  box(.89, .79, .55, dark, [.15, 1.69, -.10], island);
  box(.71, .58, .035, createDioramaMaterial(THREE, "#40464b"), [.15, 1.70, .187], island);
  box(.62, .45, .015, new THREE.MeshStandardMaterial({ color: "#202330", roughness: .3, emissive: "#75798f", emissiveIntensity: .12 }), [.15, 1.73, .21], island);
  cylinder(.023, .024, brass, [.45, 1.40, .214], [Math.PI / 2, 0, 0], island);
  const headphones = new THREE.Mesh(new THREE.TorusGeometry(.2, .023, 8, 24, Math.PI), dark);
  headphones.position.set(1.05, 1.59, .15); island.add(headphones);
  for (const x of [.85, 1.25]) box(.08, .2, .14, dark, [x, 1.53, .15], island);
  // Woven rug, clear of the exterior paving and attached to the room floor.
  const rug = createDioramaMaterial(THREE, "#a94c3d", "wood");
  box(3.55, .014, 2.04, rug, [2.82, .362, 1.62]);
  for (const z of [.66, 2.58]) box(3.4, .005, .055, paper, [2.82, .373, z]);

  const counter = new THREE.Group(); counter.position.set(-1.25, 0, -2.05); scene.add(counter);
  box(2.55, .93, 1.13, oak, [0, .855, 0], counter);
  box(2.34, .72, .04, coral, [0, .87, .585], counter);
  for (let row = 0; row < 5; row++) for (let col = 0; col < 18; col++) cylinder(.027, .012, dark, [-1.05 + col * .123, .59 + row * .14, .612], [Math.PI / 2, 0, 0], counter);
  box(2.72, .12, 1.28, oak, [0, 1.38, 0], counter);
  box(.55, .09, .38, paper, [.65, 1.48, .19], counter);
  box(.6, .05, .43, dark, [.65, 1.535, .19], counter);
  cylinder(.075, .16, coral, [.10, 1.52, .20], [0, 0, 0], counter);
  cylinder(.18, .04, dark, [-.78, 1.47, -.16], [0, 0, 0], counter);
  cylinder(.025, .48, brass, [-.78, 1.72, -.16], [0, 0, 0], counter);
  const shade = new THREE.Mesh(new THREE.ConeGeometry(.23, .24, 24, 1, true), dark);
  shade.position.set(-.78, 1.98, -.16); counter.add(shade);
  cylinder(.14, .02, bulb, [-.78, 1.88, -.16], [0, 0, 0], counter);
  // Hanging plant: separate stems and leaves, rather than a faceted green ball.
  const leaves = ["#3d6557", "#59846b", "#91a36c"].map(c => createDioramaMaterial(THREE, c));
  const leafGeo = new THREE.SphereGeometry(1, 7, 5);
  const plant = (x: number, y: number, z: number, scale = 1, hanging = false) => {
    const pot = new THREE.Mesh(new THREE.CylinderGeometry(.23 * scale, .18 * scale, .34 * scale, 20), dark);
    pot.position.set(x, y, z); scene.add(pot);
    cylinder(.24 * scale, .045 * scale, dark, [x, y + .15 * scale, z]);
    for (let branch = 0; branch < 7; branch++) {
      const a = branch * 2.4;
      for (let i = 0; i < 5; i++) {
        const leaf = new THREE.Mesh(leafGeo, leaves[(branch + i) % 3]);
        leaf.scale.set(.085 * scale, .16 * scale, .033 * scale);
        leaf.rotation.set(.4, a, .75 * Math.cos(a));
        const radius = (.10 + i * .065) * scale;
        leaf.position.set(x + Math.cos(a) * radius, y + (.22 + (hanging ? -.09 : .10) * i) * scale, z + Math.sin(a) * radius);
        scene.add(leaf);
      }
    }
    if (hanging) for (const dx of [-.14, .14]) cylinder(.009, .54, brass, [x + dx, y + .40, z]);
  };
  plant(-4.65, 2.9, 3.9, 1.1, true);
  plant(5.25, .6, 2.15, 1.2);
  plant(3.98, 1.45, 1.28, .65);
  plant(-4.75, 3.43, -3.7, .7);

  // Visible ceiling tracks and warm pools, limited to the shop interior.
  for (const x of [-3.3, 2.7]) {
    box(.075, .08, 8.1, dark, [x, 3.44, -.3]);
    for (const z of [-3.5, -.3, 3]) {
      cylinder(.065, .13, dark, [x, 3.31, z]);
      cylinder(.052, .012, bulb, [x, 3.236, z]);
    }
  }
  const lamps = [[-3.2, 2.8, 1.1], [2.9, 2.85, 1.7], [0, 2.85, -3.2]].map(p => {
    const light = new THREE.PointLight("#ffd59c", 8, 8, 2); light.position.set(p[0], p[1], p[2]); scene.add(light); return light;
  });
  return (count: number) => lamps.forEach(light => { light.intensity = count ? (night ? 18 : 9) : (night ? 3 : 5); });
}
