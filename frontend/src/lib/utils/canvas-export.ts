/**
 * Canvas export utility for generating shareable images from DOM elements.
 * Uses html2canvas for reliable DOM-to-canvas conversion.
 */
import html2canvas from 'html2canvas';

export interface ExportOptions {
	/** Include Bo1 branding watermark */
	includeBranding?: boolean;
	/** Custom title to display */
	title?: string;
	/** Subtitle (e.g., date range) */
	subtitle?: string;
	/** Background color */
	backgroundColor?: string;
	/** Image quality (0-1) for JPEG */
	quality?: number;
	/** Scale factor for higher resolution */
	scale?: number;
}

const DEFAULT_OPTIONS: Required<ExportOptions> = {
	includeBranding: true,
	title: 'Activity Heatmap',
	subtitle: '',
	backgroundColor: '#ffffff',
	quality: 0.92,
	scale: 2
};

/**
 * Export a DOM element as a PNG data URL with optional branding.
 */
export async function exportElementAsImage(
	element: HTMLElement,
	options: ExportOptions = {}
): Promise<string> {
	const opts = { ...DEFAULT_OPTIONS, ...options };

	// Capture the element
	const canvas = await html2canvas(element, {
		backgroundColor: opts.backgroundColor,
		scale: opts.scale,
		logging: false,
		useCORS: true
	});

	if (!opts.includeBranding && !opts.title && !opts.subtitle) {
		return canvas.toDataURL('image/png');
	}

	// Create a new canvas with space for branding
	const headerHeight = opts.title ? 60 : 0;
	const footerHeight = opts.includeBranding ? 40 : 0;
	const padding = 20;

	const finalCanvas = document.createElement('canvas');
	finalCanvas.width = canvas.width + padding * 2;
	finalCanvas.height = canvas.height + headerHeight + footerHeight + padding * 2;

	const ctx = finalCanvas.getContext('2d');
	if (!ctx) {
		throw new Error('Could not get canvas context');
	}

	// Fill background
	ctx.fillStyle = opts.backgroundColor;
	ctx.fillRect(0, 0, finalCanvas.width, finalCanvas.height);

	// Draw title if present
	if (opts.title) {
		ctx.fillStyle = '#1a1a1a';
		ctx.font = `bold ${18 * opts.scale}px Inter, system-ui, sans-serif`;
		ctx.textAlign = 'left';
		ctx.fillText(opts.title, padding, padding + 24 * opts.scale);

		if (opts.subtitle) {
			ctx.fillStyle = '#666666';
			ctx.font = `${14 * opts.scale}px Inter, system-ui, sans-serif`;
			ctx.fillText(opts.subtitle, padding, padding + 44 * opts.scale);
		}
	}

	// Draw the captured element
	ctx.drawImage(canvas, padding, headerHeight + padding);

	// Draw branding watermark
	if (opts.includeBranding) {
		const brandingY = finalCanvas.height - footerHeight / 2 - padding / 2;
		ctx.fillStyle = '#999999';
		ctx.font = `${12 * opts.scale}px Inter, system-ui, sans-serif`;
		ctx.textAlign = 'right';
		ctx.fillText('Board of One', finalCanvas.width - padding, brandingY);
	}

	return finalCanvas.toDataURL('image/png');
}

/**
 * Download an image data URL as a file.
 */
export function downloadImage(dataUrl: string, filename: string = 'activity-heatmap.png'): void {
	const link = document.createElement('a');
	link.download = filename;
	link.href = dataUrl;
	document.body.appendChild(link);
	link.click();
	document.body.removeChild(link);
}

/**
 * Convert data URL to Blob for sharing.
 */
export async function dataUrlToBlob(dataUrl: string): Promise<Blob> {
	const response = await fetch(dataUrl);
	return response.blob();
}

/**
 * Check if Web Share API is available and supports file sharing.
 */
export function canShareFiles(): boolean {
	return typeof navigator !== 'undefined' &&
		'share' in navigator &&
		'canShare' in navigator;
}

/**
 * Share an image using the Web Share API (mobile-friendly).
 */
export async function shareImage(
	dataUrl: string,
	title: string,
	text: string,
	filename: string = 'activity-heatmap.png'
): Promise<boolean> {
	if (!canShareFiles()) {
		return false;
	}

	try {
		const blob = await dataUrlToBlob(dataUrl);
		const file = new File([blob], filename, { type: 'image/png' });

		if (navigator.canShare && navigator.canShare({ files: [file] })) {
			await navigator.share({
				title,
				text,
				files: [file]
			});
			return true;
		}
	} catch (error) {
		// User cancelled or share failed
		if (error instanceof Error && error.name !== 'AbortError') {
			console.error('Share failed:', error);
		}
	}

	return false;
}

/**
 * Meeting summary data for export.
 */
export interface MeetingSummaryData {
	recommendation: string;
	consensusLevel: number;
	expertCount: number;
	completionDate: string;
	problemStatement?: string;
}

/**
 * Action achievement data for export.
 */
export interface ActionAchievementData {
	title: string;
	completionDate: string;
	daysToComplete?: number;
	projectName?: string;
	priority?: 'high' | 'medium' | 'low';
}

/**
 * Export a meeting summary as an image.
 * Creates a canvas-rendered card without requiring DOM elements.
 */
export async function exportMeetingSummary(
	data: MeetingSummaryData,
	options: Omit<ExportOptions, 'title' | 'subtitle'> = {}
): Promise<string> {
	const opts = { ...DEFAULT_OPTIONS, ...options };
	const scale = opts.scale;

	// Card dimensions (600x315 scaled)
	const width = 600 * scale;
	const height = 315 * scale;

	const canvas = document.createElement('canvas');
	canvas.width = width;
	canvas.height = height;

	const ctx = canvas.getContext('2d');
	if (!ctx) {
		throw new Error('Could not get canvas context');
	}

	// Background
	ctx.fillStyle = opts.backgroundColor;
	ctx.fillRect(0, 0, width, height);

	// Header background
	ctx.fillStyle = '#eff6ff'; // brand-50 equivalent
	ctx.fillRect(0, 0, width, 60 * scale);

	// Header border
	ctx.strokeStyle = '#e5e7eb';
	ctx.lineWidth = 1;
	ctx.beginPath();
	ctx.moveTo(0, 60 * scale);
	ctx.lineTo(width, 60 * scale);
	ctx.stroke();

	// Logo placeholder
	ctx.fillStyle = '#3b82f6'; // brand-600
	roundRect(ctx, 24 * scale, 16 * scale, 32 * scale, 32 * scale, 8 * scale);
	ctx.fill();

	ctx.fillStyle = '#ffffff';
	ctx.font = `bold ${14 * scale}px Inter, system-ui, sans-serif`;
	ctx.textAlign = 'center';
	ctx.textBaseline = 'middle';
	ctx.fillText('Bo1', 40 * scale, 32 * scale);

	// Board of One text
	ctx.fillStyle = '#6b7280';
	ctx.font = `${12 * scale}px Inter, system-ui, sans-serif`;
	ctx.textAlign = 'left';
	ctx.textBaseline = 'alphabetic';
	ctx.fillText('Board of One', 64 * scale, 36 * scale);

	// Meeting Summary label
	ctx.fillStyle = '#9ca3af';
	ctx.font = `${10 * scale}px Inter, system-ui, sans-serif`;
	ctx.textAlign = 'right';
	ctx.fillText('Meeting Summary', (width - 24 * scale), 36 * scale);

	// Problem statement (if provided)
	let contentStartY = 80 * scale;
	if (data.problemStatement) {
		ctx.fillStyle = '#9ca3af';
		ctx.font = `${10 * scale}px Inter, system-ui, sans-serif`;
		ctx.textAlign = 'left';
		const truncatedProblem = truncateText(data.problemStatement, 100);
		ctx.fillText(truncatedProblem, 24 * scale, contentStartY);
		contentStartY += 24 * scale;
	}

	// Recommendation icon circle
	ctx.fillStyle = '#dbeafe'; // brand-100
	ctx.beginPath();
	ctx.arc(44 * scale, contentStartY + 40 * scale, 20 * scale, 0, Math.PI * 2);
	ctx.fill();

	// Recommendation text
	ctx.fillStyle = '#111827';
	ctx.font = `600 ${16 * scale}px Inter, system-ui, sans-serif`;
	ctx.textAlign = 'left';
	const truncatedRec = truncateText(data.recommendation, 200);
	wrapText(ctx, truncatedRec, 74 * scale, contentStartY + 30 * scale, (width - 98 * scale), 22 * scale);

	// Bottom metrics bar
	const metricsY = height - 60 * scale;

	// Border
	ctx.strokeStyle = '#f3f4f6';
	ctx.lineWidth = 1;
	ctx.beginPath();
	ctx.moveTo(24 * scale, metricsY);
	ctx.lineTo(width - 24 * scale, metricsY);
	ctx.stroke();

	// Consensus bar
	ctx.fillStyle = '#e5e7eb';
	roundRect(ctx, 24 * scale, metricsY + 20 * scale, 64 * scale, 8 * scale, 4 * scale);
	ctx.fill();

	ctx.fillStyle = '#3b82f6';
	roundRect(ctx, 24 * scale, metricsY + 20 * scale, 64 * scale * data.consensusLevel, 8 * scale, 4 * scale);
	ctx.fill();

	// Consensus label
	ctx.fillStyle = '#3b82f6';
	ctx.font = `500 ${11 * scale}px Inter, system-ui, sans-serif`;
	ctx.textAlign = 'left';
	ctx.fillText(getConsensusLabel(data.consensusLevel), 96 * scale, metricsY + 28 * scale);

	// Expert count
	ctx.fillStyle = '#6b7280';
	ctx.font = `${11 * scale}px Inter, system-ui, sans-serif`;
	ctx.textAlign = 'center';
	ctx.fillText(`${data.expertCount} experts`, width / 2, metricsY + 28 * scale);

	// Date
	ctx.textAlign = 'right';
	ctx.fillText(formatDateShort(data.completionDate), width - 24 * scale, metricsY + 28 * scale);

	return canvas.toDataURL('image/png');
}

/**
 * Export an action achievement as an image.
 * Creates a canvas-rendered card without requiring DOM elements.
 */
export async function exportActionAchievement(
	data: ActionAchievementData,
	options: Omit<ExportOptions, 'title' | 'subtitle'> = {}
): Promise<string> {
	const opts = { ...DEFAULT_OPTIONS, ...options };
	const scale = opts.scale;

	// Card dimensions (600x315 scaled)
	const width = 600 * scale;
	const height = 315 * scale;

	const canvas = document.createElement('canvas');
	canvas.width = width;
	canvas.height = height;

	const ctx = canvas.getContext('2d');
	if (!ctx) {
		throw new Error('Could not get canvas context');
	}

	// Background
	ctx.fillStyle = opts.backgroundColor;
	ctx.fillRect(0, 0, width, height);

	// Header gradient (success-50 to brand-50)
	const gradient = ctx.createLinearGradient(0, 0, width, 0);
	gradient.addColorStop(0, '#f0fdf4'); // success-50
	gradient.addColorStop(1, '#eff6ff'); // brand-50
	ctx.fillStyle = gradient;
	ctx.fillRect(0, 0, width, 72 * scale);

	// Header border
	ctx.strokeStyle = '#e5e7eb';
	ctx.lineWidth = 1;
	ctx.beginPath();
	ctx.moveTo(0, 72 * scale);
	ctx.lineTo(width, 72 * scale);
	ctx.stroke();

	// Trophy circle
	ctx.fillStyle = '#22c55e'; // success-500
	ctx.beginPath();
	ctx.arc(44 * scale, 36 * scale, 20 * scale, 0, Math.PI * 2);
	ctx.fill();

	// Achievement message
	ctx.fillStyle = '#15803d'; // success-700
	ctx.font = `bold ${16 * scale}px Inter, system-ui, sans-serif`;
	ctx.textAlign = 'left';
	ctx.textBaseline = 'alphabetic';
	ctx.fillText(getAchievementMessage(data.daysToComplete), 74 * scale, 32 * scale);

	// Days to complete subtext
	if (data.daysToComplete) {
		ctx.fillStyle = '#6b7280';
		ctx.font = `${10 * scale}px Inter, system-ui, sans-serif`;
		ctx.fillText(
			`Completed in ${data.daysToComplete} day${data.daysToComplete !== 1 ? 's' : ''}`,
			74 * scale,
			48 * scale
		);
	}

	// Logo
	ctx.fillStyle = '#3b82f6';
	roundRect(ctx, width - 56 * scale, 20 * scale, 32 * scale, 32 * scale, 8 * scale);
	ctx.fill();

	ctx.fillStyle = '#ffffff';
	ctx.font = `bold ${14 * scale}px Inter, system-ui, sans-serif`;
	ctx.textAlign = 'center';
	ctx.textBaseline = 'middle';
	ctx.fillText('Bo1', width - 40 * scale, 36 * scale);

	// Content area
	const contentStartY = 92 * scale;

	// Checkmark circle
	ctx.fillStyle = '#dcfce7'; // success-100
	ctx.beginPath();
	ctx.arc(44 * scale, contentStartY + 40 * scale, 20 * scale, 0, Math.PI * 2);
	ctx.fill();

	// Action title
	ctx.fillStyle = '#111827';
	ctx.font = `600 ${18 * scale}px Inter, system-ui, sans-serif`;
	ctx.textAlign = 'left';
	ctx.textBaseline = 'alphabetic';
	const truncatedTitle = truncateText(data.title, 150);
	wrapText(ctx, truncatedTitle, 74 * scale, contentStartY + 30 * scale, (width - 98 * scale), 24 * scale);

	// Bottom metrics bar
	const metricsY = height - 60 * scale;

	// Border
	ctx.strokeStyle = '#f3f4f6';
	ctx.lineWidth = 1;
	ctx.beginPath();
	ctx.moveTo(24 * scale, metricsY);
	ctx.lineTo(width - 24 * scale, metricsY);
	ctx.stroke();

	// Project or priority
	ctx.fillStyle = '#6b7280';
	ctx.font = `${11 * scale}px Inter, system-ui, sans-serif`;
	ctx.textAlign = 'left';
	if (data.projectName) {
		ctx.fillText(truncateText(data.projectName, 30), 24 * scale, metricsY + 28 * scale);
	} else if (data.priority) {
		ctx.fillText(`${data.priority.charAt(0).toUpperCase() + data.priority.slice(1)} Priority`, 24 * scale, metricsY + 28 * scale);
	}

	// Days to complete (center)
	if (data.daysToComplete) {
		ctx.textAlign = 'center';
		ctx.fillText(`${data.daysToComplete} day${data.daysToComplete !== 1 ? 's' : ''}`, width / 2, metricsY + 28 * scale);
	}

	// Date
	ctx.textAlign = 'right';
	ctx.fillText(formatDateShort(data.completionDate), width - 24 * scale, metricsY + 28 * scale);

	return canvas.toDataURL('image/png');
}

// Helper: Draw rounded rectangle
function roundRect(
	ctx: CanvasRenderingContext2D,
	x: number,
	y: number,
	w: number,
	h: number,
	r: number
): void {
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

// Helper: Wrap text
function wrapText(
	ctx: CanvasRenderingContext2D,
	text: string,
	x: number,
	y: number,
	maxWidth: number,
	lineHeight: number
): void {
	const words = text.split(' ');
	let line = '';
	let currentY = y;
	let lineCount = 0;
	const maxLines = 3;

	for (let i = 0; i < words.length; i++) {
		const testLine = line + words[i] + ' ';
		const metrics = ctx.measureText(testLine);

		if (metrics.width > maxWidth && i > 0) {
			lineCount++;
			if (lineCount > maxLines) {
				line = line.trim().slice(0, -3) + '...';
				ctx.fillText(line, x, currentY);
				return;
			}
			ctx.fillText(line, x, currentY);
			line = words[i] + ' ';
			currentY += lineHeight;
		} else {
			line = testLine;
		}
	}
	ctx.fillText(line, x, currentY);
}

// Helper: Truncate text
function truncateText(text: string, maxLength: number): string {
	if (text.length <= maxLength) return text;
	return text.slice(0, maxLength - 3) + '...';
}

// Helper: Format date
function formatDateShort(dateStr: string): string {
	try {
		const date = new Date(dateStr);
		return date.toLocaleDateString('en-US', {
			month: 'short',
			day: 'numeric',
			year: 'numeric'
		});
	} catch {
		return dateStr;
	}
}

// Helper: Get consensus label
function getConsensusLabel(level: number): string {
	if (level >= 0.9) return 'Strong Consensus';
	if (level >= 0.7) return 'Good Consensus';
	if (level >= 0.5) return 'Moderate Agreement';
	return 'Mixed Opinions';
}

// Helper: Get achievement message
function getAchievementMessage(days: number | undefined): string {
	if (!days) return 'Task Completed';
	if (days <= 1) return 'Lightning Fast!';
	if (days <= 3) return 'Quick Win!';
	if (days <= 7) return 'Solid Progress';
	if (days <= 14) return 'Mission Accomplished';
	return 'Goal Achieved';
}
