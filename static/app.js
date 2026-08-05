const state = {
  lang: localStorage.getItem('maildeck-language') === 'en' ? 'en' : 'ru',
  provider: 'outlook',
  accounts: [],
  activeAccount: null,
  messages: [],
  activeMessage: null,
  page: 1,
  hasMore: false,
  search: '',
  importProvider: 'outlook',
  addMode: 'single',
  file: null,
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

function initials(email = '') {
  const name = email.split('@')[0].replace(/[^a-z0-9]/gi, '');
  return (name.slice(0, 2) || 'M').toUpperCase();
}

function providerTitle(provider) {
  return provider === 'outlook' ? 'Outlook' : 'Firstmail';
}

function statusCopy(account) {
  if (account.status === 'connected') return translate('connected');
  if (account.status === 'error') return state.lang === 'en' ? translate('needsCheck') : (account.lastError || translate('needsCheck'));
  return translate('unchecked');
}

function formatDate(value, compact = false) {
  if (!value) return translate('noDate');
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return translate('noDate');
  const today = new Date();
  const sameDay = date.toDateString() === today.toDateString();
  if (sameDay) return new Intl.DateTimeFormat(state.lang === 'en' ? 'en-US' : 'ru-RU', { hour: '2-digit', minute: '2-digit' }).format(date);
  return new Intl.DateTimeFormat(state.lang === 'en' ? 'en-US' : 'ru-RU', compact
    ? { day: '2-digit', month: 'short' }
    : { day: 'numeric', month: 'long', year: date.getFullYear() === today.getFullYear() ? undefined : 'numeric', hour: '2-digit', minute: '2-digit' }
  ).format(date);
}

function bytes(value) {
  if (!value) return `0 ${translate('bytes')}`;
  if (value < 1024) return `${value} ${translate('bytes')}`;
  if (value < 1024 * 1024) return `${Math.round(value / 1024)} ${translate('kilobytes')}`;
  return `${(value / 1024 / 1024).toFixed(1)} ${translate('megabytes')}`;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  });
  let payload;
  try { payload = await response.json(); } catch { payload = null; }
  if (!response.ok) {
    const error = new Error(payload?.error?.message || `${translate('error')} ${response.status}`);
    error.code = payload?.error?.code;
    throw error;
  }
  return payload;
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function toast(message, kind = 'success') {
  const node = element('div', `toast${kind === 'error' ? ' is-error' : ''}`, message);
  $('#toast-region').append(node);
  window.setTimeout(() => node.remove(), 4200);
}

function accountItem(account) {
  const button = element('button', `account-item${state.activeAccount?.id === account.id ? ' is-active' : ''}`);
  button.type = 'button';
  button.dataset.accountId = account.id;
  button.style.setProperty('--item-index', String(Math.min(state.accounts.indexOf(account), 8)));
  button.setAttribute('aria-pressed', String(state.activeAccount?.id === account.id));
  button.title = account.email;

  const avatar = element('span', 'avatar', initials(account.email));
  avatar.setAttribute('aria-hidden', 'true');
  const copy = element('span', 'account-copy');
  copy.append(element('span', 'account-email', account.email));
  const status = element('span', 'account-state');
  status.append(element('span', `status-dot ${account.status}`));
  status.append(document.createTextNode(statusCopy(account)));

  copy.append(status);
  button.append(avatar, copy, element('span', 'account-chevron', '›'));
  button.addEventListener('click', () => selectAccount(account.id));
  return button;
}

function renderAccounts() {
  const list = $('#account-list');
  list.replaceChildren();
  const visible = state.accounts.filter((account) => account.provider === state.provider && account.email.includes(state.search.toLowerCase()));
  $('#provider-label').textContent = `${translate('accounts')} ${providerTitle(state.provider)}`;
  $('#account-list').setAttribute('aria-labelledby', `tab-${state.provider}`);
  if (!visible.length) {
    const empty = element('div', 'empty-state compact-empty');
    empty.append(element('div', 'empty-orbit'));
    empty.append(element('h3', '', state.search ? translate('nothingFound') : translate('noAccounts')));
    empty.append(element('p', '', state.search ? translate('tryAnother') : translate('addHint')));
    list.append(empty);
    return;
  }
  visible.forEach((account) => list.append(accountItem(account)));
}

function updateCounts() {
  $('#outlook-count').textContent = state.accounts.filter((a) => a.provider === 'outlook').length;
  $('#firstmail-count').textContent = state.accounts.filter((a) => a.provider === 'firstmail').length;
}

async function loadAccounts(preserve = true) {
  const previousId = preserve ? state.activeAccount?.id : null;
  const payload = await api('/api/accounts');
  state.accounts = payload.accounts;
  state.activeAccount = state.accounts.find((a) => a.id === previousId) || null;
  updateCounts();
  renderAccounts();
}

function setProvider(provider) {
  const changed = state.provider !== provider;
  state.provider = provider;
  state.search = '';
  $('#account-search').value = '';
  $$('.provider-tab').forEach((tab) => {
    const active = tab.dataset.provider === provider;
    tab.classList.toggle('is-active', active);
    tab.setAttribute('aria-selected', String(active));
  });
  renderAccounts();
  if (changed) restartAnimation($('#account-list'), 'is-switching');
}

function restartAnimation(node, className) {
  if (!node || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  node.classList.remove(className);
  void node.offsetWidth;
  node.classList.add(className);
  node.addEventListener('animationend', () => node.classList.remove(className), { once: true });
}

function animateVisibleSection(node) {
  if (!node || node.hidden) return;
  restartAnimation(node, 'is-entering');
}

function setSyncStatus(copy, kind = '') {
  const status = $('#sync-status');
  status.className = `sync-status${kind ? ` ${kind}` : ''}`;
  $('.sync-copy', status).textContent = copy;
  restartAnimation(status, 'is-updating');
}

function renderHeader() {
  const account = state.activeAccount;
  $('#active-email').textContent = account?.email || translate('selectAccount');
  $('#active-avatar').textContent = initials(account?.email);
  $('#refresh-button').disabled = !account;
  $('#delete-account-button').disabled = !account;
  if (!account) setSyncStatus(translate('waiting'));
}

function loadingMessages() {
  const wrapper = element('div', 'list-loading');
  for (let i = 0; i < 5; i += 1) wrapper.append(element('div', 'skeleton'));
  $('#message-list').replaceChildren(wrapper);
  $('#message-count').textContent = translate('loadingMail');
  $('#load-more').hidden = true;
  restartAnimation($('#message-list'), 'is-switching');
}

function messageItem(message) {
  const button = element('button', `message-item${message.isUnread ? ' is-unread' : ''}${state.activeMessage?.uid === message.uid ? ' is-active' : ''}`);
  button.type = 'button';
  button.dataset.uid = message.uid;
  button.style.setProperty('--item-index', String(Math.min(state.messages.indexOf(message), 8)));
  const top = element('span', 'message-topline');
  top.append(element('span', 'message-sender', message.from || translate('unknownSender')));
  top.append(element('span', 'message-date', formatDate(message.date, true)));
  button.append(top, element('span', 'message-subject', message.subject || translate('noSubject')));
  if (message.isUnread) button.append(element('span', 'unread-mark'));
  button.addEventListener('click', () => openMessage(message.uid));
  return button;
}

function renderMessages(append = false) {
  const list = $('#message-list');
  if (!append) list.replaceChildren();
  if (!state.messages.length) {
    const empty = element('div', 'empty-state compact-empty');
    empty.append(element('div', 'empty-orbit'));
    empty.append(element('h3', '', translate('noMail')));
    empty.append(element('p', '', translate('emptyInbox')));
    list.append(empty);
  } else {
    const existing = new Set($$('[data-uid]', list).map((node) => node.dataset.uid));
    state.messages.filter((message) => !existing.has(message.uid)).forEach((message) => list.append(messageItem(message)));
  }
  $('#message-count').textContent = translate('messageCount', {
    shown: state.messages.length,
    total: state.total || state.messages.length,
  });
  $('#load-more').hidden = !state.hasMore;
  restartAnimation(list, append ? 'is-appending' : 'is-switching');
}

function emptyReader() {
  const box = element('div', 'reader-empty');
  const graphic = element('div', 'reader-graphic');
  graphic.append(element('span', 'ring ring-a'), element('span', 'ring ring-b'), element('span', 'core'));
  box.append(graphic, element('p', 'eyebrow', translate('zeroDistraction')), element('h3', '', translate('selectMessage')));
  box.append(element('p', '', translate('safeMessageHint')));
  $('#reader-pane').replaceChildren(box);
  $('#mail-layout').classList.remove('reader-open');
  restartAnimation($('#reader-pane'), 'is-revealing');
}

function readerLoading() {
  const box = element('div', 'reader-empty');
  box.append(element('p', 'eyebrow', translate('decryptingMessage')), element('h3', '', translate('opening')));
  $('#reader-pane').replaceChildren(box);
  restartAnimation($('#reader-pane'), 'is-revealing');
}

function renderReader(message) {
  const content = element('div', 'reader-content');
  content.append(element('p', 'reader-kicker', `${providerTitle(state.activeAccount.provider).toUpperCase()} · ${formatDate(message.date)}`));
  content.append(element('h3', 'reader-title', message.subject || translate('noSubject')));
  const meta = element('div', 'reader-meta');
  meta.append(element('div', 'avatar', initials(message.from)));
  const metaCopy = element('div', 'reader-meta-copy');
  metaCopy.append(element('div', 'reader-from', message.from || translate('unknownSender')));
  metaCopy.append(element('div', 'reader-to', message.to ? `${translate('to')}: ${message.to}` : translate('recipientMissing')));
  metaCopy.append(element('div', 'reader-date', formatDate(message.date)));
  meta.append(metaCopy);
  content.append(meta);
  content.append(element('div', 'reader-body', message.body || translate('noBody')));
  if (message.attachments?.length) {
    const attachments = element('div', 'attachment-list');
    attachments.append(element('p', 'reader-kicker', `${translate('attachments')} · ${message.attachments.length}`));
    message.attachments.forEach((file) => {
      const row = element('div', 'attachment');
      row.append(element('span', '', file.name), element('span', '', bytes(file.size)));
      attachments.append(row);
    });
    content.append(attachments);
  }
  const reader = $('#reader-pane');
  reader.replaceChildren(content);
  reader.scrollTop = 0;
  $('#mail-layout').classList.add('reader-open');
  restartAnimation(reader, 'is-revealing');
}

async function selectAccount(id) {
  const account = state.accounts.find((item) => item.id === id);
  if (!account) return;
  state.activeAccount = account;
  state.activeMessage = null;
  state.messages = [];
  state.page = 1;
  state.provider = account.provider;
  setProvider(account.provider);
  renderHeader();
  emptyReader();
  loadingMessages();
  setSyncStatus(translate('connecting'));
  document.body.classList.remove('sidebar-open');
  try {
    const payload = await api(`/api/accounts/${id}/messages?page=1&pageSize=30`);
    state.messages = payload.messages;
    state.hasMore = payload.hasMore;
    state.total = payload.total;
    renderMessages();
    setSyncStatus(translate('mailConnected'), 'connected');
    await loadAccounts(true);
    renderHeader();
  } catch (error) {
    setSyncStatus(translate('connectionError'), 'error');
    $('#message-list').replaceChildren(errorState(error.message, () => selectAccount(id)));
    $('#message-count').textContent = translate('failedLoad');
    toast(error.message, 'error');
    await loadAccounts(true);
  }
}

function errorState(message, retry) {
  const box = element('div', 'empty-state compact-empty');
  box.append(element('div', 'empty-orbit'), element('h3', '', translate('openFailed')), element('p', '', message));
  const button = element('button', 'primary-button', translate('retry'));
  button.type = 'button';
  button.addEventListener('click', retry);
  button.style.marginTop = '18px';
  box.append(button);
  return box;
}

async function openMessage(uid) {
  if (!state.activeAccount) return;
  readerLoading();
  state.activeMessage = { uid };
  $$('.message-item').forEach((node) => node.classList.toggle('is-active', node.dataset.uid === uid));
  try {
    const message = await api(`/api/accounts/${state.activeAccount.id}/messages/${uid}`);
    state.activeMessage = message;
    renderReader(message);
  } catch (error) {
    $('#reader-pane').replaceChildren(errorState(error.message, () => openMessage(uid)));
    toast(error.message, 'error');
  }
}

async function loadMore() {
  if (!state.activeAccount || !state.hasMore) return;
  const button = $('#load-more');
  button.disabled = true;
  button.textContent = translate('loading');
  try {
    state.page += 1;
    const payload = await api(`/api/accounts/${state.activeAccount.id}/messages?page=${state.page}&pageSize=30`);
    state.messages.push(...payload.messages);
    state.hasMore = payload.hasMore;
    state.total = payload.total;
    renderMessages(true);
  } catch (error) {
    state.page -= 1;
    toast(error.message, 'error');
  } finally {
    button.disabled = false;
    button.textContent = translate('loadMore');
  }
}

function openAdd(provider = state.provider) {
  state.importProvider = provider;
  state.file = null;
  $('#add-form').reset();
  $('#form-error').hidden = true;
  $('#file-name').textContent = translate('chooseFile');
  setImportProvider(provider);
  setAddMode('single');
  $('#add-dialog').showModal();
  restartAnimation($('#add-form'), 'is-revealing');
}

function setImportProvider(provider) {
  const changed = state.importProvider !== provider;
  state.importProvider = provider;
  $$('.modal-provider').forEach((button) => button.classList.toggle('is-active', button.dataset.importProvider === provider));
  $('#outlook-extra').hidden = provider !== 'outlook';
  $('#format-hint').textContent = provider === 'outlook'
    ? translate('outlookFormat')
    : translate('firstmailFormat');
  const email = $('#add-form [name="email"]');
  email.placeholder = provider === 'outlook' ? 'your Outlook address' : 'your Firstmail address';
  if (changed) restartAnimation($('#single-fields'), 'is-switching');
}

function setAddMode(mode) {
  const changed = state.addMode !== mode;
  state.addMode = mode;
  $$('.mode-tab').forEach((button) => button.classList.toggle('is-active', button.dataset.mode === mode));
  $('#single-fields').hidden = mode !== 'single';
  $('#bulk-fields').hidden = mode !== 'bulk';
  $('#submit-add').textContent = mode === 'single' ? translate('add') : translate('importAction');
  if (changed) {
    animateVisibleSection($('#single-fields'));
    animateVisibleSection($('#bulk-fields'));
  }
}

function showFormError(message) {
  const error = $('#form-error');
  error.textContent = message;
  error.hidden = false;
}

async function submitAdd(event) {
  event.preventDefault();
  const submit = $('#submit-add');
  $('#form-error').hidden = true;
  submit.disabled = true;
  const original = submit.textContent;
  submit.textContent = translate('saving');
  try {
    let result;
    if (state.addMode === 'single') {
      const form = new FormData($('#add-form'));
      result = await api('/api/accounts', {
        method: 'POST',
        body: JSON.stringify({
          provider: state.importProvider,
          email: form.get('email'),
          password: form.get('password'),
          refreshToken: form.get('refreshToken'),
          clientId: form.get('clientId'),
        }),
      });
      toast(result.created ? translate('accountAdded') : translate('accountUpdated'));
    } else {
      if (!state.file) throw new Error(translate('chooseTextFile'));
      if (state.file.size > 1024 * 1024) throw new Error(translate('fileTooBig'));
      const content = await state.file.text();
      result = await api('/api/import', {
        method: 'POST',
        body: JSON.stringify({ provider: state.importProvider, content }),
      });
      toast(translate('imported', result));
    }
    $('#add-dialog').close();
    setProvider(state.importProvider);
    await loadAccounts(true);
  } catch (error) {
    showFormError(error.message);
  } finally {
    submit.disabled = false;
    submit.textContent = original;
  }
}

async function deleteActiveAccount() {
  const account = state.activeAccount;
  if (!account) return;
  if (!window.confirm(translate('deleteConfirm', { email: account.email }))) return;
  try {
    await api(`/api/accounts/${account.id}`, { method: 'DELETE' });
    state.activeAccount = null;
    state.messages = [];
    state.activeMessage = null;
    renderHeader();
    renderMessages();
    emptyReader();
    await loadAccounts(false);
    toast(translate('accountDeleted'));
  } catch (error) { toast(error.message, 'error'); }
}

function installEvents() {
  $('#language-toggle').addEventListener('click', () => setLanguage(state.lang === 'ru' ? 'en' : 'ru'));
  $$('.provider-tab').forEach((tab) => tab.addEventListener('click', () => setProvider(tab.dataset.provider)));
  $$('[data-action="open-add"]').forEach((button) => button.addEventListener('click', () => openAdd()));
  $('[data-action="close-add"]').addEventListener('click', () => $('#add-dialog').close());
  $('[data-action="toggle-sidebar"]').addEventListener('click', () => document.body.classList.toggle('sidebar-open'));
  $('[data-action="close-sidebar"]').addEventListener('click', () => document.body.classList.remove('sidebar-open'));
  $('#account-search').addEventListener('input', (event) => { state.search = event.target.value.trim().toLowerCase(); renderAccounts(); });
  $('#refresh-button').addEventListener('click', () => state.activeAccount && selectAccount(state.activeAccount.id));
  $('#delete-account-button').addEventListener('click', deleteActiveAccount);
  $('#load-more').addEventListener('click', loadMore);
  $('#add-form').addEventListener('submit', submitAdd);
  $$('.modal-provider').forEach((button) => button.addEventListener('click', () => setImportProvider(button.dataset.importProvider)));
  $$('.mode-tab').forEach((button) => button.addEventListener('click', () => setAddMode(button.dataset.mode)));
  $('#file-input').addEventListener('change', (event) => {
    state.file = event.target.files[0] || null;
    $('#file-name').textContent = state.file ? state.file.name : translate('chooseFile');
  });
  const drop = $('#drop-zone');
  ['dragenter', 'dragover'].forEach((name) => drop.addEventListener(name, (event) => { event.preventDefault(); drop.classList.add('is-dragging'); }));
  ['dragleave', 'drop'].forEach((name) => drop.addEventListener(name, (event) => { event.preventDefault(); drop.classList.remove('is-dragging'); }));
  drop.addEventListener('drop', (event) => {
    state.file = event.dataTransfer.files[0] || null;
    $('#file-name').textContent = state.file ? state.file.name : translate('chooseFile');
  });
  $('#add-dialog').addEventListener('click', (event) => {
    if (event.target === $('#add-dialog')) $('#add-dialog').close();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === '/' && !/INPUT|TEXTAREA/.test(document.activeElement.tagName)) {
      event.preventDefault();
      $('#account-search').focus();
    }
    if (event.key === 'Escape') document.body.classList.remove('sidebar-open');
  });
}

async function start() {
  applyStaticTranslations();
  installEvents();
  renderHeader();
  try { await loadAccounts(false); }
  catch (error) {
    $('#account-list').replaceChildren(errorState(error.message, () => loadAccounts(false)));
    toast(error.message, 'error');
  }
}

document.addEventListener('DOMContentLoaded', start);
