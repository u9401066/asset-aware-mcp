import * as assert from 'assert';
import {
    checkOllamaModels,
    formatOllamaPullCommands,
    getMissingOllamaModels,
    getRequiredOllamaModelsForLightRag,
} from '../../ollama';

describe('ollama helpers', () => {
    it('reports missing configured models', () => {
        const missing = getMissingOllamaModels(
            ['mistral', 'granite3.3:8b'],
            ['granite4.1', 'nomic-embed-text'],
        );

        assert.deepStrictEqual(missing, ['granite4.1', 'nomic-embed-text']);
    });

    it('deduplicates and ignores blank required models', () => {
        const missing = getMissingOllamaModels(
            ['granite4.1'],
            ['granite4.1', ' ', undefined, 'granite4.1'],
        );

        assert.deepStrictEqual(missing, []);
    });

    it('formats pull commands for actionable setup guidance', () => {
        assert.strictEqual(
            formatOllamaPullCommands(['granite4.1', 'nomic-embed-text']),
            'ollama pull granite4.1\nollama pull nomic-embed-text',
        );
    });

    it('requires only the Granite LLM model when LightRAG is disabled', () => {
        assert.deepStrictEqual(
            getRequiredOllamaModelsForLightRag('granite4.1', 'nomic-embed-text', false),
            ['granite4.1'],
        );
    });

    it('requires the embedding model only when LightRAG is enabled', () => {
        assert.deepStrictEqual(
            getRequiredOllamaModelsForLightRag('granite4.1', 'nomic-embed-text', true),
            ['granite4.1', 'nomic-embed-text'],
        );
    });

    it('parses /api/tags model names', async () => {
        const originalFetch = globalThis.fetch;
        (globalThis as any).fetch = async () => ({
            ok: true,
            json: async () => ({ models: [{ name: 'granite4.1' }] }),
        });

        try {
            const status = await checkOllamaModels(
                'http://localhost:11434',
                ['granite4.1', 'nomic-embed-text'],
            );

            assert.strictEqual(status.connected, true);
            assert.deepStrictEqual(status.models, ['granite4.1']);
            assert.deepStrictEqual(status.missingModels, ['nomic-embed-text']);
        } finally {
            globalThis.fetch = originalFetch;
        }
    });
});
