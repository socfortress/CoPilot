<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Upload</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/upload"
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
				<n-upload
					action="https://www.mocky.io/v2/5e4bafc63100007100d8b70f"
					:headers="{
						'naive-info': 'hello!'
					}"
					:data="{
						'naive-data': 'cool! naive!'
					}"
				>
					<n-button>Upload File</n-button>
				</n-upload>
				<template #code="{ html }">
					{{ html(`
					<n-upload
						action="https://www.mocky.io/v2/5e4bafc63100007100d8b70f"
						:headers="{
							'naive-info': 'hello!'
						}"
						:data="{
							'naive-data': 'cool! naive!'
						}"
					>
						<n-button>Upload File</n-button>
					</n-upload>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Drag to upload">
				<template #description>
					You can set
					<n-text code>directory-dnd</n-text>
					to
					<n-text code>true</n-text>
					to make directory drag and drop available.
				</template>
				<n-upload multiple directory-dnd action="https://www.mocky.io/v2/5e4bafc63100007100d8b70f" :max="5">
					<n-upload-dragger>
						<div style="margin-bottom: 12px">
							<Icon :name="ArchiveIcon" :size="48" :depth="3" />
						</div>
						<n-text style="font-size: 16px">Click or drag a file to this area to upload</n-text>
						<n-p depth="3" style="margin: 8px 0 0 0">
							Strictly prohibit from uploading sensitive information. For example, your bank card PIN or
							your credit card expiry date.
						</n-p>
					</n-upload-dragger>
				</n-upload>
				<template #code="{ html, js }">
					{{ html(`
					<n-upload multiple directory-dnd action="https://www.mocky.io/v2/5e4bafc63100007100d8b70f" :max="5">
						<n-upload-dragger>
							<div style="margin-bottom: 12px">
								<n-icon size="48" :depth="3">
									<archive-icon />
								</n-icon>
							</div>
							<n-text style="font-size: 16px">Click or drag a file to this area to upload</n-text>
							<n-p depth="3" style="margin: 8px 0 0 0">
								Strictly prohibit from uploading sensitive information. For example, your bank card PIN
								or your credit card expiry date.
							</n-p>
						</n-upload-dragger>
					</n-upload>
					`) }}

					{{
						js(`
						import { ArchiveOutline as ArchiveIcon } from '@vicons/ionicons5'
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Pictures wall">
				<template #description>
					By default, this will use Naive UI's internal preview component. You can also use
					<n-text code>on-preview</n-text>
					to customize what to do when previewing a file.
				</template>

				<n-upload
					action="https://www.mocky.io/v2/5e4bafc63100007100d8b70f"
					:default-file-list="fileList"
					list-type="image-card"
				>
					Click to Upload
				</n-upload>
				<template #code="{ html, js }">
					{{ html(`
					<n-upload
						action="https://www.mocky.io/v2/5e4bafc63100007100d8b70f"
						:default-file-list="fileList"
						list-type="image-card"
					>
						Click to Upload
					</n-upload>

					`) }}

					{{
						js(`
						const fileList = ref\<\UploadFileInfo[]\>\([
							{
								id: "a",
								name: "我是上传出错的普通文件.png",
								status: "error"
							},
							{
								id: "b",
								name: "我是普通文本.doc",
								status: "finished",
								type: "text/plain"
							},
							{
								id: "c",
								name: "我是自带url的图片.png",
								status: "finished",
								url: "https://picsum.photos/seed/FsNXmz/460/460"
							},
							{
								id: "d",
								name: "我是上传进度99%的文本.doc",
								status: "uploading",
								percentage: 99
							}
						])
						
						`)
					}}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NUpload, NButton, NText, NUploadDragger, NP, type UploadFileInfo } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"

const ArchiveIcon = "ion:archive-outline"
import { ref } from "vue"

const fileList = ref<UploadFileInfo[]>([
	{
		id: "a",
		name: "我是上传出错的普通文件.png",
		status: "error"
	},
	{
		id: "b",
		name: "我是普通文本.doc",
		status: "finished",
		type: "text/plain"
	},
	{
		id: "c",
		name: "我是自带url的图片.png",
		status: "finished",
		url: "https://picsum.photos/seed/FsNXmz/460/460"
	},
	{
		id: "d",
		name: "我是上传进度99%的文本.doc",
		status: "uploading",
		percentage: 99
	}
])
</script>
