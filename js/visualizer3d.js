// Interactive 3D Silicon Chip Physical Visualizer with Three.js
class Visualizer3D {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.scene = null;
    this.camera = null;
    this.renderer = null;
    this.controls = null;
    this.data = null;

    // Layer groups for toggle and vertical exploded view
    this.layerGroups = {
      substrate: null,
      cells: null,
      fillers: null,
      metal1: null,
      metal2: null,
      metal3: null,
      metal4: null,
      metal5: null,
      metal6: null,
      clockTree: null,
      powerMesh: null,
      vias: null,
      criticalPath: null
    };

    this.explodeFactor = 1.0;
    this.raycaster = new THREE.Raycaster();
    this.mouse = new THREE.Vector2();

    this.initScene();
  }

  initScene() {
    if (!this.container) return;

    const width = this.container.clientWidth || 800;
    const height = this.container.clientHeight || 600;

    // Scene
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x050811);

    // Camera
    this.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 2000);
    this.camera.position.set(60, 80, 100);

    // Renderer
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setSize(width, height);
    this.renderer.setPixelRatio(window.devicePixelRatio);
    this.renderer.shadowMap.enabled = true;
    this.container.appendChild(this.renderer.domElement);

    // Controls
    if (typeof THREE.OrbitControls !== 'undefined') {
      this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
      this.controls.enableDamping = true;
      this.controls.dampingFactor = 0.08;
    }

    // Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
    this.scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(0x38bdf8, 0.8);
    dirLight1.position.set(50, 100, 50);
    this.scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0xffffff, 0.4);
    dirLight2.position.set(-50, -50, -50);
    this.scene.add(dirLight2);

    // Initialize layer groups
    for (const key of Object.keys(this.layerGroups)) {
      const grp = new THREE.Group();
      this.scene.add(grp);
      this.layerGroups[key] = grp;
    }

    // Events
    window.addEventListener('resize', () => this.onWindowResize());
    this.renderer.domElement.addEventListener('click', (e) => this.onRaycastClick(e));

    this.animate();
  }

  onWindowResize() {
    if (!this.container || !this.renderer || !this.camera) return;
    const width = this.container.clientWidth;
    const height = this.container.clientHeight;
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height);
  }

  animate() {
    requestAnimationFrame(() => this.animate());
    if (this.controls) this.controls.update();
    if (this.renderer && this.scene && this.camera) {
      this.renderer.render(this.scene, this.camera);
    }
  }

  loadData(pipelineData) {
    this.data = pipelineData;
    this.build3DModel();
  }

  clearModel() {
    for (const key of Object.keys(this.layerGroups)) {
      const grp = this.layerGroups[key];
      while (grp.children.length > 0) {
        const obj = grp.children[0];
        if (obj.geometry) obj.geometry.dispose();
        if (obj.material) {
          if (Array.isArray(obj.material)) obj.material.forEach(m => m.dispose());
          else obj.material.dispose();
        }
        grp.remove(obj);
      }
    }
  }

  build3DModel() {
    this.clearModel();
    if (!this.data || !this.data.floorplan || !this.data.floorplan.die) return;

    const fp = this.data.floorplan;
    const die = fp.die;
    const core = fp.core;

    // Center offset so (0,0) is at origin
    const cx = die.width_um / 2;
    const cz = die.height_um / 2;

    // 1. Silicon Substrate / P-Well base slab (Y = -2)
    const subGeo = new THREE.BoxGeometry(die.width_um, 2.5, die.height_um);
    const subMat = new THREE.MeshStandardMaterial({
      color: 0x1e293b,
      metalness: 0.8,
      roughness: 0.3,
      wireframe: false
    });
    const substrate = new THREE.Mesh(subGeo, subMat);
    substrate.position.set(0, -1.25, 0);
    this.layerGroups.substrate.add(substrate);

    // Substrate Edge Wireframe border
    const edgeGeo = new THREE.EdgesGeometry(subGeo);
    const edgeMat = new THREE.LineBasicMaterial({ color: 0x38bdf8 });
    const edgeLine = new THREE.LineSegments(edgeGeo, edgeMat);
    edgeLine.position.copy(substrate.position);
    this.layerGroups.substrate.add(edgeLine);

    // 2. Standard Cells (Y = 1.0)
    const cells = this.data.placement.cells || [];
    for (const c of cells) {
      const w = c.width_um;
      const h = 2.0; // Cell height in 3D
      const d = c.height_um; // Row depth
      const x = (c.x_um + w / 2) - cx;
      const z = (c.y_um + d / 2) - cz;

      let color = 0x0284c7; // logic
      if (c.function.startsWith('DFF')) color = 0x9333ea; // sequential
      else if (c.function.startsWith('CLK')) color = 0x06b6d4; // clock
      else if (c.function.startsWith('FA') || c.function.startsWith('HA')) color = 0x10b981; // adder
      else if (c.function.startsWith('MUX')) color = 0xd97706; // mux

      const cellGeo = new THREE.BoxGeometry(w * 0.95, h, d * 0.9);
      const cellMat = new THREE.MeshStandardMaterial({
        color: color,
        metalness: 0.4,
        roughness: 0.5
      });
      const cellMesh = new THREE.Mesh(cellGeo, cellMat);
      cellMesh.position.set(x, h / 2, z);
      cellMesh.userData = { isCell: true, cellData: c };
      this.layerGroups.cells.add(cellMesh);
    }

    // 3. Routing Layers: Metal 1 to Metal 5
    const routes = this.data.routing.route_segments || [];
    const layerY = {
      metal1: 3.0,
      metal2: 5.5,
      metal3: 8.0,
      metal4: 10.5,
      metal5: 13.0,
      metal6: 16.0
    };

    for (const r of routes) {
      const yBase = layerY[r.layer] || 8.0;
      const x1 = r.x1 - cx;
      const z1 = r.y1 - cz;
      const x2 = r.x2 - cx;
      const z2 = r.y2 - cz;

      const len = Math.hypot(x2 - x1, z2 - z1);
      if (len < 0.1) continue;

      let color = 0x38bdf8;
      if (r.layer === 'metal2') color = 0xa855f7;
      if (r.layer === 'metal3') color = 0x3b82f6;
      if (r.layer === 'metal4') color = 0x06b6d4;
      if (r.is_critical) color = 0xfacc15;

      const lineGeo = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(x1, yBase, z1),
        new THREE.Vector3(x2, yBase, z2)
      ]);
      const lineMat = new THREE.LineBasicMaterial({
        color: color,
        linewidth: r.is_critical ? 3 : 1
      });
      const wire = new THREE.Line(lineGeo, lineMat);

      if (r.is_critical) {
        this.layerGroups.criticalPath.add(wire);
      } else if (this.layerGroups[r.layer]) {
        this.layerGroups[r.layer].add(wire);
      }
    }

    // 4. Clock Tree Network (Metal 5 trunk & Metal 4 branches)
    const ctsSegs = this.data.cts.tree_segments || [];
    for (const seg of ctsSegs) {
      const y = (seg.layer === 'metal5') ? layerY.metal5 : layerY.metal4;
      const x1 = seg.from_x - cx;
      const z1 = seg.from_y - cz;
      const x2 = seg.to_x - cx;
      const z2 = seg.to_y - cz;

      const pts = [new THREE.Vector3(x1, y, z1), new THREE.Vector3(x2, y, z2)];
      const geo = new THREE.BufferGeometry().setFromPoints(pts);
      const mat = new THREE.LineBasicMaterial({ color: 0x22d3ee, linewidth: 3 });
      const clkLine = new THREE.Line(geo, mat);
      this.layerGroups.clockTree.add(clkLine);
    }

    // 5. Power Grid Mesh (Metal 6 stripes & rings)
    const pMesh = this.data.routing.power_mesh || [];
    for (const pm of pMesh) {
      const y = (pm.layer === 'metal6') ? layerY.metal6 : layerY.metal1;
      const isVdd = (pm.net === 'VDD');
      const color = isVdd ? 0xef4444 : 0x3b82f6;

      if (pm.type === 'RING') {
        const x1 = pm.x1 - cx, z1 = pm.y1 - cz;
        const x2 = pm.x2 - cx, z2 = pm.y2 - cz;
        const ringPts = [
          new THREE.Vector3(x1, y, z1), new THREE.Vector3(x2, y, z1),
          new THREE.Vector3(x2, y, z2), new THREE.Vector3(x1, y, z2),
          new THREE.Vector3(x1, y, z1)
        ];
        const geo = new THREE.BufferGeometry().setFromPoints(ringPts);
        const mat = new THREE.LineBasicMaterial({ color: color, linewidth: 2 });
        this.layerGroups.powerMesh.add(new THREE.Line(geo, mat));
      } else {
        const x1 = pm.x1 - cx, z1 = pm.y1 - cz;
        const x2 = pm.x2 - cx, z2 = pm.y2 - cz;
        const pts = [new THREE.Vector3(x1, y, z1), new THREE.Vector3(x2, y, z2)];
        const geo = new THREE.BufferGeometry().setFromPoints(pts);
        const mat = new THREE.LineBasicMaterial({ color: color, linewidth: 2 });
        this.layerGroups.powerMesh.add(new THREE.Line(geo, mat));
      }
    }

    // 6. Via Pillars (vertical interconnects)
    const viaGeo = new THREE.CylinderGeometry(0.3, 0.3, 2.5, 6);
    const viaMat = new THREE.MeshStandardMaterial({ color: 0xe2e8f0, metalness: 0.9, roughness: 0.2 });

    const placedCells = this.data.placement.cells || [];
    for (let i = 0; i < Math.min(placedCells.length, 40); i++) {
      const c = placedCells[i];
      const vx = (c.x_um + c.width_um / 2) - cx;
      const vz = (c.y_um + c.height_um / 2) - cz;
      const via = new THREE.Mesh(viaGeo, viaMat);
      via.position.set(vx, 4.25, vz);
      this.layerGroups.vias.add(via);
    }

    // Set camera target to center of die
    if (this.controls) {
      this.controls.target.set(0, 5, 0);
      this.camera.position.set(die.width_um * 0.9, die.height_um * 1.2, die.width_um * 1.1);
    }
  }

  setLayerVisible(layerName, visible) {
    if (this.layerGroups[layerName]) {
      this.layerGroups[layerName].visible = visible;
    }
  }

  setExplodedView(factor) {
    this.explodeFactor = factor;
    const baseOffset = (factor - 1.0) * 12.0;
    if (this.layerGroups.metal1) this.layerGroups.metal1.position.y = baseOffset * 0.5;
    if (this.layerGroups.metal2) this.layerGroups.metal2.position.y = baseOffset * 1.0;
    if (this.layerGroups.metal3) this.layerGroups.metal3.position.y = baseOffset * 1.5;
    if (this.layerGroups.metal4) this.layerGroups.metal4.position.y = baseOffset * 2.0;
    if (this.layerGroups.metal5) this.layerGroups.metal5.position.y = baseOffset * 2.5;
    if (this.layerGroups.metal6) this.layerGroups.metal6.position.y = baseOffset * 3.0;
    if (this.layerGroups.clockTree) this.layerGroups.clockTree.position.y = baseOffset * 2.5;
    if (this.layerGroups.powerMesh) this.layerGroups.powerMesh.position.y = baseOffset * 3.0;
  }

  onRaycastClick(e) {
    if (!this.renderer || !this.camera || !this.scene) return;
    const rect = this.renderer.domElement.getBoundingClientRect();
    this.mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    this.mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

    this.raycaster.setFromCamera(this.mouse, this.camera);
    const intersects = this.raycaster.intersectObjects(this.layerGroups.cells.children, true);

    if (intersects.length > 0) {
      const obj = intersects[0].object;
      if (obj.userData && obj.userData.cellData) {
        const cell = obj.userData.cellData;
        if (window.CrossProbe) {
          window.CrossProbe.onPhysicalCellSelected(cell);
        }
      }
    }
  }
}
window.Visualizer3D = Visualizer3D;
