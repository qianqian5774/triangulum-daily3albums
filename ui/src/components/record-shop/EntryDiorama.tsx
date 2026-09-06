import { useCallback, useEffect, useRef, useState, type CSSProperties } from "react";
import type * as Three from "three";
import authorityAxonometric from "../../assets/record-shop/exterior/entry-diorama-axonometric.webp";
import type { RecordShopCopy } from "../../strings/copy";
import type { RecordShopCue } from "./audio";
import { createDioramaGlass, createDioramaMaterial, createDioramaWorldMaterial } from "./diorama-materials";
import { addStreetDetails, DIORAMA_SITE } from "./diorama-street";
import { addShopInterior } from "./diorama-shop-interior";
import { batchDiorama } from "./diorama-batching";

export type DioramaView = "axonometric" | "front" | "right" | "rear" | "left" | "roof";
export type EntryInfoKey = "project" | "rhythm";

interface EntryDioramaProps {
  view: DioramaView;
  theme: "day" | "night";
  statusLabel: string;
  copy: RecordShopCopy["exterior"];
  onViewChange: (view: DioramaView) => void;
  onOpenInfo: (panel: EntryInfoKey) => void;
  onEnter: () => void;
  onCue: (cue: RecordShopCue) => void;
  availableCount: number;
  interiorReady: boolean;
  onApproach: () => void;
  debugReplayToken?: number;
}

interface ViewConfig {
  label: string;
  shortLabel: string;
  position: [number, number, number];
  target: [number, number, number];
  zoom: number;
  doorVisible: boolean;
}

const VIEW_CONFIGS: Record<DioramaView, ViewConfig> = {
  axonometric: { label: "AXONOMETRIC", shortLabel: "AXON", position: [13.8, 9.2, 18], target: [0, 2.72, 0.55], zoom: 0.82, doorVisible: true },
  front: { label: "FRONT ELEVATION", shortLabel: "FRONT", position: [0, 3.75, 20], target: [0, 2.7, 0.2], zoom: 0.94, doorVisible: true },
  right: { label: "RIGHT ELEVATION", shortLabel: "RIGHT", position: [20, 3.75, 0], target: [0, 2.7, 0], zoom: 0.96, doorVisible: false },
  rear: { label: "REAR ELEVATION", shortLabel: "REAR", position: [0, 3.75, -18], target: [0, 2.7, -0.1], zoom: 0.96, doorVisible: false },
  left: { label: "LEFT ELEVATION", shortLabel: "LEFT", position: [-20, 3.75, 0], target: [0, 2.7, 0], zoom: 0.96, doorVisible: false },
  roof: { label: "ROOF PLAN", shortLabel: "ROOF", position: [0, 24, 0.01], target: [0, 0, 0.7], zoom: 0.68, doorVisible: false }
};

const viewOrder = Object.keys(VIEW_CONFIGS) as DioramaView[];

function disposeScene(root: Three.Object3D) {
  const geometries = new Set<Three.BufferGeometry>();
  const materialSet = new Set<Three.Material>();
  const textures = new Set<Three.Texture>();
  root.traverse((node) => {
    const mesh = node as Three.Mesh;
    if (mesh.geometry) geometries.add(mesh.geometry);
    if ((mesh as Three.InstancedMesh).isInstancedMesh) (mesh as Three.InstancedMesh).dispose();
    const meshMaterials = Array.isArray(mesh.material) ? mesh.material : mesh.material ? [mesh.material] : [];
    for (const material of meshMaterials) {
      if (!material) continue;
      materialSet.add(material);
      const textured = material as Three.Material & { map?: Three.Texture; alphaMap?: Three.Texture; gradientMap?: Three.Texture };
      if (textured.map) textures.add(textured.map);
      if (textured.alphaMap) textures.add(textured.alphaMap);
      if (textured.gradientMap) textures.add(textured.gradientMap);
    }
  });
  geometries.forEach((geometry) => geometry.dispose());
  materialSet.forEach((material) => material.dispose());
  textures.forEach((texture) => texture.dispose());
}

function easeInOutCubic(value: number) {
  return value < 0.5 ? 4 * value * value * value : 1 - Math.pow(-2 * value + 2, 3) / 2;
}

function easeOutCubic(value: number) {
  return 1 - Math.pow(1 - value, 3);
}

// The miniature remains a complete framed world across its public zoom range.
// Closer inspection belongs to free orbit, rather than cropping the building.
const MIN_ZOOM_SCALE = 0.9;
const MAX_ZOOM_SCALE = 1.12;

function clampZoomScale(value: number) {
  return Math.min(MAX_ZOOM_SCALE, Math.max(MIN_ZOOM_SCALE, value));
}

function placeAlongSafeTransition(from: Three.Vector3, to: Three.Vector3, progress: number, output: Three.Vector3) {
  const fromRadius = Math.hypot(from.x, from.z);
  const toRadius = Math.hypot(to.x, to.z);

  // Horizontal elevations travel around the outside of the building. A direct
  // lerp between them would put the camera inside the shell during the turn.
  if (fromRadius > 8 && toRadius > 8) {
    const fromAngle = Math.atan2(from.x, from.z);
    let delta = Math.atan2(to.x, to.z) - fromAngle;
    if (delta > Math.PI) delta -= Math.PI * 2;
    if (delta <= -Math.PI) delta += Math.PI * 2;
    const angle = fromAngle + delta * progress;
    const radius = fromRadius + (toRadius - fromRadius) * progress;
    output.set(Math.sin(angle) * radius, from.y + (to.y - from.y) * progress, Math.cos(angle) * radius);
    return output;
  }

  // Roof/side transitions use a lifted arc so the camera clears the roof and
  // never slices through the walls or the glazing.
  output.lerpVectors(from, to, progress);
  output.y += Math.sin(Math.PI * progress) * 8;
  return output;
}

interface CameraTransition {
  startedAt: number;
  fromPosition: Three.Vector3;
  fromTarget: Three.Vector3;
  fromUp: Three.Vector3;
  fromZoom: number;
}

type EntryPhase = "idle" | "opening" | "approaching" | "crossing";

export function EntryDiorama({ view, theme, statusLabel, copy, onViewChange, onOpenInfo, onEnter, onCue, availableCount, interiorReady, onApproach, debugReplayToken = 0 }: EntryDioramaProps) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const doorButtonRef = useRef<HTMLButtonElement | null>(null);
  const wakeRenderRef = useRef<(() => void) | null>(null);
  const snapViewRef = useRef<((view: DioramaView) => void) | null>(null);
  const viewRef = useRef(view);
  const enterRequestRef = useRef<(() => void) | null>(null);
  const enteringRef = useRef(false);
  const interiorReadyRef = useRef(interiorReady);
  const thresholdRef = useRef<HTMLDivElement | null>(null);
  const updateLifeRef = useRef<((count: number) => void) | null>(null);
  const entryPhaseRef = useRef<EntryPhase>("idle");
  const zoomScaleRef = useRef(1);
  const [rendererUnavailable, setRendererUnavailable] = useState(false);
  const [ready, setReady] = useState(false);
  const [entering, setEntering] = useState(false);
  const [entryPhase, setEntryPhase] = useState<EntryPhase>("idle");
  const [zoomScale, setZoomScale] = useState(1);

  const lastDebugReplayRef = useRef(0);

  useEffect(() => { interiorReadyRef.current = interiorReady; wakeRenderRef.current?.(); }, [interiorReady]);
  useEffect(() => { updateLifeRef.current?.(availableCount); wakeRenderRef.current?.(); }, [availableCount]);

  useEffect(() => {
    if (viewRef.current !== view) snapViewRef.current?.(view);
    viewRef.current = view;
    wakeRenderRef.current?.();
  }, [view]);

  const requestEnter = useCallback(() => {
    if (enteringRef.current || !interiorReadyRef.current || !enterRequestRef.current || !VIEW_CONFIGS[viewRef.current].doorVisible) return;
    enteringRef.current = true;
    entryPhaseRef.current = "opening";
    setEntryPhase("opening");
    setEntering(true);
    onCue("door");
    onApproach();
    enterRequestRef.current();
  }, [onApproach, onCue]);

  useEffect(() => {
    if (!debugReplayToken || debugReplayToken === lastDebugReplayRef.current || !ready || !interiorReady || entering) return;
    lastDebugReplayRef.current = debugReplayToken;
    requestEnter();
  }, [debugReplayToken, entering, interiorReady, ready, requestEnter]);

  const changeZoom = useCallback((factor: number) => {
    if (!Number.isFinite(factor) || factor <= 0) return;
    const next = clampZoomScale(zoomScaleRef.current * factor);
    if (next === zoomScaleRef.current) return;
    zoomScaleRef.current = next;
    setZoomScale(next);
    wakeRenderRef.current?.();
  }, []);

  const resetZoom = useCallback(() => {
    if (zoomScaleRef.current === 1) return;
    zoomScaleRef.current = 1;
    setZoomScale(1);
    wakeRenderRef.current?.();
  }, []);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    setReady(false);
    setRendererUnavailable(false);
    let disposed = false;
    let frameId = 0;
    let resizeObserver: ResizeObserver | undefined;
    let renderer: Three.WebGLRenderer | undefined;
    let scene: Three.Scene | undefined;
    let entryStartedAt: number | null = null;
    let entryCompleted = false;
    let announcedReady = false;
    let detachCanvasListeners: (() => void) | undefined;
    let detachViewportListeners: (() => void) | undefined;

    const initialize = async () => {
      try {
        const THREE = await import("three");
        const { RoundedBoxGeometry } = await import("three/examples/jsm/geometries/RoundedBoxGeometry.js");
        if (disposed) return;
        scene = new THREE.Scene();
        const isNight = theme === "night";
        // The dome below owns the rendered field. This fallback is only ever
        // visible during context restoration, so it deliberately matches it.
        scene.background = new THREE.Color(isNight ? "#0c1228" : "#d1cdd6");

        renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: "high-performance" });
        renderer.outputColorSpace = THREE.SRGBColorSpace;
        renderer.toneMapping = THREE.ACESFilmicToneMapping;
        renderer.toneMappingExposure = 1;
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = THREE.PCFShadowMap;
        renderer.domElement.setAttribute("aria-hidden", "true");
        host.append(renderer.domElement);

        const camera = new THREE.OrthographicCamera(-8, 8, 4.5, -4.5, 1, 160);
        const selected = VIEW_CONFIGS[viewRef.current];
        camera.position.set(...selected.position);
        camera.zoom = selected.zoom;
        camera.updateProjectionMatrix();
        const lookTarget = new THREE.Vector3(...selected.target);
        if (viewRef.current === "roof") camera.up.set(0, 0, -1);
        camera.lookAt(lookTarget);

        const toon = (color: string) => createDioramaMaterial(THREE, color);
        const graphite = createDioramaMaterial(THREE, "#4b5870", "metal");
        const deepGraphite = createDioramaMaterial(THREE, "#354258", "metal");
        const fasciaMetal = createDioramaMaterial(THREE, "#65748d", "metal");
        const frameMetal = createDioramaMaterial(THREE, "#65748b", "metal");
        const frameEdge = createDioramaMaterial(THREE, "#b6bfce", "metal");
        const roofSurface = createDioramaMaterial(THREE, "#7b879f", "roof");
        const roofEdge = createDioramaMaterial(THREE, "#58667d", "metal");
        const roofHighlight = createDioramaMaterial(THREE, "#c4ccd6", "metal");
        const ivory = toon("#eee6d9");
        const tile = toon("#c8c0b8");
        const warmMetal = toon("#aaa4a0");
        const brass = toon("#dda95e");
        const coral = toon("#c65a44");
        const paleWood = createDioramaMaterial(THREE, "#c99f73", "wood");
        const foliage = toon("#68745c");
        const glassMaterial = createDioramaGlass(THREE, isNight);
        const boxGeometryCache = new Map<string, Three.BufferGeometry>();
        const cylinderGeometryCache = new Map<string, Three.BufferGeometry>();
        const worldDome = new THREE.Mesh(new THREE.SphereGeometry(78, 32, 20), createDioramaWorldMaterial(THREE, isNight));
        worldDome.name = "closed-diorama-world";
        worldDome.renderOrder = -1;
        worldDome.frustumCulled = false;
        scene.add(worldDome);
        const shopRoot = new THREE.Group();
        shopRoot.name = "heightened-record-shop";
        shopRoot.scale.y = 1.2;
        scene.add(shopRoot);

        const getBoxGeometry = (width: number, height: number, depth: number) => {
          const key = `${width}:${height}:${depth}`;
          let geometry = boxGeometryCache.get(key);
          if (!geometry) {
            const edge = Math.min(width, height, depth);
            geometry = edge >= .12
              ? new RoundedBoxGeometry(width, height, depth, 2, Math.min(.022, edge * .08))
              : new THREE.BoxGeometry(width, height, depth);
            boxGeometryCache.set(key, geometry);
          }
          return geometry;
        };

        const getCylinderGeometry = (radius: number, height: number, segments: number) => {
          const key = `${radius}:${height}:${segments}`;
          let geometry = cylinderGeometryCache.get(key);
          if (!geometry) {
            geometry = new THREE.CylinderGeometry(radius, radius, height, Math.max(20, segments));
            cylinderGeometryCache.set(key, geometry);
          }
          return geometry;
        };

        const addBox = (width: number, height: number, depth: number, material: Three.Material, position: [number, number, number], parent: Three.Object3D = scene!) => {
          const mesh = new THREE.Mesh(getBoxGeometry(width, height, depth), material);
          mesh.position.set(...position);
          const minimumDimension = Math.min(width, height, depth);
          mesh.castShadow = !material.transparent && minimumDimension >= 0.075;
          // Thin mullions do not sample their own shadow map. Broad receiving
          // surfaces use the same fixed light frustum at every camera scale.
          mesh.receiveShadow = !material.transparent && Math.max(width, depth) > .5 && minimumDimension >= .16;
          parent.add(mesh);
          return mesh;
        };
        const addCylinder = (radius: number, height: number, material: Three.Material, position: [number, number, number], rotation: [number, number, number] = [0, 0, 0], parent: Three.Object3D = scene!) => {
          const mesh = new THREE.Mesh(getCylinderGeometry(radius, height, 12), material);
          mesh.position.set(...position);
          mesh.rotation.set(...rotation);
          const participatesInShadows = radius >= 0.08;
          mesh.castShadow = participatesInShadows;
          mesh.receiveShadow = participatesInShadows;
          parent.add(mesh);
          return mesh;
        };
        const addPipe = (start: Three.Vector3, end: Three.Vector3, radius = 0.045, parent: Three.Object3D = scene!) => {
          const direction = end.clone().sub(start);
          const mesh = addCylinder(radius, direction.length(), warmMetal, [0, 0, 0], [0, 0, 0], parent);
          mesh.position.copy(start.clone().add(end).multiplyScalar(0.5));
          mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction.normalize());
          return mesh;
        };
        const addShopBox = (width: number, height: number, depth: number, material: Three.Material, position: [number, number, number], parent: Three.Object3D = shopRoot) => addBox(width, height, depth, material, position, parent);
        const addShopCylinder = (radius: number, height: number, material: Three.Material, position: [number, number, number], rotation: [number, number, number] = [0, 0, 0], parent: Three.Object3D = shopRoot) => addCylinder(radius, height, material, position, rotation, parent);
        const addShopPipe = (start: Three.Vector3, end: Three.Vector3, radius = .045) => addPipe(start, end, radius, shopRoot);
        const addFrame = (width: number, height: number, position: [number, number, number], rotationY = 0) => {
          const group = new THREE.Group();
          group.position.set(...position);
          group.rotation.y = rotationY;
          addShopBox(width, 0.14, 0.16, frameMetal, [0, (height - .14) / 2, 0], group);
          addShopBox(width, 0.14, 0.16, frameMetal, [0, -(height - .14) / 2, 0], group);
          addShopBox(0.14, height - .28, 0.16, frameMetal, [-(width - .14) / 2, 0, 0], group);
          addShopBox(0.14, height - .28, 0.16, frameMetal, [(width - .14) / 2, 0, 0], group);
          // A raised cool edge breaks the flat-black silhouette and makes the
          // powder-coated mullion readable at grazing angles.
          addShopBox(width - .12, .025, .035, frameEdge, [0, (height - .09) / 2, .085], group);
          addShopBox(width - .12, .025, .035, frameEdge, [0, -(height - .09) / 2, .085], group);
          addShopBox(.025, height - .12, .035, frameEdge, [-(width - .09) / 2, 0, .085], group);
          addShopBox(.025, height - .12, .035, frameEdge, [(width - .09) / 2, 0, .085], group);
          const glass = new THREE.Mesh(new THREE.PlaneGeometry(width - 0.24, height - 0.24), glassMaterial);
          glass.position.z = 0.028;
          glass.castShadow = false;
          glass.receiveShadow = false;
          glass.renderOrder = 1;
          group.add(glass);
          shopRoot.add(group);
          return group;
        };
        const exteriorLeafGeometry = new THREE.SphereGeometry(1, 7, 5);
        const site = DIORAMA_SITE;
        addBox(site.width, site.baseTop - site.bottom, site.front - site.back, deepGraphite,
          [0, (site.baseTop + site.bottom) / 2, (site.front + site.back) / 2]);
        addBox(site.width, 0.36, 14, tile, [0, 0, 0]);
        // Individual paving faces with genuine joints; no intersecting line grid.
        const paving = [tile, toon("#c2b9b1"), toon("#b5adb0"), toon("#d0c7bd")];
        for (let x = -6; x <= 6; x += 1.5) for (let z = -6; z <= 6; z += 1.5) {
          if (Math.abs(x) < 6 && z > -5.25 && z < 5.25) continue;
          addBox(1.47, .045, 1.47, paving[(Math.round(x + z) + 16) % 4], [x, .2025, z]);
        }
        addShopBox(11.7, 0.16, 10, paleWood, [0, 0.27, -0.25]);
        addBox(13.88, 0.055, 0.12, roofHighlight, [0, 0.22, 6.91]);
        addBox(0.12, 0.055, 13.64, roofHighlight, [6.91, 0.22, 0]);

        // The shop is constructed as actual miniature geometry. No exterior
        // elevation image is mapped onto these walls, windows, doors or props.
        addShopBox(12.28, .7, .24, fasciaMetal, [0, 4.23, 4.93]);
        for (const x of [-5.88, -1.35, -0.94, 0.94, 1.35, 5.88]) addShopBox(.24, 3.6, .24, ivory, [x, 2.08, 4.93]);
        addFrame(4.3, 3.5, [-3.62, 2.13, 4.99]);
        addFrame(4.3, 3.5, [3.62, 2.13, 4.99]);

        addShopBox(.28, .7, 10.09, fasciaMetal, [6, 4.23, -.235]);
        addShopBox(0.24, 0.22, 10.3, deepGraphite, [6.03, 0.4, -0.25]);
        for (const z of [-3.42, -.16, 3.1]) addFrame(3.26, 3.5, [6.075, 2.13, z], Math.PI / 2);

        addShopBox(12, 3.6, .28, ivory, [0, 2.08, -5.42]);
        addShopBox(2.08, 2.84, 0.16, deepGraphite, [2.85, 1.72, -5.58]);
        addShopBox(1.72, 2.54, 0.07, graphite, [2.85, 1.72, -5.68]);
        addShopCylinder(0.06, 0.18, brass, [3.46, 1.62, -5.78], [Math.PI / 2, 0, 0]);
        // The six-view authority has a solid left/service wall. Shelves face
        // into the shop here; the front and three right panes reveal the room.
        addShopBox(.28, 3.6, 10.3, ivory, [-6.02, 2.08, -.25]);
        addShopBox(.28, .7, 10.3, fasciaMetal, [-6.02, 4.23, -.25]);
        addShopBox(12, .7, .28, fasciaMetal, [0, 4.23, -5.42]);

        // Leave the entrance void open so the door reads as a glazed threshold,
        // not as a black plate pasted over the facade. A small warm display and
        // local light give the room behind the glass a readable sense of depth.
        addShopBox(1.5, .075, .82, paleWood, [-.02, .305, 4.62]);
        const entryLight = new THREE.PointLight(isNight ? "#d7a76b" : "#f5dca7", isNight ? 0.72 : 0.56, 3.6, 2);
        entryLight.position.set(-0.02, 2.45, 4.26);
        shopRoot.add(entryLight);

        const updateInteriorLife = addShopInterior(THREE, shopRoot, addShopBox, addShopCylinder, isNight);

        const signCanvas = document.createElement("canvas");
        signCanvas.width = 1536;
        signCanvas.height = 256;
        const signContext = signCanvas.getContext("2d");
        if (signContext) {
          signContext.fillStyle = "#272a39";
          signContext.fillRect(0, 0, signCanvas.width, signCanvas.height);
          signContext.fillStyle = "#ce7150";
          for (const [x, y] of [[104, 150], [156, 150], [130, 105]]) {
            signContext.beginPath(); signContext.arc(x, y, 19, 0, Math.PI * 2); signContext.fill();
          }
          signContext.fillStyle = "#f1dcb4";
          signContext.font = "700 96px Trebuchet MS, Arial, sans-serif";
          signContext.textAlign = "center";
          signContext.textBaseline = "middle";
          signContext.fillText("TRIANGULUM DAILY", signCanvas.width / 2 + 65, signCanvas.height / 2 + 4);
        }
        const signTexture = new THREE.CanvasTexture(signCanvas);
        signTexture.colorSpace = THREE.SRGBColorSpace;
        addShopBox(4.9, 0.78, 0.16, graphite, [0, 4.05, 5.04]);
        const signFace = new THREE.Mesh(new THREE.PlaneGeometry(4.76, 0.64), new THREE.MeshBasicMaterial({ map: signTexture, toneMapped: false }));
        signFace.position.set(0, 4.05, 5.13);
        shopRoot.add(signFace);

        // Roof parts meet on deliberate seams instead of overlapping coplanar
        // faces. This removes the corner z-fighting that became visible at
        // browser zoom while preserving a complete, supported flat roof.
        const roofTop = 4.59;
        addShopBox(12.22, .18, 10.48, roofSurface, [0, roofTop - .09, -.25]);
        addShopBox(12.34, 0.28, 0.22, roofEdge, [0, 4.73, 4.95]);
        addShopBox(12.34, 0.28, 0.22, roofEdge, [0, 4.73, -5.45]);
        addShopBox(0.22, 0.28, 10.18, roofEdge, [6.06, 4.73, -0.25]);
        addShopBox(0.22, 0.28, 10.18, roofEdge, [-6.06, 4.73, -0.25]);
        // Folded zinc cap, standing seams and a perimeter flashing strip make
        // the roof read as a maintained surface at every inspection distance.
        addShopBox(12.36, .035, .25, roofHighlight, [0, 4.8875, 4.95]);
        addShopBox(12.36, .035, .25, roofHighlight, [0, 4.8875, -5.45]);
        for (const x of [-6.06, 6.06]) addShopBox(.25, .035, 10.18, roofHighlight, [x, 4.8875, -.25]);
        const seamMaterial = toon("#747788");
        for (const x of [-4.5, -3, -1.5, 0, 1.5, 3, 4.5]) {
          addShopBox(.026, .026, 9.99, seamMaterial, [x, roofTop + .013, -.25]);
        }
        addShopBox(11.85, .018, .16, roofHighlight, [0, roofTop + .009, 4.59]);
        // Tile dado and a thin enamel reveal join the light plaster to glazing.
        addShopBox(.035, .46, 10.0, roofHighlight, [-6.18, .57, -.25]);
        addShopBox(11.85, .46, .035, roofHighlight, [0, .57, -5.585]);
        for (const x of [-3.65, 3.65]) addShopBox(4.28, .045, .10, brass, [x, .47, 5.10]);
        addShopBox(12.15, .055, .08, brass, [0, 3.90, 5.08]);
        addShopBox(1.95, .18, 1.35, deepGraphite, [2.1, roofTop + .09, -2.15]);
        const hvac = addShopBox(1.62, .92, 1.08, warmMetal, [2.1, roofTop + .64, -2.15]);
        for (let index = -5; index <= 5; index += 1) addShopBox(0.035, 0.55, 0.025, deepGraphite, [index * 0.115, 0, 0.552], hvac);
        addShopCylinder(.19, .75, deepGraphite, [-2.1, roofTop + .455, -.9]);
        addShopCylinder(.27, .08, deepGraphite, [-2.1, roofTop + .87, -.9]);
        addShopBox(.56, .08, .56, deepGraphite, [-2.1, roofTop + .04, -.9]);
        addShopPipe(new THREE.Vector3(2.87, 5.02, -2.15), new THREE.Vector3(3.65, 5.02, -2.15));
        addShopPipe(new THREE.Vector3(3.65, 5.02, -2.15), new THREE.Vector3(3.65, roofTop + .06, -2.15));
        addShopCylinder(.16, .08, warmMetal, [3.65, roofTop + .04, -2.15]);
        // Weatherproof junction box, conduit saddle and roof gland all sit on
        // the same roof datum. Neither the base nor the pipe end hangs in air.
        addShopBox(1.15, .08, .82, roofEdge, [-3.7, roofTop + .04, -2.92]);
        addShopBox(.94, .1, .64, roofHighlight, [-3.7, roofTop + .13, -2.92]);
        const conduitHeight = roofTop + .14;
        addShopPipe(new THREE.Vector3(-3.32, conduitHeight, -2.92), new THREE.Vector3(-2.72, conduitHeight, -2.92), .032);
        addShopPipe(new THREE.Vector3(-2.72, conduitHeight, -2.92), new THREE.Vector3(-2.72, roofTop + .035, -2.92), .032);
        addShopBox(.11, .108, .13, roofEdge, [-2.98, roofTop + .054, -2.92]);
        addShopCylinder(.1, .055, deepGraphite, [-2.72, roofTop + .0275, -2.92]);

        const doorFrameMaterial = createDioramaMaterial(THREE, "#5b6b85", "metal");
        const doorFrameEdge = createDioramaMaterial(THREE, "#bbc5d1", "metal");
        addShopBox(1.9, 0.12, 0.22, deepGraphite, [-0.02, 3.1, 5.12]);
        addShopBox(0.12, 2.9, 0.22, doorFrameMaterial, [-0.92, 1.65, 5.12]);
        addShopBox(0.12, 2.9, 0.22, doorFrameMaterial, [0.88, 1.65, 5.12]);
        addShopBox(1.86, 0.035, 0.82, graphite, [-0.02, 0.39, 5.56]);
        for (const x of [-1.18, 1.14]) {
          addShopBox(0.24, 0.34, 0.18, graphite, [x, 2.72, 5.08]);
          addShopCylinder(0.11, 0.12, brass, [x, 2.56, 5.19], [Math.PI / 2, 0, 0]);
        }
        addShopBox(0.42, 0.66, 0.08, graphite, [1.12, 1.76, 5.08]);
        addShopBox(0.3, 0.06, 0.04, brass, [1.12, 1.93, 5.13]);
        addShopBox(0.3, 0.035, 0.04, warmMetal, [1.12, 1.75, 5.13]);
        addShopBox(0.3, 0.035, 0.04, warmMetal, [1.12, 1.62, 5.13]);

        const doorPivot = new THREE.Group();
        doorPivot.position.set(0.76, 0.32, 5.18);
        shopRoot.add(doorPivot);
        const doorLeaf = new THREE.Group();
        doorLeaf.position.set(-0.77, 1.34, 0);
        doorLeaf.userData.isEntranceDoor = true;
        doorPivot.add(doorLeaf);
        addBox(1.54, 0.12, 0.1, doorFrameMaterial, [0, 1.28, 0], doorLeaf);
        addBox(1.54, 0.12, 0.1, doorFrameMaterial, [0, -1.28, 0], doorLeaf);
        addBox(0.12, 2.44, 0.1, doorFrameMaterial, [-0.71, 0, 0], doorLeaf);
        addBox(0.12, 2.44, 0.1, doorFrameMaterial, [0.71, 0, 0], doorLeaf);
        // The raised interior outline makes the glazed entrance read as a
        // powder-coated assembly with a real rebate, not a black cutout.
        addBox(1.29, 0.024, 0.026, doorFrameEdge, [0, 1.205, .06], doorLeaf);
        addBox(1.29, 0.024, 0.026, doorFrameEdge, [0, -1.205, .06], doorLeaf);
        addBox(0.024, 2.29, 0.026, doorFrameEdge, [-.645, 0, .06], doorLeaf);
        addBox(0.024, 2.29, 0.026, doorFrameEdge, [.645, 0, .06], doorLeaf);
        const doorGlass = new THREE.Mesh(new THREE.PlaneGeometry(1.30, 2.44), glassMaterial);
        doorGlass.position.set(0, 0, 0.006);
        doorGlass.renderOrder = 1;
        doorLeaf.add(doorGlass);
        addCylinder(0.04, 0.78, brass, [-1.28, 1.34, 0.08], [0, 0, 0], doorPivot);
        addCylinder(0.07, 0.06, brass, [-1.28, 0.97, 0.08], [Math.PI / 2, 0, 0], doorPivot);
        addCylinder(0.07, 0.06, brass, [-1.28, 1.71, 0.08], [Math.PI / 2, 0, 0], doorPivot);

        addShopPipe(new THREE.Vector3(-6.05, 3.28, 3.62), new THREE.Vector3(-6.84, 3.28, 3.62), 0.055);
        addShopPipe(new THREE.Vector3(-6.05, 2.72, 3.62), new THREE.Vector3(-6.84, 2.72, 3.62), 0.055);
        addShopCylinder(0.54, 0.11, deepGraphite, [-6.88, 3, 3.62], [0, 0, Math.PI / 2]);
        addShopCylinder(0.17, 0.125, coral, [-6.95, 3, 3.62], [0, 0, Math.PI / 2]);
        addBox(0.78, 0.8, 0.78, graphite, [-5.45, 0.58, 5.7]);
        for (let index = 0; index < 48; index += 1) {
          const angle = index * 2.399;
          const leaf = new THREE.Mesh(exteriorLeafGeometry, foliage);
          leaf.scale.set(.065, .15, .022);
          const radius = .16 + (index % 5) * .047;
          leaf.position.set(-5.45 + Math.cos(angle) * radius, 1.05 + (index % 7) * .09, 5.7 + Math.sin(angle) * radius);
          leaf.rotation.set(.45, angle, Math.cos(angle) * .8);
          leaf.castShadow = false;
          leaf.receiveShadow = false;
          scene.add(leaf);
        }
        addCylinder(0.21, 1.1, deepGraphite, [1.18, 0.74, 5.82]);
        addCylinder(0.26, 0.12, warmMetal, [1.18, 1.32, 5.82]);
        addShopCylinder(0.075, 3.75, roofEdge, [5.8, 2.28, -5.25]);
        addShopPipe(new THREE.Vector3(5.8, 4.18, -5.25), new THREE.Vector3(5.45, 4.18, -5.25), 0.075);
        const updateStreetLife = addStreetDetails(THREE, scene, addBox, addCylinder, isNight);
        updateLifeRef.current = (count) => { updateStreetLife(count); updateInteriorLife(count); };
        updateLifeRef.current(availableCount);

        // The visible floor is the bottom of the same continuous dome as the
        // sky. This transparent receiver supplies only contact shadows, so it
        // cannot create a horizon, a rectangular floor edge, or a second band.
        const shadowCatcher = new THREE.Mesh(new THREE.PlaneGeometry(46, 46), new THREE.ShadowMaterial({
          color: new THREE.Color(isNight ? "#070b19" : "#5e6173"),
          opacity: isNight ? .28 : .16,
          transparent: true,
          depthWrite: false
        }));
        shadowCatcher.name = "diorama-contact-shadow-receiver";
        shadowCatcher.rotation.x = -Math.PI / 2;
        shadowCatcher.position.y = site.bottom - .012;
        shadowCatcher.receiveShadow = true;
        scene.add(shadowCatcher);
        scene.add(new THREE.HemisphereLight(isNight ? "#aeb6d5" : "#f1edf7", isNight ? "#262b3d" : "#9695aa", isNight ? .94 : 1.55));
        const key = new THREE.DirectionalLight(isNight ? "#c8d0e8" : "#fff0d6", isNight ? .68 : .76);
        key.position.set(-8.5, 15.5, 9.5);
        key.castShadow = true;
        key.shadow.mapSize.set(2048, 2048);
        key.shadow.bias = -0.00004;
        key.shadow.normalBias = 0.045;
        key.shadow.intensity = .52;
        key.shadow.radius = 3;
        key.shadow.camera.left = -14;
        key.shadow.camera.right = 14;
        key.shadow.camera.top = 14;
        key.shadow.camera.bottom = -14;
        key.shadow.camera.near = 1;
        key.shadow.camera.far = 38;
        scene.add(key);
        const fill = new THREE.DirectionalLight(isNight ? "#858fb7" : "#d5d9e6", isNight ? .52 : .64);
        fill.position.set(9, 7, -6);
        scene.add(fill);
        batchDiorama(THREE, scene, doorPivot);
        renderer.shadowMap.autoUpdate = false;
        renderer.shadowMap.needsUpdate = true;

        const cameraGoal = new THREE.Vector3(...selected.position);
        const targetGoal = new THREE.Vector3(...selected.target);
        const cameraUpGoal = new THREE.Vector3(0, 1, 0);
        const normalCameraUp = new THREE.Vector3(0, 1, 0);
        const roofCameraUp = new THREE.Vector3(0, 0, -1);
        const safePosition = new THREE.Vector3();
        const doorProjection = new THREE.Vector3();
        const doorCorners = [new THREE.Vector3(-.77, -1.34, .06), new THREE.Vector3(.77, -1.34, .06), new THREE.Vector3(-.77, 1.34, .06), new THREE.Vector3(.77, 1.34, .06)];
        const cornerProjection = new THREE.Vector3();
        const entryFromPosition = camera.position.clone();
        const entryFromTarget = lookTarget.clone();
        const entryFromUp = camera.up.clone();
        const entryStagingPosition = new THREE.Vector3(0.02, 2.78, 8.35);
        const entryStagingTarget = new THREE.Vector3(0, 2.05, 5.02);
        // End outside the shell. A fully opaque, brief doorway occlusion joins
        // the already-decoded fixed interior; the camera never crosses a wall.
        const entryInsidePosition = new THREE.Vector3(0.02, 2.30, 5.72);
        const entryInsideTarget = new THREE.Vector3(0, 2.04, 3.5);
        const raycaster = new THREE.Raycaster();
        const pointer = new THREE.Vector2();
        const pointerPositions = new Map<number, { x: number; y: number }>();
        const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        let portraitViewport = false;
        let ultrawideCompositionScale = 1;
        let lastView = viewRef.current;
        let pinchDistance = 0;
        let entryFromZoom = camera.zoom;
        let doorPress: { pointerId: number; x: number; y: number } | null = null;
        let orbitDrag: { pointerId: number; startX: number; startY: number; lastX: number; lastY: number } | null = null;
        let freeOrbit = false;
        const orbitTarget = lookTarget.clone();
        const orbitOffset = camera.position.clone().sub(orbitTarget);
        let orbitRadius = orbitOffset.length();
        let orbitYawGoal = Math.atan2(orbitOffset.x, orbitOffset.z);
        let orbitPitchGoal = Math.atan2(orbitOffset.y, Math.hypot(orbitOffset.x, orbitOffset.z));
        let cameraTransition: CameraTransition | null = null;
        const resize = () => {
          if (!renderer) return;
          const rect = host.getBoundingClientRect();
          const width = Math.max(1, Math.round(rect.width));
          const height = Math.max(1, Math.round(rect.height));
          const aspect = width / height;
          portraitViewport = aspect < 0.72;
          // Preserve the miniature's physical proportions, but give a 21:9+
          // canvas a deliberate composition instead of leaving the shop as a
          // narrow specimen in a very wide empty field. This does not alter the
          // public min/max zoom range; it is an aspect-specific camera framing.
          ultrawideCompositionScale = aspect > 2.15
            ? Math.min(1.33, 1 + (aspect - 2.15) * .24)
            : 1;
          const deviceScale = Math.min(2, Math.max(1, window.devicePixelRatio || 1));
          renderer.setPixelRatio(deviceScale);
          renderer.domElement.dataset.pixelRatio = deviceScale.toFixed(2);
          const vertical = Math.max(13.2, 20 / aspect);
          camera.left = (-vertical * aspect) / 2;
          camera.right = (vertical * aspect) / 2;
          camera.top = vertical / 2;
          camera.bottom = -vertical / 2;
          camera.updateProjectionMatrix();
          renderer.setSize(width, height, false);
          wakeRenderRef.current?.();
        };
        const beginEntry = () => {
          if (entryStartedAt !== null || !VIEW_CONFIGS[viewRef.current].doorVisible) return;
          entryStartedAt = performance.now();
          entryFromPosition.copy(camera.position);
          entryFromTarget.copy(lookTarget);
          entryFromUp.copy(camera.up);
          entryFromZoom = camera.zoom;
          cameraTransition = null;
          wakeRenderRef.current?.();
        };
        enterRequestRef.current = beginEntry;
        const getPinchDistance = () => {
          const points = Array.from(pointerPositions.values());
          if (points.length < 2) return 0;
          return Math.hypot(points[0].x - points[1].x, points[0].y - points[1].y);
        };
        const hitDoor = (event: PointerEvent) => {
          const rect = renderer!.domElement.getBoundingClientRect();
          pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
          pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
          raycaster.setFromCamera(pointer, camera);
          return raycaster.intersectObject(doorLeaf, true).length > 0;
        };
        const onCanvasPointer = (event: PointerEvent) => {
          const canvas = renderer!.domElement;
          if (event.type === "pointerdown") {
            pointerPositions.set(event.pointerId, { x: event.clientX, y: event.clientY });
            if (pointerPositions.size === 1) canvas.setPointerCapture?.(event.pointerId);
            if (pointerPositions.size > 1) {
              doorPress = null;
              orbitDrag = null;
              pinchDistance = getPinchDistance();
              event.preventDefault();
              return;
            }
            if (entryStartedAt === null && VIEW_CONFIGS[viewRef.current].doorVisible && camera.position.z > 5.3 && hitDoor(event)) {
              doorPress = { pointerId: event.pointerId, x: event.clientX, y: event.clientY };
            } else if (entryStartedAt === null) {
              orbitDrag = { pointerId: event.pointerId, startX: event.clientX, startY: event.clientY, lastX: event.clientX, lastY: event.clientY };
              canvas.style.cursor = "grabbing";
            }
          } else if (event.type === "pointermove" && pointerPositions.has(event.pointerId)) {
            pointerPositions.set(event.pointerId, { x: event.clientX, y: event.clientY });
            if (doorPress?.pointerId === event.pointerId && Math.hypot(event.clientX - doorPress.x, event.clientY - doorPress.y) > 8) doorPress = null;
          }

          if (pointerPositions.size > 1) {
            const nextDistance = getPinchDistance();
            if (pinchDistance > 0 && nextDistance > 0) changeZoom(nextDistance / pinchDistance);
            pinchDistance = nextDistance;
            event.preventDefault();
            return;
          }

          if (event.type === "pointermove" && orbitDrag?.pointerId === event.pointerId && entryStartedAt === null) {
            const dx = event.clientX - orbitDrag.lastX;
            const dy = event.clientY - orbitDrag.lastY;
            orbitDrag.lastX = event.clientX;
            orbitDrag.lastY = event.clientY;
            if (Math.hypot(event.clientX - orbitDrag.startX, event.clientY - orbitDrag.startY) > 3) {
              if (!freeOrbit) {
                orbitTarget.copy(lookTarget);
                orbitOffset.copy(camera.position).sub(orbitTarget);
                orbitRadius = Math.max(15, orbitOffset.length());
                orbitYawGoal = Math.atan2(orbitOffset.x, orbitOffset.z);
                orbitPitchGoal = Math.atan2(orbitOffset.y, Math.hypot(orbitOffset.x, orbitOffset.z));
              }
              freeOrbit = true;
              cameraTransition = null;
              doorPress = null;
              orbitYawGoal -= dx * .0075;
              // Treat the model as a grabbed object: dragging upward tilts its
              // front upward, so the camera elevation moves down, and vice versa.
              orbitPitchGoal = Math.max(.12, Math.min(1.23, orbitPitchGoal + dy * .006));
              canvas.dataset.orbitElevation = orbitPitchGoal.toFixed(3);
              scheduleRender();
              event.preventDefault();
              return;
            }
          }

          if (entryStartedAt !== null || !VIEW_CONFIGS[viewRef.current].doorVisible) return;
          const hit = camera.position.z > 5.3 && hitDoor(event);
          canvas.style.cursor = hit ? "pointer" : "grab";
        };
        const onCanvasPointerEnd = (event: PointerEvent) => {
          const activateDoor = event.type === "pointerup"
            && doorPress?.pointerId === event.pointerId
            && entryStartedAt === null
            && VIEW_CONFIGS[viewRef.current].doorVisible
            && hitDoor(event);
          if (doorPress?.pointerId === event.pointerId) doorPress = null;
          if (orbitDrag?.pointerId === event.pointerId) orbitDrag = null;
          pointerPositions.delete(event.pointerId);
          pinchDistance = pointerPositions.size > 1 ? getPinchDistance() : 0;
          const canvas = renderer?.domElement;
          if (canvas?.hasPointerCapture?.(event.pointerId)) canvas.releasePointerCapture(event.pointerId);
          if (canvas) canvas.style.cursor = "grab";
          if (activateDoor) requestEnter();
        };
        const onCanvasWheel = (event: WheelEvent) => {
          // Ctrl-wheel belongs to browser zoom, not the miniature camera.
          if (event.ctrlKey || event.metaKey) return;
          event.preventDefault();
          if (entryStartedAt !== null) return;
          changeZoom(Math.exp(-event.deltaY * 0.0012));
        };
        renderer.domElement.style.touchAction = "none";
        renderer.domElement.addEventListener("pointermove", onCanvasPointer);
        renderer.domElement.addEventListener("pointerdown", onCanvasPointer);
        renderer.domElement.addEventListener("pointerup", onCanvasPointerEnd);
        renderer.domElement.addEventListener("pointercancel", onCanvasPointerEnd);
        renderer.domElement.addEventListener("wheel", onCanvasWheel, { passive: false });
        detachCanvasListeners = () => {
          renderer?.domElement.removeEventListener("pointermove", onCanvasPointer);
          renderer?.domElement.removeEventListener("pointerdown", onCanvasPointer);
          renderer?.domElement.removeEventListener("pointerup", onCanvasPointerEnd);
          renderer?.domElement.removeEventListener("pointercancel", onCanvasPointerEnd);
          renderer?.domElement.removeEventListener("wheel", onCanvasWheel);
        };

        const scheduleRender = () => {
          if (disposed || frameId !== 0 || document.hidden) return;
          frameId = window.requestAnimationFrame(render);
        };
        snapViewRef.current = (nextView) => {
          const next = VIEW_CONFIGS[nextView];
          cameraTransition = {
            startedAt: performance.now(),
            fromPosition: camera.position.clone(),
            fromTarget: lookTarget.clone(),
            fromUp: camera.up.clone(),
            fromZoom: camera.zoom
          };
          freeOrbit = false;
          orbitDrag = null;
          viewRef.current = nextView;
          lastView = nextView;
          cameraGoal.set(...next.position);
          targetGoal.set(...next.target);
          scheduleRender();
        };

        function render(now: number) {
          frameId = 0;
          if (disposed || !renderer || !scene) return;
          const previousZoom = camera.zoom;
          const activeViewName = viewRef.current;
          if (activeViewName !== lastView && entryStartedAt === null) {
            cameraTransition = {
              startedAt: now,
              fromPosition: camera.position.clone(),
              fromTarget: lookTarget.clone(),
              fromUp: camera.up.clone(),
              fromZoom: camera.zoom
            };
            lastView = activeViewName;
          }
          const activeView = VIEW_CONFIGS[activeViewName];
          // The roof plan already consumes the full short axis with its 16-unit
          // plinth; applying the elevation composition gain there would crop
          // the miniature on 32:9 screens.
          const aspectFraming = activeViewName === "roof" ? 1 : ultrawideCompositionScale;
          let cameraZoomGoal = activeView.zoom * zoomScaleRef.current * aspectFraming;
          if (freeOrbit) {
            const horizontalRadius = Math.cos(orbitPitchGoal) * orbitRadius;
            cameraGoal.set(
              orbitTarget.x + Math.sin(orbitYawGoal) * horizontalRadius,
              orbitTarget.y + Math.sin(orbitPitchGoal) * orbitRadius,
              orbitTarget.z + Math.cos(orbitYawGoal) * horizontalRadius
            );
            targetGoal.copy(orbitTarget);
          } else {
            cameraGoal.set(...activeView.position);
            targetGoal.set(...activeView.target);
          }
          if (portraitViewport && entryStartedAt === null) targetGoal.y = 1.85;
          if (entryStartedAt !== null) {
            cameraTransition = null;
            const elapsed = now - entryStartedAt;
            const doorT = reducedMotion ? 1 : Math.min(1, elapsed / 320);
            const approachT = reducedMotion ? 1 : Math.max(0, Math.min(1, (elapsed - 90) / 670));
            const crossT = reducedMotion ? 1 : Math.max(0, Math.min(1, (elapsed - 620) / 360));
            const approach = easeInOutCubic(approachT);
            const crossing = easeInOutCubic(crossT);
            doorPivot.rotation.y = -Math.PI * .47 * easeOutCubic(doorT);
            // Include the final open pose in the cached shadow, then stop.
            renderer.shadowMap.needsUpdate = elapsed <= 360;
            if (crossT <= 0) {
              placeAlongSafeTransition(entryFromPosition, entryStagingPosition, approach, safePosition);
              camera.position.copy(safePosition);
              lookTarget.lerpVectors(entryFromTarget, entryStagingTarget, approach);
              camera.up.lerpVectors(entryFromUp, normalCameraUp, approach).normalize();
              camera.zoom = entryFromZoom + (2.45 - entryFromZoom) * approach;
            } else {
              camera.position.lerpVectors(entryStagingPosition, entryInsidePosition, crossing);
              lookTarget.lerpVectors(entryStagingTarget, entryInsideTarget, crossing);
              camera.up.copy(normalCameraUp);
              camera.zoom = 2.45 + (3.35 - 2.45) * crossing;
            }
            if (!reducedMotion && elapsed >= 320 && entryPhaseRef.current === "opening") {
              entryPhaseRef.current = "approaching";
              setEntryPhase("approaching");
            }
            if ((reducedMotion || elapsed >= 620) && entryPhaseRef.current !== "crossing") {
              entryPhaseRef.current = "crossing";
              setEntryPhase("crossing");
              onCue("threshold");
            }
            // Hide the perceptual cut before the camera reaches the near door
            // frame. Both sides use the same ink value, with no light flash.
            if (thresholdRef.current) thresholdRef.current.style.opacity = String(reducedMotion ? 1 : easeInOutCubic(Math.max(0, Math.min(1, (elapsed - 600) / 180))));
            if (!entryCompleted && interiorReadyRef.current && (reducedMotion || elapsed >= 1050)) {
              entryCompleted = true;
              onCue("arrival");
              onEnter();
            }
          }
          const interpolation = reducedMotion ? 1 : 0.095;
          if (entryStartedAt !== null) {
            // The entry timeline writes its camera pose directly above. Keeping
            // it out of the settling lerp prevents any reverse or toggle feel.
          } else if (cameraTransition) {
            const progress = reducedMotion ? 1 : Math.min(1, (now - cameraTransition.startedAt) / 420);
            const eased = easeInOutCubic(progress);
            placeAlongSafeTransition(cameraTransition.fromPosition, cameraGoal, eased, safePosition);
            camera.position.copy(safePosition);
            lookTarget.lerpVectors(cameraTransition.fromTarget, targetGoal, eased);
            camera.up.lerpVectors(cameraTransition.fromUp, !freeOrbit && activeViewName === "roof" ? roofCameraUp : normalCameraUp, eased).normalize();
            camera.zoom = cameraTransition.fromZoom + (cameraZoomGoal - cameraTransition.fromZoom) * eased;
            if (progress >= 1) cameraTransition = null;
          } else {
            camera.position.lerp(cameraGoal, interpolation);
            lookTarget.lerp(targetGoal, interpolation);
            camera.zoom += (cameraZoomGoal - camera.zoom) * interpolation;
            cameraUpGoal.copy(!freeOrbit && activeViewName === "roof" ? roofCameraUp : normalCameraUp);
            camera.up.lerp(cameraUpGoal, interpolation).normalize();
          }
          camera.lookAt(lookTarget);
          if (Math.abs(camera.zoom - previousZoom) > 0.00001) camera.updateProjectionMatrix();
          const button = doorButtonRef.current;
          if (button) {
            doorProjection.set(-0.02, 2.04, 5.3).project(camera);
            const projectedX = (doorProjection.x * 0.5 + 0.5) * 100;
            const projectedY = (-doorProjection.y * 0.5 + 0.5) * 100;
            const safeX = Number.isFinite(projectedX) ? Math.min(92, Math.max(8, projectedX)) : 50;
            const safeY = Number.isFinite(projectedY) ? Math.min(92, Math.max(8, projectedY)) : 60;
            button.style.setProperty("--door-x", `${safeX}%`);
            button.style.setProperty("--door-y", `${safeY}%`);
            if (entryStartedAt === null) {
              let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
              doorLeaf.updateWorldMatrix(true, false);
              for (const corner of doorCorners) {
                cornerProjection.copy(corner).applyMatrix4(doorLeaf.matrixWorld).project(camera);
                minX = Math.min(minX, cornerProjection.x); maxX = Math.max(maxX, cornerProjection.x);
                minY = Math.min(minY, cornerProjection.y); maxY = Math.max(maxY, cornerProjection.y);
              }
              button.style.width = `${(maxX - minX) * renderer.domElement.clientWidth / 2}px`;
              button.style.height = `${(maxY - minY) * renderer.domElement.clientHeight / 2}px`;
              button.style.setProperty("--door-x", `${(minX + maxX + 2) * 25}%`);
              button.style.setProperty("--door-y", `${(2 - minY - maxY) * 25}%`);
            }
            button.dataset.visible = activeView.doorVisible && camera.position.z > 5.3 && entryStartedAt === null && doorProjection.x > -.9 && doorProjection.x < .9 && doorProjection.y > -.9 && doorProjection.y < .9 ? "true" : "false";
          }
          if (import.meta.env.DEV) renderer.info.autoReset = false;
          renderer.info.reset();
          const frameStarted = performance.now();
          renderer.render(scene, camera);
          if (import.meta.env.DEV) {
            const data = renderer.domElement.dataset;
            data.renderCount = String(Number(data.renderCount || 0) + 1);
            data.drawCalls = String(renderer.info.render.calls);
            data.triangles = String(renderer.info.render.triangles);
            data.geometries = String(renderer.info.memory.geometries);
            data.textures = String(renderer.info.memory.textures);
            data.frameMs = (performance.now() - frameStarted).toFixed(2);
          }
          const desiredUp = !freeOrbit && activeViewName === "roof" ? roofCameraUp : normalCameraUp;
          const cameraSettled = camera.position.distanceToSquared(cameraGoal) <= 0.0009
            && lookTarget.distanceToSquared(targetGoal) <= 0.0009
            && Math.abs(camera.zoom - cameraZoomGoal) <= 0.0009
            && camera.up.distanceToSquared(desiredUp) <= 0.0009;
          if (!announcedReady && cameraSettled && entryStartedAt === null) {
            announcedReady = true;
            setReady(true);
          }
          if ((entryStartedAt !== null && !entryCompleted) || cameraTransition !== null || !cameraSettled) scheduleRender();
        }
        wakeRenderRef.current = scheduleRender;
        resize();
        resizeObserver = new ResizeObserver(resize);
        resizeObserver.observe(host);
        document.addEventListener("visibilitychange", scheduleRender);
        window.addEventListener("resize", resize, { passive: true });
        window.visualViewport?.addEventListener("resize", resize, { passive: true });
        detachViewportListeners = () => {
          document.removeEventListener("visibilitychange", scheduleRender);
          window.removeEventListener("resize", resize);
          window.visualViewport?.removeEventListener("resize", resize);
        };
        scheduleRender();
      } catch (error) {
        console.error("Entry Diorama initialization failed", error);
        if (!disposed) setRendererUnavailable(true);
      }
    };
    void initialize();
    return () => {
      disposed = true;
      wakeRenderRef.current = null;
      snapViewRef.current = null;
      enterRequestRef.current = null;
      updateLifeRef.current = null;
      if (frameId) window.cancelAnimationFrame(frameId);
      resizeObserver?.disconnect();
      detachCanvasListeners?.();
      detachViewportListeners?.();
      if (scene) disposeScene(scene);
      renderer?.dispose();
      renderer?.domElement.remove();
    };
  }, [changeZoom, onCue, onEnter, requestEnter, theme]);

  return (
    <section className="entry-diorama" data-model="procedural-geometry" data-ready={ready} data-view={view} data-theme={theme} data-life={availableCount ? "open" : "quiet"} data-entering={entering || undefined} data-entry-phase={entryPhase} data-zoom={zoomScale.toFixed(2)} aria-label={copy.aria}>
      <div ref={hostRef} className="entry-diorama__canvas">
        {rendererUnavailable ? <img className="entry-diorama__authority-fallback" src={authorityAxonometric} alt={copy.fallbackAlt} /> : null}
      </div>
      <header className="entry-diorama__heading">
        <p>TRIANGULUM DAILY</p>
        <span>{copy.approvedView} {viewOrder.indexOf(view) + 1}/6</span>
      </header>
      <nav className="entry-diorama__views" aria-label={copy.viewsAria}>
        <span className="entry-diorama__views-label"><b>{copy.views}</b><small>{copy.orbitHint}</small></span>
        {viewOrder.map((candidate) => (
          <button key={candidate} className="entry-diorama__view-button" type="button" aria-label={copy.viewNames[candidate]} aria-pressed={view === candidate} disabled={entering} onPointerEnter={() => onCue("hover")} onClick={() => { onCue("view"); snapViewRef.current?.(candidate); onViewChange(candidate); }}>
            <span>{copy.viewShort[candidate]}</span>
          </button>
        ))}
      </nav>
      <div className="entry-diorama__zoom" aria-label={copy.zoomAria}>
        <button type="button" aria-label={copy.zoomOut} disabled={entering} onPointerEnter={() => onCue("hover")} onClick={() => { onCue("press"); changeZoom(0.88); }}>−</button>
        <output aria-live="polite">{Math.round(zoomScale * 100)}%</output>
        <button type="button" aria-label={copy.zoomIn} disabled={entering} onPointerEnter={() => onCue("hover")} onClick={() => { onCue("press"); changeZoom(1.14); }}>+</button>
        <button type="button" aria-label={copy.zoomReset} disabled={entering} onPointerEnter={() => onCue("hover")} onClick={() => { onCue("press"); resetZoom(); }}>{copy.reset}</button>
      </div>
      <button ref={doorButtonRef} className="entry-diorama__door" style={{ "--door-x": "50%", "--door-y": "60%" } as CSSProperties} data-visible={ready && !entering && VIEW_CONFIGS[view].doorVisible ? "true" : undefined} type="button" onPointerEnter={() => onCue("hover")} onClick={requestEnter} disabled={!ready || !interiorReady || !VIEW_CONFIGS[view].doorVisible || entering} aria-label={copy.doorAria} />
      <p className="entry-diorama__hint">{VIEW_CONFIGS[view].doorVisible ? copy.enterHint : copy.selectEntryViewHint}</p>
      <p className="entry-diorama__status" role="status">{statusLabel}</p>
      <nav className="entry-diorama__info" aria-label={copy.infoAria}>
        <button type="button" onPointerEnter={() => onCue("hover")} onClick={() => { onCue("press"); onOpenInfo("project"); }}>{copy.projectInfo}</button>
        <button type="button" onPointerEnter={() => onCue("hover")} onClick={() => { onCue("press"); onOpenInfo("rhythm"); }}>{copy.dailyRhythm}</button>
      </nav>
      <div ref={thresholdRef} className="entry-diorama__threshold" aria-hidden="true" />
    </section>
  );
}
