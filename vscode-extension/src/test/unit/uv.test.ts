import * as assert from 'assert';
import {
    DEFAULT_TORCH_BACKEND,
    getAssetAwareRuntimeProbeArgs,
    getMarkerRuntimeArgs,
    getUvPaths,
    getUvRunArgs,
    getUvxLaunch,
    PREFERRED_RUNTIME_PYTHON,
} from '../../uv';

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
        assert.ok(paths.indexOf('C:\\Users\\alice\\AppData\\Local\\uv\\bin\\uv.exe') < paths.indexOf('uv'));
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
        assert.ok(paths.indexOf('/home/alice/.local/bin/uv') < paths.indexOf('uv'));
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

    it('builds uvx launch args with preferred python', () => {
        const launch = getUvxLaunch('uv');

        assert.strictEqual(launch.command, 'uvx');
        assert.deepStrictEqual(launch.args, ['--python', PREFERRED_RUNTIME_PYTHON]);
    });

    it('builds uv tool run launch args with preferred python', () => {
        const launch = getUvxLaunch('/usr/local/bin/uv');

        assert.strictEqual(launch.command, '/usr/local/bin/uv');
        assert.deepStrictEqual(launch.args, ['tool', 'run', '--python', PREFERRED_RUNTIME_PYTHON]);
    });

    it('builds uv run args with preferred python', () => {
        assert.deepStrictEqual(getUvRunArgs(), ['run', '--python', PREFERRED_RUNTIME_PYTHON]);
    });

    it('does not add the local marker extra while the marker backend is on security hold', () => {
        assert.deepStrictEqual(
            getUvRunArgs(PREFERRED_RUNTIME_PYTHON, true),
            ['run', '--python', PREFERRED_RUNTIME_PYTHON],
        );
    });

    it('does not build marker runtime args while the marker backend is on security hold', () => {
        assert.deepStrictEqual(getMarkerRuntimeArgs(DEFAULT_TORCH_BACKEND), []);
    });

    it('omits marker runtime args from uvx launch while the marker backend is on security hold', () => {
        const launch = getUvxLaunch('uv', PREFERRED_RUNTIME_PYTHON, true, 'cpu');

        assert.deepStrictEqual(launch.args, ['--python', PREFERRED_RUNTIME_PYTHON]);
    });

    it('pins server version with --from when serverVersion provided', () => {
        const launch = getUvxLaunch('uv', PREFERRED_RUNTIME_PYTHON, false, 'cpu', '0.6.19');

        assert.deepStrictEqual(launch.args, ['--python', PREFERRED_RUNTIME_PYTHON, '--from', 'asset-aware-mcp==0.6.19']);
    });

    it('adds --upgrade flag when upgrade is true', () => {
        const launch = getUvxLaunch('uv', PREFERRED_RUNTIME_PYTHON, false, 'cpu', '0.6.19', true);

        assert.ok(launch.args.includes('--upgrade'));
        assert.ok(launch.args.includes('--from'));
        assert.ok(launch.args.includes('asset-aware-mcp==0.6.19'));
    });

    it('combines version pin and upgrade without marker args while the marker backend is on security hold', () => {
        const launch = getUvxLaunch('/usr/bin/uv', PREFERRED_RUNTIME_PYTHON, true, 'cpu', '0.5.3', true);

        assert.strictEqual(launch.command, '/usr/bin/uv');
        assert.deepStrictEqual(launch.args, [
            'tool', 'run', '--python', PREFERRED_RUNTIME_PYTHON,
            '--upgrade', '--from', 'asset-aware-mcp==0.5.3',
        ]);
    });

    it('builds a runtime probe command that exits after importing the MCP server', () => {
        const launch = getUvxLaunch('/usr/bin/uv', PREFERRED_RUNTIME_PYTHON, false, 'cpu', '0.6.19');
        const args = getAssetAwareRuntimeProbeArgs(launch.args);

        assert.deepStrictEqual(args.slice(0, launch.args.length), launch.args);
        assert.deepStrictEqual(args.slice(-3, -1), ['python', '-c']);
        assert.ok(args[args.length - 1].includes('src.presentation.server'));
    });
});
