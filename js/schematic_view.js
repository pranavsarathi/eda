// Inferred Hardware Block Diagram & Schematic Visualizer
class SchematicVisualizer {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.canvas = document.createElement('canvas');
    if (this.container) {
      this.container.appendChild(this.canvas);
      this.ctx = this.canvas.getContext('2d');
    }
    this.data = null;
    this.resize();
    window.addEventListener('resize', () => this.resize());
  }

  resize() {
    if (!this.container || !this.canvas) return;
    this.canvas.width = this.container.clientWidth || 800;
    this.canvas.height = this.container.clientHeight || 500;
    this.render();
  }

  loadData(inferenceData) {
    this.data = inferenceData;
    this.render();
  }

  render() {
    if (!this.ctx) return;
    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    if (!this.data || !this.data.schematic) {
      ctx.fillStyle = '#64748b';
      ctx.font = '14px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('No hardware schematic data loaded.', this.canvas.width / 2, this.canvas.height / 2);
      return;
    }

    const nodes = this.data.schematic.nodes || [];
    const links = this.data.schematic.links || [];

    // Categorize nodes by column: Inputs -> Comb Logic -> Registers -> Outputs
    const inPorts = nodes.filter(n => n.type === 'PORT' && n.direction === 'input');
    const combNodes = nodes.filter(n => ['ADDER', 'SUBTRACTOR', 'MULTIPLIER', 'MUX', 'COMPARATOR', 'GATE'].includes(n.type));
    const seqNodes = nodes.filter(n => ['REGISTER', 'COUNTER', 'FSM', 'MEMORY'].includes(n.type));
    const outPorts = nodes.filter(n => n.type === 'PORT' && n.direction === 'output');

    const colX = [80, 260, 480, 700];
    const nodeCoords = {};

    const placeCol = (items, x) => {
      const spacing = this.canvas.height / (items.length + 1);
      items.forEach((item, idx) => {
        const y = (idx + 1) * spacing;
        nodeCoords[item.id] = { x, y, item };
      });
    };

    placeCol(inPorts, colX[0]);
    placeCol(combNodes, colX[1]);
    placeCol(seqNodes, colX[2]);
    placeCol(outPorts, colX[3]);

    // Draw Links
    ctx.strokeStyle = '#38bdf8';
    ctx.lineWidth = 1.5;
    for (const l of links) {
      const src = nodeCoords[l.source];
      const tgt = nodeCoords[l.target];
      if (src && tgt) {
        ctx.beginPath();
        ctx.moveTo(src.x + 40, src.y);
        const midX = (src.x + tgt.x) / 2;
        ctx.bezierCurveTo(midX, src.y, midX, tgt.y, tgt.x - 40, tgt.y);
        ctx.stroke();
      }
    }

    // Connect inPorts to combNodes generically if no explicit link
    if (inPorts.length > 0 && combNodes.length > 0) {
      ctx.strokeStyle = 'rgba(56, 189, 248, 0.3)';
      inPorts.forEach(ip => {
        combNodes.slice(0, 2).forEach(cn => {
          const s = nodeCoords[ip.id], t = nodeCoords[cn.id];
          if (s && t) {
            ctx.beginPath();
            ctx.moveTo(s.x + 30, s.y);
            ctx.lineTo(t.x - 40, t.y);
            ctx.stroke();
          }
        });
      });
    }

    // Connect combNodes to seqNodes
    if (combNodes.length > 0 && seqNodes.length > 0) {
      ctx.strokeStyle = 'rgba(168, 85, 247, 0.4)';
      combNodes.forEach((cn, idx) => {
        const sn = seqNodes[idx % seqNodes.length];
        const s = nodeCoords[cn.id], t = nodeCoords[sn.id];
        if (s && t) {
          ctx.beginPath();
          ctx.moveTo(s.x + 45, s.y);
          ctx.lineTo(t.x - 45, t.y);
          ctx.stroke();
        }
      });
    }

    // Connect seqNodes to outPorts
    if (seqNodes.length > 0 && outPorts.length > 0) {
      ctx.strokeStyle = 'rgba(16, 185, 129, 0.4)';
      seqNodes.forEach((sn, idx) => {
        const op = outPorts[idx % outPorts.length];
        const s = nodeCoords[sn.id], t = nodeCoords[op.id];
        if (s && t) {
          ctx.beginPath();
          ctx.moveTo(s.x + 45, s.y);
          ctx.lineTo(t.x - 30, t.y);
          ctx.stroke();
        }
      });
    }

    // Draw Nodes
    for (const [id, nc] of Object.entries(nodeCoords)) {
      const { x, y, item } = nc;
      let w = 80, h = 34;
      let bg = '#1e293b', border = '#38bdf8';

      if (item.type === 'PORT') {
        w = 60; h = 26;
        bg = item.direction === 'input' ? '#064e3b' : '#78350f';
        border = item.direction === 'input' ? '#10b981' : '#f59e0b';
      } else if (['REGISTER', 'COUNTER', 'FSM'].includes(item.type)) {
        bg = '#4c1d95'; border = '#a855f7';
      } else if (['ADDER', 'SUBTRACTOR', 'MULTIPLIER'].includes(item.type)) {
        bg = '#065f46'; border = '#34d399';
      } else if (item.type === 'MUX') {
        bg = '#7c2d12'; border = '#fb923c';
      }

      ctx.fillStyle = bg;
      ctx.strokeStyle = border;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.roundRect(x - w / 2, y - h / 2, w, h, 4);
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = '#ffffff';
      ctx.font = '11px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      const label = item.label.length > 12 ? item.label.slice(0, 11) + '..' : item.label;
      ctx.fillText(label, x, y - 2);

      // Width or subtext badge
      if (item.width) {
        ctx.fillStyle = '#94a3b8';
        ctx.font = '9px monospace';
        ctx.fillText(`[${item.width}b]`, x, y + 9);
      }
    }
  }
}

window.SchematicVisualizer = SchematicVisualizer;
