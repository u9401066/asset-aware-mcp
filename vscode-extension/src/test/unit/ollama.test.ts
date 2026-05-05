import * as assert from 'assert';
import {
    checkOllamaModels,
    formatOllamaPullCommands,
    getMissingOllamaModels,
} from '../../ollama';

describe('ollama helpers', () => {
    it('reports missing configured models', () => {
        const missing = getMissingOllamaModels(
            ['qwen2.5:3b', 'llama3.1:8b'],
            ['qwen2.5:7b', 'nomic-embed-text'],
        );

        assert.deepStrictEqual(missing, ['qwen2.5:7b', 'nomic-embed-text']);
    });

    it('deduplicates and ignores blank required models', () => {
        const missing = getMissingOllamaModels(
            ['qwen2.5:7b'],
            ['qwen2.5:7b', ' ', undefined, 'qwen2.5:7b'],
        );

        assert.deepStrictEqual(missing, []);
    });

    it('formats pull commands for actionable setup guidance', () => {
        assert.strictEqual(
            formatOllamaPullCommands(['qwen2.5:7b', 'nomic-embed-text']),
            'ollama pull qwen2.5:7b\nollama pull nomic-embed-text',
        );
    });

    it('parses /api/tags model names', async () => {
        const originalFetch = globalThis.fetch;
        (globalThis as any).fetch = async () => ({
            ok: true,
            json: async () => ({ models: [{ name: 'qwen2.5:3b' }] }),
        });

        try {
            const status = await checkOllamaModels(
                'http://localhost:11434',
                ['qwen2.5:3b', 'nomic-embed-text'],
            );

            assert.strictEqual(status.connected, true);
            assert.deepStrictEqual(status.models, ['qwen2.5:3b']);
            assert.deepStrictEqual(status.missingModels, ['nomic-embed-text']);
        } finally {
            globalThis.fetch = originalFetch;
        }
    });
});
