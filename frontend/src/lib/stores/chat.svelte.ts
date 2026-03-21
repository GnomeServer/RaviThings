/**
 * Chat store — manages message history, streaming state, and retrieval counts.
 * Uses Svelte 5 runes ($state) for reactivity.
 */

export interface RetrievalCounts {
	vector: number;
	keyword: number;
	graph: number;
	fused: number;
}

export interface ChatMessage {
	id: string;
	role: 'user' | 'assistant';
	content: string;
	timestamp: number;
	retrieval?: RetrievalCounts;
	graphHighlight?: {
		nodes: string[];
		edges: Array<{ source: string; target: string }>;
	};
	totalContracts?: number;
	totalDollars?: number;
	isStreaming?: boolean;
}

function createChatStore() {
	let messages = $state<ChatMessage[]>([]);
	let isStreaming = $state(false);
	let currentStreamId = $state<string | null>(null);
	let retrieval = $state<RetrievalCounts>({ vector: 0, keyword: 0, graph: 0, fused: 0 });
	let error = $state<string | null>(null);
	let pendingQuestion = $state<string | null>(null);

	function addUserMessage(content: string): string {
		const id = crypto.randomUUID();
		messages.push({
			id,
			role: 'user',
			content,
			timestamp: Date.now()
		});
		error = null;
		return id;
	}

	function startAssistantMessage(): string {
		const id = crypto.randomUUID();
		messages.push({
			id,
			role: 'assistant',
			content: '',
			timestamp: Date.now(),
			isStreaming: true
		});
		isStreaming = true;
		currentStreamId = id;
		retrieval = { vector: 0, keyword: 0, graph: 0, fused: 0 };
		return id;
	}

	function appendToken(token: string): void {
		const msg = messages.find((m) => m.id === currentStreamId);
		if (msg) {
			msg.content += token;
		}
	}

	function setRetrieval(counts: RetrievalCounts): void {
		retrieval = counts;
		const msg = messages.find((m) => m.id === currentStreamId);
		if (msg) {
			msg.retrieval = counts;
		}
	}

	function setGraphHighlight(highlight: ChatMessage['graphHighlight']): void {
		const msg = messages.find((m) => m.id === currentStreamId);
		if (msg) {
			msg.graphHighlight = highlight;
		}
	}

	function finishStream(summary?: { totalContracts?: number; totalDollars?: number }): void {
		const msg = messages.find((m) => m.id === currentStreamId);
		if (msg) {
			msg.isStreaming = false;
			if (summary) {
				msg.totalContracts = summary.totalContracts;
				msg.totalDollars = summary.totalDollars;
			}
		}
		isStreaming = false;
		currentStreamId = null;
	}

	function setError(message: string): void {
		error = message;
		isStreaming = false;
		currentStreamId = null;
	}

	function setPendingQuestion(text: string): void {
		pendingQuestion = text;
	}

	function clearPendingQuestion(): void {
		pendingQuestion = null;
	}

	function clearMessages(): void {
		messages = [];
		isStreaming = false;
		currentStreamId = null;
		retrieval = { vector: 0, keyword: 0, graph: 0, fused: 0 };
		error = null;
		pendingQuestion = null;
	}

	return {
		get messages() {
			return messages;
		},
		get isStreaming() {
			return isStreaming;
		},
		get retrieval() {
			return retrieval;
		},
		get error() {
			return error;
		},
		get pendingQuestion() {
			return pendingQuestion;
		},
		addUserMessage,
		startAssistantMessage,
		appendToken,
		setRetrieval,
		setGraphHighlight,
		finishStream,
		setError,
		clearMessages,
		setPendingQuestion,
		clearPendingQuestion
	};
}

export const chatStore = createChatStore();
