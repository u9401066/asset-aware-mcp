/**
 * Mocha root hook — register vscode mock before any imports.
 *
 * Usage: mocha --require out/test/unit/setup.js
 */

// eslint-disable-next-line @typescript-eslint/no-require-imports
const Module = require('module');
// eslint-disable-next-line @typescript-eslint/no-require-imports
const path = require('path');

const originalResolve = Module._resolveFilename;

Module._resolveFilename = function (request: string, parent: any, isMain: boolean, options: any) {
    if (request === 'vscode') {
        return path.resolve(__dirname, 'mock-vscode.js');
    }
    return originalResolve.call(this, request, parent, isMain, options);
};
