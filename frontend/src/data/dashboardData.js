export const dashboardStats = [
  {
    id: 1,
    label: 'Total Scans',
    value: '--',
    trend: 'Awaiting backend data',
    tone: 'primary',
  },
  {
    id: 2,
    label: 'Normal Scans',
    value: '--',
    trend: 'Awaiting AI integration',
    tone: 'success',
  },
  {
    id: 3,
    label: 'Flagged Scans',
    value: '--',
    trend: 'Awaiting AI integration',
    tone: 'danger',
  },
  {
    id: 4,
    label: 'Under Review',
    value: '--',
    trend: 'Awaiting backend data',
    tone: 'warning',
  },
  {
    id: 5,
    label: 'Patients',
    value: '--',
    trend: 'Awaiting database',
    tone: 'primary',
  },
];

export const recentScans = [];

export const monthlyScanData = [
  { month: 'Jan', scans: 0 },
  { month: 'Feb', scans: 0 },
  { month: 'Mar', scans: 0 },
  { month: 'Apr', scans: 0 },
  { month: 'May', scans: 0 },
  { month: 'Jun', scans: 0 },
];

export const anomalyDistribution = [];

export const systemStatus = [
  {
    id: 1,
    name: 'Frontend',
    status: 'Ready',
    tone: 'success',
  },
  {
    id: 2,
    name: 'Backend API',
    status: 'Foundation ready',
    tone: 'success',
  },
  {
    id: 3,
    name: 'AI Model',
    status: 'Not connected',
    tone: 'warning',
  },
  {
    id: 4,
    name: 'Database',
    status: 'Integration pending',
    tone: 'warning',
  },
];
