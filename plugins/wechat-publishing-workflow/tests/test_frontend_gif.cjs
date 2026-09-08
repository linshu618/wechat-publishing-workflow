const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = process.env.WECHAT_TEST_SKILLS || path.join(__dirname, '..', 'skills');
const source = fs.readFileSync(path.join(root, 'wechat-html-editor/assets/editor.js'), 'utf8');
const start = source.indexOf('  async function buildWechatContent()');
const end = source.indexOf('  async function createWechatDraft()', start);
const build = source.slice(start, end);
const gifPath = process.env.WECHAT_TEST_GIF;
const raw = gifPath ? fs.readFileSync(gifPath) : Buffer.from('R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7', 'base64');

async function run(declared, mime, shouldFetch, expectedError) {
  let fetchCount = 0;
  const cloneImage = { src: '', setAttribute(key, value) { this[key] = value; } };
  const clone = { querySelectorAll: () => [cloneImage], get innerHTML() { return cloneImage.src; } };
  const image = { getAttribute: () => declared, src: declared, currentSrc: declared, alt: 'motion' };
  const context = {
    article: { cloneNode: () => clone, querySelectorAll: () => [image] },
    inlineWechatStyles() {},
    fetch: async () => { fetchCount++; return {ok: true, blob: async () => new Blob([raw], {type: mime})}; },
    readImage: async blob => `data:${blob.type};base64,${Buffer.from(await blob.arrayBuffer()).toString('base64')}`,
  };
  vm.createContext(context);
  vm.runInContext(build, context);
  if (expectedError) {
    await assert.rejects(context.buildWechatContent(), /PNG、JPEG 或 GIF/);
  } else {
    const result = await context.buildWechatContent();
    if (shouldFetch) {
      assert.ok(result.startsWith('data:image/gif;base64,'));
      assert.deepEqual(Buffer.from(result.split(',')[1], 'base64'), raw);
    } else assert.equal(result, declared);
  }
  assert.equal(fetchCount, shouldFetch ? 1 : 0);
}

(async () => {
  await run('assets/motion.gif', 'image/gif', true);
  await run('data:image/gif;base64,' + raw.toString('base64'), 'image/gif', false);
  await run('https://mmbiz.qpic.cn/gif/0', 'image/gif', false);
  await run('assets/unsupported.webp', 'image/webp', true, true);
  console.log('PASS: local GIF, embedded GIF, WeChat URL, unsupported format; original GIF bytes preserved');
})().catch(error => { console.error(error); process.exitCode = 1; });
