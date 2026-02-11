import { type VariantProps, tv } from "tailwind-variants";

export const alertVariants = tv({
	base: "relative grid w-full grid-cols-[0_1fr] items-start gap-y-0.5 rounded-lg border px-4 py-3 text-sm has-[>svg]:grid-cols-[calc(var(--spacing)*4)_1fr] has-[>svg]:gap-x-3 [&>svg]:size-4 [&>svg]:tranneutral-y-0.5 [&>svg]:text-current",
	variants: {
		variant: {
			default: "bg-card text-card-foreground",
			destructive:
				"text-destructive bg-card *:data-[slot=alert-description]:text-destructive/90 [&>svg]:text-current",
			success: "border-success-200 bg-success-50 text-success-800 dark:border-success-800 dark:bg-success-900/20 dark:text-success-200 [&>svg]:text-current",
			warning: "border-warning-200 bg-warning-50 text-warning-800 dark:border-warning-800 dark:bg-warning-900/20 dark:text-warning-200 [&>svg]:text-current",
			error: "border-error-200 bg-error-50 text-error-800 dark:border-error-800 dark:bg-error-900/20 dark:text-error-200 [&>svg]:text-current",
			info: "border-info-200 bg-info-50 text-info-800 dark:border-info-800 dark:bg-info-900/20 dark:text-info-200 [&>svg]:text-current",
		},
	},
	defaultVariants: {
		variant: "default",
	},
});

export type AlertVariant = VariantProps<typeof alertVariants>["variant"];
