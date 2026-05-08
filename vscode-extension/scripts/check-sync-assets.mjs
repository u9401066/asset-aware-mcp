import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const extensionRoot = path.resolve(scriptDir, '..');
const repoRoot = path.resolve(extensionRoot, '..');
const assetRoot = path.join(extensionRoot, 'resources', 'repo-assets', 'asset-aware');
const syncScript = path.join(scriptDir, 'sync-assistant-assets.mjs');
const textExtensions = new Set(['.md', '.json', '.toml', '.sh', '.ps1']);

function assertNoReplacementCharacters(filePath, content) {
    if (content.includes('\uFFFD')) {
        throw new Error(
            `Text asset contains Unicode replacement character U+FFFD: ${filePath}. ` +
            'Run sync-assets from correctly encoded UTF-8 sources.',
        );
    }
}

function normalizedContent(filePath) {
    const raw = fs.readFileSync(filePath);
    let content = raw[0] === 0xef && raw[1] === 0xbb && raw[2] === 0xbf
        ? raw.subarray(3)
        : raw;

    if (textExtensions.has(path.extname(filePath).toLowerCase())) {
        const text = content.toString('utf8').replace(/\r\n/g, '\n');
        assertNoReplacementCharacters(filePath, text);
        content = Buffer.from(text, 'utf8');
    }

    return content;
}

function snapshotDirectory(root) {
    const snapshot = new Map();

    function walk(dir) {
        if (!fs.existsSync(dir)) {
            return;
        }

        const entries = fs.readdirSync(dir, { withFileTypes: true })
            .sort((a, b) => a.name.localeCompare(b.name));

        for (const entry of entries) {
            const fullPath = path.join(dir, entry.name);
            if (entry.isDirectory()) {
                walk(fullPath);
                continue;
            }
            if (!entry.isFile()) {
                continue;
            }

            const relativePath = path.relative(root, fullPath).replaceAll(path.sep, '/');
            const digest = createHash('sha256').update(normalizedContent(fullPath)).digest('hex');
            snapshot.set(relativePath, digest);
        }
    }

    walk(root);
    return snapshot;
}

function diffSnapshots(before, after) {
    const changes = [];
    const paths = new Set([...before.keys(), ...after.keys()]);

    for (const relativePath of [...paths].sort()) {
        if (!before.has(relativePath)) {
            changes.push(`added ${relativePath}`);
        } else if (!after.has(relativePath)) {
            changes.push(`removed ${relativePath}`);
        } else if (before.get(relativePath) !== after.get(relativePath)) {
            changes.push(`changed ${relativePath}`);
        }
    }

    return changes;
}

const expectedRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'asset-aware-assets-check-'));
const expectedAssetRoot = path.join(expectedRoot, 'asset-aware');

let changes;
try {
    execFileSync(process.execPath, [syncScript], {
        cwd: extensionRoot,
        stdio: 'inherit',
        env: {
            ...process.env,
            ASSET_AWARE_REPO_ROOT: repoRoot,
            ASSET_AWARE_EXTENSION_ROOT: extensionRoot,
            ASSET_AWARE_ASSET_ROOT: expectedAssetRoot,
        },
    });
    changes = diffSnapshots(snapshotDirectory(assetRoot), snapshotDirectory(expectedAssetRoot));
} finally {
    fs.rmSync(expectedRoot, { recursive: true, force: true });
}

if (changes.length > 0) {
    console.error('Assistant assets are not synchronized with their source files.');
    for (const change of changes.slice(0, 50)) {
        console.error(`- ${change}`);
    }
    if (changes.length > 50) {
        console.error(`...and ${changes.length - 50} more`);
    }
    process.exit(1);
}

console.log('Assistant assets are synchronized.');
