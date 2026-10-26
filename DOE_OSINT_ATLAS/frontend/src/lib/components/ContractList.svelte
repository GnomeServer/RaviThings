<script lang="ts">
	import RetrievalBadges from './RetrievalBadges.svelte';
	import { graphStore } from '$lib/stores/graph.svelte';

	export interface ContractResult {
		id: string;
		recipient: string;
		description: string;
		totalObligated: number;
		sources: {
			vector: boolean;
			keyword: boolean;
			graph: boolean;
		};
		graphNodeIds?: string[];
	}

	interface Props {
		contracts: ContractResult[];
	}

	let { contracts }: Props = $props();

	function formatDollars(amount: number): string {
		if (Math.abs(amount) >= 1_000_000_000) {
			return `$${(amount / 1_000_000_000).toFixed(1)}B`;
		}
		if (Math.abs(amount) >= 1_000_000) {
			return `$${(amount / 1_000_000).toFixed(1)}M`;
		}
		if (Math.abs(amount) >= 1_000) {
			return `$${(amount / 1_000).toFixed(0)}K`;
		}
		return `$${amount.toFixed(0)}`;
	}

	function handleContractClick(contract: ContractResult) {
		if (contract.graphNodeIds && contract.graphNodeIds.length > 0) {
			graphStore.highlightNodes(contract.graphNodeIds);
			graphStore.selectNode(contract.graphNodeIds[0]);
		}
	}
</script>

{#if contracts.length > 0}
	<div class="contract-list">
		<div class="contract-list-header">
			<span class="text-secondary" style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600;">
				Contracts ({contracts.length})
			</span>
		</div>
		{#each contracts as contract (contract.id)}
			<button
				class="contract-item"
				onclick={() => handleContractClick(contract)}
				type="button"
			>
				<div class="contract-header">
					<span class="contract-recipient">{contract.recipient}</span>
					<span class="dollars">{formatDollars(contract.totalObligated)}</span>
				</div>
				<div class="contract-description">{contract.description}</div>
				<div class="contract-sources">
					<RetrievalBadges
						vector={contract.sources.vector ? 1 : 0}
						keyword={contract.sources.keyword ? 1 : 0}
						graph={contract.sources.graph ? 1 : 0}
					/>
				</div>
			</button>
		{/each}
	</div>
{/if}

<style>
	.contract-list {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.contract-list-header {
		padding: 6px 0;
		margin-bottom: 4px;
	}

	.contract-item {
		display: flex;
		flex-direction: column;
		gap: 4px;
		padding: 8px 10px;
		background: var(--bg-surface);
		border: 1px solid var(--border-color);
		border-radius: 6px;
		cursor: pointer;
		transition: all 0.15s ease;
		text-align: left;
		width: 100%;
		font-family: var(--font-sans);
		font-size: 13px;
		color: var(--text-primary);
	}

	.contract-item:hover {
		background: var(--bg-hover);
		border-color: var(--border-accent);
	}

	.contract-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 8px;
	}

	.contract-recipient {
		font-weight: 600;
		font-size: 12px;
		color: var(--accent-blue-light);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		flex: 1;
	}

	.contract-description {
		font-size: 12px;
		color: var(--text-secondary);
		line-height: 1.4;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}

	.contract-sources {
		margin-top: 2px;
	}
</style>
