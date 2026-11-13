// The Exam Desk's page. Talks to the desk server over WebSockets only: a control socket (sign-in,
// the exam's state once a second, actions) and one socket per terminal (raw bytes both ways).
// Nothing here is a security boundary: the server checks the code, the secret, the origin and
// the user, and it is the server that makes the shells read-only when time is up. The page builds
// every element with the DOM and sets text with textContent, so task text can't inject markup.
'use strict';
(() => {
  const KEY = 'autorelabel-desk';
  const $ = (id) => document.getElementById(id);
  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
  const wsUrl = (path) => `ws://${location.host}${path}`;
  // state arrives every second; a part of the page is rebuilt only when what it shows has changed,
  // so a button is never replaced between a press and its release
  const unchanged = (node, value) => { const sig = JSON.stringify(value); if (node.dataset.sig === sig) return true; node.dataset.sig = sig; return false; };
  const fmt = (s) => { s = Math.max(0, Math.round(s)); const h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), x = s % 60; return `${h}:${String(m).padStart(2, '0')}:${String(x).padStart(2, '0')}`; };
  const LOCKED = new Set(['locked', 'grading', 'grading_interrupted', 'graded']);
  const WORDS = {running: ['✓', 'running', 'ok'], 'shut off': ['✗', 'off', 'bad'], paused: ['‖', 'paused', 'warn'],
                 'in shutdown': ['↻', 'rebooting', 'warn'], crashed: ['✗', 'crashed', 'bad'], unknown: ['?', 'unknown', '']};

  let secret = sessionStorage.getItem(KEY) || '';
  let control = null, state = {}, currentTask = 1, currentNode = '', split = innerWidth >= 1600, retry = 0;
  const tiles = new Map();                     // terminal id -> tile
  let busy = '';

  // --- sign-in and the control socket -----------------------------------------------------------
  function connect() {
    control = new WebSocket(wsUrl('/ws/control'));
    control.onopen = () => { retry = 0; if (secret) control.send(JSON.stringify({secret})); else showLogin(''); };
    control.onmessage = (event) => onControl(JSON.parse(event.data));
    control.onclose = (event) => {
      control = null;
      if (event.code === 4401) { secret = ''; sessionStorage.removeItem(KEY); return; }
      if (!$('app').hidden) setBar('conn', 'bad', 'Disconnected', 'Reconnecting to the Exam Desk. Your shells keep running.');
      setTimeout(connect, Math.min(5000, 500 * 2 ** retry++));
    };
  }
  function showLogin(message) {
    $('app').hidden = true; document.body.classList.remove('in-app'); $('login').hidden = false;
    $('login-msg').textContent = message; $('code').focus();
  }
  $('login-form').addEventListener('submit', (event) => {
    event.preventDefault();
    const code = $('code').value.trim();
    const once = new WebSocket(wsUrl('/ws/control'));
    once.onopen = () => once.send(JSON.stringify({code}));
    once.onmessage = (e) => {
      const reply = JSON.parse(e.data);
      if (reply.secret) { secret = reply.secret; sessionStorage.setItem(KEY, secret); once.close(); if (!control) connect(); else control.send(JSON.stringify({secret})); }
      else if (reply.error === 'wrong') showLogin(reply.left > 0 ? `That is not the code. ${reply.left} ${reply.left === 1 ? 'try' : 'tries'} left.` : 'That was the last try. Stop the Exam Desk with Ctrl+C and start it again for a new code.');
      else if (reply.error === 'used') showLogin('This code has no tries left. Stop the Exam Desk with Ctrl+C and start it again for a new code.');
    };
  });
  function onControl(msg) {
    if (msg.ok) { $('login').hidden = true; $('app').hidden = false; document.body.classList.add('in-app'); clearBar('conn'); return; }
    if (msg.state) { state = msg.state; render(); }
    if (msg.opened) { currentNode = msg.opened.node; attachTile(msg.opened, true); }
    if (msg.error === 'login') { showLogin('Sign in again: the Exam Desk was started again since this tab last used it.'); return; }
    if (msg.error) toast(msg.error);
    if (msg.busy !== undefined) { busy = msg.busy; renderBars(); }
    if (msg.codeServer) { if (msg.codeServer.startsWith('http')) window.open(msg.codeServer, '_blank', 'noopener'); else toast(`VS Code is ${msg.codeServer}`); }
  }
  const send = (action) => { if (control && control.readyState === 1) control.send(JSON.stringify(action)); };

  // --- rendering ----------------------------------------------------------------------------------
  function render() {
    if (!state.open) { renderClosed(); return; }
    const exam = state.exam.toUpperCase();
    $('exam-name').textContent = `${exam} ${state.mode === 'exam' ? 'exam' : 'practice'}`;
    renderClock(); renderLab(); renderBars(); renderTasks(); renderNodes(); renderStage();
    const running = state.state === 'in_progress';
    for (const id of ['new-shell', 'new-console', 'reset-node', 'mark-done', 'mark-flag']) $(id).disabled = !running;
    $('end-exam').disabled = !['in_progress', 'interrupted'].includes(state.state);
    $('end-exam').textContent = LOCKED.has(state.state) ? 'Exam ended' : 'End exam';
    $('vscode').hidden = state.exam !== 'rhce';
  }
  function renderClosed() {
    $('exam-name').textContent = 'No exam open'; $('lab-state').textContent = ''; $('clock').textContent = '-:--:--';
    $('task-grid').replaceChildren(); $('node-tabs').replaceChildren();
    const note = el('div', 'empty-note'); note.append(el('h2', '', 'No exam is open.'), el('p', '', 'Start an exam or a practice session in autorelabel (./autorelabel). This page picks it up by itself.'));
    $('task').replaceChildren(note); $('stage').replaceChildren(stageNote('Nothing to connect to yet.', 'The terminals appear here once an exam is running.'));
  }
  function renderClock() {
    const clock = $('clock').parentElement;
    if (!state.timed) { $('clock').textContent = 'untimed'; $('clock-note').textContent = ''; clock.className = 'clock'; return; }
    $('clock').textContent = fmt(state.remaining);
    $('clock-note').textContent = state.state === 'ready' ? 'starts when you start it' : `left of ${fmt(state.duration)}`;
    clock.className = 'clock' + (state.remaining <= 300 ? ' bad' : state.remaining <= 900 ? ' warn' : '');
  }
  function renderLab() {
    const chip = $('lab-state');
    const words = {ready: ['✓', 'lab ready', 'ok'], in_progress: ['✓', 'lab ready', 'ok'], locked: ['■', 'time is up', 'bad'],
                   grading: ['…', 'grading', 'warn'], grading_interrupted: ['!', 'grading interrupted', 'bad'], graded: ['✓', 'graded', 'ok'],
                   provisioning: ['…', 'preparing the lab', 'warn'], new: ['…', 'preparing the lab', 'warn'], interrupted: ['!', 'interrupted', 'bad']};
    let [mark, word, tone] = words[state.state] || ['?', state.state, ''];
    const rebooting = (state.nodes || []).filter((n) => n.power !== 'running' && n.power !== 'unknown').map((n) => n.name);
    if (state.state === 'in_progress' && rebooting.length) [mark, word, tone] = ['↻', `${rebooting.join(', ')} not running`, 'warn'];
    if (state.state === 'in_progress' && state.unreachable.length) [mark, word, tone] = ['✗', `${state.unreachable.join(', ')} unreachable`, 'bad'];
    chip.textContent = `${mark} ${word}`; chip.className = `chip ${tone}`;
  }
  const bars = new Map();
  function setBar(key, tone, label, text, actions = []) { bars.set(key, {tone, label, text, actions}); drawBars(); }
  function clearBar(key) { if (bars.delete(key)) drawBars(); }
  function renderBars() {
    for (const key of ['time', 'unreach', 'busy', 'ro']) bars.delete(key);
    const left = state.remaining;
    if (state.timed && state.state === 'in_progress' && left <= 300) bars.set('time', {tone: 'bad', label: '5 minutes', text: 'At 0:00:00 the terminals become read-only and grading starts. Save your work now.'});
    else if (state.timed && state.state === 'in_progress' && left <= 900) bars.set('time', {tone: 'warn', label: '15 minutes', text: 'Finish up, and check that your work survives a reboot: enabled services, persistent settings, fstab.'});
    if (LOCKED.has(state.state) && state.state !== 'graded') bars.set('ro', {tone: 'bad', label: 'Time is up', text: 'The terminals are read-only. You can still read and scroll them. Grading reboots every node first.'});
    for (const node of state.unreachable || []) bars.set('unreach', {tone: 'bad', label: `${node} unreachable`, text: `The grader can no longer reach ${node}. Undo changes to its management interface, the vagrant account, sshd or sudo, or its tasks score 0.`,
      actions: [['Open the console', () => { currentNode = node; send({do: 'console', node}); }]]});
    if (busy) bars.set('busy', {tone: 'info', label: 'Working', text: busy});
    drawBars();
  }
  function drawBars() {
    const box = $('bars');
    if (unchanged(box, [...bars.values()].map(({tone, label, text}) => [tone, label, text]))) return;
    box.replaceChildren();
    for (const {tone, label, text, actions = []} of bars.values()) {
      const bar = el('div', `bar ${tone}`); bar.append(el('b', '', label), el('span', '', text));
      for (const [name, fn] of actions) { const b = el('button', 'btn', name); b.type = 'button'; b.onclick = fn; bar.append(b); }
      box.append(bar);
    }
  }
  function renderTasks() {
    // before the clock starts the tasks stay hidden, as on the exam: reading time is exam time
    const grid = $('task-grid'), tasks = state.state === 'ready' ? [] : state.tasks || [];
    if (!tasks.length) { grid.replaceChildren(); grid.dataset.sig = ''; if (!unchanged($('task'), ['empty', state.state, state.taskCount])) $('task').replaceChildren(emptyTasks()); return; }
    if (!tasks.some((t) => t.number === currentTask)) currentTask = tasks[0].number;
    if (!unchanged(grid, [tasks.map((t) => t.number), state.marks, currentTask])) grid.replaceChildren(...tasks.map((t) => {
      const mark = state.marks[String(t.number)] || '';
      const b = el('button', `task-num ${mark}`); b.type = 'button'; b.setAttribute('role', 'tab');
      b.setAttribute('aria-selected', String(t.number === currentTask));
      b.setAttribute('aria-label', `Task ${t.number}${mark === 'done' ? ', marked done' : mark === 'flag' ? ', marked for review' : ''}`);
      b.append(el('span', '', String(t.number)), el('small', '', mark === 'done' ? '✓' : mark === 'flag' ? '⚑' : ''));
      b.onclick = () => { currentTask = t.number; renderTasks(); };
      return b;
    }));
    const t = tasks.find((x) => x.number === currentTask);
    if (!t) return;
    const mark = state.marks[String(t.number)] || '';
    const art = $('task');
    if (unchanged(art, ['task', t.number, t.prompt])) { setMarkButtons(mark); return; }
    const scroll = art.dataset.task === String(t.number) ? art.scrollTop : 0;
    const meta = [`Task ${t.number} of ${tasks.length}`, `${t.points} points`, `on ${t.node}`, t.difficulty, t.consoleOnly ? 'console' : ''].filter(Boolean).join(' · ');
    art.replaceChildren(el('p', 'meta', meta), el('h2', '', t.title), ...markdown(t.prompt));
    art.dataset.task = String(t.number); art.scrollTop = scroll;
    setMarkButtons(mark);
  }
  function setMarkButtons(mark) {
    $('mark-done').textContent = mark === 'done' ? '✓ Done (undo)' : 'Mark done';
    $('mark-flag').textContent = mark === 'flag' ? '⚑ For review (undo)' : 'Mark for review';
  }
  function emptyTasks() {
    const note = el('div', 'empty-note');
    if (state.state === 'ready') {
      note.append(el('h2', '', 'Ready when you are.'), el('p', '', `The lab is prepared. Your ${state.taskCount || 20} tasks appear when you start the exam, here or in autorelabel, and the clock starts with them.`));
      const go = el('button', 'btn primary', 'Start the exam'); go.type = 'button'; go.onclick = () => send({do: 'begin'}); note.append(go);
    } else note.append(el('h2', '', 'Your tasks appear here when the lab is ready.'));
    return note;
  }
  // a small Markdown subset for task prompts, built with DOM nodes only: paragraphs, lists, code
  function markdown(text) {
    const out = []; const lines = String(text || '').replace(/\r/g, '').split('\n');
    let para = [], list = null, code = null;
    const inline = (s, parent) => {
      for (const part of s.split(/(`[^`]+`|\*\*[^*]+\*\*)/)) {
        if (!part) continue;
        if (part.startsWith('`') && part.endsWith('`') && part.length > 1) parent.append(el('code', '', part.slice(1, -1)));
        else if (part.startsWith('**') && part.endsWith('**')) parent.append(el('strong', '', part.slice(2, -2)));
        else parent.append(document.createTextNode(part));
      }
      return parent;
    };
    const flush = () => { if (para.length) { out.push(inline(para.join(' '), el('p'))); para = []; } if (list) { out.push(list); list = null; } };
    for (const line of lines) {
      if (code !== null) { if (line.trim().startsWith('```')) { out.push(el('pre', '', code.join('\n'))); code = null; } else code.push(line); continue; }
      if (line.trim().startsWith('```')) { flush(); code = []; continue; }
      const item = line.match(/^\s*(?:[-*]|\d+\.)\s+(.*)$/);
      if (item) { if (para.length) { out.push(inline(para.join(' '), el('p'))); para = []; } list = list || el(/^\s*\d/.test(line) ? 'ol' : 'ul'); list.append(inline(item[1], el('li'))); continue; }
      if (!line.trim()) { flush(); continue; }
      if (list) { out.push(list); list = null; }
      para.push(line.trim());
    }
    if (code !== null) out.push(el('pre', '', code.join('\n')));
    flush();
    return out;
  }

  function renderNodes() {
    const nodes = state.nodes || [];
    if (!nodes.some((n) => n.name === currentNode)) currentNode = nodes.length ? nodes[0].name : '';
    if (!unchanged($('node-tabs'), [nodes.map((n) => [n.name, n.power]), state.unreachable, currentNode])) $('node-tabs').replaceChildren(...nodes.map((n) => {
      const [mark, word, tone] = state.unreachable.includes(n.name) ? ['✗', 'unreachable', 'bad'] : WORDS[n.power] || ['?', n.power, ''];
      const b = el('button', 'node-tab'); b.type = 'button'; b.setAttribute('role', 'tab'); b.setAttribute('aria-selected', String(n.name === currentNode));
      const small = el('small'); small.append(el('span', tone, mark), document.createTextNode(` ${word}`));
      b.append(el('span', '', n.name), small);
      b.onclick = () => { currentNode = n.name; renderNodes(); renderStage(); };
      return b;
    }));
    $('reset-node').textContent = currentNode ? `Reset ${currentNode}` : 'Reset node';
  }

  // --- terminals ----------------------------------------------------------------------------------
  const theme = {background: '#0E0E10', foreground: '#ECE8E1', cursor: '#FFD15C', cursorAccent: '#0E0E10',
                 selectionBackground: 'rgba(255, 209, 92, .32)', black: '#1E1E21', brightBlack: '#5E5A54',
                 red: '#F0566B', green: '#4EBF71', yellow: '#FFD15C', blue: '#5AA9F0', magenta: '#D58CF0', cyan: '#5BC8C0', white: '#ECE8E1'};
  function stageNote(title, text) { const n = el('div', 'stage-note'); n.append(el('h2', '', title), el('p', '', text)); return n; }
  function renderStage() {
    const stage = $('stage');
    if (state.state === 'graded' && state.result) {
      if (unchanged(stage, ['graded', state.result.score])) return;
      const r = state.result, n = el('div', 'stage-note');
      n.append(el('h2', '', `${Math.round(r.score)} of ${r.total}: ${r.passed ? '✓ Pass' : '✗ Fail'}`),
               el('p', '', `The pass mark is ${r.passMark}. See every check of this attempt in the results dashboard (./autorelabel dashboard, or o on Progress and history), or in autorelabel itself.`));
      stage.replaceChildren(n); return;
    }
    if (state.state === 'grading') { if (unchanged(stage, ['grading'])) return; stage.replaceChildren(stageNote('Grading.', 'Every node reboots first, then each task is checked. You can close this window: autorelabel finishes on its own.')); return; }
    const mine = (state.terminals || []).filter((t) => t.node === currentNode);     // an ended shell stays until closed
    for (const t of state.terminals || []) if (!tiles.has(t.id)) attachTile(t, false);
    for (const [id, tile] of tiles) if (!(state.terminals || []).some((t) => t.id === id)) { tile.dispose(); tiles.delete(id); }
    // the selected node's newest terminal, and with Split the newest other one, of any node, beside it
    const first = mine[mine.length - 1];
    const other = split && first ? [...(state.terminals || [])].reverse().find((t) => t.id !== first.id) : null;
    const shown = [first, other].filter(Boolean).map((t) => tiles.get(t.id)).filter(Boolean);
    stage.classList.toggle('two', shown.length === 2);
    $('split').setAttribute('aria-pressed', String(split));
    if (!shown.length) {
      const running = state.state === 'in_progress';
      if (unchanged(stage, ['note', currentNode, running])) return;
      stage.replaceChildren(stageNote(currentNode ? `No shell on ${currentNode} yet.` : 'No node.', running ? 'Open a new shell (SSH) or the serial console from the buttons above.' : 'Shells open once the exam is running.'));
      return;
    }
    stage.dataset.sig = '';
    if (stage.children.length !== shown.length || shown.some((t, i) => stage.children[i] !== t.root)) stage.replaceChildren(...shown.map((t) => t.root));
    for (const t of shown) { t.update(); t.fit(); }
  }
  function attachTile(info, focus) {
    if (tiles.has(info.id)) { if (focus) { renderNodes(); renderStage(); tiles.get(info.id).term.focus(); } return; }
    const root = el('section', 'tile'); root.setAttribute('aria-label', `${info.node} ${info.title}`);
    const head = el('div', 'tile-head'), body = el('div', 'tile-body'), strip = el('div', 'tile-strip');
    const what = el('span', 'what', `${info.node} · ${info.title}`), how = el('span', 'how'), st = el('span', 'state');
    const close = el('button', 'x', '✕'); close.type = 'button'; close.setAttribute('aria-label', `Close ${info.title} on ${info.node}`);
    head.append(what, how, st, close); strip.hidden = true; root.append(head, body, strip);
    const term = new Terminal({fontFamily: 'JetBrains, ui-monospace, monospace', fontSize: 14, lineHeight: 1.15, cursorBlink: true,
                               scrollback: 5000, theme, allowProposedApi: false, macOptionIsMeta: true});
    const fit = new FitAddon.FitAddon(); term.loadAddon(fit);
    let ws = null, opened = false, size = '', acked = 0, readOnly = false, ended = !!info.exited;
    const node = (state.nodes || []).find((n) => n.name === info.node);
    how.textContent = info.kind === 'console' ? `serial console${node ? ` · ${node.login}` : ''}` : `ssh ${node ? `${node.user}@${node.fqdn}` : ''}`;
    const tile = {root, term, id: info.id,
      fit() { if (!opened && root.isConnected) { term.open(body); opened = true; connectTerm(); } if (!opened) return; try { fit.fit(); } catch { return; } const s = `${term.cols}x${term.rows}`; if (s !== size && ws && ws.readyState === 1) { size = s; ws.send(JSON.stringify({resize: [term.cols, term.rows]})); } },
      update() {
        const locked = LOCKED.has(state.state), n = (state.nodes || []).find((x) => x.name === info.node), down = n && n.power !== 'running' && n.power !== 'unknown';
        const t = (state.terminals || []).find((x) => x.id === info.id); if (t && t.exited) ended = true;
        st.textContent = ended ? '■ ended' : locked || readOnly ? '■ read-only' : down ? '↻ waiting' : '● connected';
        root.classList.toggle('dim', (!!down && !locked) || ended);
        strip.hidden = !(down || locked || readOnly || ended);
        strip.textContent = ended ? 'This shell has ended. Close it, or open a new one from the buttons above.'
          : locked || readOnly ? 'Read-only: time is up. You can read and scroll; typing goes nowhere.'
          : down ? `${info.node} is not running. This shell is kept; if the connection dropped, open a new shell when ${info.node} is back.` : '';
      },
      dispose() { if (ws) ws.close(); term.dispose(); root.remove(); },
    };
    const connectTerm = () => {
      ws = new WebSocket(wsUrl(`/ws/term/${encodeURIComponent(info.id)}`)); ws.binaryType = 'arraybuffer'; size = '';
      ws.onopen = () => ws.send(JSON.stringify({secret}));
      ws.onmessage = (event) => {
        if (typeof event.data === 'string') { const m = JSON.parse(event.data); if (m.ok) tile.fit(); if (m.readOnly) { readOnly = true; tile.update(); } if (m.ended) { ended = true; tile.update(); } return; }
        const bytes = new Uint8Array(event.data);
        term.write(bytes, () => { acked += bytes.length; if (acked >= 64 * 1024 && ws.readyState === 1) { ws.send(JSON.stringify({ack: acked})); acked = 0; } });
        if (acked && ws.readyState === 1) setTimeout(() => { if (acked && ws.readyState === 1) { ws.send(JSON.stringify({ack: acked})); acked = 0; } }, 50);
      };
      ws.onclose = (event) => { if (tiles.get(info.id) === tile && event.code !== 1000 && event.code !== 4401) setTimeout(connectTerm, 1000); };
    };
    const enc = new TextEncoder();
    term.onData((data) => { if (ws && ws.readyState === 1) ws.send(enc.encode(data)); });
    term.onBinary((data) => { if (ws && ws.readyState === 1) ws.send(Uint8Array.from(data, (c) => c.charCodeAt(0) & 255)); });
    term.textarea && term.textarea.addEventListener('focus', () => root.classList.add('focus'));
    root.addEventListener('focusout', () => root.classList.remove('focus'));
    close.onclick = () => send({do: 'close', terminal: info.id});
    new ResizeObserver(() => tile.fit()).observe(body);
    tiles.set(info.id, tile);              // its socket opens when the tile is first on screen (fit)
    if (focus) { renderNodes(); renderStage(); setTimeout(() => term.focus(), 50); }
    return tile;
  }

  // --- actions ----------------------------------------------------------------------------------
  const mark = (kind) => { const now = state.marks[String(currentTask)] || ''; send({do: 'mark', task: currentTask, mark: now === kind ? '' : kind}); };
  $('mark-done').onclick = () => mark('done');
  $('mark-flag').onclick = () => mark('flag');
  const step = (d) => { const nums = (state.tasks || []).map((t) => t.number), i = nums.indexOf(currentTask); if (nums.length) { currentTask = nums[(i + d + nums.length) % nums.length]; renderTasks(); $('task').focus(); } };
  $('prev').onclick = () => step(-1); $('next').onclick = () => step(1);
  $('new-shell').onclick = () => currentNode && send({do: 'shell', node: currentNode});
  $('new-console').onclick = () => currentNode && send({do: 'console', node: currentNode});
  $('split').onclick = () => { split = !split; renderStage(); };
  $('vscode').onclick = () => send({do: 'code'});
  function confirmThen(title, body, loss, ok, fn) {
    $('confirm-title').textContent = title; $('confirm-body').textContent = body; $('confirm-loss').textContent = loss; $('confirm-ok').textContent = ok;
    const dialog = $('confirm'); dialog.returnValue = ''; dialog.showModal();
    dialog.addEventListener('close', () => { if (dialog.returnValue === 'ok') fn(); }, {once: true});
  }
  $('reset-node').onclick = () => currentNode && confirmThen(`Reset ${currentNode}?`, `${currentNode} goes back to how it was when the exam started, and restarts. Its shells disconnect.`,
    `Everything you changed on ${currentNode} is lost.`, `Reset ${currentNode}`, () => send({do: 'reset', node: currentNode}));
  $('end-exam').onclick = () => confirmThen('End the exam now?', 'The terminals become read-only, every node reboots, and your work is graded.',
    'You can’t change anything after this.', 'End and grade', () => send({do: 'end'}));
  $('fullscreen').onclick = async () => {
    try {
      await document.documentElement.requestFullscreen();
      if (navigator.keyboard && navigator.keyboard.lock) { await navigator.keyboard.lock(['KeyW', 'KeyT', 'KeyN', 'Escape']); toast('Full screen: Ctrl+W, Ctrl+T and Ctrl+N now go to your shell. Hold Esc to leave full screen.'); }
      else toast('Full screen. This browser keeps Ctrl+W for itself (only Chromium browsers hand it over): it closes the tab, but your shells keep running. Open the address again to get back.');
    } catch { toast('This browser did not allow full screen.'); }
  };
  addEventListener('beforeunload', (event) => { if (state.state === 'in_progress') event.preventDefault(); });
  let toastTimer = 0;
  function toast(text) { const t = $('toast'); t.textContent = text; t.hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => { t.hidden = true; }, 7000); }

  connect();
})();
