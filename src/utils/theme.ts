export function toggleSidebarClass(
	sidebarCollapsed: boolean,
	elementId: string,
	classOpen: string,
	classClose: string
) {
	const el = window?.document?.getElementById(elementId)
	if (sidebarCollapsed) {
		el && el.classList.remove(classOpen)
		el && el.classList.add(classClose)
	} else {
		el && el.classList.add(classOpen)
		el && el.classList.remove(classClose)
	}
}
