import * as assert from 'assert';
import * as fs from 'fs';
import * as path from 'path';

const extensionRoot = path.resolve(__dirname, '../../..');

describe('install smoke quality selector', () => {
    it('can target VS Code Insiders explicitly', () => {
        const installSmokeSource = fs.readFileSync(
            path.join(extensionRoot, 'src', 'test', 'installSmoke.ts'),
            'utf8',
        );

        assert.match(installSmokeSource, /ASSET_AWARE_MCP_VSCODE_QUALITY/);
        assert.match(installSmokeSource, /--vscode-quality/);
        assert.match(installSmokeSource, /downloadAndUnzipVSCode\(vscodeQuality\)/);
        assert.match(installSmokeSource, /code-insiders\.cmd/);
    });
});
