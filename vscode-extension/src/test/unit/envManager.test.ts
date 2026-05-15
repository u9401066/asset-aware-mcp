import * as assert from 'assert';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import { EnvManager } from '../../envManager';
import { DfmSessionManager, normalizeSessionPath } from '../../dfm/dfmEditorService';

describe('EnvManager', () => {
    let tempDir: string;
    let originalAssetAwareHasGpu: string | undefined;
    let originalAssetAwareUseGpu: string | undefined;
    let originalAssetAwareGpu: string | undefined;
    let originalNvidiaVisibleDevices: string | undefined;
    let originalCudaVisibleDevices: string | undefined;

    beforeEach(() => {
        tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'asset-aware-env-'));
        fs.writeFileSync(path.join(tempDir, 'pyproject.toml'), '[project]\nname = "asset-aware-mcp"\n');
        originalAssetAwareHasGpu = process.env.ASSET_AWARE_HAS_GPU;
        originalAssetAwareUseGpu = process.env.ASSET_AWARE_USE_GPU;
        originalAssetAwareGpu = process.env.ASSET_AWARE_GPU;
        originalNvidiaVisibleDevices = process.env.NVIDIA_VISIBLE_DEVICES;
        originalCudaVisibleDevices = process.env.CUDA_VISIBLE_DEVICES;
        delete process.env.ASSET_AWARE_HAS_GPU;
        delete process.env.ASSET_AWARE_USE_GPU;
        delete process.env.ASSET_AWARE_GPU;
        delete process.env.NVIDIA_VISIBLE_DEVICES;
        delete process.env.CUDA_VISIBLE_DEVICES;
    });

    afterEach(() => {
        fs.rmSync(tempDir, { recursive: true, force: true });
        restoreEnv('ASSET_AWARE_HAS_GPU', originalAssetAwareHasGpu);
        restoreEnv('ASSET_AWARE_USE_GPU', originalAssetAwareUseGpu);
        restoreEnv('ASSET_AWARE_GPU', originalAssetAwareGpu);
        restoreEnv('NVIDIA_VISIBLE_DEVICES', originalNvidiaVisibleDevices);
        restoreEnv('CUDA_VISIBLE_DEVICES', originalCudaVisibleDevices);
    });

    function restoreEnv(key: string, value: string | undefined): void {
        if (value === undefined) {
            delete process.env[key];
        } else {
            process.env[key] = value;
        }
    }

    it('writes the CPU-friendly Granite model in a new default env', async () => {
        const manager = new EnvManager(tempDir);

        await manager.createDefaultEnv();

        const content = fs.readFileSync(path.join(tempDir, '.env'), 'utf8');
        assert.ok(content.includes('OLLAMA_MODEL=granite4.1:3b'));
        const env = await manager.readEnv();
        assert.strictEqual(env.OLLAMA_MODEL, 'granite4.1:3b');
        assert.strictEqual(env.ENABLE_LIGHTRAG, 'false');
    });

    it('writes the 8b Granite model in a new default env when GPU hint is enabled', async () => {
        process.env.ASSET_AWARE_HAS_GPU = 'true';
        const manager = new EnvManager(tempDir);

        await manager.createDefaultEnv();

        const content = fs.readFileSync(path.join(tempDir, '.env'), 'utf8');
        assert.ok(content.includes('OLLAMA_MODEL=granite4.1:8b'));
        const env = await manager.readEnv();
        assert.strictEqual(env.OLLAMA_MODEL, 'granite4.1:8b');
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

    it('persists the canonical LightRAG embedding model key', async () => {
        const manager = new EnvManager(tempDir);

        await manager.updateEnv('LIGHTRAG_EMBEDDING_MODEL', 'text-embedding-3-large');

        const content = fs.readFileSync(path.join(tempDir, '.env'), 'utf8');
        assert.ok(content.includes('LIGHTRAG_EMBEDDING_MODEL=text-embedding-3-large'));
        assert.strictEqual(content.includes('OPENAI_EMBEDDING_MODEL='), false);

        const env = await manager.readEnv();
        assert.strictEqual(env.LIGHTRAG_EMBEDDING_MODEL, 'text-embedding-3-large');
        assert.strictEqual(env.OPENAI_EMBEDDING_MODEL, 'text-embedding-3-large');
    });

    it('maps legacy OpenAI embedding env key into LightRAG canonical key', async () => {
        fs.writeFileSync(path.join(tempDir, '.env'), 'OPENAI_EMBEDDING_MODEL=text-embedding-legacy\n');
        const manager = new EnvManager(tempDir);

        const env = await manager.readEnv();

        assert.strictEqual(env.LIGHTRAG_EMBEDDING_MODEL, 'text-embedding-legacy');
        assert.strictEqual(env.OPENAI_EMBEDDING_MODEL, 'text-embedding-legacy');
    });

    it('lists document artifacts and citation span summaries', () => {
        const manager = new EnvManager(tempDir);
        const docDir = path.join(manager.getDataDir(), 'doc_gamma');
        fs.mkdirSync(docDir, { recursive: true });
        fs.writeFileSync(path.join(docDir, 'doc_gamma_manifest.json'), '{"title":"Gamma"}');
        fs.writeFileSync(path.join(docDir, 'doc_gamma_full.md'), '# Gamma\n');
        fs.writeFileSync(path.join(docDir, 'citation_index.status.json'), '{"found":1}');
        fs.writeFileSync(
            path.join(docDir, 'citation_index.jsonl'),
            JSON.stringify({
                span_id: 'spn_1',
                page: 2,
                line_start: 4,
                line_end: 5,
                text: 'Gamma evidence',
            }) + '\n',
        );

        const artifacts = manager.listDocumentArtifacts('doc_gamma');
        assert.ok(artifacts.some(artifact => artifact.id === 'manifest'));
        assert.ok(artifacts.some(artifact => artifact.id === 'markdown'));
        assert.ok(artifacts.some(artifact => artifact.id === 'citation-index'));

        const spans = manager.listCitationSpans('doc_gamma');
        assert.strictEqual(spans.length, 1);
        assert.strictEqual(spans[0].spanId, 'spn_1');
        assert.match(spans[0].description, /p\.2 L5-5/);
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
