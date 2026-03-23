export function getDashboardIcon(icon: string) {
	switch (icon) {
		case "cpu":
		case "memory":
			return "carbon:chip"
		case "network":
			return "carbon:load-balancer-network"
		case "storage":
			return "carbon:vmdk-disk"
		case "security":
			return "carbon:security"
		case "performance":
			return "ph:gauge"
		default:
			return "carbon:dashboard"
	}
}

/** Span responsive su griglia 12 col: `col-span-12` su schermi stretti, poi breakpoint (`@lg`, `@2xl`, `@3xl`, `@5xl`) verso lo span target `w`. */
export const PANEL_COL_SPAN_BY_WIDTH: Record<number, string> = {
	1: "col-span-12 @2xl:col-span-4 @3xl:col-span-2 @5xl:col-span-1",
	2: "col-span-12 @lg:col-span-4 @5xl:col-span-2",
	3: "col-span-12 @lg:col-span-6 @5xl:col-span-3",
	4: "col-span-12 @3xl:col-span-4",
	5: "col-span-12 @3xl:col-span-5",
	6: "col-span-12 @2xl:col-span-6",
	7: "col-span-12 @3xl:col-span-7",
	8: "col-span-12 @2xl:col-span-8",
	9: "col-span-12 @2xl:col-span-9",
	10: "col-span-12 @xl:col-span-10",
	11: "col-span-12 @xl:col-span-11",
	12: "col-span-12"
}

export function panelColSpanClass(w: number): string {
	return PANEL_COL_SPAN_BY_WIDTH[w] ?? "col-span-12"
}
