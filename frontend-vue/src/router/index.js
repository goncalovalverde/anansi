import { createRouter, createWebHashHistory } from 'vue-router'
import DashboardView from '@/views/DashboardView.vue'
import ConfigView from '@/views/ConfigView.vue'

export default createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', component: DashboardView },
    { path: '/config', component: ConfigView },
  ],
})
