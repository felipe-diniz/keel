/**
 * Masking of personal data in the captured page, ON by default. The text is replaced in place, keeping the column
 * width: a blur leaves a grey stain that reads as a broken product, and a seed generator can produce a document number
 * that belongs to a real person. The presets cover Brazilian documents and contacts; `mask.patterns` in the config adds
 * the project's own. `applyRules` and `maskDom` are self-contained so they can run inside the page by their source.
 */
export const PRESETS = {
  cpf: ['\\b\\d{3}\\.\\d{3}\\.\\d{3}-\\d{2}\\b', '•••.•••.•••-••'],
  cnpj: ['\\b\\d{2}\\.\\d{3}\\.\\d{3}/\\d{4}-\\d{2}\\b', '••.•••.•••/••••-••'],
  /** With or without +55, the area code in parentheses or after +55; the last 4 digits stay so it still reads as a phone. */
  'phone-br': ['((?:\\+55\\s?)?\\(\\d{2}\\)\\s?|\\+55\\s?\\d{2}\\s?)\\d{4,5}-?(\\d{4})\\b', '$1•••••-$2'],
  /** The domain stays so the line still reads as an e-mail. */
  email: ['\\b[\\w.+-]+@([\\w-]+\\.[\\w.-]+)\\b', '•••@$1'],
};

export function rulesOf(mask = {}) {
  const presets = (mask.presets ?? Object.keys(PRESETS)).map((name) => {
    if (!PRESETS[name]) throw new Error(`unknown mask preset: ${name} (${Object.keys(PRESETS).join(', ')})`);
    return { source: PRESETS[name][0], flags: 'g', replace: PRESETS[name][1] };
  });
  const own = (mask.patterns ?? []).map((p) => ({ source: p.regex, flags: (p.flags ?? 'g').includes('g') ? p.flags ?? 'g' : `${p.flags}g`, replace: p.replace ?? '•••' }));
  return [...presets, ...own];
}

export function applyRules(text, rules) {
  let count = 0;
  for (const rule of rules) {
    const re = new RegExp(rule.source, rule.flags);
    const hits = text.match(re);
    if (!hits) continue;
    count += hits.length;
    text = text.replace(re, rule.replace);
  }
  return { text, count };
}

export function maskText(text, mask) {
  return applyRules(text, rulesOf(mask));
}

/** Runs in the page: every text node and every input value, plus `hide` selectors set invisible. Returns the count. */
export function maskDom(apply, rules, hide) {
  let count = 0;
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);
  for (const node of nodes) {
    const out = apply(node.nodeValue ?? '', rules);
    if (out.count) {
      node.nodeValue = out.text;
      count += out.count;
    }
  }
  for (const input of document.querySelectorAll('input, textarea')) {
    const out = apply(input.value ?? '', rules);
    if (out.count) {
      input.value = out.text;
      count += out.count;
    }
  }
  for (const selector of hide) for (const el of document.querySelectorAll(selector)) el.style.visibility = 'hidden';
  return count;
}

/** The expression `page.evaluate` runs: the functions go by source, so no `eval` runs inside the page. */
export function maskExpression(mask = {}) {
  return `(${maskDom.toString()})(${applyRules.toString()}, ${JSON.stringify(rulesOf(mask))}, ${JSON.stringify(mask.hide ?? [])})`;
}
