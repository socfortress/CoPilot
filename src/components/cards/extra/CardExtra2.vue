<template>
	<n-card hoverable content-style="padding: 0;">
		<n-carousel show-arrow autoplay dot-type="line" :space-between="20" draggable>
			<img class="carousel-img" src="https://picsum.photos/seed/VZLH8/1600/600" />
			<img class="carousel-img" src="https://picsum.photos/seed/easJc3/1600/600" />
			<img class="carousel-img" src="https://picsum.photos/seed/mW1uVF/1600/600" />
			<img class="carousel-img" src="https://picsum.photos/seed/IqZMU/1600/600" />
		</n-carousel>
	</n-card>
</template>
<script setup lang="ts">
import { NCard, NCarousel } from "naive-ui"
</script>

<style scoped lang="scss">
.n-card {
	overflow: hidden;
	.carousel-img {
		width: 100%;
		height: 100%;
		object-fit: cover;
		object-position: center;
	}
}
</style>
