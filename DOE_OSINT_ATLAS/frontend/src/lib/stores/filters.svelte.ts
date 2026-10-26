/**
 * Filters store — manages global filter state for fiscal year range,
 * minimum dollar threshold, and community filter.
 * Uses Svelte 5 runes ($state) for reactivity.
 */

function createFiltersStore() {
	let fiscalYearMin = $state(2007);
	let fiscalYearMax = $state(2026);
	let minDollars = $state(0);
	let communityFilter = $state<number | null>(null);

	function setFiscalYearRange(min: number, max: number): void {
		fiscalYearMin = Math.max(2007, Math.min(min, 2026));
		fiscalYearMax = Math.max(2007, Math.min(max, 2026));
		if (fiscalYearMin > fiscalYearMax) {
			[fiscalYearMin, fiscalYearMax] = [fiscalYearMax, fiscalYearMin];
		}
	}

	function setMinDollars(amount: number): void {
		minDollars = Math.max(0, amount);
	}

	function setCommunityFilter(communityId: number | null): void {
		communityFilter = communityId;
	}

	function resetFilters(): void {
		fiscalYearMin = 2007;
		fiscalYearMax = 2026;
		minDollars = 0;
		communityFilter = null;
	}

	/**
	 * Returns query parameters suitable for API calls.
	 */
	function toQueryParams(): Record<string, string> {
		const params: Record<string, string> = {};
		if (fiscalYearMin > 2007) params['fy_min'] = String(fiscalYearMin);
		if (fiscalYearMax < 2026) params['fy_max'] = String(fiscalYearMax);
		if (minDollars > 0) params['min_dollars'] = String(minDollars);
		if (communityFilter !== null) params['community'] = String(communityFilter);
		return params;
	}

	return {
		get fiscalYearMin() {
			return fiscalYearMin;
		},
		get fiscalYearMax() {
			return fiscalYearMax;
		},
		get minDollars() {
			return minDollars;
		},
		get communityFilter() {
			return communityFilter;
		},
		setFiscalYearRange,
		setMinDollars,
		setCommunityFilter,
		resetFilters,
		toQueryParams
	};
}

export const filtersStore = createFiltersStore();
