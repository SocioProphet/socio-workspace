import { createRouter, createWebHashHistory } from 'vue-router'

import HomePage from '../routes/HomePage.vue'
import SearchResultsPage from '../routes/SearchResultsPage.vue'
import EntityProfilePage from '../routes/EntityProfilePage.vue'
import GraphExplorerPage from '../routes/GraphExplorerPage.vue'
import KbHomePage from '../routes/KbHomePage.vue'
import SettingsPage from '../routes/SettingsPage.vue'
import ConnectorsPage from '../routes/admin/ConnectorsPage.vue'
import CurationPage from '../routes/admin/CurationPage.vue'
import TrustRegistryPage from '../routes/admin/TrustRegistryPage.vue'

export default createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', name: 'home', component: HomePage },
    { path: '/search', name: 'search', component: SearchResultsPage },
    { path: '/entity/:type/:id', name: 'entity', component: EntityProfilePage, props: true },
    { path: '/graph/:id', name: 'graph', component: GraphExplorerPage, props: true },
    { path: '/kb', name: 'kb', component: KbHomePage },
    { path: '/settings', name: 'settings', component: SettingsPage },
    { path: '/connectors', name: 'connectors', component: ConnectorsPage },
    { path: '/curation', name: 'curation', component: CurationPage },
    { path: '/admin/trust', name: 'trust', component: TrustRegistryPage },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})
