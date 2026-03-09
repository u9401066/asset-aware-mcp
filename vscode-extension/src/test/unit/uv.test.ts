import * as assert from 'assert';
import { getUvPaths } from '../../uv';

describe('uv path discovery', () => {
    it('includes common Windows install locations', () => {
        const paths = getUvPaths('win32', {
            USERPROFILE: 'C:\\Users\\alice',
            LOCALAPPDATA: 'C:\\Users\\alice\\AppData\\Local',
            CARGO_HOME: 'C:\\Users\\alice\\.cargo',
        });

        assert.ok(paths.includes('uv'));
        assert.ok(paths.includes('C:\\Users\\alice\\AppData\\Local\\uv\\bin\\uv.exe'));
        assert.ok(paths.includes('C:\\Users\\alice\\scoop\\shims\\uv.exe'));
        assert.ok(paths.includes('C:\\ProgramData\\chocolatey\\bin\\uv.exe'));
    });

    it('includes common Linux install locations', () => {
        const paths = getUvPaths('linux', {
            HOME: '/home/alice',
            CARGO_HOME: '/home/alice/.cargo',
        });

        assert.ok(paths.includes('uv'));
        assert.ok(paths.includes('/home/alice/.local/bin/uv'));
        assert.ok(paths.includes('/home/alice/.cargo/bin/uv'));
        assert.ok(paths.includes('/home/linuxbrew/.linuxbrew/bin/uv'));
        assert.ok(paths.includes('/snap/bin/uv'));
    });

    it('includes common macOS install locations', () => {
        const paths = getUvPaths('darwin', {
            HOME: '/Users/alice',
            CARGO_HOME: '/Users/alice/.cargo',
        });

        assert.ok(paths.includes('uv'));
        assert.ok(paths.includes('/Users/alice/.local/bin/uv'));
        assert.ok(paths.includes('/opt/homebrew/bin/uv'));
        assert.ok(paths.includes('/opt/local/bin/uv'));
    });
});