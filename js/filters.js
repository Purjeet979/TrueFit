export function applyFilters(pool) {
  const minExp = parseFloat(document.getElementById('filter-exp').value) || 0;
  const location = document.getElementById('filter-location').value;
  const workMode = document.getElementById('filter-workmode').value;
  const otwOnly = document.getElementById('filter-otw').classList.contains('active');

  return pool.filter(c => {
    if (c.profile.years_of_experience < minExp) return false;
    if (location) {
      const candidateLoc = c.profile.location || '';
      // Also check country for broader location matching
      const candidateCountry = c.profile.country || '';
      if (!candidateLoc.toLowerCase().includes(location.toLowerCase()) &&
          !candidateCountry.toLowerCase().includes(location.toLowerCase())) return false;
    }
    if (workMode) {
      const candMode = c.redrob_signals?.preferred_work_mode;
      // 'flexible' candidates match any mode; also allow if candidate mode not set
      if (candMode && candMode !== workMode && candMode !== 'flexible') return false;
    }
    if (otwOnly && (!c.redrob_signals || !c.redrob_signals.open_to_work_flag)) return false;
    return true;
  });
}
