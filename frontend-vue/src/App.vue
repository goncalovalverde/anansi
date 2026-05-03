<template>
  <div :class="['app-root', { 'dark-mode': configStore.theme === 'dark' }]">
    <AppSidebar />
    <AppTopBar />
    <div class="app-content">
      <router-view />
    </div>
    <div id="notification" :class="['notification', notif.type, notif.show ? 'show' : '']" role="alert" aria-live="assertive">
      {{ notif.message }}
    </div>
  </div>
</template>

<script setup>
import { reactive, provide } from 'vue'
import AppSidebar from '@/components/AppSidebar.vue'
import AppTopBar from '@/components/AppTopBar.vue'
import { useConfigStore } from '@/stores/config.js'

const configStore = useConfigStore()

// Global notification — provided to all children via inject
const notif = reactive({ message: '', type: 'info', show: false })
let notifTimer = null
function showNotification(message, type = 'info') {
  clearTimeout(notifTimer)
  notif.message = message
  notif.type = type
  notif.show = true
  notifTimer = setTimeout(() => { notif.show = false }, 4000)
}
provide('showNotification', showNotification)
</script>

<style scoped>
.app-content {
  margin-left: 56px;
  margin-top: 44px;
  min-height: calc(100vh - 44px);
}
</style>
