// ✏️ Add new statuses here as the project grows
const STATUS_STYLES = {
  'Non Urgent':    'bg-green-100 text-green-700',
  'Urgent':        'bg-orange-100 text-orange-700',
  'Emergency':     'bg-red-100 text-red-700',
  'Resuscitation': 'bg-purple-100 text-purple-700',
  'Pass Away':     'bg-gray-100 text-gray-500',
};

const DEFAULT_STYLE = 'bg-gray-100 text-gray-500';

export default function StatusBadge({ status }) {
  const style = STATUS_STYLES[status] ?? DEFAULT_STYLE;
  return (
    <span className={`inline-block px-3 py-1 rounded-full text-xs font-semibold ${style}`}>
      {status}
    </span>
  );
}