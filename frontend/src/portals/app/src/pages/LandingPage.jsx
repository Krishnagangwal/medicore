import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  PlusIcon,
  CheckCircleIcon,
  BuildingOffice2Icon,
  UserPlusIcon,
  KeyIcon,
  BoltIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  FlagIcon,
  EyeIcon,
  ShieldCheckIcon,
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

const CHECK_ITEMS = [
  'Real-time sepsis alerts',
  'Federated privacy-preserving AI',
  'SHAP explainability on every prediction',
]

const CREDITS = ['PhysioNet 2019 Sepsis Challenge', 'Time2Vec Transformer', 'Flower Federated Learning', 'Duke Sepsis Watch, FAccT 2020']

const STATS = [
  { value: '0.7777', label: 'AUROC' },
  { value: '27%', label: 'Sepsis death reduction' },
  { value: 'Real-time', label: 'Alerts' },
  { value: 'Federated', label: 'Training' },
]

// Carousel content for the hero's floating-card visual — each slide shows a
// different real output shape from the platform's own model contracts.
const SLIDES = [
  {
    kind: 'sepsis',
    label: 'Live Sepsis Alert',
    patient: 'Mrs. Priya Sharma — ICU-B / B4',
    value: '0.82',
    valueLabel: 'HIGH RISK',
    valueTone: 'red',
    body: 'Critical sepsis risk. Primary driver: tachycardia (HR 118). SOFA score 7.',
    pills: ['0.7777 AUROC', '24h attention window'],
  },
  {
    kind: 'drug',
    label: 'Drug Interaction Check',
    patient: 'Fentanyl + Sevoflurane',
    value: 'Moderate',
    valueLabel: 'REVIEW',
    valueTone: 'amber',
    body: 'Documented interaction in the reference database. Monitor for adverse effects.',
    pills: ['645 drugs indexed', 'RDKit fingerprints'],
  },
  {
    kind: 'explain',
    label: 'Explainability Trace',
    patient: 'Attention peak: hour 22 of 24',
    value: '7',
    valueLabel: 'SOFA SCORE',
    valueTone: 'green',
    body: 'Attention weights show exactly which hours of vitals drove this prediction.',
    pills: ['SHAP-equivalent', 'Per-hour breakdown'],
  },
]

const TONE_STYLES = {
  red: 'text-red-600',
  amber: 'text-amber-600',
  green: 'text-primary',
}
const BADGE_STYLES = {
  red: 'bg-red-100 text-red-600',
  amber: 'bg-amber-100 text-amber-700',
  green: 'bg-green-100 text-primary',
}

function HeroCard({ slide }) {
  return (
    <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-sm">
      <div className="flex items-center gap-2 mb-4">
        <span className="relative flex h-2.5 w-2.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
          <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500" />
        </span>
        <h3 className="font-semibold text-gray-800 text-sm">{slide.label}</h3>
      </div>
      <p className="text-sm text-gray-500 mb-4">{slide.patient}</p>
      <div className="flex items-center gap-3 mb-4">
        <span className={`text-4xl font-bold ${TONE_STYLES[slide.valueTone]}`}>{slide.value}</span>
        <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${BADGE_STYLES[slide.valueTone]}`}>
          {slide.valueLabel}
        </span>
      </div>
      <p className="text-sm text-gray-600">{slide.body}</p>
    </div>
  )
}

function ShowcaseCard({ title, description, pills }) {
  return (
    <div className="bg-cream-dark rounded-[1.75rem] p-8">
      <h3 className="font-serif text-2xl text-gray-900 mb-3">{title}</h3>
      <p className="text-gray-500 leading-relaxed">{description}</p>
      <div className="mt-6 space-y-3">
        {pills.map((p) => (
          <div key={p.text} className="flex items-center gap-3 bg-white rounded-xl px-4 py-3 shadow-sm">
            <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
              <p.icon className="w-5 h-5 text-primary" />
            </div>
            <span className="text-sm text-gray-700">{p.text}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function LandingPage() {
  const [slide, setSlide] = useState(0)
  const prevSlide = () => setSlide((s) => (s - 1 + SLIDES.length) % SLIDES.length)
  const nextSlide = () => setSlide((s) => (s + 1) % SLIDES.length)

  return (
    <div className="min-h-screen overflow-x-hidden bg-cream font-sans text-gray-800 p-3 sm:p-5">
      <div className="max-w-7xl mx-auto">
        {/* ── Framed hero ── */}
        <div className="relative bg-[#faf9f5] rounded-[2rem] sm:rounded-[2.5rem] border border-black/5 shadow-sm overflow-visible">
          {/* Nav pill */}
          <div className="pt-6 px-6 flex justify-center">
            <nav className="bg-white rounded-full shadow-sm px-2 py-1.5 flex items-center gap-1">
              <div className="flex items-center gap-2 pl-2 pr-3">
                <div className="w-7 h-7 rounded-full bg-primary flex items-center justify-center">
                  <PlusIcon className="w-4 h-4 text-white" />
                </div>
                <span className="font-bold text-sm text-gray-900">MediCore</span>
              </div>
              <span className="w-px h-5 bg-gray-200" />
              <a
                href="#how-it-works"
                className="px-4 py-2 rounded-full text-sm font-medium text-gray-600 hover:bg-surface transition hidden sm:inline-block"
              >
                How it works
              </a>
              <Link
                to="/request"
                className="px-4 py-2 rounded-full text-sm font-medium text-gray-600 hover:bg-surface transition"
              >
                Request Access
              </Link>
              <Link
                to="/login"
                className="px-4 py-2 rounded-full text-sm font-semibold bg-primary text-white hover:bg-primary/90 transition"
              >
                Login
              </Link>
            </nav>
          </div>

          {/* Hero content */}
          <div className="relative px-6 sm:px-10 lg:px-16 py-14 lg:py-20 grid lg:grid-cols-2 gap-14 items-center">
            <div>
              <span className="inline-block px-3 py-1 rounded-full bg-accent/10 text-accent text-xs font-semibold tracking-wide mb-6">
                AI-Powered Sepsis Care
              </span>
              <h1 className="font-serif text-5xl sm:text-6xl text-gray-900 leading-[1.08] mb-6">
                Built for hospitals.
                <br />
                Trusted by clinicians.
              </h1>
              <p className="text-gray-500 text-base sm:text-lg mb-8 max-w-md">
                MediCore brings explainable AI to every critical decision point in sepsis care —
                from the first warning sign to safe discharge. Inspired by Sepsis Watch, Duke University.
              </p>
              <div className="flex flex-wrap gap-3 mb-8">
                <Link
                  to="/request"
                  className="px-6 py-3 rounded-full font-semibold bg-primary text-white hover:bg-primary/90 transition"
                >
                  Get Started
                </Link>
                <Link
                  to="/login"
                  className="px-6 py-3 rounded-full font-semibold border-2 border-gray-200 text-gray-700 hover:border-gray-300 transition"
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

            <div className="flex justify-center">
              <div className="relative rounded-[1.75rem] overflow-hidden w-full max-w-md aspect-[4/5] sm:aspect-square lg:aspect-[4/5] bg-primary flex items-center justify-center p-6">
                <HeroCard slide={SLIDES[slide]} />
              </div>
            </div>

            {/* Carousel controls — cycle the hero card between different
                model outputs (sepsis alert / drug interaction / explainability) */}
            <button
              type="button"
              onClick={prevSlide}
              aria-label="Previous example"
              className="hidden lg:flex absolute left-0 top-1/2 -translate-y-1/2 -translate-x-1/2 w-14 h-14 rounded-full bg-white shadow-lg items-center justify-center hover:scale-105 transition z-10"
            >
              <ChevronLeftIcon className="w-5 h-5 text-gray-700" />
            </button>
            <button
              type="button"
              onClick={nextSlide}
              aria-label="Next example"
              className="hidden lg:flex absolute right-0 top-1/2 -translate-y-1/2 translate-x-1/2 w-14 h-14 rounded-full bg-white shadow-lg items-center justify-center hover:scale-105 transition z-10"
            >
              <ChevronRightIcon className="w-5 h-5 text-gray-700" />
            </button>
            <div className="flex lg:hidden justify-center gap-2 -mt-6">
              {SLIDES.map((s, i) => (
                <button
                  key={s.label}
                  type="button"
                  onClick={() => setSlide(i)}
                  aria-label={`Show ${s.label}`}
                  className={`h-2 rounded-full transition-all ${i === slide ? 'w-6 bg-primary' : 'w-2 bg-gray-300'}`}
                />
              ))}
            </div>
          </div>

          {/* Credits strip */}
          <div className="border-t border-black/5 px-6 sm:px-10 py-6 flex flex-wrap items-center justify-center gap-x-10 gap-y-2">
            {CREDITS.map((c) => (
              <span key={c} className="text-xs sm:text-sm text-gray-400 font-medium tracking-wide text-center">
                {c}
              </span>
            ))}
          </div>
        </div>

        {/* ── How it works ── */}
        <section id="how-it-works" className="py-16 scroll-mt-6">
          <h2 className="font-serif text-3xl text-center text-gray-900 mb-12">How MediCore works</h2>
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
        </section>

        {/* ── Showcase cards ── */}
        <section className="pb-16 grid md:grid-cols-2 gap-6">
          <ShowcaseCard
            title="Completely Explainable"
            description="Every alert traces back to the exact hours and vitals that drove it — attention weights and SHAP-equivalent breakdowns, not a black box."
            pills={[
              { icon: FlagIcon, text: 'Flag high-risk vitals automatically' },
              { icon: EyeIcon, text: 'Per-hour attention breakdown on every alert' },
            ]}
          />
          <ShowcaseCard
            title="Privacy-First Training"
            description="Trained across 3 simulated hospital partitions using federated learning. Raw patient data never leaves the hospital it came from."
            pills={[
              { icon: ShieldCheckIcon, text: 'No raw data ever leaves the hospital' },
              { icon: BoltIcon, text: 'Real-time posting to the AI Gateway' },
            ]}
          />
        </section>

        {/* ── Stats bar ── */}
        <section className="rounded-[2rem] bg-primary py-14 mb-16">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
            {STATS.map((s) => (
              <div key={s.label}>
                <p className="text-3xl font-bold text-white mb-1">{s.value}</p>
                <p className="text-sm text-white/70">{s.label}</p>
              </div>
            ))}
          </div>
        </section>

        {/* ── Reference ── */}
        <section className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 pb-16 text-center">
          <p className="font-serif text-2xl sm:text-3xl text-gray-800 italic leading-relaxed">
            "The first deep learning system deployed in routine hospital clinical care."
          </p>
          <p className="text-sm text-gray-500 mt-4">— Sendak et al., FAccT 2020 (Duke University)</p>
        </section>

        {/* ── Footer ── */}
        <footer className="border-t border-black/10 py-8">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 px-2">
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
    </div>
  )
}
