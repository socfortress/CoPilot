<template>
	<footer class="footer" :class="{ boxed }">
		<div class="wrap flex items-center justify-end gap-3">
			<div class="copy">
				Made with
				<Icon :size="22" :color="style['primary-color']" class="mx-1">
					<BrainIcon />
				</Icon>
				By
				<a
					href="https://www.socfortress.co/"
					target="_blank"
					alt="SOCFortress"
					rel="noopener noreferrer"
					class="mx-1"
				>
					SOCFortress
				</a>
				All rights Reserved © Copyright {{ year }}
			</div>
		</div>
	</footer>
</template>

<script lang="ts" setup>
import BrainIcon from "@/assets/icons/brain-icon.svg"
import Icon from "@/components/common/Icon.vue"
import { useThemeStore } from "@/stores/theme"
import { computed, ref, toRefs } from "vue"

const props = defineProps<{
	boxed: boolean
}>()
const { boxed } = toRefs(props)

const themeStore = useThemeStore()
const style = computed(() => themeStore.style)
const year = ref(new Date().getFullYear())
</script>

<style lang="scss" scoped>
.footer {
	width: 100%;
	max-width: 100%;
	padding: var(--view-padding);
	padding-top: 0;
	overflow: hidden;
	font-size: 13px;

	.wrap {
		overflow: hidden;
		width: 100%;
		max-width: 100%;

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
		padding: 0;
		.wrap {
			padding: var(--view-padding);
			padding-top: 0;
			max-width: var(--boxed-width);
			margin: 0 auto;
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
