<template>
  <div class="input-details-box" v-loading="loading" :class="{ active: currentInput }">
      <div class="box-header">
          <div class="title">
              <span v-if="currentInput"> Below the details for input </span>
              <span v-else> Select an input to see the details </span>
          </div>
          <div class="select-box" v-if="inputs && inputs.length">
              <el-select v-model="currentInput" placeholder="Inputs list" clearable value-key="input" filterable>
                  <el-option v-for="input in inputs" :key="input.id" :label="input.title" :value="input"></el-option>
              </el-select>
          </div>
      </div>
      <div class="details-box" v-if="currentInput">
          <div class="info">
              <InputCard :input="currentInput" showActions @delete="clearCurrentInput()" />
          </div>
          <!-- <div class="shards">
              <el-scrollbar>
                  <table class="styled">
                      <thead>
                          <tr>
                              <th>Title</th>
                              <th>Port</th>
                          </tr>
                      </thead>
                      <tbody>
                          <tr v-for="shard of filteredShards" :key="shard.id">
                              <td>{{ shard.title || "-" }}</td>
                              <td>{{ shard.port || "-" }}</td>
                              <td>
                                  <span class="shard-state" :class="shard.state">
                                      {{ shard.state || "-" }}
                                  </span>
                              </td>
                          </tr>
                      </tbody>
                  </table>
              </el-scrollbar>
          </div> -->
      </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeMount, ref, toRefs } from "vue"
import { Inputs } from "@/types/graylog.d"
import { ElMessage } from "element-plus"
import InputCard from "@/components/inputs/InputCard.vue"
import Api from "@/api"
import { nanoid } from "nanoid"

type InputModel = Inputs | null | ""

const emit = defineEmits<{
  (e: "update:modelValue", value: InputModel): void
}>()

const props = defineProps<{
  inputs: Inputs[] | null
  modelValue: InputModel
}>()
const { inputs, modelValue } = toRefs(props)

// const shards = ref<InputShard[]>([])
// const loadingShards = ref(false)
const loading = computed(() => !inputs?.value || inputs.value === null)

// const filteredShards = computed(() =>
//   shards.value.filter((shard: InputShard) => {
//       if (!currentInput.value || typeof currentInput.value === "string") return false
//       return shard.input === currentInput.value?.input
//   })
// )

const currentInput = computed<InputModel>({
  get() {
      return modelValue.value
  },
  set(value) {
      emit("update:modelValue", value)
  }
})

function clearCurrentInput() {
  currentInput.value = null
}

// function getShards() {
//   loadingShards.value = true
//   Api.indices
//       .getShards()
//       .then(res => {
//           if (res.data.success) {
//               shards.value = (res.data?.shards || []).map(obj => {
//                   obj.id = nanoid()
//                   return obj
//               })
//           } else {
//               ElMessage({
//                   message: res.data?.message || "An error occurred. Please try again later.",
//                   type: "error"
//               })
//           }
//       })
//       .catch(err => {
//           if (err.response.status === 401) {
//               ElMessage({
//                   message: err.response?.data?.message || "Wazuh-Indexer returned Unauthorized. Please check your connector credentials.",
//                   type: "error"
//               })
//           } else if (err.response.status === 404) {
//               ElMessage({
//                   message: err.response?.data?.message || "No alerts were found.",
//                   type: "error"
//               })
//           } else {
//               ElMessage({
//                   message: err.response?.data?.message || "An error occurred. Please try again later.",
//                   type: "error"
//               })
//           }
//       })
//       .finally(() => {
//           loadingShards.value = false
//       })
// }

onBeforeMount(() => {
  // getShards()
})
</script>

<style lang="scss" scoped>
@import "@/assets/scss/_variables";
@import "@/assets/scss/card-shadow";

.input-details-box {
  padding: var(--size-5) var(--size-6);
  border: 2px solid transparent;
  @extend .card-base;
  &.active {
      border-color: $text-color-accent;
      @extend .card-shadow--small;
  }

  .box-header {
      display: flex;
      align-items: center;

      .title {
          margin-right: var(--size-4);
      }

      .select-box {
          .el-select {
              min-width: var(--size-fluid-9);
              max-width: 100%;
          }
      }
  }

  .details-box {
      margin-top: var(--size-6);

      .shards {
          margin-top: var(--size-4);
          @extend .card-base;
          @extend .card-shadow--small;

          .shard-state {
              font-weight: bold;
              &.STARTED {
                  color: $text-color-success;
              }
              &.UNASSIGNED {
                  color: $text-color-warning;
              }
          }
      }
  }

  @media (max-width: 1000px) {
      .box-header {
          flex-direction: column;
          align-items: flex-start;
          gap: var(--size-2);
          .select-box {
              width: 100%;
              .el-select {
                  min-width: 100%;
              }
          }
      }
  }
}
</style>
