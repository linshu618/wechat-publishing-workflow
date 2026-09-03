(() => {
  'use strict';

  const token = window.__WECHAT_EDITOR_TOKEN__;
  const mount = document.getElementById('wechat-html-editor-runtime');
  const article = document.querySelector('#article, article, main');
  if (!mount || !article) return;
  if (!article.id) article.id = 'article';

  mount.innerHTML = `
    <div class="wechat-html-editor-toolbar">
      <div class="wechat-html-editor-toolbar-brand">
        <span class="wechat-html-editor-toolbar-mark" aria-hidden="true">编</span>
        <span><strong>公众号工作台</strong><small>本地自动保存</small></span>
      </div>
      <div class="wechat-html-editor-toolbar-actions">
        <button type="button" class="secondary" data-action="copy-title">
          <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><rect x="8" y="8" width="11" height="11" rx="2"></rect><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"></path></svg>
          <span>复制标题</span>
        </button>
        <button type="button" class="secondary" data-action="insert-image">
          <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><rect x="3" y="4" width="18" height="16" rx="2"></rect><circle cx="8.5" cy="9" r="1.5"></circle><path d="m5 17 4.5-4.5 3 3 2-2L19 18"></path></svg>
          <span>插入图片</span>
        </button>
        <button type="button" class="primary" data-action="copy-article">
          <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M9 5h8a2 2 0 0 1 2 2v12H9a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2Z"></path><path d="M15 5V3H5a2 2 0 0 0-2 2v10h4"></path><path d="m11 12 2 2 4-4"></path></svg>
          <span>复制到公众号</span>
        </button>
        <button type="button" class="publish" data-action="publish">
          <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M12 16V4"></path><path d="m7 9 5-5 5 5"></path><path d="M5 13v6h14v-6"></path></svg>
          <span>推送到草稿箱</span>
        </button>
      </div>
    </div>
    <input data-wechat-editor data-image-picker type="file" accept="image/*" hidden>
    <div id="wechat-html-editor-image-tools" data-wechat-editor>
      <button type="button" class="secondary" data-image-action="replace">替换图片</button>
      <button type="button" class="secondary" data-image-action="up">上移</button>
      <button type="button" class="secondary" data-image-action="down">下移</button>
      <button type="button" class="secondary" data-image-action="50">50%</button>
      <button type="button" class="secondary" data-image-action="75">75%</button>
      <button type="button" class="secondary" data-image-action="100">100%</button>
      <button type="button" class="secondary" data-image-action="left">左对齐</button>
      <button type="button" class="secondary" data-image-action="center">居中</button>
      <button type="button" class="secondary" data-image-action="right">右对齐</button>
      <button type="button" class="danger" data-image-action="delete" title="删除选中的图片（Delete）" aria-keyshortcuts="Delete">删除图片</button>
    </div>
    <span id="wechat-html-editor-status" data-wechat-editor data-state="success">正文可直接编辑，修改会自动保存。</span>
    <div id="wechat-html-editor-publish-modal" data-wechat-editor aria-hidden="true">
      <div class="wechat-html-editor-publish-panel" role="dialog" aria-modal="true" aria-labelledby="wechat-html-editor-publish-title">
        <div class="wechat-html-editor-publish-heading">
          <div class="wechat-html-editor-publish-brand">
            <span class="wechat-html-editor-publish-mark" aria-hidden="true">微</span>
            <div>
              <span class="wechat-html-editor-publish-eyebrow">公众号发布</span>
              <strong id="wechat-html-editor-publish-title">确认并推送到草稿箱</strong>
            </div>
          </div>
          <button type="button" class="wechat-html-editor-publish-close" data-action="close-publish" aria-label="关闭发布窗口" title="关闭">×</button>
        </div>
        <div class="wechat-html-editor-publish-layout">
          <section class="wechat-html-editor-publish-section wechat-html-editor-publish-article">
            <div class="wechat-html-editor-publish-section-heading">
              <span>01</span>
              <div><strong>文章信息</strong></div>
            </div>
            <div class="wechat-html-editor-publish-grid">
              <label class="wide"><span class="field-title">标题</span><input data-publish-title maxlength="64" aria-required="true" placeholder="请输入文章标题"></label>
              <label><span class="field-title">作者</span><input data-publish-author maxlength="16" placeholder="最多 16 个字符"><small>保存后作为默认作者</small></label>
              <label><span class="field-title">阅读原文链接</span><input data-publish-source-url type="url" maxlength="1024" placeholder="https://example.com/article"><small>选填，保存后作为默认链接</small></label>
              <label class="wide checkbox-row">
                <input data-publish-open-comment type="checkbox" checked>
                <span class="wechat-html-editor-switch" aria-hidden="true"></span>
                <span class="wechat-html-editor-switch-copy"><strong>允许读者评论</strong></span>
              </label>
            </div>
          </section>
          <div class="wechat-html-editor-publish-side">
            <section class="wechat-html-editor-publish-section">
              <div class="wechat-html-editor-publish-section-heading">
                <span>02</span>
                <div><strong>公众号账号</strong><p>凭据仅保存在这台电脑</p></div>
                <b>本机加密</b>
              </div>
              <div class="wechat-html-editor-publish-grid wechat-html-editor-account-grid">
                <label class="wide"><span class="field-title">AppID</span><input data-publish-appid autocomplete="off" placeholder="填写公众号 AppID"></label>
                <label class="wide"><span class="field-title">AppSecret</span><input data-publish-secret type="password" autocomplete="off" placeholder="已保存时无需重复填写"></label>
              </div>
            </section>
            <section class="wechat-html-editor-publish-section wechat-html-editor-cover-section">
              <div class="wechat-html-editor-publish-section-heading">
                <span>03</span>
                <div><strong>文章封面</strong><p>自动识别，也可以手动替换</p></div>
              </div>
              <label class="wechat-html-editor-cover-picker">
                <input data-publish-cover type="file" accept="image/png,image/jpeg">
                <span class="wechat-html-editor-cover-plus" aria-hidden="true">＋</span>
                <span><strong>选择封面图片</strong><small>支持 PNG、JPEG</small></span>
              </label>
              <p class="wechat-html-editor-cover-status" data-publish-cover-status>正在检查文章目录中的封面……</p>
            </section>
          </div>
        </div>
        <div class="wechat-html-editor-publish-footer">
          <div id="wechat-html-editor-publish-status" data-state="neutral" role="status" aria-live="polite">账号设置和封面就绪后即可创建草稿。</div>
          <div class="wechat-html-editor-publish-actions">
            <div>
              <button type="button" class="secondary" data-action="save-wechat-config">保存账号设置</button>
              <button type="button" class="secondary" data-action="test-wechat">检查账号连接</button>
            </div>
            <button type="button" class="publish" data-action="create-draft">创建草稿 <span aria-hidden="true">→</span></button>
          </div>
        </div>
      </div>
    </div>
  `;

  const status = mount.querySelector('#wechat-html-editor-status');
  const imagePicker = mount.querySelector('[data-image-picker]');
  const imageTools = mount.querySelector('#wechat-html-editor-image-tools');
  const publishModal = mount.querySelector('#wechat-html-editor-publish-modal');
  const publishTrigger = mount.querySelector('[data-action="publish"]');
  const publishStatus = publishModal.querySelector('#wechat-html-editor-publish-status');
  const publishTitle = publishModal.querySelector('[data-publish-title]');
  const publishAuthor = publishModal.querySelector('[data-publish-author]');
  const publishSourceUrl = publishModal.querySelector('[data-publish-source-url]');
  const publishOpenComment = publishModal.querySelector('[data-publish-open-comment]');
  const publishAppid = publishModal.querySelector('[data-publish-appid]');
  const publishSecret = publishModal.querySelector('[data-publish-secret]');
  const publishCover = publishModal.querySelector('[data-publish-cover]');
  const publishCoverStatus = publishModal.querySelector('[data-publish-cover-status]');
  // 工具栏的模糊效果会改变固定定位的参考范围，弹窗必须挂在工具栏之外。
  document.body.appendChild(publishModal);
  let selectedImage = null;
  let imageMode = 'insert';
  let lastRange = null;
  let draggedBlock = null;
  let selectedCoverData = '';
  let autosaveTimer = null;
  let saveInProgress = false;
  let pendingAutosave = false;
  let changeVersion = 0;
  let savedVersion = 0;
  const autosaveDelay = 1000;

  const setStatus = message => {
    status.textContent = message;
    status.dataset.state = /(正在|等待|检测到)/.test(message)
      ? 'loading'
      : /(失败|未授权|异常)/.test(message)
        ? 'error'
        : /(已|成功|可以|自动保存)/.test(message)
          ? 'success'
          : 'neutral';
  };
  const setPublishStatus = message => {
    publishStatus.textContent = message;
    publishStatus.dataset.state = /^正在/.test(message)
      ? 'loading'
      : /(失败|无法|不能为空)/.test(message)
        ? 'error'
        : /(成功|正常|已保存|已读取|可用)/.test(message)
          ? 'success'
          : 'neutral';
  };

  async function apiRequest(path, payload) {
    const options = { headers: { 'X-WeChat-Editor-Token': token } };
    if (payload !== undefined) {
      options.method = 'POST';
      options.headers['Content-Type'] = 'application/json; charset=utf-8';
      options.body = JSON.stringify(payload);
    }
    const response = await fetch(path, options);
    const result = await response.json();
    if (!response.ok || !result.ok) throw Object.assign(new Error(result.error || `HTTP ${response.status}`), result);
    return result;
  }

  function enableDirectEditing() {
    article.contentEditable = 'true';
    article.querySelectorAll('p').forEach(paragraph => {
      paragraph.setAttribute('contenteditable', 'true');
      paragraph.setAttribute('tabindex', '0');
    });
    article.spellcheck = false;
    article.classList.add('wechat-html-editor-editing');
  }

  function scheduleAutosave(delay = autosaveDelay) {
    window.clearTimeout(autosaveTimer);
    setStatus('检测到修改，等待自动保存……');
    autosaveTimer = window.setTimeout(() => {
      autosaveTimer = null;
      saveDocument({ automatic: true });
    }, delay);
  }

  function markChanged() {
    changeVersion += 1;
    scheduleAutosave();
  }

  function clearImageSelection() {
    if (selectedImage) selectedImage.classList.remove('wechat-html-editor-selected');
    selectedImage = null;
    imageTools.classList.remove('visible');
  }

  function selectImage(image) {
    clearImageSelection();
    selectedImage = image;
    image.classList.add('wechat-html-editor-selected');
    imageTools.classList.add('visible');
    if (!article.contains(document.activeElement)) article.focus({ preventScroll: true });
  }

  function deleteSelectedImage() {
    const image = selectedImage;
    if (!image || !article.contains(image)) {
      clearImageSelection();
      return;
    }

    // 仅移除选中的图片和空包装节点，保留周围文字及正文根节点。
    const caret = document.createRange();
    caret.setStartBefore(image);
    caret.collapse(true);
    let wrapper = image.parentElement;
    clearImageSelection();
    image.remove();
    while (wrapper && wrapper !== article && wrapper.matches('p, figure, picture, span, a, .figure')
      && !wrapper.textContent.trim()
      && !wrapper.querySelector('img, video, audio, iframe, svg, canvas, object, embed, input, textarea, select, table, hr')) {
      const parent = wrapper.parentElement;
      caret.setStartBefore(wrapper);
      caret.collapse(true);
      wrapper.remove();
      wrapper = parent;
    }
    article.focus({ preventScroll: true });
    const selection = window.getSelection();
    selection?.removeAllRanges();
    selection?.addRange(caret);
    lastRange = caret.cloneRange();
    markChanged();
    setStatus('图片已删除，等待自动保存……');
  }

  function imageBlock(image) {
    return image.closest('.figure, figure') || image.parentElement;
  }

  function rememberSelection() {
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0) return;
    const range = selection.getRangeAt(0);
    if (article.contains(range.commonAncestorContainer)) lastRange = range.cloneRange();
  }

  function pickImage(mode) {
    imageMode = mode;
    imagePicker.value = '';
    imagePicker.click();
  }

  function readImage(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(reader.error || new Error('图片读取失败'));
      reader.readAsDataURL(file);
    });
  }

  async function openPublishModal() {
    publishModal.classList.add('visible');
    publishModal.setAttribute('aria-hidden', 'false');
    document.documentElement.classList.add('wechat-html-editor-modal-open');
    publishModal.querySelector('.wechat-html-editor-publish-layout').scrollTop = 0;
    publishTitle.value = document.title.trim().slice(0, 64);
    publishAuthor.value = '';
    publishSourceUrl.value = '';
    publishOpenComment.checked = true;
    publishSecret.value = '';
    selectedCoverData = '';
    setPublishStatus('正在读取本机账号设置……');
    try {
      const config = await apiRequest('/__wechat_editor/wechat/config');
      const defaults = config.defaults || {};
      publishAppid.value = config.appid || '';
      publishAuthor.value = defaults.author || localStorage.getItem('wechat-draft-author') || '';
      publishSourceUrl.value = defaults.contentSourceUrl || '';
      publishOpenComment.checked = defaults.needOpenComment !== false;
      publishCoverStatus.textContent = config.coverName
        ? `默认使用文章目录中的 ${config.coverName}；也可以重新选择。`
        : '文章目录中没有自动识别到封面，请选择 PNG/JPEG。';
      setPublishStatus(config.configured
        ? '账号设置已就绪，可以直接创建草稿。'
        : '请先填写公众号 AppID 和 AppSecret。');
      window.setTimeout(() => {
        if (publishModal.classList.contains('visible')) publishTitle.focus({ preventScroll: true });
      }, 0);
    } catch (error) {
      setPublishStatus(`无法读取账号设置：${error.message}`);
    }
  }

  function closePublishModal() {
    publishModal.classList.remove('visible');
    publishModal.setAttribute('aria-hidden', 'true');
    document.documentElement.classList.remove('wechat-html-editor-modal-open');
    publishTrigger.focus({ preventScroll: true });
  }

  function credentialPayload() {
    return { appid: publishAppid.value.trim(), secret: publishSecret.value.trim() };
  }

  function publishDefaultsPayload() {
    return {
      author: publishAuthor.value.trim(),
      contentSourceUrl: publishSourceUrl.value.trim(),
      needOpenComment: publishOpenComment.checked
    };
  }

  function configPayload() {
    return { ...credentialPayload(), defaults: publishDefaultsPayload() };
  }

  async function saveWechatConfig() {
    setPublishStatus('正在验证账号并安全保存……');
    try {
      const result = await apiRequest('/__wechat_editor/wechat/config', configPayload());
      publishSecret.value = '';
      localStorage.removeItem('wechat-draft-author');
      setPublishStatus(`账号设置已保存，连接正常；当前草稿数 ${result.totalCount}。`);
    } catch (error) {
      setPublishStatus(`保存失败：${error.message}`);
    }
  }

  async function testWechatAccess() {
    setPublishStatus('正在检查公众号账号连接……');
    try {
      const result = await apiRequest('/__wechat_editor/wechat/test', credentialPayload());
      setPublishStatus(`账号连接正常，当前草稿数 ${result.totalCount}。`);
    } catch (error) {
      setPublishStatus(`连接失败：${error.message}`);
    }
  }

  function insertImage(src, name) {
    const block = document.createElement('p');
    block.className = 'figure';
    const image = document.createElement('img');
    image.src = src;
    image.alt = name.replace(/\.[^.]+$/, '');
    image.style.width = '100%';
    image.style.maxWidth = '100%';
    image.style.height = 'auto';
    image.draggable = true;
    block.appendChild(image);
    if (lastRange && article.contains(lastRange.commonAncestorContainer)) {
      lastRange.collapse(false);
      lastRange.insertNode(block);
    } else {
      article.appendChild(block);
    }
    selectImage(image);
  }

  function moveSelected(direction) {
    if (!selectedImage) return;
    const block = imageBlock(selectedImage);
    if (!block || block.parentElement !== article) return;
    if (direction < 0 && block.previousElementSibling) block.previousElementSibling.before(block);
    if (direction > 0 && block.nextElementSibling) block.nextElementSibling.after(block);
    setStatus('图片位置已调整。');
    markChanged();
  }

  function resizeSelected(width) {
    if (!selectedImage) return;
    selectedImage.style.width = `${width}%`;
    selectedImage.style.maxWidth = '100%';
    selectedImage.style.height = 'auto';
    setStatus(`图片宽度已调整为 ${width}%。`);
    markChanged();
  }

  function alignSelected(alignment) {
    if (!selectedImage) return;
    const margins = {
      left: ['0', 'auto'],
      center: ['auto', 'auto'],
      right: ['auto', '0']
    }[alignment];
    selectedImage.style.display = 'block';
    selectedImage.style.marginLeft = margins[0];
    selectedImage.style.marginRight = margins[1];
    setStatus('图片对齐方式已调整。');
    markChanged();
  }

  function cleanDocumentForSave() {
    const clone = document.documentElement.cloneNode(true);
    clone.classList.remove('wechat-html-editor-modal-open');
    if (!clone.className) clone.removeAttribute('class');
    clone.querySelectorAll('[data-wechat-editor], #wechat-html-editor-runtime-style, #wechat-html-editor-runtime-script')
      .forEach(element => element.remove());
    clone.querySelectorAll('.wechat-html-editor-editing, .wechat-html-editor-selected, .wechat-html-editor-dragging')
      .forEach(element => {
        element.classList.remove('wechat-html-editor-editing', 'wechat-html-editor-selected', 'wechat-html-editor-dragging');
        if (!element.className) element.removeAttribute('class');
      });
    clone.querySelectorAll('[contenteditable], [draggable]').forEach(element => {
      element.removeAttribute('contenteditable');
      element.removeAttribute('draggable');
    });
    return '<!doctype html>\n' + clone.outerHTML;
  }

  async function saveDocument({ automatic = false } = {}) {
    window.clearTimeout(autosaveTimer);
    autosaveTimer = null;
    if (saveInProgress) {
      pendingAutosave = true;
      return;
    }
    if (automatic && changeVersion === savedVersion) return;
    saveInProgress = true;
    const versionAtStart = changeVersion;
    let saved = false;
    setStatus(automatic ? '正在自动保存……' : '正在保存……');
    try {
      const response = await fetch('/__wechat_editor/save', {
        method: 'POST',
        headers: { 'Content-Type': 'text/html; charset=utf-8', 'X-WeChat-Editor-Token': token },
        body: cleanDocumentForSave()
      });
      const result = await response.json();
      if (!response.ok || !result.ok) throw new Error(result.error || `HTTP ${response.status}`);
      savedVersion = Math.max(savedVersion, versionAtStart);
      saved = true;
      const time = new Date().toLocaleTimeString('zh-CN', { hour12: false });
      if (result.backupCreated) {
        setStatus(`${automatic ? '已自动保存' : '已保存'}，并生成 ${result.backup} 原始备份。`);
      } else {
        setStatus(`${automatic ? '已自动保存' : '已保存'} ${time}。`);
      }
    } catch (error) {
      setStatus(`${automatic ? '自动保存' : '保存'}失败：${error.message}`);
    } finally {
      saveInProgress = false;
      if (pendingAutosave || (saved && changeVersion > savedVersion)) {
        pendingAutosave = false;
        scheduleAutosave(0);
      }
    }
  }

  async function copyTitle() {
    const title = document.title.trim();
    try {
      await navigator.clipboard.writeText(title);
      setStatus('标题已复制。');
    } catch {
      const input = document.createElement('textarea');
      input.value = title;
      document.body.appendChild(input);
      input.select();
      document.execCommand('copy');
      input.remove();
      setStatus('标题已复制。');
    }
  }

  function inlineWechatStyles(sourceRoot, cloneRoot) {
    const properties = [
      'display', 'font-family', 'font-size', 'font-weight', 'font-style',
      'line-height', 'letter-spacing', 'color', 'background-color',
      'text-align', 'text-decoration', 'text-indent', 'vertical-align',
      'margin-top', 'margin-right', 'margin-bottom', 'margin-left',
      'padding-top', 'padding-right', 'padding-bottom', 'padding-left',
      'border-top-width', 'border-right-width', 'border-bottom-width', 'border-left-width',
      'border-top-style', 'border-right-style', 'border-bottom-style', 'border-left-style',
      'border-top-color', 'border-right-color', 'border-bottom-color', 'border-left-color',
      'border-radius', 'border-collapse', 'border-spacing',
      'white-space', 'word-break', 'overflow-wrap', 'list-style-type'
    ];
    const dimensions = ['width', 'max-width', 'height', 'max-height'];
    const sourceElements = [sourceRoot, ...sourceRoot.querySelectorAll('*')];
    const cloneElements = [cloneRoot, ...cloneRoot.querySelectorAll('*')];
    sourceElements.forEach((source, index) => {
      const clone = cloneElements[index];
      if (!clone) return;
      const computed = getComputedStyle(source);
      properties.forEach(property => {
        const value = computed.getPropertyValue(property);
        if (value) clone.style.setProperty(property, value);
      });
      dimensions.forEach(property => clone.style.removeProperty(property));
      if (source.tagName === 'IMG') {
        const declaredWidth = source.style.width;
        const computedMaxWidth = computed.getPropertyValue('max-width');
        clone.style.display = 'block';
        clone.style.width = declaredWidth && declaredWidth.endsWith('%') ? declaredWidth : '100%';
        clone.style.maxWidth = computedMaxWidth && computedMaxWidth !== 'none' ? computedMaxWidth : '100%';
        clone.style.height = 'auto';
      } else if (source.matches('.table-wrap, table')) {
        clone.style.width = '100%';
        clone.style.maxWidth = '100%';
        clone.style.height = 'auto';
      }
      clone.removeAttribute('contenteditable');
      clone.removeAttribute('draggable');
      clone.classList.remove('wechat-html-editor-editing', 'wechat-html-editor-selected', 'wechat-html-editor-dragging');
    });
  }

  async function buildWechatContent() {
    const clone = article.cloneNode(true);
    inlineWechatStyles(article, clone);
    const sourceImages = [...article.querySelectorAll('img')];
    const cloneImages = [...clone.querySelectorAll('img')];
    for (let index = 0; index < cloneImages.length; index += 1) {
      const sourceImage = sourceImages[index];
      const cloneImage = cloneImages[index];
      const declared = sourceImage.getAttribute('src') || '';
      if (/^data:image\/(?:png|jpe?g);base64,/i.test(declared) || /^https:\/\/mmbiz\.(?:qpic|qlogo)\.cn\//i.test(declared)) {
        cloneImage.setAttribute('src', declared);
        continue;
      }
      const response = await fetch(sourceImage.currentSrc || sourceImage.src);
      if (!response.ok) throw new Error(`无法读取正文图片：${sourceImage.alt || sourceImage.src}`);
      const blob = await response.blob();
      if (!/^image\/(?:png|jpe?g)$/i.test(blob.type)) throw new Error('正文图片只支持 PNG 或 JPEG');
      cloneImage.setAttribute('src', await readImage(blob));
    }
    return clone.innerHTML;
  }

  async function createWechatDraft() {
    const title = publishTitle.value.trim();
    if (!title) {
      setPublishStatus('创建失败：标题不能为空。');
      return;
    }
    setPublishStatus('正在整理正文图片并创建草稿，请不要关闭页面……');
    try {
      const author = publishAuthor.value.trim();
      const result = await apiRequest('/__wechat_editor/wechat/draft', {
        ...credentialPayload(),
        title,
        author,
        content: await buildWechatContent(),
        contentSourceUrl: publishSourceUrl.value.trim(),
        needOpenComment: publishOpenComment.checked,
        coverData: selectedCoverData
      });
      setPublishStatus(`草稿创建成功，media_id：${result.mediaId}`);
      setStatus('文章已推送到公众号草稿箱。');
    } catch (error) {
      setPublishStatus(`创建失败：${error.message}`);
    }
  }

  async function copyArticle() {
    setStatus('正在整理正文图片……');
    let container;
    try {
      container = document.createElement('div');
      container.contentEditable = 'true';
      container.setAttribute('data-wechat-editor', '');
      container.style.cssText = `position:fixed;left:-100000px;top:0;width:${article.getBoundingClientRect().width}px`;
      container.innerHTML = await buildWechatContent();
      document.body.appendChild(container);
      const range = document.createRange();
      range.selectNodeContents(container);
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
      const ok = document.execCommand('copy');
      setStatus(ok ? '已复制公众号兼容格式，请直接粘贴到公众号正文编辑区。' : '浏览器未授权复制，请重试。');
    } catch (error) {
      setStatus(`复制失败：${error.message}`);
    } finally {
      window.getSelection()?.removeAllRanges();
      container?.remove();
    }
  }

  function handleEditorClick(event) {
    const action = event.target.closest('button')?.dataset.action;
    if (action === 'copy-title') copyTitle();
    if (action === 'insert-image') pickImage('insert');
    if (action === 'copy-article') copyArticle();
    if (action === 'publish') openPublishModal();
    if (action === 'close-publish') closePublishModal();
    if (action === 'save-wechat-config') saveWechatConfig();
    if (action === 'test-wechat') testWechatAccess();
    if (action === 'create-draft') createWechatDraft();

    const imageAction = event.target.closest('button')?.dataset.imageAction;
    if (!imageAction) return;
    if (imageAction === 'replace') pickImage('replace');
    if (imageAction === 'up') moveSelected(-1);
    if (imageAction === 'down') moveSelected(1);
    if (/^(50|75|100)$/.test(imageAction)) resizeSelected(Number(imageAction));
    if (/^(left|center|right)$/.test(imageAction)) alignSelected(imageAction);
    if (imageAction === 'delete') deleteSelectedImage();
  }

  mount.addEventListener('click', handleEditorClick);
  publishModal.addEventListener('click', handleEditorClick);

  publishModal.addEventListener('click', event => {
    if (event.target === publishModal) closePublishModal();
  });

  imagePicker.addEventListener('change', async event => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const src = await readImage(file);
      if (imageMode === 'replace' && selectedImage) {
        selectedImage.src = src;
        selectedImage.alt = file.name.replace(/\.[^.]+$/, '');
        setStatus('图片已替换。');
        markChanged();
      } else {
        insertImage(src, file.name);
        setStatus('图片已插入。');
        markChanged();
      }
    } catch (error) {
      setStatus(`图片处理失败：${error.message}`);
    }
  });

  publishCover.addEventListener('change', async event => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!/^image\/(?:png|jpeg)$/i.test(file.type)) {
      publishCoverStatus.textContent = '封面只支持 PNG 或 JPEG。';
      return;
    }
    try {
      selectedCoverData = await readImage(file);
      publishCoverStatus.textContent = `已选择 ${file.name}，创建草稿时使用这张封面。`;
    } catch (error) {
      publishCoverStatus.textContent = `封面读取失败：${error.message}`;
    }
  });

  document.addEventListener('selectionchange', rememberSelection);
  document.addEventListener('focusin', event => {
    if (!article.contains(event.target) && !imageTools.contains(event.target)) clearImageSelection();
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && publishModal.classList.contains('visible')) {
      closePublishModal();
      return;
    }
    const target = event.target instanceof Element ? event.target : null;
    if (event.key === 'Delete' && !event.isComposing && !event.ctrlKey && !event.metaKey && !event.altKey && !event.shiftKey
      && selectedImage && article.contains(selectedImage) && article.isContentEditable
      && !publishModal.classList.contains('visible')
      && target && (article.contains(target) || imageTools.contains(target))
      && !target.closest('input, textarea, select, [role="textbox"]')) {
      event.preventDefault();
      deleteSelectedImage();
      return;
    }
    if (/^(ArrowLeft|ArrowRight|ArrowUp|ArrowDown|Home|End|PageUp|PageDown)$/.test(event.key)) clearImageSelection();
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
      event.preventDefault();
      saveDocument({ automatic: false });
    }
  });
  window.addEventListener('beforeunload', event => {
    if (changeVersion <= savedVersion) return;
    event.preventDefault();
    event.returnValue = '';
  });
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden' && changeVersion > savedVersion) {
      saveDocument({ automatic: true });
    }
  });
  article.addEventListener('beforeinput', clearImageSelection);
  article.addEventListener('input', markChanged);
  article.addEventListener('click', event => {
    if (article.contentEditable !== 'true') return;
    const paragraph = event.target instanceof Element ? event.target.closest('p') : null;
    if (paragraph instanceof HTMLParagraphElement && article.contains(paragraph)) {
      paragraph.focus({ preventScroll: true });
      const selection = window.getSelection();
      if (!selection || !paragraph.contains(selection.anchorNode)) {
        const range = document.createRange();
        range.selectNodeContents(paragraph);
        range.collapse(false);
        selection?.removeAllRanges();
        selection?.addRange(range);
      }
    }
    if (event.target instanceof HTMLImageElement) selectImage(event.target);
    else if (!imageTools.contains(event.target)) clearImageSelection();
  });
  article.addEventListener('dragstart', event => {
    if (article.contentEditable !== 'true' || !(event.target instanceof HTMLImageElement)) return;
    draggedBlock = imageBlock(event.target);
    draggedBlock?.classList.add('wechat-html-editor-dragging');
    event.dataTransfer.effectAllowed = 'move';
  });
  article.addEventListener('dragover', event => {
    if (!draggedBlock) return;
    event.preventDefault();
    const target = event.target.closest('#article > *, article > *, main > *');
    if (!target || target === draggedBlock || target.parentElement !== article) return;
    const rect = target.getBoundingClientRect();
    target.parentElement.insertBefore(draggedBlock, event.clientY < rect.top + rect.height / 2 ? target : target.nextSibling);
  });
  article.addEventListener('dragend', () => {
    draggedBlock?.classList.remove('wechat-html-editor-dragging');
    if (draggedBlock) {
      setStatus('图片位置已调整。');
      markChanged();
    }
    draggedBlock = null;
  });
  article.querySelectorAll('img').forEach(image => { image.draggable = true; });
  enableDirectEditing();
  setStatus('正文可直接编辑，修改会自动保存。');
})();
