/* Local reading preferences and progress marks are navigation conveniences, never learning evidence. */
(() => {
  'use strict';
  const one = (selector, root = document) => root.querySelector(selector);
  const all = (selector, root = document) => [...root.querySelectorAll(selector)];
  const main = one('#main');
  const data = JSON.parse(one('#rf-page-data').textContent);
  const root = new URL(data.root, location.href);
  const key = `reformation-ui:v1:${root.pathname}`;
  const pages = new Map(data.pages.map(page => [page.path, page]));
  const modules = new Map(data.modules.map(module => [module.id, module]));
  const modalSupported = typeof HTMLDialogElement !== 'undefined' && typeof HTMLDialogElement.prototype.showModal === 'function';
  const plainClick = event => event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey;
  const decode = hash => { try { return decodeURIComponent(hash.slice(1)); } catch { return null; } };
  const urlFor = (path, anchor = '') => new URL(path + (anchor ? `#${encodeURIComponent(anchor)}` : ''), root).href;
  const blankState = () => ({version: 2, theme: 'system', view: 'guided', shell: null, last: null, positions: {}, done: {}});
  const targets = page => pages.has(page) ? data.resume[page] || [] : [];
  const stepIds = page => pages.get(page)?.steps || [];
  const SHELLS = ['bash', 'powershell'];
  let state = blankState();
  let storageAvailable = true;
  let storageAnnounced = false;
  let printing = false;
  let landing = 0;
  let navigationSerial = 0;
  let refreshLocation = () => {};
  const listeners = [];
  const onProgress = handler => listeners.push(handler);
  const announce = text => { const status = one('#rf-state-status'); if (status) status.textContent = text; };

  function storageFailure() {
    storageAvailable = false;
    if (!storageAnnounced) {
      announce('Your place and progress could not be saved on this device.');
      storageAnnounced = true;
    }
  }
  function save() {
    if (!storageAvailable) return;
    try { localStorage.setItem(key, JSON.stringify(state)); } catch { storageFailure(); }
  }
  function load() {
    let raw;
    try { raw = localStorage.getItem(key); } catch { storageFailure(); return; }
    let value;
    try { value = JSON.parse(raw); } catch { return; }
    if (!value || ![1, 2].includes(value.version)) return;
    if (['system', 'dark', 'sand'].includes(value.theme)) state.theme = value.theme;
    if (['guided', 'read'].includes(value.view)) state.view = value.view;
    if (SHELLS.includes(value.shell)) state.shell = value.shell;
    const last = value.last;
    if (last && pages.has(last.page) && ['lab', 'setup'].includes(pages.get(last.page).kind)) {
      state.last = {page: last.page, anchor: targets(last.page).some(item => item.id === last.anchor) ? last.anchor : ''};
    }
    if (value.positions && typeof value.positions === 'object') {
      for (const [page, anchor] of Object.entries(value.positions)) {
        if (targets(page).some(item => item.id === anchor && !item.optional) &&
            (page !== data.page || one('.rf-step > h2[id="' + anchor + '"]'))) state.positions[page] = anchor;
      }
    }
    if (value.done && typeof value.done === 'object') {
      for (const [page, anchors] of Object.entries(value.done)) {
        if (!Array.isArray(anchors) || !pages.has(page)) continue;
        const kept = anchors.filter(anchor => stepIds(page).includes(anchor));
        if (kept.length) state.done[page] = [...new Set(kept)];
      }
    }
  }
  function remember(anchor, core) {
    if (printing || !targets(data.page).some(item => item.id === anchor)) return;
    if (core) state.positions[data.page] = anchor;
    state.last = {page: data.page, anchor};
    save();
  }

  // Progress: which steps a learner marked done, per page, summed per assignment.
  const doneList = page => (state.done[page] || []).filter(id => stepIds(page).includes(id));
  const isDone = (page, id) => doneList(page).includes(id);
  function setDone(page, id, value) {
    if (!stepIds(page).includes(id)) return;
    const current = doneList(page);
    const next = value ? [...new Set([...current, id])] : current.filter(item => item !== id);
    if (next.length) state.done[page] = next; else delete state.done[page];
    save();
    listeners.forEach(handler => handler());
  }
  function moduleProgress(moduleId) {
    let total = 0, done = 0;
    for (const page of data.pages) {
      if (page.moduleId !== moduleId || !['lab', 'setup'].includes(page.kind)) continue;
      total += page.steps.length;
      done += doneList(page.path).length;
    }
    return {total, done};
  }
  function progressWords(done, total) {
    if (!total) return '';
    if (done >= total) return `All ${total} steps done`;
    return `${done} of ${total} steps done`;
  }
  function paintBar(container, done, total) {
    const fill = one('.rf-progress-fill', container);
    if (fill) fill.style.width = `${total ? Math.round((done / total) * 100) : 0}%`;
    container.toggleAttribute('data-complete', total > 0 && done >= total);
    container.toggleAttribute('data-started', done > 0);
  }

  function applyTheme() {
    if (state.theme === 'system') document.documentElement.removeAttribute('data-sc-theme');
    else document.documentElement.dataset.scTheme = state.theme;
    all('[data-theme]').forEach(select => { select.value = state.theme; });
  }
  function initTheme() {
    applyTheme();
    all('[data-theme]').forEach(select => {
      select.addEventListener('change', () => { state.theme = select.value; applyTheme(); save(); });
      select.closest('.rf-appearance').hidden = false;
    });
  }
  function resumeRecord() {
    if (!state.last) return null;
    const page = pages.get(state.last.page);
    const section = targets(page.path).find(item => item.id === state.last.anchor);
    return {page, section, module: modules.get(page.moduleId)};
  }
  function renderHomeResume() {
    const primary = one('#rf-home-primary');
    if (!primary) return;
    const resume = resumeRecord();
    const setup = one('#rf-home-setup');
    const note = one('#rf-resume-note');
    if (!resume) {
      primary.textContent = 'Start with setup';
      primary.href = urlFor(data.modules[0].overview);
      setup.hidden = note.hidden = true;
      return;
    }
    const progress = moduleProgress(resume.module.id);
    primary.textContent = `Continue · ${resume.module.caseName}`;
    primary.href = urlFor(resume.page.path, resume.section?.id);
    note.textContent = `${resume.section?.title || resume.page.title} · Last opened on this device${progress.total ? ` · ${progressWords(progress.done, progress.total)}` : ''}`;
    setup.hidden = note.hidden = false;
  }
  function renderModuleProgress() {
    all('[data-module-progress]').forEach(node => {
      const {done, total} = moduleProgress(node.dataset.moduleProgress);
      if (node.classList.contains('rf-map-progress')) {
        node.textContent = done ? progressWords(done, total) : '';
        node.toggleAttribute('data-complete', total > 0 && done >= total);
        return;
      }
      const text = one('.rf-module-progress-text', node);
      if (text && done) text.textContent = `${progressWords(done, total)} on this device.`;
      paintBar(node, done, total);
    });
  }
  function initReset() {
    all('[data-reset-place]').forEach(button => {
      button.addEventListener('click', () => {
        if (!confirm('Reset your saved place and progress marks for this course on this device?')) return;
        state.last = null;
        state.positions = {};
        state.done = {};
        save();
        renderHomeResume();
        listeners.forEach(handler => handler());
        announce('Saved place and progress marks were reset on this device.');
      });
      button.hidden = false;
    });
  }

  // Removing [hidden] prepares a native dialog; only showModal makes it visible.
  function dialogController(dialog, fallback = false) {
    let trigger;
    let restoreOnClose = true;
    function restoreFocus() {
      const destination = trigger?.getClientRects().length ? trigger : one('.rf-brand');
      destination?.focus({preventScroll: true});
    }
    function close(restore = true) {
      restoreOnClose = restore;
      if (modalSupported) dialog.close();
      else { dialog.hidden = true; delete dialog.dataset.inFlow; if (restore) restoreFocus(); }
    }
    all('[data-dialog-close]', dialog).forEach(button => button.addEventListener('click', () => close()));
    dialog.addEventListener('close', () => { if (restoreOnClose) restoreFocus(); });
    dialog.addEventListener('click', event => {
      if (event.target !== dialog) return;
      const box = dialog.getBoundingClientRect();
      if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) close();
    });
    dialog.addEventListener('keydown', event => {
      if (event.key === 'Escape') { event.preventDefault(); close(); }
    });
    if (modalSupported) dialog.hidden = false;
    else if (fallback) dialog.setAttribute('role', 'region');
    return {
      close,
      open(source) {
        restoreOnClose = true;
        if (!dialog.open && !dialog.hasAttribute('data-in-flow')) trigger = source || document.activeElement;
        if (modalSupported) { if (!dialog.open) dialog.showModal(); }
        else if (fallback) { dialog.dataset.inFlow = ''; dialog.hidden = false; }
      }
    };
  }
  function initCourse() {
    if (!modalSupported) return;
    const trigger = one('[data-course-open]');
    const dialog = one('#rf-course-dialog');
    const controller = dialogController(dialog);
    trigger.addEventListener('click', () => controller.open(trigger));
    all('a', dialog).forEach(link => link.addEventListener('click', event => { if (plainClick(event)) controller.close(false); }));
    trigger.hidden = false;
    one('.rf-course-fallback').hidden = true;
  }
  function initCopy() {
    all('pre', main).forEach(pre => {
      const command = pre.hasAttribute('data-command');
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'sc-btn rf-btn sc-btn--secondary rf-copy';
      button.textContent = command ? 'Copy command' : 'Copy text';
      button.addEventListener('click', async () => {
        const status = one('#copy-status');
        try {
          await navigator.clipboard.writeText(one('code', pre).textContent);
          status.textContent = command ? 'Command copied.' : 'Text copied.';
          button.dataset.copied = '';
          setTimeout(() => { delete button.dataset.copied; }, 1600);
        } catch { status.textContent = 'Copy failed. Select the text and copy it manually.'; }
      });
      const head = pre.closest('.rf-command')?.querySelector(':scope > .rf-command-head');
      if (head) head.append(button);
      else pre.before(button);
    });
  }
  // One shell at a time. The first explicit choice is remembered for every page; before that, the device's platform picks.
  function initShell() {
    const pairs = all('.rf-shell-pair', main);
    if (!pairs.length) return;
    const platform = navigator.userAgentData?.platform || navigator.platform || '';
    const current = () => state.shell || (/win/i.test(platform) ? 'powershell' : 'bash');
    const tabs = [];
    pairs.forEach((pair, index) => {
      const panels = SHELLS.map(shell => one(`:scope > .rf-shell-panel[data-shell="${shell}"]`, pair)).filter(Boolean);
      if (panels.length !== 2) return;
      const list = document.createElement('div');
      list.className = 'rf-shell-tabs';
      list.setAttribute('role', 'tablist');
      list.setAttribute('aria-label', 'Shell');
      panels.forEach((panel, order) => {
        const shell = panel.dataset.shell;
        const tab = document.createElement('button');
        tab.type = 'button';
        tab.className = 'rf-shell-tab';
        tab.setAttribute('role', 'tab');
        tab.id = `rf-shell-tab-${index}-${shell}`;
        tab.dataset.shell = shell;
        tab.textContent = panel.dataset.shellName;
        panel.setAttribute('role', 'tabpanel');
        panel.setAttribute('aria-labelledby', tab.id);
        tab.addEventListener('click', () => { state.shell = shell; save(); paint(); tab.focus(); });
        tab.addEventListener('keydown', event => {
          if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
          event.preventDefault();
          const next = event.key === 'Home' ? 0 : event.key === 'End' ? 1 : (order + 1) % 2;
          state.shell = panels[next].dataset.shell; save(); paint();
          one(`[data-shell="${state.shell}"]`, list).focus();
        });
        list.append(tab);
        tabs.push(tab);
      });
      pair.prepend(list);
      pair.dataset.tabbed = '';
    });
    function paint() {
      const shell = current();
      pairs.forEach(pair => {
        all(':scope > .rf-shell-panel', pair).forEach(panel => { panel.hidden = panel.dataset.shell !== shell; });
        all('.rf-shell-tab', pair).forEach(tab => {
          const selected = tab.dataset.shell === shell;
          tab.setAttribute('aria-selected', String(selected));
          tab.tabIndex = selected ? 0 : -1;
        });
      });
      document.body.dataset.shell = shell;
    }
    paint();
    addEventListener('beforeprint', () => pairs.forEach(pair => all(':scope > .rf-shell-panel', pair).forEach(panel => { panel.hidden = false; })));
    addEventListener('afterprint', paint);
  }
  function initFigures() {
    if (!modalSupported) return;
    const dialog = one('#rf-figure-dialog');
    const controller = dialogController(dialog);
    all('[data-figure-open]').forEach(link => link.addEventListener('click', event => {
      if (!plainClick(event)) return;
      const source = one('img', link.closest('.rf-figure'));
      const image = document.createElement('img');
      image.src = link.href;
      image.alt = source.alt;
      image.width = Number(source.getAttribute('width'));
      image.height = Number(source.getAttribute('height'));
      one('.rf-figure-scroll', dialog).replaceChildren(image);
      event.preventDefault();
      controller.open(link);
    }));
  }

  function initSearch() {
    const dialog = one('#rf-search-dialog');
    const trigger = one('[data-search-open]');
    const input = one('#rf-search-input');
    const scope = one('#rf-search-scope');
    const results = one('#rf-search-results');
    const status = one('#rf-search-status');
    const recovery = one('.rf-search-recovery');
    const controller = dialogController(dialog, true);
    let index = null;
    let request = null;
    let shown = 20;
    if (!data.moduleId) one('option[value="module"]', scope).remove();
    const normalize = text => text.toLowerCase().trim().replace(/\s+/g, ' ');
    const eligible = page => pages.has(page.path) && (scope.value === 'all' ||
      (scope.value === 'page' ? page.path === data.page : page.moduleId === data.moduleId));
    function find(query) {
      if (!query) {
        const list = scope.value === 'all' ?
          data.modules.map(module => ({path: module.overview, title: module.caseName, context: `${module.id} · Overview`, anchor: '', excerpt: ''})) :
          index.pages.filter(eligible).map(page => ({path: page.path, title: page.title, context: '', anchor: '', excerpt: ''}));
        const resume = scope.value === 'all' && resumeRecord();
        if (resume) list.unshift({path: resume.page.path, anchor: resume.section?.id || '', title: `Continue · ${resume.module.caseName}`, context: resume.section?.title || resume.page.title, excerpt: 'Last opened on this device'});
        return list;
      }
      const tokens = query.split(' ');
      const list = [];
      for (const page of index.pages) {
        if (!eligible(page)) continue;
        for (const section of page.sections) {
          const title = section.title || page.title;
          const lower = normalize(title);
          const pageTitle = normalize(page.title);
          const headings = `${pageTitle} ${lower}`;
          const prose = section.text || '';
          const body = normalize(prose);
          if (!tokens.every(token => `${headings} ${body}`.includes(token))) continue;
          const rank = lower === query || pageTitle === query ? 0 :
            lower.includes(query) || pageTitle.includes(query) ? 1 :
            tokens.every(token => headings.includes(token)) ? 2 : body.includes(query) ? 3 : 4;
          const matches = tokens.map(token => prose.toLowerCase().indexOf(token)).filter(at => at >= 0);
          const start = matches.length ? Math.max(0, Math.min(...matches) - 45) : 0;
          const excerpt = (start ? '…' : '') + prose.slice(start, start + 180) + (prose.length > start + 180 ? '…' : '');
          const module = modules.get(page.moduleId);
          list.push({path: page.path, anchor: section.id, title, rank, order: list.length,
            context: `${module ? `${module.id} · ${module.caseName} · ` : ''}${page.title}${section.optional ? ' · Optional stretch' : ''}`, excerpt});
        }
      }
      return list.sort((a, b) => a.rank - b.rank || a.order - b.order);
    }
    function highlightedText(span, text, query) {
      if (!query) { span.textContent = text; return; }
      const tokens = [...new Set(query.split(' '))].sort((a, b) => b.length - a.length);
      const pattern = new RegExp(tokens.map(token => token.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|'), 'gi');
      let end = 0;
      for (const match of text.matchAll(pattern)) {
        span.append(document.createTextNode(text.slice(end, match.index)));
        const mark = document.createElement('mark');
        mark.textContent = match[0];
        span.append(mark);
        end = match.index + match[0].length;
      }
      span.append(document.createTextNode(text.slice(end)));
    }
    function render(focusIndex = null) {
      if (!index) return;
      const query = normalize(input.value);
      const found = find(query);
      results.replaceChildren();
      status.textContent = `${scope.selectedOptions[0].textContent}: ` + (found.length ?
        `${found.length} results; showing ${Math.min(shown, found.length)}.` : 'No matches.');
      for (const item of found.slice(0, shown)) {
        const li = document.createElement('li');
        const link = document.createElement('a');
        link.href = urlFor(item.path, item.anchor);
        for (const [className, content] of [['rf-search-meta', item.context], ['rf-search-title', item.title], ['rf-search-excerpt', item.excerpt]]) {
          if (!content) continue;
          const span = document.createElement('span');
          span.className = className;
          if (className === 'rf-search-excerpt') highlightedText(span, content, query);
          else span.textContent = content;
          link.append(span);
        }
        link.addEventListener('click', event => { if (plainClick(event)) controller.close(false); });
        li.append(link);
        results.append(li);
      }
      if (found.length > shown) {
        const li = document.createElement('li');
        const more = document.createElement('button');
        more.type = 'button';
        more.className = 'sc-btn rf-btn sc-btn--secondary';
        more.textContent = `Show more (${found.length - shown} remaining)`;
        more.addEventListener('click', () => { const firstNew = shown; shown += 20; render(firstNew); });
        li.append(more);
        results.append(li);
      }
      if (focusIndex !== null) all('a', results)[focusIndex]?.focus();
    }
    async function loadIndex(retry = false) {
      if (retry) request = null;
      if (!request) {
        status.textContent = 'Loading search…';
        recovery.hidden = true;
        request = fetch(new URL('assets/search-index.json', root), {credentials: 'same-origin'}).then(response => {
          if (!response.ok) throw new Error('Search unavailable');
          return response.json();
        }).then(value => {
          if (value.version !== 1 || !Array.isArray(value.pages)) throw new Error('Invalid search index');
          return value;
        });
      }
      try { index = await request; recovery.hidden = true; render(); }
      catch { index = null; results.replaceChildren(); status.textContent = 'Search unavailable. Retry or use the Course map.'; recovery.hidden = false; }
    }
    function open(source) { controller.open(source); input.focus(); input.select(); loadIndex(); }
    trigger.addEventListener('click', () => open(trigger));
    input.addEventListener('input', () => { shown = 20; render(); });
    scope.addEventListener('change', () => { shown = 20; render(); });
    one('[data-search-retry]').addEventListener('click', () => loadIndex(true));
    document.addEventListener('keydown', event => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k' && !event.target.closest('input, textarea, select, [contenteditable]:not([contenteditable="false"])')) {
        event.preventDefault(); open(document.activeElement === document.body ? trigger : document.activeElement);
      }
    });
    dialog.addEventListener('keydown', event => {
      if (!['ArrowDown', 'ArrowUp'].includes(event.key)) return;
      const links = all('a, button', results);
      const at = links.indexOf(document.activeElement);
      if (!links.length || (event.target !== input && at < 0)) return;
      event.preventDefault();
      if (at === 0 && event.key === 'ArrowUp') input.focus();
      else links[at < 0 ? 0 : (at + (event.key === 'ArrowDown' ? 1 : -1) + links.length) % links.length].focus();
    });
    trigger.hidden = false;
  }

  function revealDetails(target) {
    for (let node = target; node && node !== main; node = node.parentElement) if (node.tagName === 'DETAILS') node.open = true;
  }
  function targetOffset() {
    const outline = one('.rf-inline-outline');
    return outline?.getClientRects().length ? one(':scope > summary', outline).getBoundingClientRect().height + 16 : 16;
  }
  async function placeTarget(target, focus) {
    const transaction = landing || ++navigationSerial;
    landing = transaction;
    const outline = one('.rf-inline-outline');
    if (outline) outline.open = false;
    // Font metrics, dialog closure and reader disclosure changes precede placement.
    await document.fonts.ready;
    let previous = null;
    let previousOffset = null;
    let stable = 0;
    for (let frame = 0; frame < 60 && stable < 3; frame++) {
      await new Promise(requestAnimationFrame);
      if (landing !== transaction || !target.isConnected) return;
      const box = target.getBoundingClientRect();
      const offset = targetOffset();
      // Native fragment scrolling must use the same offset as explicit placement.
      if (offset !== previousOffset) {
        main.style.setProperty('--rf-target-offset', `${offset}px`);
        previousOffset = offset;
      }
      const position = box.top + scrollY;
      const desired = Math.max(0, Math.min(position - offset, document.documentElement.scrollHeight - innerHeight));
      window.scrollTo({top: desired, behavior: 'instant'});
      stable = previous !== null && Math.abs(previous - position) < 1 && Math.abs(scrollY - desired) < 1 ? stable + 1 : 0;
      previous = position;
    }
    if (landing !== transaction) return;
    if (focus) {
      const control = one(':scope > .rf-step-toggle', target) || (target.tagName === 'DETAILS' ? one(':scope > summary', target) : target);
      if (!control.matches('button, a, summary')) control.setAttribute('tabindex', '-1');
      control.focus({preventScroll: true});
    }
    landing = 0;
    refreshLocation();
  }
  const headingTitle = heading => [...heading.childNodes].filter(node => !(node.classList?.contains('rf-step-number'))).map(node => node.textContent).join('').trim();
  function initReader() {
    const controls = one('#rf-reader-controls');
    const sections = all('.rf-step, .rf-context', main).map(section => {
      const heading = one(':scope > h2', section);
      const body = one(':scope > .rf-step-body, :scope > .rf-context-body', section);
      const badge = heading.querySelector('.rf-step-number')?.textContent.trim();
      return {section, heading, body, id: heading.id, title: headingTitle(heading), label: /^\d+$/.test(badge || '') ? `Step ${badge}` : 'Section', nodes: [...heading.childNodes], core: section.classList.contains('rf-step'), open: false};
    });
    const steps = sections.filter(item => item.core);
    if (!steps.length) { history.scrollRestoration = 'auto'; return null; }
    const byId = new Map(sections.map(item => [item.id, item]));
    let selected = steps[0].id;
    let targetId = selected;
    let detailSnapshot = null;
    let locationSeen = '';
    const details = () => all('details:not(.rf-inline-outline)', main);
    function display() {
      const read = state.view === 'read';
      document.body.dataset.view = state.view;
      history.scrollRestoration = read ? 'auto' : 'manual';
      for (const item of sections) {
        if (read) item.heading.replaceChildren(...item.nodes);
        else {
          item.button.replaceChildren(...item.nodes, item.cue);
          item.heading.replaceChildren(item.button);
        }
        const open = read || item.open;
        item.body.hidden = !open;
        item.button.setAttribute('aria-expanded', String(open));
        item.cue.textContent = open ? '▾' : '▸';
        item.section.toggleAttribute('data-selected', item.core && item.id === selected);
      }
      all('[data-view-choice]', controls).forEach(button => button.setAttribute('aria-pressed', String(button.dataset.viewChoice === state.view)));
      all('.rf-step-actions', main).forEach(nav => { nav.hidden = read; });
    }
    function select(id, {scroll = false, focus = false, record = false} = {}) {
      const target = document.getElementById(id);
      if (!target) return;
      if (scroll) landing = ++navigationSerial;
      targetId = id;
      const owner = target.closest('.rf-step, .rf-context');
      const item = owner && byId.get(owner.dataset.stepId || owner.dataset.contextId);
      if (item?.core) {
        selected = item.id;
        steps.forEach(step => { step.open = step === item; });
        if (record) remember(item.id, true);
      } else if (item) item.open = true;
      else if (record && target.closest('.rf-stretch, .rf-optional')) remember(id, false);
      display();
      revealDetails(target);
      if (scroll) placeTarget(target, focus);
    }
    function historyState(anchor) { return {...history.state, rfReader: {page: data.page, anchor}}; }
    function navigate(id) {
      if (decode(location.hash) !== id) {
        const method = id === targetId ? 'replaceState' : 'pushState';
        history[method](historyState(id), '', '#' + encodeURIComponent(id));
      }
      locationSeen = location.href;
      select(id, {scroll: true, focus: true, record: true});
    }
    function fromLocation(initial) {
      const hasHash = location.hash.length > 1;
      const fragment = decode(location.hash);
      const explicit = hasHash && fragment && document.getElementById(fragment);
      const entry = history.state?.rfReader;
      const saved = !hasHash && (initial ? state.positions[data.page] : entry?.page === data.page ? entry.anchor : null);
      const id = explicit ? fragment : saved && byId.get(saved)?.core ? saved : steps[0].id;
      steps.forEach(item => { item.open = item.id === selected; });
      select(id, {scroll: !!explicit || !!saved || !initial, focus: !!explicit || !!saved || !initial});
      if (initial) history.replaceState(historyState(id), '', location.href);
      locationSeen = location.href;
    }
    // Progress marks for this page: rail checkboxes, step badges, the header bar, and each step's done button.
    function paintProgress() {
      const done = doneList(data.page);
      const total = stepIds(data.page).length;
      for (const item of steps) {
        const marked = done.includes(item.id);
        item.section.toggleAttribute('data-done', marked);
        if (item.doneButton) {
          item.doneButton.setAttribute('aria-pressed', String(marked));
          item.doneButton.textContent = marked ? 'Done · undo' : 'Mark step done';
        }
        const row = one(`.rf-stepper-item[data-step-ref="${CSS.escape(item.id)}"]`);
        if (row) {
          row.toggleAttribute('data-done', marked);
          const box = one('input[data-step-done]', row);
          if (box) box.checked = marked;
        }
      }
      const header = one('[data-progress]');
      if (header) {
        paintBar(header, done.length, total);
        const text = one('.rf-progress-text', header);
        if (text) text.textContent = done.length ? progressWords(done.length, total) : `${total} steps. Mark each step done as you finish it; progress is saved on this device.`;
      }
    }
    try {
      for (const item of sections) {
        item.button = document.createElement('button');
        item.button.type = 'button';
        item.button.className = 'rf-step-toggle';
        item.button.setAttribute('aria-controls', item.body.id);
        item.cue = document.createElement('span');
        item.cue.className = 'rf-disclosure-cue';
        item.cue.setAttribute('aria-hidden', 'true');
        item.button.addEventListener('click', () => {
          if (!item.core) { item.open = !item.open; display(); return; }
          const close = selected === item.id && item.open;
          navigate(item.id);
          if (close) { item.open = false; display(); }
        });
      }
      steps.forEach((item, index) => {
        const footer = document.createElement('div');
        footer.className = 'rf-step-footer';
        const done = document.createElement('button');
        done.type = 'button';
        done.className = 'sc-btn rf-btn sc-btn--primary rf-done-button';
        done.addEventListener('click', () => {
          const marked = !isDone(data.page, item.id);
          setDone(data.page, item.id, marked);
          const {done: count, total} = {done: doneList(data.page).length, total: stepIds(data.page).length};
          announce(marked ? `${item.label} marked done. ${progressWords(count, total)}.` : `${item.label} unmarked. ${progressWords(count, total)}.`);
          const next = steps[index + 1];
          if (marked && next && state.view === 'guided') navigate(next.id);
        });
        item.doneButton = done;
        const nav = document.createElement('nav');
        nav.className = 'rf-step-actions';
        nav.setAttribute('aria-label', 'Adjacent sections');
        for (const [label, neighbor] of [['Previous', steps[index - 1]], ['Next', steps[index + 1]]]) {
          if (!neighbor) continue;
          const link = document.createElement('a');
          link.href = '#' + neighbor.id;
          link.textContent = `${label}: ${neighbor.title}`;
          nav.append(link);
        }
        footer.append(done, nav);
        item.body.append(footer);
      });
      all('input[data-step-done]').forEach(box => box.addEventListener('change', () => {
        setDone(data.page, box.dataset.stepDone, box.checked);
        const {length: count} = doneList(data.page);
        announce(`${box.checked ? 'Marked' : 'Unmarked'}. ${progressWords(count, stepIds(data.page).length)}.`);
      }));
      onProgress(paintProgress);
      paintProgress();
      fromLocation(true);
      function setView(view, persist) {
        if (view === 'read') {
          if (!detailSnapshot) detailSnapshot = details().map(detail => [detail, detail.open]);
          details().forEach(detail => { detail.open = true; });
        } else if (detailSnapshot) {
          detailSnapshot.forEach(([detail, open]) => { detail.open = open; });
          detailSnapshot = null;
          revealDetails(document.getElementById(targetId));
        }
        state.view = view;
        display();
        if (persist) save();
      }
      setView(state.view, false);
      all('[data-view-choice]', controls).forEach(button => button.addEventListener('click', () => setView(button.dataset.viewChoice, true)));
      function placeControls() {
        const slot = one(matchMedia('(min-width: 1280px) and (min-height: 720px)').matches ? '.rf-reader-desktop-slot' : '.rf-reader-mobile-slot');
        if (controls.parentElement !== slot) slot.append(controls);
      }
      placeControls();
      addEventListener('resize', placeControls);
      controls.hidden = false;
      all('.rf-stretch > summary', main).forEach(summary => summary.addEventListener('click', event => {
        if (!plainClick(event)) return;
        const detail = summary.parentElement;
        event.preventDefault();
        if (detail.open) detail.open = false;
        else navigate(detail.id);
      }));
      return {select, navigate, fromLocation, locationChanged() { if (locationSeen !== location.href) fromLocation(false); }};
    } catch (error) {
      sections.forEach(item => { item.heading.replaceChildren(...item.nodes); item.body.hidden = false; item.section.removeAttribute('data-selected'); });
      all('.rf-step-actions, .rf-step-footer', main).forEach(node => node.remove());
      controls.hidden = true;
      delete document.body.dataset.view;
      history.scrollRestoration = 'auto';
      console.warn('Guided reading unavailable; the full document remains open.', error);
      return null;
    }
  }
  function initNavigation(reader) {
    function navigate(id, push = true) {
      const target = document.getElementById(id);
      if (!target) return;
      if (reader) { if (push) reader.navigate(id); else reader.locationChanged(); return; }
      landing = ++navigationSerial;
      if (push && decode(location.hash) !== id) history.pushState(history.state, '', '#' + encodeURIComponent(id));
      revealDetails(target);
      placeTarget(target, true);
    }
    document.addEventListener('click', event => {
      const link = event.target.closest('a[href]');
      if (!link || !plainClick(event) || link.target || link.hasAttribute('download')) return;
      const url = new URL(link.href);
      if (url.origin !== location.origin || url.pathname !== location.pathname || url.search !== location.search) return;
      const id = decode(url.hash);
      if (!id || id === 'main' || !document.getElementById(id)) return;
      event.preventDefault();
      navigate(id);
    });
    const changed = () => { if (reader) reader.locationChanged(); else navigate(decode(location.hash), false); };
    addEventListener('hashchange', changed);
    addEventListener('popstate', changed);
    if (!reader && location.hash) changed();

    const links = all('#rf-outline a, .rf-inline-outline a');
    const ids = new Set(links.map(link => decode(new URL(link.href).hash)));
    const targets = all('[id]', main).filter(node => ids.has(node.id));
    let pending = false;
    let current = '';
    function update() {
      pending = false;
      if (landing || printing) return;
      const visible = targets.filter(target => target.getClientRects().length);
      const offset = targetOffset() + 8;
      let target = visible[0];
      for (const candidate of visible) {
        const heading = candidate.tagName === 'DETAILS' ? one(':scope > summary', candidate) : candidate;
        if (heading.getBoundingClientRect().top <= offset) target = candidate;
      }
      if (!target || target.id === current) return;
      current = target.id;
      for (const link of links) {
        const selected = decode(new URL(link.href).hash) === current;
        if (selected) link.setAttribute('aria-current', 'location');
        else link.removeAttribute('aria-current');
        link.closest('li')?.toggleAttribute('data-current', selected);
      }
      const label = one('.rf-outline-current');
      if (label) { label.textContent = links.find(link => decode(new URL(link.href).hash) === current)?.textContent.trim() || ''; label.hidden = false; }
    }
    refreshLocation = () => { if (!pending) { pending = true; requestAnimationFrame(update); } };
    addEventListener('scroll', refreshLocation, {passive: true});
    addEventListener('resize', refreshLocation);
    main.addEventListener('toggle', refreshLocation, true);
    main.addEventListener('load', refreshLocation, true);
    if (typeof ResizeObserver === 'function') new ResizeObserver(refreshLocation).observe(main);
    document.fonts.ready.then(refreshLocation);
    // An explicit user action cancels deferred placement instead of pulling them back.
    for (const event of ['wheel', 'pointerdown', 'keydown']) addEventListener(event, () => { if (landing) { landing = 0; refreshLocation(); } }, {passive: true});
    refreshLocation();
  }
  function initPrint() {
    let snapshot;
    addEventListener('beforeprint', () => {
      if (snapshot) return;
      printing = true;
      snapshot = {
        details: all('details', main).map(detail => [detail, detail.open]),
        bodies: all('.rf-step-body, .rf-context-body', main).map(body => [body, body.hidden]),
        buttons: all('.rf-step-toggle', main).map(button => [button, button.getAttribute('aria-expanded')])
      };
      snapshot.details.forEach(([detail]) => { detail.open = true; });
      snapshot.bodies.forEach(([body]) => { body.hidden = false; });
      snapshot.buttons.forEach(([button]) => button.setAttribute('aria-expanded', 'true'));
    });
    addEventListener('afterprint', () => {
      if (!snapshot) return;
      snapshot.details.forEach(([detail, open]) => { detail.open = open; });
      snapshot.bodies.forEach(([body, hidden]) => { body.hidden = hidden; });
      snapshot.buttons.forEach(([button, expanded]) => button.setAttribute('aria-expanded', expanded));
      snapshot = null;
      printing = false;
    });
  }
  function independently(initialize) {
    try { initialize(); } catch (error) { console.warn('A reading control is unavailable; ordinary course links remain usable.', error); }
  }
  load();
  onProgress(renderModuleProgress);
  onProgress(renderHomeResume);
  [initTheme, initCopy, initShell, initCourse, initFigures, initSearch, initReset, renderHomeResume, renderModuleProgress, initPrint].forEach(independently);
  const reader = initReader();
  one('.sc-skip-link').addEventListener('click', () => main.focus({preventScroll: true}));
  independently(() => initNavigation(reader));
})();
