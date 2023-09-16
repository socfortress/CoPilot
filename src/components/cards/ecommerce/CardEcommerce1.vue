<template>
	<n-card hoverable>
		<template #cover>
			<img src="@/assets/images/ecommerce/super-bike.jpg" width="900" height="400" />
		</template>
		<template #header>
			<span>Super bike</span>
			<span class="ml-3 opacity-70">$644,00</span>
		</template>
		<template #header-extra>
			<n-icon class="mr-3" :size="20" color="#FF0156">
				<HeartIcon />
			</n-icon>
			<n-icon :size="20">
				<ShareIcon />
			</n-icon>
		</template>
		<template #default>
			<p>
				Introducing the perfect bike for your adventures! Our top-of-the-line bicycle combines sleek design,
				superior performance, and unbeatable comfort.
				<br />
				<br />
				With its lightweight frame and precision engineering, this bike offers effortless speed and agility.
				Equipped with advanced gear systems, it effortlessly conquers any terrain, whether it's a challenging
				mountain trail or a smooth city street. Experience the joy of cycling with our exceptional bike,
				designed for both beginners and seasoned riders. Upgrade your ride and embrace the freedom of the open
				road.
			</p>
		</template>
		<template #action>
			<div class="flex items-center justify-between">
				<n-button type="primary" quaternary>Details</n-button>
				<n-button type="primary">
					<n-icon class="mr-3">
						<CartIcon />
					</n-icon>
					Add to cart
				</n-button>
			</div>
		</template>
	</n-card>
</template>

<script setup lang="ts">
import { NCard, NButton, NIcon } from "naive-ui"
import CartIcon from "@vicons/tabler/ShoppingCart"
import HeartIcon from "@vicons/ionicons5/Heart"
import ShareIcon from "@vicons/carbon/Share"
</script>
