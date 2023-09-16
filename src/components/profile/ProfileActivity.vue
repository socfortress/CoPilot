<template>
	<div class="activity">
		<div class="masonry">
			<div class="card-wrap" v-for="(card, index) of cards" :key="index">
				<CardSocial1
					:hideText="card.hideText"
					:showImage="card.showImage"
					:like="card.like"
					:showComments="card.showComments"
				/>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref } from "vue"
import type { CardSocial } from "@/components/cards/social/CardSocial1.vue"
import CardSocial1 from "@/components/cards/social/CardSocial1.vue"
const cardCount = 30

const cards = ref<CardSocial[]>([])

for (let i = 0; i < cardCount; i++) {
	const type = i % 3

	switch (type) {
		case 0:
			cards.value.push({
				showImage: true,
				hideText: undefined,
				showComments: true,
				like: undefined
			})
			break
		case 1:
			cards.value.push({
				showImage: undefined,
				hideText: undefined,
				showComments: undefined,
				like: true
			})
			break
		case 2:
			cards.value.push({
				showImage: true,
				hideText: true,
				showComments: undefined,
				like: true
			})
			break
	}
}
</script>

<style lang="scss" scoped>
.activity {
	container-type: inline-size;

	.masonry {
		--card-gap: 30px;
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
