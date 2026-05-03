// Fiscal year normalization utilities
export function normalizeFiscalYear(value) {
  if (!value) return ''
  return String(value).trim()
}

export function getSelectedFiscalYear() {
  try {
    const stored = localStorage.getItem('selected_fiscal_year') || ''
    return normalizeFiscalYear(stored)
  } catch (e) {
    return ''
  }
}

export function setSelectedFiscalYear(value) {
  try {
    if (value) localStorage.setItem('selected_fiscal_year', value)
  } catch (e) {
    // ignore
  }
}

export default { normalizeFiscalYear, getSelectedFiscalYear, setSelectedFiscalYear }
