import * as assert from 'assert';
import * as fs from 'fs';
import * as path from 'path';

const extensionRoot = path.resolve(__dirname, '../../..');

describe('package contents guard', () => {
    it('rejects generated dist and tmp directories from VSIX packages', () => {
        const packageContentsSource = fs.readFileSync(
            path.join(extensionRoot, 'src', 'test', 'packageContents.ts'),
            'utf8'
        );
        const vscodeIgnore = fs.readFileSync(
            path.join(extensionRoot, '.vscodeignore'),
            'utf8'
        );

        assert.match(packageContentsSource, /'dist\/'/);
        assert.match(packageContentsSource, /'tmp\/'/);
        assert.match(packageContentsSource, /forbiddenRepoAssetGeneratedDirPattern/);
        assert.match(packageContentsSource, /node_modules/);
        assert.match(packageContentsSource, /__pycache__/);
        assert.match(vscodeIgnore, /^dist\/\*\*/m);
        assert.match(vscodeIgnore, /^tmp\/\*\*/m);
    });
});
