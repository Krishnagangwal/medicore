const COLOR_CLASSES = {
  primary: 'text-primary border-primary/30 bg-primary/5',
  orange: 'text-orange-600 border-orange-200 bg-orange-50',
  red: 'text-red-600 border-red-200 bg-red-50',
  green: 'text-green-600 border-green-200 bg-green-50',
}

export default function StatCard({ icon: Icon, label, value, total, color = 'primary' }) {
  const cls = COLOR_CLASSES[color] || COLOR_CLASSES.primary

  return (
    <div className="bg-white rounded-2xl shadow-sm p-4 flex flex-col items-center text-center">
      <div className={`w-12 h-12 rounded-full border-2 flex items-center justify-center mb-2 ${cls}`}>
        {Icon && <Icon className="w-6 h-6" />}
      </div>
      <p className="text-2xl font-bold text-gray-800">
        {value}
        {total !== undefined && <span className="text-sm font-medium text-gray-400"> / {total}</span>}
      </p>
      <p className="text-xs text-gray-500 mt-0.5">{label}</p>
    </div>
  )
}
