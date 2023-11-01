<template>
	<n-card hoverable content-style="padding: 0;">
		<div class="flex sm:flex-row flex-col sm:items-stretch">
			<div class="card-cover basis-2/5">
				<img src="@/assets/images/ecommerce/premium-headphones.jpg" width="400" height="400" />
			</div>
			<div class="basis-3/5 flex flex-col">
				<div class="card-header flex justify-between items-center">
					<div>
						<span>Premium Headphones</span>
						<span class="ml-3 opacity-70">$399,00</span>
					</div>
					<div class="flex items-center">
						<Icon class="mr-3" :size="20" :name="HeartIcon"></Icon>
						<Icon :size="20" :name="ShareIcon"></Icon>
					</div>
				</div>
				<div class="card-content grow">
					<div class="mb-2">
						<n-rate readonly :allow-half="true" :default-value="4.5" color="#FFB600" />
					</div>
					<p>
						Discover the ultimate sound experience with our premium headphones! Immerse yourself in
						crystal-clear audio and deep, rich bass. Our cutting-edge technology ensures exceptional noise
						cancellation, allowing you to escape into your favorite music or podcasts.
						<br />
						<br />
						With a sleek and comfortable design, these headphones are perfect for long listening sessions or
						on-the-go use. Whether you're a music lover, a gamer, or a podcast enthusiast, these headphones
						will elevate your audio enjoyment to new heights. Treat yourself to the best sound quality and
						indulge in pure sonic bliss with our top-of-the-line headphones.
					</p>
				</div>
				<div class="card-footer">
					<div class="flex items-center justify-between">
						<n-button type="primary" quaternary>Details</n-button>
						<n-button type="primary">
							<Icon class="mr-3" :name="CartIcon"></Icon>
							Add to cart
						</n-button>
					</div>
				</div>
			</div>
		</div>
	</n-card>
</template>

<script setup lang="ts">
import { NCard, NButton, NRate } from "naive-ui"
import Icon from "@/components/common/Icon.vue"

const CartIcon = "tabler:shopping-cart"
const HeartIcon = "ion:heart-outline"
const ShareIcon = "carbon:share"
</script>

<style scoped lang="scss">
.n-card {
	overflow: hidden;
	.card-cover {
		min-height: 100%;

		img {
			display: block;
			width: 100%;
			height: 100%;
			max-height: 100%;
			object-fit: cover;
			object-position: center center;
		}
	}

	.card-header {
		box-sizing: border-box;
		display: flex;
		align-items: center;
		font-family: var(--font-family-display);
		font-weight: 700;
		font-size: var(--n-title-font-size);
		padding: var(--n-padding-top) var(--n-padding-left) var(--n-padding-bottom) var(--n-padding-left);
	}

	.card-content {
		box-sizing: border-box;
		padding: 0 var(--n-padding-left) var(--n-padding-bottom) var(--n-padding-left);
		font-size: var(--n-font-size);
	}

	.card-footer {
		box-sizing: border-box;
		transition:
			background-color 0.3s var(--n-bezier),
			border-color 0.3s var(--n-bezier);
		background-clip: padding-box;
		background-color: var(--n-action-color);
		padding: var(--n-padding-bottom) var(--n-padding-left);
		border-bottom-left-radius: var(--n-border-radius);
		border-bottom-right-radius: var(--n-border-radius);
	}

	@media (max-width: 639px) {
		.card-cover {
			min-height: initial;
			max-height: 200px;
			overflow: hidden;

			img {
				max-height: 200px;
			}
		}
	}
}
</style>
