/**
 * DFM Unit Tests
 *
 * Pure mocha tests — no VS Code host required.
 * Tests DfmSessionManager, DFM_PATTERNS, computeFoldingRanges, computeDecorations.
 *
 * Run: npx mocha out/test/unit/dfm.test.js
 */

import * as assert from 'assert';
import { DfmSessionManager, DfmSession } from '../../dfm/dfmEditorService';
import {
    DFM_PATTERNS,
    computeFoldingRanges,
    computeDecorations,
} from '../../dfm/dfmLanguageFeatures';

// ── Mock helpers ──────────────────────────────────────────────

/** Create a fake document from lines (for pure-function tests) */
function mockDocument(lines: string[]): { lineCount: number; lineAt(i: number): { text: string } } {
    return {
        lineCount: lines.length,
        lineAt(i: number) {
            return { text: lines[i] };
        },
    };
}

function makeSession(overrides: Partial<DfmSession> = {}): DfmSession {
    return {
        docId: overrides.docId ?? 'doc_001',
        docxPath: overrides.docxPath ?? '/path/to/test.docx',
        dfmPath: overrides.dfmPath ?? '/path/to/data/content.dfm',
        dataDir: overrides.dataDir ?? '/path/to/data',
        createdAt: overrides.createdAt ?? Date.now(),
        dirty: overrides.dirty ?? false,
    };
}

// ── DfmSessionManager Tests ──────────────────────────────────

describe('DfmSessionManager', () => {
    let manager: DfmSessionManager;

    beforeEach(() => {
        manager = new DfmSessionManager();
    });

    describe('addSession / getSession', () => {
        it('should add and retrieve by dfmPath', () => {
            const session = makeSession();
            manager.addSession(session);
            assert.strictEqual(manager.getSessionByDfm(session.dfmPath), session);
        });

        it('should retrieve by docId', () => {
            const session = makeSession({ docId: 'unique_id' });
            manager.addSession(session);
            assert.strictEqual(manager.getSessionByDocId('unique_id'), session);
        });

        it('should retrieve by docxPath', () => {
            const session = makeSession({ docxPath: '/my/file.docx' });
            manager.addSession(session);
            assert.strictEqual(manager.getSessionByDocx('/my/file.docx'), session);
        });

        it('should return undefined for unknown paths', () => {
            assert.strictEqual(manager.getSessionByDfm('/nonexistent'), undefined);
            assert.strictEqual(manager.getSessionByDocId('nope'), undefined);
            assert.strictEqual(manager.getSessionByDocx('/nope.docx'), undefined);
        });
    });

    describe('removeSession', () => {
        it('should remove a session', () => {
            const session = makeSession();
            manager.addSession(session);
            assert.strictEqual(manager.removeSession(session.dfmPath), true);
            assert.strictEqual(manager.getSessionByDfm(session.dfmPath), undefined);
        });

        it('should return false for unknown path', () => {
            assert.strictEqual(manager.removeSession('/ghost'), false);
        });
    });

    describe('setDirty', () => {
        it('should mark session as dirty', () => {
            const session = makeSession({ dirty: false });
            manager.addSession(session);
            manager.setDirty(session.dfmPath, true);
            assert.strictEqual(manager.getSessionByDfm(session.dfmPath)!.dirty, true);
        });

        it('should mark session as clean', () => {
            const session = makeSession({ dirty: true });
            manager.addSession(session);
            manager.setDirty(session.dfmPath, false);
            assert.strictEqual(manager.getSessionByDfm(session.dfmPath)!.dirty, false);
        });

        it('should do nothing for unknown path', () => {
            // Should not throw
            manager.setDirty('/unknown', true);
        });
    });

    describe('getAllSessions', () => {
        it('should return all sessions', () => {
            manager.addSession(makeSession({ dfmPath: '/a.dfm', docId: 'a' }));
            manager.addSession(makeSession({ dfmPath: '/b.dfm', docId: 'b' }));
            assert.strictEqual(manager.getAllSessions().length, 2);
        });

        it('should return empty array initially', () => {
            assert.deepStrictEqual(manager.getAllSessions(), []);
        });
    });

    describe('isDfmTracked', () => {
        it('should return true for tracked files', () => {
            const session = makeSession();
            manager.addSession(session);
            assert.strictEqual(manager.isDfmTracked(session.dfmPath), true);
        });

        it('should return false for untracked files', () => {
            assert.strictEqual(manager.isDfmTracked('/random.md'), false);
        });
    });

    describe('size', () => {
        it('should reflect session count', () => {
            assert.strictEqual(manager.size, 0);
            manager.addSession(makeSession({ dfmPath: '/a.dfm' }));
            assert.strictEqual(manager.size, 1);
            manager.addSession(makeSession({ dfmPath: '/b.dfm' }));
            assert.strictEqual(manager.size, 2);
            manager.removeSession('/a.dfm');
            assert.strictEqual(manager.size, 1);
        });
    });

    describe('multiple sessions', () => {
        it('should handle multiple independent sessions', () => {
            const s1 = makeSession({ dfmPath: '/s1.dfm', docId: 'id1', docxPath: '/doc1.docx' });
            const s2 = makeSession({ dfmPath: '/s2.dfm', docId: 'id2', docxPath: '/doc2.docx' });

            manager.addSession(s1);
            manager.addSession(s2);

            assert.strictEqual(manager.getSessionByDocId('id1'), s1);
            assert.strictEqual(manager.getSessionByDocId('id2'), s2);
            assert.strictEqual(manager.getSessionByDocx('/doc1.docx'), s1);
            assert.strictEqual(manager.getSessionByDocx('/doc2.docx'), s2);
        });
    });
});

// ── DFM Pattern Tests ────────────────────────────────────────

describe('DFM_PATTERNS', () => {
    describe('compoundOpen', () => {
        it('should match opening compound tags', () => {
            const m = DFM_PATTERNS.compoundOpen.exec('<!-- dfm:table @b:t001 -->');
            assert.ok(m);
            assert.strictEqual(m[1], 'table');
            assert.strictEqual(m[2], 't001');
        });

        it('should match with YAML content', () => {
            const m = DFM_PATTERNS.compoundOpen.exec('<!-- dfm:format @b:f001');
            assert.ok(m);
            assert.strictEqual(m[1], 'format');
            assert.strictEqual(m[2], 'f001');
        });

        it('should not match simple blocks', () => {
            const m = DFM_PATTERNS.compoundOpen.exec('<!-- @b:p001 -->');
            assert.strictEqual(m, null);
        });
    });

    describe('compoundClose', () => {
        it('should match closing tags', () => {
            const m = DFM_PATTERNS.compoundClose.exec('<!-- /dfm:table -->');
            assert.ok(m);
            assert.strictEqual(m[1], 'table');
        });

        it('should not match opening tags', () => {
            const m = DFM_PATTERNS.compoundClose.exec('<!-- dfm:table @b:t001 -->');
            assert.strictEqual(m, null);
        });
    });

    describe('simpleBlock', () => {
        it('should match simple block annotations', () => {
            const m = DFM_PATTERNS.simpleBlock.exec('<!-- @b:p001 -->');
            assert.ok(m);
            assert.strictEqual(m[1], 'p001');
        });

        it('should match with extra attributes', () => {
            const m = DFM_PATTERNS.simpleBlock.exec('<!-- @b:h001 style:Heading1 -->');
            assert.ok(m);
            assert.strictEqual(m[1], 'h001');
        });
    });

    describe('bookmark', () => {
        it('should match bookmark markers', () => {
            const m = DFM_PATTERNS.bookmark.exec('<!-- dfm:bookmark @b:bm001 -->');
            assert.ok(m);
            assert.strictEqual(m[1], 'bm001');
        });
    });

    describe('protectedTypes', () => {
        it('should classify protected types', () => {
            assert.strictEqual(DFM_PATTERNS.protectedTypes.has('chart'), true);
            assert.strictEqual(DFM_PATTERNS.protectedTypes.has('toc'), true);
            assert.strictEqual(DFM_PATTERNS.protectedTypes.has('header'), true);
            assert.strictEqual(DFM_PATTERNS.protectedTypes.has('footer'), true);
            assert.strictEqual(DFM_PATTERNS.protectedTypes.has('macro'), true);
        });

        it('should not classify editable types as protected', () => {
            assert.strictEqual(DFM_PATTERNS.protectedTypes.has('table'), false);
            assert.strictEqual(DFM_PATTERNS.protectedTypes.has('format'), false);
            assert.strictEqual(DFM_PATTERNS.protectedTypes.has('image'), false);
        });
    });

    describe('editableTypes', () => {
        it('should classify editable compound types', () => {
            assert.strictEqual(DFM_PATTERNS.editableTypes.has('table'), true);
            assert.strictEqual(DFM_PATTERNS.editableTypes.has('format'), true);
            assert.strictEqual(DFM_PATTERNS.editableTypes.has('image'), true);
        });
    });
});

// ── computeFoldingRanges Tests ───────────────────────────────

// vscode.FoldingRange is provided by mock-vscode

// Monkey-patch for tests (the function uses vscode.FoldingRange)
// We need to ensure the module can import vscode
// In the test environment, vscode is mocked globally

describe('computeFoldingRanges', () => {
    it('should fold frontmatter', () => {
        const doc = mockDocument([
            '---',
            'dfm_version: "1.0"',
            'doc_id: test',
            '---',
            '',
            '# Content',
        ]);
        const ranges = computeFoldingRanges(doc);
        assert.ok(ranges.length >= 1);
        const frontmatter = ranges.find(r => r.start === 0 && r.end === 3);
        assert.ok(frontmatter, 'Should fold frontmatter block');
    });

    it('should fold compound blocks', () => {
        const doc = mockDocument([
            '<!-- dfm:table @b:t001 -->',
            '| A | B |',
            '|---|---|',
            '| 1 | 2 |',
            '<!-- /dfm:table -->',
        ]);
        const ranges = computeFoldingRanges(doc);
        assert.ok(ranges.length >= 1);
        const tableRange = ranges.find(r => r.start === 0 && r.end === 4);
        assert.ok(tableRange, 'Should fold table block');
    });

    it('should handle nested compound blocks', () => {
        const doc = mockDocument([
            '<!-- dfm:format @b:f001',
            'runs:',
            '  - text: hello',
            '-->',
            'hello world',
            '<!-- /dfm:format -->',
        ]);
        const ranges = computeFoldingRanges(doc);
        assert.ok(ranges.length >= 1);
    });

    it('should return empty for plain markdown', () => {
        const doc = mockDocument([
            '# Heading',
            '',
            'Just a paragraph.',
        ]);
        const ranges = computeFoldingRanges(doc);
        assert.strictEqual(ranges.length, 0);
    });
});

// ── computeDecorations Tests ─────────────────────────────────

describe('computeDecorations', () => {
    it('should detect simple block annotations', () => {
        const doc = mockDocument([
            '<!-- @b:p001 -->',
            'Hello world',
        ]);
        const result = computeDecorations(doc);
        assert.strictEqual(result.annotationLines.length, 1);
        assert.strictEqual(result.annotationLines[0], 0);
        assert.strictEqual(result.blockIdLines.length, 1);
    });

    it('should detect protected compound blocks', () => {
        const doc = mockDocument([
            '<!-- dfm:chart @b:c001 -->',
            '📊 Embedded chart',
            '<!-- /dfm:chart -->',
        ]);
        const result = computeDecorations(doc);
        assert.strictEqual(result.protectedRanges.length, 1);
        assert.strictEqual(result.protectedRanges[0].start, 0);
        assert.strictEqual(result.protectedRanges[0].end, 2);
    });

    it('should NOT mark editable types as protected', () => {
        const doc = mockDocument([
            '<!-- dfm:table @b:t001 -->',
            '| A | B |',
            '<!-- /dfm:table -->',
        ]);
        const result = computeDecorations(doc);
        assert.strictEqual(result.protectedRanges.length, 0);
    });

    it('should detect bookmark as protected', () => {
        const doc = mockDocument([
            '<!-- dfm:bookmark @b:bm001 -->',
        ]);
        const result = computeDecorations(doc);
        assert.strictEqual(result.protectedRanges.length, 1);
        assert.strictEqual(result.protectedRanges[0].start, 0);
        assert.strictEqual(result.protectedRanges[0].end, 0);
    });

    it('should detect break as protected', () => {
        const doc = mockDocument([
            '<!-- dfm:break @b:br001 type:page -->',
        ]);
        const result = computeDecorations(doc);
        assert.strictEqual(result.protectedRanges.length, 1);
    });

    it('should handle mixed editable and protected blocks', () => {
        const doc = mockDocument([
            '<!-- @b:p001 -->',
            'Editable paragraph',
            '',
            '<!-- dfm:toc @b:toc001 -->',
            'Table of Contents (auto)',
            '<!-- /dfm:toc -->',
            '',
            '<!-- dfm:table @b:t001 -->',
            '| Col | Val |',
            '<!-- /dfm:table -->',
        ]);
        const result = computeDecorations(doc);

        // TOC is protected, table is not
        assert.strictEqual(result.protectedRanges.length, 1);
        assert.strictEqual(result.protectedRanges[0].start, 3);
        assert.strictEqual(result.protectedRanges[0].end, 5);

        // Annotations: line 0 (simpleBlock), 3 (toc open), 5 (toc close), 7 (table open), 9 (table close)
        assert.ok(result.annotationLines.length >= 3);
    });

    it('should return empty for plain content', () => {
        const doc = mockDocument([
            '# Just markdown',
            'No DFM blocks here.',
        ]);
        const result = computeDecorations(doc);
        assert.strictEqual(result.protectedRanges.length, 0);
        assert.strictEqual(result.annotationLines.length, 0);
        assert.strictEqual(result.blockIdLines.length, 0);
    });
});
