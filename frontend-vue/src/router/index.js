import { createRouter, createWebHashHistory } from 'vue-router'

export default createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', component: () => import('@/views/DashboardView.vue') },
    { path: '/config', component: () => import('@/views/ConfigView.vue') },
    { path: '/flow', component: () => import('@/views/FlowView.vue') },
    { path: '/trends', component: () => import('@/views/TrendsView.vue') },
  ],
})
