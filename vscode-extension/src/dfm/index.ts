/**
 * DFM Module - barrel export
 */

export { DfmEditorService, DfmSessionManager } from './dfmEditorService';
export type { DfmSession, IngestResult, SaveResult } from './dfmEditorService';
export {
    DfmLanguageFeatures,
    DfmFoldingProvider,
    DFM_PATTERNS,
    computeFoldingRanges,
    computeDecorations,
} from './dfmLanguageFeatures';
