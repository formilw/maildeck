const state = {
  lang: localStorage.getItem('maildeck-language') === 'en' ? 'en' : 'ru',
  provider: 'outlook',
  accounts: [],
  folders: [],
  activeAccount: null,
  messages: [],
  activeMessage: null,
  page: 1,
  hasMore: false,
  search: '',
  importProvider: 'outlook',
  addMode: 'single',
  file: null,
  selectionMode: false,
  selectedIds: new Set(),
  collapsedFolders: new Set(),
  confirmAction: null,
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const svg = (path) => `<svg viewBox="0 0 24 24" aria-hidden="true">${path}</svg>`;

const ICONS = {
  pin: svg('<path d="m15 4 5 5-3 1-4 4v4l-2 2-2-7-5-5 2-2h4l4-4z"/>'),
  trash: svg('<path d="M4 7h16M9 7V4h6v3m-9 0 1 13h10l1-13M10 11v5m4-5v5"/>'),
  folder: svg('<path d="M3 7.5h7l2 2h9v9H3z"/>'),
  chevron: svg('<path d="m9 6 6 6-6 6"/>'),
};

function initials(email = '') {
  const name = email.split('@')[0].replace(/[^a-z0-9]/gi, '');
  return (name.slice(0, 2) || 'M').toUpperCase();
}

function providerTitle(provider) {
  return provider === 'outlook' ? 'Outlook' : 'Firstmail';
}

function statusCopy(account) {
  if (account.status === 'connected') return translate('connected');
  if (account.status === 'error') return translate('needsCheck');
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

function translatedApiError(payload, status) {
  const code = payload?.error?.code;
  const details = payload?.error?.details;
  const keyByCode = {
    FILE_TOO_LARGE: 'fileTooBig', VALIDATION_ERROR: 'invalidData', ACCOUNT_NOT_FOUND: 'accountNotFound',
    FOLDER_NOT_FOUND: 'folderNotFound', FOLDER_PROVIDER_MISMATCH: 'folderProviderMismatch',
    FOLDER_NAME_CONFLICT: 'folderNameConflict', STORE_ERROR: 'dataReadError', NOT_FOUND: 'notFound',
  };
  if (code === 'INVALID_IMPORT_FORMAT') {
    return details?.line ? translate('importFormatLine', { line: details.line }) : translate('invalidImportFormat');
  }
  return translate(keyByCode[code] || 'requestError', { status });
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { 'Content-Type': 'application/json', 'Accept-Language': state.lang, ...(options.headers || {}) },
  });
  let payload;
  try { payload = await response.json(); } catch { payload = null; }
  if (!response.ok) {
    const error = new Error(translatedApiError(payload, response.status));
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

function iconButton(className, label, icon) {
  const button = element('button', className);
  button.type = 'button';
  button.setAttribute('aria-label', label);
  button.title = label;
  button.innerHTML = icon;
  return button;
}

function toast(message, kind = 'success') {
  const node = element('div', `toast${kind === 'error' ? ' is-error' : ''}`, message);
  $('#toast-region').append(node);
  window.setTimeout(() => node.remove(), 4200);
}

function folderById(id) {
  return state.folders.find((folder) => folder.id === id);
}

function providerFolders(provider = state.provider) {
  return state.folders
    .filter((folder) => folder.provider === provider)
    .sort((a, b) => Number(b.pinned) - Number(a.pinned) || a.name.localeCompare(b.name, state.lang));
}

function visibleAccounts() {
  return state.accounts
    .filter((account) => account.provider === state.provider && account.email.toLowerCase().includes(state.search))
    .sort((a, b) => Number(b.pinned) - Number(a.pinned) || a.email.localeCompare(b.email));
}

function accountItem(account) {
  const row = element('div', `account-item${state.activeAccount?.id === account.id ? ' is-active' : ''}${state.selectedIds.has(account.id) ? ' is-selected' : ''}${account.pinned ? ' is-pinned' : ''}`);
  row.dataset.accountId = account.id;
  row.style.setProperty('--item-index', String(Math.min(state.accounts.indexOf(account), 8)));

  if (state.selectionMode) {
    const checkbox = element('input', 'account-checkbox');
    checkbox.type = 'checkbox';
    checkbox.checked = state.selectedIds.has(account.id);
    checkbox.setAttribute('aria-label', translate('selectEmail', { email: account.email }));
    checkbox.addEventListener('change', () => toggleAccountSelection(account.id));
    row.append(checkbox);
  } else {
    const avatar = element('span', 'avatar', initials(account.email));
    avatar.setAttribute('aria-hidden', 'true');
    row.append(avatar);
  }

  const main = element('button', 'account-main');
  main.type = 'button';
  main.title = account.email;
  main.setAttribute('aria-pressed', String(state.activeAccount?.id === account.id));
  const copy = element('span', 'account-copy');
  copy.append(element('span', 'account-email', account.email));
  const status = element('span', 'account-state');
  status.append(element('span', `status-dot ${account.status}`), document.createTextNode(statusCopy(account)));
  copy.append(status);
  main.append(copy);
  main.addEventListener('click', () => state.selectionMode ? toggleAccountSelection(account.id) : selectAccount(account.id));
  row.append(main);

  const actions = element('div', 'account-actions');
  const pin = iconButton(`row-action pin-action${account.pinned ? ' is-active' : ''}`, account.pinned ? translate('unpinAccount') : translate('pinAccount'), ICONS.pin);
  pin.setAttribute('aria-pressed', String(account.pinned));
  pin.addEventListener('click', () => toggleAccountPin(account.id));

  const folder = iconButton('row-action folder-action', translate('moveToFolder'), ICONS.folder);
  const select = element('select', 'folder-move-select');
  select.setAttribute('aria-label', translate('moveEmailToFolder', { email: account.email }));
  select.append(new Option(translate('noFolder'), '', false, !account.folderId));
  providerFolders(account.provider).forEach((item) => select.append(new Option(item.name, item.id, false, item.id === account.folderId)));
  select.addEventListener('change', () => moveAccountToFolder(account.id, select.value || null));
  folder.append(select);

  const remove = iconButton('row-action delete-action', translate('deleteEmail', { email: account.email }), ICONS.trash);
  remove.addEventListener('click', () => requestAccountDeletion(account.id));
  actions.append(pin, folder, remove);
  row.append(actions);
  return row;
}

function folderSection(folder, accounts) {
  const section = element('section', `folder-section${folder.pinned ? ' is-pinned' : ''}`);
  const header = element('div', 'folder-header');
  const collapse = iconButton('folder-collapse', translate('toggleFolder', { name: folder.name }), ICONS.chevron);
  const collapsed = state.collapsedFolders.has(folder.id);
  collapse.classList.toggle('is-collapsed', collapsed);
  collapse.setAttribute('aria-expanded', String(!collapsed));
  collapse.addEventListener('click', () => {
    collapsed ? state.collapsedFolders.delete(folder.id) : state.collapsedFolders.add(folder.id);
    renderAccounts();
  });
  const title = element('div', 'folder-title');
  title.innerHTML = ICONS.folder;
  title.append(element('span', '', folder.name), element('span', 'folder-count', String(accounts.length)));
  const actions = element('div', 'folder-actions');
  const pin = iconButton(`row-action pin-action${folder.pinned ? ' is-active' : ''}`, folder.pinned ? translate('unpinFolder') : translate('pinFolder'), ICONS.pin);
  pin.setAttribute('aria-pressed', String(folder.pinned));
  pin.addEventListener('click', () => toggleFolderPin(folder.id));
  const remove = iconButton('row-action delete-action', translate('deleteFolderNamed', { name: folder.name }), ICONS.trash);
  remove.addEventListener('click', () => requestFolderDeletion(folder.id));
  actions.append(pin, remove);
  header.append(collapse, title, actions);
  section.append(header);
  if (!collapsed) {
    const list = element('div', 'folder-accounts');
    accounts.forEach((account) => list.append(accountItem(account)));
    if (!accounts.length) list.append(element('p', 'folder-empty', translate('emptyFolder')));
    section.append(list);
  }
  return section;
}

function renderAccountSections(list, accounts) {
  const pinned = accounts.filter((account) => account.pinned);
  if (pinned.length) {
    const label = element('p', 'account-section-label', translate('pinnedAccounts'));
    list.append(label);
    pinned.forEach((account) => list.append(accountItem(account)));
  }
  providerFolders().forEach((folder) => {
    const folderAccounts = accounts.filter((account) => !account.pinned && account.folderId === folder.id);
    list.append(folderSection(folder, folderAccounts));
  });
  const unfiled = accounts.filter((account) => !account.pinned && !account.folderId);
  if (unfiled.length) {
    if (providerFolders().length || pinned.length) list.append(element('p', 'account-section-label', translate('unfiled')));
    unfiled.forEach((account) => list.append(accountItem(account)));
  }
}

function renderAccounts() {
  const list = $('#account-list');
  list.replaceChildren();
  const visible = visibleAccounts();
  $('#provider-label').textContent = `${translate('accounts')} ${providerTitle(state.provider)}`;
  list.setAttribute('aria-labelledby', `tab-${state.provider}`);
  if (!visible.length) {
    const empty = element('div', 'empty-state compact-empty');
    empty.append(element('div', 'empty-orbit'), element('h3', '', state.search ? translate('nothingFound') : translate('noAccounts')), element('p', '', state.search ? translate('tryAnother') : translate('addHint')));
    list.append(empty);
  } else {
    renderAccountSections(list, visible);
  }
  updateSelectionBar();
}

function updateCounts() {
  $('#outlook-count').textContent = state.accounts.filter((a) => a.provider === 'outlook').length;
  $('#firstmail-count').textContent = state.accounts.filter((a) => a.provider === 'firstmail').length;
}

function updateSelectionBar() {
  const count = state.selectedIds.size;
  $('#selection-bar').hidden = !state.selectionMode;
  $('#selection-count').textContent = translate('selectedCount', { count });
  $('#delete-selected-button').disabled = count === 0;
  $('#selection-toggle').classList.toggle('is-active', state.selectionMode);
  $('#selection-toggle').setAttribute('aria-pressed', String(state.selectionMode));
  $('#selection-toggle').title = state.selectionMode ? translate('finishSelection') : translate('selectAccounts');
  $('#selection-toggle').setAttribute('aria-label', state.selectionMode ? translate('finishSelection') : translate('selectAccounts'));
}

function updateFolderSelect() {
  const select = $('#folder-select');
  const value = select.value;
  select.replaceChildren(new Option(translate('noFolder'), ''));
  providerFolders(state.importProvider).forEach((folder) => select.append(new Option(folder.name, folder.id)));
  select.value = [...select.options].some((option) => option.value === value) ? value : '';
}

async function loadAccounts(preserve = true) {
  const previousId = preserve ? state.activeAccount?.id : null;
  const payload = await api('/api/accounts');
  state.accounts = payload.accounts;
  state.folders = payload.folders || [];
  state.activeAccount = state.accounts.find((a) => a.id === previousId) || null;
  state.selectedIds = new Set([...state.selectedIds].filter((id) => state.accounts.some((a) => a.id === id)));
  updateCounts();
  updateFolderSelect();
  renderAccounts();
}

function setProvider(provider) {
  const changed = state.provider !== provider;
  state.provider = provider;
  state.search = '';
  state.selectionMode = false;
  state.selectedIds.clear();
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
  $('#copy-email-button').disabled = !account;
  if (!account) setSyncStatus(translate('waiting'));
}

function closeReader() {
  $('#mail-layout').classList.remove('reader-open');
  $('#message-list-pane').focus({ preventScroll: true });
}

function resetMailbox() {
  state.activeAccount = null;
  state.messages = [];
  state.activeMessage = null;
  state.page = 1;
  state.hasMore = false;
  state.total = 0;
  renderHeader();
  $('#message-count').textContent = translate('selectMailboxLeft');
  const empty = element('div', 'empty-state compact-empty');
  empty.append(element('div', 'empty-orbit'), element('h3', '', translate('noAccountSelected')), element('p', '', translate('selectAddressHint')));
  $('#message-list').replaceChildren(empty);
  $('#load-more').hidden = true;
  emptyReader();
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
  const active = state.activeMessage?.uid === message.uid && state.activeMessage?.folder === message.folder;
  const button = element('button', `message-item${message.isUnread ? ' is-unread' : ''}${active ? ' is-active' : ''}`);
  button.type = 'button';
  button.dataset.uid = message.uid;
  button.dataset.folder = message.folder || 'INBOX';
  button.style.setProperty('--item-index', String(Math.min(state.messages.indexOf(message), 8)));
  const top = element('span', 'message-topline');
  top.append(element('span', 'message-sender', message.from || translate('unknownSender')), element('span', 'message-date', formatDate(message.date, true)));
  button.append(top, element('span', 'message-subject', message.subject || translate('noSubject')));
  if (message.folder && message.folder.toUpperCase() !== 'INBOX') button.append(element('span', 'message-folder', message.folderLabel || message.folder));
  if (message.isUnread) button.append(element('span', 'unread-mark'));
  button.addEventListener('click', () => openMessage(message.uid, message.folder));
  return button;
}

function renderMessages(append = false) {
  const list = $('#message-list');
  if (!append) list.replaceChildren();
  if (!state.messages.length) {
    const empty = element('div', 'empty-state compact-empty');
    empty.append(element('div', 'empty-orbit'), element('h3', '', translate('noMail')), element('p', '', translate('emptyInbox')));
    list.append(empty);
  } else {
    const existing = new Set($$('[data-uid]', list).map((node) => `${node.dataset.folder}\u0000${node.dataset.uid}`));
    state.messages.filter((message) => !existing.has(`${message.folder || 'INBOX'}\u0000${message.uid}`)).forEach((message) => list.append(messageItem(message)));
  }
  $('#message-count').textContent = translate('messageCount', { shown: state.messages.length, total: state.total || state.messages.length });
  $('#load-more').hidden = !state.hasMore;
  restartAnimation(list, append ? 'is-appending' : 'is-switching');
}

function readerBackButton() {
  const button = iconButton('reader-back-button icon-button', translate('backToMessages'), svg('<path d="m15 18-6-6 6-6"/>'));
  button.id = 'reader-back-button';
  button.addEventListener('click', closeReader);
  return button;
}

function emptyReader() {
  const box = element('div', 'reader-empty');
  const graphic = element('div', 'reader-graphic');
  graphic.append(element('span', 'ring ring-a'), element('span', 'ring ring-b'), element('span', 'core'));
  box.append(graphic, element('p', 'eyebrow', translate('zeroDistraction')), element('h3', '', translate('selectMessage')), element('p', '', translate('safeMessageHint')));
  $('#reader-pane').replaceChildren(readerBackButton(), box);
  $('#mail-layout').classList.remove('reader-open');
  restartAnimation($('#reader-pane'), 'is-revealing');
}

function readerLoading() {
  const box = element('div', 'reader-empty');
  box.append(element('p', 'eyebrow', translate('decryptingMessage')), element('h3', '', translate('opening')));
  $('#reader-pane').replaceChildren(readerBackButton(), box);
  restartAnimation($('#reader-pane'), 'is-revealing');
}

function renderMessageBody(message) {
  const body = element('div', 'reader-body');
  if (!message.bodyParts?.length) {
    body.textContent = message.body || translate('noBody');
    return body;
  }
  message.bodyParts.forEach((part) => {
    if (!part?.text) return;
    if (part.href) {
      const link = element('a', 'reader-link', part.text);
      link.href = part.href;
      link.target = '_blank';
      link.rel = 'noopener noreferrer nofollow';
      body.append(link);
    } else body.append(document.createTextNode(part.text));
  });
  return body;
}

function renderReader(message) {
  const content = element('div', 'reader-content');
  content.append(element('p', 'reader-kicker', `${providerTitle(state.activeAccount.provider).toUpperCase()} · ${message.folderLabel || message.folder || 'INBOX'} · ${formatDate(message.date)}`));
  content.append(element('h3', 'reader-title', message.subject || translate('noSubject')));
  const meta = element('div', 'reader-meta');
  meta.append(element('div', 'avatar', initials(message.from)));
  const metaCopy = element('div', 'reader-meta-copy');
  metaCopy.append(element('div', 'reader-from', message.from || translate('unknownSender')));
  metaCopy.append(element('div', 'reader-to', message.to ? `${translate('to')}: ${message.to}` : translate('recipientMissing')));
  metaCopy.append(element('div', 'reader-date', formatDate(message.date)));
  meta.append(metaCopy);
  content.append(meta, renderMessageBody(message));
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
  reader.replaceChildren(readerBackButton(), content);
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
  const button = element('button', 'primary-button retry-button', translate('retry'));
  button.type = 'button';
  button.addEventListener('click', retry);
  box.append(button);
  return box;
}

async function openMessage(uid, folder = 'INBOX') {
  if (!state.activeAccount) return;
  readerLoading();
  state.activeMessage = { uid, folder };
  $$('.message-item').forEach((node) => node.classList.toggle('is-active', node.dataset.uid === uid && node.dataset.folder === folder));
  try {
    const message = await api(`/api/accounts/${state.activeAccount.id}/messages/${uid}?folder=${encodeURIComponent(folder)}`);
    state.activeMessage = message;
    renderReader(message);
  } catch (error) {
    $('#reader-pane').replaceChildren(readerBackButton(), errorState(error.message, () => openMessage(uid, folder)));
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
  $$('.modal-provider').forEach((button) => {
    const active = button.dataset.importProvider === provider;
    button.classList.toggle('is-active', active);
    button.setAttribute('aria-selected', String(active));
  });
  $('#outlook-extra').hidden = provider !== 'outlook';
  $('#format-hint').textContent = provider === 'outlook' ? translate('outlookFormat') : translate('firstmailFormat');
  $('#add-form [name="email"]').placeholder = translate(provider === 'outlook' ? 'outlookAddress' : 'firstmailAddress');
  updateFolderSelect();
  if (changed) restartAnimation($('#single-fields'), 'is-switching');
}

function setAddMode(mode) {
  const changed = state.addMode !== mode;
  state.addMode = mode;
  $$('.mode-tab').forEach((button) => {
    const active = button.dataset.mode === mode;
    button.classList.toggle('is-active', active);
    button.setAttribute('aria-selected', String(active));
  });
  $('#single-fields').hidden = mode !== 'single';
  $('#bulk-fields').hidden = mode !== 'bulk';
  $('#submit-add').textContent = mode === 'single' ? translate('add') : translate('importAction');
  if (changed) {
    animateVisibleSection($('#single-fields'));
    animateVisibleSection($('#bulk-fields'));
  }
}

function showFormError(message, selector = '#form-error') {
  const error = $(selector);
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
    const folderId = $('#folder-select').value || null;
    if (state.addMode === 'single') {
      const form = new FormData($('#add-form'));
      result = await api('/api/accounts', {
        method: 'POST',
        body: JSON.stringify({
          provider: state.importProvider, email: form.get('email'), password: form.get('password'),
          refreshToken: form.get('refreshToken'), clientId: form.get('clientId'), folderId,
        }),
      });
      toast(result.created ? translate('accountAdded') : translate('accountUpdated'));
    } else {
      if (!state.file) throw new Error(translate('chooseTextFile'));
      if (state.file.size > 1024 * 1024) throw new Error(translate('fileTooBig'));
      const content = await state.file.text();
      result = await api('/api/import', {
        method: 'POST', body: JSON.stringify({ provider: state.importProvider, folderId, content }),
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

async function toggleAccountPin(id) {
  const account = state.accounts.find((item) => item.id === id);
  if (!account) return;
  try {
    await api(`/api/accounts/${id}`, { method: 'PATCH', body: JSON.stringify({ pinned: !account.pinned }) });
    await loadAccounts(true);
    toast(account.pinned ? translate('accountUnpinned') : translate('accountPinned'));
  } catch (error) { toast(error.message, 'error'); }
}

async function moveAccountToFolder(id, folderId) {
  try {
    await api(`/api/accounts/${id}`, { method: 'PATCH', body: JSON.stringify({ folderId }) });
    await loadAccounts(true);
    toast(folderId ? translate('accountMoved') : translate('accountUnfiled'));
  } catch (error) { toast(error.message, 'error'); }
}

async function toggleFolderPin(id) {
  const folder = folderById(id);
  if (!folder) return;
  try {
    await api(`/api/folders/${id}`, { method: 'PATCH', body: JSON.stringify({ pinned: !folder.pinned }) });
    await loadAccounts(true);
    toast(folder.pinned ? translate('folderUnpinned') : translate('folderPinned'));
  } catch (error) { toast(error.message, 'error'); }
}

function toggleAccountSelection(id) {
  state.selectedIds.has(id) ? state.selectedIds.delete(id) : state.selectedIds.add(id);
  renderAccounts();
}

function toggleSelectionMode() {
  state.selectionMode = !state.selectionMode;
  if (!state.selectionMode) state.selectedIds.clear();
  renderAccounts();
}

function openConfirmation({ title, description, submitLabel, action }) {
  $('#confirm-title').textContent = title;
  $('#confirm-description').textContent = description;
  $('#confirm-submit').textContent = submitLabel;
  state.confirmAction = action;
  $('#confirm-dialog').showModal();
  restartAnimation($('#confirm-form'), 'is-revealing');
}

function requestAccountDeletion(id) {
  const account = state.accounts.find((item) => item.id === id);
  if (!account) return;
  openConfirmation({
    title: translate('deleteAccountTitle'),
    description: translate('deleteAccountDescription', { email: account.email }),
    submitLabel: translate('delete'),
    action: () => deleteAccounts([id]),
  });
}

function deleteSelectedAccounts() {
  if (!state.selectedIds.size) return;
  openConfirmation({
    title: translate('deleteAccountsTitle', { count: state.selectedIds.size }),
    description: translate('deleteAccountsDescription'),
    submitLabel: translate('deleteCount', { count: state.selectedIds.size }),
    action: () => deleteAccounts([...state.selectedIds]),
  });
}

function requestFolderDeletion(id) {
  const folder = folderById(id);
  if (!folder) return;
  openConfirmation({
    title: translate('deleteFolderTitle'),
    description: translate('deleteFolderDescription', { name: folder.name }),
    submitLabel: translate('deleteFolder'),
    action: () => deleteFolder(id),
  });
}

async function deleteAccounts(ids) {
  const activeDeleted = state.activeAccount && ids.includes(state.activeAccount.id);
  try {
    const result = await api('/api/accounts/delete-batch', { method: 'POST', body: JSON.stringify({ ids }) });
    state.selectedIds.clear();
    state.selectionMode = false;
    if (activeDeleted) resetMailbox();
    await loadAccounts(!activeDeleted);
    toast(translate('accountsDeleted', { count: result.deleted }));
    return true;
  } catch (error) {
    toast(error.message, 'error');
    return false;
  }
}

async function deleteFolder(id) {
  try {
    await api(`/api/folders/${id}`, { method: 'DELETE' });
    await loadAccounts(true);
    toast(translate('folderDeleted'));
    return true;
  } catch (error) {
    toast(error.message, 'error');
    return false;
  }
}

async function submitFolder(event) {
  event.preventDefault();
  const submit = $('#folder-form button[type="submit"]');
  $('#folder-error').hidden = true;
  submit.disabled = true;
  try {
    await api('/api/folders', { method: 'POST', body: JSON.stringify({ provider: state.provider, name: $('#folder-name').value }) });
    $('#folder-dialog').close();
    await loadAccounts(true);
    toast(translate('folderCreated'));
  } catch (error) { showFormError(error.message, '#folder-error'); }
  finally { submit.disabled = false; }
}

async function copyActiveEmail() {
  if (!state.activeAccount) return;
  try {
    await navigator.clipboard.writeText(state.activeAccount.email);
    toast(translate('emailCopied'));
  } catch {
    const area = element('textarea', 'clipboard-fallback', state.activeAccount.email);
    document.body.append(area);
    area.select();
    const copied = document.execCommand('copy');
    area.remove();
    toast(translate(copied ? 'emailCopied' : 'copyFailed'), copied ? 'success' : 'error');
  }
}

function installDialogDismiss(dialogSelector, closeSelector) {
  const dialog = $(dialogSelector);
  $(closeSelector).addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', (event) => { if (event.target === dialog) dialog.close(); });
}

function installEvents() {
  $('#language-toggle').addEventListener('click', () => setLanguage(state.lang === 'ru' ? 'en' : 'ru'));
  $$('.provider-tab').forEach((tab) => tab.addEventListener('click', () => setProvider(tab.dataset.provider)));
  $$('[data-action="open-add"]').forEach((button) => button.addEventListener('click', () => openAdd()));
  installDialogDismiss('#add-dialog', '[data-action="close-add"]');
  installDialogDismiss('#folder-dialog', '[data-action="close-folder"]');
  $('[data-action="toggle-sidebar"]').addEventListener('click', () => document.body.classList.toggle('sidebar-open'));
  $('[data-action="close-sidebar"]').addEventListener('click', () => document.body.classList.remove('sidebar-open'));
  $('#account-search').addEventListener('input', (event) => { state.search = event.target.value.trim().toLowerCase(); renderAccounts(); });
  $('#refresh-button').addEventListener('click', () => state.activeAccount && selectAccount(state.activeAccount.id));
  $('#copy-email-button').addEventListener('click', copyActiveEmail);
  $('#selection-toggle').addEventListener('click', toggleSelectionMode);
  $('#delete-selected-button').addEventListener('click', deleteSelectedAccounts);
  $('#create-folder-button').addEventListener('click', () => {
    $('#folder-form').reset(); $('#folder-error').hidden = true; $('#folder-dialog').showModal(); $('#folder-name').focus();
  });
  $('#load-more').addEventListener('click', loadMore);
  $('#add-form').addEventListener('submit', submitAdd);
  $('#folder-form').addEventListener('submit', submitFolder);
  $('#confirm-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const action = state.confirmAction;
    if (!action) return;
    const submit = $('#confirm-submit');
    submit.disabled = true;
    try {
      const succeeded = await action();
      if (succeeded) {
        state.confirmAction = null;
        $('#confirm-dialog').close();
      }
    } finally {
      submit.disabled = false;
    }
  });
  $('[data-action="cancel-confirm"]').addEventListener('click', () => { state.confirmAction = null; $('#confirm-dialog').close(); });
  $('#confirm-dialog').addEventListener('cancel', () => { state.confirmAction = null; });
  $('#confirm-dialog').addEventListener('click', (event) => {
    if (event.target === $('#confirm-dialog')) {
      state.confirmAction = null;
      $('#confirm-dialog').close();
    }
  });
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
  document.addEventListener('keydown', (event) => {
    if (event.key === '/' && !/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)) {
      event.preventDefault(); $('#account-search').focus();
    }
    if (event.key === 'Escape') document.body.classList.remove('sidebar-open');
  });
}

function renderLocalizedState() {
  renderAccounts();
  renderHeader();
  updateFolderSelect();
  if (state.activeAccount) renderMessages();
  else resetMailbox();
  if (state.activeMessage?.body !== undefined) renderReader(state.activeMessage);
  else if (state.activeAccount) emptyReader();
  setImportProvider(state.importProvider);
  setAddMode(state.addMode);
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
