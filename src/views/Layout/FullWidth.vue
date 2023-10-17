<template>
	<div class="page">
		<div class="spacer">Full Width</div>
	</div>
</template>

<style lang="scss" scoped>
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
	padding: 30px;
}
</style>
