const I18N = {
  ru: {
    documentTitle: 'Maildeck — единое окно почты', skipToMail: 'К письмам', appLabel: 'Почтовая панель Maildeck',
    accountsLabel: 'Аккаунты почты', privateMailHub: 'ПРИВАТНЫЙ ПОЧТОВЫЙ ЦЕНТР', addAccounts: 'Добавить аккаунты',
    providerLabel: 'Тип почты', searchAccount: 'Найти аккаунт', accountsOutlook: 'Аккаунты Outlook', accounts: 'Аккаунты',
    import: 'Импорт', selectAccounts: 'Выбрать аккаунты', finishSelection: 'Завершить выбор', createFolder: 'Создать папку',
    deleteSelected: 'Удалить выбранные', privateZone: 'Приватный контур', imapReadOnly: 'IMAP · только чтение',
    showAccounts: 'Показать аккаунты', inbox: 'ВСЕ ПИСЬМА', selectAccount: 'Выбери аккаунт', copyEmail: 'Копировать адрес', backToMessages: 'Назад к письмам',
    refresh: 'Обновить письма', waiting: 'Ожидает выбора', messageListLabel: 'Список писем', recentMail: 'Все письма',
    selectMailboxLeft: 'Выбери почту слева', noAccountSelected: 'Аккаунт ещё не выбран',
    selectAddressHint: 'Нажми на адрес слева, и реальные письма появятся здесь.', loadMore: 'Показать ещё',
    zeroDistraction: 'РЕЖИМ БЕЗ ОТВЛЕЧЕНИЙ', mailOpensHere: 'Письмо откроется здесь',
    safeTextNotice: 'Текст приводится к безопасному виду. Скрипты и внешняя разметка писем не запускаются.',
    addToMaildeck: 'ДОБАВИТЬ В MAILDECK', singleOrFile: 'По одному или целым текстовым файлом.',
    importProviderLabel: 'Тип добавляемой почты', addMethodLabel: 'Способ добавления', oneAccount: 'Один аккаунт',
    uploadFile: 'Загрузить файл', outlookAddress: 'Адрес Outlook', firstmailAddress: 'Адрес Firstmail', password: 'Пароль',
    refreshToken: 'Токен обновления', clientId: 'ID клиента', chooseFile: 'Выбрать .txt файл',
    outlookFormat: 'Формат: email:password:refresh_token:client_id', firstmailFormat: 'Формат: email:password',
    fileLimit: 'До 1 МБ. Пустые строки разрешены.', importFolder: 'Папка для импорта', noFolder: 'Без папки',
    encryptedServer: 'Данные шифруются на сервере', add: 'Добавить', close: 'Закрыть',
    organization: 'ОРГАНИЗАЦИЯ', newFolder: 'Новая папка', folderHint: 'Папка появится в текущем типе почты.',
    folderName: 'Название папки', folderPlaceholder: 'Например, Работа', create: 'Создать',
    carefulAction: 'ОСТОРОЖНОЕ ДЕЙСТВИЕ', removeFromMaildeck: 'Удалить из Maildeck?',
    deleteDoesNotTouchMailbox: 'Почтовые ящики не удалятся. Исчезнут только записи из этой панели.',
    cancel: 'Отмена', delete: 'Удалить', connected: 'Подключено', needsCheck: 'Нужна проверка',
    unchecked: 'Ещё не проверено', noDate: 'Без даты', nothingFound: 'Ничего не найдено', noAccounts: 'Аккаунтов пока нет',
    tryAnother: 'Попробуй другой запрос.', addHint: 'Добавь адрес вручную или загрузи готовый файл.',
    pinnedAccounts: 'Закреплённые', unfiled: 'Без папки', emptyFolder: 'В этой папке пока нет аккаунтов',
    selectEmail: 'Выбрать {email}', pinAccount: 'Закрепить аккаунт', unpinAccount: 'Открепить аккаунт',
    moveToFolder: 'Переместить в папку', moveEmailToFolder: 'Выбрать папку для {email}', deleteEmail: 'Удалить {email}',
    toggleFolder: 'Свернуть или развернуть папку {name}', pinFolder: 'Закрепить папку', unpinFolder: 'Открепить папку',
    deleteFolderNamed: 'Удалить папку {name}', selectedCount: 'Выбрано: {count}',
    connecting: 'Подключаемся…', mailConnected: 'Почта подключена', connectionError: 'Ошибка подключения',
    loadingMail: 'Подключаемся к почте…', failedLoad: 'Не удалось загрузить', noMail: 'Писем пока нет',
    emptyInbox: 'В этом ящике писем пока нет. Обнови позже.', unknownSender: 'Неизвестный отправитель', noSubject: 'Без темы',
    selectMessage: 'Выбери письмо', safeMessageHint: 'Письмо откроется без активной HTML-разметки и внешних скриптов.',
    decryptingMessage: 'РАСШИФРОВКА ПИСЬМА', opening: 'Открываем письмо…', to: 'Кому',
    recipientMissing: 'Получатель не указан', noBody: 'В письме нет текстового содержимого.', attachments: 'ВЛОЖЕНИЯ',
    bytes: 'Б', kilobytes: 'КБ', megabytes: 'МБ', messageCount: '{shown} из {total}', openFailed: 'Не удалось открыть почту',
    retry: 'Повторить', loading: 'Загружаем…', saving: 'Сохраняем…', importAction: 'Импортировать',
    accountAdded: 'Аккаунт добавлен', accountUpdated: 'Данные аккаунта обновлены', chooseTextFile: 'Сначала выбери текстовый файл',
    fileTooBig: 'Файл больше 1 МБ', imported: 'Импортировано: {imported}. Новых: {created}, обновлено: {updated}',
    invalidData: 'Проверь введённые данные', accountNotFound: 'Аккаунт не найден', folderNotFound: 'Папка не найдена',
    folderProviderMismatch: 'Эта папка относится к другому типу почты', folderNameConflict: 'Папка с таким именем уже есть',
    dataReadError: 'Не удалось прочитать данные', notFound: 'Запрошенный адрес не найден', requestError: 'Ошибка запроса ({status})',
    invalidImportFormat: 'Не удалось распознать формат файла', importFormatLine: 'Проверь формат данных в строке {line}',
    accountPinned: 'Аккаунт закреплён', accountUnpinned: 'Аккаунт откреплён', accountMoved: 'Аккаунт перемещён в папку',
    accountUnfiled: 'Аккаунт перемещён в раздел «Без папки»', folderPinned: 'Папка закреплена', folderUnpinned: 'Папка откреплена',
    deleteAccountTitle: 'Удалить аккаунт?', deleteAccountDescription: 'Удалить {email} из Maildeck? Сам почтовый ящик останется без изменений.',
    deleteAccountsTitle: 'Удалить аккаунты ({count})?', deleteAccountsDescription: 'Выбранные записи исчезнут из Maildeck. Сами почтовые ящики не удалятся.',
    deleteCount: 'Удалить ({count})', accountsDeleted: 'Удалено аккаунтов: {count}',
    deleteFolderTitle: 'Удалить папку?', deleteFolderDescription: 'Папка «{name}» исчезнет, а её аккаунты перейдут в раздел «Без папки».',
    deleteFolder: 'Удалить папку', folderDeleted: 'Папка удалена', folderCreated: 'Папка создана',
    emailCopied: 'Адрес скопирован', copyFailed: 'Не удалось скопировать адрес',
    switchToEnglish: 'Переключить на английский', switchToRussian: 'Переключить на русский'
  },
  en: {
    documentTitle: 'Maildeck — unified inbox', skipToMail: 'Skip to mail', appLabel: 'Maildeck inbox panel',
    accountsLabel: 'Mail accounts', privateMailHub: 'PRIVATE MAIL HUB', addAccounts: 'Add accounts',
    providerLabel: 'Mail provider', searchAccount: 'Find an account', accountsOutlook: 'Outlook accounts', accounts: 'Accounts',
    import: 'Import', selectAccounts: 'Select accounts', finishSelection: 'Finish selection', createFolder: 'Create folder',
    deleteSelected: 'Delete selected', privateZone: 'Self-hosted', imapReadOnly: 'IMAP · read-only',
    showAccounts: 'Show accounts', inbox: 'ALL MAIL', selectAccount: 'Select an account', copyEmail: 'Copy address', backToMessages: 'Back to messages',
    refresh: 'Refresh messages', waiting: 'Waiting for selection', messageListLabel: 'Message list', recentMail: 'All mail',
    selectMailboxLeft: 'Select a mailbox on the left', noAccountSelected: 'No account selected',
    selectAddressHint: 'Select an address on the left to load all its mail.', loadMore: 'Load more',
    zeroDistraction: 'ZERO DISTRACTION VIEW', mailOpensHere: 'Your message opens here',
    safeTextNotice: 'Messages are converted to safe text. Scripts and remote markup never run.',
    addToMaildeck: 'ADD TO MAILDECK', singleOrFile: 'Add one account or upload a text file.',
    importProviderLabel: 'Mail provider to add', addMethodLabel: 'Add method', oneAccount: 'One account',
    uploadFile: 'Upload file', outlookAddress: 'Outlook address', firstmailAddress: 'Firstmail address', password: 'Password',
    refreshToken: 'Refresh token', clientId: 'Client ID', chooseFile: 'Choose .txt file',
    outlookFormat: 'Format: email:password:refresh_token:client_id', firstmailFormat: 'Format: email:password',
    fileLimit: 'Up to 1 MB. Blank lines are allowed.', importFolder: 'Import into folder', noFolder: 'No folder',
    encryptedServer: 'Data is encrypted on the server', add: 'Add', close: 'Close',
    organization: 'ORGANIZATION', newFolder: 'New folder', folderHint: 'The folder will belong to the current mail provider.',
    folderName: 'Folder name', folderPlaceholder: 'For example, Work', create: 'Create',
    carefulAction: 'CAREFUL ACTION', removeFromMaildeck: 'Remove from Maildeck?',
    deleteDoesNotTouchMailbox: 'The mailboxes will stay intact. Only their records in this panel will be removed.',
    cancel: 'Cancel', delete: 'Delete', connected: 'Connected', needsCheck: 'Needs attention',
    unchecked: 'Not checked yet', noDate: 'No date', nothingFound: 'Nothing found', noAccounts: 'No accounts yet',
    tryAnother: 'Try another query.', addHint: 'Add an address manually or upload a prepared file.',
    pinnedAccounts: 'Pinned', unfiled: 'No folder', emptyFolder: 'This folder has no accounts yet',
    selectEmail: 'Select {email}', pinAccount: 'Pin account', unpinAccount: 'Unpin account',
    moveToFolder: 'Move to folder', moveEmailToFolder: 'Choose a folder for {email}', deleteEmail: 'Delete {email}',
    toggleFolder: 'Collapse or expand folder {name}', pinFolder: 'Pin folder', unpinFolder: 'Unpin folder',
    deleteFolderNamed: 'Delete folder {name}', selectedCount: 'Selected: {count}',
    connecting: 'Connecting…', mailConnected: 'Mailbox connected', connectionError: 'Connection error',
    loadingMail: 'Connecting to mailbox…', failedLoad: 'Could not load', noMail: 'No messages yet',
    emptyInbox: 'This mailbox has no messages yet. Check again later.', unknownSender: 'Unknown sender', noSubject: 'No subject',
    selectMessage: 'Select a message', safeMessageHint: 'The message opens without active HTML or external scripts.',
    decryptingMessage: 'DECRYPTING MESSAGE', opening: 'Opening message…', to: 'To',
    recipientMissing: 'Recipient not specified', noBody: 'This message has no text content.', attachments: 'ATTACHMENTS',
    bytes: 'B', kilobytes: 'KB', megabytes: 'MB', messageCount: '{shown} of {total}', openFailed: 'Could not open mailbox',
    retry: 'Retry', loading: 'Loading…', saving: 'Saving…', importAction: 'Import',
    accountAdded: 'Account added', accountUpdated: 'Account credentials updated', chooseTextFile: 'Choose a text file first',
    fileTooBig: 'File is larger than 1 MB', imported: 'Imported: {imported}. New: {created}, updated: {updated}',
    invalidData: 'Check the submitted data', accountNotFound: 'Account not found', folderNotFound: 'Folder not found',
    folderProviderMismatch: 'This folder belongs to another mail provider', folderNameConflict: 'A folder with this name already exists',
    dataReadError: 'Could not read stored data', notFound: 'The requested address was not found', requestError: 'Request failed ({status})',
    invalidImportFormat: 'Could not recognize the file format', importFormatLine: 'Check the data format on line {line}',
    accountPinned: 'Account pinned', accountUnpinned: 'Account unpinned', accountMoved: 'Account moved to folder',
    accountUnfiled: 'Account moved to No folder', folderPinned: 'Folder pinned', folderUnpinned: 'Folder unpinned',
    deleteAccountTitle: 'Delete account?', deleteAccountDescription: 'Remove {email} from Maildeck? The mailbox itself will stay intact.',
    deleteAccountsTitle: 'Delete accounts ({count})?', deleteAccountsDescription: 'The selected records will disappear from Maildeck. The mailboxes themselves will stay intact.',
    deleteCount: 'Delete ({count})', accountsDeleted: 'Accounts deleted: {count}',
    deleteFolderTitle: 'Delete folder?', deleteFolderDescription: 'Folder “{name}” will be removed and its accounts will move to No folder.',
    deleteFolder: 'Delete folder', folderDeleted: 'Folder deleted', folderCreated: 'Folder created',
    emailCopied: 'Address copied', copyFailed: 'Could not copy the address',
    switchToEnglish: 'Switch to English', switchToRussian: 'Switch to Russian'
  }
};

function translate(key, vars = {}) {
  let value = I18N[state.lang]?.[key] || I18N.ru[key] || key;
  Object.entries(vars).forEach(([name, replacement]) => { value = value.replaceAll(`{${name}}`, String(replacement)); });
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
  const languageAction = translate(state.lang === 'ru' ? 'switchToEnglish' : 'switchToRussian');
  toggle.title = languageAction;
  toggle.setAttribute('aria-label', languageAction);
}

function setLanguage(lang) {
  state.lang = lang === 'en' ? 'en' : 'ru';
  localStorage.setItem('maildeck-language', state.lang);
  $('#toast-region').replaceChildren();
  applyStaticTranslations();
  renderLocalizedState();
}
