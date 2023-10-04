<template>
	<div class="page">
		<div class="spacer">Full Width</div>
	</div>
</template>

<style lang="scss" scoped>
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
	padding: 30px;
}
</style>
