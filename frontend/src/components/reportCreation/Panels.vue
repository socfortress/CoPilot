<template>
	<div class="report-panels">
		<div class="panels-container" v-if="panelsList.length">
			<div
				class="panel"
				v-for="panel of panelsList"
				:key="panel.id"
				:style="panel.width ? `flex-basis:${panel.width}%` : ''"
			>
				<div class="toolbar">
					<n-popover trigger="hover" overlap raw placement="right-start">
						<template #trigger>
							<n-button size="tiny">
								<template #icon>
									<Icon :name="MenuIcon"></Icon>
								</template>
							</n-button>
						</template>
						<div class="popover-input-container">
							<div class="w-52 flex items-center gap-3 py-2 px-5">
								<span class="font-mono w-12">{{ panel.width }}</span>
								<n-slider :tooltip="false" v-model:value="panel.width" :min="0" :max="100" :step="10" />
							</div>
							<!--
								<n-input-number
									size="tiny"
									v-model:value="panel.width"
									:min="0"
									:max="100"
									:step="10"
									class="max-w-32"
								/>
							-->
						</div>
					</n-popover>
				</div>
				<div class="content">
					<img :src="'data:image/png;base64,' + panel.image" v-if="panel.image" />
					<iframe :src="panel.url + '&theme=' + panelTheme" v-else></iframe>
					<!--
						<iframe :src="panel.panel_url + '&theme=light'" v-show="panelTheme === 'light'"></iframe>
						<iframe :src="panel.panel_url + '&theme=dark'" v-show="panelTheme === 'dark'"></iframe>
					-->
				</div>
			</div>
		</div>

		<div class="toolbar mt-5">
			<n-button type="success" v-if="linksList.length" @click="print()" :loading="loading">
				<template #icon>
					<Icon :name="PrintIcon"></Icon>
				</template>
				Print Report
			</n-button>
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref, nextTick, computed, toRefs, watch, onBeforeMount } from "vue"
import { useMessage, NButton, NInputNumber, NSlider, NPopover } from "naive-ui"
import type { PanelLink, PanelImage } from "@/types/reporting"
import Icon from "@/components/common/Icon.vue"
import { type ThemeName } from "@/types/theme.d"
import { useThemeStore } from "@/stores/theme"
import Api from "@/api"
import { mockImage, mockLinks } from "./data"
import { saveAs } from "file-saver"
import html2canvas from "html2canvas"

const props = defineProps<{
	linksList: PanelLink[]
}>()
const { linksList } = toRefs(props)

const MenuIcon = "carbon:overflow-menu-horizontal"
const PrintIcon = "carbon:printer"
const message = useMessage()
const imagesList = ref<PanelImage[]>([])
const panelTheme = computed<ThemeName>(() => useThemeStore().themeName)
const loadingImages = ref(false)
const loadingPrint = ref(false)
const loading = computed(() => loadingImages.value || loadingPrint.value)
const panelsList = ref([])

watch(linksList, () => {
	createPanels()
})

onBeforeMount(() => {
	createPanels()
})

function createPanels() {
	const panels = []
	for (const i in mockLinks /*linksList.value*/) {
		panels.push({
			id: mockLinks[i].panel_id, // linksList.value[i].panel_id,
			url: mockLinks[i].panel_url, // linksList.value[i].panel_url,
			image: imagesList.value[i]?.base64_image || mockImage,
			width: 50
		})
	}

	panelsList.value = panels
}

function print() {
	loadingPrint.value = true
	getImages(() => {
		nextTick(() => {
			setTimeout(() => {
				html2canvas(document.querySelector(".panels-container"))
					.then(canvas => {
						//document.body.appendChild(canvas)
						loadingPrint.value = false
						const dataURL = canvas.toDataURL("image/png", 1)
						console.log(dataURL)
						saveAs(dataURL, "report.png")
					})
					.catch(() => {
						loadingPrint.value = false
					})
			}, 2000)
		})
	})
}

function getImages(cb?: () => void) {
	loadingImages.value = true

	Api.reporting
		.generatePanelsImages(linksList.value.map(o => o.panel_url + "&theme=" + panelTheme.value))
		.then(res => {
			if (res.data.success) {
				imagesList.value = res.data?.base64_images || []

				if (cb) {
					cb()
				}
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingImages.value = false
		})
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
		padding: 1vw;

		.panel {
			overflow: hidden;
			flex-grow: 1;
			min-width: 200px;
			padding: 1vw;
			position: relative;

			.toolbar {
				position: absolute;
				top: 8px;
				right: 8px;
				backdrop-filter: blur(2px);
			}
			.content {
				border-radius: var(--border-radius);
				background-color: var(--bg-secondary-color);
				border: var(--border-small-050);
				overflow: hidden;
			}

			iframe {
				width: 100%;
				aspect-ratio: 1;
			}
			img {
				width: 100%;
			}
		}
	}
}

.popover-input-container {
	background-color: var(--bg-secondary-color);
	border-radius: var(--border-radius);
}
</style>
