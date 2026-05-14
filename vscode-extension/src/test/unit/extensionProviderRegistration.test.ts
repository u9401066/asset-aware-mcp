import * as assert from 'assert';
import * as vscode from 'vscode';
import {
    __registerMcpServerProviderForTests,
    __resetMcpServerProviderRegistrationForTests,
} from '../../extension';

describe('extension MCP provider registration', () => {
    afterEach(() => {
        __resetMcpServerProviderRegistrationForTests();
        delete (vscode.lm as any).registerMcpServerDefinitionProvider;
    });

    it('disposes the previous MCP provider registration before replacing it', () => {
        const disposed: string[] = [];
        const registrations: string[] = [];
        (vscode.lm as any).registerMcpServerDefinitionProvider = (
            id: string,
            provider: { token: string },
        ) => {
            registrations.push(`${id}:${provider.token}`);
            return {
                dispose: () => disposed.push(provider.token),
            };
        };
        const context = { subscriptions: [] } as any;

        const firstRegistered = __registerMcpServerProviderForTests(
            context,
            { token: 'first' } as any,
        );
        const secondRegistered = __registerMcpServerProviderForTests(
            context,
            { token: 'second' } as any,
        );

        assert.strictEqual(firstRegistered, true);
        assert.strictEqual(secondRegistered, true);
        assert.deepStrictEqual(registrations, [
            'asset-aware-mcp.servers:first',
            'asset-aware-mcp.servers:second',
        ]);
        assert.deepStrictEqual(disposed, ['first']);
        assert.strictEqual(context.subscriptions.length, 2);
    });
});
