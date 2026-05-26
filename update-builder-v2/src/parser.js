/**
 * Parses raw copy-pasted text from investor updates into structured content blocks.
 * Uses heuristic rule matching to categorize paragraphs/lines.
 */
export function parseRawText(text) {
  if (!text || !text.trim()) return [];

  // Split by double newlines to isolate paragraphs/blocks
  const paragraphs = text
    .split(/\n\s*\n/)
    .map(p => p.trim())
    .filter(Boolean);

  const blocks = [];
  let i = 0;

  // 1. Identify Header (usually the first block contains title and sometimes subtitle)
  if (paragraphs.length > 0) {
    const lines = paragraphs[0].split('\n').map(l => l.trim()).filter(Boolean);
    if (lines.length > 0) {
      const title = lines[0];
      const subtitle = lines.slice(1).join(' ') || '';
      blocks.push({
        id: generateId(),
        type: 'header',
        theme: 'light',
        title,
        subtitle: subtitle || 'STABLE UPDATE'
      });
      i++;
    }
  }

  // 2. Loop through remaining blocks
  while (i < paragraphs.length) {
    const blockText = paragraphs[i];
    const uppercaseText = blockText.toUpperCase();

    // Key Insights check
    if (uppercaseText.startsWith('KEY INSIGHTS:') || uppercaseText === 'KEY INSIGHTS') {
      const items = [];
      // Look at the lines in this block, or collect subsequent single line blocks
      const lines = blockText.split('\n').map(l => l.trim()).filter(Boolean);
      
      // If there's content after the header in the same block, add it
      const headerIndex = lines.findIndex(l => l.toUpperCase().includes('KEY INSIGHTS'));
      for (let j = headerIndex + 1; j < lines.length; j++) {
        items.push(lines[j].replace(/^[-•*]\s*/, ''));
      }

      // If the block was just the heading, we might look at subsequent paragraphs until we hit another section
      if (items.length === 0 && i + 1 < paragraphs.length) {
        let peekIndex = i + 1;
        while (peekIndex < paragraphs.length) {
          const peekText = paragraphs[peekIndex];
          // Stop if it matches another known block type header
          if (isBlockHeader(peekText)) {
            break;
          }
          // Split paragraph by lines to get multiple bullet points if they are in one block
          const bulletLines = peekText.split('\n').map(l => l.trim()).filter(Boolean);
          bulletLines.forEach(line => {
            items.push(line.replace(/^[-•*]\s*/, ''));
          });
          peekIndex++;
        }
        i = peekIndex - 1; // advance main pointer
      }

      blocks.push({
        id: generateId(),
        type: 'insights',
        theme: 'dark', // default key insights to dark block
        label: 'KEY INSIGHTS',
        items: items.length > 0 ? items : ['First insight...', 'Second insight...']
      });
      i++;
      continue;
    }

    // Quote Check: Starts with a quotation mark or contains a line starting with an em dash / attribution indicator
    const hasQuoteMarks = blockText.startsWith('"') || blockText.startsWith('“') || blockText.includes('\n—') || blockText.includes('\n-');
    if (hasQuoteMarks) {
      const lines = blockText.split('\n').map(l => l.trim()).filter(Boolean);
      let quoteText = '';
      let attribution = '';
      
      lines.forEach(line => {
        if (line.startsWith('—') || line.startsWith('-')) {
          attribution = line.replace(/^[—\-]\s*/, '');
        } else {
          quoteText += (quoteText ? ' ' : '') + line;
        }
      });

      blocks.push({
        id: generateId(),
        type: 'quote',
        theme: 'light',
        text: quoteText.replace(/^["“]|["”]$/g, ''),
        attribution: attribution || 'Lance O\'Sullivan, Wexford Stables'
      });
      i++;
      continue;
    }

    // Numbered Grid check (e.g. looks like 01 followed by title and text)
    // Or if current block is "01" and subsequent contains text
    const isNumberMarker = /^\d{2}$/.test(blockText);
    if (isNumberMarker || (i + 1 < paragraphs.length && /^\d{2}$/.test(paragraphs[i + 1]))) {
      const items = [];
      let currentIdx = i;

      while (currentIdx < paragraphs.length) {
        const itemNumText = paragraphs[currentIdx];
        if (/^\d{2}$/.test(itemNumText)) {
          const num = itemNumText;
          let titleStr = '';
          let bodyStr = '';

          // Look ahead for title
          if (currentIdx + 1 < paragraphs.length) {
            titleStr = paragraphs[currentIdx + 1];
          }
          // Look ahead for body
          if (currentIdx + 2 < paragraphs.length) {
            bodyStr = paragraphs[currentIdx + 2];
          }

          items.push({
            num,
            title: titleStr,
            text: bodyStr
          });
          currentIdx += 3;
        } else {
          break;
        }
      }

      if (items.length > 0) {
        blocks.push({
          id: generateId(),
          type: 'box',
          theme: 'light',
          title: '',
          text: '',
          items
        });
        i = currentIdx;
        continue;
      }
    }

    // Default to plain paragraph block
    blocks.push({
      id: generateId(),
      type: 'paragraph',
      theme: 'light',
      text: blockText
    });
    i++;
  }

  // Always append a beautiful footer at the end by default
  blocks.push({
    id: generateId(),
    type: 'footer',
    theme: 'dark',
    title: 'The Future of Ownership <br /> Has Arrived',
    subtitle: 'DIGITAL-SYNDICATION, BY EVOLUTION STABLES, POWERED BY TOKINVEST'
  });

  // Post-processing: Merge preceding paragraph section headers into box blocks
  const merged = [];
  for (let j = 0; j < blocks.length; j++) {
    const current = blocks[j];
    const next = blocks[j + 1];
    if (current.type === 'paragraph' && next && next.type === 'box') {
      const lines = current.text.split('\n').map(l => l.trim()).filter(Boolean);
      if (lines.length > 0) {
        next.title = lines[0];
        next.text = lines.slice(1).join(' ');
        continue; // Skip pushing this paragraph block since it is now part of the box section header
      }
    }
    merged.push(current);
  }

  return merged;
}

function generateId() {
  return 'block-' + Math.random().toString(36).substr(2, 9);
}

function isBlockHeader(text) {
  const upper = text.toUpperCase();
  if (upper.startsWith('KEY INSIGHTS:') || upper === 'KEY INSIGHTS') return true;
  if (/^\d{2}$/.test(text)) return true;
  if (text.startsWith('"') || text.startsWith('“')) return true;
  return false;
}
