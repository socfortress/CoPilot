<template>
	<footer class="footer py-4" :class="{ boxed }">
		<div class="wrap flex items-center justify-end gap-3">
			<div class="copy">
				<template v-if="portalTitle">© Copyright {{ year }} {{ portalTitle }}</template>
				<template v-else>© Copyright {{ year }}</template>
			</div>
		</div>
	</footer>
</template>

<script lang="ts" setup>
import { computed, ref } from "vue"
import { usePortalSettingsStore } from "@/stores/portalSettings"

const { boxed } = defineProps<{
	boxed: boolean
}>()

const portalSettingsStore = usePortalSettingsStore()
const portalTitle = computed(() => portalSettingsStore.portalTitle)
const year = ref(new Date().getFullYear())
</script>

<style lang="scss" scoped>
.footer {
	width: 100%;
	max-width: 100%;
	overflow: hidden;
	font-size: 13px;

	.wrap {
		overflow: hidden;
		width: 100%;
		max-width: 100%;
		margin: 0 auto;
		padding: 0 var(--view-padding);

		.copy {
			line-height: 1.6;

			a {
				font-weight: bold;
				text-decoration: none;
			}
			* {
				display: inline;
			}
			i {
				display: inline-block;
			}
		}
	}

	&.boxed {
		.wrap {
			max-width: var(--boxed-width);
		}
	}

	@media (max-width: 700px) {
		font-size: 10px;

		i.n-icon {
			font-size: 18px !important;
		}
	}
}
</style>
