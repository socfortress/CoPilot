<template>
	<div class="kv-card">
		<div class="key" v-if="$slots.key"><slot name="key"></slot></div>
		<div class="value" v-if="$slots.value"><slot name="value"></slot></div>
	</div>
</template>

<style lang="scss" scoped>
.kv-card {
	border: var(--border-small-100);
	background-color: var(--bg-secondary-color);
	border-radius: var(--border-radius);
	overflow: hidden;
	display: flex;
	flex-direction: column;
	flex-basis: 140px;
	flex-grow: 1;

	.key {
		border-bottom: var(--border-small-050);
		padding: 8px 12px;
		font-size: 12px;
	}
	.value {
		font-size: 14px;
		padding: 8px 12px;
		background-color: var(--bg-color);
		font-family: var(--font-family-mono);
		height: 100%;
		flex-grow: 1;
		word-break: break-word;
	}
}
</style>
