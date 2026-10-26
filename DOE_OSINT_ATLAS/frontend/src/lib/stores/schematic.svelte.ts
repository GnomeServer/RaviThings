/**
 * Schematic store — manages the current ProcessSchematic data for the
 * process flow diagram panel. Uses Svelte 5 runes ($state) for reactivity.
 */

export type InputType = 'raw_material' | 'precursor' | 'equipment' | 'energy';

export interface InputNode {
	id: string;
	name: string;
	type: InputType;
	sources: {
		commercial: string[];
		diy: string;
	};
	feeds_into: string[];
}

export interface ContractorParticipation {
	name: string;
	role: string;
	contract_value: number;
	significance_pct: number;
}

export interface ProcessStep {
	id: string;
	name: string;
	description: string;
	parameters: Record<string, string>;
	equipment: string[];
	inputs_from: string[];
	outputs_to: string[];
	doe_contractors: string[];
	investment: string;
	contractor_details: ContractorParticipation[];
	step_total_capital: number;
}

export interface OutputNode {
	id: string;
	name: string;
	description: string;
	type: 'intermediate' | 'final';
	receives_from: string[];
}

export interface ProcessSchematic {
	title: string;
	inputs: InputNode[];
	steps: ProcessStep[];
	outputs: OutputNode[];
}

/**
 * Normalize raw LLM-generated schematic data by adding safe defaults
 * for any missing fields. The model often omits array fields.
 */
function normalize(raw: Record<string, unknown>): ProcessSchematic {
	const inputs = (Array.isArray(raw.inputs) ? raw.inputs : []).map(
		(inp: Record<string, unknown>) => ({
			id: inp.id ?? `in_${Math.random().toString(36).slice(2, 6)}`,
			name: inp.name ?? 'Unknown input',
			type: (['raw_material', 'precursor', 'equipment', 'energy'].includes(inp.type as string)
				? inp.type
				: 'raw_material') as InputType,
			sources: {
				commercial: Array.isArray((inp.sources as Record<string, unknown>)?.commercial)
					? (inp.sources as Record<string, string[]>).commercial
					: [],
				diy: ((inp.sources as Record<string, unknown>)?.diy as string) ?? ''
			},
			feeds_into: Array.isArray(inp.feeds_into) ? inp.feeds_into : []
		})
	) as InputNode[];

	const steps = (Array.isArray(raw.steps) ? raw.steps : []).map(
		(s: Record<string, unknown>) => ({
			id: s.id ?? `step_${Math.random().toString(36).slice(2, 6)}`,
			name: s.name ?? 'Unknown step',
			description: (s.description as string) ?? '',
			parameters: (typeof s.parameters === 'object' && s.parameters !== null
				? s.parameters
				: {}) as Record<string, string>,
			equipment: Array.isArray(s.equipment) ? s.equipment : [],
			inputs_from: Array.isArray(s.inputs_from) ? s.inputs_from : [],
			outputs_to: Array.isArray(s.outputs_to) ? s.outputs_to : [],
			doe_contractors: Array.isArray(s.doe_contractors) ? s.doe_contractors : [],
			investment: (s.investment as string) ?? '',
			contractor_details: (Array.isArray(s.contractor_details) ? s.contractor_details : []).map(
				(c: Record<string, unknown>) => ({
					name: String(c.name ?? 'Unknown'),
					role: String(c.role ?? ''),
					contract_value: Number(c.contract_value) || 0,
					significance_pct: Number(c.significance_pct) || 0,
				})
			),
			step_total_capital: Number(s.step_total_capital) || 0,
		})
	) as ProcessStep[];

	const outputs = (Array.isArray(raw.outputs) ? raw.outputs : []).map(
		(o: Record<string, unknown>) => ({
			id: o.id ?? `out_${Math.random().toString(36).slice(2, 6)}`,
			name: o.name ?? 'Unknown output',
			description: (o.description as string) ?? '',
			type: (o.type === 'intermediate' ? 'intermediate' : 'final') as 'intermediate' | 'final',
			receives_from: Array.isArray(o.receives_from) ? o.receives_from : []
		})
	) as OutputNode[];

	return {
		title: (raw.title as string) ?? 'Process Schematic',
		inputs,
		steps,
		outputs
	};
}

function createSchematicStore() {
	let schematic = $state<ProcessSchematic | null>(null);
	let isLoading = $state(false);

	function setSchematic(data: Record<string, unknown> | ProcessSchematic): void {
		schematic = normalize(data as Record<string, unknown>);
	}

	function clear(): void {
		schematic = null;
	}

	function setLoading(loading: boolean): void {
		isLoading = loading;
	}

	return {
		get schematic() {
			return schematic;
		},
		get isLoading() {
			return isLoading;
		},
		setSchematic,
		clear,
		setLoading
	};
}

export const schematicStore = createSchematicStore();
