import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
document.body.append(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x9fd8cf);
scene.fog = new THREE.Fog(0x9fd8cf, 20, 60);

const camera = new THREE.PerspectiveCamera(45, innerWidth / innerHeight, 0.1, 200);
camera.position.set(10, 8, 14);
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 1, 0);
controls.enableDamping = true;

scene.add(new THREE.HemisphereLight(0xfff3d6, 0x0e5a57, 1.5));
const sun = new THREE.DirectionalLight(0xffe2a8, 2.5);
sun.position.set(6, 12, 4);
scene.add(sun);

const isle = new THREE.Group();
const rock = new THREE.Mesh(new THREE.ConeGeometry(4, 6, 10), new THREE.MeshStandardMaterial({ color: 0x6b5a45, flatShading: true }));
rock.rotation.x = Math.PI;
rock.position.y = -3;
const grass = new THREE.Mesh(new THREE.CylinderGeometry(4, 4, 0.4, 32), new THREE.MeshStandardMaterial({ color: 0x4f7a3a }));
const pond = new THREE.Mesh(new THREE.CircleGeometry(1.2, 24), new THREE.MeshStandardMaterial({ color: 0x2fc4b2, emissive: 0x0e5a57 }));
pond.rotation.x = -Math.PI / 2;
pond.position.set(1.8, 0.21, 1);
const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.4, 0.8, 3.5, 8), new THREE.MeshStandardMaterial({ color: 0x7a5a3a, flatShading: true }));
trunk.position.y = 1.9;
const canopy = new THREE.Mesh(new THREE.IcosahedronGeometry(2.4, 1), new THREE.MeshStandardMaterial({ color: 0x7fa64a, flatShading: true }));
canopy.position.y = 4.6;
isle.add(rock, grass, pond, trunk, canopy);
scene.add(isle);

addEventListener("resize", () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});

renderer.setAnimationLoop((t) => {
  isle.position.y = Math.sin(t * 0.0008) * 0.3;
  controls.update();
  renderer.render(scene, camera);
});
