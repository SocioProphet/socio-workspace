import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import './styles.css'
import Dashboard from './pages/Dashboard.vue'
import Builder from './pages/Builder.vue'
import Entities from './pages/Entities.vue'
import Layouts from './pages/Layouts.vue'
import Terminal from './pages/Terminal.vue'
import Settings from './pages/Settings.vue'
import SpecManager from './pages/SpecManager.vue'
import { spaceMeta } from './services/api'
import { TwinBridge, GenesisBridge } from './services/bridge'

const routes=[
  { path:'/', redirect:'/dashboard' },
  { path:'/dashboard', component:Dashboard },
  { path:'/builder', component:Builder },
  { path:'/entities', component:Entities },
  { path:'/layouts', component:Layouts },
  { path:'/specs', component:SpecManager },
  { path:'/terminal', component:Terminal },
  { path:'/settings', component:Settings },
]
const { routerBase } = spaceMeta()
const router=createRouter({ history:createWebHistory(routerBase), routes })
const app=createApp(App); app.use(router).mount('#app')
new TwinBridge().start(); new GenesisBridge().start()