const fs = require('fs');
const http = require('http');
const assert = require('assert');

const CDP = 'http://127.0.0.1:9224';
const APP = process.env.MAILDECK_QA_URL || 'http://127.0.0.1:28794';

function requestJson(method, url) {
  return new Promise((resolve, reject) => {
    const req = http.request(url, { method }, (res) => {
      let body = '';
      res.on('data', (chunk) => body += chunk);
      res.on('end', () => {
        if (res.statusCode < 200 || res.statusCode >= 300) return reject(new Error(`${method} ${url}: ${res.statusCode} ${body}`));
        resolve(JSON.parse(body || '{}'));
      });
    });
    req.on('error', reject);
    req.end();
  });
}

async function connect() {
  const target = await requestJson('PUT', `${CDP}/json/new?${encodeURIComponent('about:blank')}`);
  const socket = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { socket.addEventListener('open', resolve, { once: true }); socket.addEventListener('error', reject, { once: true }); });
  let nextId = 0;
  const pending = new Map();
  const events = [];
  socket.addEventListener('message', (event) => {
    const message = JSON.parse(event.data);
    if (message.id && pending.has(message.id)) {
      const { resolve, reject } = pending.get(message.id);
      pending.delete(message.id);
      message.error ? reject(new Error(message.error.message)) : resolve(message.result);
    } else if (message.method) events.push(message);
  });
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++nextId;
    pending.set(id, { resolve, reject });
    socket.send(JSON.stringify({ id, method, params }));
  });
  return { socket, send, events };
}

async function waitForEvent(session, method, timeout = 10000) {
  const started = Date.now();
  while (Date.now() - started < timeout) {
    const index = session.events.findIndex((event) => event.method === method);
    if (index >= 0) return session.events.splice(index, 1)[0];
    await new Promise((resolve) => setTimeout(resolve, 25));
  }
  throw new Error(`Timed out waiting for ${method}`);
}

async function evaluate(session, expression, awaitPromise = true) {
  const response = await session.send('Runtime.evaluate', { expression, awaitPromise, returnByValue: true, userGesture: true });
  if (response.exceptionDetails) throw new Error(response.exceptionDetails.text || JSON.stringify(response.exceptionDetails));
  return response.result.value;
}

async function waitFor(session, expression, timeout = 10000) {
  const started = Date.now();
  while (Date.now() - started < timeout) {
    if (await evaluate(session, expression)) return;
    await new Promise((resolve) => setTimeout(resolve, 50));
  }
  throw new Error(`Timed out waiting for ${expression}`);
}

async function click(session, selector) {
  await evaluate(session, `(() => { const node = document.querySelector(${JSON.stringify(selector)}); if (!node) throw new Error('Missing ${selector}'); node.click(); return true; })()`);
}

async function type(session, selector, value) {
  await evaluate(session, `(() => { const node = document.querySelector(${JSON.stringify(selector)}); if (!node) throw new Error('Missing ${selector}'); node.value = ${JSON.stringify(value)}; node.dispatchEvent(new Event('input', {bubbles:true})); return true; })()`);
}

async function screenshot(session, name, width, height) {
  await session.send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: width <= 640 });
  await new Promise((resolve) => setTimeout(resolve, 100));
  const result = await session.send('Page.captureScreenshot', { format: 'png', fromSurface: true, captureBeyondViewport: false });
  fs.mkdirSync('/tmp/maildeck-qa/screens', { recursive: true });
  fs.writeFileSync(`/tmp/maildeck-qa/screens/${name}.png`, Buffer.from(result.data, 'base64'));
}

async function main() {
  const session = await connect();
  const consoleProblems = [];
  await session.send('Page.enable');
  await session.send('Runtime.enable');
  await session.send('Log.enable');
  await session.send('Network.enable');
  await session.send('Page.addScriptToEvaluateOnNewDocument', {
    source: `localStorage.setItem('maildeck-language', 'ru');`,
  });
  await session.send('Page.navigate', { url: APP });
  await waitForEvent(session, 'Page.loadEventFired');
  await waitFor(session, `document.querySelector('#account-list') && document.documentElement.lang === 'ru'`);

  await evaluate(session, `(async () => {
    const payload = await (await fetch('/api/accounts')).json();
    if (payload.accounts.length) await fetch('/api/accounts/delete-batch', {
      method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({ids:payload.accounts.map(a=>a.id)})
    });
    await Promise.all(payload.folders.map(folder => fetch('/api/folders/' + folder.id, {method:'DELETE'})));
  })()`);

  // Seed through the site's own API in the page's origin.
  const seeded = await evaluate(session, `(async () => {
    const json = async (url, options={}) => {
      const response = await fetch(url, { headers:{'Content-Type':'application/json'}, ...options });
      const body = await response.json();
      if (!response.ok) throw new Error(JSON.stringify(body));
      return body;
    };
    const folder = await json('/api/folders', {method:'POST', body:JSON.stringify({provider:'firstmail',name:'Work'})});
    const a = await json('/api/accounts', {method:'POST',body:JSON.stringify({provider:'firstmail',email:'qa.one@firsthidden.com',password:'Secret!1234',folderId:folder.id})});
    const b = await json('/api/accounts', {method:'POST',body:JSON.stringify({provider:'firstmail',email:'qa.two@firsthidden.com',password:'Secret!1234'})});
    const c = await json('/api/accounts', {method:'POST',body:JSON.stringify({provider:'firstmail',email:'qa.three@firsthidden.com',password:'Secret!1234'})});
    return {folder,a:a.account,b:b.account,c:c.account};
  })()`);
  seeded.folder = seeded.folder.folder;
  assert(seeded.a.id && seeded.folder.id);
  await evaluate(session, `loadAccounts(false)`);
  await click(session, '#tab-firstmail');
  await waitFor(session, `document.querySelectorAll('.account-item').length === 3`);

  // Folder pin + account pin.
  await evaluate(session, `document.querySelector('.folder-section .pin-action').click()`);
  await waitFor(session, `document.querySelector('.folder-section.is-pinned')`);
  await evaluate(session, `(() => document.querySelector('[data-account-id="${seeded.b.id}"] .pin-action').click())()`);
  await waitFor(session, `document.querySelector('[data-account-id="${seeded.b.id}"]').classList.contains('is-pinned')`);

  // Create another folder through the site's modal.
  await click(session, '#create-folder-button');
  await type(session, '#folder-name', 'Archive');
  await click(session, '#folder-form button[type="submit"]');
  await waitFor(session, `!document.querySelector('#folder-dialog').open && [...document.querySelectorAll('.folder-title span:first-of-type')].some(n => n.textContent === 'Archive')`);

  // Batch selection and in-site confirmation. Cancel to preserve seed accounts.
  await click(session, '#selection-toggle');
  await evaluate(session, `document.querySelector('[data-account-id="${seeded.a.id}"] .account-main').click()`);
  await evaluate(session, `document.querySelector('[data-account-id="${seeded.c.id}"] .account-main').click()`);
  await waitFor(session, `document.querySelector('#selection-count').textContent.includes('2')`);
  await click(session, '#delete-selected-button');
  assert.strictEqual(await evaluate(session, `document.querySelector('#confirm-dialog').open`), true);
  assert.strictEqual(await evaluate(session, `document.querySelector('#confirm-description').textContent.includes('почтовые ящики')`), true);
  await click(session, '[data-action="cancel-confirm"]');

  // Copy address from the upper toolbar. Avoid a real IMAP attempt in QA.
  await evaluate(session, `(() => {
    state.activeAccount = state.accounts.find(account => account.id === '${seeded.b.id}');
    renderHeader();
  })()`);
  await waitFor(session, `document.querySelector('#active-email').textContent === 'qa.two@firsthidden.com'`);
  await click(session, '#copy-email-button');
  await waitFor(session, `document.querySelector('#toast-region').textContent.includes('Адрес скопирован')`);

  // RU -> EN must relocalize all visible site-owned text and modal copy.
  await click(session, '#language-toggle');
  await waitFor(session, `document.documentElement.lang === 'en' && document.title.includes('unified inbox')`);
  const enChecks = await evaluate(session, `({
    body: document.body.innerText,
    placeholders: [...document.querySelectorAll('input')].map(n=>n.placeholder),
    titles: [...document.querySelectorAll('[title]')].map(n=>n.title),
    labels: [...document.querySelectorAll('[aria-label]')].map(n=>n.getAttribute('aria-label')),
  })`);
  assert(!/[А-Яа-яЁё]/.test(enChecks.body), `Cyrillic remained in EN body: ${enChecks.body.match(/[А-Яа-яЁё][^\n]*/)?.[0]}`);
  assert(!/[А-Яа-яЁё]/.test(enChecks.placeholders.join('\n')));
  assert(!/[А-Яа-яЁё]/.test(enChecks.titles.join('\n')), `Cyrillic remained in EN titles: ${enChecks.titles.filter(value => /[А-Яа-яЁё]/.test(value)).join(' | ')}`);
  assert(!/[А-Яа-яЁё]/.test(enChecks.labels.join('\n')));
  await click(session, '[data-action="open-add"]');
  await waitFor(session, `document.querySelector('#add-dialog').open`);
  assert.strictEqual(await evaluate(session, `document.querySelector('#add-dialog').innerText.includes('ADD TO MAILDECK')`), true);
  assert.strictEqual(await evaluate(session, `/[А-Яа-яЁё]/.test(document.querySelector('#add-dialog').innerText)`), false);
  await click(session, '[data-action="close-add"]');

  // The compact reader must have a clear way back to the message list.
  await session.send('Emulation.setDeviceMetricsOverride', { width:320, height:700, deviceScaleFactor:1, mobile:true });
  await evaluate(session, `emptyReader()`);
  await evaluate(session, `document.querySelector('#mail-layout').classList.add('reader-open')`);
  await waitFor(session, `getComputedStyle(document.querySelector('#reader-back-button')).display !== 'none'`);
  await click(session, '#reader-back-button');
  assert.strictEqual(await evaluate(session, `document.querySelector('#mail-layout').classList.contains('reader-open')`), false);

  // Responsive screenshots and overflow assertions.
  await screenshot(session, 'desktop-en', 1440, 900);
  const desktopOverflow = await evaluate(session, `document.documentElement.scrollWidth - document.documentElement.clientWidth`);
  assert(desktopOverflow <= 1, `desktop horizontal overflow ${desktopOverflow}`);
  await screenshot(session, 'tablet-en', 768, 900);
  const tabletOverflow = await evaluate(session, `document.documentElement.scrollWidth - document.documentElement.clientWidth`);
  assert(tabletOverflow <= 1, `tablet horizontal overflow ${tabletOverflow}`);
  await screenshot(session, 'mobile-en', 320, 700);
  const mobileOverflow = await evaluate(session, `document.documentElement.scrollWidth - document.documentElement.clientWidth`);
  assert(mobileOverflow <= 1, `mobile horizontal overflow ${mobileOverflow}`);
  await click(session, '[data-action="toggle-sidebar"]');
  await waitFor(session, `document.body.classList.contains('sidebar-open')`);
  await screenshot(session, 'mobile-sidebar-en', 320, 700);

  for (const event of session.events) {
    if (event.method === 'Runtime.consoleAPICalled' && ['error','warning'].includes(event.params.type)) consoleProblems.push(event.params);
    if (event.method === 'Runtime.exceptionThrown') consoleProblems.push(event.params);
    if (event.method === 'Log.entryAdded' && ['error','warning'].includes(event.params.entry.level)) consoleProblems.push(event.params.entry);
  }
  assert.strictEqual(consoleProblems.length, 0, `Console problems: ${JSON.stringify(consoleProblems)}`);
  console.log(JSON.stringify({ ok:true, seeded, screenshots:['desktop-en','tablet-en','mobile-en','mobile-sidebar-en'], consoleProblems:0 }));
  session.socket.close();
}

main().catch((error) => { console.error(error.stack || error); process.exit(1); });
