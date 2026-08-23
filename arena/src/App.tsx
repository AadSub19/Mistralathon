import Arena from './pages/Arena'
import Join from './pages/Join'

/** Tiny router: "/" = host arena, "/join" = mobile participant page. */
export default function App() {
  const path = window.location.pathname.replace(/\/+$/, '')
  if (path === '/join') return <Join />
  return <Arena />
}
