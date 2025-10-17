<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <header class="bg-white shadow">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between h-16">
          <div class="flex items-center">
            <router-link
              to="/cases"
              class="text-indigo-600 hover:text-indigo-500 mr-4"
            >
              ← Back to Cases
            </router-link>
            <h1 class="text-xl font-semibold">Case Details</h1>
          </div>
          <div class="flex items-center space-x-4">
            <span class="text-sm text-gray-700">{{ user?.username }}</span>
            <button
              @click="logout"
              class="bg-red-600 hover:bg-red-700 text-white px-3 py-2 rounded-md text-sm font-medium"
            >
              Logout
            </button>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <div class="px-4 py-6 sm:px-0">
        <!-- Loading State -->
        <div v-if="loading" class="text-center py-8">
          <div class="inline-flex items-center px-4 py-2 font-semibold leading-6 text-sm shadow rounded-md text-white bg-indigo-500">
            Loading case details...
          </div>
        </div>

        <!-- Error State -->
        <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-md p-4">
          <div class="flex">
            <div class="ml-3">
              <h3 class="text-sm font-medium text-red-800">
                Error loading case
              </h3>
              <div class="mt-2 text-sm text-red-700">
                {{ error }}
              </div>
            </div>
          </div>
        </div>

        <!-- Case Details -->
        <div v-else-if="caseData" class="space-y-6">
          <!-- Case Header -->
          <div class="bg-white shadow overflow-hidden sm:rounded-lg">
            <div class="px-4 py-5 sm:px-6">
              <div class="flex items-center justify-between">
                <div>
                  <h3 class="text-lg leading-6 font-medium text-gray-900">
                    {{ caseData.case_name || 'Unnamed Case' }}
                  </h3>
                  <p class="mt-1 max-w-2xl text-sm text-gray-500">
                    Case #{{ caseData.id }}
                  </p>
                </div>
                <div class="flex items-center space-x-2">
                  <span
                    class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                    :class="{
                      'bg-red-100 text-red-800': caseData.case_status === 'open',
                      'bg-yellow-100 text-yellow-800': caseData.case_status === 'in_progress',
                      'bg-green-100 text-green-800': caseData.case_status === 'closed',
                      'bg-gray-100 text-gray-800': !caseData.case_status
                    }"
                  >
                    {{ caseData.case_status || 'Unknown' }}
                  </span>
                </div>
              </div>
            </div>
            <div class="border-t border-gray-200 px-4 py-5 sm:p-0">
              <dl class="sm:divide-y sm:divide-gray-200">
                <div class="py-4 sm:py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                  <dt class="text-sm font-medium text-gray-500">Description</dt>
                  <dd class="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                    {{ caseData.case_description || 'No description available' }}
                  </dd>
                </div>
                <div class="py-4 sm:py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                  <dt class="text-sm font-medium text-gray-500">Created</dt>
                  <dd class="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                    {{ formatDate(caseData.case_creation_time) }}
                  </dd>
                </div>
                <div class="py-4 sm:py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                  <dt class="text-sm font-medium text-gray-500">Assigned to</dt>
                  <dd class="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                    {{ caseData.assigned_to || 'Unassigned' }}
                  </dd>
                </div>
                <div v-if="caseData.customer_code" class="py-4 sm:py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                  <dt class="text-sm font-medium text-gray-500">Customer</dt>
                  <dd class="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                    {{ caseData.customer_code }}
                  </dd>
                </div>
              </dl>
            </div>
          </div>

          <!-- Alerts Section -->
          <div v-if="caseData.alerts && caseData.alerts.length > 0" class="bg-white shadow overflow-hidden sm:rounded-lg">
            <div class="px-4 py-5 sm:px-6">
              <h3 class="text-lg leading-6 font-medium text-gray-900">
                Related Alerts ({{ caseData.alerts.length }})
              </h3>
            </div>
            <div class="border-t border-gray-200">
              <ul class="divide-y divide-gray-200">
                <li v-for="alert in caseData.alerts" :key="alert.id" class="px-4 py-4 sm:px-6">
                  <div class="flex items-center justify-between">
                    <div>
                      <p class="text-sm font-medium text-gray-900">
                        {{ alert.alert_name || 'Unnamed Alert' }}
                      </p>
                      <p class="text-sm text-gray-500">
                        Alert #{{ alert.id }}
                      </p>
                    </div>
                    <span
                      class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                      :class="{
                        'bg-red-100 text-red-800': alert.status === 'open',
                        'bg-yellow-100 text-yellow-800': alert.status === 'in_progress',
                        'bg-green-100 text-green-800': alert.status === 'closed',
                        'bg-gray-100 text-gray-800': !alert.status
                      }"
                    >
                      {{ alert.status || 'Unknown' }}
                    </span>
                  </div>
                </li>
              </ul>
            </div>
          </div>

          <!-- Comments Section -->
          <div class="bg-white shadow overflow-hidden sm:rounded-lg">
            <div class="px-4 py-5 sm:px-6">
              <CaseCommentsList
                :case-id="caseData.id"
                :comments="comments"
                @comments-updated="handleCommentsUpdated"
              />
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { CasesAPI, type Case, type CaseComment } from '@/api/cases'
import CaseCommentsList from '@/components/CaseCommentsList.vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const caseData = ref<Case | null>(null)
const comments = ref<CaseComment[]>([])
const loading = ref(false)
const error = ref('')

const user = computed(() => authStore.user)

const formatDate = (dateString: string) => {
  if (!dateString) return 'Unknown'
  try {
    return new Date(dateString).toLocaleString()
  } catch {
    return 'Invalid date'
  }
}

const fetchCaseDetails = async () => {
  const caseId = Number(route.params.id)
  if (!caseId) {
    error.value = 'Invalid case ID'
    return
  }

  loading.value = true
  error.value = ''

  try {
    const response = await CasesAPI.getCase(caseId)
    if (response.success && response.cases.length > 0) {
      caseData.value = response.cases[0]
      comments.value = response.cases[0].comments || []
    } else {
      error.value = 'Case not found'
    }
  } catch (err: any) {
    error.value = err.response?.data?.detail || 'Failed to fetch case details'
    console.error('Failed to fetch case details:', err)
  } finally {
    loading.value = false
  }
}

const handleCommentsUpdated = (updatedComments: CaseComment[]) => {
  comments.value = updatedComments
  // Also update the case data if it has comments
  if (caseData.value) {
    caseData.value.comments = updatedComments
  }
}

const logout = () => {
  authStore.logout()
  router.push('/login')
}

onMounted(() => {
  fetchCaseDetails()
})
</script>
