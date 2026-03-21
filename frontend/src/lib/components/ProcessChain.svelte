<script lang="ts">
	/**
	 * ProcessChain — renders recipe steps as a horizontal flow with arrows.
	 * Each step shows its step number, name, and contractors.
	 * Scrollable horizontally if many steps.
	 */

	export interface ProcessStep {
		step: number;
		name: string;
		who: string[];
		dollars?: number;
		contracts?: number;
		description?: string;
	}

	interface Props {
		steps: ProcessStep[];
		compact?: boolean;
	}

	let { steps = [], compact = false }: Props = $props();

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
</script>

{#if steps.length > 0}
	<div class="process-chain" class:compact>
		<div class="chain-scroll">
			{#each steps as processStep, i}
				{#if i > 0}
					<div class="chain-arrow">
						<svg width="24" height="16" viewBox="0 0 24 16">
							<path d="M0 8 L18 8 M14 3 L20 8 L14 13" stroke="var(--accent-purple-light)" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round" />
						</svg>
					</div>
				{/if}
				<div class="chain-step">
					<div class="step-number">{processStep.step}</div>
					<div class="step-body">
						<div class="step-name">{processStep.name}</div>
						{#if processStep.who.length > 0}
							<div class="step-who">
								{processStep.who.join(', ')}
							</div>
						{/if}
						{#if !compact && processStep.dollars}
							<div class="step-dollars dollars">
								{formatDollars(processStep.dollars)}
							</div>
						{/if}
					</div>
				</div>
			{/each}
		</div>
	</div>
{/if}

<style>
	.process-chain {
		width: 100%;
		overflow-x: auto;
		overflow-y: hidden;
		padding: 8px 0;
	}

	.chain-scroll {
		display: flex;
		align-items: center;
		gap: 0;
		min-width: min-content;
		padding: 4px 8px;
	}

	.chain-arrow {
		display: flex;
		align-items: center;
		flex-shrink: 0;
		padding: 0 2px;
		opacity: 0.7;
	}

	.chain-step {
		display: flex;
		align-items: flex-start;
		gap: 8px;
		background: rgba(124, 58, 237, 0.15);
		border: 1px solid rgba(124, 58, 237, 0.3);
		border-radius: 8px;
		padding: 8px 12px;
		flex-shrink: 0;
		min-width: 120px;
		max-width: 220px;
		transition: background 0.15s ease;
	}

	.chain-step:hover {
		background: rgba(124, 58, 237, 0.25);
	}

	.step-number {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 22px;
		height: 22px;
		border-radius: 50%;
		background: var(--accent-purple);
		color: white;
		font-size: 11px;
		font-weight: 700;
		flex-shrink: 0;
	}

	.step-body {
		display: flex;
		flex-direction: column;
		gap: 2px;
		min-width: 0;
	}

	.step-name {
		font-size: 12px;
		font-weight: 600;
		color: var(--text-primary);
		line-height: 1.3;
		word-wrap: break-word;
	}

	.step-who {
		font-size: 10px;
		color: var(--text-secondary);
		line-height: 1.3;
		overflow: hidden;
		text-overflow: ellipsis;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
	}

	.step-dollars {
		font-size: 10px;
		margin-top: 2px;
	}

	/* Compact mode for inline use */
	.compact .chain-step {
		padding: 5px 8px;
		min-width: 90px;
		max-width: 160px;
	}

	.compact .step-number {
		width: 18px;
		height: 18px;
		font-size: 10px;
	}

	.compact .step-name {
		font-size: 11px;
	}

	.compact .step-who {
		font-size: 9px;
	}
</style>
