/**
 * HLT Engine - Pure JavaScript port of the TypeScript calculation engine
 * Handles all commercial HLT calculations for the digital syndication model
 */

export function calculateHltTerms(input) {
  const { monthlyRate, leaseDuration, totalStakePercent, numTokens } = input;

  // 1. Price for 1% over the full duration (e.g., $70 * 16 = $1,120)
  const pricePer1PercentTotal = monthlyRate * leaseDuration;

  // 2. Annual rate (e.g., $70 * 12 = $840)
  const annualRatePer1Percent = monthlyRate * 12;

  // 3. Total Issuance Value (e.g., $1,120 * 5% = $5,600)
  const totalIssuanceValue = pricePer1PercentTotal * totalStakePercent;

  // 4. Fractional Interest per Token (e.g., 5% / 20 tokens = 0.25%)
  const fractionalInterestPerToken = numTokens > 0 ? totalStakePercent / numTokens : 0;

  // 5. Price per Token (e.g., $5,600 / 20 tokens = $280)
  const pricePerToken = numTokens > 0 ? totalIssuanceValue / numTokens : 0;

  return {
    pricePer1PercentTotal,
    annualRatePer1Percent,
    totalIssuanceValue,
    pricePerToken,
    fractionalInterestPerToken,
  };
}

/**
 * Calculate derived values when any field changes
 * Returns all calculated fields based on the "last edited" field
 */
export function calculateDerivedFields(fields, lastEditedField) {
  const {
    monthlyRate = 0,
    leaseDuration = 1,
    totalStakePercent = 0,
    numTokens = 1,
    pricePer1PercentTotal = 0,
    annualRatePer1Percent = 0,
    totalIssuanceValue = 0,
    pricePerToken = 0,
    fractionalInterestPerToken = 0,
  } = fields;

  const result = { ...fields };

  // Always calculate fractional interest from stake and tokens
  result.fractionalInterestPerToken = numTokens > 0 ? totalStakePercent / numTokens : 0;

  switch (lastEditedField) {
    case 'monthlyRate':
      // Monthly rate changed -> cascade everything
      result.pricePer1PercentTotal = monthlyRate * leaseDuration;
      result.annualRatePer1Percent = monthlyRate * 12;
      result.totalIssuanceValue = result.pricePer1PercentTotal * totalStakePercent;
      result.pricePerToken = numTokens > 0 ? result.totalIssuanceValue / numTokens : 0;
      break;

    case 'pricePer1PercentTotal':
      // Total price per 1% changed -> back-calculate monthly and annual
      result.monthlyRate = leaseDuration > 0 ? pricePer1PercentTotal / leaseDuration : 0;
      result.annualRatePer1Percent = result.monthlyRate * 12;
      result.totalIssuanceValue = pricePer1PercentTotal * totalStakePercent;
      result.pricePerToken = numTokens > 0 ? result.totalIssuanceValue / numTokens : 0;
      break;

    case 'annualRatePer1Percent':
      // Annual rate changed -> back-calculate monthly
      result.monthlyRate = annualRatePer1Percent / 12;
      result.pricePer1PercentTotal = result.monthlyRate * leaseDuration;
      result.totalIssuanceValue = result.pricePer1PercentTotal * totalStakePercent;
      result.pricePerToken = numTokens > 0 ? result.totalIssuanceValue / numTokens : 0;
      break;

    case 'totalIssuanceValue':
      // Total value changed -> back-calculate monthly rate
      result.pricePer1PercentTotal = totalStakePercent > 0 ? totalIssuanceValue / totalStakePercent : 0;
      result.monthlyRate = leaseDuration > 0 ? result.pricePer1PercentTotal / leaseDuration : 0;
      result.annualRatePer1Percent = result.monthlyRate * 12;
      result.pricePerToken = numTokens > 0 ? totalIssuanceValue / numTokens : 0;
      break;

    case 'pricePerToken':
      // Token price changed -> back-calculate total value
      result.totalIssuanceValue = pricePerToken * numTokens;
      result.pricePer1PercentTotal = totalStakePercent > 0 ? result.totalIssuanceValue / totalStakePercent : 0;
      result.monthlyRate = leaseDuration > 0 ? result.pricePer1PercentTotal / leaseDuration : 0;
      result.annualRatePer1Percent = result.monthlyRate * 12;
      break;

    case 'leaseDuration':
      // Duration changed -> recalc from monthly rate
      result.pricePer1PercentTotal = monthlyRate * leaseDuration;
      result.totalIssuanceValue = result.pricePer1PercentTotal * totalStakePercent;
      result.pricePerToken = numTokens > 0 ? result.totalIssuanceValue / numTokens : 0;
      break;

    case 'totalStakePercent':
      // Stake % changed -> recalc token size and total value
      result.fractionalInterestPerToken = numTokens > 0 ? totalStakePercent / numTokens : 0;
      result.pricePer1PercentTotal = monthlyRate * leaseDuration;
      result.totalIssuanceValue = result.pricePer1PercentTotal * totalStakePercent;
      result.pricePerToken = numTokens > 0 ? result.totalIssuanceValue / numTokens : 0;
      break;

    case 'numTokens':
      // Token count changed -> recalc token size and token price
      result.fractionalInterestPerToken = numTokens > 0 ? totalStakePercent / numTokens : 0;
      result.pricePerToken = numTokens > 0 ? result.totalIssuanceValue / numTokens : 0;
      break;

    default:
      // Default: calculate from monthly rate if we have one
      if (monthlyRate > 0) {
        result.pricePer1PercentTotal = monthlyRate * leaseDuration;
        result.annualRatePer1Percent = monthlyRate * 12;
        result.totalIssuanceValue = result.pricePer1PercentTotal * totalStakePercent;
        result.pricePerToken = numTokens > 0 ? result.totalIssuanceValue / numTokens : 0;
      }
  }

  return result;
}

/**
 * Format currency for display
 */
export function formatCurrency(value) {
  if (value === null || value === undefined || isNaN(value)) return '$0.00';
  return new Intl.NumberFormat('en-NZ', {
    style: 'currency',
    currency: 'NZD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

/**
 * Format percentage for display
 */
export function formatPercent(value) {
  if (value === null || value === undefined || isNaN(value)) return '0%';
  return `${value.toFixed(2)}%`;
}

/**
 * Format number for display
 */
export function formatNumber(value, decimals = 0) {
  if (value === null || value === undefined || isNaN(value)) return '0';
  return value.toFixed(decimals);
}

/**
 * Generate ERC20 identifier from horse name and lease ID
 */
export function generateErc20Identifier(horseName, leaseId) {
  const namePart = horseName?.substring(0, 3).toUpperCase() || 'HLT';
  const leasePart = leaseId?.replace('LSE-', '') || '';
  return `TVHLT${namePart}${leasePart}`;
}

/**
 * Generate next lease ID
 */
export function nextLeaseId(existingLeases) {
  const maxNum = existingLeases.reduce((max, lease) => {
    const match = lease.lease_id?.match(/LSE-(\d+)/);
    if (match) {
      const num = parseInt(match[1], 10);
      return Math.max(max, num);
    }
    return max;
  }, 0);
  return `LSE-${String(maxNum + 1).padStart(4, '0')}`;
}

/**
 * Add months to ISO date string
 */
export function addMonthsIso(isoDate, months) {
  if (!isoDate) return '';
  const date = new Date(isoDate + 'T00:00:00');
  date.setMonth(date.getMonth() + months);
  // Return last day of the month
  const lastDay = new Date(date.getFullYear(), date.getMonth() + 1, 0);
  return lastDay.toISOString().split('T')[0];
}

/**
 * Parse number from string (handles empty strings)
 */
export function parseNumber(value) {
  if (value === '' || value === null || value === undefined) return 0;
  const num = parseFloat(value);
  return isNaN(num) ? 0 : num;
}

/**
 * Build HLT Term Sheet HTML document
 */
export function buildHltDocumentHtml(record) {
  const formalDate = (iso) => {
    if (!iso) return '—';
    const date = new Date(iso + 'T00:00:00');
    return date.toLocaleDateString('en-NZ', { day: '2-digit', month: 'short', year: 'numeric' });
  };

  const formatCurrency = (val) => {
    if (!val) return '$0.00';
    return new Intl.NumberFormat('en-NZ', { style: 'currency', currency: 'NZD', minimumFractionDigits: 2 }).format(val);
  };

  const leaseEndDate = record.lease_end_date || addMonthsIso(record.lease_start_date, record.lease_length_months);

  return `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>HLT Term Sheet - ${record.token_name}</title>
  <style>
    body { font-family: 'IBM Plex Sans', sans-serif; margin: 0; padding: 40px; background: #f8fafc; color: #1e293b; }
    .container { max-width: 800px; margin: 0 auto; background: white; padding: 60px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
    .header { text-align: center; margin-bottom: 40px; padding-bottom: 30px; border-bottom: 2px solid #e2e8f0; }
    .header h1 { font-family: 'DM Serif Display', serif; font-size: 32px; margin: 0 0 8px; color: #1e3a8a; }
    .header .subtitle { font-size: 14px; color: #64748b; text-transform: uppercase; letter-spacing: 0.1em; }
    .section { margin-bottom: 32px; }
    .section h2 { font-family: 'Sora', sans-serif; font-size: 14px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: #3b82f6; margin: 0 0 16px; padding-bottom: 8px; border-bottom: 1px solid #e2e8f0; }
    .grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }
    .field { display: flex; flex-direction: column; }
    .field label { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #94a3b8; margin-bottom: 4px; }
    .field span { font-size: 14px; font-weight: 500; color: #1e293b; }
    .field .value { font-weight: 700; }
    .grid-3 { grid-template-columns: repeat(3, 1fr); }
    .full-width { grid-column: span 2; }
    .highlight { background: #eff6ff; padding: 16px; border-radius: 8px; border: 1px solid #bfdbfe; }
    .highlight .value { font-size: 18px; color: #1e40af; }
    .footer { margin-top: 48px; padding-top: 24px; border-top: 1px solid #e2e8f0; text-align: center; font-size: 12px; color: #94a3b8; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>${record.token_name}</h1>
      <div class="subtitle">Horse Lease Token — Issuance Term Sheet</div>
    </div>

    <div class="section">
      <h2>Lease Overview</h2>
      <div class="grid">
        <div class="field"><label>Lease Reference</label><span class="value">${record.lease_id}</span></div>
        <div class="field"><label>Submission Date</label><span>${formalDate(record.submission_date)}</span></div>
        <div class="field"><label>Horse</label><span class="value">${record.horse_name}</span></div>
        <div class="field"><label>Microchip</label><span>${record.horse_microchip}</span></div>
        <div class="field"><label>Trainer</label><span>${record.trainer_name}</span></div>
        <div class="field"><label>Owner</label><span>${record.owner_name}</span></div>
        <div class="field"><label>Governing Body</label><span>${record.governing_body_name} (${record.governing_body_code})</span></div>
        <div class="field"><label>Lease Period</label><span class="value">${formalDate(record.lease_start_date)} → ${formalDate(leaseEndDate)}</span></div>
        <div class="field"><label>Duration</label><span>${record.lease_length_months} Months</span></div>
      </div>
    </div>

    <div class="section">
      <h2>Token Economics</h2>
      <div class="grid">
        <div class="field"><label>Percentage Leased</label><span class="value">${record.percentage_leased}%</span></div>
        <div class="field"><label>Total Tokens</label><span class="value">${record.num_tokens}</span></div>
        <div class="field"><label>Size per Token</label><span class="value">${record.percentage_per_token?.toFixed(4) || '0.0000'}%</span></div>
        <div class="field"><label>Investor Stakes Split</label><span class="value">${record.investor_stakes_split}%</span></div>
      </div>
    </div>

    <div class="section">
      <h2>Pricing</h2>
      <div class="grid">
        <div class="field"><label>Price per 1% Monthly</label><span class="value">${formatCurrency(record.percentage_price)}</span></div>
        <div class="field"><label>Price per 1% Over Lease</label><span class="value">${formatCurrency(record.percentage_price * record.lease_length_months)}</span></div>
        <div class="field"><label>Annual Rate per 1%</label><span class="value">${formatCurrency(record.annual_percentage_price)}</span></div>
        <div class="field"><label>Total Issuance Value</label><span class="value">${formatCurrency(record.total_issuance_value)}</span></div>
      </div>
    </div>

    <div class="section highlight">
      <h2>Token Pricing Summary</h2>
      <div class="grid grid-3">
        <div class="field"><label>Price Per Token</label><span class="value">${formatCurrency(record.token_price_nzd)}</span></div>
        <div class="field"><label>Total Tokens</label><span class="value">${record.num_tokens}</span></div>
        <div class="field"><label>Total Issuance</label><span class="value">${formatCurrency(record.total_issuance_value)}</span></div>
      </div>
    </div>

    <div class="section">
      <h2>Commercial Terms</h2>
      <div class="grid">
        <div class="field full-width"><label>ERC-20 Identifier</label><span class="value" style="font-family: monospace; font-size: 13px;">${record.erc20_identifier}</span></div>
        <div class="field full-width"><label>Variations</label><span>${record.variations || 'n/a'}</span></div>
      </div>
    </div>

    <div class="footer">
      Generated ${new Date().toLocaleDateString('en-NZ', { day: '2-digit', month: 'short', year: 'numeric' })} — Evolution Stables SSOT Build
    </div>
  </div>
</body>
</html>
  `;
}