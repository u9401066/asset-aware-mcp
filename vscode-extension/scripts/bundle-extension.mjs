import { build } from 'esbuild';
import { rename, rm } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const extensionRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const entryPoint = path.join(extensionRoot, 'out', 'extension.js');
const bundledOutput = path.join(extensionRoot, 'out', 'extension.bundle.cjs');

try {
    await build({
        entryPoints: [entryPoint],
        outfile: bundledOutput,
        bundle: true,
        platform: 'node',
        format: 'cjs',
        target: 'node18',
        external: ['vscode'],
        legalComments: 'inline',
        logLevel: 'warning',
    });
    await rename(bundledOutput, entryPoint);
} finally {
    await rm(bundledOutput, { force: true });
}
