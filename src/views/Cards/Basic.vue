<template>
	<div class="page">
		<div class="masonry">
			<div class="card-wrap">
				<CardBasic1 />
			</div>
			<div class="card-wrap">
				<CardBasic2 />
			</div>
			<div class="card-wrap">
				<CardBasic3 />
			</div>
			<div class="card-wrap">
				<CardBasic4 />
			</div>
			<div class="card-wrap">
				<CardBasic5 />
			</div>
			<div class="card-wrap">
				<CardBasic6 />
			</div>
		</div>
	</div>
</template>

<style lang="scss" scoped>
.page {
	container-type: inline-size;

	.masonry {
		--card-gap: 1.25em;
		column-count: 3;
		column-gap: var(--card-gap);

		@container (min-width: 1600px) {
			column-count: 4;
		}

		@container (max-width: 1200px) {
			column-count: 3;
		}

		@container (max-width: 900px) {
			column-count: 2;
		}

		@container (max-width: 600px) {
			column-count: 1;
		}

		.card-wrap {
			margin-bottom: var(--card-gap);
			overflow: hidden;
		}
	}
}
</style>
