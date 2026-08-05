const I18N = {
  ru: {
    documentTitle: 'Maildeck — единое окно почты', skipToMail: 'К письмам', addAccounts: 'Добавить аккаунты',
    searchAccount: 'Найти аккаунт', import: 'Импорт', privateZone: 'Приватный контур', inbox: 'ВХОДЯЩИЕ',
    selectAccount: 'Выбери аккаунт', recentMail: 'Последние письма', selectMailboxLeft: 'Выбери почту слева',
    noAccountSelected: 'Аккаунт ещё не выбран', selectAddressHint: 'Нажми на адрес слева, и реальные письма появятся здесь.',
    loadMore: 'Показать ещё', mailOpensHere: 'Письмо откроется здесь', safeTextNotice: 'Текст приводится к безопасному виду. Скрипты и внешняя разметка писем не запускаются.',
    singleOrFile: 'По одному или целым текстовым файлом.', oneAccount: 'Один аккаунт', uploadFile: 'Загрузить файл',
    password: 'Пароль', fileLimit: 'До 1 МБ. Пустые строки разрешены.', encryptedServer: 'Данные шифруются на сервере', add: 'Добавить',
    accounts: 'Аккаунты', connected: 'Подключено', needsCheck: 'Нужна проверка', unchecked: 'Ещё не проверено', noDate: 'Без даты',
    nothingFound: 'Ничего не найдено', noAccounts: 'Аккаунтов пока нет', tryAnother: 'Попробуй другой запрос.', addHint: 'Добавь адрес вручную или загрузи готовый файл.',
    waiting: 'Ожидает выбора', connecting: 'Подключаемся…', mailConnected: 'Почта подключена', connectionError: 'Ошибка подключения',
    loadingMail: 'Подключаемся к почте…', failedLoad: 'Не удалось загрузить', noMail: 'Писем пока нет', emptyInbox: 'В этом ящике входящие пусты. Обнови позже.',
    unknownSender: 'Неизвестный отправитель', noSubject: 'Без темы', selectMessage: 'Выбери письмо', safeMessageHint: 'Письмо откроется без активной HTML-разметки и внешних скриптов.',
    opening: 'Открываем письмо…', to: 'Кому', recipientMissing: 'Получатель не указан', noBody: 'В письме нет текстового содержимого.', attachments: 'ВЛОЖЕНИЯ',
    retry: 'Повторить', openFailed: 'Не удалось открыть почту', loading: 'Загружаем…', saving: 'Сохраняем…', importAction: 'Импортировать',
    chooseFile: 'Выбрать .txt файл', outlookFormat: 'Формат: email:password:refresh_token:client_id', firstmailFormat: 'Формат: email:password',
    accountAdded: 'Аккаунт добавлен', accountUpdated: 'Данные аккаунта обновлены', chooseTextFile: 'Сначала выбери текстовый файл', fileTooBig: 'Файл больше 1 МБ',
    deleteConfirm: 'Удалить {email} из Maildeck? Почтовый ящик не удалится.', accountDeleted: 'Аккаунт удалён из панели',
    imported: 'Импортировано: {imported}. Новых: {created}, обновлено: {updated}', error: 'Ошибка', bytes: 'Б', kilobytes: 'КБ', megabytes: 'МБ',
    appLabel: 'Почтовая панель Maildeck', accountsLabel: 'Аккаунты почты', providerLabel: 'Тип почты', messageListLabel: 'Список писем', refresh: 'Обновить письма', deleteAccount: 'Удалить аккаунт', close: 'Закрыть', messageCount: '{shown} из {total}',
    privateMailHub: 'ПРИВАТНЫЙ ПОЧТОВЫЙ ЦЕНТР', imapReadOnly: 'IMAP · только чтение', showAccounts: 'Показать аккаунты', zeroDistraction: 'РЕЖИМ БЕЗ ОТВЛЕЧЕНИЙ', addToMaildeck: 'ДОБАВИТЬ В MAILDECK', importProviderLabel: 'Тип добавляемой почты', addMethodLabel: 'Способ добавления', decryptingMessage: 'РАСШИФРОВКА ПИСЬМА', accountsOutlook: 'Аккаунты Outlook'
  },
  en: {
    documentTitle: 'Maildeck — unified inbox', skipToMail: 'Skip to mail', addAccounts: 'Add accounts',
    searchAccount: 'Find an account', import: 'Import', privateZone: 'Self-hosted', inbox: 'INBOX',
    selectAccount: 'Select an account', recentMail: 'Recent mail', selectMailboxLeft: 'Select a mailbox on the left',
    noAccountSelected: 'No account selected', selectAddressHint: 'Select an address on the left to load its real inbox.',
    loadMore: 'Load more', mailOpensHere: 'Your message opens here', safeTextNotice: 'Messages are converted to safe text. Scripts and remote markup never run.',
    singleOrFile: 'Add one account or upload a text file.', oneAccount: 'One account', uploadFile: 'Upload file',
    password: 'Password', fileLimit: 'Up to 1 MB. Blank lines are allowed.', encryptedServer: 'Data is encrypted on the server', add: 'Add',
    accounts: 'Accounts', connected: 'Connected', needsCheck: 'Needs attention', unchecked: 'Not checked yet', noDate: 'No date',
    nothingFound: 'Nothing found', noAccounts: 'No accounts yet', tryAnother: 'Try another query.', addHint: 'Add an address manually or upload a prepared file.',
    waiting: 'Waiting for selection', connecting: 'Connecting…', mailConnected: 'Mailbox connected', connectionError: 'Connection error',
    loadingMail: 'Connecting to mailbox…', failedLoad: 'Could not load', noMail: 'No messages yet', emptyInbox: 'This inbox is empty. Check again later.',
    unknownSender: 'Unknown sender', noSubject: 'No subject', selectMessage: 'Select a message', safeMessageHint: 'The message opens without active HTML or external scripts.',
    opening: 'Opening message…', to: 'To', recipientMissing: 'Recipient not specified', noBody: 'This message has no text content.', attachments: 'ATTACHMENTS',
    retry: 'Retry', openFailed: 'Could not open mailbox', loading: 'Loading…', saving: 'Saving…', importAction: 'Import',
    chooseFile: 'Choose .txt file', outlookFormat: 'Format: email:password:refresh_token:client_id', firstmailFormat: 'Format: email:password',
    accountAdded: 'Account added', accountUpdated: 'Account credentials updated', chooseTextFile: 'Choose a text file first', fileTooBig: 'File is larger than 1 MB',
    deleteConfirm: 'Remove {email} from Maildeck? The mailbox itself will not be deleted.', accountDeleted: 'Account removed from the panel',
    imported: 'Imported: {imported}. New: {created}, updated: {updated}', error: 'Error', bytes: 'B', kilobytes: 'KB', megabytes: 'MB',
    appLabel: 'Maildeck inbox panel', accountsLabel: 'Mail accounts', providerLabel: 'Mail provider', messageListLabel: 'Message list', refresh: 'Refresh messages', deleteAccount: 'Remove account', close: 'Close', messageCount: '{shown} of {total}',
    privateMailHub: 'PRIVATE MAIL HUB', imapReadOnly: 'IMAP · read-only', showAccounts: 'Show accounts', zeroDistraction: 'ZERO DISTRACTION VIEW', addToMaildeck: 'ADD TO MAILDECK', importProviderLabel: 'Mail provider to add', addMethodLabel: 'Add method', decryptingMessage: 'DECRYPTING MESSAGE', accountsOutlook: 'Outlook accounts'
  }
};

function translate(key, vars = {}) {
  let value = I18N[state.lang]?.[key] || I18N.ru[key] || key;
  Object.entries(vars).forEach(([name, replacement]) => { value = value.replace(`{${name}}`, replacement); });
  return value;
}

function applyStaticTranslations() {
  document.documentElement.lang = state.lang;
  document.title = translate('documentTitle');
  $$('[data-i18n]').forEach((node) => { node.textContent = translate(node.dataset.i18n); });
  $$('[data-i18n-placeholder]').forEach((node) => { node.placeholder = translate(node.dataset.i18nPlaceholder); });
  $$('[data-i18n-aria]').forEach((node) => { node.setAttribute('aria-label', translate(node.dataset.i18nAria)); });
  $$('[data-i18n-title]').forEach((node) => { node.title = translate(node.dataset.i18nTitle); });
  const toggle = $('#language-toggle');
  toggle.textContent = state.lang === 'ru' ? 'EN' : 'RU';
  toggle.title = state.lang === 'ru' ? 'English' : 'Русский';
  toggle.setAttribute('aria-label', state.lang === 'ru' ? 'Switch to English' : 'Переключить на русский');
}

function setLanguage(lang) {
  state.lang = lang === 'en' ? 'en' : 'ru';
  localStorage.setItem('maildeck-language', state.lang);
  applyStaticTranslations();
  renderAccounts();
  renderHeader();
  if (state.messages.length || state.activeAccount) renderMessages();
  if (state.activeMessage?.body !== undefined) renderReader(state.activeMessage);
  else if (!state.activeMessage) emptyReader();
  setImportProvider(state.importProvider);
  setAddMode(state.addMode);
}
