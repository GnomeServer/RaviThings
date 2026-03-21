/**
 * Graph store — manages nodes, edges, highlights, and selection for the
 * force-graph visualization. Uses Svelte 5 runes ($state) for reactivity.
 */

export type NodeType = 'recipient' | 'psc' | 'naics' | 'topic';

export interface GraphNode {
	id: string;
	label: string;
	type: NodeType;
	community?: number;
	totalDollars?: number;
	metadata?: Record<string, unknown>;
}

export interface GraphEdge {
	source: string;
	target: string;
	weight: number;
	type?: string;
}

function createGraphStore() {
	let nodes = $state<GraphNode[]>([]);
	let edges = $state<GraphEdge[]>([]);
	let highlightedNodeIds = $state<Set<string>>(new Set());
	let highlightedEdges = $state<Array<{ source: string; target: string }>>([]);
	let selectedNodeId = $state<string | null>(null);
	let isLoading = $state(false);

	function setGraph(newNodes: GraphNode[], newEdges: GraphEdge[]): void {
		nodes = newNodes;
		edges = newEdges;
	}

	function addNodes(newNodes: GraphNode[]): void {
		const existingIds = new Set(nodes.map((n) => n.id));
		const toAdd = newNodes.filter((n) => !existingIds.has(n.id));
		nodes = [...nodes, ...toAdd];
	}

	function addEdges(newEdges: GraphEdge[]): void {
		edges = [...edges, ...newEdges];
	}

	function highlightNodes(nodeIds: string[]): void {
		highlightedNodeIds = new Set(nodeIds);
	}

	function highlightPaths(
		nodeIds: string[],
		edgePairs: Array<{ source: string; target: string }>
	): void {
		highlightedNodeIds = new Set(nodeIds);
		highlightedEdges = edgePairs;
	}

	function clearHighlights(): void {
		highlightedNodeIds = new Set();
		highlightedEdges = [];
	}

	function selectNode(nodeId: string | null): void {
		selectedNodeId = nodeId;
	}

	function setLoading(loading: boolean): void {
		isLoading = loading;
	}

	function clearGraph(): void {
		nodes = [];
		edges = [];
		highlightedNodeIds = new Set();
		highlightedEdges = [];
		selectedNodeId = null;
	}

	return {
		get nodes() {
			return nodes;
		},
		get edges() {
			return edges;
		},
		get highlightedNodeIds() {
			return highlightedNodeIds;
		},
		get highlightedEdges() {
			return highlightedEdges;
		},
		get selectedNodeId() {
			return selectedNodeId;
		},
		get isLoading() {
			return isLoading;
		},
		setGraph,
		addNodes,
		addEdges,
		highlightNodes,
		highlightPaths,
		clearHighlights,
		selectNode,
		setLoading,
		clearGraph
	};
}

export const graphStore = createGraphStore();
