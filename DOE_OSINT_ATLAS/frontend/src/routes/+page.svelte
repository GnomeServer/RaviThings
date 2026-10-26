<script lang="ts">
	import { graphStore } from '$lib/stores/graph.svelte';
	import { filtersStore } from '$lib/stores/filters.svelte';
	import { chatStore } from '$lib/stores/chat.svelte';
	import Toolbar from '$lib/components/Toolbar.svelte';
	import ChatPanel from '$lib/components/ChatPanel.svelte';
	import SchematicPanel from '$lib/components/SchematicPanel.svelte';

	let recipeMode = $state(false);

	function toggleRecipeMode() {
		recipeMode = !recipeMode;
	}

	function handleStepClick(stepName: string) {
		chatStore.setPendingQuestion(
			`Tell me more about the ${stepName} step — what specific equipment, temperatures, materials, and parameters are used?`
		);
	}
</script>

<div class="app-container">
	<!-- Top Toolbar -->
	<Toolbar
		nodeCount={graphStore.nodes.length}
		edgeCount={graphStore.edges.length}
		{recipeMode}
		onToggleRecipe={toggleRecipeMode}
	/>

	<!-- Split Pane Layout -->
	<main class="split-pane">
		<!-- Left Panel: Chat (40%) -->
		<section class="panel panel-chat">
			<ChatPanel />
		</section>

		<!-- Divider -->
		<div class="divider"></div>

		<!-- Right Panel: Schematic (60%) -->
		<section class="panel panel-graph">
			<SchematicPanel onStepClick={handleStepClick} />
		</section>
	</main>
</div>

<style>
	.app-container {
		display: flex;
		flex-direction: column;
		height: 100vh;
		width: 100vw;
		overflow: hidden;
		background: var(--bg-base);
	}

	/* Split Pane */
	.split-pane {
		display: flex;
		flex: 1;
		overflow: hidden;
	}

	.panel {
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}

	.panel-chat {
		width: 40%;
		min-width: 320px;
		background: var(--bg-panel);
		border-right: 1px solid var(--border-color);
	}

	.panel-graph {
		width: 60%;
		min-width: 400px;
		background: var(--bg-panel-alt);
		position: relative;
	}

	.divider {
		width: 1px;
		background: var(--border-color);
		cursor: col-resize;
		flex-shrink: 0;
	}

	.divider:hover {
		background: var(--accent-blue);
		width: 3px;
	}
</style>
