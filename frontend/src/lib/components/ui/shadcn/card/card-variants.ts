import { type VariantProps, tv } from "tailwind-variants";

export const cardVariants = tv({
	base: "bg-card text-card-foreground flex flex-col gap-6 rounded-xl border py-6 shadow-sm",
	variants: {
		variant: {
			default: "",
			bordered: "border-2",
			elevated: "shadow-lg",
		},
		padding: {
			default: "",
			none: "py-0",
			sm: "p-4",
			md: "p-6",
			lg: "p-8",
		},
	},
	defaultVariants: {
		variant: "default",
		padding: "default",
	},
});

export type CardVariant = VariantProps<typeof cardVariants>["variant"];
export type CardPadding = VariantProps<typeof cardVariants>["padding"];
