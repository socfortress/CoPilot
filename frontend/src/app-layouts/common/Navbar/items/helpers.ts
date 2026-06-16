import type { MenuMixedOption } from "naive-ui/es/menu/src/interface"
import type { Component } from "vue"
import { h } from "vue"
import { RouterLink } from "vue-router"

import { renderIcon } from "@/utils"

export function routerLinkItem(label: string, routeName: string, key: string = routeName): MenuMixedOption {
	return {
		label: () => h(RouterLink, { to: { name: routeName } }, { default: () => label }),
		key
	}
}

export function parentMenuItem(
	label: string,
	key: string,
	icon: string | Component,
	children: MenuMixedOption[]
): MenuMixedOption {
	return {
		label,
		key,
		icon: renderIcon(icon),
		children
	}
}
