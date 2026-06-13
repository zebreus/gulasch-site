import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.165.0/build/three.module.js";

const canvas = document.querySelector("#cageScene");
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

if (canvas) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.25;

  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x071018, 0.032);

  const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 120);
  camera.position.set(8.2, 6.1, 10.4);
  camera.lookAt(0, 1.15, 0);

  const rig = new THREE.Group();
  scene.add(rig);

  const materials = {
    rack: new THREE.MeshStandardMaterial({ color: 0x101827, metalness: 0.68, roughness: 0.34 }),
    rackDark: new THREE.MeshStandardMaterial({ color: 0x05080d, metalness: 0.78, roughness: 0.25 }),
    glass: new THREE.MeshPhysicalMaterial({ color: 0x6ee7ff, transmission: 0.22, opacity: 0.34, transparent: true, roughness: 0.08, metalness: 0.2, thickness: 0.35 }),
    table: new THREE.MeshStandardMaterial({ color: 0x172033, metalness: 0.34, roughness: 0.42 }),
    cableGreen: new THREE.MeshBasicMaterial({ color: 0x48ff99 }),
    cableCyan: new THREE.MeshBasicMaterial({ color: 0x60d8ff }),
    cableYellow: new THREE.MeshBasicMaterial({ color: 0xffc75a }),
    red: new THREE.MeshBasicMaterial({ color: 0xff5577 }),
    floor: new THREE.MeshStandardMaterial({ color: 0x07111d, metalness: 0.28, roughness: 0.55 }),
    hologram: new THREE.MeshBasicMaterial({ color: 0x60d8ff, transparent: true, opacity: 0.22, side: THREE.DoubleSide }),
  };

  scene.add(new THREE.HemisphereLight(0xa4f7ff, 0x09111d, 1.7));
  const key = new THREE.PointLight(0x48ff99, 48, 28);
  key.position.set(-5, 8, 5);
  scene.add(key);
  const magenta = new THREE.PointLight(0xb695ff, 28, 24);
  magenta.position.set(5, 4, -5);
  scene.add(magenta);

  const floor = new THREE.Mesh(new THREE.BoxGeometry(12, 0.12, 8), materials.floor);
  floor.position.y = -0.08;
  rig.add(floor);

  const grid = new THREE.GridHelper(14, 28, 0x48ff99, 0x153247);
  grid.position.y = 0.01;
  grid.material.transparent = true;
  grid.material.opacity = 0.34;
  rig.add(grid);

  const animated = [];
  const leds = [];
  const sparks = [];
  const dataBars = [];
  const drones = [];
  const packets = [];
  const pointer = { x: 0, y: 0 };

  function cube(geo, mat, position, scale, parent = rig) {
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.set(...position);
    mesh.scale.set(...scale);
    parent.add(mesh);
    return mesh;
  }

  function addRack(x, z, height, rotation = 0) {
    const rack = new THREE.Group();
    rack.position.set(x, height / 2, z);
    rack.rotation.y = rotation;
    rig.add(rack);

    cube(new THREE.BoxGeometry(1.05, height, 0.95), materials.rack, [0, 0, 0], [1, 1, 1], rack);
    cube(new THREE.BoxGeometry(0.86, height * 0.82, 0.04), materials.rackDark, [0, 0.02, 0.5], [1, 1, 1], rack);

    for (let i = 0; i < 10; i += 1) {
      const y = -height * 0.36 + i * (height * 0.08);
      cube(new THREE.BoxGeometry(0.78, 0.035, 0.055), materials.glass, [0, y, 0.535], [1, 1, 1], rack);
      for (let j = 0; j < 4; j += 1) {
        const led = new THREE.Mesh(new THREE.SphereGeometry(0.035, 12, 12), [materials.cableGreen, materials.cableCyan, materials.cableYellow, materials.red][(i + j) % 4]);
        led.position.set(-0.3 + j * 0.2, y + 0.035, 0.59);
        rack.add(led);
        leds.push({ mesh: led, phase: Math.random() * Math.PI * 2, base: led.scale.x });
      }
    }

    return rack;
  }

  addRack(-3.7, -1.4, 3.4, 0.12);
  addRack(-2.35, -1.25, 3.9, -0.04);
  addRack(2.9, -1.5, 3.2, -0.16);
  addRack(4.05, -1.15, 2.8, -0.28);

  const desk = new THREE.Group();
  desk.position.set(0.45, 0.72, 1.85);
  desk.rotation.y = -0.08;
  rig.add(desk);
  cube(new THREE.BoxGeometry(3.25, 0.18, 1.15), materials.table, [0, 0.55, 0], [1, 1, 1], desk);
  cube(new THREE.BoxGeometry(0.12, 1, 0.12), materials.table, [-1.35, 0, -0.4], [1, 1, 1], desk);
  cube(new THREE.BoxGeometry(0.12, 1, 0.12), materials.table, [1.35, 0, -0.4], [1, 1, 1], desk);
  cube(new THREE.BoxGeometry(0.12, 1, 0.12), materials.table, [-1.35, 0, 0.4], [1, 1, 1], desk);
  cube(new THREE.BoxGeometry(0.12, 1, 0.12), materials.table, [1.35, 0, 0.4], [1, 1, 1], desk);

  for (let i = 0; i < 3; i += 1) {
    const monitor = cube(new THREE.BoxGeometry(0.72, 0.42, 0.04), materials.glass, [-0.8 + i * 0.8, 1.02, -0.2], [1, 1, 1], desk);
    monitor.rotation.x = -0.18;
    animated.push({ mesh: monitor, kind: "monitor", phase: i });
  }

  function cable(points, material, radius = 0.025) {
    const curve = new THREE.CatmullRomCurve3(points.map((p) => new THREE.Vector3(...p)));
    const mesh = new THREE.Mesh(new THREE.TubeGeometry(curve, 80, radius, 8, false), material);
    rig.add(mesh);
    const packet = new THREE.Mesh(new THREE.SphereGeometry(radius * 3.3, 16, 16), material);
    rig.add(packet);
    packets.push({ mesh: packet, curve, speed: 0.08 + Math.random() * 0.09, offset: Math.random() });
    return mesh;
  }

  cable([[-3.7, 1.2, -0.85], [-2.1, 2.2, 0.2], [-0.6, 1.35, 1.35], [0.1, 1.28, 1.45]], materials.cableGreen);
  cable([[3.1, 1.05, -0.95], [2.1, 2.0, 0.2], [1.1, 1.25, 1.35], [0.75, 1.28, 1.45]], materials.cableCyan);
  cable([[-2.4, 2.7, -0.8], [-0.3, 3.2, -0.5], [1.8, 2.25, -0.8], [3.9, 1.6, -0.75]], materials.cableYellow, 0.018);

  for (let i = 0; i < 20; i += 1) {
    const bar = new THREE.Mesh(
      new THREE.BoxGeometry(0.04 + Math.random() * 0.05, 0.5 + Math.random() * 1.8, 0.025),
      new THREE.MeshBasicMaterial({ color: [0x48ff99, 0x60d8ff, 0xffc75a, 0xb695ff][i % 4], transparent: true, opacity: 0.42 })
    );
    bar.position.set(-5.6 + Math.random() * 11.2, 1 + Math.random() * 3.8, -3.55 + Math.random() * 0.18);
    rig.add(bar);
    dataBars.push({ mesh: bar, speed: 0.35 + Math.random() * 1.4, phase: Math.random() * 8 });
  }

  for (let i = 0; i < 5; i += 1) {
    const drone = new THREE.Group();
    const body = new THREE.Mesh(new THREE.OctahedronGeometry(0.16, 0), new THREE.MeshStandardMaterial({ color: 0x101827, metalness: 0.8, roughness: 0.2 }));
    const core = new THREE.Mesh(new THREE.SphereGeometry(0.06, 16, 16), [materials.cableGreen, materials.cableCyan, materials.cableYellow, materials.red, materials.hologram][i]);
    const wing = new THREE.Mesh(new THREE.TorusGeometry(0.22, 0.01, 8, 48), materials.cableCyan);
    wing.rotation.x = Math.PI / 2;
    drone.add(body, core, wing);
    rig.add(drone);
    drones.push({ mesh: drone, radius: 2.1 + i * 0.55, height: 2.3 + i * 0.27, speed: 0.24 + i * 0.045, phase: i * 1.3 });
  }

  // --------------------------------------------------
  // HAMSTER WHEEL + HAMSTER + PET ACCESSORIES
  // --------------------------------------------------
  const wheelGroup = new THREE.Group();
  wheelGroup.position.set(-1.4, 0.55, 1.6);
  rig.add(wheelGroup);

  // Wheel rim
  const wheelRim = new THREE.Mesh(
    new THREE.TorusGeometry(0.42, 0.025, 10, 64),
    new THREE.MeshStandardMaterial({ color: 0x60d8ff, metalness: 0.6, roughness: 0.3 })
  );
  wheelRim.rotation.y = Math.PI / 2;
  wheelGroup.add(wheelRim);

  // Wheel axle
  cube(
    new THREE.CylinderGeometry(0.02, 0.02, 0.18, 8),
    materials.rack,
    [0, 0, 0],
    [1, 1, 1],
    wheelGroup
  );

  // Wheel rungs
  for (let i = 0; i < 8; i += 1) {
    const angle = (i / 8) * Math.PI * 2;
    const rung = new THREE.Mesh(
      new THREE.BoxGeometry(0.018, 0.8, 0.018),
      new THREE.MeshStandardMaterial({ color: 0x48ff99, metalness: 0.4, roughness: 0.4 })
    );
    rung.position.set(0, Math.cos(angle) * 0.42, Math.sin(angle) * 0.42);
    wheelGroup.add(rung);
  }

  // Wheel stand
  cube(
    new THREE.BoxGeometry(0.06, 0.6, 0.06),
    materials.rack,
    [0, -0.5, 0.5],
    [1, 1, 1],
    wheelGroup
  );
  cube(
    new THREE.BoxGeometry(0.06, 0.6, 0.06),
    materials.rack,
    [0, -0.5, -0.5],
    [1, 1, 1],
    wheelGroup
  );

  // Hamster (running on the wheel)
  const hamsterBody = new THREE.Mesh(
    new THREE.SphereGeometry(0.11, 16, 16),
    new THREE.MeshStandardMaterial({ color: 0xe2a96b, roughness: 0.7, metalness: 0.05 })
  );
  const hamsterBelly = new THREE.Mesh(
    new THREE.SphereGeometry(0.09, 12, 12),
    new THREE.MeshStandardMaterial({ color: 0xfbe4c2, roughness: 0.8 })
  );
  hamsterBelly.position.set(0, -0.02, 0.02);
  hamsterBelly.scale.set(1, 0.9, 1.1);
  const hamsterEar1 = new THREE.Mesh(
    new THREE.SphereGeometry(0.028, 8, 8),
    new THREE.MeshStandardMaterial({ color: 0xc88a4a, roughness: 0.7 })
  );
  hamsterEar1.position.set(-0.05, 0.1, 0);
  const hamsterEar2 = hamsterEar1.clone();
  hamsterEar2.position.set(0.05, 0.1, 0);
  const hamster = new THREE.Group();
  hamster.add(hamsterBody, hamsterBelly, hamsterEar1, hamsterEar2);
  hamster.scale.set(1, 0.85, 1.2);
  wheelGroup.add(hamster);

  // Food bowl
  const bowl = new THREE.Mesh(
    new THREE.SphereGeometry(0.13, 18, 18, 0, Math.PI * 2, 0, Math.PI / 2),
    new THREE.MeshStandardMaterial({ color: 0xffc75a, metalness: 0.2, roughness: 0.45 })
  );
  bowl.position.set(1.4, 0.04, 1.7);
  bowl.rotation.x = Math.PI;
  rig.add(bowl);
  for (let i = 0; i < 6; i += 1) {
    const seed = new THREE.Mesh(
      new THREE.SphereGeometry(0.022, 8, 8),
      new THREE.MeshStandardMaterial({ color: i % 2 === 0 ? 0x6b4a1f : 0xc4a070, roughness: 0.7 })
    );
    const a = (i / 6) * Math.PI * 2;
    seed.position.set(1.4 + Math.cos(a) * 0.06, 0.08, 1.7 + Math.sin(a) * 0.06);
    rig.add(seed);
  }

  // Water bottle on a rack
  const bottle = new THREE.Group();
  bottle.position.set(-2.35, 2.1, -0.6);
  rig.add(bottle);
  cube(
    new THREE.CylinderGeometry(0.07, 0.07, 0.32, 16),
    new THREE.MeshPhysicalMaterial({ color: 0x88e1ff, transmission: 0.55, roughness: 0.1, metalness: 0.05, thickness: 0.2 }),
    [0, 0, 0],
    [1, 1, 1],
    bottle
  );
  cube(
    new THREE.CylinderGeometry(0.022, 0.022, 0.12, 10),
    materials.rack,
    [0, -0.21, 0],
    [1, 1, 1],
    bottle
  );
  cube(
    new THREE.SphereGeometry(0.012, 8, 8),
    new THREE.MeshBasicMaterial({ color: 0x48ff99 }),
    [0, -0.27, 0.04],
    [1, 1, 1],
    bottle
  );

  for (let i = 0; i < 70; i += 1) {
    const spark = new THREE.Mesh(
      new THREE.SphereGeometry(0.018 + Math.random() * 0.025, 8, 8),
      new THREE.MeshBasicMaterial({ color: [0x48ff99, 0x60d8ff, 0xffc75a, 0xff5577][i % 4], transparent: true, opacity: 0 })
    );
    rig.add(spark);
    sparks.push({
      mesh: spark,
      origin: new THREE.Vector3((Math.random() - 0.5) * 5, 1.2 + Math.random() * 2.4, (Math.random() - 0.5) * 2.8),
      velocity: new THREE.Vector3((Math.random() - 0.5) * 0.06, Math.random() * 0.05, (Math.random() - 0.5) * 0.06),
      phase: Math.random() * 4,
      life: 0.6 + Math.random() * 1.2,
    });
  }

  const ringGroup = new THREE.Group();
  ringGroup.position.set(0, 2.25, -0.2);
  rig.add(ringGroup);
  for (let i = 0; i < 4; i += 1) {
    const ring = new THREE.Mesh(new THREE.TorusGeometry(2.1 + i * 0.38, 0.01, 8, 120), materials.hologram);
    ring.rotation.x = Math.PI / 2 + i * 0.12;
    ring.rotation.z = i * 0.8;
    ringGroup.add(ring);
    animated.push({ mesh: ring, kind: "ring", phase: i });
  }

  const antenna = new THREE.Group();
  antenna.position.set(-4.9, 0.1, 2.7);
  rig.add(antenna);
  cube(new THREE.CylinderGeometry(0.04, 0.04, 2.2, 16), materials.rack, [0, 1.1, 0], [1, 1, 1], antenna);
  const dish = new THREE.Mesh(new THREE.TorusGeometry(0.46, 0.025, 12, 80), materials.cableCyan);
  dish.position.y = 2.24;
  dish.rotation.x = Math.PI / 2.6;
  antenna.add(dish);
  animated.push({ mesh: dish, kind: "dish", phase: 0 });

  const particles = new THREE.Group();
  scene.add(particles);
  const particleMaterial = new THREE.MeshBasicMaterial({ color: 0x8fffd0, transparent: true, opacity: 0.48 });
  for (let i = 0; i < 90; i += 1) {
    const p = new THREE.Mesh(new THREE.SphereGeometry(0.012 + Math.random() * 0.018, 8, 8), particleMaterial);
    p.position.set((Math.random() - 0.5) * 14, Math.random() * 6, (Math.random() - 0.5) * 9);
    particles.add(p);
    animated.push({ mesh: p, kind: "particle", phase: Math.random() * 9, speed: 0.18 + Math.random() * 0.5 });
  }

  const clock = new THREE.Clock();

  function resize() {
    const rect = canvas.getBoundingClientRect();
    const width = Math.max(1, Math.floor(rect.width));
    const height = Math.max(1, Math.floor(rect.height));
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  }

  function animate() {
    const t = clock.getElapsedTime();
    const chaos = Number.parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--editor-chaos")) || 1;
    const isNight = document.body.dataset.time === "night";
    camera.position.x += ((8.2 + pointer.x * 0.7) - camera.position.x) * 0.035;
    camera.position.y += ((6.1 - pointer.y * 0.35) - camera.position.y) * 0.035;
    camera.lookAt(pointer.x * 0.35, 1.1 - pointer.y * 0.16, 0);

    const pulse = Math.max(0, Math.sin(t * 2.7 * chaos)) ** 12;
    rig.rotation.y = Math.sin(t * 0.18 * chaos) * 0.08 - 0.16 + pointer.x * 0.035;
    rig.rotation.x = pointer.y * 0.018;
    rig.position.y = Math.sin(t * 0.7 * chaos) * 0.035;
    ringGroup.rotation.y = t * 0.22 * chaos;
    ringGroup.rotation.z = Math.sin(t * 0.4 * chaos) * 0.08;
    key.intensity = (42 + Math.sin(t * 1.7) * 8 + pulse * 16) * (isNight ? 0.32 : 1);
    magenta.intensity = (26 + Math.sin(t * 1.1 + 2) * 7 + pulse * 10) * (isNight ? 0.42 : 1);

    // Hamster wheel spins; hamster bobs on top
    wheelRim.rotation.x += 0.08 * chaos * (isNight ? 0.6 : 1);
    hamster.position.set(0, 0.36, 0);
    hamster.position.y += Math.sin(wheelRim.rotation.x) * 0.05;
    hamster.rotation.z = wheelRim.rotation.x;

    for (const led of leds) {
      const s = 0.65 + Math.max(0.15, Math.sin(t * 4.2 * chaos + led.phase)) * 0.62;
      led.mesh.scale.setScalar(s);
    }

    for (const item of animated) {
      if (item.kind === "monitor") item.mesh.material.opacity = 0.24 + Math.sin(t * 2.1 * chaos + item.phase) * 0.08;
      if (item.kind === "ring") item.mesh.rotation.z += 0.002 + item.phase * 0.0008;
      if (item.kind === "dish") item.mesh.rotation.z = Math.sin(t * 1.6 * chaos) * 0.32;
      if (item.kind === "particle") {
        item.mesh.position.y += item.speed * 0.01 * chaos;
        item.mesh.position.x += Math.sin(t + item.phase) * 0.0015;
        if (item.mesh.position.y > 6.2) item.mesh.position.y = 0.05;
      }
    }

    for (const packet of packets) {
      const u = (t * packet.speed * chaos + packet.offset) % 1;
      packet.mesh.position.copy(packet.curve.getPointAt(u));
      packet.mesh.scale.setScalar(0.7 + Math.sin(t * 18 + packet.offset * 9) * 0.25 + pulse * 1.6);
    }

    for (const bar of dataBars) {
      bar.mesh.position.y -= bar.speed * 0.025 * chaos;
      bar.mesh.material.opacity = 0.18 + Math.sin(t * 4 * chaos + bar.phase) * 0.16 + pulse * 0.16;
      bar.mesh.scale.y = 0.55 + Math.sin(t * 3.2 * chaos + bar.phase) * 0.28;
      if (bar.mesh.position.y < 0.4) {
        bar.mesh.position.y = 5.2 + Math.random();
        bar.mesh.position.x = -5.6 + Math.random() * 11.2;
      }
    }

    for (const drone of drones) {
      const a = t * drone.speed * chaos + drone.phase;
      drone.mesh.position.set(Math.cos(a) * drone.radius, drone.height + Math.sin(a * 1.9) * 0.35, Math.sin(a) * drone.radius * 0.72);
      drone.mesh.rotation.y = -a + Math.PI / 2;
      drone.mesh.rotation.z = Math.sin(t * 3 * chaos + drone.phase) * 0.22;
      drone.mesh.children[2].rotation.z += 0.08 + pulse * 0.02;
    }

    for (const spark of sparks) {
      const local = (t * chaos + spark.phase) % spark.life;
      const f = local / spark.life;
      spark.mesh.position.copy(spark.origin).addScaledVector(spark.velocity, local * 42);
      spark.mesh.material.opacity = Math.sin(f * Math.PI) * (0.15 + pulse * 0.85);
      spark.mesh.scale.setScalar(0.5 + f * 2.8 + pulse * 2.4);
      if (f > 0.96 && Math.random() > 0.92) {
        spark.origin.set((Math.random() - 0.5) * 5.2, 1.1 + Math.random() * 2.6, (Math.random() - 0.5) * 3);
      }
    }

    renderer.render(scene, camera);
    if (!reduceMotion) requestAnimationFrame(animate);
  }

  window.addEventListener("resize", resize, { passive: true });
  window.addEventListener("pointermove", (event) => {
    pointer.x = (event.clientX / window.innerWidth - 0.5) * 2;
    pointer.y = (event.clientY / window.innerHeight - 0.5) * 2;
  }, { passive: true });
  resize();
  animate();
}
