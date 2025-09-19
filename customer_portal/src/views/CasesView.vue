<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <header class="bg-white shadow">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between h-16">
          <div class="flex items-center">
            <router-link
              to="/"
              class="text-indigo-600 hover:text-indigo-500 mr-4"
            >
              ← Back to Dashboard
            </router-link>
            <h1 class="text-xl font-semibold">Security Cases</h1>
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
            Loading cases...
          </div>
        </div>

        <!-- Error State -->
        <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-md p-4">
          <div class="flex">
            <div class="ml-3">
              <h3 class="text-sm font-medium text-red-800">
                Error loading cases
              </h3>
              <div class="mt-2 text-sm text-red-700">
                {{ error }}
              </div>
            </div>
          </div>
        </div>

        <!-- Cases List -->
        <div v-else>
          <!-- Stats Cards -->
          <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div class="bg-white overflow-hidden shadow rounded-lg">
              <div class="p-5">
                <div class="flex items-center">
                  <div class="w-8 h-8 bg-red-500 rounded-md flex items-center justify-center">
                    <span class="text-white text-sm font-medium">O</span>
                  </div>
                  <div class="ml-3">
                    <p class="text-sm font-medium text-gray-500">Open</p>
                    <p class="text-lg font-semibold text-gray-900">{{ getCaseCount('open') }}</p>
                  </div>
                </div>
              </div>
            </div>
            <div class="bg-white overflow-hidden shadow rounded-lg">
              <div class="p-5">
                <div class="flex items-center">
                  <div class="w-8 h-8 bg-yellow-500 rounded-md flex items-center justify-center">
                    <span class="text-white text-sm font-medium">P</span>
                  </div>
                  <div class="ml-3">
                    <p class="text-sm font-medium text-gray-500">In Progress</p>
                    <p class="text-lg font-semibold text-gray-900">{{ getCaseCount('in_progress') }}</p>
                  </div>
                </div>
              </div>
            </div>
            <div class="bg-white overflow-hidden shadow rounded-lg">
              <div class="p-5">
                <div class="flex items-center">
                  <div class="w-8 h-8 bg-green-500 rounded-md flex items-center justify-center">
                    <span class="text-white text-sm font-medium">C</span>
                  </div>
                  <div class="ml-3">
                    <p class="text-sm font-medium text-gray-500">Closed</p>
                    <p class="text-lg font-semibold text-gray-900">{{ getCaseCount('closed') }}</p>
                  </div>
                </div>
              </div>
            </div>
            <div class="bg-white overflow-hidden shadow rounded-lg">
              <div class="p-5">
                <div class="flex items-center">
                  <div class="w-8 h-8 bg-gray-500 rounded-md flex items-center justify-center">
                    <span class="text-white text-sm font-medium">T</span>
                  </div>
                  <div class="ml-3">
                    <p class="text-sm font-medium text-gray-500">Total</p>
                    <p class="text-lg font-semibold text-gray-900">{{ cases.length }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Cases Table -->
          <div class="bg-white shadow overflow-hidden sm:rounded-md">
            <div class="px-4 py-5 sm:px-6">
              <h3 class="text-lg leading-6 font-medium text-gray-900">
                Security Cases
              </h3>
              <p class="mt-1 max-w-2xl text-sm text-gray-500">
                Security incident cases for your organization
              </p>
            </div>

            <div v-if="cases.length === 0" class="px-4 py-5 sm:px-6 text-center text-gray-500">
              No cases found
            </div>

            <ul v-else class="divide-y divide-gray-200">
              <li v-for="case_ in cases" :key="case_.id" class="px-4 py-4 sm:px-6 hover:bg-gray-50 cursor-pointer" @click="viewCaseDetails(case_.id)">
                <div class="flex items-center justify-between">
                  <div class="flex items-center">
                    <div
                      class="w-3 h-3 rounded-full mr-3"
                      :class="{
                        'bg-red-500': case_.case_status === 'open',
                        'bg-yellow-500': case_.case_status === 'in_progress',
                        'bg-green-500': case_.case_status === 'closed',
                        'bg-gray-500': !case_.case_status
                      }"
                    ></div>
                    <div>
                      <p class="text-sm font-medium text-gray-900 hover:text-indigo-600">
                        {{ case_.case_name || 'Unnamed Case' }}
                      </p>
                      <p class="text-sm text-gray-500">
                        {{ case_.case_description || 'No description available' }}
                      </p>
                      <p class="text-xs text-gray-400 mt-1">
                        Created: {{ formatDate(case_.case_creation_time) }}
                        <span v-if="case_.assigned_to"> • Assigned to: {{ case_.assigned_to }}</span>
                        <span v-if="case_.comments && case_.comments.length > 0"> • {{ case_.comments.length }} {{ case_.comments.length === 1 ? 'comment' : 'comments' }}</span>
                      </p>
                    </div>
                  </div>
                  <div class="flex items-center space-x-2">
                    <span
                      class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                      :class="{
                        'bg-red-100 text-red-800': case_.case_status === 'open',
                        'bg-yellow-100 text-yellow-800': case_.case_status === 'in_progress',
                        'bg-green-100 text-green-800': case_.case_status === 'closed',
                        'bg-gray-100 text-gray-800': !case_.case_status
                      }"
                    >
                      {{ case_.case_status || 'Unknown' }}
                    </span>
                    <span
                      v-if="case_.escalation_level"
                      class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                      :class="{
                        'bg-red-100 text-red-800': case_.escalation_level === 'high',
                        'bg-yellow-100 text-yellow-800': case_.escalation_level === 'medium',
                        'bg-blue-100 text-blue-800': case_.escalation_level === 'low'
                      }"
                    >
                      {{ case_.escalation_level }}
                    </span>
                  </div>
                </div>
              </li>
            </ul>
          </div>

          <!-- Pagination (if needed) -->
          <div v-if="cases.length > 0" class="mt-6 flex justify-center">
            <button
              @click="refreshCases"
              class="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-md text-sm font-medium"
            >
              Refresh
            </button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { httpClient } from '@/utils/httpClient'

interface Case {
  id: number
  case_name: string
  case_description: string
  case_status: string
  case_creation_time: string
  assigned_to?: string
  escalation_level?: string
  customer_code?: string
  comments?: Array<{
    id: number
    comment: string
    user_name?: string
    created_at: string
  }>
}

const router = useRouter()
const authStore = useAuthStore()

const cases = ref<Case[]>([])
const loading = ref(false)
const error = ref('')

const user = computed(() => authStore.user)

const getCaseCount = (status: string) => {
  return cases.value.filter(case_ => case_.case_status === status).length
}

const formatDate = (dateString: string) => {
  if (!dateString) return 'Unknown'
  try {
    return new Date(dateString).toLocaleDateString()
  } catch {
    return 'Invalid date'
  }
}

const fetchCases = async () => {
  loading.value = true
  error.value = ''

  try {
    const response = await httpClient.get('/cases/')
    cases.value = response.data || []
  } catch (err: any) {
    error.value = err.response?.data?.detail || 'Failed to fetch cases'
    console.error('Failed to fetch cases:', err)
  } finally {
    loading.value = false
  }
}

const refreshCases = () => {
  fetchCases()
}

const viewCaseDetails = (caseId: number) => {
  router.push(`/cases/${caseId}`)
}

const logout = () => {
  authStore.logout()
  router.push('/login')
}

onMounted(() => {
  fetchCases()
})
</script>
