// Renders structured block-based update data into production-quality HTML
// v2: Web Editorial - clean, modern white-space layout with block-level theme overrides (Light/Dark)
// v3: Gmail Teaser - table-based, email-safe teaser linking to the hosted update

export function renderWeb(blocks, tokens) {
  const containerWidth = tokens.containerWidth || 600;

  // Generate HTML for each block based on its type and theme settings
  const blocksHtml = blocks.map(block => {
    const isDark = block.theme === 'dark';
    const bg = isDark ? tokens.colorBgDark : tokens.colorBgPrimary;
    const textMain = isDark ? tokens.colorTextInv : tokens.colorTextMain;
    const textMuted = isDark ? tokens.colorTextMuted : tokens.colorTextMuted;
    const border = isDark ? tokens.colorBorderDark : tokens.colorBorderLight;
    const accent = tokens.colorBrandGold;

    // Outer block wrapper
    const blockStyle = `
      background-color: ${bg};
      color: ${textMain};
      border-bottom: 1px solid ${border}22;
      transition: all 0.2s;
    `;

    switch (block.type) {
      case 'header':
        const isWatermark = block.logoType 
          ? block.logoType === 'watermark'
          : isDark;
        
        const colorOpt = block.logoColor || 'adaptive';
        let useWhiteImage = isDark;
        let opacityVal = 1;

        if (colorOpt === 'white') {
          useWhiteImage = true;
          opacityVal = 1;
        } else if (colorOpt === 'dark') {
          useWhiteImage = false;
          opacityVal = 1;
        } else if (colorOpt === 'dark-grey') {
          useWhiteImage = isDark;
          opacityVal = isDark ? 0.3 : 0.7;
        } else if (colorOpt === 'grey') {
          useWhiteImage = isDark;
          opacityVal = isDark ? 0.6 : 0.4;
        } else {
          // adaptive
          useWhiteImage = isDark;
          opacityVal = 1;
        }

        const logoUrl = isWatermark
          ? (useWhiteImage 
              ? 'https://www.evolutionstables.nz/updates/Evolution-Stables-Logo-White.png'
              : 'https://www.evolutionstables.nz/updates/Evolution-Stables-Logo-Black.png')
          : (useWhiteImage
              ? 'https://www.evolutionstables.nz/updates/Logo-White.png'
              : 'https://www.evolutionstables.nz/updates/Logo-Black.png');

        const sizeHeight = block.logoSize === 'small' 
          ? 64 
          : (block.logoSize === 'large' 
              ? 96 
              : (block.logoSize === 'xlarge' ? 112 : 80));

        const needsInvert = useWhiteImage && !isWatermark;
        const filterStyle = needsInvert ? 'filter: brightness(0) invert(1); -webkit-filter: brightness(0) invert(1);' : '';

        return `
          <div style="${blockStyle} padding: 64px 48px 32px 48px; text-align: left;">
            <div style="margin-bottom: 24px;">
              <img src="${logoUrl}" alt="Evolution Stables" style="height: ${sizeHeight}px; max-height: ${sizeHeight}px; width: auto; display: block; margin: 0; opacity: ${opacityVal}; ${filterStyle}">
            </div>
            <div style="font-family:'${tokens.fontInterface}',sans-serif; font-size: 11px; font-weight: 700; letter-spacing: 3px; text-transform: uppercase; color: ${accent}; margin-bottom: 12px;">
              ${escapeHtml(block.subtitle || 'STABLE UPDATE')}
            </div>
            <h1 style="font-family:'${tokens.fontDisplay}',serif; font-size: 48px; font-weight: 400; line-height: 1.15; margin: 0; color: ${textMain}; letter-spacing: -0.02em;">
              ${block.title ? formatTitle(block.title, accent) : 'Update Title'}
            </h1>
          </div>
        `;

      case 'paragraph':
        return `
          <div style="${blockStyle} padding: 16px 48px; line-height: 1.8; font-size: 16px; font-family:'${tokens.fontInterface}',sans-serif; font-weight: 400; color: ${textMain === '#020202' ? '#333333' : textMain}; text-align: justify;">
            <p style="margin: 0 0 1.5em 0;">${escapeHtml(block.text || '')}</p>
          </div>
        `;

      case 'insights':
        const bulletItems = (block.items || [])
          .filter(item => item.trim())
          .map(item => `
            <li style="margin-bottom: 12px; display: flex; align-items: flex-start; text-align: left; line-height: 1.6;">
              <span style="color: ${accent}; margin-right: 12px; font-weight: bold; font-size: 18px; line-height: 1;">•</span>
              <span style="font-family:'${tokens.fontInterface}',sans-serif; font-size: 15px; color: ${isDark ? '#e4e4e7' : '#4b5563'};">${escapeHtml(item)}</span>
            </li>
          `).join('');

        return `
          <div style="${blockStyle} padding: 36px 48px;">
            <div style="background-color: ${isDark ? '#0a0a0a' : '#fafafa'}; border: 1px solid ${border}; border-radius: 12px; padding: 28px 32px; text-align: left;">
              <h3 style="font-family:'${tokens.fontInterface}',sans-serif; font-size: 11px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; color: ${accent}; margin: 0 0 18px 0;">
                ${escapeHtml(block.label || 'KEY INSIGHTS')}
              </h3>
              <ul style="list-style: none; padding: 0; margin: 0;">
                ${bulletItems || '<li style="color:#747474;font-size:14px;font-style:italic;">No insights added yet</li>'}
              </ul>
            </div>
          </div>
        `;

      case 'quote':
        let attributionHtml = '';
        if (block.attribution) {
          const commaIdx = block.attribution.indexOf(',');
          if (commaIdx !== -1) {
            const name = block.attribution.substring(0, commaIdx).trim();
            const company = block.attribution.substring(commaIdx).trim(); // includes the comma
            attributionHtml = `
              <span style="color: ${textMuted}; font-weight: 500;">&mdash; ${escapeHtml(name)}</span><span style="color: ${textMain}; font-weight: 700;">${escapeHtml(company)}</span>
            `;
          } else {
            attributionHtml = `
              <span style="color: ${textMuted}; font-weight: 500;">&mdash; ${escapeHtml(block.attribution)}</span>
            `;
          }
        }

        return `
          <div style="${blockStyle} padding: 36px 48px; text-align: left;">
            <div style="border-left: 3px solid ${accent}; padding: 12px 0 12px 32px; margin: 8px 0;">
              <blockquote style="font-family:'${tokens.fontDisplay}',serif; font-style: italic; font-size: 24px; line-height: 1.7; color: ${textMain}; margin: 0 0 28px 0; text-align: justify; max-width: 66.67%; box-sizing: border-box;">
                &ldquo;${escapeHtml(block.text || 'Quote goes here...')}&rdquo;
              </blockquote>
              ${attributionHtml ? `
                <cite style="font-family:'${tokens.fontInterface}',sans-serif; font-style: normal; font-size: 12px; text-transform: uppercase; letter-spacing: 1.5px; display: block; text-align: right;">
                  ${attributionHtml}
                </cite>
              ` : ''}
            </div>
          </div>
        `;

      case 'numbered_grid':
        const gridCells = (block.items || []).map((item, idx) => {
          const borderRightStyle = idx % 2 === 0 ? `border-right: 1px solid ${border};` : '';
          const borderBottomStyle = idx < 2 ? `border-bottom: 1px solid ${border};` : '';
          return `
            <div class="grid-cell" style="padding: 24px; flex: 1 1 45%; min-width: 220px; box-sizing: border-box; text-align: left; ${borderRightStyle} ${borderBottomStyle}">
              <div style="font-family:'${tokens.fontInterface}',monospace; font-size: 13px; font-weight: bold; color: ${accent}; margin-bottom: 12px; letter-spacing: 1px;">
                ${escapeHtml(item.num || `0${idx + 1}`)}
              </div>
              <h4 style="font-family:'${tokens.fontInterface}',sans-serif; font-size: 16px; font-weight: 700; margin: 0 0 8px 0; color: ${textMain}; line-height: 1.4;">
                ${escapeHtml(item.title || 'Item Title')}
              </h4>
              <p style="font-family:'${tokens.fontInterface}',sans-serif; font-size: 13px; line-height: 1.6; color: ${isDark ? '#a1a1aa' : '#6b7280'}; margin: 0;">
                ${escapeHtml(item.text || 'Item description...')}
              </p>
            </div>
          `;
        }).join('');

        return `
          <div style="${blockStyle} padding: 36px 48px;">
            <div style="border: 1px solid ${border}; border-radius: 12px; overflow: hidden; display: flex; flex-wrap: wrap; background-color: ${isDark ? '#000000' : '#ffffff'};">
              ${gridCells || '<div style="padding: 24px; color:#747474; font-size:14px; font-style:italic; width:100%; text-align:center;">No grid items added yet</div>'}
            </div>
          </div>
        `;

      case 'box':
        const total = (block.items || []).length;
        const numRows = Math.ceil(total / 2);
        
        const boxCards = (block.items || []).map((item, idx) => {
          const col = idx % 2;
          const row = Math.floor(idx / 2);
          const borderRightStyle = (col === 0 && idx + 1 < total) ? `border-right: 1px solid ${border};` : '';
          const borderBottomStyle = (row < numRows - 1) ? `border-bottom: 1px solid ${border};` : '';
          
          return `
            <div class="grid-cell" style="flex: 1 1 45%; min-width: 220px; padding: 32px; box-sizing: border-box; text-align: left; ${borderRightStyle} ${borderBottomStyle}">
              <div style="font-family:'${tokens.fontInterface}',monospace; font-size: 13px; font-weight: bold; color: ${isDark ? '#747474' : '#9ca3af'}; margin-bottom: 12px; letter-spacing: 1px;">
                ${escapeHtml(item.num || `0${idx + 1}`)}
              </div>
              <h4 style="font-family:'${tokens.fontInterface}',sans-serif; font-size: 16px; font-weight: 700; margin: 0 0 8px 0; color: ${textMain}; line-height: 1.4;">
                ${escapeHtml(item.title || 'Item Title')}
              </h4>
              <p style="font-family:'${tokens.fontInterface}',sans-serif; font-size: 13px; line-height: 1.6; color: ${isDark ? '#a1a1aa' : '#6b7280'}; margin: 0;">
                ${escapeHtml(item.text || 'Item description...')}
              </p>
            </div>
          `;
        }).join('');

        const headerHtml = (block.title || block.text) ? `
          <div style="margin-bottom: 32px; text-align: left;">
            ${block.title ? `
              <div style="font-family:'${tokens.fontInterface}',sans-serif; font-size: 11px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; color: ${isDark ? '#747474' : '#6b7280'}; margin-bottom: 8px;">
                ${escapeHtml(block.title)}
              </div>
            ` : ''}
            ${block.text ? `
              <h3 style="font-family:'${tokens.fontDisplay}',serif; font-size: 32px; font-weight: 400; line-height: 1.25; margin: 0; color: ${textMain}; letter-spacing: -0.01em;">
                ${formatTitle(block.text, textMain)}
              </h3>
            ` : ''}
          </div>
        ` : '';

        return `
          <div style="${blockStyle} padding: 48px 48px; --block-border: ${border};">
            ${headerHtml}
            <div style="border: 1px solid ${border}; border-radius: 12px; overflow: hidden; display: flex; flex-wrap: wrap; background-color: ${bg};">
              ${boxCards || '<div style="padding: 24px; color:#747474; font-size:14px; font-style:italic; width:100%; text-align:center;">No boxes added yet</div>'}
            </div>
          </div>
        `;

      case 'hero_image':
        return `
          <div style="${blockStyle} padding: 0;">
            <img src="${escapeHtml(block.url || 'placeholder.jpg')}" alt="Hero" style="display: block; width: 100%; height: auto; border: 0; margin: 0;">
            ${block.caption ? `
              <div style="font-family:'${tokens.fontInterface}',sans-serif; font-size: 10px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; color: ${textMuted}; padding: 16px 48px 12px 48px; text-align: left;">
                ${escapeHtml(block.caption)}
              </div>
            ` : ''}
          </div>
        `;

      case 'footer':
        return `
          <div style="${blockStyle} padding: 64px 48px; text-align: center; border-top: 1px solid ${border}44;">
            <h2 style="font-family:'${tokens.fontDisplay}',serif; font-size: 32px; font-weight: 400; line-height: 1.25; margin: 0 0 12px 0; color: ${textMain}; letter-spacing: -0.01em;">
              ${block.title ? formatTitle(block.title, accent) : 'The Future of Ownership <br /> Has Arrived'}
            </h2>
            <p style="font-family:'${tokens.fontInterface}',sans-serif; font-size: 10px; font-weight: 600; color: ${textMuted}; text-transform: uppercase; letter-spacing: 2px; margin: 0 0 40px 0;">
              ${escapeHtml(block.subtitle || 'DIGITAL-SYNDICATION, BY EVOLUTION STABLES, POWERED BY TOKINVEST')}
            </p>
            <div style="border-top: 1px solid ${border}22; padding-top: 24px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;">
              <div>
                <img src="${isDark ? 'https://www.evolutionstables.nz/updates/Logo-White.png' : 'https://www.evolutionstables.nz/updates/Logo-Black.png'}" alt="Evolution Stables" style="height: 32px; max-height: 32px; width: auto; display: block; ${isDark ? 'filter: brightness(0) invert(1) opacity(0.4); -webkit-filter: brightness(0) invert(1) opacity(0.4);' : 'filter: opacity(0.4); -webkit-filter: opacity(0.4);'}">
              </div>
              <div style="display: flex; gap: 18px; align-items: center;">
                <a href="https://linkedin.com" target="_blank" style="color: #747474; display: inline-block; transition: opacity 0.2s;" title="LinkedIn">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" style="display: block; width: 24px; height: 24px;">
                    <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
                  </svg>
                </a>
                <a href="https://x.com" target="_blank" style="color: #747474; display: inline-block; transition: opacity 0.2s;" title="X">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" style="display: block; width: 24px; height: 24px;">
                    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                  </svg>
                </a>
                <a href="mailto:alex@evolutionstables.nz" style="color: #747474; display: inline-block; transition: opacity 0.2s;" title="Email">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" style="display: block; width: 24px; height: 24px;">
                    <path d="M20 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z" />
                  </svg>
                </a>
              </div>
            </div>
          </div>
        `;

      default:
        return '';
    }
  }).join('');

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="robots" content="noindex, nofollow">
  <title>Evolution Stables | Hosted Update</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter:wght@300;400;500;600;700;800&family=Playfair+Display:ital,wght@0,400;0,600;0,700;1,400&display=swap" rel="stylesheet">
  <style>
    body {
      background-color: #f7f7f8;
      margin: 0;
      padding: 48px 16px;
      display: flex;
      justify-content: center;
      align-items: flex-start;
      min-height: 100vh;
      box-sizing: border-box;
      -webkit-font-smoothing: antialiased;
    }
    .update-container {
      width: 100%;
      max-width: ${containerWidth}px;
      background-color: ${tokens.colorBgPrimary};
      border: 1px solid ${tokens.colorBorderLight};
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 20px 40px rgba(0,0,0,0.03);
    }
    @media (max-width: 640px) {
      body {
        padding: 16px 8px;
      }
      .update-container {
        border-radius: 12px;
      }
      .grid-cell {
        border-right: none !important;
        border-bottom: 1px solid var(--block-border, ${tokens.colorBorderLight}) !important;
      }
      .grid-cell:last-child {
        border-bottom: none !important;
      }
    }
  </style>
</head>
<body>
  <div class="update-container">
    ${blocksHtml}
  </div>
</body>
</html>`;
}

export function renderTeaser(blocks, tokens) {
  // Find first header block, paragraph block, and footer block for email teaser
  const headerBlock = blocks.find(b => b.type === 'header') || { title: 'Investor Update', subtitle: 'STABLE UPDATE' };
  const firstParagraphBlock = blocks.find(b => b.type === 'paragraph') || { text: 'Click below to read the full update.' };
  const footerBlock = blocks.find(b => b.type === 'footer') || {
    title: 'The Future of Ownership <br /> Has Arrived',
    subtitle: 'DIGITAL-SYNDICATION, BY EVOLUTION STABLES, POWERED BY TOKINVEST'
  };
  
  // Try to find slug from header or generate a simple one
  const slug = (headerBlock.title || 'update')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '');

  const accent = tokens.colorBrandGold;

  const isTeaserWatermark = headerBlock.logoType === 'watermark';
  
  const teaserColorOpt = headerBlock.logoColor || 'adaptive';
  let teaserUseWhiteImage = false; // default for light background in email teaser
  let teaserOpacityVal = 1;

  if (teaserColorOpt === 'white') {
    teaserUseWhiteImage = true;
    teaserOpacityVal = 1;
  } else if (teaserColorOpt === 'dark') {
    teaserUseWhiteImage = false;
    teaserOpacityVal = 1;
  } else if (teaserColorOpt === 'dark-grey') {
    teaserUseWhiteImage = false;
    teaserOpacityVal = 0.7;
  } else if (teaserColorOpt === 'grey') {
    teaserUseWhiteImage = false;
    teaserOpacityVal = 0.4;
  } else {
    // adaptive
    teaserUseWhiteImage = false;
    teaserOpacityVal = 1;
  }

  const teaserLogoUrl = isTeaserWatermark
    ? (teaserUseWhiteImage 
        ? 'https://www.evolutionstables.nz/updates/Evolution-Stables-Logo-White.png'
        : 'https://www.evolutionstables.nz/updates/Evolution-Stables-Logo-Black.png')
    : (teaserUseWhiteImage
        ? 'https://www.evolutionstables.nz/updates/Logo-White.png'
        : 'https://www.evolutionstables.nz/updates/Logo-Black.png');

  const teaserSizeHeight = headerBlock.logoSize === 'small' 
    ? 64 
    : (headerBlock.logoSize === 'large' 
        ? 96 
        : (headerBlock.logoSize === 'xlarge' ? 112 : 80));

  const footerIsDark = (footerBlock.theme === 'dark');
  const footerBg = footerIsDark ? tokens.colorBgDark : tokens.colorBgPrimary;
  const footerTextMain = footerIsDark ? tokens.colorTextInv : tokens.colorTextMain;
  const footerTextMuted = tokens.colorTextMuted;
  const footerBorder = footerIsDark ? tokens.colorBorderDark : tokens.colorBorderLight;

  return `<!doctype html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="x-apple-disable-message-reformatting">
  <title>${escapeHtml(headerBlock.title)}</title>
  <!--[if mso]><noscript><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml></noscript><![endif]-->
</head>
<body style="margin: 0; padding: 0; background-color: #f7f7f8; word-wrap:break-word; word-break:break-word;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%; border-collapse:collapse; background-color:#f7f7f8; margin:0; padding:0;">
    <tr>
      <td align="center" style="padding:32px 12px;">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:100%; max-width:600px; border-collapse:collapse; background-color:#ffffff; border: 1px solid #e4e4e7; border-radius:16px;">

          <!-- HEADER -->
          <tr>
            <td style="padding:40px 40px 20px 40px; border-bottom:1px solid #f4f4f5; border-radius:16px 16px 0 0;">
              <img
                src="${teaserLogoUrl}"
                alt="Evolution Stables"
                style="display:block; height:${teaserSizeHeight}px; max-height:${teaserSizeHeight}px; width:auto; border:0; opacity:${teaserOpacityVal};"
              />
              <div style="font-family:'Inter', Arial, Helvetica, sans-serif; font-size:11px; line-height:16px; font-weight:bold; letter-spacing:2px; text-transform:uppercase; color:#737373; padding-top:16px;">
                ${escapeHtml(headerBlock.subtitle || 'STABLE UPDATE')}
              </div>
            </td>
          </tr>

          <!-- HEADLINE & BODY TEASER -->
          <tr>
            <td style="padding:32px 40px 20px 40px;">
              <div style="font-family:'Playfair Display', Georgia, serif; font-size:32px; line-height:1.2; font-weight:normal; color:#020202; padding-bottom:18px; letter-spacing:-0.01em;">
                ${escapeHtml(headerBlock.title)}
              </div>
              <div style="font-family:'Inter', Arial, Helvetica, sans-serif; font-size:15px; line-height:1.7; color:#4b5563; padding-bottom:16px;">
                ${escapeHtml(firstParagraphBlock.text)}
              </div>
            </td>
          </tr>

          <!-- CTA BUTTON -->
          <tr>
            <td style="padding:0 40px 40px 40px; text-align:center;">
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:0 auto;">
                <tr>
                  <td style="background-color:#020202; border-radius:8px; text-align:center;">
                    <a href="https://evolutionstables.nz/updates/${escapeHtml(slug)}.html" style="display:inline-block; font-family:'Inter', Arial, Helvetica, sans-serif; font-size:14px; font-weight:600; line-height:20px; color:#ffffff; text-decoration:none; padding:12px 28px; border-radius:8px;">
                      Read full update &rarr;
                    </a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- FOOTER -->
          <tr>
            <td style="background-color:${footerBg}; padding:64px 40px; text-align:center; border-radius:0 0 16px 16px; border-top: 1px solid ${footerBorder}44;">
              <div style="font-family:'${tokens.fontDisplay}', Georgia, serif; font-size:32px; line-height:1.25; font-weight:normal; color:${footerTextMain}; padding-bottom:12px; letter-spacing:-0.01em;">
                ${footerBlock.title ? formatTitle(footerBlock.title, accent) : 'The Future of Ownership <br /> Has Arrived'}
              </div>
              <div style="font-family:'${tokens.fontInterface}', Arial, Helvetica, sans-serif; font-size:10px; line-height:18px; letter-spacing:2px; text-transform:uppercase; color:${footerTextMuted}; padding-bottom:40px; font-weight:600;">
                ${escapeHtml(footerBlock.subtitle || 'DIGITAL-SYNDICATION, BY EVOLUTION STABLES, POWERED BY TOKINVEST')}
              </div>
              
              <!-- Divider line -->
              <div style="border-top: 1px solid ${footerBorder}22; margin-top: 24px; margin-bottom: 24px; height: 1px;"></div>

              <!-- Social Links & Logo row -->
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td align="left" style="vertical-align: middle;">
                    <img src="${footerIsDark ? 'https://www.evolutionstables.nz/updates/Logo-White.png' : 'https://www.evolutionstables.nz/updates/Logo-Black.png'}" alt="Evolution Stables" height="32" style="display: block; height: 32px; width: auto; border: 0; margin: 0; opacity: 0.4; ${footerIsDark ? 'filter: brightness(0) invert(1); -webkit-filter: brightness(0) invert(1);' : ''}" />
                  </td>
                  <td align="right" style="vertical-align: middle;">
                    <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin: 0 0 0 auto;">
                      <tr>
                        <td style="padding-right: 18px; vertical-align: middle;">
                          <a href="https://linkedin.com" target="_blank" style="color: #747474; text-decoration: none; display: inline-block;">
                            <span style="font-family:'Inter', Arial, sans-serif; font-size: 13px; font-weight: bold; letter-spacing: 1.5px; text-transform: uppercase;">LinkedIn</span>
                          </a>
                        </td>
                        <td style="padding-right: 18px; vertical-align: middle;">
                          <a href="https://x.com" target="_blank" style="color: #747474; text-decoration: none; display: inline-block;">
                            <span style="font-family:'Inter', Arial, sans-serif; font-size: 13px; font-weight: bold; letter-spacing: 1.5px; text-transform: uppercase;">X</span>
                          </a>
                        </td>
                        <td style="vertical-align: middle;">
                          <a href="mailto:alex@evolutionstables.nz" style="color: #747474; text-decoration: none; display: inline-block;">
                            <span style="font-family:'Inter', Arial, sans-serif; font-size: 13px; font-weight: bold; letter-spacing: 1.5px; text-transform: uppercase;">Email</span>
                          </a>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>`;
}

// Helpers
function escapeHtml(text) {
  if (!text) return '';
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function formatTitle(title, goldColor) {
  if (!title) return '';
  // Highlight specific words or text inside quotes, or handle custom markup
  let formatted = escapeHtml(title);
  
  // Unescape safe line breaks
  formatted = formatted.replace(/&lt;br\s*\/?&gt;/gi, '<br />');
  
  // Highlight words like Ownership or First Gear
  const highlightWords = ['Ownership', 'First Gear', 'Otaki', 'Prudentia'];
  highlightWords.forEach(word => {
    const regex = new RegExp(`\\b(${word})\\b`, 'gi');
    formatted = formatted.replace(regex, `<span style="color: ${goldColor}; font-style: italic;">$1</span>`);
  });

  return formatted;
}
