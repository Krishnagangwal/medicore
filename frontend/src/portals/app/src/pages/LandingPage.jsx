import { Link } from 'react-router-dom'
import {
  PlusIcon,
  CheckCircleIcon,
  BuildingOffice2Icon,
  UserPlusIcon,
  KeyIcon,
  BoltIcon,
  CpuChipIcon,
  ShieldCheckIcon,
  EyeIcon,
} from '@heroicons/react/24/outline'

const HOW_IT_WORKS = [
  {
    icon: BuildingOffice2Icon,
    title: 'Hospital registers',
    description: 'Submit a request — verified by the MediCore team before access is granted.',
  },
  {
    icon: UserPlusIcon,
    title: 'Admin invites staff',
    description: 'Nurses and doctors are added securely by the hospital admin.',
  },
  {
    icon: KeyIcon,
    title: 'Staff login',
    description: 'Hospital and name are selected from a dropdown — no email to remember.',
  },
  {
    icon: BoltIcon,
    title: 'AI monitors',
    description: 'Real-time sepsis alerts fire automatically as vitals are recorded.',
  },
]

const FEATURES = [
  {
    icon: CpuChipIcon,
    title: 'Time2Vec Transformer',
    description:
      'Deep learning on irregular vital sign time series. Attention weights show which hours drove the alert.',
  },
  {
    icon: ShieldCheckIcon,
    title: 'Federated Learning',
    description: 'Trained across 3 hospital partitions. No raw patient data ever leaves the hospital.',
  },
  {
    icon: EyeIcon,
    title: 'Explainable AI',
    description:
      'SHAP-equivalent attention weights on every prediction. Not a black box — a transparent clinical tool.',
  },
]

const CHECK_ITEMS = [
  'Real-time sepsis alerts',
  'Federated privacy-preserving AI',
  'SHAP explainability on every prediction',
]

const STATS = [
  { value: '0.7777', label: 'AUROC' },
  { value: '27%', label: 'Sepsis death reduction' },
  { value: 'Real-time', label: 'Alerts' },
  { value: 'Federated', label: 'Training' },
]

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white font-sans text-gray-800">
      {/* ── Navbar ── */}
      <nav className="sticky top-0 z-20 bg-white/90 backdrop-blur border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-full bg-primary flex items-center justify-center">
              <PlusIcon className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-lg text-gray-900">MediCore</span>
          </div>
          <div className="flex items-center gap-3">
            <Link
              to="/login"
              className="px-4 py-2 rounded-lg text-sm font-semibold border-2 border-primary text-primary hover:bg-primary/5 transition"
            >
              Login
            </Link>
            <Link
              to="/request"
              className="px-4 py-2 rounded-lg text-sm font-semibold bg-primary text-white hover:bg-primary/90 transition"
            >
              Request Access
            </Link>
          </div>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 lg:py-24 grid lg:grid-cols-2 gap-12 items-center">
        <div>
          <span className="inline-block px-3 py-1 rounded-full bg-accent/10 text-accent text-xs font-semibold tracking-wide mb-5">
            AI-Powered Sepsis Care
          </span>
          <h1 className="text-4xl sm:text-5xl font-bold text-gray-900 leading-tight mb-5">
            Built for hospitals. <br className="hidden sm:block" />
            Trusted by clinicians.
          </h1>
          <p className="text-gray-500 text-base sm:text-lg mb-8 max-w-xl">
            MediCore brings explainable AI to every critical decision point in sepsis care — from the first
            warning sign to safe discharge. Inspired by Sepsis Watch, Duke University.
          </p>
          <div className="flex flex-wrap gap-4 mb-8">
            <Link
              to="/request"
              className="px-6 py-3 rounded-lg font-semibold bg-primary text-white hover:bg-primary/90 transition"
            >
              Get Started
            </Link>
            <Link
              to="/login"
              className="px-6 py-3 rounded-lg font-semibold border-2 border-primary text-primary hover:bg-primary/5 transition"
            >
              Login to MediCore
            </Link>
          </div>
          <ul className="space-y-2">
            {CHECK_ITEMS.map((item) => (
              <li key={item} className="flex items-center gap-2 text-sm text-gray-600">
                <CheckCircleIcon className="w-5 h-5 text-accent shrink-0" />
                {item}
              </li>
            ))}
          </ul>
        </div>

        <div>
          <div className="bg-white rounded-2xl shadow-xl p-6 max-w-md mx-auto">
            <div className="flex items-center gap-2 mb-4">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500" />
              </span>
              <h3 className="font-semibold text-gray-800 text-sm">Live Sepsis Alert</h3>
            </div>
            <p className="text-sm text-gray-500 mb-4">Mrs. Priya Sharma — ICU-B / B4</p>
            <div className="flex items-center gap-3 mb-4">
              <span className="text-4xl font-bold text-red-600">0.82</span>
              <span className="px-2.5 py-1 rounded-full bg-red-100 text-red-600 text-xs font-bold">HIGH RISK</span>
            </div>
            <p className="text-sm text-gray-600 mb-5">
              Critical sepsis risk. Primary driver: tachycardia (HR 118). SOFA score 7.
            </p>
            <button
              type="button"
              className="w-full bg-primary text-white font-semibold rounded-lg py-2.5 hover:bg-primary/90 transition"
            >
              View Patient
            </button>
          </div>
          <div className="flex justify-center gap-3 mt-5 flex-wrap">
            {['0.7777 AUROC', '9ms inference', '3 hospitals'].map((stat) => (
              <span
                key={stat}
                className="px-3 py-1.5 rounded-full bg-surface text-gray-600 text-xs font-medium"
              >
                {stat}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ── */}
      <section className="bg-surface py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">How MediCore works</h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-8">
            {HOW_IT_WORKS.map((step, idx) => (
              <div key={step.title} className="text-center">
                <div className="mx-auto mb-4 w-14 h-14 rounded-full bg-primary/10 flex items-center justify-center relative">
                  <step.icon className="w-7 h-7 text-primary" />
                  <span className="absolute -top-1 -right-1 w-6 h-6 rounded-full bg-primary text-white text-xs font-bold flex items-center justify-center">
                    {idx + 1}
                  </span>
                </div>
                <h3 className="font-semibold text-gray-800 mb-1">{step.title}</h3>
                <p className="text-sm text-gray-500">{step.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Features ── */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="grid md:grid-cols-3 gap-8">
          {FEATURES.map((feature) => (
            <div key={feature.title} className="rounded-2xl border border-gray-100 shadow-sm p-6">
              <div className="w-11 h-11 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
                <feature.icon className="w-6 h-6 text-primary" />
              </div>
              <h3 className="font-semibold text-gray-900 mb-2">{feature.title}</h3>
              <p className="text-sm text-gray-500 leading-relaxed">{feature.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Stats bar ── */}
      <section className="bg-primary py-14">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
          {STATS.map((stat) => (
            <div key={stat.label}>
              <p className="text-3xl font-bold text-white mb-1">{stat.value}</p>
              <p className="text-sm text-white/70">{stat.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Reference ── */}
      <section className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-16 text-center">
        <p className="text-xl sm:text-2xl font-medium text-gray-800 italic leading-relaxed">
          "The first deep learning system deployed in routine hospital clinical care."
        </p>
        <p className="text-sm text-gray-500 mt-4">— Sendak et al., FAccT 2020 (Duke University)</p>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-gray-100 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-sm text-gray-500">MediCore — TCET, University of Mumbai. BE Capstone 2025-26</p>
          <div className="flex gap-5 text-sm">
            <Link to="/login" className="text-gray-500 hover:text-primary transition">
              Login
            </Link>
            <Link to="/request" className="text-gray-500 hover:text-primary transition">
              Request Access
            </Link>
          </div>
        </div>
      </footer>
    </div>
  )
}
