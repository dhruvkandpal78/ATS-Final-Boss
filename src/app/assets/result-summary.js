/* User-facing decisions follow review policy, never a detector's numeric score. */
(() => {
  'use strict';
  function summarize(data, mode) {
    const legacy = { attack: 'review_recommended', clean: 'no_signals_detected' };
    const supplied = data.decision || legacy[data.verdict];
    const decision = ['review_recommended', 'no_signals_detected', 'insufficient_evidence'].includes(supplied)
      ? supplied : 'insufficient_evidence';
    const findings = Array.isArray(data.findings) ? data.findings : [];
    const triggers = findings.filter(finding => finding.review_trigger === true);
    const instruction = triggers.some(finding => finding.category === 'direct_instruction');
    const repetition = triggers.some(finding => finding.category === 'keyword_repetition');
    if (decision === 'review_recommended') {
      return { decision, label: 'Potential manipulation', title: 'Needs review',
        reason: instruction && repetition ? 'Screening instructions and sustained keyword repetition were found.' :
          instruction ? 'Instructions aimed at changing screening behavior were found.' :
          repetition ? 'Sustained keyword repetition was found.' : 'The review policy flagged this document.',
        action: 'Review the findings before continuing screening.' };
    }
    if (decision === 'no_signals_detected') {
      return { decision, label: 'Completed checks', title: 'No review triggers found',
        reason: 'The completed checks found no signals that trigger manual review. Advisory observations may still be listed.',
        action: 'Continue your standard review. This does not verify authenticity.' };
    }
    const density = findings.some(finding => finding.category === 'keyword_density');
    return { decision, label: 'Limited assessment', title: 'Inconclusive',
      reason: (mode === 'text' ? 'Text checks ran, but a full document assessment is unavailable for pasted text.' :
        'This document could not be fully assessed.') +
        (density ? ' Keyword density alone does not prove manipulation.' : ''),
      action: mode === 'text' ? 'Upload the PDF for document checks, or review the resume manually.' :
        'Review the coverage details and the document manually.' };
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = summarize;
  else window.ATSResultSummary = summarize;
})();
