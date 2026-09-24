// Main EDA Workstation Controller — Unified 5-Screen Causal Architecture
let currentPipelineData = null;
let v2d = null;
let v3d = null;
let schem = null;
let is3DMode = false;

document.addEventListener('DOMContentLoaded', () => {
  initUI();
  initVisualizers();
  loadExamples();
});

function initVisualizers() {
  v2d = new Visualizer2D('canvas2d');
  window.v2d = v2d;

  v3d = new Visualizer3D('canvas3d-wrapper');
  window.v3d = v3d;

  schem = new SchematicVisualizer('schematic-canvas-wrapper');
  window.schem = schem;
}

function initUI() {
  // Navigation tabs (VERIFY, HARDWARE, PHYSICAL, REPORT)
  document.querySelectorAll('.nav-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.view-panel').forEach(p => p.classList.remove('active'));

      tab.classList.add('active');
      const targetId = tab.getAttribute('data-view');
      const panel = document.getElementById(targetId);
      if (panel) {
        panel.classList.add('active');
        if (targetId === 'view-physical') {
          if (is3DMode && v3d) setTimeout(() => v3d.onWindowResize(), 50);
          else if (v2d) setTimeout(() => v2d.resize(), 50);
        }
        if (targetId === 'view-hardware' && schem) setTimeout(() => schem.resize(), 50);
      }
    });
  });

  // Editor tabs (RTL vs TESTBENCH)
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const tabName = btn.getAttribute('data-tab');
      document.getElementById('rtl-editor').style.display = (tabName === 'rtl') ? 'block' : 'none';
      document.getElementById('tb-editor').style.display = (tabName === 'tb') ? 'block' : 'none';
    });
  });

  // 2D Layer Checkboxes
  document.querySelectorAll('.layer-checkbox').forEach(cb => {
    cb.addEventListener('change', () => {
      const layer = cb.getAttribute('data-layer');
      if (v2d) {
        v2d.layers[layer] = cb.checked;
        v2d.render();
      }
    });
  });

  // 3D Layer Checkboxes
  document.querySelectorAll('.layer3d-checkbox').forEach(cb => {
    cb.addEventListener('change', () => {
      const layer = cb.getAttribute('data-layer3d');
      if (v3d) v3d.setLayerVisible(layer, cb.checked);
    });
  });

  // RTL & Testbench Editor Stale State Listeners
  const rtlEditor = document.getElementById('rtl-editor');
  const tbEditor = document.getElementById('tb-editor');

  const markStale = () => {
    currentPipelineData = null;
    window.currentPipelineData = null;

    const staleBanner = document.getElementById('stale-banner');
    if (staleBanner) staleBanner.style.display = 'flex';

    const rightPane = document.querySelector('.right-pane');
    if (rightPane) rightPane.classList.add('stale-dimmed');

    const statusBar = document.querySelector('.eda-status-bar');
    if (statusBar) statusBar.classList.add('stale-dimmed');

    const badge = document.getElementById('status-verif-badge');
    if (badge) {
      badge.textContent = 'STALE';
      badge.className = 'badge badge-warn';
    }

    const stateEl = document.getElementById('status-pipeline-state');
    if (stateEl) {
      stateEl.textContent = 'Code changed (Stale)';
      stateEl.style.color = '#f59e0b';
    }
  };

  rtlEditor.addEventListener('input', () => {
    const lines = rtlEditor.value.split('\n').length;
    document.getElementById('editor-line-status').textContent = `Lines: ${lines}`;
    markStale();
  });

  tbEditor.addEventListener('input', () => {
    markStale();
  });

  // Config controls also invalidate old results
  ['tech-node-select', 'clock-target-input', 'core-util-input', 'aspect-ratio-input'].forEach(id => {
    document.getElementById(id)?.addEventListener('change', markStale);
  });

  rtlEditor.addEventListener('click', (e) => {
    const textBefore = rtlEditor.value.substr(0, rtlEditor.selectionStart);
    const lineNum = textBefore.split('\n').length;
    if (window.CrossProbe) {
      window.CrossProbe.onRTLSelectionChanged(lineNum);
    }
  });
}

// Load canonical examples into dropdown
async function loadExamples() {
  try {
    const res = await fetch('/api/examples');
    const examples = await res.json();
    const select = document.getElementById('example-select');

    select.addEventListener('change', () => {
      const selected = examples[select.value];
      if (selected) {
        document.getElementById('rtl-editor').value = selected.rtl;
        document.getElementById('tb-editor').value = selected.tb;
        const lines = selected.rtl.split('\n').length;
        document.getElementById('editor-line-status').textContent = `Lines: ${lines}`;
        document.getElementById('editor-file-info').textContent = `Example: ${selected.name}`;

        // Invalidate old results immediately. User MUST click Run Analysis!
        currentPipelineData = null;
        window.currentPipelineData = null;

        const staleBanner = document.getElementById('stale-banner');
        if (staleBanner) staleBanner.style.display = 'flex';
        document.querySelector('.right-pane')?.classList.add('stale-dimmed');
        document.querySelector('.eda-status-bar')?.classList.add('stale-dimmed');

        const badge = document.getElementById('status-verif-badge');
        if (badge) {
          badge.textContent = 'STALE';
          badge.className = 'badge badge-warn';
        }
        const stateEl = document.getElementById('status-pipeline-state');
        if (stateEl) {
          stateEl.textContent = 'Example loaded. Click [RUN ANALYSIS]';
          stateEl.style.color = '#38bdf8';
        }
      }
    });

    // Populate first example (Counter) into editors only; user triggers analysis
    const defaultKey = 'counter';
    if (examples[defaultKey]) {
      document.getElementById('rtl-editor').value = examples[defaultKey].rtl;
      document.getElementById('tb-editor').value = examples[defaultKey].tb;
      const lines = examples[defaultKey].rtl.split('\n').length;
      document.getElementById('editor-line-status').textContent = `Lines: ${lines}`;
      document.getElementById('editor-file-info').textContent = `Example: ${examples[defaultKey].name}`;
      select.value = defaultKey;
      const stateEl = document.getElementById('status-pipeline-state');
      if (stateEl) {
        stateEl.textContent = 'Ready. Click [RUN ANALYSIS]';
        stateEl.style.color = '#38bdf8';
      }
    }
  } catch (e) {
    console.warn('Could not load examples:', e);
  }
}

// Single Canonical Pipeline Trigger
async function runAnalysis() {
  const rtl = document.getElementById('rtl-editor').value;
  const tb = document.getElementById('tb-editor').value;
  const techNode = document.getElementById('tech-node-select').value;
  const clockMhz = parseFloat(document.getElementById('clock-target-input').value) || 100.0;
  const coreUtil = parseFloat(document.getElementById('core-util-input').value) / 100.0 || 0.70;
  const aspectRatio = parseFloat(document.getElementById('aspect-ratio-input').value) || 1.0;

  // Clear stale state
  const staleBanner = document.getElementById('stale-banner');
  if (staleBanner) staleBanner.style.display = 'none';
  document.querySelector('.right-pane')?.classList.remove('stale-dimmed');
  document.querySelector('.eda-status-bar')?.classList.remove('stale-dimmed');

  showLoading(true);

  try {
    const res = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        rtl: rtl,
        tb: tb,
        tech_node: techNode,
        clock_mhz: clockMhz,
        core_util: coreUtil,
        aspect_ratio: aspectRatio
      })
    });

    const data = await res.json();
    if (data.error) {
      alert(`Pipeline Execution Error: ${data.error}`);
      showLoading(false);
      return;
    }

    currentPipelineData = data;
    window.currentPipelineData = data;
    renderResults(data);
  } catch (err) {
    console.error('API call failed:', err);
    alert('Failed to connect to backend server. Make sure server.py is running.');
  } finally {
    showLoading(false);
  }
}

function showLoading(show) {
  const btn = document.getElementById('btn-run');
  if (btn) {
    btn.disabled = show;
    btn.innerHTML = show ? '<span>⏳</span> ANALYZING...' : '<span>▶</span> RUN ANALYSIS';
  }
}

// Master Render Dispatcher
function renderResults(d) {
  const isCompileFail = d.compile && d.compile.status === 'FAIL';
  const verifStatus = isCompileFail ? 'COMPILE ERROR' : (d.verification?.correctness_state || d.verification?.status || 'UNKNOWN');
  const isPass = verifStatus === 'VERIFIED';

  // 1. Status Bar & Header Badges
  const badgeEl = document.getElementById('status-verif-badge');
  if (badgeEl) {
    badgeEl.textContent = verifStatus;
    badgeEl.className = `badge ${isPass ? 'badge-pass' : (isCompileFail || verifStatus === 'FAILED' ? 'badge-fail' : 'badge-warn')}`;
  }

  const stateEl = document.getElementById('status-pipeline-state');
  if (stateEl) {
    stateEl.textContent = isCompileFail ? 'Compile Error (Physical Blocked)' : 'Analysis Complete';
    stateEl.style.color = isCompileFail ? '#ef4444' : '#10b981';
  }

  const cells = d.synthesis?.total_cells ?? d.synthesisEstimate?.total_cells;
  const cellsEl = document.getElementById('status-cells');
  if (cellsEl) cellsEl.textContent = cells ? `${cells}` : '--';

  const area = d.floorplan?.core?.area_um2 ?? d.floorplanEstimate?.core?.area_um2;
  const areaEl = document.getElementById('status-area');
  if (areaEl) areaEl.textContent = area ? `${Math.round(area).toLocaleString()} µm²` : '--';

  const fmax = d.timing?.estimated_fmax_mhz ?? d.timingEstimate?.estimated_fmax_mhz;
  const fmaxEl = document.getElementById('status-fmax');
  if (fmaxEl) fmaxEl.textContent = fmax ? `${fmax} MHz` : '--';

  const slack = d.timing?.worst_setup_slack_ns ?? d.timingEstimate?.worst_setup_slack_ns;
  const slackEl = document.getElementById('status-slack');
  if (slackEl) {
    if (slack !== undefined && slack !== null) {
      slackEl.textContent = `${slack >= 0 ? '+' : ''}${slack} ns`;
      slackEl.style.color = slack >= 0 ? '#10b981' : '#ef4444';
    } else {
      slackEl.textContent = '--';
      slackEl.style.color = 'var(--text-main)';
    }
  }

  const elapEl = document.getElementById('status-elapsed');
  if (elapEl) elapEl.textContent = `${d.elapsed_ms || 0}ms`;

  // 2. Render Screen 1: VERIFY
  renderVerifyScreen(d);

  // 3. Render Screen 2: HARDWARE
  renderHardwareScreen(d);

  // 4. Render Screen 3: PHYSICAL
  renderPhysicalScreen(d);

  // 5. Render Screen 4: REPORT
  renderReportScreen(d);

  // If compilation failed, auto-navigate to VERIFY screen so student sees errors immediately
  if (isCompileFail) {
    const verifTab = document.querySelector('.nav-tab[data-view="view-verify"]');
    if (verifTab) verifTab.click();
  }
}

// ----------------------------------------------------
// SCREEN 1: VERIFY & SIMULATION
// ----------------------------------------------------
function renderVerifyScreen(d) {
  const container = document.getElementById('verification-content');
  if (!container) return;

  const compile = d.compile || { status: 'PASS', errors: [], warnings: [], modules: [] };
  const sim = d.simulation || { executed: false, exit_code: 0, stdout: '', duration_ms: 0, reason: '' };
  const verif = d.verification || {};
  const tbChecks = verif.tb_checks || {};
  const isCompileFail = compile.status === 'FAIL';
  const isSimExecuted = sim.executed;

  let html = `
    <div style="padding:20px; overflow-y:auto; height:100%;">
      <!-- Status Cards -->
      <div class="dashboard-grid" style="padding:0; margin-bottom:20px;">
        <div class="metric-card">
          <div class="metric-card-title">1. RTL Compilation</div>
          <div class="metric-val-large" style="color:${isCompileFail ? '#ef4444' : '#10b981'};">
            ${isCompileFail ? 'FAIL' : 'PASS'}
          </div>
          <div style="font-size:11px; color:#94a3b8; margin-top:4px;">
            ${compile.errors.length} error(s), ${compile.warnings.length} warning(s)
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-card-title">2. Testbench Simulation</div>
          <div class="metric-val-large" style="color:${!isSimExecuted ? '#64748b' : (sim.exit_code === 0 ? '#10b981' : '#ef4444')};">
            ${!isSimExecuted ? 'NOT RUN' : (sim.exit_code === 0 ? 'PASS' : 'FAIL')}
          </div>
          <div style="font-size:11px; color:#38bdf8; margin-top:4px;">
            ${isSimExecuted ? `Exit Code ${sim.exit_code} (${sim.duration_ms}ms)` : (sim.reason ? 'Skipped' : 'No TB')}
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-card-title">3. Correctness State</div>
          <div class="metric-val-large" style="color:${verif.correctness_state === 'VERIFIED' ? '#10b981' : (verif.correctness_state === 'FAILED' ? '#ef4444' : '#f59e0b')}; font-size:18px;">
            ${verif.correctness_state || (isCompileFail ? 'FAILED' : 'UNVERIFIED')}
          </div>
          <div style="font-size:11px; color:#94a3b8; margin-top:4px;">Evidence-based RTL evaluation</div>
        </div>

        <div class="metric-card">
          <div class="metric-card-title">4. Testbench Quality</div>
          <div class="metric-val-large" style="color:#38bdf8; font-size:18px;">
            ${tbChecks.status || (isCompileFail ? 'BLOCKED' : 'UNVERIFIED')}
          </div>
          <div style="font-size:11px; color:#10b981; margin-top:4px;">
            ${tbChecks.self_checking ? 'Self-Checking Assertions' : (tbChecks.outputs_observed ? 'Outputs Observed ($display)' : 'Stimulus Only')}
          </div>
        </div>
      </div>

      <!-- Real Simulation Terminal Output -->
      <div class="terminal-window">
        <div class="terminal-header">
          <div class="terminal-title">
            <span>🖥️</span> REAL SIMULATION CONSOLE OUTPUT ($display stdout)
          </div>
          <div class="terminal-status">
            ${isSimExecuted ? `EXIT: ${sim.exit_code} | SIM TIME: ${sim.simulation_time_units || 0} units | RUNTIME: ${sim.duration_ms}ms` : 'SIMULATION NOT EXECUTED'}
          </div>
        </div>
        <pre class="terminal-body">${
          isSimExecuted && sim.stdout
            ? escapeHtml(sim.stdout)
            : (isCompileFail
                ? `[COMPILER HALT] Simulation aborted because RTL has fatal compilation errors.\n` + compile.errors.map(e => `  >> ERROR: ${e}`).join('\n')
                : (sim.reason || `[SIMULATION INFO] Simulation completed. However: No output correctness checks were detected in testbench.`))
        }</pre>
      </div>

      <!-- Transparent Smoke Test Checklist -->
      <div style="margin-bottom:20px;">
        <h3 style="color:#38bdf8; font-size:12px; font-weight:700; margin-bottom:8px;">TRANSPARENT SMOKE TEST CHECKLIST</h3>
        <table class="data-table">
          <tr><th>Verification Check</th><th>Status</th><th>Criterion</th></tr>
          ${(verif.smoke_items && verif.smoke_items.length > 0) ? verif.smoke_items.map(item => {
            const st = (item.status || '').toUpperCase();
            const isP = st === 'PASS' || st === 'VERIFIED';
            const isF = st === 'FAIL' || st === 'FAILED';
            const bClass = isP ? 'badge-pass' : (isF ? 'badge-fail' : 'badge-warn');
            const icon = isP ? '✓ ' : (isF ? '✕ ' : '⚠ ');
            return `<tr>
              <td><strong>${escapeHtml(item.name)}</strong></td>
              <td><span class="badge ${bClass}">${icon}${escapeHtml(item.status)}</span></td>
              <td>${escapeHtml(item.standard || '')}</td>
            </tr>`;
          }).join('') : `
          <tr>
            <td><strong>1. RTL Compilation</strong></td>
            <td><span class="badge ${!isCompileFail ? 'badge-pass' : 'badge-fail'}">${!isCompileFail ? '✓ PASS' : '✕ FAIL'}</span></td>
            <td>RTL parses into valid AST without syntax or critical lint errors.</td>
          </tr>
          <tr>
            <td><strong>2. Simulation Execution</strong></td>
            <td><span class="badge ${isSimExecuted && sim.exit_code === 0 ? 'badge-pass' : (isSimExecuted ? 'badge-fail' : 'badge-warn')}">${isSimExecuted && sim.exit_code === 0 ? '✓ PASS' : (isSimExecuted ? '✕ FAIL' : '✕ NOT RUN')}</span></td>
            <td>Testbench stimulus executes in simulator to clean $finish.</td>
          </tr>
          <tr>
            <td><strong>3. Testbench Activity</strong></td>
            <td><span class="badge ${tbChecks.status === 'VALID' ? 'badge-pass' : 'badge-warn'}">${tbChecks.status === 'VALID' ? '✓ PASS' : '✕ INCOMPLETE'}</span></td>
            <td>Clock generation, reset sequence, and input stimuli driven into DUT.</td>
          </tr>
          <tr>
            <td><strong>4. Output Observation</strong></td>
            <td><span class="badge ${tbChecks.outputs_observed ? 'badge-pass' : 'badge-warn'}">${tbChecks.outputs_observed ? '✓ PASS' : '✕ NOT OBSERVED'}</span></td>
            <td>DUT output signals inspected or displayed via $display/$monitor.</td>
          </tr>
          <tr>
            <td><strong>5. Self-Checking Assertions</strong></td>
            <td><span class="badge ${tbChecks.self_checking ? 'badge-pass' : 'badge-warn'}">${tbChecks.self_checking ? '✓ PASS' : '⚠ NOT PROVEN'}</span></td>
            <td>Automated assertions or expected-vs-actual checks prove correctness.</td>
          </tr>
          <tr>
            <td><strong>6. Functional Correctness</strong></td>
            <td><span class="badge ${verif.correctness_state === 'VERIFIED' ? 'badge-pass' : (verif.correctness_state === 'FAILED' ? 'badge-fail' : 'badge-warn')}">${verif.correctness_state || 'UNVERIFIED'}</span></td>
            <td>Evidence-based functional verification sign-off.</td>
          </tr>
          `}
        </table>
      </div>
  `;

  // Compilation / Lint Issues Section if any
  if (compile.errors.length > 0 || compile.warnings.length > 0) {
    html += `
      <div>
        <h3 style="color:${isCompileFail ? '#f87171' : '#fbbf24'}; font-size:12px; font-weight:700; margin-bottom:8px;">
          ${isCompileFail ? '❌ COMPILER ERRORS' : '⚠️ LINT WARNINGS'} (${compile.errors.length} Errors, ${compile.warnings.length} Warnings)
        </h3>
        <table class="data-table">
          <tr><th style="width:80px;">Severity</th><th>Issue Description</th></tr>
    `;
    compile.errors.forEach(err => {
      html += `<tr><td><span class="badge badge-fail">ERROR</span></td><td style="color:#fca5a5;">${escapeHtml(err)}</td></tr>`;
    });
    compile.warnings.forEach(warn => {
      html += `<tr><td><span class="badge badge-warn">WARN</span></td><td style="color:#fef08a;">${escapeHtml(warn)}</td></tr>`;
    });
    html += `</table></div>`;
  }

  html += `</div>`;
  container.innerHTML = html;
}

// ----------------------------------------------------
// SCREEN 2: HARDWARE INFERENCE & ESTIMATED CELLS
// ----------------------------------------------------
function renderHardwareScreen(d) {
  const container = document.getElementById('hardware-content');
  if (!container) return;

  if (d.compile?.status === 'FAIL') {
    container.innerHTML = `
      <div style="padding:40px 20px; text-align:center; color:#94a3b8;">
        <div style="font-size:28px; margin-bottom:12px;">✕</div>
        <h3 style="color:#f87171; margin-bottom:6px;">Hardware Inference Halted</h3>
        <p style="font-size:12px;">RTL has syntax or critical lint errors. Fix errors in the RTL editor and re-run.</p>
      </div>
    `;
    return;
  }

  const inf = d.rtlStructure || d.inference || {};
  const synth = d.synthesis || d.synthesisEstimate || {};

  let html = `
    <!-- Summary Metric Cards -->
    <div class="dashboard-grid" style="padding:0; margin-bottom:20px;">
      <div class="metric-card">
        <div class="metric-card-title">Register Bits (Flip-Flops)</div>
        <div class="metric-val-large">${inf.register_bits || 0} bits</div>
        <div style="font-size:11px; color:#94a3b8; margin-top:4px;">Clock Domains: ${(inf.clock_domains || []).length || 1}</div>
      </div>
      <div class="metric-card">
        <div class="metric-card-title">Arithmetic Logic</div>
        <div class="metric-val-large">${(inf.adders || 0) + (inf.multipliers || 0)} units</div>
        <div style="font-size:11px; color:#38bdf8; margin-top:4px;">${inf.adders || 0} Adders/Subs, ${inf.multipliers || 0} Multipliers</div>
      </div>
      <div class="metric-card">
        <div class="metric-card-title">Steering & Comparators</div>
        <div class="metric-val-large">${(inf.multiplexers || 0) + (inf.comparators || 0)} blocks</div>
        <div style="font-size:11px; color:#a7f3d0; margin-top:4px;">${inf.multiplexers || 0} Muxes, ${inf.comparators || 0} Comparators</div>
      </div>
      <div class="metric-card">
        <div class="metric-card-title">Estimated Standard Cells</div>
        <div class="metric-val-large">${synth.total_cells || 0} cells</div>
        <div style="font-size:11px; color:#f59e0b; margin-top:4px;">Cell Area: ${synth.estimated_cell_area_um2 ? Math.round(synth.estimated_cell_area_um2) : 0} µm²</div>
      </div>
    </div>

    <!-- Estimated Standard Cell Mapping Table -->
    <div style="margin-bottom:24px;">
      <h3 style="color:#38bdf8; font-size:12px; font-weight:700; margin-bottom:8px;">ESTIMATED STANDARD CELL BREAKDOWN (${synth.technology_node || 'Generic CMOS'})</h3>
      <table class="data-table">
        <tr><th>Cell Type</th><th>Inferred Function</th><th>Count</th><th>Total Area (µm²)</th></tr>
  `;

  const counts = synth.cell_counts || {};
  if (Object.keys(counts).length > 0) {
    for (const [cellType, cnt] of Object.entries(counts)) {
      let func = 'Combinational Logic';
      if (cellType.startsWith('DFF')) func = 'Edge-Triggered Flip-Flop';
      else if (cellType.startsWith('NAND') || cellType.startsWith('NOR') || cellType.startsWith('AND') || cellType.startsWith('OR')) func = 'Elementary Logic Gate';
      else if (cellType.startsWith('MUX')) func = 'Data Multiplexer';
      else if (cellType.startsWith('FA') || cellType.startsWith('HA')) func = 'Full/Half Adder';

      html += `
        <tr>
          <td><code>${cellType}</code></td>
          <td>${func}</td>
          <td><strong>${cnt}</strong></td>
          <td>${((synth.instances || []).filter(i => i.cell_type === cellType).reduce((a, b) => a + b.area_um2, 0)).toFixed(1)} µm²</td>
        </tr>
      `;
    }
  } else {
    html += `<tr><td colspan="4" style="color:#94a3b8; text-align:center;">No cell mapping data available.</td></tr>`;
  }

  html += `
      </table>
      <div style="font-size:11px; color:#94a3b8; margin-top:6px;">
        Cell count reconciliation: ${synth.sequential_elements || 0} Sequential + ${synth.combinational_cells || 0} Combinational Logic + ${(synth.clock_cells !== undefined) ? synth.clock_cells : Math.max(0, (synth.total_cells || 0) - (synth.sequential_elements || 0) - (synth.combinational_cells || 0))} Clock Buffers = <strong style="color:#e2e8f0;">${synth.total_cells || 0} Total Cells</strong>
      </div>
    </div>

    <!-- Inferred Block Diagram / Schematic View -->
    <div>
      <h3 style="color:#38bdf8; font-size:12px; font-weight:700; margin-bottom:8px;">INFERRED HARDWARE SCHEMATIC</h3>
      <div id="schematic-canvas-wrapper" style="width:100%; height:320px; background:#070a0f; border:1px solid var(--border-color); border-radius:6px; position:relative;"></div>
    </div>
  `;

  container.innerHTML = html;

  // Load schematic data
  if (schem && inf.schematic) {
    setTimeout(() => {
      schem.container = document.getElementById('schematic-canvas-wrapper');
      schem.resize();
      schem.loadData(inf);
    }, 50);
  }
}

// ----------------------------------------------------
// SCREEN 3: PHYSICAL IMPLEMENTATION
// ----------------------------------------------------
function renderPhysicalScreen(d) {
  const isCompileFail = d.compile && d.compile.status === 'FAIL';

  if (isCompileFail || !d.floorplan || !d.floorplan.die) {
    document.getElementById('phys-area-val').textContent = '--';
    document.getElementById('phys-dim-val').textContent = '--';
    document.getElementById('phys-fmax-val').textContent = '--';
    document.getElementById('phys-slack-val').textContent = '--';
    document.getElementById('phys-cong-val').textContent = '--';
    document.getElementById('phys-clock-val').textContent = '--';
    document.getElementById('phys-critical-path-content').innerHTML = `
      <div style="color:#ef4444; font-size:11px; padding:8px 0;">Physical estimation blocked: RTL failed compilation.</div>
    `;
    if (v2d) v2d.loadData(d);
    if (v3d) v3d.loadData(d);
    return;
  }

  const fp = d.floorplan;
  const timing = d.timing || {};
  const cong = d.routing || {};
  const cts = d.cts || {};

  // Sidebar Metrics
  document.getElementById('phys-area-val').textContent = `${Math.round(fp.core.area_um2)} µm²`;
  document.getElementById('phys-dim-val').textContent = `${Math.round(fp.core.width_um)} × ${Math.round(fp.core.height_um)} µm (${fp.core.utilization_pct}%)`;
  document.getElementById('phys-fmax-val').textContent = `≈ ${timing.estimated_fmax_mhz || '--'} MHz`;

  const slackEl = document.getElementById('phys-slack-val');
  if (timing.worst_setup_slack_ns !== undefined) {
    slackEl.textContent = `${timing.worst_setup_slack_ns >= 0 ? '+' : ''}${timing.worst_setup_slack_ns} ns`;
    slackEl.style.color = timing.worst_setup_slack_ns >= 0 ? '#10b981' : '#ef4444';
  } else {
    slackEl.textContent = '--';
  }

  document.getElementById('phys-cong-val').textContent = `${cong.max_tile_congestion_pct || cong.peak_congestion_pct || 0}% (${cong.estimated_drc_risk || cong.drc_risk || 'LOW'})`;
  document.getElementById('phys-clock-val').textContent = `${cts.estimated_max_slew_ps || 80} ps / ${cts.estimated_clock_skew_ps || 25} ps`;

  // Render Critical Path Chain in Sidebar
  const cpContainer = document.getElementById('phys-critical-path-content');
  if (cpContainer && timing.stages && timing.stages.length > 0) {
    let chainHtml = `<div class="critical-path-chain">`;
    timing.stages.forEach((st, idx) => {
      chainHtml += `
        <div class="critical-stage-node">
          <div>
            <span style="font-weight:bold; color:#38bdf8;">${st.instance_name}</span>
            <span style="font-size:10px; color:#94a3b8;"> (${st.cell_type})</span>
          </div>
          <div style="font-family:var(--font-mono); color:#fde68a;">+${st.delay_ns} ns</div>
        </div>
      `;
      if (idx < timing.stages.length - 1) {
        chainHtml += `<div class="critical-stage-arrow">↓</div>`;
      }
    });
    chainHtml += `
      <div style="margin-top:8px; padding-top:6px; border-top:1px solid #1e293b; display:flex; justify-content:space-between; font-size:10px;">
        <span style="color:#94a3b8;">Total Delay:</span>
        <strong style="color:#38bdf8;">${timing.critical_path_delay_ns} ns</strong>
      </div>
    </div>`;
    cpContainer.innerHTML = chainHtml;
  } else {
    cpContainer.innerHTML = `<div style="color:#64748b; font-size:11px; padding:8px 0;">No sequential timing path inferred.</div>`;
  }

  // Load Canvas Visualizers
  if (v2d) v2d.loadData(d);
  if (v3d) v3d.loadData(d);
}

// ----------------------------------------------------
// SCREEN 4: REPORT PREVIEW
// ----------------------------------------------------
function renderReportScreen(d) {
  const frame = document.getElementById('report-frame');
  if (frame && d.report_html) {
    frame.srcdoc = d.report_html;
  }
}

// Toggle Physical View between 2D and 3D
function togglePhysicalMode() {
  is3DMode = !is3DMode;
  const canvas2dWrapper = document.getElementById('canvas2d-wrapper');
  const canvas3dWrapper = document.getElementById('canvas3d-wrapper');

  if (is3DMode) {
    canvas2dWrapper.style.display = 'none';
    canvas3dWrapper.style.display = 'block';
    if (v3d) {
      setTimeout(() => {
        v3d.onWindowResize();
        if (currentPipelineData) v3d.loadData(currentPipelineData);
      }, 50);
    }
  } else {
    canvas3dWrapper.style.display = 'none';
    canvas2dWrapper.style.display = 'block';
    if (v2d) setTimeout(() => v2d.resize(), 50);
  }
}

// Contextual WHY Modal Handler
function showContextualWhy(topic) {
  if (!currentPipelineData) return;
  const explanations = currentPipelineData.explanations || currentPipelineData.why || {};
  const exp = explanations[topic];

  const modal = document.getElementById('why-modal');
  const titleEl = document.getElementById('why-modal-title');
  const bodyEl = document.getElementById('why-modal-body');

  const topicTitles = {
    area: 'WHY THIS ESTIMATED CORE AREA?',
    floorplan: 'WHY THIS FLOORPLAN & UTILIZATION?',
    timing: 'WHY THIS ESTIMATED FMAX & SLACK?',
    routing: 'WHY THIS CONGESTION ESTIMATE?',
    cts: 'WHY THIS CLOCK TREE TOPOLOGY?'
  };

  titleEl.textContent = topicTitles[topic] || 'WHY? PHYSICAL EXPLANATION';

  if (exp) {
    bodyEl.innerHTML = `
      <div class="why-card-section">
        <div class="why-card-label">Result:</div>
        <div class="why-card-text" style="font-weight:bold; color:#f1f5f9;">${escapeHtml(exp.result)}</div>
      </div>
      <div class="why-card-section">
        <div class="why-card-label">Inferred Evidence:</div>
        <div class="why-card-text">${escapeHtml(exp.evidence)}</div>
      </div>
      <div class="why-card-section">
        <div class="why-card-label">Silicon Physical Reason:</div>
        <div class="why-card-text">${escapeHtml(exp.reason)}</div>
      </div>
      <div class="why-card-section">
        <div class="why-card-label">RTL Source Trace:</div>
        <div class="why-card-source">${escapeHtml(exp.source_rtl)}</div>
      </div>
      <div class="why-card-section" style="margin-bottom:0;">
        <div class="why-card-label">Physical Consequence:</div>
        <div class="why-card-text" style="color:#a7f3d0;">${escapeHtml(exp.consequence)}</div>
      </div>
    `;
  } else {
    bodyEl.innerHTML = `<div style="color:#94a3b8;">Explanation data is not available for this topic.</div>`;
  }

  modal.style.display = 'flex';
}

function closeContextualWhy() {
  const modal = document.getElementById('why-modal');
  if (modal) modal.style.display = 'none';
}

// Download Standalone Report
function downloadReport() {
  if (!currentPipelineData || !currentPipelineData.report_html) {
    alert('Please run analysis first to generate the report.');
    return;
  }
  const blob = new Blob([currentPipelineData.report_html], { type: 'text/html' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${currentPipelineData.top_module || 'design'}_pre_physical_design_report.html`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
