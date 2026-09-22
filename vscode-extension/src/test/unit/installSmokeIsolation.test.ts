import * as assert from 'assert';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import {
    isolatedExtensionDirectory,
    supportsIsolatedInstall,
    verifyInstalledAssistantAssets,
} from '../installSmokeIsolation';

describe('isolated VSIX installation evidence', () => {
    let root: string;
    const id = 'u9401066.asset-aware-mcp';
    const help = 'Options:\n  --user-data-dir <dir>\n  --extensions-dir <dir>\n';
    const assets = [
        'AGENTS.md',
        '.github/copilot-instructions.md',
        '.github/agents/asset-aware-document.agent.md',
        '.codex/skills/asset-aware-mcp-harness/SKILL.md',
        '.cline/skills/asset-aware-mcp-harness/SKILL.md',
    ];

    function write(relative: string, text: string = ''): string {
        const target = path.join(root, relative);
        fs.mkdirSync(path.dirname(target), { recursive: true });
        fs.writeFileSync(target, text);
        return target;
    }

    beforeEach(() => {
        root = fs.mkdtempSync(path.join(os.tmpdir(), 'asset-aware-smoke-isolation-'));
    });

    afterEach(() => {
        fs.rmSync(root, { recursive: true, force: true });
    });

    it('rejects a remote terminal launcher before invoking it', async () => {
        const remote = write('server/bin/remote-cli/code-insiders');
        let invoked = false;
        assert.strictEqual(await supportsIsolatedInstall(remote, async () => {
            invoked = true;
            return help;
        }), false);
        assert.strictEqual(invoked, false);
    });

    it('rejects aliases that resolve to a remote terminal launcher', async () => {
        write('remote-cli/code');
        fs.symlinkSync(path.join(root, 'remote-cli'), path.join(root, 'alias'), 'junction');
        let invoked = false;
        assert.strictEqual(await supportsIsolatedInstall(path.join(root, 'alias/code'), async () => {
            invoked = true;
            return help;
        }), false);
        assert.strictEqual(invoked, false);
    });

    it('requires both isolation options from a usable local CLI', async () => {
        const local = write('desktop/bin/code');
        assert.strictEqual(await supportsIsolatedInstall(local, async () => help), true);
        assert.strictEqual(await supportsIsolatedInstall(local, async () => '--extensions-dir <dir>'), false);
        assert.strictEqual(await supportsIsolatedInstall(local, async () => '--user-data-dir <dir>'), false);
        assert.strictEqual(await supportsIsolatedInstall(local, async () => {
            throw new Error('CLI cannot start');
        }), false);
        assert.strictEqual(await supportsIsolatedInstall(path.join(root, 'missing'), async () => help), false);
    });

    it('rejects a reported installation with no files in the isolated directory', () => {
        assert.throws(() => isolatedExtensionDirectory(root, id, '1.4.0'), /found 0/);
    });

    it('requires the requested manifest identity and version inside that directory', () => {
        const manifest = write(`${id}-1.4.0/package.json`, JSON.stringify({
            publisher: 'u9401066', name: 'asset-aware-mcp', version: '1.3.0',
        }));
        assert.throws(() => isolatedExtensionDirectory(root, id, '1.4.0'), /found 0/);
        fs.writeFileSync(manifest, JSON.stringify({
            publisher: 'another', name: 'asset-aware-mcp', version: '1.4.0',
        }));
        assert.throws(() => isolatedExtensionDirectory(root, id, '1.4.0'), /found 0/);
        fs.writeFileSync(manifest, JSON.stringify({
            publisher: 'u9401066', name: 'asset-aware-mcp', version: '1.4.0',
        }));
        assert.strictEqual(isolatedExtensionDirectory(root, id, '1.4.0'), path.dirname(manifest));
    });

    it('checks installed guide bytes, including stale same-version updates', () => {
        for (const asset of assets) {
            write(`source/resources/repo-assets/asset-aware/${asset}`, `current ${asset}\n`);
            write(`installed/resources/repo-assets/asset-aware/${asset}`, `current ${asset}\n`);
        }
        const installed = path.join(root, 'installed');
        const source = path.join(root, 'source');
        verifyInstalledAssistantAssets(installed, source);
        write('installed/resources/repo-assets/asset-aware/AGENTS.md', 'old guide\n');
        assert.throws(() => verifyInstalledAssistantAssets(installed, source), /differs.*AGENTS.md/);
        fs.unlinkSync(path.join(installed, 'resources/repo-assets/asset-aware/AGENTS.md'));
        assert.throws(() => verifyInstalledAssistantAssets(installed, source), /ENOENT/);
    });
});
