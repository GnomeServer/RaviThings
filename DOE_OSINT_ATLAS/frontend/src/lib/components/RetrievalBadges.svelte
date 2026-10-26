<script lang="ts">
	interface Props {
		vector: number;
		keyword: number;
		graph: number;
		web?: number;
	}

	let { vector, keyword, graph, web = 0 }: Props = $props();
</script>

<div class="retrieval-badges">
	{#if vector > 0}
		<span class="badge badge-vector">Vector: {vector}</span>
	{/if}
	{#if keyword > 0}
		<span class="badge badge-keyword">Keyword: {keyword}</span>
	{/if}
	{#if graph > 0}
		<span class="badge badge-graph">Graph: {graph}</span>
	{/if}
	{#if web > 0}
		<span class="badge badge-web">Web: {web}</span>
	{/if}
</div>

<style>
	.retrieval-badges {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
	}
</style>
