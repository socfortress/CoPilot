<template>
    <n-spin :show="loading" class="creation-report-form">
        <n-form ref="formRef" :model="form" :rules="rules">
            <div class="flex flex-col gap-8">
                <div class="flex flex-col gap-2">
                    <n-form-item v-if="showIndexNameField" label="Index name" path="index_name">
                        <n-select
                            v-model:value="form.index_name"
                            :options="indexNamesOptions"
                            placeholder="Select..."
                            clearable
                            filterable
                            to="body"
                            :disabled="disableIndexNameField"
                            :loading="loadingIndexNames"
                        />
                    </n-form-item>

                    <div v-if="showSourceField">
                        <n-form-item path="source" :show-require-mark="false" class="source-field">
                            <template #label>
                                <div class="flex items-end justify-between gap-2">
                                    <span>
                                        Source
                                        <span class="n-form-item-label__asterisk">*</span>
                                    </span>

                                    <span v-if="isSocfortressRecommendsAvailable">
                                        <n-button
                                            :loading="loadingSocfortressRecommendsWazuh"
                                            size="tiny"
                                            ghost
                                            type="primary"
                                            @click="getSocfortressRecommendsWazuh()"
                                        >
                                            SOCFortress Recommends
                                        </n-button>
                                    </span>
                                </div>
                            </template>
                            <n-input
                                v-if="arbitrarySourceField"
                                v-model:value.trim="form.source"
                                placeholder="Please insert Source"
                                clearable
                            />
                            <n-input
                                v-else
                                v-model:value.trim="form.source"
                                placeholder="Please insert Source"
                                clearable
                                :disabled="disableSourceField"
                                :loading="loadingSource"
                                @update:value="resetIndexAvailable()"
                            />
                        </n-form-item>
                    </div>

                    <n-alert v-if="isSourceNotAllowed" title="Source already exists" type="warning" class="mb-5">
                        A configuration for
                        <strong>"{{ form.source }}"</strong>
                        already exists. Please select a different
                        <strong>Index name</strong>
                        to proceed.
                    </n-alert>

                    <n-alert
                        v-if="arbitrarySourceField"
                        title="Proceed with caution, incorrect settings can disrupt system operation"
                        type="warning"
                        class="mb-5"
                    ></n-alert>

                    <n-form-item label="Field names" path="field_names">
                        <n-select
                            v-model:value="form.field_names"
                            :options="availableMappingsOptions"
                            placeholder="Select..."
                            clearable
                            filterable
                            multiple
                            :tag="arbitrarySourceField"
                            to="body"
                            :disabled="!isFieldEnabled"
                            :loading="loadingAvailableMappings"
                        >
                            <template v-if="arbitrarySourceField" #empty>Press Enter to add the typed value</template>
                        </n-select>
                    </n-form-item>
                    <n-form-item label="IOC Field names" path="ioc_field_names">
                        <n-select
                            v-model:value="form.ioc_field_names"
                            :options="availableMappingsOptions"
                            placeholder="Select..."
                            clearable
                            filterable
                            multiple
                            :tag="arbitrarySourceField"
                            to="body"
                            :disabled="!isFieldEnabled"
                            :loading="loadingAvailableMappings"
                        >
                            <template v-if="arbitrarySourceField" #empty>Press Enter to add the typed value</template>
                        </n-select>
                    </n-form-item>
                    <n-form-item path="asset_name_array" :show-require-mark="false">
                        <template #label>
                            <div class="flex flex-col gap-1">
                                <span>
                                    Asset name fields
                                    <span class="n-form-item-label__asterisk">*</span>
                                </span>
                                <n-text depth="3" style="font-size: 11px; font-weight: 400">
                                    Add multiple fields. First field has priority (checked first).
                                </n-text>
                            </div>
                        </template>
                        <n-dynamic-tags
                            v-model:value="form.asset_name_array"
                            :max="10"
                            :disabled="!isFieldEnabled"
                            :render-tag="renderAssetTag"
                        >
                            <template #input="{ submit, deactivate }">
                                <n-auto-complete
                                    v-model:value="assetNameInput"
                                    :options="filteredAssetNameOptions"
                                    :disabled="!isFieldEnabled"
                                    placeholder="Type or select field name"
                                    @select="handleAssetSelect($event, submit)"
                                    @blur="deactivate"
                                    @keyup.enter="handleAssetEnter(submit)"
                                />
                            </template>
                            <template #trigger="{ activate, disabled }">
                                <n-button
                                    size="small"
                                    type="primary"
                                    dashed
                                    :disabled="disabled || !isFieldEnabled"
                                    @click="activate()"
                                >
                                    <template #icon>
                                        <Icon :name="AddIcon" />
                                    </template>
                                    Add Field
                                </n-button>
                            </template>
                        </n-dynamic-tags>
                    </n-form-item>
                    <n-form-item label="Timefield name" path="timefield_name">
                        <n-select
                            v-model:value="form.timefield_name"
                            :options="availableMappingsOptions"
                            placeholder="Select..."
                            clearable
                            filterable
                            :tag="arbitrarySourceField"
                            to="body"
                            :disabled="!isFieldEnabled"
                            :loading="loadingAvailableMappings"
                        >
                            <template v-if="arbitrarySourceField" #empty>Press Enter to add the typed value</template>
                        </n-select>
                    </n-form-item>
                    <n-form-item label="Alert title name" path="alert_title_name">
                        <n-select
                            v-model:value="form.alert_title_name"
                            :options="availableMappingsOptions"
                            placeholder="Select..."
                            clearable
                            filterable
                            :tag="arbitrarySourceField"
                            to="body"
                            :disabled="!isFieldEnabled"
                            :loading="loadingAvailableMappings"
                        >
                            <template v-if="arbitrarySourceField" #empty>Press Enter to add the typed value</template>
                        </n-select>
                    </n-form-item>
                </div>
                <div class="flex justify-between gap-3">
                    <div>
                        <slot name="additionalActions"></slot>
                    </div>
                    <div class="flex items-center gap-3">
                        <n-button :disabled="loading" @click="reset()">Reset</n-button>
                        <n-button
                            type="primary"
                            :disabled="!isValid"
                            :loading="submitting"
                            @click="validate(() => submit())"
                        >
                            Submit
                        </n-button>
                    </div>
                </div>
            </div>
        </n-form>
    </n-spin>
</template>

<script setup lang="ts">
import type { FormInst, FormItemRule, FormRules, FormValidationError, MessageReactive } from "naive-ui"
import type { SourceConfiguration, SourceConfigurationModel, SourceName } from "@/types/incidentManagement/sources.d"
import _intersection from "lodash/intersection"
import { NAlert, NButton, NForm, NFormItem, NInput, NSelect, NSpin, NDynamicTags, NAutoComplete, NTag, NText, useMessage } from "naive-ui"
import { computed, h, onBeforeMount, onMounted, ref, toRefs, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"

const AddIcon = "carbon:add"

const props = defineProps<{
    sourceConfigurationModel?: SourceConfigurationModel
    showSourceField?: boolean
    arbitrarySourceField?: boolean
    disableSourceField?: boolean
    showIndexNameField?: boolean
    disableIndexNameField?: boolean
    applyFieldsSanitize?: boolean
    disabledSources?: SourceName[]
}>()

const emit = defineEmits<{
    (e: "submitted", value: SourceConfiguration): void
    (
        e: "mounted",
        value: {
            reset: () => void
            toggleSubmittingFlag: () => boolean
        }
    ): void
}>()

const {
    sourceConfigurationModel,
    showSourceField,
    arbitrarySourceField,
    disableSourceField,
    showIndexNameField,
    disableIndexNameField,
    applyFieldsSanitize,
    disabledSources
} = toRefs(props)

const submitting = ref(false)
const loadingSource = ref(false)
const loadingIndexNames = ref(false)
const loadingAvailableMappings = ref(false)
const loadingSocfortressRecommendsWazuh = ref(false)
const socfortressRecommendsWazuh = ref<SourceConfiguration | null>(null)
const loading = computed(() => loadingAvailableMappings.value || loadingIndexNames.value || loadingSource.value)
const message = useMessage()
const form = ref<SourceConfigurationModel>(getSourceConfigurationForm())
const formRef = ref<FormInst | null>(null)
const availableMappingsOptions = ref<{ label: string; value: string }[]>([])
const indexNamesOptions = ref<{ label: string; value: string }[]>([])
const assetNameInput = ref("")

const rules: FormRules = {
    source: {
        required: true,
        message: "Please input the Source",
        trigger: ["input", "blur"]
    },
    field_names: {
        required: true,
        validator: validateAtLeastOne,
        trigger: ["input", "blur"]
    },
    asset_name_array: {
        required: true,
        validator: validateAtLeastOneAsset,
        trigger: ["input", "blur", "change"]
    },
    timefield_name: {
        required: true,
        message: "Please input the timefield name",
        trigger: ["input", "blur"]
    },
    alert_title_name: {
        required: true,
        message: "Please input the alert title name",
        trigger: ["input", "blur"]
    }
}

let validationMessage: MessageReactive | null = null

const isSourceNotAllowed = computed(
    () => form.value.source && disabledSources.value?.length && disabledSources.value.includes(form.value.source)
)
const isFieldEnabled = computed(
    () => (!!form.value.index_name && !isSourceNotAllowed.value) || arbitrarySourceField.value
)

const isValid = computed(() => {
    if (
        !form.value.field_names.length ||
        !form.value.asset_name_array?.length ||
        !form.value.timefield_name ||
        !form.value.alert_title_name ||
        !form.value.source ||
        isSourceNotAllowed.value
    ) {
        return false
    }

    return true
})

const isSocfortressRecommendsAvailable = computed(() => form.value.source?.toLowerCase() === "wazuh")

const filteredAssetNameOptions = computed(() => {
    return availableMappingsOptions.value.filter(
        option => !form.value.asset_name_array?.includes(option.value)
    )
})

watch(sourceConfigurationModel, () => {
    reset()
    init()
})

watch(
    () => form.value.index_name,
    val => {
        if (val) {
            getAvailableMappings(val)
            getSourceByIndex(val)
        } else {
            availableMappingsOptions.value = []
        }
    }
)

watch(
    () => form.value.asset_name_array,
    (newVal) => {
        if (newVal && newVal.length > 0) {
            form.value.asset_name = newVal.join(", ")
        } else {
            form.value.asset_name = null
        }
    },
    { deep: true }
)

function renderAssetTag(tag: string, index: number) {
    return h(
        NTag,
        {
            type: index === 0 ? "primary" : "default",
            closable: true,
            onClose: () => {
                form.value.asset_name_array?.splice(index, 1)
            }
        },
        {
            default: () => tag,
            icon: () => (index === 0 ? h(Icon, { name: "carbon:star-filled", size: 14 }) : null)
        }
    )
}

function handleAssetSelect(value: string, submit: (value: string) => void) {
    if (value && !form.value.asset_name_array?.includes(value)) {
        submit(value)
        assetNameInput.value = ""
    }
}

function handleAssetEnter(submit: (value: string) => void) {
    const value = assetNameInput.value.trim()
    if (value && !form.value.asset_name_array?.includes(value)) {
        submit(value)
        assetNameInput.value = ""
    }
}

function resetIndexAvailable() {
    form.value.index_name = null
    if (form.value.source) {
        getAvailableIndices(form.value.source)
    }
}

function validateAtLeastOne(_rule: FormItemRule, value: string[]) {
    if (!value || !value.length) {
        return new Error("Please select at least one option")
    }

    return true
}

function validateAtLeastOneAsset(_rule: FormItemRule, value: string[]) {
    if (!value || !value.length) {
        return new Error("Please add at least one asset name field")
    }
    return true
}

function validate(cb?: () => void) {
    if (!formRef.value) return

    formRef.value.validate((errors?: Array<FormValidationError>) => {
        if (!errors) {
            validationMessage?.destroy()
            validationMessage = null
            if (cb) cb()
        } else {
            if (!validationMessage) {
                validationMessage = message.warning("You must fill in the required fields correctly.")
            }
            return false
        }
    })
}

function getSourceConfigurationForm(): SourceConfigurationModel {
    const assetName = sourceConfigurationModel.value?.asset_name
    const assetNameArray = assetName
        ? assetName.split(",").map(s => s.trim()).filter(Boolean)
        : []

    return {
        field_names: sourceConfigurationModel.value?.field_names || [],
        ioc_field_names: sourceConfigurationModel.value?.ioc_field_names || [],
        asset_name: sourceConfigurationModel.value?.asset_name || null,
        asset_name_array: assetNameArray,
        timefield_name: sourceConfigurationModel.value?.timefield_name || null,
        alert_title_name: sourceConfigurationModel.value?.alert_title_name || null,
        source: sourceConfigurationModel.value?.source || "",
        index_name: sourceConfigurationModel.value?.index_name || null
    }
}

function reset() {
    if (!loading.value) {
        resetForm()
        formRef.value?.restoreValidation()
    }
}

function resetForm() {
    form.value = getSourceConfigurationForm()
}

function sanitizeFields() {
    const availableMappings = availableMappingsOptions.value.map(o => o.value)

    form.value.field_names = _intersection(availableMappings, form.value.field_names)
    form.value.ioc_field_names = _intersection(availableMappings, form.value.ioc_field_names)

    if (form.value.asset_name_array?.length) {
        form.value.asset_name_array = form.value.asset_name_array.filter(name =>
            availableMappings.includes(name) || arbitrarySourceField.value
        )
    }

    if (form.value.timefield_name && !availableMappings.includes(form.value.timefield_name)) {
        form.value.timefield_name = null
    }
    if (form.value.alert_title_name && !availableMappings.includes(form.value.alert_title_name)) {
        form.value.alert_title_name = null
    }
}

function submit() {
    const payload: SourceConfiguration = {
        field_names: form.value?.field_names || [],
        ioc_field_names: form.value?.ioc_field_names || [],
        asset_name: form.value?.asset_name || "",
        timefield_name: form.value?.timefield_name || "",
        alert_title_name: form.value?.alert_title_name || "",
        source: form.value?.source || ""
    }
    emit("submitted", payload)
}

function toggleSubmittingFlag(status?: boolean) {
    if (status !== undefined) {
        submitting.value = status
    } else {
        submitting.value = !submitting.value
    }

    return submitting.value
}

function resetSource() {
    form.value.source = ""
}

function setSocfortressRecommendsWazuh() {
    form.value.field_names = socfortressRecommendsWazuh.value?.field_names || []
    form.value.ioc_field_names = socfortressRecommendsWazuh.value?.ioc_field_names || []

    const assetName = socfortressRecommendsWazuh.value?.asset_name
    form.value.asset_name_array = assetName
        ? assetName.split(",").map(s => s.trim()).filter(Boolean)
        : []

    form.value.timefield_name = socfortressRecommendsWazuh.value?.timefield_name || null
    form.value.alert_title_name = socfortressRecommendsWazuh.value?.alert_title_name || null
    form.value.source = socfortressRecommendsWazuh.value?.source || ""
}

function getSocfortressRecommendsWazuh() {
    if (socfortressRecommendsWazuh.value) {
        setSocfortressRecommendsWazuh()
        return
    }

    loadingSocfortressRecommendsWazuh.value = true

    Api.incidentManagement.sources
        .getSocfortressRecommendsWazuh()
        .then(res => {
            if (res.data.success) {
                socfortressRecommendsWazuh.value = {
                    field_names: res.data.field_names,
                    ioc_field_names: res.data.ioc_field_names,
                    asset_name: res.data.asset_name,
                    timefield_name: res.data.timefield_name,
                    alert_title_name: res.data.alert_title_name,
                    source: res.data.source
                }

                setSocfortressRecommendsWazuh()
            } else {
                message.warning(res.data?.message || "An error occurred. Please try again later.")
            }
        })
        .catch(err => {
            message.error(err.response?.data?.message || "An error occurred. Please try again later.")
        })
        .finally(() => {
            loadingSocfortressRecommendsWazuh.value = false
        })
}

function getAvailableMappings(indexName: string) {
    loadingAvailableMappings.value = true

    Api.incidentManagement.sources
        .getAvailableMappings(indexName)
        .then(res => {
            if (res.data.success) {
                availableMappingsOptions.value = (res.data?.available_mappings || []).map(o => ({
                    label: o,
                    value: o
                }))
                if (applyFieldsSanitize.value) {
                    sanitizeFields()
                }
            } else {
                message.warning(res.data?.message || "An error occurred. Please try again later.")
            }
        })
        .catch(err => {
            message.error(err.response?.data?.message || "An error occurred. Please try again later.")
        })
        .finally(() => {
            loadingAvailableMappings.value = false
        })
}

function getAvailableIndices(source: SourceName) {
    loadingIndexNames.value = true

    Api.incidentManagement.sources
        .getAvailableIndices(source)
        .then(res => {
            if (res.data.success) {
                indexNamesOptions.value = (res.data?.indices || []).map(o => ({
                    label: o,
                    value: o
                }))
            } else {
                resetSource()
                message.warning(res.data?.message || "An error occurred. Please try again later.")
            }
        })
        .catch(err => {
            resetSource()
            message.error(err.response?.data?.message || "An error occurred. Please try again later.")
        })
        .finally(() => {
            loadingIndexNames.value = false
        })
}

function getSourceByIndex(indexName: string) {
    loadingSource.value = true

    Api.incidentManagement.sources
        .getSourceByIndex(indexName)
        .then(res => {
            if (res.data.success) {
                form.value.source = res.data.source
            } else {
                resetSource()
                message.warning(res.data?.message || "An error occurred. Please try again later.")
            }
        })
        .catch(err => {
            resetSource()
            message.error(err.response?.data?.message || "An error occurred. Please try again later.")
        })
        .finally(() => {
            loadingSource.value = false
        })
}

function init() {
    if (sourceConfigurationModel.value?.index_name) {
        getAvailableMappings(sourceConfigurationModel.value.index_name)

        if (!sourceConfigurationModel.value?.source) {
            getSourceByIndex(sourceConfigurationModel.value.index_name)
        }
    }
    if (sourceConfigurationModel.value?.source) {
        getAvailableIndices(sourceConfigurationModel.value.source)
    }
}

onBeforeMount(() => {
    init()
})

onMounted(() => {
    emit("mounted", {
        reset,
        toggleSubmittingFlag
    })
})
</script>

<style lang="scss" scoped>
.source-field {
    :deep() {
        .n-form-item-label__text {
            width: 100%;
        }
    }
}

:deep(.n-dynamic-tags) {
    width: 100%;
}
</style>
