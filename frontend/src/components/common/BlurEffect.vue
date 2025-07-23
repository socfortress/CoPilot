<template>
	<div class="blur-effect">
		<div v-for="n in 8" :key="n"></div>
	</div>
</template>

<style lang="scss" scoped>
.blur-effect {
	position: absolute;
	width: 100%;
	height: 100%;
	top: 0;
	left: 0;
	z-index: 0;

	// Function to generate blur gradient
	@function blur-gradient($start, $mid1, $mid2, $end) {
		@return linear-gradient(
			to top,
			rgba(0, 0, 0, 0) $start,
			rgba(0, 0, 0, 1) $mid1,
			rgba(0, 0, 0, 1) $mid2,
			rgba(0, 0, 0, 0) $end
		);
	}

	& > div {
		position: absolute;
		inset: 0;
		z-index: 1;
		pointer-events: none;
	}

	// Generate blur effects with incremental values
	@for $i from 1 through 8 {
		$blur: 1px * pow(1.6, $i - 1);
		$start: ($i - 1) * 12.5%;
		$mid1: $i * 12.5%;
		$mid2: ($i + 1) * 12.5%;
		$end: ($i + 2) * 12.5%;

		& > div:nth-child(#{$i}) {
			backdrop-filter: blur($blur);
			@if $i < 8 {
				mask-image: blur-gradient($start, $mid1, $mid2, $end);
			} @else {
				mask-image: linear-gradient(to top, rgba(0, 0, 0, 0) 87.5%, rgba(0, 0, 0, 1) 100%);
			}
		}
	}
}
</style>
