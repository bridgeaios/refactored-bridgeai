/**
 * 50 Real-World Applications for Bridge AI OS — data for the applications showcase page.
 * Market estimates from industry forecasts (e.g. digital twin ~$154B–$195B by 2030).
 */

export const CATEGORIES = [
  { id: 'infrastructure', title: 'Infrastructure & Smart Cities', range: '1–10' },
  { id: 'healthcare', title: 'Healthcare', range: '11–20' },
  { id: 'business', title: 'Business & Enterprise', range: '21–30' },
  { id: 'industry', title: 'Industry & Manufacturing', range: '31–40' },
  { id: 'consumer', title: 'Consumer & Society', range: '41–50' },
];

export const APPLICATIONS = [
  // 1–10 Infrastructure & Smart Cities
  { id: 1, category: 'infrastructure', title: 'Smart City Digital Twin', value: '$100B+', deploy: ['IoT sensors', 'city twin simulation', 'Bridge API + Redis telemetry'] },
  { id: 2, category: 'infrastructure', title: 'Traffic Optimization AI', value: '$40B', deploy: ['sensors → /api/sensors', 'twin simulation for routing', 'edge compute via Worker'] },
  { id: 3, category: 'infrastructure', title: 'Energy Grid Optimization', value: '$60B', deploy: ['grid digital twins', 'agent optimization'] },
  { id: 4, category: 'infrastructure', title: 'Water Infrastructure Monitoring', value: '$20B', deploy: ['sensor ingestion', 'predictive maintenance twins'] },
  { id: 5, category: 'infrastructure', title: 'Disaster Prediction Systems', value: '$15B', deploy: ['AI twins simulate disasters', 'live sensor feeds'] },
  { id: 6, category: 'infrastructure', title: 'Smart Waste Management', value: '$8B', deploy: ['IoT bins', 'task marketplace for logistics'] },
  { id: 7, category: 'infrastructure', title: 'City Planning Simulator', value: '$25B', deploy: ['urban digital twins', 'AI simulations'] },
  { id: 8, category: 'infrastructure', title: 'Smart Lighting Systems', value: '$10B', deploy: ['sensors + automation agents'] },
  { id: 9, category: 'infrastructure', title: 'Infrastructure Predictive Maintenance', value: '$30B', deploy: ['asset twins', 'AI anomaly detection'] },
  { id: 10, category: 'infrastructure', title: 'Public Safety AI Monitoring', value: '$35B', deploy: ['sensor ingestion', 'twin risk analysis'] },
  // 11–20 Healthcare
  { id: 11, category: 'healthcare', title: 'Patient Digital Twins', value: '$2.2B by 2030', deploy: ['health data ingestion', 'AI diagnosis twin'] },
  { id: 12, category: 'healthcare', title: 'Remote Diagnostics', value: '$15B', deploy: ['sensor devices', 'telemedicine agents'] },
  { id: 13, category: 'healthcare', title: 'Hospital Optimization AI', value: '$25B', deploy: ['hospital digital twin'] },
  { id: 14, category: 'healthcare', title: 'Drug Discovery Simulation', value: '$70B', deploy: ['AI simulation twins'] },
  { id: 15, category: 'healthcare', title: 'Medical Device Monitoring', value: '$12B', deploy: ['IoT ingestion'] },
  { id: 16, category: 'healthcare', title: 'Emergency Response AI', value: '$20B', deploy: ['dispatch optimization'] },
  { id: 17, category: 'healthcare', title: 'Personalized Treatment Planning', value: '$30B', deploy: ['patient twin models'] },
  { id: 18, category: 'healthcare', title: 'Mental Health AI Agents', value: '$10B', deploy: ['speech + agent therapy'] },
  { id: 19, category: 'healthcare', title: 'Medical Imaging AI', value: '$40B', deploy: ['inference agents'] },
  { id: 20, category: 'healthcare', title: 'Healthcare Logistics', value: '$12B', deploy: ['hospital supply twins'] },
  // 21–30 Business & Enterprise
  { id: 21, category: 'business', title: 'Autonomous Customer Support', value: '$80B', deploy: ['AI agents + speech embodiment'] },
  { id: 22, category: 'business', title: 'Autonomous Sales Agents', value: '$50B', deploy: ['AI negotiation bots'] },
  { id: 23, category: 'business', title: 'AI Marketplaces', value: '$100B+', deploy: ['Bridge marketplace module'] },
  { id: 24, category: 'business', title: 'Corporate Digital Twins', value: '$60B', deploy: ['enterprise simulation'] },
  { id: 25, category: 'business', title: 'Supply Chain Optimization', value: '$90B', deploy: ['supply chain twins'] },
  { id: 26, category: 'business', title: 'Autonomous Finance Agents', value: '$35B', deploy: ['AI trading bots'] },
  { id: 27, category: 'business', title: 'AI Knowledge Workers', value: '$150B', deploy: ['LLM runtime + vector DB'] },
  { id: 28, category: 'business', title: 'AI Product Managers', value: '$20B', deploy: ['decision agents'] },
  { id: 29, category: 'business', title: 'Autonomous Market Research', value: '$15B', deploy: ['data scraping agents'] },
  { id: 30, category: 'business', title: 'Smart Contract Governance', value: '$30B', deploy: ['SIWE + blockchain roles'] },
  // 31–40 Industry & Manufacturing
  { id: 31, category: 'industry', title: 'Factory Digital Twins', value: '$80B', deploy: ['machine telemetry'] },
  { id: 32, category: 'industry', title: 'Predictive Maintenance', value: '$50B', deploy: ['sensor ingestion'] },
  { id: 33, category: 'industry', title: 'Robotics Fleet Coordination', value: '$40B', deploy: ['swarm AI agents'] },
  { id: 34, category: 'industry', title: 'Warehouse Optimization', value: '$35B', deploy: ['digital twin logistics'] },
  { id: 35, category: 'industry', title: 'Autonomous Construction Planning', value: '$25B', deploy: ['simulation twins'] },
  { id: 36, category: 'industry', title: 'Mining Operations AI', value: '$30B', deploy: ['remote sensors'] },
  { id: 37, category: 'industry', title: 'Oil & Gas Monitoring', value: '$60B', deploy: ['infrastructure twins'] },
  { id: 38, category: 'industry', title: 'Industrial Safety AI', value: '$20B', deploy: ['anomaly detection'] },
  { id: 39, category: 'industry', title: 'Asset Lifecycle Management', value: '$40B', deploy: ['equipment twins'] },
  { id: 40, category: 'industry', title: 'Manufacturing Simulation', value: '$70B', deploy: ['factory twin simulation'] },
  // 41–50 Consumer & Society
  { id: 41, category: 'consumer', title: 'AI Personal Assistants', value: '$200B', deploy: ['twin agents'] },
  { id: 42, category: 'consumer', title: 'Digital Identity Networks', value: '$30B', deploy: ['SIWE identity layer'] },
  { id: 43, category: 'consumer', title: 'AI Education Tutors', value: '$50B', deploy: ['LLM tutoring agents'] },
  { id: 44, category: 'consumer', title: 'Autonomous Media Generation', value: '$11B', deploy: ['generative models'] },
  { id: 45, category: 'consumer', title: 'Creator AI Tools', value: '$20B', deploy: ['content generation agents'] },
  { id: 46, category: 'consumer', title: 'Gaming AI NPC Ecosystems', value: '$40B', deploy: ['digital twin NPCs'] },
  { id: 47, category: 'consumer', title: 'Smart Home AI Orchestration', value: '$60B', deploy: ['IoT + automation agents'] },
  { id: 48, category: 'consumer', title: 'AI Personal Finance Advisors', value: '$35B', deploy: ['financial agents'] },
  { id: 49, category: 'consumer', title: 'Decentralized Work Platforms', value: '$100B', deploy: ['AI marketplace'] },
  { id: 50, category: 'consumer', title: 'Global AI Agent Economy', value: '$220B+', deploy: ['millions of autonomous agents'] },
];

export const TOP_FIVE = [
  { rank: 1, title: 'AI Marketplace for Agents', note: '$100B+', id: 23 },
  { rank: 2, title: 'Enterprise Digital Twins', note: '$60B', id: 24 },
  { rank: 3, title: 'Autonomous Business Agents', note: 'Customer support, sales, finance', id: 21 },
  { rank: 4, title: 'Smart City Infrastructure Twins', note: '$100B+', id: 1 },
  { rank: 5, title: 'AI Personal Assistants', note: '$200B', id: 41 },
];

export const TAM_DESCRIPTION = 'If a platform orchestrates these markets, the potential addressable economy is **$2T – $10T+** (AI coordination economy), because AI orchestration touches infrastructure, healthcare, finance, manufacturing, and consumer AI.';

export const BRIDGE_WINS_PILLARS = [
  'AI agents',
  'digital twins',
  'marketplace economy',
  'sensor ingestion',
  'edge compute',
  'deterministic orchestration',
];

export const SOURCES = [
  { label: 'GlobalData', url: 'https://www.globaldata.com/media/thematic-research/global-digital-twins-market-will-be-worth-154-billion-in-2030-forecasts-globaldata/', desc: 'Digital twins market ~$154B by 2030' },
  { label: 'Grand View Research', url: 'https://www.grandviewresearch.com/horizon/outlook/healthcare-digital-twins-market-size/global', desc: 'Healthcare digital twins' },
  { label: 'Reddit (media)', url: 'https://www.reddit.com/r/u_marketus/comments/18lti5c', desc: 'Generative AI in media' },
  { label: 'Reddit (AI agents)', url: 'https://www.reddit.com/r/aiagents/comments/1oeqmu5', desc: 'AI agent market evolution' },
];
