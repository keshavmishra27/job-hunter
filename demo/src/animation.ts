import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';

let homeModel: THREE.Group | null = null;
let otherModel: THREE.Group | null = null;
const mixers: THREE.AnimationMixer[] = [];

export function setAnimationPage(page: string) {
    if (homeModel) homeModel.visible = (page === "home");
    if (otherModel) otherModel.visible = (page !== "home");
}

export function initAnimation() {
    // SETUP
    const COUNT = 20000;
    const SPEED_MULT = 1;
    const AUTO_SPIN = true;

    // SETUP
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x000000, 0.01);
    const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 2000);

    // MODEL LIGHTING
    const ambientLight = new THREE.AmbientLight(0xffffff, 2.0);
    scene.add(ambientLight);
    const directionalLight = new THREE.DirectionalLight(0xffffff, 3.0);
    directionalLight.position.set(50, 100, 50);
    scene.add(directionalLight);

    // LOAD MODELS
    const loader = new GLTFLoader();

    loader.load('/models/ancient.glb', (gltf) => {
        homeModel = gltf.scene;
        // Position and scale adjustments (tweak as needed based on model size)
        homeModel.position.set(0, -30, 0); 
        homeModel.scale.set(15, 15, 15);
        homeModel.visible = true; // Default visible on home
        scene.add(homeModel);

        if (gltf.animations && gltf.animations.length > 0) {
            const mixer = new THREE.AnimationMixer(homeModel);
            const action = mixer.clipAction(gltf.animations[0]);
            action.play();
            mixers.push(mixer);
        }
    }, undefined, (error) => console.error('Error loading ancient.glb:', error));

    loader.load('/models/platform.glb', (gltf) => {
        otherModel = gltf.scene;
        // Position and scale adjustments
        otherModel.position.set(0, -20, 0); 
        otherModel.scale.set(2, 2, 2);
        otherModel.visible = false;
        scene.add(otherModel);

        if (gltf.animations && gltf.animations.length > 0) {
            const mixer = new THREE.AnimationMixer(otherModel);
            // Play all animations for complex level scenes
            gltf.animations.forEach(clip => mixer.clipAction(clip).play());
            mixers.push(mixer);
        }
    }, undefined, (error) => console.error('Error loading platform.glb:', error));
    camera.position.set(0, 0, 100);

    const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance", alpha: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setClearColor(0x000000, 0); // Transparent background to show Nintendo UI
    renderer.domElement.style.position = 'fixed';
    renderer.domElement.style.top = '0';
    renderer.domElement.style.left = '0';
    renderer.domElement.style.zIndex = '-1';
    document.body.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.autoRotate = AUTO_SPIN;
    controls.autoRotateSpeed = 2.0;
    controls.enableZoom = false; // Disable zoom so it doesn't mess with page scrolling
    controls.enablePan = false;

    // POST PROCESSING disabled for transparent background
    // const composer = new EffectComposer(renderer);
    // const renderPass = new RenderPass(scene, camera);
    // composer.addPass(renderPass);
    // const bloomPass = new UnrealBloomPass(new THREE.Vector2(window.innerWidth, window.innerHeight), 1.5, 0.4, 0.85);
    // bloomPass.strength = 1.8; bloomPass.radius = 0.4; bloomPass.threshold = 0;
    // composer.addPass(bloomPass);



    // ANIMATION LOOP
    const clock = new THREE.Clock();

    function animate() {
        requestAnimationFrame(animate);
        
        const delta = clock.getDelta();
        const time = clock.elapsedTime * SPEED_MULT;

        // Update model animations
        mixers.forEach(m => m.update(delta));
        controls.update();

        renderer.render(scene, camera);
    }
    animate();

    window.addEventListener('scroll', () => {
        const scrollY = window.scrollY;
        if (homeModel) homeModel.rotation.y = scrollY * 0.002;
        if (otherModel) otherModel.rotation.y = scrollY * 0.002;
    });

    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
        // composer.setSize(window.innerWidth, window.innerHeight);
    });
}
