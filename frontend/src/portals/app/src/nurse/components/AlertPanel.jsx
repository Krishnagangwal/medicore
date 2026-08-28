import { CheckCircleIcon } from '@heroicons/react/24/outline'
import AlertCard from './AlertCard.jsx'

export default function AlertPanel({ alerts, totalPatients = 0, flash = false }) {
  return (
    <div className={`bg-white rounded-2xl shadow-sm p-5 transition ${flash ? 'ring-2 ring-red-400' : ''}`}>
      <div className="flex items-center gap-2 mb-4">
        <h2 className="font-bold text-gray-800">Live Alerts</h2>
        {alerts.length > 0 && <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />}
      </div>

      {alerts.length === 0 ? (
        <div className="text-center py-8">
          <CheckCircleIcon className="w-10 h-10 text-green-500 mx-auto mb-2" />
          <p className="text-sm text-gray-500">No alerts. Monitoring {totalPatients} patients.</p>
        </div>
      ) : (
        <div className="space-y-3 max-h-[480px] overflow-y-auto pr-1">
          {alerts.map((alert, idx) => (
            <AlertCard key={`${alert.encounter_id}-${alert.receivedAt}`} alert={alert} isNewest={idx === 0} />
          ))}
        </div>
      )}
    </div>
  )
}
