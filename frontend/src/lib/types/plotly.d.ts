/**
 * Plotly.js-basic-dist TypeScript declarations
 */
declare module 'plotly.js-basic-dist' {
	export interface Data {
		type?: string;
		x?: (string | number | Date)[];
		y?: (string | number)[];
		name?: string;
		mode?: string;
		marker?: {
			color?: string | string[];
			size?: number | number[];
		};
		line?: {
			color?: string;
			width?: number;
		};
		text?: string[];
		hoverinfo?: string;
		values?: number[];
		labels?: string[];
		hole?: number;
	}

	export interface Layout {
		title?: string | { text: string; font?: { size: number } };
		xaxis?: {
			title?: string;
			showgrid?: boolean;
			zeroline?: boolean;
			tickangle?: number;
			gridcolor?: string;
			zerolinecolor?: string;
		};
		yaxis?: {
			title?: string;
			showgrid?: boolean;
			zeroline?: boolean;
			gridcolor?: string;
			zerolinecolor?: string;
		};
		showlegend?: boolean;
		legend?: {
			orientation?: 'h' | 'v';
			x?: number;
			y?: number;
		};
		margin?: {
			l?: number;
			r?: number;
			t?: number;
			b?: number;
			pad?: number;
		};
		paper_bgcolor?: string;
		plot_bgcolor?: string;
		font?: {
			family?: string;
			size?: number;
			color?: string;
		};
		autosize?: boolean;
		width?: number;
		height?: number;
		hovermode?: 'closest' | 'x' | 'y' | 'x unified' | 'y unified' | false;
	}

	export interface Config {
		displayModeBar?: boolean;
		displaylogo?: boolean;
		responsive?: boolean;
		scrollZoom?: boolean;
		staticPlot?: boolean;
	}

	export function react(
		graphDiv: HTMLElement,
		data: Data[],
		layout?: Partial<Layout>,
		config?: Partial<Config>
	): Promise<void>;

	export function newPlot(
		graphDiv: HTMLElement,
		data: Data[],
		layout?: Partial<Layout>,
		config?: Partial<Config>
	): Promise<void>;

	export function purge(graphDiv: HTMLElement): void;

	export function relayout(graphDiv: HTMLElement, update: Partial<Layout>): Promise<void>;
}
