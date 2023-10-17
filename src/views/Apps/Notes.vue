<template>
	<div class="page">
		<div class="toolbar flex items-center mb-6 gap-4">
			<n-button type="primary" size="large" @click="newNote()">
				<Icon :name="AddIcon" class="mr-2"></Icon>
				Add notes
			</n-button>

			<n-select
				v-model:value="selectedLabels"
				multiple
				:options="options"
				size="large"
				placeholder="Labels filter..."
			/>
		</div>
		<div class="list">
			<n-image-group>
				<div class="masonry">
					<div class="note" v-for="note of filteredNotes" :key="note.id">
						<div class="n-image" v-if="note.image">
							<n-image :src="note.image" width="640" height="400" alt="image" lazy />
						</div>
						<div class="n-content" @click="selectNote(note)">
							<div class="n-title" v-if="note.title">{{ note.title }}</div>
							<div class="n-body" v-html="note.body" v-if="note.body"></div>
						</div>
						<div class="n-footer flex justify-between items-end" @click="selectNote(note)">
							<div class="n-date">{{ note.dateText }}</div>
							<div class="n-labels flex flex-wrap justify-end">
								<span
									class="n-label custom-label"
									v-for="label of note.labels"
									:key="label.id"
									:style="`--label-color:${labelsColors[label.id]}`"
								>
									{{ label.title }}
								</span>
							</div>
						</div>
					</div>
				</div>
			</n-image-group>
		</div>

		<n-modal v-model:show="showModal">
			<div class="note-modal">
				<div class="form flex flex-col" v-if="selectedNote">
					<div v-if="selectedNote.id && selectedNote.image" class="mb-4">
						<img :src="selectedNote.image" />
					</div>
					<n-upload class="mb-2" :max="1" v-else>
						<n-upload-dragger>
							<div style="margin-bottom: 12px">
								<Icon :name="ImageIcon" :size="48" :depth="3"></Icon>
							</div>
							<n-text style="font-size: 16px">Click or drag a file to this area to upload</n-text>
							<n-p depth="3" style="margin: 8px 0 0 0">
								Strictly prohibit from uploading sensitive information. For example, your bank card PIN
								or your credit card expiry date.
							</n-p>
						</n-upload-dragger>
					</n-upload>
					<n-input v-model:value="selectedNote.title" placeholder="Title" class="mb-4" />
					<n-input
						v-model:value="selectedNote.body"
						placeholder="Body"
						type="textarea"
						class="mb-4"
						:autosize="{
							minRows: 2,
							maxRows: 7
						}"
					/>
					<div class="flex item-center justify-between gap-4">
						<div class="flex item-center gap-4 grow">
							<div class="n-labels" v-if="selectedNote.id">
								<span
									class="n-label custom-label"
									v-for="label of selectedNote.labels"
									:key="label.id"
									:style="`--label-color:${labelsColors[label.id]}`"
								>
									{{ label.title }}
								</span>
							</div>
							<div v-else class="w-full">
								<n-select multiple class="w-full" :options="options" placeholder="Labels filter..." />
							</div>
						</div>
						<div class="flex item-center gap-4">
							<n-button v-if="selectedNote.id">Delete</n-button>
							<n-button
								@click="save(selectedNote)"
								strong
								secondary
								type="primary"
								:disabled="!noteValid"
							>
								Save
							</n-button>
						</div>
					</div>
				</div>
			</div>
		</n-modal>
	</div>
</template>

<script lang="ts" setup>
import { NButton, NImage, NImageGroup, NSelect, NModal, NInput, NUpload, NUploadDragger, NText, NP } from "naive-ui"
import Icon from "@/components/common/Icon.vue"

import { type Note, getNotes, labels } from "@/mock/notes"
import { type Ref, ref, computed } from "vue"
import _clone from "lodash/cloneDeep"
import dayjs from "@/utils/dayjs"
import { useThemeStore } from "@/stores/theme"

const AddIcon = "fluent:notebook-add-24-regular"
const ImageIcon = "carbon:image"

const notes: Ref<Note[]> = ref(getNotes())
const options = labels.map(l => ({
	label: l.title,
	value: l.id
}))

const secondaryColors = computed(() => useThemeStore().secondaryColors)

const labelsColors = {
	personal: secondaryColors.value["secondary1"],
	office: secondaryColors.value["secondary2"],
	important: secondaryColors.value["secondary3"],
	shop: secondaryColors.value["secondary4"]
} as unknown as { [key: string]: string }

const selectedLabels = ref([])
const selectedNote = ref<Note | null>(null)
const filteredNotes = computed(() =>
	notes.value.filter(n => {
		if (!selectedLabels.value.length) {
			return true
		}

		for (const label of selectedLabels.value) {
			return n.labels.map(l => l.id).includes(label)
		}

		return false
	})
)
const noteValid = computed(() => !!selectedNote.value?.title || !!selectedNote.value?.body)

const showModal = computed({ get: () => selectedNote.value !== null, set: () => (selectedNote.value = null) })

function newNote() {
	selectedNote.value = {
		id: "",
		date: new Date(),
		dateText: dayjs().format("HH:mm"),
		title: "",
		body: "",
		image: "",
		labels: []
	}
}
function selectNote(note: Note) {
	selectedNote.value = { ..._clone(note), body: note.body.replace(/<br\/>/gim, "\n") }
}
function save(note: Note) {
	const index = notes.value.findIndex(n => n.id === note.id)
	note.body = note.body.replace(/\n/gim, "<br/>")

	if (index !== -1) {
		notes.value[index] = note
	} else {
		note.id = new Date().getTime() + ""
		notes.value = [note, ...notes.value]
	}

	selectedNote.value = null
}
</script>

<style lang="scss" scoped>
.page {
	.toolbar {
		max-width: 600px;

		.n-select {
			:deep(.n-base-selection__border) {
				border-color: var(--divider-020-color);
			}
			:deep(.n-base-selection-tags) {
				background-color: var(--bg-secondary-color);
			}
		}
	}
	.list {
		container-type: inline-size;

		.masonry {
			--notes-gap: 1.25em;
			column-count: 4;
			column-gap: var(--notes-gap);

			@container (min-width: 1600px) {
				column-count: 5;
			}

			@container (max-width: 1200px) {
				column-count: 3;
			}

			@container (max-width: 900px) {
				column-count: 2;
			}

			@container (max-width: 600px) {
				column-count: 1;
			}

			.note {
				margin-bottom: var(--notes-gap);
				transition: all 0.25s;
				box-sizing: border-box;
				width: 100%;
				background-color: var(--bg-color);
				border-radius: var(--border-radius);
				border: 1px solid var(--border-color);
				overflow: hidden;
				cursor: pointer;

				.n-content {
					padding: 20px;

					.n-title {
						font-size: 18px;
						line-height: 1.3;
						font-weight: bold;
						margin-bottom: 20px;
						opacity: 0;
						font-family: var(--font-family-display);
						animation: note-el-fade 0.6s forwards;
					}

					.n-body {
						font-size: 14px;
						opacity: 0;
						color: var(--fg-secondary-color);
						animation: note-el-fade 0.6s 0.2s forwards;
					}
				}

				.n-footer {
					padding: 16px 20px;
					opacity: 0;
					font-size: 12px;
					color: var(--primary-color);
					animation: note-el-fade 0.6s 0.4s forwards;
				}

				@keyframes note-el-fade {
					from {
						opacity: 0;
					}
					to {
						opacity: 1;
					}
				}

				&:hover {
					transform: translateY(-3px);
				}
			}
		}
	}

	.custom-label::before {
		z-index: 0;
	}
}
</style>
<style lang="scss">
.note-modal {
	background-color: var(--bg-body);
	border-radius: var(--border-radius);
	width: 90vw;
	max-width: 500px;

	.form {
		background-color: var(--bg-color);
		padding: 20px;

		img {
			border-radius: var(--border-radius-small);
		}
	}

	.custom-label::before {
		z-index: 0;
	}
}
</style>
