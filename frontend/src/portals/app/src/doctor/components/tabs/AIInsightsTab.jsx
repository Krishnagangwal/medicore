import SepsisRiskCard from '../ai/SepsisRiskCard.jsx'
import AttentionHeatmap from '../ai/AttentionHeatmap.jsx'
import SofaCard from '../ai/SofaCard.jsx'
import DrugInteractionCard from '../ai/DrugInteractionCard.jsx'

export default function AIInsightsTab({ prediction, onRefresh, assessing }) {
  const sepsis = prediction?.result?.sepsis
  const sepsisResult = sepsis?.result
  const drugInteraction = prediction?.result?.drug_interaction

  if (!prediction || !sepsisResult) {
    return (
      <div className="bg-white rounded-2xl shadow-sm p-10 text-center">
        <p className="text-sm text-gray-500 mb-4">No AI assessment has been run for this patient yet.</p>
        <button
          type="button"
          onClick={onRefresh}
          disabled={assessing}
          className="bg-primary text-white text-sm font-semibold rounded-lg px-4 py-2.5 hover:bg-primary/90 transition disabled:opacity-60"
        >
          {assessing ? 'Running Assessment...' : 'Run AI Assessment'}
        </button>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <SepsisRiskCard sepsis={sepsis} />
      <SofaCard sepsisResult={sepsisResult} />
      <div className="lg:col-span-2">
        <AttentionHeatmap sepsisResult={sepsisResult} />
      </div>
      <div className="lg:col-span-2">
        <DrugInteractionCard drugInteraction={drugInteraction} />
      </div>
    </div>
  )
}
