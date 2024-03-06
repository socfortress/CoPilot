<template>
	<div class="report-panels">
		<div class="panels-container" v-if="panelsBlock.length">
			<div
				class="panel"
				v-for="panel of panelsBlock"
				:key="panel.id"
				:style="panel.width ? `flex-basis:${panel.width}%` : ''"
			>
				<div class="toolbar">
					<n-popover trigger="hover" overlap raw placement="right-start" class="popover-report-panel-slider">
						<template #trigger>
							<n-button size="tiny">
								<template #icon>
									<Icon :name="MenuIcon"></Icon>
								</template>
							</n-button>
						</template>
						<div class="w-52 flex items-center gap-3 py-2 px-5">
							<span class="font-mono w-12">{{ panel.width / 100 }}</span>
							<n-slider :tooltip="false" v-model:value="panel.width" :min="0" :max="100" :step="10" />
						</div>
					</n-popover>
				</div>
				<div class="content">
					{{ panel.name }}
				</div>
			</div>
		</div>

		<div class="toolbar mt-5">
			<n-button type="success" v-if="panelsBlock.length" @click="print()" :loading="loading">
				<template #icon>
					<Icon :name="PrintIcon"></Icon>
				</template>
				Print Report
			</n-button>
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref, computed, toRefs, watch } from "vue"
import { NButton, NSlider, NPopover } from "naive-ui"
import type { PanelLink, Panel } from "@/types/reporting"
import Icon from "@/components/common/Icon.vue"
// import Api from "@/api"
// import { saveAs } from "file-saver"

interface PanelBlock {
	id: string | number
	name: string
	width: number
}

const props = defineProps<{
	panelsList?: Panel[]
	linksList?: PanelLink[]
}>()
const { panelsList } = toRefs(props)

const MenuIcon = "carbon:overflow-menu-horizontal"
const PrintIcon = "carbon:printer"
// const message = useMessage()
const loadingImages = ref(false)
const loadingPrint = ref(false)
const loading = computed(() => loadingImages.value || loadingPrint.value)
const panelsBlock = ref<PanelBlock[]>([])

watch(panelsList, val => {
	createPanels(val || [])
})

function createPanels(list: Panel[]) {
	const panels: PanelBlock[] = []

	for (const panel of list) {
		panels.push({
			id: panel.id,
			name: panel.title,
			width: 50
		})
	}

	panelsBlock.value = panels
}

function print() {
	loadingPrint.value = true

	setTimeout(() => {
		loadingPrint.value = false
	}, 2000)
}
</script>

<style lang="scss" scoped>
.report-panels {
	.panels-container {
		border-radius: var(--border-radius);
		background-color: var(--bg-secondary-color);
		border: var(--border-small-050);
		display: flex;
		flex-wrap: wrap;
		padding: clamp(5px, 1vw, 10px);

		.panel {
			overflow: hidden;
			flex-grow: 1;
			min-width: 200px;
			padding: clamp(5px, 1vw, 10px);
			position: relative;

			.toolbar {
				position: absolute;
				top: 7px;
				right: 7px;
				backdrop-filter: blur(2px);
			}
			.content {
				border-radius: var(--border-radius);
				background-color: var(--bg-color);
				border: var(--border-small-050);
				overflow: hidden;
				display: flex;
				align-items: center;
				justify-content: center;
				aspect-ratio: 1.6;
				font-size: clamp(12px, 1.7vw, 18px);
				font-weight: bold;
				padding: 3vw;
				text-align: center;
			}
		}
	}
}
</style>

<style lang="scss">
.popover-report-panel-slider {
	background-color: rgba(var(--modal-color-rgb), 0.5);
	border-radius: var(--border-radius);
	overflow: hidden;
	backdrop-filter: blur(5px);
}
</style>
