<script lang="ts">
	/**
	 * RecipeCard — structured recipe output card for deep research results.
	 * Displays the query, confidence badge, process chain, progress info,
	 * and an expandable evidence list.
	 */

	import ProcessChain from './ProcessChain.svelte';
	import type { ProcessStep } from './ProcessChain.svelte';

	export interface RecipeEvidence {
		id: string;
		description: string;
		recipient?: string;
		dollars?: number;
	}

	export interface RecipeProgress {
		roundsCompleted: number;
		contractsFound: number;
		topicsDiscovered: number;
	}

	export interface RecipeData {
		query: string;
		confidence: 'high' | 'medium' | 'low';
		totalDollars: number;
		steps: ProcessStep[];
		progress?: RecipeProgress;
		evidence?: RecipeEvidence[];
		narrative?: string;
	}

	interface Props {
		recipe: RecipeData;
	}

	let { recipe }: Props = $props();

	let evidenceExpanded = $state(false);

	let confidenceClass = $derived(
		recipe.confidence === 'high'
			? 'conf-high'
			: recipe.confidence === 'medium'
				? 'conf-medium'
				: 'conf-low'
	);

	let displayEvidence = $derived(
		recipe.evidence
			? evidenceExpanded
				? recipe.evidence
				: recipe.evidence.slice(0, 3)
			: []
	);

	function formatDollars(amount: number): string {
		if (amount >= 1_000_000_000) {
			return `$${(amount / 1_000_000_000).toFixed(1)}B`;
		}
		if (amount >= 1_000_000) {
			return `$${(amount / 1_000_000).toFixed(1)}M`;
		}
		if (amount >= 1_000) {
			return `$${(amount / 1_000).toFixed(0)}K`;
		}
		return `$${amount.toFixed(0)}`;
	}

	function toggleEvidence() {
		evidenceExpanded = !evidenceExpanded;
	}
</script>

<div class="recipe-card">
	<!-- Header -->
	<div class="recipe-header">
		<div class="recipe-header-top">
			<span class="recipe-label">Recipe</span>
			<span class="badge confidence-badge {confidenceClass}">
				{recipe.confidence}
			</span>
		</div>
		<h3 class="recipe-query">{recipe.query}</h3>
		<div class="recipe-investment">
			<span class="investment-label">Total Investment:</span>
			<span class="dollars">{formatDollars(recipe.totalDollars)}</span>
		</div>
	</div>

	<!-- Process Chain -->
	{#if recipe.steps.length > 0}
		<div class="recipe-section">
			<div class="section-label">Process Chain</div>
			<ProcessChain steps={recipe.steps} />
		</div>
	{/if}

	<!-- Progress -->
	{#if recipe.progress}
		<div class="recipe-section">
			<div class="section-label">Research Progress</div>
			<div class="progress-grid">
				<div class="progress-item">
					<span class="progress-value">{recipe.progress.roundsCompleted}</span>
					<span class="progress-label">Rounds</span>
				</div>
				<div class="progress-item">
					<span class="progress-value">{recipe.progress.contractsFound.toLocaleString()}</span>
					<span class="progress-label">Contracts</span>
				</div>
				<div class="progress-item">
					<span class="progress-value">{recipe.progress.topicsDiscovered}</span>
					<span class="progress-label">Topics</span>
				</div>
			</div>
		</div>
	{/if}

	<!-- Narrative -->
	{#if recipe.narrative}
		<div class="recipe-section">
			<div class="section-label">Summary</div>
			<p class="recipe-narrative">{recipe.narrative}</p>
		</div>
	{/if}

	<!-- Evidence -->
	{#if recipe.evidence && recipe.evidence.length > 0}
		<div class="recipe-section">
			<div class="section-label">
				Evidence
				<span class="evidence-count">({recipe.evidence.length} contracts)</span>
			</div>
			<div class="evidence-list">
				{#each displayEvidence as item}
					<div class="evidence-item">
						<div class="evidence-meta">
							{#if item.recipient}
								<span class="evidence-recipient">{item.recipient}</span>
							{/if}
							{#if item.dollars}
								<span class="dollars evidence-dollars">{formatDollars(item.dollars)}</span>
							{/if}
						</div>
						<div class="evidence-desc">{item.description}</div>
					</div>
				{/each}
			</div>
			{#if recipe.evidence.length > 3}
				<button class="btn evidence-toggle" onclick={toggleEvidence}>
					{evidenceExpanded ? 'Show less' : `Show all ${recipe.evidence.length} contracts`}
				</button>
			{/if}
		</div>
	{/if}
</div>

<style>
	.recipe-card {
		background: var(--bg-surface);
		border: 1px solid rgba(124, 58, 237, 0.3);
		border-radius: 10px;
		overflow: hidden;
	}

	/* Header */
	.recipe-header {
		padding: 14px 16px 10px;
		background: rgba(124, 58, 237, 0.08);
		border-bottom: 1px solid rgba(124, 58, 237, 0.15);
	}

	.recipe-header-top {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-bottom: 6px;
	}

	.recipe-label {
		font-size: 10px;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--accent-purple-light);
	}

	.confidence-badge {
		font-size: 10px;
		padding: 1px 6px;
	}

	.conf-high {
		background-color: rgba(5, 150, 105, 0.2);
		color: var(--accent-green-light);
		border: 1px solid rgba(5, 150, 105, 0.3);
	}

	.conf-medium {
		background-color: rgba(234, 88, 12, 0.2);
		color: var(--accent-orange-light);
		border: 1px solid rgba(234, 88, 12, 0.3);
	}

	.conf-low {
		background-color: rgba(239, 68, 68, 0.2);
		color: #fca5a5;
		border: 1px solid rgba(239, 68, 68, 0.3);
	}

	.recipe-query {
		font-size: 15px;
		font-weight: 600;
		color: var(--text-primary);
		margin: 0;
		line-height: 1.4;
	}

	.recipe-investment {
		display: flex;
		align-items: center;
		gap: 6px;
		margin-top: 6px;
		font-size: 12px;
	}

	.investment-label {
		color: var(--text-muted);
	}

	/* Sections */
	.recipe-section {
		padding: 10px 16px;
		border-bottom: 1px solid var(--border-color);
	}

	.recipe-section:last-child {
		border-bottom: none;
	}

	.section-label {
		font-size: 10px;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--text-muted);
		margin-bottom: 6px;
	}

	/* Progress */
	.progress-grid {
		display: flex;
		gap: 16px;
	}

	.progress-item {
		display: flex;
		flex-direction: column;
		align-items: center;
		min-width: 60px;
	}

	.progress-value {
		font-size: 18px;
		font-weight: 700;
		color: var(--accent-purple-light);
		font-family: var(--font-mono);
	}

	.progress-label {
		font-size: 10px;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	/* Narrative */
	.recipe-narrative {
		font-size: 13px;
		color: var(--text-secondary);
		line-height: 1.5;
		margin: 0;
	}

	/* Evidence */
	.evidence-count {
		font-weight: 400;
		color: var(--text-secondary);
		text-transform: none;
		letter-spacing: normal;
	}

	.evidence-list {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}

	.evidence-item {
		padding: 6px 8px;
		background: rgba(0, 0, 0, 0.15);
		border-radius: 6px;
		border: 1px solid var(--border-color);
	}

	.evidence-meta {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
		margin-bottom: 2px;
	}

	.evidence-recipient {
		font-size: 11px;
		font-weight: 600;
		color: var(--accent-blue-light);
	}

	.evidence-dollars {
		font-size: 11px;
	}

	.evidence-desc {
		font-size: 11px;
		color: var(--text-secondary);
		line-height: 1.4;
		overflow: hidden;
		text-overflow: ellipsis;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
	}

	.evidence-toggle {
		margin-top: 8px;
		font-size: 11px;
		padding: 3px 10px;
		width: 100%;
	}
</style>
