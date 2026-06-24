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
    
    const COUNT = 20000;
    const SPEED_MULT = 1;
    const AUTO_SPIN = true;

    
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x000000, 0.01);
    const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 2000);

    
    const ambientLight = new THREE.AmbientLight(0xffffff, 2.0);
    scene.add(ambientLight);
    const directionalLight = new THREE.DirectionalLight(0xffffff, 3.0);
    directionalLight.position.set(50, 100, 50);
    scene.add(directionalLight);

    
    const loader = new GLTFLoader();

    loader.load(`${import.meta.env.BASE_URL}models/ancient.glb`, (gltf) => {
        homeModel = gltf.scene;
        
        homeModel.position.set(0, -30, 0); 
        homeModel.scale.set(15, 15, 15);
        homeModel.visible = true; 
        scene.add(homeModel);

        if (gltf.animations && gltf.animations.length > 0) {
            const mixer = new THREE.AnimationMixer(homeModel);
            const action = mixer.clipAction(gltf.animations[0]);
            action.play();
            mixers.push(mixer);
        }
    }, undefined, (error) => console.error('Error loading ancient.glb:', error));

    loader.load(`${import.meta.env.BASE_URL}models/platform.glb`, (gltf) => {
        otherModel = gltf.scene;
        
        otherModel.position.set(0, -20, 0); 
        otherModel.scale.set(2, 2, 2);
        otherModel.visible = false;
        scene.add(otherModel);

        if (gltf.animations && gltf.animations.length > 0) {
            const mixer = new THREE.AnimationMixer(otherModel);
            
            gltf.animations.forEach(clip => mixer.clipAction(clip).play());
            mixers.push(mixer);
        }
    }, undefined, (error) => console.error('Error loading platform.glb:', error));
    camera.position.set(0, 0, 100);

    const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance", alpha: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setClearColor(0x000000, 0); 
    renderer.domElement.style.position = 'fixed';
    renderer.domElement.style.top = '0';
    renderer.domElement.style.left = '0';
    renderer.domElement.style.zIndex = '-1';
    document.body.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.autoRotate = AUTO_SPIN;
    controls.autoRotateSpeed = 2.0;
    controls.enableZoom = false; 
    controls.enablePan = false;

    
    
    
    
    
    
    



    
    const clock = new THREE.Clock();

    function animate() {
        requestAnimationFrame(animate);
        
        const delta = clock.getDelta();
        const time = clock.elapsedTime * SPEED_MULT;

        
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
        
    });
}
