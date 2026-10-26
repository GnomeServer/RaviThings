/**
 * API helpers for DOE Contract GraphRAG frontend.
 *
 * fetchSSE: POST request that reads an SSE stream line-by-line,
 *           parsing `event:` and `data:` fields, calling onEvent for each.
 *
 * fetchJSON: Simple GET request returning parsed JSON.
 */

export interface SSEEvent {
	event: string;
	data: unknown;
}

/**
 * Perform a POST request to an SSE endpoint and stream events.
 *
 * The server sends events in the format:
 *   event: <type>
 *   data: <json>
 *   \n
 *
 * @param url   - API endpoint (e.g., '/api/chat')
 * @param body  - Request body (will be JSON-serialized)
 * @param onEvent - Callback invoked for each parsed SSE event
 * @returns AbortController so the caller can cancel the stream
 */
export function fetchSSE(
	url: string,
	body: unknown,
	onEvent: (event: SSEEvent) => void
): AbortController {
	const controller = new AbortController();

	(async () => {
		try {
			const response = await fetch(url, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Accept: 'text/event-stream'
				},
				body: JSON.stringify(body),
				signal: controller.signal
			});

			if (!response.ok) {
				const errorText = await response.text();
				onEvent({
					event: 'error',
					data: { message: `HTTP ${response.status}: ${errorText}` }
				});
				return;
			}

			if (!response.body) {
				onEvent({
					event: 'error',
					data: { message: 'Response body is null — SSE not supported' }
				});
				return;
			}

			const reader = response.body.getReader();
			const decoder = new TextDecoder();

			let buffer = '';
			let currentEvent = '';
			let currentData = '';

			while (true) {
				const { done, value } = await reader.read();

				if (done) {
					// Process any remaining buffered event
					if (currentEvent || currentData) {
						dispatchEvent(currentEvent, currentData, onEvent);
					}
					break;
				}

				buffer += decoder.decode(value, { stream: true });

				// Process complete lines from buffer
				const lines = buffer.split('\n');
				// Keep the last partial line in the buffer
				buffer = lines.pop() ?? '';

				for (const line of lines) {
					if (line.startsWith('event:')) {
						// If we have a pending event with data, dispatch it first
						if (currentData) {
							dispatchEvent(currentEvent, currentData, onEvent);
							currentData = '';
						}
						currentEvent = line.slice(6).trim();
					} else if (line.startsWith('data:')) {
						currentData += line.slice(5).trim();
					} else if (line.trim() === '') {
						// Blank line = end of SSE event block
						if (currentEvent || currentData) {
							dispatchEvent(currentEvent, currentData, onEvent);
							currentEvent = '';
							currentData = '';
						}
					}
				}
			}
		} catch (err: unknown) {
			if (err instanceof DOMException && err.name === 'AbortError') {
				// Stream was intentionally cancelled — not an error
				return;
			}
			onEvent({
				event: 'error',
				data: { message: err instanceof Error ? err.message : String(err) }
			});
		}
	})();

	return controller;
}

/**
 * Dispatch a single parsed SSE event.
 */
function dispatchEvent(
	eventType: string,
	data: string,
	onEvent: (event: SSEEvent) => void
): void {
	const type = eventType || 'message';
	let parsed: unknown;

	try {
		parsed = JSON.parse(data);
	} catch {
		// If data is not valid JSON, pass it as a raw string
		parsed = data;
	}

	onEvent({ event: type, data: parsed });
}

/**
 * Perform a GET request and return parsed JSON.
 *
 * @param url - API endpoint (e.g., '/api/stats')
 * @param signal - Optional AbortSignal for cancellation
 */
export async function fetchJSON<T = unknown>(url: string, signal?: AbortSignal): Promise<T> {
	const response = await fetch(url, {
		headers: { Accept: 'application/json' },
		signal
	});

	if (!response.ok) {
		const errorText = await response.text();
		throw new Error(`HTTP ${response.status}: ${errorText}`);
	}

	return response.json() as Promise<T>;
}
