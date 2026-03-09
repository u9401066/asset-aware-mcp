import * as assert from 'assert';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import { EnvManager } from '../../envManager';
import { DfmSessionManager, normalizeSessionPath } from '../../dfm/dfmEditorService';

describe('EnvManager', () => {
    let tempDir: string;

    beforeEach(() => {
        tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'asset-aware-env-'));
        fs.writeFileSync(path.join(tempDir, 'pyproject.toml'), '[project]\nname = "asset-aware-mcp"\n');
    });

    afterEach(() => {
        fs.rmSync(tempDir, { recursive: true, force: true });
    });

    it('finds current manifest naming scheme', () => {
        const manager = new EnvManager(tempDir);
        const docDir = path.join(manager.getDataDir(), 'doc_alpha');
        fs.mkdirSync(docDir, { recursive: true });
        fs.writeFileSync(path.join(docDir, 'doc_alpha_manifest.json'), '{"title":"Alpha"}');

        assert.strictEqual(manager.getManifestPath('doc_alpha'), path.join(docDir, 'doc_alpha_manifest.json'));
        assert.deepStrictEqual(manager.readManifest('doc_alpha'), { title: 'Alpha' });
    });

    it('falls back to legacy manifest naming scheme', () => {
        const manager = new EnvManager(tempDir);
        const docDir = path.join(manager.getDataDir(), 'doc_beta');
        fs.mkdirSync(docDir, { recursive: true });
        fs.writeFileSync(path.join(docDir, 'manifest.json'), '{"title":"Beta"}');

        assert.strictEqual(manager.getManifestPath('doc_beta'), path.join(docDir, 'manifest.json'));
        assert.deepStrictEqual(manager.readManifest('doc_beta'), { title: 'Beta' });
    });
});

describe('DfmSessionManager path normalization', () => {
    it('matches normalized docx paths', () => {
        const manager = new DfmSessionManager();
        const baseDir = path.join(os.tmpdir(), 'asset-aware-dfm');
        const docxPath = path.join(baseDir, 'docs', 'file.docx');
        const dfmPath = path.join(baseDir, 'data', 'content.dfm');

        manager.addSession({
            docId: 'doc_001',
            docxPath,
            dfmPath,
            dataDir: path.join(baseDir, 'data'),
            createdAt: Date.now(),
            dirty: false,
        });

        const lookupPath = path.join(baseDir, 'docs', '..', 'docs', 'file.docx');
        assert.ok(manager.getSessionByDocx(lookupPath));
        assert.ok(manager.getSessionByDfm(path.join(baseDir, 'data', '.', 'content.dfm')));
    });

    it('normalizes Windows path casing', () => {
        const normalized = normalizeSessionPath('C:/Users/Test/Documents/FILE.DOCX', 'win32');
        assert.strictEqual(normalized, path.win32.resolve('C:/Users/Test/Documents/FILE.DOCX').toLowerCase());
    });
});