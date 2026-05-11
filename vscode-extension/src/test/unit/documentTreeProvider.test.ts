import * as assert from 'assert';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import { DocumentTreeProvider } from '../../documentTreeProvider';
import { EnvManager } from '../../envManager';

describe('DocumentTreeProvider', () => {
    let tempDir: string;

    beforeEach(() => {
        tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'asset-aware-doc-tree-'));
        fs.writeFileSync(path.join(tempDir, 'pyproject.toml'), '[project]\nname = "asset-aware-mcp"\n');
    });

    afterEach(() => {
        fs.rmSync(tempDir, { recursive: true, force: true });
    });

    it('exposes artifact and citation groups for ingested documents', async () => {
        const manager = new EnvManager(tempDir);
        const docDir = path.join(manager.getDataDir(), 'doc_delta');
        fs.mkdirSync(docDir, { recursive: true });
        fs.writeFileSync(path.join(docDir, 'doc_delta_manifest.json'), '{"title":"Delta"}');
        fs.writeFileSync(path.join(docDir, 'citation_index.jsonl'), '{"span_id":"spn_delta","text":"Evidence"}\n');

        const provider = new DocumentTreeProvider(manager);
        const roots = await provider.getChildren();
        assert.strictEqual(roots.length, 1);

        const details = await provider.getChildren(roots[0] as any);
        const labels = details.map(item => String(item.label));

        assert.ok(labels.includes('Artifacts: 2'));
        assert.ok(labels.includes('Citations'));
    });
});
