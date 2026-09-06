import { describe, expect, it } from "vitest";
import * as THREE from "three";
import { batchDiorama } from "./diorama-batching";

describe("static diorama batching preserves the authored scene", () => {
  it("retains world transforms under translated, rotated and scaled parents", () => {
    const scene = new THREE.Scene();
    const room = new THREE.Group();
    room.position.set(2, .5, -3); room.rotation.y = .6; room.scale.set(1, 1.2, 1);
    scene.add(room);
    const material = new THREE.MeshBasicMaterial();
    const geometry = new THREE.BoxGeometry(1, 2, 3);
    const expected: THREE.Matrix4[] = [];
    for (let i = 0; i < 4; i++) {
      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.set(i, .2 * i, 2); mesh.rotation.z = i * .1; room.add(mesh);
    }
    scene.updateMatrixWorld(true);
    room.children.forEach(mesh => expected.push(mesh.matrixWorld.clone()));
    batchDiorama(THREE, scene, new THREE.Group());
    const batch = scene.getObjectByName("static-shop-batch") as THREE.InstancedMesh;
    expect(batch.count).toBe(4);
    const actual = new THREE.Matrix4();
    expected.forEach((matrix, i) => {
      batch.getMatrixAt(i, actual);
      actual.elements.forEach((value, index) => expect(value).toBeCloseTo(matrix.elements[index], 5));
    });
  });

  it("leaves the door independently animated and raycastable", () => {
    const scene = new THREE.Scene();
    const pivot = new THREE.Group(); scene.add(pivot);
    const geometry = new THREE.BoxGeometry(1, 1, .1), material = new THREE.MeshBasicMaterial();
    for (let i = 0; i < 4; i++) pivot.add(new THREE.Mesh(geometry, material));
    const leaf = pivot.children[0];
    batchDiorama(THREE, scene, pivot);
    pivot.rotation.y = Math.PI / 4; scene.updateMatrixWorld(true);
    expect(pivot.children.length).toBe(4);
    expect(pivot.matrixAutoUpdate).toBe(true);
    expect(leaf.matrixWorld.elements[0]).toBeCloseTo(Math.SQRT1_2);
    expect(new THREE.Raycaster(new THREE.Vector3(0, 0, 3), new THREE.Vector3(0, 0, -1)).intersectObject(pivot, true).length).toBeGreaterThan(0);
  });

  it("keeps transparency and distinct shadow participation separate", () => {
    const scene = new THREE.Scene();
    const geometry = new THREE.BoxGeometry(), material = new THREE.MeshBasicMaterial();
    for (const casts of [false, true]) for (let i = 0; i < 3; i++) {
      const mesh = new THREE.Mesh(geometry, material); mesh.castShadow = casts; scene.add(mesh);
    }
    const glass = new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({ transparent: true, opacity: .2 }));
    scene.add(glass);
    batchDiorama(THREE, scene, new THREE.Group());
    expect(scene.children.includes(glass)).toBe(true);
    const batches = scene.children.filter(node => (node as THREE.InstancedMesh).isInstancedMesh);
    expect(batches.length).toBe(2);
    expect(batches.map(node => node.castShadow).sort()).toEqual([false, true]);
  });
});
