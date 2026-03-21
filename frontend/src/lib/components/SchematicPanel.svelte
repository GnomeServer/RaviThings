<script lang="ts">
	import { schematicStore, type ProcessSchematic } from '$lib/stores/schematic.svelte';
	import type { InputNode, ProcessStep, OutputNode, InputType } from '$lib/stores/schematic.svelte';
	import { chatStore } from '$lib/stores/chat.svelte';

	// Props
	let { onStepClick }: { onStepClick?: (stepName: string) => void } = $props();

	// Use local $state that gets updated via $effect to guarantee reactivity
	let schematic = $state<ProcessSchematic | null>(null);

	$effect(() => {
		schematic = schematicStore.schematic;
	});

	// ---- Export session ----

	function downloadFile(filename: string, content: string, mimeType: string) {
		const blob = new Blob([content], { type: mimeType });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = filename;
		document.body.appendChild(a);
		a.click();
		document.body.removeChild(a);
		URL.revokeObjectURL(url);
	}

	function exportSession() {
		if (!schematic) return;

		const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
		const safeTitle = schematic.title.replace(/[^a-zA-Z0-9]+/g, '_').slice(0, 40);

		// 1. JSON export
		const jsonContent = JSON.stringify(schematic, null, 2);
		downloadFile(`${safeTitle}_${timestamp}.json`, jsonContent, 'application/json');

		// 2. Markdown report
		const md = buildMarkdownReport(schematic);
		downloadFile(`${safeTitle}_${timestamp}.md`, md, 'text/markdown');
	}

	function buildMarkdownReport(s: ProcessSchematic): string {
		const lines: string[] = [];
		lines.push(`# ${s.title}`);
		lines.push('');
		lines.push(`**Date:** ${new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}`);
		lines.push('');

		// Conversation history
		const msgs = chatStore.messages;
		if (msgs.length > 0) {
			lines.push('## Conversation History');
			lines.push('');
			for (const msg of msgs) {
				const role = msg.role === 'user' ? 'User' : 'Assistant';
				lines.push(`**${role}:**`);
				lines.push(msg.content || '*(empty)*');
				lines.push('');
			}
		}

		// Process Schematic
		lines.push('## Process Schematic');
		lines.push('');

		// Inputs
		if (s.inputs.length > 0) {
			lines.push('### Inputs');
			lines.push('');
			for (const inp of s.inputs) {
				lines.push(`- **${inp.name}** (${inp.type.replace('_', ' ')})`);
				const realCommercial = inp.sources.commercial.filter((c) => isReal(c));
				if (realCommercial.length > 0) {
					lines.push(`  - Commercial: ${realCommercial.join(', ')}`);
				}
				if (isReal(inp.sources.diy)) {
					lines.push(`  - DIY: ${inp.sources.diy}`);
				}
			}
			lines.push('');
		}

		// Steps
		if (s.steps.length > 0) {
			lines.push('### Steps');
			lines.push('');
			for (const step of s.steps) {
				lines.push(`#### ${step.name}`);
				lines.push('');
				if (isReal(step.description)) {
					lines.push(step.description);
					lines.push('');
				}
				const params = realEntries(step.parameters);
				if (params.length > 0) {
					lines.push('**Parameters:**');
					for (const [key, val] of params) {
						lines.push(`- ${key}: ${val}`);
					}
					lines.push('');
				}
				const equip = realList(step.equipment);
				if (equip.length > 0) {
					lines.push('**Equipment:**');
					for (const eq of equip) {
						lines.push(`- ${eq}`);
					}
					lines.push('');
				}
				const contractors = realList(step.doe_contractors);
				if (contractors.length > 0) {
					lines.push('**DOE Contractors:**');
					for (const c of contractors) {
						lines.push(`- ${c}`);
					}
					lines.push('');
				}
				if (isReal(step.investment)) {
					lines.push(`**Investment:** ${step.investment}`);
					lines.push('');
				}
			}
		}

		// Outputs
		if (s.outputs.length > 0) {
			lines.push('### Outputs');
			lines.push('');
			for (const out of s.outputs) {
				lines.push(`- **${out.name}** (${out.type})`);
				if (isReal(out.description)) {
					lines.push(`  - ${out.description}`);
				}
			}
			lines.push('');
		}

		return lines.join('\n');
	}

	// Container element for SVG arrow overlay
	let containerEl: HTMLDivElement | undefined = $state();

	// ---- Helpers: filter out placeholder / empty values ----

	const PLACEHOLDER_RE = /^\$\d*x?m$/i;

	function isReal(value: string | undefined | null): boolean {
		if (!value) return false;
		const v = value.trim();
		if (v === '') return false;
		if (v.toLowerCase() === 'unknown') return false;
		if (PLACEHOLDER_RE.test(v)) return false;
		return true;
	}

	function realEntries(params: Record<string, string>): [string, string][] {
		return Object.entries(params).filter(([, v]) => isReal(v));
	}

	function realList(items: string[]): string[] {
		return items.filter((s) => isReal(s));
	}

	// ---- Topological depth assignment for steps ----

	interface StepWithCol {
		step: ProcessStep;
		col: number;
		row: number;
	}

	let stepLayout = $derived.by<{ columns: Map<number, ProcessStep[]>; lookup: Map<string, StepWithCol> }>(() => {
		if (!schematic) return { columns: new Map(), lookup: new Map() };
		const steps = schematic.steps;
		if (steps.length === 0) return { columns: new Map(), lookup: new Map() };

		const stepIds = new Set(steps.map((s) => s.id));
		const inputIds = new Set(schematic.inputs.map((i) => i.id));
		const depthMap = new Map<string, number>();

		function getDepth(stepId: string, visited: Set<string>): number {
			if (depthMap.has(stepId)) return depthMap.get(stepId)!;
			if (visited.has(stepId)) return 0;
			visited.add(stepId);

			const step = steps.find((s) => s.id === stepId);
			if (!step) return 0;

			let maxParentDepth = -1;
			for (const fromId of step.inputs_from) {
				if (stepIds.has(fromId)) {
					maxParentDepth = Math.max(maxParentDepth, getDepth(fromId, visited));
				} else if (inputIds.has(fromId)) {
					maxParentDepth = Math.max(maxParentDepth, -1);
				}
			}
			const depth = maxParentDepth + 1;
			depthMap.set(stepId, depth);
			return depth;
		}

		for (const step of steps) {
			getDepth(step.id, new Set());
		}

		const colGroups = new Map<number, ProcessStep[]>();
		for (const step of steps) {
			const col = depthMap.get(step.id) ?? 0;
			if (!colGroups.has(col)) colGroups.set(col, []);
			colGroups.get(col)!.push(step);
		}

		const lookup = new Map<string, StepWithCol>();
		for (const [col, colSteps] of colGroups) {
			colSteps.forEach((step, row) => {
				lookup.set(step.id, { step, col, row });
			});
		}

		return { columns: colGroups, lookup };
	});

	let sortedStepCols = $derived.by<number[]>(() => {
		return Array.from(stepLayout.columns.keys()).sort((a, b) => a - b);
	});

	// ---- Input type labels ----

	function inputTypeLabel(type: InputType): string {
		switch (type) {
			case 'raw_material': return 'Raw Material';
			case 'precursor': return 'Precursor';
			case 'equipment': return 'Equipment';
			case 'energy': return 'Energy';
			default: return type;
		}
	}

	function inputTypeBadgeClass(type: InputType): string {
		switch (type) {
			case 'raw_material': return 'badge-raw';
			case 'precursor': return 'badge-precursor';
			case 'equipment': return 'badge-equipment';
			case 'energy': return 'badge-energy';
			default: return '';
		}
	}

	// ---- SVG arrow overlay ----
	// We draw arrows on a transparent SVG overlay that covers the scroll area.
	// We track element positions using data-node-id attributes and recompute on resize/scroll.

	let arrowPaths = $state<{ d: string; dashed: boolean; key: string }[]>([]);
	let svgOverlayWidth = $state(0);
	let svgOverlayHeight = $state(0);

	function recomputeArrows() {
		if (!containerEl || !schematic) {
			arrowPaths = [];
			return;
		}

		const paths: { d: string; dashed: boolean; key: string }[] = [];
		const scrollLeft = containerEl.scrollLeft;
		const scrollTop = containerEl.scrollTop;
		const containerRect = containerEl.getBoundingClientRect();

		svgOverlayWidth = containerEl.scrollWidth;
		svgOverlayHeight = containerEl.scrollHeight;

		function getNodeRect(id: string): DOMRect | null {
			const el = containerEl!.querySelector(`[data-node-id="${id}"]`);
			if (!el) return null;
			return el.getBoundingClientRect();
		}

		function toLocal(rect: DOMRect): { left: number; top: number; right: number; centerY: number } {
			return {
				left: rect.left - containerRect.left + scrollLeft,
				top: rect.top - containerRect.top + scrollTop,
				right: rect.right - containerRect.left + scrollLeft,
				centerY: rect.top - containerRect.top + scrollTop + rect.height / 2
			};
		}

		// Inputs -> Steps
		for (const input of schematic.inputs) {
			for (const targetId of input.feeds_into) {
				const fromRect = getNodeRect(input.id);
				const toRect = getNodeRect(targetId);
				if (fromRect && toRect) {
					const from = toLocal(fromRect);
					const to = toLocal(toRect);
					const dx = (to.left - from.right) * 0.45;
					const d = `M ${from.right} ${from.centerY} C ${from.right + dx} ${from.centerY}, ${to.left - dx} ${to.centerY}, ${to.left} ${to.centerY}`;
					paths.push({ d, dashed: input.type === 'energy', key: `${input.id}-${targetId}` });
				}
			}
		}

		// Steps -> Steps and Steps -> Outputs
		for (const step of schematic.steps) {
			for (const targetId of step.outputs_to) {
				const fromRect = getNodeRect(step.id);
				const toRect = getNodeRect(targetId);
				if (fromRect && toRect) {
					const from = toLocal(fromRect);
					const to = toLocal(toRect);
					const dx = (to.left - from.right) * 0.45;
					const d = `M ${from.right} ${from.centerY} C ${from.right + dx} ${from.centerY}, ${to.left - dx} ${to.centerY}, ${to.left} ${to.centerY}`;
					paths.push({ d, dashed: false, key: `${step.id}-${targetId}` });
				}
			}
		}

		arrowPaths = paths;
	}

	// Recompute arrows after layout settles
	$effect(() => {
		// depend on schematic so it re-runs when data changes
		void schematic;
		// small delay for DOM to settle
		const timer = setTimeout(recomputeArrows, 80);
		return () => clearTimeout(timer);
	});

	// Also recompute on scroll and resize
	$effect(() => {
		if (!containerEl) return;
		const el = containerEl;
		el.addEventListener('scroll', recomputeArrows);
		const observer = new ResizeObserver(() => recomputeArrows());
		observer.observe(el);
		return () => {
			el.removeEventListener('scroll', recomputeArrows);
			observer.disconnect();
		};
	});
</script>

<section class="schematic-panel">
	<div class="panel-header">
		<span class="panel-title">
			{#if schematic}
				{schematic.title}
			{:else}
				Process Schematic
			{/if}
		</span>
		<div class="panel-controls">
			{#if schematicStore.isLoading}
				<span class="loading-text">Generating...</span>
			{/if}
			{#if schematic}
				<button class="btn btn-export" onclick={exportSession}>
					Export
				</button>
				<button class="btn" style="font-size: 11px;" onclick={() => schematicStore.clear()}>
					Clear
				</button>
			{/if}
		</div>
	</div>

	<div class="schematic-container" bind:this={containerEl}>
		{#if !schematic && !schematicStore.isLoading}
			<!-- Empty state -->
			<div class="placeholder-content">
				<svg
					class="placeholder-icon"
					width="72"
					height="72"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="1"
					stroke-linecap="round"
					stroke-linejoin="round"
				>
					<rect x="2" y="3" width="20" height="18" rx="2" opacity="0.3" />
					<line x1="6" y1="8" x2="10" y2="8" opacity="0.5" />
					<line x1="10" y1="8" x2="10" y2="12" opacity="0.5" />
					<line x1="10" y1="12" x2="14" y2="12" opacity="0.5" />
					<line x1="14" y1="12" x2="14" y2="16" opacity="0.5" />
					<line x1="14" y1="16" x2="18" y2="16" opacity="0.5" />
					<circle cx="6" cy="8" r="1.5" fill="currentColor" opacity="0.4" />
					<rect x="8.5" y="10.5" width="3" height="3" rx="0.5" fill="currentColor" opacity="0.4" />
					<circle cx="18" cy="16" r="1.5" fill="currentColor" opacity="0.4" />
				</svg>
				<p>Process Schematic</p>
				<p class="text-muted" style="font-size: 12px;">
					Ask a question to generate a process schematic
				</p>
			</div>
		{:else if schematic}
			<!-- SVG arrow overlay -->
			<svg
				class="arrow-overlay"
				width={svgOverlayWidth}
				height={svgOverlayHeight}
				viewBox="0 0 {svgOverlayWidth} {svgOverlayHeight}"
				xmlns="http://www.w3.org/2000/svg"
			>
				<defs>
					<marker
						id="arrowhead"
						markerWidth="10"
						markerHeight="7"
						refX="9"
						refY="3.5"
						orient="auto"
					>
						<polygon points="0 0, 10 3.5, 0 7" fill="#64748b" />
					</marker>
				</defs>
				{#each arrowPaths as arrow (arrow.key)}
					<path
						d={arrow.d}
						fill="none"
						stroke="#475569"
						stroke-width="1.5"
						stroke-dasharray={arrow.dashed ? '6,4' : 'none'}
						marker-end="url(#arrowhead)"
						opacity="0.6"
					/>
				{/each}
			</svg>

			<!-- HTML flow layout -->
			<div class="flow-layout">
				<!-- Column labels row -->
				<div class="column-label-row">
					<div class="col-label">INPUTS</div>
					{#each sortedStepCols as col (col)}
						<div class="col-label">STEP {col + 1}</div>
					{/each}
					<div class="col-label">OUTPUTS</div>
				</div>

				<!-- Nodes row -->
				<div class="columns-row">
					<!-- INPUT COLUMN -->
					<div class="node-column input-column">
						{#each schematic.inputs as node (node.id)}
							<div class="node-card input-card" data-node-id={node.id}>
								<div class="card-header input-header">
									<span class="card-name input-name">{node.name}</span>
									<span class="type-badge {inputTypeBadgeClass(node.type)}">{inputTypeLabel(node.type)}</span>
								</div>

								<!-- Commercial suppliers -->
								{#if node.sources.commercial.length > 0}
									{@const realSuppliers = realList(node.sources.commercial)}
									{#if realSuppliers.length > 0}
										<div class="card-section">
											<div class="section-label">Commercial Suppliers</div>
											<ul class="supplier-list">
												{#each realSuppliers as supplier}
													<li>{supplier}</li>
												{/each}
											</ul>
										</div>
									{/if}
								{/if}

								<!-- DIY instructions -->
								{#if isReal(node.sources.diy)}
									<div class="card-section">
										<div class="section-label">DIY</div>
										<p class="diy-text">{node.sources.diy}</p>
									</div>
								{/if}
							</div>
						{/each}
					</div>

					<!-- STEP COLUMNS (one per topological depth) -->
					{#each sortedStepCols as col (col)}
						<div class="node-column step-column">
							{#each stepLayout.columns.get(col) ?? [] as step (step.id)}
								<!-- svelte-ignore a11y_click_events_have_key_events -->
							<!-- svelte-ignore a11y_no_static_element_interactions -->
							<div
								class="node-card step-card"
								class:step-card-clickable={!!onStepClick}
								data-node-id={step.id}
								onclick={() => onStepClick?.(step.name)}
							>
									<div class="card-header step-header">
										<span class="card-name step-name">{step.name}</span>
									</div>

									<!-- Description -->
									{#if isReal(step.description)}
										<div class="card-section">
											<div class="section-label">Description</div>
											<p class="desc-text">{step.description}</p>
										</div>
									{/if}

									<!-- Parameters -->
									{#if realEntries(step.parameters).length > 0}
										<div class="card-section">
											<div class="section-label">Parameters</div>
											<div class="params-grid">
												{#each realEntries(step.parameters) as [key, val]}
													<span class="param-key">{key}</span>
													<span class="param-val">{val}</span>
												{/each}
											</div>
										</div>
									{/if}

									<!-- Equipment -->
									{#if realList(step.equipment).length > 0}
										<div class="card-section">
											<div class="section-label">Equipment</div>
											<ul class="equip-list">
												{#each realList(step.equipment) as eq}
													<li>{eq}</li>
												{/each}
											</ul>
										</div>
									{/if}

									<!-- DOE Contractors -->
									{#if realList(step.doe_contractors).length > 0}
										<div class="card-section">
											<div class="section-label">DOE Contractors</div>
											<ul class="equip-list">
												{#each realList(step.doe_contractors) as contractor}
													<li>{contractor}</li>
												{/each}
											</ul>
										</div>
									{/if}

									<!-- Investment -->
									{#if isReal(step.investment)}
										<div class="card-section investment-section">
											<span class="investment-value">{step.investment}</span>
										</div>
									{/if}
								</div>
							{/each}
						</div>
					{/each}

					<!-- OUTPUT COLUMN -->
					<div class="node-column output-column">
						{#each schematic.outputs as node (node.id)}
							<div class="node-card output-card" data-node-id={node.id}>
								<div class="card-header output-header">
									<span class="card-name output-name">{node.name}</span>
									<span class="type-badge {node.type === 'final' ? 'badge-final' : 'badge-intermediate'}">
										{node.type.toUpperCase()}
									</span>
								</div>

								{#if isReal(node.description)}
									<div class="card-section">
										<p class="desc-text">{node.description}</p>
									</div>
								{/if}
							</div>
						{/each}
					</div>
				</div>
			</div>
		{/if}
	</div>

	<!-- Legend overlay -->
	{#if schematic}
		<div class="schematic-legend">
			<div class="legend-item">
				<span class="legend-swatch" style="background: var(--accent-green); border-radius: 6px;"></span>
				<span class="text-muted">Input</span>
			</div>
			<div class="legend-item">
				<span class="legend-swatch" style="background: var(--accent-purple); border-radius: 3px;"></span>
				<span class="text-muted">Step</span>
			</div>
			<div class="legend-item">
				<span class="legend-swatch" style="background: var(--accent-blue-light); border-radius: 6px;"></span>
				<span class="text-muted">Output</span>
			</div>
			<div class="legend-divider"></div>
			<div class="legend-item">
				<span class="legend-line"></span>
				<span class="text-muted">Material</span>
			</div>
			<div class="legend-item">
				<span class="legend-line-dashed"></span>
				<span class="text-muted">Energy</span>
			</div>
		</div>
	{/if}
</section>

<style>
	/* ====================== Panel shell ====================== */
	.schematic-panel {
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

	.btn-export {
		font-size: 11px;
		color: var(--accent-blue-light);
		border-color: var(--accent-blue-light);
		background: rgba(59, 130, 246, 0.1);
	}

	.btn-export:hover {
		background: rgba(59, 130, 246, 0.2);
	}

	.loading-text {
		font-size: 11px;
		color: var(--accent-purple-light);
		animation: pulse 1.5s ease-in-out infinite;
	}

	@keyframes pulse {
		0%, 100% { opacity: 1; }
		50% { opacity: 0.3; }
	}

	/* ====================== Scroll container ====================== */
	.schematic-container {
		flex: 1;
		overflow: auto;
		position: relative;
	}

	/* ====================== Arrow overlay ====================== */
	.arrow-overlay {
		position: absolute;
		top: 0;
		left: 0;
		pointer-events: none;
		z-index: 0;
	}

	/* ====================== Placeholder ====================== */
	.placeholder-content {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		height: 100%;
		gap: 8px;
		color: var(--text-secondary);
		position: absolute;
		top: 0; left: 0; right: 0; bottom: 0;
		pointer-events: none;
	}

	.placeholder-icon {
		opacity: 0.3;
		color: var(--text-muted);
	}

	.placeholder-content p {
		font-size: 16px;
		font-weight: 500;
	}

	/* ====================== Flow layout ====================== */
	.flow-layout {
		position: relative;
		z-index: 1;
		padding: 16px 24px 80px 24px;
		min-width: max-content;
	}

	.column-label-row {
		display: flex;
		gap: 32px;
		margin-bottom: 12px;
	}

	.col-label {
		min-width: 260px;
		text-align: center;
		font-size: 11px;
		font-weight: 600;
		letter-spacing: 0.1em;
		color: var(--text-muted);
		text-transform: uppercase;
	}

	.columns-row {
		display: flex;
		gap: 32px;
		align-items: flex-start;
	}

	.node-column {
		display: flex;
		flex-direction: column;
		gap: 16px;
		min-width: 260px;
		max-width: 320px;
	}

	/* ====================== Card base ====================== */
	.node-card {
		border-radius: 10px;
		padding: 14px 16px;
		border-width: 1.5px;
		border-style: solid;
		transition: box-shadow 0.2s ease;
	}

	.node-card:hover {
		box-shadow: 0 0 12px rgba(255, 255, 255, 0.04);
	}

	/* Input cards */
	.input-card {
		background: rgba(5, 150, 105, 0.08);
		border-color: var(--accent-green);
	}

	/* Step cards */
	.step-card {
		background: rgba(124, 58, 237, 0.08);
		border-color: var(--accent-purple);
	}

	.step-card-clickable {
		cursor: pointer;
	}

	.step-card-clickable:hover {
		background: rgba(124, 58, 237, 0.16);
		box-shadow: 0 0 16px rgba(124, 58, 237, 0.15);
	}

	/* Output cards */
	.output-card {
		background: rgba(59, 130, 246, 0.08);
		border-color: var(--accent-blue-light);
	}

	/* ====================== Card header ====================== */
	.card-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
		margin-bottom: 8px;
	}

	.card-name {
		font-size: 13px;
		font-weight: 600;
		line-height: 1.3;
	}

	.input-name {
		color: var(--accent-green-light);
	}

	.step-name {
		color: var(--accent-purple-light);
	}

	.output-name {
		color: var(--accent-blue-light);
	}

	/* ====================== Type badges ====================== */
	.type-badge {
		display: inline-flex;
		align-items: center;
		padding: 2px 8px;
		border-radius: 9999px;
		font-size: 9px;
		font-weight: 700;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		white-space: nowrap;
		flex-shrink: 0;
	}

	.badge-raw {
		background: rgba(5, 150, 105, 0.2);
		color: var(--accent-green-light);
		border: 1px solid rgba(5, 150, 105, 0.35);
	}

	.badge-precursor {
		background: rgba(251, 146, 60, 0.2);
		color: var(--accent-orange-light);
		border: 1px solid rgba(251, 146, 60, 0.35);
	}

	.badge-equipment {
		background: rgba(148, 163, 184, 0.15);
		color: var(--text-secondary);
		border: 1px solid rgba(148, 163, 184, 0.3);
	}

	.badge-energy {
		background: rgba(250, 204, 21, 0.15);
		color: #fde68a;
		border: 1px solid rgba(250, 204, 21, 0.3);
	}

	.badge-final {
		background: rgba(59, 130, 246, 0.2);
		color: var(--accent-blue-light);
		border: 1px solid rgba(59, 130, 246, 0.35);
	}

	.badge-intermediate {
		background: rgba(148, 163, 184, 0.15);
		color: var(--text-secondary);
		border: 1px solid rgba(148, 163, 184, 0.3);
	}

	/* ====================== Card sections ====================== */
	.card-section {
		margin-top: 8px;
	}

	.section-label {
		font-size: 9px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--text-muted);
		margin-bottom: 4px;
	}

	/* Supplier bulleted list */
	.supplier-list {
		list-style: disc;
		padding-left: 16px;
		font-size: 11px;
		color: var(--text-secondary);
		line-height: 1.5;
	}

	.supplier-list li {
		margin-bottom: 1px;
	}

	/* DIY paragraph */
	.diy-text {
		font-size: 11px;
		color: var(--text-secondary);
		line-height: 1.45;
	}

	/* Description */
	.desc-text {
		font-size: 11px;
		color: var(--text-secondary);
		line-height: 1.45;
	}

	/* Parameters grid */
	.params-grid {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: 2px 8px;
		font-size: 11px;
		font-family: var(--font-mono);
	}

	.param-key {
		color: var(--text-muted);
		white-space: nowrap;
	}

	.param-key::after {
		content: ':';
	}

	.param-val {
		color: var(--text-secondary);
	}

	/* Equipment / contractor list */
	.equip-list {
		list-style: disc;
		padding-left: 16px;
		font-size: 11px;
		color: var(--text-secondary);
		line-height: 1.5;
	}

	.equip-list li {
		margin-bottom: 1px;
	}

	/* Investment */
	.investment-section {
		text-align: right;
	}

	.investment-value {
		font-size: 13px;
		font-weight: 700;
		font-family: var(--font-mono);
		color: var(--accent-green-light);
	}

	/* ====================== Legend ====================== */
	.schematic-legend {
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

	.legend-swatch {
		width: 10px;
		height: 10px;
		flex-shrink: 0;
	}

	.legend-divider {
		height: 1px;
		background: var(--border-color);
		margin: 2px 0;
	}

	.legend-line {
		width: 18px;
		height: 2px;
		background: #475569;
		flex-shrink: 0;
	}

	.legend-line-dashed {
		width: 18px;
		height: 0;
		border-top: 2px dashed #475569;
		flex-shrink: 0;
	}
</style>
