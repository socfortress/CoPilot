<template>
	<div class="report-panels">
		<div class="panels-container grid grid-cols-2 gap-6 p-6" :class="{ printing }" v-if="panelsList.length">
			<div class="panel" v-for="panel of panelsList" :key="panel.id">
				<img :src="'data:image/png;base64,' + panel.image" v-if="panel.image" />
				<iframe :src="panel.url + '&theme=' + panelTheme" v-else></iframe>
				<!--
					<iframe :src="panel.panel_url + '&theme=light'" v-show="panelTheme === 'light'"></iframe>
					<iframe :src="panel.panel_url + '&theme=dark'" v-show="panelTheme === 'dark'"></iframe>
				-->
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
import { ref, nextTick, computed, toRefs } from "vue"
import { NButton, useMessage } from "naive-ui"
import type { PanelLink, PanelImage } from "@/types/reporting"
import Icon from "@/components/common/Icon.vue"
import { type ThemeName } from "@/types/theme.d"
import { useThemeStore } from "@/stores/theme"
import Api from "@/api"
import { mockImage } from "./data"
import { saveAs } from "file-saver"
import html2canvas from "html2canvas"

// @ts-ignore
// import domtoimage from "dom-to-image-more"

const isDirty = defineModel<boolean>("isDirty", { default: false })

const props = defineProps<{
	linksList: PanelLink[]
}>()
const { linksList } = toRefs(props)

const PrintIcon = "carbon:printer"
const message = useMessage()
const imagesList = ref<PanelImage[]>([])
const printing = ref(false)
// const panelTheme = ref<"light" | "dark">("light")
const panelTheme = computed<ThemeName>(() => useThemeStore().themeName)
const loadingImages = ref(false)
const loadingPrint = ref(false)
const loading = computed(() => loadingImages.value || loadingPrint.value)

const panelsList = computed(() => {
	const panels = []

	for (const i in linksList.value) {
		panels.push({
			id: linksList.value[i].panel_id,
			url: linksList.value[i].panel_url,
			image: imagesList.value[i]?.base64_image // || mockImage
		})
	}

	return panels
})

function print() {
	/*
	html2canvas(document.querySelector(".panels-container")).then(canvas => {
		//document.body.appendChild(canvas)
		console.log(canvas.toDataURL("image/jpeg", 0.9))
	})
*/

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

	/*
	printing.value = true
	// panelTheme.value = "light"

	nextTick(() => {
		setTimeout(() => {
			window.print()
			// panelTheme.value = "dark"
			printing.value = false
		}, 2000)
	})
	*/

	/*
	// @ts-ignore
	html2canvas(document.querySelector(".page"), { allowTaint: true, useCORS: true }).then(canvas => {
		//document.body.appendChild(canvas)
		console.log(canvas.toDataURL("image/jpeg", 0.9))
	})
	var node = document.querySelector(".page")

	domtoimage
		.toPng(node)
		// @ts-ignore
		.then(function (dataUrl) {
			var img = new Image()
			img.src = dataUrl
			console.log(dataUrl)
			document.body.appendChild(img)
		})
		// @ts-ignore
		.catch(function (error) {
			console.error("oops, something went wrong!", error)
		})
		*/
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

		.panel {
			border-radius: var(--border-radius);
			background-color: var(--bg-secondary-color);
			border: var(--border-small-050);
			overflow: hidden;

			iframe {
				width: 100%;
				height: 500px;
			}
		}

		&.printing {
			grid-template-columns: repeat(1, minmax(0, 1fr));
			max-width: 600px;
		}
	}
}
</style>

<style lang="scss">
@media print {
	html,
	body {
		overflow: initial;
	}
	body {
		#app {
			height: initial;
			background-color: white;

			& > .n-config-provider {
				& > .layout {
					display: block;
					height: initial;
					background-color: white;

					& > .header-bar {
						display: none;
					}
					& > .main {
						background-color: white;
						overflow: initial;
						height: initial;

						header.toolbar {
							display: none;
						}
						footer.footer {
							display: none;
						}

						& > .n-scrollbar {
							overflow: initial;
							height: initial;

							& > .n-scrollbar-container {
								overflow: initial;
								height: initial;
							}
						}

						.page {
							.report-wizard {
								display: none;
							}
							.report-panels {
								max-width: 600px;

								.panels-container {
									grid-template-columns: repeat(1, minmax(0, 1fr));

									.panel {
										border: 2px solid black;
									}
								}
								.toolbar {
									display: none;
								}
							}
						}
					}
				}
			}
		}
	}
}
</style>
