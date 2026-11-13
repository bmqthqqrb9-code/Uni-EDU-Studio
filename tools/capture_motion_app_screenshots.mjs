import { execFileSync } from 'node:child_process';
import { mkdir, readFile, rm } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect } from '@playwright/test';
import { chromium } from 'playwright';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const baseURL = process.argv[2] || 'http://127.0.0.1:4173';
const library = JSON.parse(
  await readFile(path.join(root, 'motion_library/library.json'), 'utf8'),
);
const requestedCaptures = process.env.MOTION_CAPTURE_FILTER
  ?.split(',')
  .map((value) => value.trim())
  .filter(Boolean);
const shouldCapture = (version, name) => (
  !requestedCaptures
  || requestedCaptures.includes(name)
  || requestedCaptures.includes(`${version}/${name}`)
);
const countBlocks = (value) => {
  if (Array.isArray(value)) return value.reduce((count, item) => count + countBlocks(item), 0);
  if (!value || typeof value !== 'object') return 0;
  const repeatCountBlock = value.type === 'controls_repeat_ext' && Number.isFinite(value.times)
    ? 1
    : 0;
  return (value.type ? 1 : 0) + repeatCountBlock
    + Object.values(value).reduce((count, item) => count + countBlocks(item), 0);
};

const captureBox = async (page, box, outputPath) => {
  if (box.width <= 0 || box.height <= 0) {
    throw new Error(`Cannot capture an element with an empty viewport box: ${outputPath}`);
  }
  await page.screenshot({
    path: outputPath,
    clip: box,
    animations: 'disabled',
  });
};

const captureBlocks = async (page, outputPath) => {
  const box = await page.evaluate(() => {
    const workspace = window.Blockly?.getMainWorkspace();
    const blocks = workspace?.getAllBlocks(false) || [];
    const rects = blocks
      .map((block) => block.getSvgRoot()?.getBoundingClientRect())
      .filter((rect) => rect && rect.width > 0 && rect.height > 0);
    if (rects.length === 0) return null;
    const left = Math.min(...rects.map((rect) => rect.left));
    const top = Math.min(...rects.map((rect) => rect.top));
    const right = Math.max(...rects.map((rect) => rect.right));
    const bottom = Math.max(...rects.map((rect) => rect.bottom));
    return {
      x: Math.max(0, left - 18),
      y: Math.max(0, top - 18),
      width: right - left + 36,
      height: bottom - top + 36,
    };
  });
  if (!box) throw new Error(`Blockly has no rendered blocks for ${outputPath}`);
  await captureBox(page, box, outputPath);
};

const captureElement = async (page, locator, outputPath) => {
  const box = await locator.evaluate((element) => {
    const { x, y, width, height } = element.getBoundingClientRect();
    return { x, y, width, height };
  });
  await captureBox(page, box, outputPath);
};

const browser = await chromium.launch({ headless: true });

try {
  for (const version of ['legacy', 'duet']) {
    const activities = library.filter((entry) => (
      entry.controller_version === version && shouldCapture(version, entry.name)
    ));
    if (activities.length === 0) continue;
    const context = await browser.newContext({
      viewport: { width: 1280, height: 900 },
      deviceScaleFactor: 1,
    });
    const page = await context.newPage();

    await page.addInitScript(() => {
      localStorage.setItem('edu-classroom-session', JSON.stringify({
        token: 'motion-screenshot-student',
        user: { role: 'student', username: 'motion_screenshot_student' },
      }));
    });
    page.setDefaultTimeout(30000);
    await page.route('**/api/**', async (route) => {
      const { pathname } = new URL(route.request().url());
      const body = pathname === '/api/classroom/codes'
        ? { codes: [], starter_codes: library.filter((entry) => entry.controller_version === version) }
        : {};
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(body),
      });
    });

    await page.goto(baseURL);
    await expect(page.locator('canvas')).toBeVisible();
    await page.getByRole('button', { name: 'Library' })
      .evaluate((button) => button.click());
    await expect(page.getByText('Starter motion library')).toBeVisible();

    const imageDirectory = path.join(root, 'motion_library', version, 'images');
    await mkdir(imageDirectory, { recursive: true });

    for (const [index, activity] of activities.entries()) {
      console.log(`Capturing ${version}/${activity.name}`);
      const blockExample = JSON.parse(await readFile(
        path.join(root, 'motion_library', version, `${activity.name}.blocks.json`),
        'utf8',
      ));
      const expectedBlockCount = countBlocks(blockExample.blocks);
      if (index === 0) {
        const activityCard = page.getByText(activity.name, { exact: true })
          .locator('xpath=../..');
        await activityCard.getByRole('button', { name: 'Load into editor' })
          .evaluate((button) => button.click());
        await page.getByRole('button', { name: 'Close', exact: true })
          .evaluate((button) => button.click());
      } else {
        const ideEditor = page.locator('textarea:visible').first();
        await ideEditor.fill(activity.code);
        await ideEditor.evaluate((element) => element.blur());
      }

      await page.getByRole('button', { name: 'Blocks', exact: true })
        .evaluate((button) => button.click());
      const workspace = page.locator('.blocklySvg').first();
      await expect(workspace).toBeVisible();
      await expect.poll(() => page.evaluate(
        () => window.Blockly?.getMainWorkspace()?.getAllBlocks(false).length || 0,
      )).toBe(expectedBlockCount);
      await page.evaluate(() => {
        const workspace = window.Blockly?.getMainWorkspace();
        if (!workspace) return;
        window.Blockly?.svgResize(workspace);
        workspace.zoomToFit(24);
        workspace.setScale(Math.min(workspace.scale, 1.35));
        workspace.scrollCenter();
      });
      await page.waitForTimeout(200);
      await captureBlocks(
        page,
        path.join(imageDirectory, `${activity.name}-blocks.png`),
      );

      await page.getByRole('button', { name: 'IDE', exact: true })
        .evaluate((button) => button.click());
      const ide = page.locator('textarea:visible').first();
      await expect(ide).toHaveValue(activity.code);
      await ide.evaluate((element) => {
        const lineCount = element.value.split('\n').length;
        element.style.height = `${Math.max(90, lineCount * 30 + 28)}px`;
        element.style.fontSize = '16px';
        element.style.lineHeight = '1.6';
        element.style.overflow = 'hidden';
      });
      await ide.evaluate((element) => element.scrollIntoView({ block: 'center' }));
      await captureElement(
        page,
        ide,
        path.join(imageDirectory, `${activity.name}-ide.png`),
      );
    }

    await context.close();
    console.log(`Captured ${activities.length * 2} real app screenshots for ${version}.`);
  }
} finally {
  await browser.close();
}

for (const version of ['legacy', 'duet']) {
  const entries = library.filter((entry) => entry.controller_version === version);
  for (const entry of entries) {
    for (const view of ['blocks', 'ide']) {
      await rm(
        path.join(root, 'motion_library', version, 'images', `${entry.name}-${view}.svg`),
        { force: true },
      );
    }
  }
}

execFileSync('python', ['tools/build_motion_bundles.py'], {
  cwd: root,
  stdio: 'inherit',
});
