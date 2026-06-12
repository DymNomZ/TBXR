// ✏️ Add new statuses here as the project grows
const STATUS_STYLES = {
  // Triage
  'Non Urgent':          'bg-green-100 text-green-700',
  'Urgent':              'bg-orange-100 text-orange-700',
  'Emergency':           'bg-red-100 text-red-700',
  'Resuscitation':       'bg-purple-100 text-purple-700',
  'Pass Away':           'bg-gray-100 text-gray-500',
  // Upload / X-ray record
  'PENDING':             'bg-blue-100 text-blue-700',
  'IN_REVIEW':           'bg-orange-100 text-orange-700',
  'AI_REVIEWED':         'bg-purple-100 text-purple-700',
  'COMPLETED':           'bg-green-100 text-green-700',
  'Reviewed - Normal':   'bg-green-100 text-green-700',
  'Reviewed - Abnormal': 'bg-red-100 text-red-700',
  'Pending AI Scoring':  'bg-blue-100 text-blue-700',
}

const DEFAULT_STYLE = 'bg-gray-100 text-gray-500';

export default function StatusBadge({ status }) {
  const style = STATUS_STYLES[status] ?? DEFAULT_STYLE;
  return (
    <span className={`inline-block px-3 py-1 rounded-full text-xs font-semibold ${style}`}>
      {status}
    </span>
  );
}