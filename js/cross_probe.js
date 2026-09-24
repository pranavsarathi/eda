// RTL <-> Physical Design Cross-Probing Subsystem
class CrossProbeManager {
  constructor() {
    this.selectedCell = null;
    this.selectedLine = null;
    this.inspectorCard = document.getElementById('inspector-card');
  }

  onPhysicalCellSelected(cell) {
    this.selectedCell = cell;
    this.showCellInspector(cell);
    this.highlightRTLLine(cell.rtl_line);
  }

  onPortSelected(port) {
    this.showPortInspector(port);
  }

  showCellInspector(cell) {
    const card = document.getElementById('inspector-card');
    if (!card) return;
    card.style.display = 'block';

    card.innerHTML = `
      <div class="inspector-title">
        <span>PHYSICAL CELL INSPECTOR</span>
        <button onclick="document.getElementById('inspector-card').style.display='none'" style="background:none;border:none;color:#94a3b8;cursor:pointer;">✕</button>
      </div>
      <table style="width:100%; font-size:11px; margin-top:6px;">
        <tr><th style="color:#94a3b8; width:90px;">Instance:</th><td style="color:#38bdf8; font-weight:bold;">${cell.inst_name}</td></tr>
        <tr><th style="color:#94a3b8;">Cell Type:</th><td style="color:#a7f3d0;">${cell.cell_type}</td></tr>
        <tr><th style="color:#94a3b8;">Function:</th><td>${cell.function}</td></tr>
        <tr><th style="color:#94a3b8;">Physical Pos:</th><td>X: ${cell.x_um} µm, Y: ${cell.y_um} µm</td></tr>
        <tr><th style="color:#94a3b8;">Dimensions:</th><td>${cell.width_um} µm × ${cell.height_um} µm</td></tr>
        <tr><th style="color:#94a3b8;">Row Index:</th><td>Row #${cell.row_idx}</td></tr>
        <tr><th style="color:#f59e0b;">RTL Source:</th><td style="color:#fde68a; font-weight:bold; text-decoration:underline; cursor:pointer;" onclick="CrossProbe.highlightRTLLine(${cell.rtl_line})">Line ${cell.rtl_line}</td></tr>
      </table>
      <div style="margin-top:8px; padding:6px; background:#0f172a; border-radius:4px; font-size:10px; color:#94a3b8;">
        <strong>Silicon Origin:</strong> Synthesized from Verilog statement at line ${cell.rtl_line}. Inferred hardware block: <code>${cell.block_ref || 'logic'}</code>.
      </div>
    `;
  }

  showPortInspector(port) {
    const card = document.getElementById('inspector-card');
    if (!card) return;
    card.style.display = 'block';

    card.innerHTML = `
      <div class="inspector-title">
        <span>IO PORT INSPECTOR</span>
        <button onclick="document.getElementById('inspector-card').style.display='none'" style="background:none;border:none;color:#94a3b8;cursor:pointer;">✕</button>
      </div>
      <table style="width:100%; font-size:11px; margin-top:6px;">
        <tr><th style="color:#94a3b8; width:90px;">Port Name:</th><td style="color:#38bdf8; font-weight:bold;">${port.name}</td></tr>
        <tr><th style="color:#94a3b8;">Direction:</th><td style="color:#a7f3d0; text-transform:uppercase;">${port.direction}</td></tr>
        <tr><th style="color:#94a3b8;">Bit Width:</th><td>${port.width} bit(s)</td></tr>
        <tr><th style="color:#94a3b8;">Boundary Side:</th><td>${port.side.toUpperCase()} edge</td></tr>
        <tr><th style="color:#94a3b8;">Pin Layer:</th><td>${port.layer}</td></tr>
        <tr><th style="color:#94a3b8;">Est. Fanout:</th><td>${port.estimated_fanout} loads</td></tr>
        <tr><th style="color:#94a3b8;">CTS Required:</th><td>${port.cts_required ? '<span style="color:#06b6d4;font-weight:bold;">YES (Clock Root)</span>' : 'NO'}</td></tr>
      </table>
      <div style="margin-top:8px; padding:6px; background:#0f172a; border-radius:4px; font-size:10px; color:#cbd5e1;">
        <strong>Placement Rationale:</strong> ${port.reason}
      </div>
    `;
  }

  highlightRTLLine(lineNumber) {
    if (!lineNumber) return;
    this.selectedLine = lineNumber;

    const editor = document.getElementById('rtl-editor');
    if (!editor) return;

    // Split text by lines and find character offset of target line
    const lines = editor.value.split('\n');
    if (lineNumber > lines.length) return;

    let charOffset = 0;
    for (let i = 0; i < lineNumber - 1; i++) {
      charOffset += lines[i].length + 1; // +1 for newline
    }
    const lineLen = lines[lineNumber - 1].length;

    editor.focus();
    editor.setSelectionRange(charOffset, charOffset + lineLen);

    // Scroll textarea to line
    const lineHeight = 18; // approx line height in px
    editor.scrollTop = Math.max(0, (lineNumber - 4) * lineHeight);

    // Flash notification in editor status
    const statusEl = document.getElementById('editor-line-status');
    if (statusEl) {
      statusEl.innerHTML = `<span style="color:#facc15; font-weight:bold;">Cross-Probed to Line ${lineNumber}</span>`;
      setTimeout(() => {
        statusEl.innerHTML = `Lines: ${lines.length}`;
      }, 3000);
    }
  }

  onRTLSelectionChanged(lineNum) {
    if (!window.currentPipelineData || !window.currentPipelineData.placement) return;
    const cells = window.currentPipelineData.placement.cells || [];

    // Find all cells generated by this line
    const matching = cells.filter(c => c.rtl_line === lineNum);
    if (matching.length > 0 && window.v2d) {
      window.v2d.selectedCell = matching[0];
      window.v2d.render();
      this.showCellInspector(matching[0]);
    }
  }
}

window.CrossProbe = new CrossProbeManager();
