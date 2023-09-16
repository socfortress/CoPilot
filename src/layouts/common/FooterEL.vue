<template>
	<footer class="footer" :class="{ boxed }">
		<div class="wrap flex items-center justify-end gap-3">
			<div class="copy">
				Made with
				<n-icon :size="22" :color="style['--primary-color']">
					<BrainIcon />
				</n-icon>
				By
				<a href="https://dverse.studio/" target="_blank" alt="D*VERSE" rel="noopener noreferrer">
					D*VERSE Studio
				</a>
				All rights Reserved © Copyright {{ year }}
			</div>
		</div>
	</footer>
</template>

<script lang="ts" setup>
import { computed, ref, toRefs } from "vue"
import { NIcon } from "naive-ui"
import BrainIcon from "@/assets/icons/brain-icon.svg"
import { useThemeStore } from "@/stores/theme"

defineOptions({
	name: "FooterEL"
})

const props = defineProps<{
	boxed: boolean
}>()
const { boxed } = toRefs(props)
const style: { [key: string]: any } = computed(() => useThemeStore().style)

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
}
</style>
