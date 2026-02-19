import { MbtistatsDashboard } from './dashboard-class.mjs';
import './top-personality.mjs';
import './type-summary.mjs';
import './trend-charts.mjs';
import './trait-pies.mjs';

export function setupCharts(data) {
    const dashboard = new MbtistatsDashboard(data);
    dashboard.setupAll();
}