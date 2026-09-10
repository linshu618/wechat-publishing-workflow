const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const skills = process.env.WECHAT_TEST_SKILLS || path.join(__dirname, '..', 'skills');
const source = fs.readFileSync(path.join(skills, 'wechat-html-editor/assets/editor.js'), 'utf8');
const start = source.indexOf('  async function createWechatDraft()');
const end = source.indexOf('  async function copyArticle()', start);
let release;
let calls = 0;
let result = {action: 'updated', mediaId: 'same-id'};
let statuses = [];
const gate = new Promise(resolve => { release = resolve; });
const context = {
  publishInProgress: false,
  publishTitle: {value: 'Title'},
  publishAuthor: {value: 'Author'},
  publishSaveButton: {disabled: false},
  publishExistingId: {value: 'existing-id'},
  publishSourceUrl: {value: ''},
  publishOpenComment: {checked: true},
  selectedCoverData: '',
  credentialPayload: () => ({}),
  buildWechatContent: async () => { await gate; return '<p>content</p>'; },
  apiRequest: async (_url, payload) => { calls++; assert.equal(payload.existingMediaId, 'existing-id'); return result; },
  setPublishStatus: value => statuses.push(value),
  setStatus: value => statuses.push(value),
};
vm.createContext(context);
vm.runInContext(source.slice(start, end), context);
(async () => {
  const first = context.createWechatDraft();
  assert.equal(context.publishSaveButton.disabled, true);
  await context.createWechatDraft();
  release();
  await first;
  assert.equal(calls, 1);
  assert.equal(context.publishSaveButton.disabled, false);
  assert.ok(statuses.some(x => x.includes('原草稿更新成功')));
  assert.equal(context.publishExistingId.value, '');
  context.apiRequest = async () => { throw new Error('后台草稿已发生变化'); };
  await context.createWechatDraft();
  assert.equal(context.publishInProgress, false);
  assert.equal(context.publishSaveButton.disabled, false);
  assert.ok(statuses.some(x => x.includes('保存失败：后台草稿已发生变化')));
  context.apiRequest = async () => ({action: 'unchanged', mediaId: 'same-id'});
  await context.createWechatDraft();
  assert.ok(statuses.some(x => x.includes('内容未变化，已保留原草稿')));
  console.log('PASS: duplicate clicks, existing draft ID, updated/unchanged states, failure recovery');
})().catch(error => { console.error(error); process.exitCode = 1; });
