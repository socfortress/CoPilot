<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Carousel</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/carousel"
					target="_blank"
					alt="docs"
					rel="nofollow noopener noreferrer"
				>
					<Icon :name="ExternalIcon" :size="16" />
					docs
				</a>
			</div>
		</div>

		<div class="components-list">
			<CardCodeExample title="Basic">
				<n-carousel draggable>
					<img class="carousel-img" src="https://picsum.photos/seed/VZLH8/640/415" />
					<img class="carousel-img" src="https://picsum.photos/seed/easJc3/640/415" />
					<img class="carousel-img" src="https://picsum.photos/seed/mW1uVF/640/415" />
					<img class="carousel-img" src="https://picsum.photos/seed/IqZMU/640/415" />
				</n-carousel>
				<template #code="{ html, css }">
					{{ html(`
					<n-carousel draggable>
						<img class="carousel-img" src="https://picsum.photos/seed/VZLH8/640/415" />
						<img class="carousel-img" src="https://picsum.photos/seed/easJc3/640/415" />
						<img class="carousel-img" src="https://picsum.photos/seed/mW1uVF/640/415" />
						<img class="carousel-img" src="https://picsum.photos/seed/IqZMU/640/415" />
					</n-carousel>
					`) }}

					{{
						css(`
						.carousel-img {
							width: 100%;
							height: 240px;
							object-fit: cover;
						}
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Arrow">
				<template #description>
					Set
					<n-text code>show-arrow</n-text>
					to show the arrow。
				</template>
				<n-carousel draggable show-arrow>
					<img class="carousel-img" src="https://picsum.photos/seed/VZLH8/640/415" />
					<img class="carousel-img" src="https://picsum.photos/seed/easJc3/640/415" />
					<img class="carousel-img" src="https://picsum.photos/seed/mW1uVF/640/415" />
					<img class="carousel-img" src="https://picsum.photos/seed/IqZMU/640/415" />
				</n-carousel>
				<template #code="{ html, css }">
					{{ html(`
					<n-carousel draggable show-arrow>
						<img class="carousel-img" src="https://picsum.photos/seed/VZLH8/640/415" />
						<img class="carousel-img" src="https://picsum.photos/seed/easJc3/640/415" />
						<img class="carousel-img" src="https://picsum.photos/seed/mW1uVF/640/415" />
						<img class="carousel-img" src="https://picsum.photos/seed/IqZMU/640/415" />
					</n-carousel>
					`) }}

					{{
						css(`
						.carousel-img {
							width: 100%;
							height: 240px;
							object-fit: cover;
						}
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Autoplay">
				<n-carousel draggable autoplay>
					<img class="carousel-img" src="https://picsum.photos/seed/VZLH8/640/415" />
					<img class="carousel-img" src="https://picsum.photos/seed/easJc3/640/415" />
					<img class="carousel-img" src="https://picsum.photos/seed/mW1uVF/640/415" />
					<img class="carousel-img" src="https://picsum.photos/seed/IqZMU/640/415" />
				</n-carousel>
				<template #code="{ html, css }">
					{{ html(`
					<n-carousel draggable autoplay>
						<img class="carousel-img" src="https://picsum.photos/seed/VZLH8/640/415" />
						<img class="carousel-img" src="https://picsum.photos/seed/easJc3/640/415" />
						<img class="carousel-img" src="https://picsum.photos/seed/mW1uVF/640/415" />
						<img class="carousel-img" src="https://picsum.photos/seed/IqZMU/640/415" />
					</n-carousel>
					`) }}

					{{
						css(`
						.carousel-img {
							width: 100%;
							height: 240px;
							object-fit: cover;
						}
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Vertical">
				<n-carousel draggable direction="vertical" dot-placement="right" style="width: 100%; height: 240px">
					<img class="carousel-img" src="https://picsum.photos/seed/VZLH8/640/415" />
					<img class="carousel-img" src="https://picsum.photos/seed/easJc3/640/415" />
					<img class="carousel-img" src="https://picsum.photos/seed/mW1uVF/640/415" />
					<img class="carousel-img" src="https://picsum.photos/seed/IqZMU/640/415" />
				</n-carousel>
				<template #code="{ html, css }">
					{{ html(`
					<n-carousel draggable direction="vertical" dot-placement="right" style="width: 100%; height: 240px">
						<img class="carousel-img" src="https://picsum.photos/seed/VZLH8/640/415" />
						<img class="carousel-img" src="https://picsum.photos/seed/easJc3/640/415" />
						<img class="carousel-img" src="https://picsum.photos/seed/mW1uVF/640/415" />
						<img class="carousel-img" src="https://picsum.photos/seed/IqZMU/640/415" />
					</n-carousel>
					`) }}

					{{
						css(`
						.carousel-img {
							width: 100%;
							height: 240px;
							object-fit: cover;
						}
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Slides per view">
				<template #description>
					Please note that this prop will conflict with
					<n-text code>loop</n-text>
					. If you need to customize the number of displays per view, then the
					<n-text code>loop</n-text>
					prop will be disabled.
				</template>
				<n-carousel :slides-per-view="3" :space-between="20" :loop="false" draggable>
					<img class="carousel-img" src="https://picsum.photos/seed/VZLH8/640/415" />
					<img class="carousel-img" src="https://picsum.photos/seed/easJc3/640/415" />
					<img class="carousel-img" src="https://picsum.photos/seed/mW1uVF/640/415" />
					<img class="carousel-img" src="https://picsum.photos/seed/IqZMU/640/415" />
				</n-carousel>
				<template #code="{ html, css }">
					{{ html(`
					<n-carousel :slides-per-view="3" :space-between="20" :loop="false" draggable>
						<img class="carousel-img" src="https://picsum.photos/seed/VZLH8/640/415" />
						<img class="carousel-img" src="https://picsum.photos/seed/easJc3/640/415" />
						<img class="carousel-img" src="https://picsum.photos/seed/mW1uVF/640/415" />
						<img class="carousel-img" src="https://picsum.photos/seed/IqZMU/640/415" />
					</n-carousel>
					`) }}

					{{
						css(`
						.carousel-img {
							width: 100%;
							height: 240px;
							object-fit: cover;
						}
						`)
					}}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NCarousel, NText } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
</script>

<style scoped>
.carousel-img {
	width: 100%;
	height: 240px;
	object-fit: cover;
}
</style>
