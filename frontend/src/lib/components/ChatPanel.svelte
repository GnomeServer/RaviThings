<script lang="ts">
	import { chatStore } from '$lib/stores/chat.svelte';
	import { graphStore } from '$lib/stores/graph.svelte';
	import { schematicStore } from '$lib/stores/schematic.svelte';
	import { fetchSSE } from '$lib/api';
	import type { SSEEvent } from '$lib/api';
	import type { RetrievalCounts } from '$lib/stores/chat.svelte';
	import RetrievalBadges from './RetrievalBadges.svelte';
	import ContractList from './ContractList.svelte';
	import type { ContractResult } from './ContractList.svelte';

	let inputValue = $state('');
	let messagesContainer: HTMLDivElement | undefined = $state();
	let currentAbortController: AbortController | null = $state(null);
	let contracts = $state<ContractResult[]>([]);
	let chatMode = $state<'quick' | 'deep'>('quick');
	let recipePhase = $state<string | null>(null);
	let recipeRounds = $state<Array<{ round: number; contracts: number; topics: number; newTopics: number }>>([]);
	let pipelineStatus = $state<{ stage: string; message: string; progress?: number; total?: number } | null>(null);
	let deepAnalysisCounts = $state<{ reviewed: number; relevant: number } | null>(null);

	// Activity log state for deep analysis
	interface LogEntry {
		timestamp: string;
		level: string;
		message: string;
	}
	let activityLogs = $state<LogEntry[]>([]);
	let activityLogExpanded = $state(true);
	let activityLogContainer: HTMLDivElement | undefined = $state();
	let deepAnalysisStartTime: number | null = $state(null);
	let deepAnalysisDone = $state(false);

	function formatElapsed(startTime: number): string {
		const elapsed = Math.floor((Date.now() - startTime) / 1000);
		const mins = Math.floor(elapsed / 60);
		const secs = elapsed % 60;
		return `${mins}:${secs.toString().padStart(2, '0')}`;
	}

	function scrollLogToBottom() {
		if (activityLogContainer && !deepAnalysisDone) {
			requestAnimationFrame(() => {
				if (activityLogContainer) {
					activityLogContainer.scrollTop = activityLogContainer.scrollHeight;
				}
			});
		}
	}

	function scrollToBottom() {
		if (messagesContainer) {
			// Use requestAnimationFrame for a smooth scroll after DOM update
			requestAnimationFrame(() => {
				if (messagesContainer) {
					messagesContainer.scrollTop = messagesContainer.scrollHeight;
				}
			});
		}
	}

	$effect(() => {
		// Auto-scroll when messages change
		if (chatStore.messages.length > 0) {
			scrollToBottom();
		}
	});

	// Watch for pending questions from other panels (e.g. click-to-ask on schematic steps)
	$effect(() => {
		const pending = chatStore.pendingQuestion;
		if (pending && !chatStore.isStreaming) {
			chatStore.clearPendingQuestion();
			inputValue = pending;
			// Use tick-like delay so inputValue is set before sendMessage reads it
			queueMicrotask(() => {
				sendMessage();
			});
		}
	});

	function handleSSEEvent(event: SSEEvent) {
		switch (event.event) {
			case 'status': {
				const data = event.data as { stage: string; message: string; progress?: number; total?: number };
				if (data.stage === 'scoring' && data.progress != null && data.total != null) {
					const pct = data.total > 0 ? Math.round((data.progress / data.total) * 100) : 0;
					pipelineStatus = {
						stage: data.stage,
						message: `Scoring contracts: ${data.progress}/${data.total} (${pct}%)`,
						progress: data.progress,
						total: data.total
					};
				} else {
					pipelineStatus = data;
				}
				if (data.stage === 'done') {
					setTimeout(() => { pipelineStatus = null; }, 2000);
				}
				break;
			}
			case 'retrieval': {
				const data = event.data as RetrievalCounts & {
					contracts?: Array<{
						id: string;
						recipient: string;
						description: string;
						total_obligated: number;
						sources: { vector: boolean; keyword: boolean; graph: boolean };
						graph_node_ids?: string[];
					}>;
				};
				chatStore.setRetrieval({
					vector: data.vector,
					keyword: data.keyword,
					graph: data.graph,
					fused: data.fused
				});
				if (data.contracts) {
					contracts = data.contracts.map((c) => ({
						id: c.id,
						recipient: c.recipient,
						description: c.description,
						totalObligated: c.total_obligated,
						sources: c.sources,
						graphNodeIds: c.graph_node_ids
					}));
				}
				break;
			}
			case 'token': {
				const data = event.data as { content: string };
				chatStore.appendToken(data.content);
				scrollToBottom();
				break;
			}
			case 'graph_highlight': {
				const data = event.data as {
					nodes: Array<{ id: string; name: string; label: string; type: string; community?: number; total_obligated?: number }>;
					edges: Array<{ source: string; target: string; weight: number; edge_type?: string }>;
				};
				// Populate graph store with actual node/edge data
				if (data.nodes && data.nodes.length > 0) {
					const graphNodes = data.nodes.map(n => ({
						id: n.name || n.id?.toString(),
						label: n.label || n.name,
						type: (n.type || 'recipient') as import('$lib/stores/graph.svelte').NodeType,
						community: n.community,
						totalDollars: n.total_obligated
					}));
					const graphEdges = data.edges?.map(e => ({
						source: e.source,
						target: e.target,
						weight: e.weight || 1,
						type: e.edge_type
					})) || [];
					graphStore.setGraph(graphNodes, graphEdges);
					// Highlight all nodes from this result
					const nodeIds = graphNodes.map(n => n.id);
					chatStore.setGraphHighlight({ nodes: nodeIds, edges: data.edges || [] });
					graphStore.highlightPaths(nodeIds, data.edges || []);
				}
				break;
			}
			case 'phase': {
				const data = event.data as { phase: string; sub_queries?: number };
				recipePhase = data.phase;
				break;
			}
			case 'round': {
				const data = event.data as {
					round: number;
					contracts: number;
					topics: number;
					new_topics: number;
				};
				recipeRounds = [
					...recipeRounds,
					{
						round: data.round,
						contracts: data.contracts,
						topics: data.topics,
						newTopics: data.new_topics
					}
				];
				break;
			}
			case 'converged': {
				recipePhase = 'synthesize';
				break;
			}
			case 'log': {
				const data = event.data as { level: string; message: string };
				if (!deepAnalysisStartTime) {
					deepAnalysisStartTime = Date.now();
				}
				const entry: LogEntry = {
					timestamp: formatElapsed(deepAnalysisStartTime),
					level: data.level,
					message: data.message
				};
				activityLogs = [...activityLogs, entry];
				scrollLogToBottom();
				break;
			}
			case 'process_schematic': {
				const data = event.data as any;
				if (data && (data.title || data.steps)) {
					schematicStore.setSchematic(data);
				}
				break;
			}
			case 'done': {
				const data = event.data as {
					total_contracts?: number;
					total_dollars?: number;
					contracts_reviewed?: number;
					contracts_relevant?: number;
				};
				chatStore.finishStream({
					totalContracts: data.total_contracts,
					totalDollars: data.total_dollars
				});
				if (data.contracts_reviewed != null && data.contracts_relevant != null) {
					deepAnalysisCounts = {
						reviewed: data.contracts_reviewed,
						relevant: data.contracts_relevant
					};
				}
				deepAnalysisDone = true;
				currentAbortController = null;
				recipePhase = null;
				recipeRounds = [];
				break;
			}
			case 'error': {
				const data = event.data as { message: string };
				chatStore.setError(data.message);
				currentAbortController = null;
				break;
			}
		}
	}

	function sendMessage() {
		const text = inputValue.trim();
		if (!text || chatStore.isStreaming) return;

		inputValue = '';
		contracts = [];
		deepAnalysisCounts = null;
		activityLogs = [];
		deepAnalysisStartTime = null;
		deepAnalysisDone = false;
		activityLogExpanded = true;
		chatStore.addUserMessage(text);
		chatStore.startAssistantMessage();

		const endpoint = chatMode === 'deep' ? '/api/deep-chat' : '/api/chat';

		const messagesPayload = chatStore.messages
			.filter((m) => !m.isStreaming)
			.map((m) => ({ role: m.role, content: m.content }));

		// Include current schematic so the LLM knows what's on screen
		const currentSchematic = schematicStore.schematic;

		currentAbortController = fetchSSE(
			endpoint,
			{
				messages: messagesPayload,
				schematic: currentSchematic,
			},
			handleSSEEvent
		);
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter' && !event.shiftKey) {
			event.preventDefault();
			sendMessage();
		}
	}

	function cancelStream() {
		if (currentAbortController) {
			currentAbortController.abort();
			currentAbortController = null;
			chatStore.finishStream();
		}
	}

	function clearChat() {
		if (currentAbortController) {
			currentAbortController.abort();
			currentAbortController = null;
		}
		chatStore.clearMessages();
		contracts = [];
		graphStore.clearHighlights();
	}

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
</script>

<section class="chat-panel">
	<div class="panel-header">
		<div class="header-left">
			<span class="panel-title">Chat</span>
			{#if chatStore.isStreaming}
				<span class="streaming-indicator"></span>
			{/if}
		</div>
		<div class="header-right">
			{#if chatStore.messages.length > 0}
				<button class="btn" style="font-size: 11px;" onclick={clearChat}>Clear</button>
			{/if}
		</div>
	</div>

	<div class="messages-container" bind:this={messagesContainer}>
		{#if chatStore.messages.length === 0}
			<div class="empty-state">
				<div class="empty-icon">?</div>
				<p>Ask about DOE contracts</p>
				<p class="text-muted" style="font-size: 12px;">
					Try: "How does DOE make solid-state batteries?"
				</p>
			</div>
		{:else}
			{#each chatStore.messages as message (message.id)}
				<div class="message message-{message.role}">
					<div class="message-bubble message-bubble-{message.role}">
						{#if message.role === 'assistant' && message.retrieval}
							<div class="message-retrieval">
								<RetrievalBadges
									vector={message.retrieval.vector}
									keyword={message.retrieval.keyword}
									graph={message.retrieval.graph}
									web={(message.retrieval as any).web || 0}
								/>
							</div>
						{/if}
						<div class="message-content">
							{#if message.content}
								{message.content}
							{:else if message.isStreaming}
								<span class="typing-cursor"></span>
							{/if}
							{#if message.isStreaming && message.content}
								<span class="typing-cursor"></span>
							{/if}
						</div>
						{#if message.role === 'assistant' && message.totalContracts != null}
							<div class="message-summary">
								<span class="text-muted" style="font-size: 11px;">
									{message.totalContracts} contracts
									{#if message.totalDollars != null}
										&middot; <span class="dollars">{formatDollars(message.totalDollars)}</span>
									{/if}
								</span>
							</div>
						{/if}
					</div>
				</div>
			{/each}

			{#if recipePhase}
				<div class="recipe-progress">
					<div class="recipe-phase">
						Phase: <span class="text-primary">{recipePhase}</span>
					</div>
					{#each recipeRounds as round}
						<div class="recipe-round text-muted" style="font-size: 11px;">
							Round {round.round}: {round.contracts} contracts, {round.topics} topics (+{round.newTopics} new)
						</div>
					{/each}
				</div>
			{/if}

			{#if contracts.length > 0}
				<div class="contracts-section">
					<ContractList {contracts} />
				</div>
			{/if}
		{/if}
	</div>

	{#if pipelineStatus}
		<div class="status-bar" class:status-done={pipelineStatus.stage === 'done'} class:status-error={pipelineStatus.stage === 'schematic_failed'} class:status-deep={chatMode === 'deep' && pipelineStatus.stage !== 'done'}>
			<span class="status-spinner" class:status-spinner-done={pipelineStatus.stage === 'done'} class:status-spinner-deep={chatMode === 'deep' && pipelineStatus.stage !== 'done'}></span>
			<span class="status-text">{pipelineStatus.message}</span>
			{#if pipelineStatus.stage === 'scoring' && pipelineStatus.total}
				<div class="scoring-progress-bar">
					<div class="scoring-progress-fill" style="width: {Math.round(((pipelineStatus.progress ?? 0) / pipelineStatus.total) * 100)}%"></div>
				</div>
			{/if}
		</div>
	{/if}

	{#if activityLogs.length > 0}
		<div class="activity-log-panel">
			<button class="activity-log-toggle" onclick={() => activityLogExpanded = !activityLogExpanded}>
				<span class="activity-log-toggle-icon">{activityLogExpanded ? '\u25BC' : '\u25B6'}</span>
				<span class="activity-log-toggle-label">Activity Log</span>
				<span class="activity-log-count">{activityLogs.length}</span>
				{#if !deepAnalysisDone}
					<span class="activity-log-live"></span>
				{/if}
			</button>
			{#if activityLogExpanded}
				<div class="activity-log-entries" bind:this={activityLogContainer}>
					{#each activityLogs as entry}
						<div class="activity-log-entry">
							<span class="log-timestamp">{entry.timestamp}</span>
							<span class="log-level log-level-{entry.level}">
								{#if entry.level === 'info'}INF
								{:else if entry.level === 'detail'}DTL
								{:else if entry.level === 'success'}OK
								{:else if entry.level === 'warn'}WRN
								{:else}{entry.level.toUpperCase().slice(0, 3)}
								{/if}
							</span>
							<span class="log-message">{entry.message}</span>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	{/if}

	{#if chatStore.error}
		<div class="error-bar">
			<span>{chatStore.error}</span>
		</div>
	{/if}

	<div class="input-bar">
		<div class="input-row">
			<input
				type="text"
				class="chat-input"
				placeholder="Ask about DOE contracts..."
				bind:value={inputValue}
				onkeydown={handleKeydown}
				disabled={chatStore.isStreaming}
			/>
			{#if chatStore.isStreaming}
				<button class="btn" onclick={cancelStream}>Stop</button>
			{:else}
				<button
					class="btn btn-primary"
					onclick={sendMessage}
					disabled={!inputValue.trim()}
				>
					Send
				</button>
			{/if}
		</div>
		<div class="input-options">
			<div class="mode-toggle" class:mode-toggle-disabled={chatStore.isStreaming}>
				<button
					class="mode-btn"
					class:mode-btn-active-quick={chatMode === 'quick'}
					disabled={chatStore.isStreaming}
					onclick={() => chatMode = 'quick'}
				>Quick</button>
				<button
					class="mode-btn"
					class:mode-btn-active-deep={chatMode === 'deep'}
					disabled={chatStore.isStreaming}
					onclick={() => chatMode = 'deep'}
				>Deep Analysis</button>
			</div>
			{#if chatMode === 'deep'}
				<span class="deep-warning">~3-5 min</span>
			{/if}
		</div>
	</div>
</section>

<style>
	.chat-panel {
		display: flex;
		flex-direction: column;
		height: 100%;
		overflow: hidden;
	}

	/* Header */
	.panel-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 8px 16px;
		border-bottom: 1px solid var(--border-color);
		flex-shrink: 0;
		background: rgba(0, 0, 0, 0.15);
	}

	.panel-title {
		font-weight: 600;
		font-size: 13px;
		color: var(--text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.header-left {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.header-right {
		display: flex;
		align-items: center;
		gap: 6px;
	}

	.streaming-indicator {
		display: inline-block;
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: var(--accent-green-light);
		animation: pulse 1.5s ease-in-out infinite;
	}

	@keyframes pulse {
		0%,
		100% {
			opacity: 1;
		}
		50% {
			opacity: 0.3;
		}
	}

	/* Messages */
	.messages-container {
		flex: 1;
		overflow-y: auto;
		padding: 16px;
		display: flex;
		flex-direction: column;
		gap: 12px;
	}

	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		height: 100%;
		gap: 8px;
		color: var(--text-secondary);
	}

	.empty-icon {
		font-size: 48px;
		opacity: 0.3;
	}

	.empty-state p {
		font-size: 16px;
		font-weight: 500;
	}

	/* Message bubbles */
	.message {
		display: flex;
		max-width: 85%;
	}

	.message-user {
		align-self: flex-end;
	}

	.message-assistant {
		align-self: flex-start;
	}

	.message-bubble {
		padding: 8px 12px;
		border-radius: 10px;
		font-size: 13px;
		line-height: 1.5;
		word-wrap: break-word;
		white-space: pre-wrap;
	}

	.message-bubble-user {
		background: var(--accent-blue);
		color: white;
		border-bottom-right-radius: 2px;
	}

	.message-bubble-assistant {
		background: var(--bg-surface);
		color: var(--text-primary);
		border: 1px solid var(--border-color);
		border-bottom-left-radius: 2px;
	}

	.message-retrieval {
		margin-bottom: 6px;
	}

	.message-content {
		min-height: 1em;
	}

	.message-summary {
		margin-top: 8px;
		padding-top: 6px;
		border-top: 1px solid var(--border-color);
	}

	.typing-cursor {
		display: inline-block;
		width: 2px;
		height: 14px;
		background: var(--accent-blue-light);
		margin-left: 2px;
		vertical-align: text-bottom;
		animation: blink 1s step-end infinite;
	}

	@keyframes blink {
		0%,
		100% {
			opacity: 1;
		}
		50% {
			opacity: 0;
		}
	}

	/* Recipe progress */
	.recipe-progress {
		padding: 8px 12px;
		background: var(--bg-panel-alt);
		border: 1px solid var(--accent-purple);
		border-radius: 8px;
		display: flex;
		flex-direction: column;
		gap: 4px;
	}

	.recipe-phase {
		font-size: 12px;
		font-weight: 600;
		color: var(--accent-purple-light);
		text-transform: capitalize;
	}

	.recipe-round {
		padding-left: 8px;
	}

	/* Contracts section */
	.contracts-section {
		padding-top: 8px;
	}

	/* Status bar */
	.status-bar {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 6px 16px;
		background: rgba(124, 58, 237, 0.1);
		border-top: 1px solid rgba(124, 58, 237, 0.3);
		color: #c4b5fd;
		font-size: 12px;
		flex-shrink: 0;
		transition: all 0.3s ease;
	}

	.status-done {
		background: rgba(5, 150, 105, 0.1);
		border-top-color: rgba(5, 150, 105, 0.3);
		color: #6ee7b7;
	}

	.status-error {
		background: rgba(239, 68, 68, 0.1);
		border-top-color: rgba(239, 68, 68, 0.3);
		color: #fca5a5;
	}

	.status-spinner {
		width: 12px;
		height: 12px;
		border: 2px solid rgba(124, 58, 237, 0.3);
		border-top-color: #a78bfa;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
		flex-shrink: 0;
	}

	.status-spinner-done {
		border-color: #6ee7b7;
		animation: none;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	.status-text {
		font-family: var(--font-mono);
		letter-spacing: 0.02em;
	}

	/* Error bar */
	.error-bar {
		padding: 8px 16px;
		background: rgba(239, 68, 68, 0.15);
		border-top: 1px solid rgba(239, 68, 68, 0.3);
		color: #fca5a5;
		font-size: 12px;
		flex-shrink: 0;
	}

	/* Input area */
	.input-bar {
		display: flex;
		flex-direction: column;
		gap: 6px;
		padding: 12px 16px;
		border-top: 1px solid var(--border-color);
		background: rgba(0, 0, 0, 0.1);
		flex-shrink: 0;
	}

	.input-row {
		display: flex;
		gap: 8px;
	}

	.chat-input {
		flex: 1;
	}

	.input-options {
		display: flex;
		align-items: center;
		gap: 12px;
	}

	/* Mode toggle */
	.mode-toggle {
		display: flex;
		border-radius: 6px;
		overflow: hidden;
		border: 1px solid var(--border-accent);
	}

	.mode-toggle-disabled {
		opacity: 0.5;
		pointer-events: none;
	}

	.mode-btn {
		padding: 3px 12px;
		font-size: 11px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		background: var(--bg-surface);
		color: var(--text-muted);
		border: none;
		cursor: pointer;
		transition: all 0.15s ease;
		white-space: nowrap;
	}

	.mode-btn:not(:last-child) {
		border-right: 1px solid var(--border-accent);
	}

	.mode-btn:hover:not(:disabled) {
		background: var(--bg-hover);
		color: var(--text-secondary);
	}

	.mode-btn-active-quick {
		background: rgba(29, 78, 216, 0.25);
		color: var(--accent-blue-light);
	}

	.mode-btn-active-deep {
		background: rgba(217, 119, 6, 0.2);
		color: #fbbf24;
	}

	.deep-warning {
		font-size: 10px;
		font-weight: 600;
		color: #d97706;
		background: rgba(217, 119, 6, 0.12);
		padding: 2px 8px;
		border-radius: 9999px;
		border: 1px solid rgba(217, 119, 6, 0.3);
		letter-spacing: 0.02em;
	}

	/* Deep analysis status bar variant */
	.status-deep {
		background: rgba(217, 119, 6, 0.1);
		border-top-color: rgba(217, 119, 6, 0.3);
		color: #fbbf24;
	}

	.status-spinner-deep {
		border-color: rgba(217, 119, 6, 0.3);
		border-top-color: #fbbf24;
	}

	/* Scoring progress bar */
	.scoring-progress-bar {
		flex: 1;
		max-width: 120px;
		height: 4px;
		background: rgba(217, 119, 6, 0.2);
		border-radius: 2px;
		overflow: hidden;
		margin-left: 8px;
	}

	.scoring-progress-fill {
		height: 100%;
		background: #d97706;
		border-radius: 2px;
		transition: width 0.3s ease;
	}

	/* Activity log panel */
	.activity-log-panel {
		flex-shrink: 0;
		border-top: 1px solid rgba(100, 100, 120, 0.3);
		background: rgba(0, 0, 0, 0.25);
	}

	.activity-log-toggle {
		display: flex;
		align-items: center;
		gap: 6px;
		width: 100%;
		padding: 5px 16px;
		background: rgba(0, 0, 0, 0.15);
		border: none;
		border-bottom: 1px solid rgba(100, 100, 120, 0.2);
		color: var(--text-secondary);
		font-size: 11px;
		font-weight: 600;
		cursor: pointer;
		text-align: left;
		letter-spacing: 0.04em;
		text-transform: uppercase;
	}

	.activity-log-toggle:hover {
		background: rgba(100, 100, 120, 0.15);
	}

	.activity-log-toggle-icon {
		font-size: 9px;
		color: var(--text-muted);
	}

	.activity-log-toggle-label {
		flex: 1;
	}

	.activity-log-count {
		font-size: 10px;
		font-weight: 600;
		color: var(--text-muted);
		background: rgba(100, 100, 120, 0.2);
		padding: 1px 6px;
		border-radius: 9999px;
	}

	.activity-log-live {
		display: inline-block;
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: #22c55e;
		animation: pulse 1.5s ease-in-out infinite;
	}

	.activity-log-entries {
		max-height: 200px;
		overflow-y: auto;
		padding: 4px 0;
		scroll-behavior: smooth;
	}

	.activity-log-entry {
		display: flex;
		align-items: flex-start;
		gap: 8px;
		padding: 2px 16px;
		font-family: var(--font-mono, 'SF Mono', 'Fira Code', 'Fira Mono', monospace);
		font-size: 11px;
		line-height: 1.4;
	}

	.activity-log-entry:hover {
		background: rgba(100, 100, 120, 0.08);
	}

	.log-timestamp {
		flex-shrink: 0;
		color: var(--text-muted);
		min-width: 36px;
		text-align: right;
		opacity: 0.6;
	}

	.log-level {
		flex-shrink: 0;
		font-weight: 700;
		font-size: 10px;
		min-width: 28px;
		text-align: center;
		padding: 0 2px;
		border-radius: 3px;
	}

	.log-level-info {
		color: #60a5fa;
		background: rgba(96, 165, 250, 0.1);
	}

	.log-level-detail {
		color: #9ca3af;
		background: rgba(156, 163, 175, 0.1);
	}

	.log-level-success {
		color: #34d399;
		background: rgba(52, 211, 153, 0.1);
	}

	.log-level-warn {
		color: #fbbf24;
		background: rgba(251, 191, 36, 0.1);
	}

	.log-message {
		color: var(--text-primary);
		word-break: break-word;
		opacity: 0.9;
	}
</style>
