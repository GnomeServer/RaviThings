<script lang="ts">
	import { graphStore } from '$lib/stores/graph.svelte';
	import type { GraphNode, NodeType } from '$lib/stores/graph.svelte';
	import { fetchJSON } from '$lib/api';

	let containerEl: HTMLDivElement | undefined = $state();
	let graphInstance: ReturnType<typeof initGraph> | null = $state(null);
	let showLabels = $state(true);

	// Node color mapping using CSS custom property values
	const NODE_COLORS: Record<NodeType, string> = {
		recipient: '#3b82f6',
		topic: '#a78bfa',
		psc: '#fb923c',
		naics: '#34d399'
	};

	const HIGHLIGHT_COLOR = '#a78bfa';
	const DIM_OPACITY = 0.2;

	// Compute min/max for sizing
	let dollarRange = $derived.by(() => {
		const dollars = graphStore.nodes
			.map((n) => n.totalDollars ?? 0)
			.filter((d) => d > 0);
		if (dollars.length === 0) return { min: 0, max: 1 };
		return {
			min: Math.min(...dollars),
			max: Math.max(...dollars)
		};
	});

	function nodeSize(node: GraphNode): number {
		const MIN_SIZE = 2;
		const MAX_SIZE = 20;
		const d = node.totalDollars ?? 0;
		if (d <= 0 || dollarRange.max <= dollarRange.min) return MIN_SIZE;
		const logMin = Math.log1p(dollarRange.min);
		const logMax = Math.log1p(dollarRange.max);
		const logVal = Math.log1p(d);
		const t = (logVal - logMin) / (logMax - logMin);
		return MIN_SIZE + t * (MAX_SIZE - MIN_SIZE);
	}

	function maxEdgeWeight(): number {
		const weights = graphStore.edges.map((e) => e.weight).filter((w) => w > 0);
		return weights.length > 0 ? Math.max(...weights) : 1;
	}

	function initGraph(container: HTMLElement) {
		// Dynamic import because force-graph requires DOM (canvas)
		let fg: any = null;
		let destroyed = false;

		(async () => {
			const ForceGraph = (await import('force-graph')).default;
			if (destroyed) return;

			fg = ForceGraph()(container)
				.backgroundColor('transparent')
				.nodeId('id')
				.nodeLabel((node: any) => {
					const n = node as GraphNode;
					const dollars = n.totalDollars
						? ` ($${(n.totalDollars / 1_000_000).toFixed(1)}M)`
						: '';
					return `${n.label}${dollars}`;
				})
				.nodeVal((node: any) => nodeSize(node as GraphNode))
				.nodeCanvasObjectMode(() => 'replace')
				.nodeCanvasObject((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
					const n = node as GraphNode & { x: number; y: number };
					const size = nodeSize(n) * 0.6;
					const color = NODE_COLORS[n.type] || '#666';
					const isHighlighted =
						graphStore.highlightedNodeIds.size === 0 ||
						graphStore.highlightedNodeIds.has(n.id);
					const isSelected = graphStore.selectedNodeId === n.id;
					const alpha = isHighlighted ? 1 : DIM_OPACITY;

					ctx.globalAlpha = alpha;

					// Glow for highlighted nodes
					if (graphStore.highlightedNodeIds.size > 0 && graphStore.highlightedNodeIds.has(n.id)) {
						ctx.shadowColor = HIGHLIGHT_COLOR;
						ctx.shadowBlur = 12;
					}

					// Draw shape based on type
					ctx.fillStyle = color;
					ctx.beginPath();

					switch (n.type) {
						case 'recipient':
							// Circle
							ctx.arc(n.x, n.y, size, 0, 2 * Math.PI);
							ctx.fill();
							break;
						case 'topic':
							// Rounded square
							drawRoundedRect(ctx, n.x - size, n.y - size, size * 2, size * 2, size * 0.3);
							ctx.fill();
							break;
						case 'psc':
							// Diamond
							ctx.moveTo(n.x, n.y - size * 1.2);
							ctx.lineTo(n.x + size, n.y);
							ctx.lineTo(n.x, n.y + size * 1.2);
							ctx.lineTo(n.x - size, n.y);
							ctx.closePath();
							ctx.fill();
							break;
						case 'naics':
							// Ring
							ctx.arc(n.x, n.y, size, 0, 2 * Math.PI);
							ctx.strokeStyle = color;
							ctx.lineWidth = size * 0.35;
							ctx.stroke();
							break;
						default:
							ctx.arc(n.x, n.y, size, 0, 2 * Math.PI);
							ctx.fill();
					}

					// Selected node border
					if (isSelected) {
						ctx.strokeStyle = '#ffffff';
						ctx.lineWidth = 1.5;
						ctx.beginPath();
						ctx.arc(n.x, n.y, size + 2, 0, 2 * Math.PI);
						ctx.stroke();
					}

					ctx.shadowColor = 'transparent';
					ctx.shadowBlur = 0;

					// Label
					if (showLabels && globalScale > 0.8) {
						const label = n.label;
						const fontSize = Math.max(10 / globalScale, 2);
						ctx.font = `${fontSize}px Inter, sans-serif`;
						ctx.textAlign = 'center';
						ctx.textBaseline = 'top';
						ctx.fillStyle = isHighlighted
							? 'rgba(226, 232, 240, 0.9)'
							: 'rgba(226, 232, 240, 0.3)';
						const maxLabelWidth = 60 / globalScale;
						const truncated =
							ctx.measureText(label).width > maxLabelWidth
								? label.substring(0, Math.floor(label.length * 0.6)) + '...'
								: label;
						ctx.fillText(truncated, n.x, n.y + size + 2);
					}

					ctx.globalAlpha = 1;
				})
				.nodePointerAreaPaint((node: any, paintColor: string, ctx: CanvasRenderingContext2D) => {
					const n = node as GraphNode & { x: number; y: number };
					const size = nodeSize(n) * 0.6 + 3; // slightly bigger hit area
					ctx.fillStyle = paintColor;
					ctx.beginPath();
					ctx.arc(n.x, n.y, size, 0, 2 * Math.PI);
					ctx.fill();
				})
				.linkColor((link: any) => {
					if (graphStore.highlightedNodeIds.size === 0) {
						return 'rgba(100, 116, 139, 0.4)';
					}
					const src = typeof link.source === 'object' ? link.source.id : link.source;
					const tgt = typeof link.target === 'object' ? link.target.id : link.target;
					const isHighlighted = graphStore.highlightedEdges.some(
						(e) =>
							(e.source === src && e.target === tgt) ||
							(e.source === tgt && e.target === src)
					);
					return isHighlighted
						? 'rgba(167, 139, 250, 0.8)'
						: 'rgba(100, 116, 139, 0.12)';
				})
				.linkWidth((link: any) => {
					const maxW = maxEdgeWeight();
					const w = link.weight ?? 1;
					return 0.5 + (w / maxW) * 3;
				})
				.onNodeClick((node: any) => {
					const n = node as GraphNode;
					graphStore.selectNode(n.id);
					expandNode(n.id);
				})
				.warmupTicks(50)
				.cooldownTime(3000)
				.minZoom(0.1)
				.maxZoom(10);

			// Set initial dimensions
			const rect = container.getBoundingClientRect();
			if (rect.width > 0 && rect.height > 0) {
				fg.width(rect.width).height(rect.height);
			}

			// If there is already graph data, feed it in
			updateGraphData();
		})();

		return {
			get instance() {
				return fg;
			},
			destroy() {
				destroyed = true;
				if (fg) {
					fg.pauseAnimation();
					fg._destructor();
				}
			}
		};
	}

	function drawRoundedRect(
		ctx: CanvasRenderingContext2D,
		x: number,
		y: number,
		w: number,
		h: number,
		r: number
	) {
		ctx.beginPath();
		ctx.moveTo(x + r, y);
		ctx.lineTo(x + w - r, y);
		ctx.quadraticCurveTo(x + w, y, x + w, y + r);
		ctx.lineTo(x + w, y + h - r);
		ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
		ctx.lineTo(x + r, y + h);
		ctx.quadraticCurveTo(x, y + h, x, y + h - r);
		ctx.lineTo(x, y + r);
		ctx.quadraticCurveTo(x, y, x + r, y);
		ctx.closePath();
	}

	function updateGraphData() {
		const fg = graphInstance?.instance;
		if (!fg) return;

		const nodes = graphStore.nodes.map((n) => ({ ...n }));
		const links = graphStore.edges.map((e) => ({
			source: e.source,
			target: e.target,
			weight: e.weight,
			type: e.type
		}));

		fg.graphData({ nodes, links });
	}

	async function expandNode(nodeId: string) {
		try {
			graphStore.setLoading(true);
			const data = await fetchJSON<{
				nodes: GraphNode[];
				edges: Array<{ source: string; target: string; weight: number; type?: string }>;
			}>(`/api/graph/expand/${encodeURIComponent(nodeId)}`);

			graphStore.addNodes(data.nodes);
			graphStore.addEdges(data.edges);
		} catch (err) {
			console.error('Failed to expand node:', err);
		} finally {
			graphStore.setLoading(false);
		}
	}

	async function loadInitialGraph() {
		try {
			graphStore.setLoading(true);
			const data = await fetchJSON<{
				nodes: GraphNode[];
				edges: Array<{ source: string; target: string; weight: number; type?: string }>;
			}>('/api/graph?entity=*&hops=1');

			graphStore.setGraph(data.nodes, data.edges);
		} catch (err) {
			console.error('Failed to load initial graph:', err);
		} finally {
			graphStore.setLoading(false);
		}
	}

	function zoomToFit() {
		graphInstance?.instance?.zoomToFit(400, 40);
	}

	function toggleLabels() {
		showLabels = !showLabels;
	}

	// Initialize force-graph when container mounts
	$effect(() => {
		if (containerEl && !graphInstance) {
			graphInstance = initGraph(containerEl);
			// Don't load initial graph — it will be populated by chat queries
		}

		return () => {
			if (graphInstance) {
				graphInstance.destroy();
				graphInstance = null;
			}
		};
	});

	// Update graph data when store changes
	$effect(() => {
		// Access reactive dependencies
		const _ = graphStore.nodes.length;
		const __ = graphStore.edges.length;
		updateGraphData();
	});

	// Re-render when highlights change (trigger canvas redraw)
	$effect(() => {
		const _ = graphStore.highlightedNodeIds.size;
		const __ = graphStore.highlightedEdges.length;
		const ___ = graphStore.selectedNodeId;
		// Force re-render by nudging the graph
		const fg = graphInstance?.instance;
		if (fg) {
			// Trigger a re-render without restarting simulation
			fg.nodeColor(fg.nodeColor());
		}
	});

	// Handle resize
	$effect(() => {
		if (!containerEl) return;

		const observer = new ResizeObserver((entries) => {
			for (const entry of entries) {
				const { width, height } = entry.contentRect;
				const fg = graphInstance?.instance;
				if (fg && width > 0 && height > 0) {
					fg.width(width).height(height);
				}
			}
		});

		observer.observe(containerEl);
		return () => observer.disconnect();
	});
</script>

<section class="graph-panel">
	<div class="panel-header">
		<span class="panel-title">Knowledge Graph</span>
		<div class="panel-controls">
			{#if graphStore.isLoading}
				<span class="loading-text">Loading...</span>
			{/if}
			<button class="btn" style="font-size: 11px;" onclick={zoomToFit}>Zoom to Fit</button>
			<button
				class="btn"
				style="font-size: 11px;"
				class:btn-active={showLabels}
				onclick={toggleLabels}
			>
				Labels
			</button>
		</div>
	</div>

	<div class="graph-container" bind:this={containerEl}>
		{#if graphStore.nodes.length === 0 && !graphStore.isLoading}
			<div class="placeholder-content">
				<div class="placeholder-icon">&#x1F578;</div>
				<p>Knowledge Graph</p>
				<p class="text-muted" style="font-size: 12px;">
					Ask a question to populate the graph
				</p>
			</div>
		{/if}
	</div>

	<!-- Legend overlay -->
	<div class="graph-legend">
		<div class="legend-item">
			<span class="legend-shape legend-circle" style="background: var(--node-recipient);"></span>
			<span class="text-muted">Recipient</span>
		</div>
		<div class="legend-item">
			<span class="legend-shape legend-square" style="background: var(--node-topic);"></span>
			<span class="text-muted">Topic</span>
		</div>
		<div class="legend-item">
			<span class="legend-shape legend-diamond" style="background: var(--node-psc);"></span>
			<span class="text-muted">PSC</span>
		</div>
		<div class="legend-item">
			<span class="legend-shape legend-ring"></span>
			<span class="text-muted">NAICS</span>
		</div>
	</div>

	<!-- Zoom controls overlay -->
	<div class="zoom-controls">
		<button
			class="zoom-btn"
			onclick={() => {
				const fg = graphInstance?.instance;
				if (fg) fg.zoom(fg.zoom() * 1.4, 300);
			}}
			title="Zoom in"
		>+</button>
		<button
			class="zoom-btn"
			onclick={() => {
				const fg = graphInstance?.instance;
				if (fg) fg.zoom(fg.zoom() * 0.7, 300);
			}}
			title="Zoom out"
		>-</button>
		<button class="zoom-btn" onclick={zoomToFit} title="Zoom to fit">
			&#x2922;
		</button>
	</div>
</section>

<style>
	.graph-panel {
		display: flex;
		flex-direction: column;
		height: 100%;
		position: relative;
		overflow: hidden;
	}

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

	.panel-controls {
		display: flex;
		align-items: center;
		gap: 6px;
	}

	.loading-text {
		font-size: 11px;
		color: var(--accent-blue-light);
		animation: pulse 1.5s ease-in-out infinite;
	}

	@keyframes pulse {
		0%, 100% { opacity: 1; }
		50% { opacity: 0.3; }
	}

	.btn-active {
		background: var(--accent-blue);
		border-color: var(--accent-blue);
		color: white;
	}

	/* Graph container */
	.graph-container {
		flex: 1;
		position: relative;
		overflow: hidden;
	}

	.graph-container :global(.force-graph-container) {
		width: 100% !important;
		height: 100% !important;
	}

	.placeholder-content {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		height: 100%;
		gap: 8px;
		color: var(--text-secondary);
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		pointer-events: none;
	}

	.placeholder-icon {
		font-size: 48px;
		opacity: 0.3;
	}

	.placeholder-content p {
		font-size: 16px;
		font-weight: 500;
	}

	/* Legend */
	.graph-legend {
		position: absolute;
		bottom: 16px;
		left: 16px;
		display: flex;
		flex-direction: column;
		gap: 6px;
		padding: 10px 14px;
		background: rgba(10, 14, 26, 0.85);
		border: 1px solid var(--border-color);
		border-radius: 8px;
		backdrop-filter: blur(8px);
		z-index: 10;
	}

	.legend-item {
		display: flex;
		align-items: center;
		gap: 8px;
		font-size: 11px;
	}

	.legend-shape {
		width: 10px;
		height: 10px;
		flex-shrink: 0;
	}

	.legend-circle {
		border-radius: 50%;
	}

	.legend-square {
		border-radius: 2px;
	}

	.legend-diamond {
		width: 10px;
		height: 10px;
		transform: rotate(45deg);
	}

	.legend-ring {
		border-radius: 50%;
		background: transparent;
		border: 2.5px solid var(--node-naics);
	}

	/* Zoom controls */
	.zoom-controls {
		position: absolute;
		top: 60px;
		right: 16px;
		display: flex;
		flex-direction: column;
		gap: 2px;
		z-index: 10;
	}

	.zoom-btn {
		width: 32px;
		height: 32px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: rgba(10, 14, 26, 0.85);
		border: 1px solid var(--border-color);
		border-radius: 6px;
		color: var(--text-primary);
		font-size: 16px;
		cursor: pointer;
		backdrop-filter: blur(8px);
		transition: all 0.15s ease;
		font-family: var(--font-sans);
	}

	.zoom-btn:hover {
		background: var(--bg-hover);
		border-color: var(--border-accent);
	}
</style>
