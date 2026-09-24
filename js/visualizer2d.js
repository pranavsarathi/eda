// Interactive 2D Physical Silicon Canvas Visualizer
class Visualizer2D {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext('2d');
    this.data = null;

    // Viewport transform
    this.scale = 1.0;
    this.offsetX = 40;
    this.offsetY = 40;
    this.isDragging = false;
    this.dragStartX = 0;
    this.dragStartY = 0;

    // Layer visibility
    this.layers = {
      die: true,
      rows: true,
      cells: true,
      fillers: false,
      routes: true,
      clock: true,
      power: true,
      congestion: false,
      criticalPath: true,
      pins: true
    };

    this.selectedCell = null;
    this.hoveredCell = null;

    this.initEvents();
    this.resize();
  }

  resize() {
    if (!this.canvas) return;
    const rect = this.canvas.parentElement.getBoundingClientRect();
    this.canvas.width = rect.width;
    this.canvas.height = rect.height;
    this.render();
  }

  initEvents() {
    window.addEventListener('resize', () => this.resize());

    this.canvas.addEventListener('mousedown', (e) => {
      this.isDragging = true;
      this.dragStartX = e.clientX - this.offsetX;
      this.dragStartY = e.clientY - this.offsetY;
    });

    window.addEventListener('mouseup', () => {
      this.isDragging = false;
    });

    this.canvas.addEventListener('mousemove', (e) => {
      if (this.isDragging) {
        this.offsetX = e.clientX - this.dragStartX;
        this.offsetY = e.clientY - this.dragStartY;
        this.render();
      } else {
        this.handleHover(e);
      }
    });

    this.canvas.addEventListener('wheel', (e) => {
      e.preventDefault();
      const zoomFactor = e.deltaY < 0 ? 1.15 : 0.85;
      const mouseX = e.clientX - this.canvas.getBoundingClientRect().left;
      const mouseY = e.clientY - this.canvas.getBoundingClientRect().top;

      this.offsetX = mouseX - (mouseX - this.offsetX) * zoomFactor;
      this.offsetY = mouseY - (mouseY - this.offsetY) * zoomFactor;
      this.scale *= zoomFactor;
      this.render();
    });

    this.canvas.addEventListener('click', (e) => {
      this.handleClick(e);
    });
  }

  loadData(pipelineData) {
    this.data = pipelineData;
    this.fitToScreen();
    this.render();
  }

  fitToScreen() {
    if (!this.data || !this.data.floorplan || !this.data.floorplan.die) return;
    const die = this.data.floorplan.die;
    const pad = 80;
    const availW = this.canvas.width - pad * 2;
    const availH = this.canvas.height - pad * 2;

    const scaleX = availW / die.width_um;
    const scaleY = availH / die.height_um;
    this.scale = Math.min(scaleX, scaleY);

    this.offsetX = (this.canvas.width - die.width_um * this.scale) / 2;
    this.offsetY = (this.canvas.height - die.height_um * this.scale) / 2;
  }

  umToPx(x_um, y_um) {
    return {
      x: this.offsetX + x_um * this.scale,
      y: this.offsetY + (this.data.floorplan.die.height_um - y_um) * this.scale
    };
  }

  pxToUm(px, py) {
    return {
      x: (px - this.offsetX) / this.scale,
      y: this.data.floorplan.die.height_um - (py - this.offsetY) / this.scale
    };
  }

  handleHover(e) {
    if (!this.data || !this.data.placement) return;
    const rect = this.canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    const um = this.pxToUm(mouseX, mouseY);

    const prevHover = this.hoveredCell;
    this.hoveredCell = null;

    // Check placed cells
    const cells = this.data.placement.cells || [];
    for (const c of cells) {
      if (um.x >= c.x_um && um.x <= (c.x_um + c.width_um) &&
          um.y >= c.y_um && um.y <= (c.y_um + c.height_um)) {
        this.hoveredCell = c;
        break;
      }
    }

    if (this.hoveredCell !== prevHover) {
      this.canvas.style.cursor = this.hoveredCell ? 'pointer' : 'crosshair';
      this.render();
      if (this.hoveredCell) {
        this.showTooltip(this.hoveredCell, e.clientX, e.clientY);
      } else {
        this.hideTooltip();
      }
    }
  }

  handleClick(e) {
    if (!this.data) return;
    const rect = this.canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    const um = this.pxToUm(mouseX, mouseY);

    // Check cells
    const cells = this.data.placement.cells || [];
    for (const c of cells) {
      if (um.x >= c.x_um && um.x <= (c.x_um + c.width_um) &&
          um.y >= c.y_um && um.y <= (c.y_um + c.height_um)) {
        this.selectedCell = c;
        this.render();
        if (window.CrossProbe) {
          window.CrossProbe.onPhysicalCellSelected(c);
        }
        return;
      }
    }

    // Check ports
    const ports = this.data.floorplan.ports || [];
    for (const p of ports) {
      const dist = Math.hypot(um.x - p.x_um, um.y - p.y_um);
      if (dist < 4.0) {
        if (window.CrossProbe) {
          window.CrossProbe.onPortSelected(p);
        }
        return;
      }
    }

    this.selectedCell = null;
    this.render();
  }

  showTooltip(cell, clientX, clientY) {
    let tip = document.getElementById('canvas2d-tooltip');
    if (!tip) {
      tip = document.createElement('div');
      tip.id = 'canvas2d-tooltip';
      tip.style.position = 'fixed';
      tip.style.background = 'rgba(15, 23, 42, 0.95)';
      tip.style.border = '1px solid #38bdf8';
      tip.style.padding = '8px 12px';
      tip.style.borderRadius = '4px';
      tip.style.fontSize = '11px';
      tip.style.color = '#e2e8f0';
      tip.style.pointerEvents = 'none';
      tip.style.zIndex = '1000';
      tip.style.fontFamily = 'monospace';
      document.body.appendChild(tip);
    }
    tip.style.display = 'block';
    tip.style.left = (clientX + 14) + 'px';
    tip.style.top = (clientY + 14) + 'px';
    tip.innerHTML = `
      <div style="font-weight: bold; color: #38bdf8;">${cell.inst_name}</div>
      <div>Type: <span style="color:#a7f3d0;">${cell.cell_type}</span> (${cell.function})</div>
      <div>Pos: (${cell.x_um} µm, ${cell.y_um} µm)</div>
      <div>Size: ${cell.width_um} × ${cell.height_um} µm</div>
      <div style="color: #fde68a;">RTL Source: Line ${cell.rtl_line}</div>
    `;
  }

  hideTooltip() {
    const tip = document.getElementById('canvas2d-tooltip');
    if (tip) tip.style.display = 'none';
  }

  render() {
    if (!this.ctx) return;
    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    if (!this.data || !this.data.floorplan || !this.data.floorplan.die) {
      ctx.fillStyle = this.data?.compile?.status === 'FAIL' ? '#ef4444' : '#64748b';
      ctx.font = '14px Inter, sans-serif';
      ctx.textAlign = 'center';
      const msg = this.data?.compile?.status === 'FAIL'
        ? 'RTL Compilation Error: Physical estimation halted. See "Verify & Simulate" tab.'
        : 'Load and run RTL pipeline to view estimated 2D physical design';
      ctx.fillText(msg, this.canvas.width / 2, this.canvas.height / 2);
      return;
    }

    const fp = this.data.floorplan;
    const die = fp.die;
    const core = fp.core;

    // 1. Die Boundary
    if (this.layers.die) {
      const dieP1 = this.umToPx(0, die.height_um);
      ctx.fillStyle = '#0f172a';
      ctx.fillRect(dieP1.x, dieP1.y, die.width_um * this.scale, die.height_um * this.scale);
      ctx.strokeStyle = '#334155';
      ctx.lineWidth = 1.5;
      ctx.strokeRect(dieP1.x, dieP1.y, die.width_um * this.scale, die.height_um * this.scale);

      // Core Boundary
      const coreP1 = this.umToPx(core.x_um, core.y_um + core.height_um);
      ctx.fillStyle = '#131d31';
      ctx.fillRect(coreP1.x, coreP1.y, core.width_um * this.scale, core.height_um * this.scale);
      ctx.strokeStyle = '#38bdf8';
      ctx.setLineDash([4, 4]);
      ctx.strokeRect(coreP1.x, coreP1.y, core.width_um * this.scale, core.height_um * this.scale);
      ctx.setLineDash([]);
    }

    // 2. Standard Cell Rows
    if (this.layers.rows && fp.rows) {
      ctx.strokeStyle = '#1e293b';
      ctx.lineWidth = 0.5;
      for (const r of fp.rows) {
        const rp = this.umToPx(core.x_um, r.y_um + r.height_um);
        ctx.strokeRect(rp.x, rp.y, r.width_um * this.scale, r.height_um * this.scale);
      }
    }

    // 3. Congestion Heatmap Overlay
    if (this.layers.congestion && this.data.routing && this.data.routing.congestion_grid) {
      const gcells = this.data.routing.congestion_grid.gcells || [];
      for (const gc of gcells) {
        const p = this.umToPx(gc.x_min, gc.y_max);
        const w = (gc.x_max - gc.x_min) * this.scale;
        const h = (gc.y_max - gc.y_min) * this.scale;

        let alpha = Math.min(0.7, gc.utilization / 100.0);
        let color = `rgba(16, 185, 129, ${alpha})`;
        if (gc.utilization > 50) color = `rgba(245, 158, 11, ${alpha})`;
        if (gc.utilization > 75) color = `rgba(239, 68, 68, ${alpha})`;

        ctx.fillStyle = color;
        ctx.fillRect(p.x, p.y, w, h);
      }
    }

    // 4. Filler Cells
    if (this.layers.fillers && this.data.placement && this.data.placement.fillers) {
      ctx.fillStyle = '#1a2234';
      ctx.strokeStyle = '#26334a';
      ctx.lineWidth = 0.5;
      for (const f of this.data.placement.fillers) {
        const p = this.umToPx(f.x_um, f.y_um + f.height_um);
        const w = f.width_um * this.scale;
        const h = f.height_um * this.scale;
        ctx.fillRect(p.x, p.y, w, h);
        ctx.strokeRect(p.x, p.y, w, h);
      }
    }

    // 5. Placed Cells
    if (this.layers.cells && this.data.placement && this.data.placement.cells) {
      for (const c of this.data.placement.cells) {
        const p = this.umToPx(c.x_um, c.y_um + c.height_um);
        const w = c.width_um * this.scale;
        const h = c.height_um * this.scale;

        let fillColor = '#0284c7'; // default logic
        if (c.function.startsWith('DFF')) fillColor = '#9333ea'; // seq flip-flop (purple)
        else if (c.function.startsWith('CLK')) fillColor = '#06b6d4'; // clock buf (cyan)
        else if (c.function.startsWith('FA') || c.function.startsWith('HA')) fillColor = '#10b981'; // adder (green)
        else if (c.function.startsWith('MUX')) fillColor = '#d97706'; // mux (amber)

        ctx.fillStyle = fillColor;
        ctx.fillRect(p.x, p.y, w, h);
        ctx.strokeStyle = '#000';
        ctx.lineWidth = 0.5;
        ctx.strokeRect(p.x, p.y, w, h);

        // Selection highlight
        if (this.selectedCell && this.selectedCell.inst_name === c.inst_name) {
          ctx.strokeStyle = '#facc15';
          ctx.lineWidth = 2.0;
          ctx.strokeRect(p.x - 1, p.y - 1, w + 2, h + 2);
        }
      }
    }

    // 6. Signal Routing (M1 - M4)
    if (this.layers.routes && this.data.routing && this.data.routing.route_segments) {
      for (const seg of this.data.routing.route_segments) {
        const p1 = this.umToPx(seg.x1, seg.y1);
        const p2 = this.umToPx(seg.x2, seg.y2);

        let color = '#38bdf8';
        if (seg.layer === 'metal2') color = '#a855f7';
        if (seg.layer === 'metal3') color = '#3b82f6';
        if (seg.layer === 'metal4') color = '#06b6d4';

        if (seg.is_critical && this.layers.criticalPath) {
          color = '#eab308'; // Glowing gold for critical path
          ctx.lineWidth = 2.0;
        } else {
          ctx.lineWidth = 1.0;
        }

        ctx.strokeStyle = color;
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.stroke();
      }
    }

    // 7. Clock Tree Network (Metal 5 & Metal 4 CTS)
    if (this.layers.clock && this.data.cts && this.data.cts.tree_segments) {
      ctx.strokeStyle = '#22d3ee';
      ctx.lineWidth = 2.0;
      for (const seg of this.data.cts.tree_segments) {
        const p1 = this.umToPx(seg.from_x, seg.from_y);
        const p2 = this.umToPx(seg.to_x, seg.to_y);
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.stroke();
      }
    }

    // 8. Power Mesh (M6 & M1)
    if (this.layers.power && this.data.routing && this.data.routing.power_mesh) {
      for (const pm of this.data.routing.power_mesh) {
        const isVdd = (pm.net === 'VDD');
        ctx.strokeStyle = isVdd ? 'rgba(239, 68, 68, 0.4)' : 'rgba(59, 130, 246, 0.4)';
        ctx.lineWidth = Math.max(1, (pm.width_um || 1.0) * this.scale);

        if (pm.type === 'RING') {
          const p1 = this.umToPx(pm.x1, pm.y2);
          const w = (pm.x2 - pm.x1) * this.scale;
          const h = (pm.y2 - pm.y1) * this.scale;
          ctx.strokeRect(p1.x, p1.y, w, h);
        } else {
          const p1 = this.umToPx(pm.x1, pm.y1);
          const p2 = this.umToPx(pm.x2, pm.y2);
          ctx.beginPath();
          ctx.moveTo(p1.x, p1.y);
          ctx.lineTo(p2.x, p2.y);
          ctx.stroke();
        }
      }
    }

    // 9. IO Ports & Boundary Pins
    if (this.layers.pins && fp.ports) {
      for (const p of fp.ports) {
        const pt = this.umToPx(p.x_um, p.y_um);
        const isClk = p.is_clock;

        ctx.fillStyle = isClk ? '#06b6d4' : (p.direction === 'input' ? '#10b981' : '#f59e0b');
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, 4.5, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1;
        ctx.stroke();

        // Pin labels
        ctx.fillStyle = '#cbd5e1';
        ctx.font = '10px Inter, sans-serif';
        if (p.side === 'top') {
          ctx.textAlign = 'center';
          ctx.fillText(p.name, pt.x, pt.y - 8);
        } else if (p.side === 'bottom') {
          ctx.textAlign = 'center';
          ctx.fillText(p.name, pt.x, pt.y + 16);
        } else if (p.side === 'left') {
          ctx.textAlign = 'right';
          ctx.fillText(p.name, pt.x - 8, pt.y + 3);
        } else {
          ctx.textAlign = 'left';
          ctx.fillText(p.name, pt.x + 8, pt.y + 3);
        }
      }
    }

    // Scale Ruler (bottom right)
    this.renderRuler();
  }

  renderRuler() {
    const ctx = this.ctx;
    const rulerUm = 20.0; // 20 um ruler bar
    const rulerPx = rulerUm * this.scale;
    const rx = this.canvas.width - rulerPx - 30;
    const ry = this.canvas.height - 25;

    ctx.strokeStyle = '#94a3b8';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(rx, ry);
    ctx.lineTo(rx + rulerPx, ry);
    ctx.moveTo(rx, ry - 4);
    ctx.lineTo(rx, ry + 4);
    ctx.moveTo(rx + rulerPx, ry - 4);
    ctx.lineTo(rx + rulerPx, ry + 4);
    ctx.stroke();

    ctx.fillStyle = '#94a3b8';
    ctx.font = '10px monospace';
    ctx.textAlign = 'center';
    ctx.fillText(`${rulerUm} µm`, rx + rulerPx / 2, ry - 6);
  }
}
window.Visualizer2D = Visualizer2D;
