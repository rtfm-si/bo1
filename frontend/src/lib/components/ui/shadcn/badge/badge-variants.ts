import { type VariantProps, tv } from "tailwind-variants";

export const badgeVariants = tv({
	base: "focus-visible:border-ring focus-visible:ring-ring/50 aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive inline-flex w-fit shrink-0 items-center justify-center gap-1 overflow-hidden rounded-full border px-2 py-0.5 text-xs font-medium whitespace-nowrap transition-[color,box-shadow] focus-visible:ring-[3px] [&>svg]:pointer-events-none [&>svg]:size-3",
	variants: {
		variant: {
			default:
				"bg-primary text-primary-foreground [a&]:hover:bg-primary/90 border-transparent",
			secondary:
				"bg-secondary text-secondary-foreground [a&]:hover:bg-secondary/90 border-transparent",
			destructive:
				"bg-destructive [a&]:hover:bg-destructive/90 focus-visible:ring-destructive/20 dark:focus-visible:ring-destructive/40 dark:bg-destructive/70 border-transparent text-white",
			outline: "text-foreground [a&]:hover:bg-accent [a&]:hover:text-accent-foreground",
			brand: "bg-brand-600 text-white border-brand-600 [a&]:hover:bg-brand-700 border-transparent",
			success: "bg-success-100 text-success-800 border-success-200 dark:bg-success-900 dark:text-success-200 dark:border-success-800",
			warning: "bg-warning-100 text-warning-800 border-warning-200 dark:bg-warning-900 dark:text-warning-200 dark:border-warning-800",
			error: "bg-destructive [a&]:hover:bg-destructive/90 border-transparent text-white dark:bg-destructive/70",
			info: "bg-info-100 text-info-800 border-info-200 dark:bg-info-900 dark:text-info-200 dark:border-info-800",
			neutral: "bg-secondary text-secondary-foreground [a&]:hover:bg-secondary/90 border-transparent",
		},
		size: {
			default: "px-2 py-0.5 text-xs",
			sm: "px-2 py-0.5 text-xs",
			md: "px-2.5 py-1 text-sm",
			lg: "px-3 py-1.5 text-base",
		},
	},
	defaultVariants: {
		variant: "default",
		size: "default",
	},
});

export type BadgeVariant = VariantProps<typeof badgeVariants>["variant"];
export type BadgeSize = VariantProps<typeof badgeVariants>["size"];
