<template>
  <div :class="['app-root', { 'light-mode': configStore.theme === 'light' }]">
    <AppHeader />
    <router-view />
    <div id="notification" :class="['notification', notif.type, notif.show ? 'show' : '']" role="alert" aria-live="assertive">
      {{ notif.message }}
    </div>
  </div>
</template>

<script setup>
import { reactive, provide } from 'vue'
import AppHeader from '@/components/AppHeader.vue'
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
