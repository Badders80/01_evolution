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