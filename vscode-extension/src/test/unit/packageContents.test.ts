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
        assert.match(packageContentsSource, /forbiddenRootGeneratedMediaPattern/);
        assert.match(packageContentsSource, /node_modules/);
        assert.match(packageContentsSource, /__pycache__/);
        assert.match(packageContentsSource, /node_modules\/smol-toml\/dist\/index\.cjs/);
        assert.match(packageContentsSource, /unpackaged smol-toml module/);
        assert.match(vscodeIgnore, /^dist\/\*\*/m);
        assert.match(vscodeIgnore, /^tmp\/\*\*/m);
        assert.match(vscodeIgnore, /^\*\.png$/m);
        assert.match(vscodeIgnore, /^!resources\/\*\*\/\*\.png$/m);
    });

    it('uses a cross-platform Mocha glob for unit tests', () => {
        const packageJson = JSON.parse(
            fs.readFileSync(path.join(extensionRoot, 'package.json'), 'utf8')
        ) as { scripts: Record<string, string> };

        assert.strictEqual(
            packageJson.scripts['test:unit'],
            'npm run compile && mocha --require out/test/unit/setup.js "out/test/unit/**/*.test.js" --timeout 5000'
        );
    });
});
