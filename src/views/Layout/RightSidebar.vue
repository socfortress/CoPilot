<template>
	<div class="page page-wrapped flex flex-col page-without-footer">
		<PageSplitted sidebar-position="right">
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
		</PageSplitted>
	</div>
</template>

<script setup lang="ts">
import PageSplitted from "@/components/common/PageSplitted.vue"
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
		background: var(--divider-005-color);
		background: repeating-linear-gradient(
			-45deg,
			var(--divider-005-color),
			var(--divider-005-color) 1px,
			transparent 1px,
			transparent 20px
		);
		width: 100%;
		height: 200vh;
		border-radius: 14px;
		border: 4px dashed var(--divider-005-color);
		opacity: 0.5;
	}
}
</style>
