import { computed, ref } from "vue"

export interface BreadcrumbItem {
	name: string
	path: string
	key: string
}

const breadcrumbItems = ref<BreadcrumbItem[]>([])

export function useBreadcrumb() {
	const items = computed(() => breadcrumbItems.value)

	/**
	 * Adds a new item to the end of the breadcrumb
	 */
	function push(item: BreadcrumbItem) {
		breadcrumbItems.value.push(item)
	}

	/**
	 * Replaces the last breadcrumb item
	 * If there are no items, adds the new item
	 */
	function replace(item: BreadcrumbItem) {
		if (breadcrumbItems.value.length === 0) {
			breadcrumbItems.value.push(item)
		} else {
			breadcrumbItems.value[breadcrumbItems.value.length - 1] = item
		}
	}

	/**
	 * Updates only the name of the last breadcrumb item
	 * If there are no items, does nothing
	 */
	function updateLastCrumbName(name: string) {
		if (breadcrumbItems.value.length > 0) {
			const lastItem = breadcrumbItems.value[breadcrumbItems.value.length - 1]
			if (!lastItem) return

			breadcrumbItems.value[breadcrumbItems.value.length - 1] = {
				...lastItem,
				name
			}
		}
	}

	/**
	 * Removes the last breadcrumb item
	 */
	function pop() {
		return breadcrumbItems.value.pop()
	}

	/**
	 * Clears all breadcrumb items
	 */
	function clear() {
		breadcrumbItems.value = []
	}

	/**
	 * Sets all breadcrumb items
	 */
	function setItems(items: BreadcrumbItem[]) {
		breadcrumbItems.value = items
	}

	/**
	 * Removes items until reaching the specified index
	 */
	function truncate(index: number) {
		if (index >= 0 && index < breadcrumbItems.value.length) {
			breadcrumbItems.value = breadcrumbItems.value.slice(0, index + 1)
		}
	}

	return {
		items,
		push,
		replace,
		updateLastCrumbName,
		pop,
		clear,
		setItems,
		truncate
	}
}
