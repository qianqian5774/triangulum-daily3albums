import type * as Three from "three";

/** Batch only immobile opaque objects. The entire door branch keeps its own
 * transforms and raycast identity. Stock already uses InstancedMesh. */
export function batchDiorama(THREE: typeof Three, scene: Three.Scene, door: Three.Object3D) {
  const moving = new Set<Three.Object3D>();
  door.traverse(node => moving.add(node));
  scene.updateMatrixWorld(true);
  const groups = new Map<string, Three.Mesh[]>();
  scene.traverse(node => {
    if (moving.has(node)) return;
    node.updateMatrix();
    node.matrixAutoUpdate = false;
    const mesh = node as Three.Mesh;
    if (!mesh.isMesh || (mesh as Three.InstancedMesh).isInstancedMesh || mesh.children.length || Array.isArray(mesh.material) || mesh.material.transparent) return;
    const key = `${mesh.geometry.uuid}/${mesh.material.uuid}/${mesh.castShadow}/${mesh.receiveShadow}/${mesh.renderOrder}`;
    const group = groups.get(key) ?? [];
    group.push(mesh);
    groups.set(key, group);
  });
  for (const meshes of groups.values()) {
    if (meshes.length < 3) continue;
    const first = meshes[0];
    const batch = new THREE.InstancedMesh(first.geometry, first.material, meshes.length);
    batch.name = "static-shop-batch";
    batch.castShadow = first.castShadow;
    batch.receiveShadow = first.receiveShadow;
    batch.renderOrder = first.renderOrder;
    meshes.forEach((mesh, index) => { batch.setMatrixAt(index, mesh.matrixWorld); mesh.removeFromParent(); });
    batch.instanceMatrix.needsUpdate = true;
    batch.computeBoundingSphere();
    batch.matrixAutoUpdate = false;
    scene.add(batch);
  }
}
