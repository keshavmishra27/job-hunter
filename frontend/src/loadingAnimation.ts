import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';

let isAnimating = false;

export function initLoadingAnimation(containerId: string) {
    const container = document.getElementById(containerId);
    if (!container) return;

    // CONFIG
    const COUNT = 20000;
    const SPEED_MULT = 1;
    const AUTO_SPIN = true;

    // SETUP
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x000000, 0.01);
    const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 2000);
    camera.position.set(0, 0, 100);
    
    const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
    renderer.setSize(window.innerWidth, window.innerHeight);
    container.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.autoRotate = AUTO_SPIN;
    controls.autoRotateSpeed = 2.0;
    controls.enableZoom = false;
    controls.enablePan = false;

    // POST PROCESSING
    const composer = new EffectComposer(renderer);
    composer.addPass(new RenderPass(scene, camera));
    const bloomPass = new UnrealBloomPass(new THREE.Vector2(window.innerWidth, window.innerHeight), 1.5, 0.4, 0.85);
    bloomPass.strength = 1.8; bloomPass.radius = 0.4; bloomPass.threshold = 0;
    composer.addPass(bloomPass);

    // SWARM OBJECTS
    const dummy = new THREE.Object3D();
    const color = new THREE.Color();
    const target = new THREE.Vector3();
    
    // INSTANCED MESH
    const geometry = new THREE.TetrahedronGeometry(0.25);
    const material = new THREE.MeshBasicMaterial({ color: 0xffffff });
    
    const instancedMesh = new THREE.InstancedMesh(geometry, material, COUNT);
    instancedMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    scene.add(instancedMesh);

    // DATA ARRAYS
    const positions: THREE.Vector3[] = [];
    for(let i=0; i<COUNT; i++) {
        positions.push(new THREE.Vector3((Math.random()-0.5)*100, (Math.random()-0.5)*100, (Math.random()-0.5)*100));
        instancedMesh.setColorAt(i, color.setHex(0x00ff88)); // Init Color
    }

    // CONTROL STUBS
    const PARAMS: Record<string, number> = {"speed":1,"spread":60,"chaos":0.15};
    const addControl = (id: string, label: string, min: number, max: number, val: number) => {
        return PARAMS[id] !== undefined ? PARAMS[id] : val;
    };

    // ANIMATION LOOP
    const clock = new THREE.Clock();
    
    function animate() {
        requestAnimationFrame(animate);
        
        if (!isAnimating) return; // Pause calculation when hidden

        const time = clock.getElapsedTime() * SPEED_MULT;
        
        // Shader Time Update
        if((material as any).uniforms && (material as any).uniforms.uTime) {
            (material as any).uniforms.uTime.value = time;
        }

        controls.update();

        // SWARM LOGIC
        const count = COUNT; 
        for(let i=0; i<COUNT; i++) {
             // USER CODE INJECTION START
             const speed = addControl("speed", "Rotation Speed", 0.1, 3, 1);
             const spread = addControl("spread", "Spread", 20, 150, 60);
             const chaos = addControl("chaos", "Chaos", 0, 1, 0.15);
             
             const t = time * speed;
             const phi = (i / count) * Math.PI * 2;
             const layer = Math.floor(i / (count / 5));
             
             // Five rings — one for each term: e, i, π, +1, 0
             const radius = spread * (0.4 + 0.15 * layer);
             const tilt = (layer * Math.PI) / 5 + t * 0.3;
             
             const x = Math.cos(phi + t + layer) * radius + Math.sin(tilt) * chaos * 20;
             const y = Math.sin(phi + t + layer) * radius * Math.cos(tilt) + Math.sin(time * 0.7 + i * 0.01) * chaos * 15;
             const z = Math.sin(phi * 2 + t) * radius * 0.5 + layer * 8 * Math.sin(t * 0.2);
             
             target.set(x, y, z);
             
             // Color cycles through gold → cyan → white — feels mathematical/elegant
             const hue = (i / count + time * 0.05) % 1;
             const sat = 0.7 + 0.3 * Math.sin(phi + time);
             color.setHSL(hue * 0.25 + 0.5, sat, 0.6 + 0.2 * Math.sin(phi));
             // USER CODE INJECTION END

             // LERP & UPDATE
             positions[i].lerp(target, 0.1);
             dummy.position.copy(positions[i]);
             dummy.updateMatrix();
             instancedMesh.setMatrixAt(i, dummy.matrix);
             instancedMesh.setColorAt(i, color); 
        }
        instancedMesh.instanceMatrix.needsUpdate = true;
        if (instancedMesh.instanceColor) {
            instancedMesh.instanceColor.needsUpdate = true;
        }

        composer.render();
    }
    
    // Start animation loop
    animate();

    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
        composer.setSize(window.innerWidth, window.innerHeight);
    });
}

export function toggleLoadingAnimation(show: boolean) {
    isAnimating = show;
    const container = document.getElementById('loading-screen');
    if (container) {
        if (show) {
            container.classList.remove('hidden');
            container.classList.add('visible');
        } else {
            container.classList.remove('visible');
            setTimeout(() => {
                if (!isAnimating) container.classList.add('hidden');
            }, 300); // Matches CSS transition duration
        }
    }
}
