<template>
	<div class="pill-wrapper flex items-center">
		<slot />
	</div>
</template>

<style lang="scss" scoped>
.pill-wrapper {
	background-color: var(--bg-sidebar-color);
	border: 1px solid var(--border-color);
	color: var(--fg-default-color);
	border-radius: 50px;
	padding: 6px;
	transition: all 0.3s;
	gap: 14px;
}
</style>
