<template>
	<div class="page page-wrapped flex flex-col page-without-footer">
		<CardWIthSiderbar sidebar-position="right">
			<template #main-toolbar>Main toolbar</template>
			<template #main-content>
				<div>Main content scrollable</div>
				<div class="spacer mt-5"></div>
			</template>
			<template #main-footer>Main footer</template>
			<template #sidebar-header>Sidebar header</template>
			<template #sidebar-content>
				<div>Sidebar content scrollable</div>
				<div class="spacer mt-5"></div>
			</template>
			<template #sidebar-footer>Sidebar footer</template>
		</CardWIthSiderbar>
	</div>
</template>

<script setup lang="ts">
import CardWIthSiderbar from "@/components/CardWIthSiderbar.vue"
import { useHideLayoutFooter } from "@/composables/useHideLayoutFooter"

// :has() CSS relational pseudo-class not yet supported by Firefox
// (https://caniuse.com/css-has)
// at the moment this worker around permit to hide Layout Footer
useHideLayoutFooter()
</script>

<style lang="scss" scoped>
@import "@/assets/scss/mixin.scss";
.page {
	@media (max-width: 700px) {
		@include page-full-view;
	}

	.spacer {
		background: rgba(var(--fg-color-rgb), 0.05);
		background: repeating-linear-gradient(
			-45deg,
			rgba(var(--fg-color-rgb), 0.05),
			rgba(var(--fg-color-rgb), 0.05) 1px,
			transparent 1px,
			transparent 20px
		);
		width: 100%;
		height: 200vh;
		border-radius: 14px;
		border: 4px dashed rgba(var(--fg-color-rgb), 0.05);
		opacity: 0.5;
	}
}
</style>
