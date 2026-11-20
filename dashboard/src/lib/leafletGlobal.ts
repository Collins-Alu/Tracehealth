// leaflet.heat is an old plugin that expects a global `L`. Import this module
// BEFORE 'leaflet.heat' so the global exists when the plugin loads.
import L from 'leaflet';

(window as unknown as { L: typeof L }).L = L;
export default L;
