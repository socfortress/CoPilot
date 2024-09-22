<template>
	<div class="sigma-queries-actions flex flex-wrap gap-2">
		<QueryActiveAllForm v-slot="{ loading, togglePopup }" @updated="emitUpdate()">
			<n-button size="small" type="primary" secondary strong :loading @click.stop="togglePopup()">
				<template #icon>
					<Icon :name="EditIcon" />
				</template>
				Update queries status
			</n-button>
		</QueryActiveAllForm>

		<QueryUploadFile v-slot="{ loading, togglePopup }" @updated="emitUpdate()">
			<n-button size="small" type="success" secondary strong :loading @click.stop="togglePopup()">
				<template #icon>
					<Icon :name="UploadFileIcon" />
				</template>
				Upload queries from FIle
			</n-button>
		</QueryUploadFile>

		<QueryUploadDB v-slot="{ loading, togglePopup }" @updated="emitUpdate()">
			<n-button size="small" type="success" secondary strong :loading @click.stop="togglePopup()">
				<template #icon>
					<Icon :name="UploadIcon" />
				</template>
				Upload queries to DB
			</n-button>
		</QueryUploadDB>

		<QueryDownloadAll v-slot="{ loading, togglePopup }" @updated="emitUpdate()">
			<n-button size="small" type="success" secondary strong :loading @click.stop="togglePopup()">
				<template #icon>
					<Icon :name="DownloadIcon" />
				</template>
				Download queries
			</n-button>
		</QueryDownloadAll>

		<QueryDeleteAll v-slot="{ loading, togglePopup }" @updated="emitUpdate()">
			<n-button size="small" type="error" secondary strong :loading @click.stop="togglePopup()">
				<template #icon>
					<Icon :name="DeleteIcon" />
				</template>
				Delete all queries
			</n-button>
		</QueryDeleteAll>
	</div>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import { NButton } from "naive-ui"
import QueryActiveAllForm from "./actionsProviders/QueryActiveAllForm.vue"
import QueryDeleteAll from "./actionsProviders/QueryDeleteAll.vue"
import QueryDownloadAll from "./actionsProviders/QueryDownloadAll.vue"
import QueryUploadDB from "./actionsProviders/QueryUploadDB.vue"
import QueryUploadFile from "./actionsProviders/QueryUploadFile.vue"

const emit = defineEmits<{
	(e: "updated"): void
}>()

const EditIcon = "uil:edit-alt"
const DeleteIcon = "ph:trash"
const DownloadIcon = "carbon:cloud-download"
const UploadIcon = "carbon:cloud-upload"
const UploadFileIcon = "carbon:upload"

function emitUpdate() {
	emit("updated")
}
</script>
