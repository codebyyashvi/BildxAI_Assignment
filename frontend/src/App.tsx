import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'

type Status = 'idle' | 'pending' | 'processing' | 'retrying' | 'completed' | 'failed'

type ProductForm = {
  image_url: string
  product_name: string
  product_description: string
  target_audience: string
  key_benefits: string[]
  tone: string
}

type Generation = {
  id: string
  status: Exclude<Status, 'idle'>
  creative_output?: {
    headline: string
    supporting_text: string
    cta: string
    visual_direction: string
  }
  image_url?: string
  error_message?: string
  metadata?: {
    model: string
    retry_count: number
    execution_time_ms?: number
  }
}

const API_URL = (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '')

const blankForm: ProductForm = {
  image_url: '',
  product_name: '',
  product_description: '',
  target_audience: '',
  key_benefits: ['', '', ''],
  tone: 'Confident and modern',
}

function absoluteApiUrl(path?: string) {
  if (!path) return ''
  if (/^https?:\/\//.test(path)) return path
  const apiOrigin = API_URL.startsWith('http') ? new URL(API_URL).origin : window.location.origin
  return `${apiOrigin}${path}`
}

function App() {
  const [form, setForm] = useState<ProductForm>(blankForm)
  const [status, setStatus] = useState<Status>('idle')
  const [generation, setGeneration] = useState<Generation | null>(null)
  const [error, setError] = useState('')
  const [samples, setSamples] = useState<ProductForm[]>([])
  const [previewFailed, setPreviewFailed] = useState(false)
  const pollTimer = useRef<number | undefined>(undefined)

  useEffect(() => {
    fetch(`${API_URL}/samples`)
      .then((response) => (response.ok ? response.json() : []))
      .then(setSamples)
      .catch(() => undefined)
    return () => window.clearTimeout(pollTimer.current)
  }, [])

  const updateField = <K extends keyof ProductForm>(field: K, value: ProductForm[K]) => {
    setForm((current) => ({ ...current, [field]: value }))
    if (field === 'image_url') setPreviewFailed(false)
  }

  const updateBenefit = (index: number, value: string) => {
    const next = [...form.key_benefits]
    next[index] = value
    updateField('key_benefits', next)
  }

  const poll = async (id: string) => {
    try {
      const response = await fetch(`${API_URL}/generations/${id}`)
      if (!response.ok) throw new Error('Could not retrieve generation status.')
      const data: Generation = await response.json()
      setGeneration(data)
      setStatus(data.status)
      if (!['completed', 'failed'].includes(data.status)) {
        pollTimer.current = window.setTimeout(() => poll(id), 900)
      }
    } catch (reason) {
      setStatus('failed')
      setError(reason instanceof Error ? reason.message : 'Status check failed.')
    }
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    window.clearTimeout(pollTimer.current)
    setError('')
    setGeneration(null)
    setStatus('pending')

    try {
      const response = await fetch(`${API_URL}/generations`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Idempotency-Key': crypto.randomUUID(),
        },
        body: JSON.stringify({
          ...form,
          key_benefits: form.key_benefits.filter((benefit) => benefit.trim()),
        }),
      })
      const data = await response.json()
      if (!response.ok) {
        const detail = Array.isArray(data.detail)
          ? data.detail.map((item: { msg: string }) => item.msg).join(' ')
          : data.detail
        throw new Error(detail || 'Generation could not be started.')
      }
      setGeneration(data)
      setStatus(data.status)
      await poll(data.id)
    } catch (reason) {
      setStatus('failed')
      setError(reason instanceof Error ? reason.message : 'Generation failed.')
    }
  }

  const loadSample = (sample: ProductForm) => {
    setForm({ ...sample, key_benefits: [...sample.key_benefits] })
    setPreviewFailed(false)
    setStatus('idle')
    setGeneration(null)
    setError('')
  }

  const reset = () => {
    window.clearTimeout(pollTimer.current)
    setStatus('idle')
    setGeneration(null)
    setError('')
  }

  const busy = ['pending', 'processing', 'retrying'].includes(status)
  const resultImage = absoluteApiUrl(generation?.image_url)

  return (
    <div className="min-h-screen">
      {/* ── Top bar ── */}
      <header className="h-[76px] px-[5vw] flex items-center justify-between border-b border-line bg-[rgba(10,12,11,.82)] backdrop-blur-[16px] sticky top-0 z-10">
        <a className="flex items-center gap-[11px] text-cream no-underline font-bold text-[19px] tracking-[-0.5px]" href="/" aria-label="Bildx Creative home">
          <span className="grid place-items-center w-8 h-8 text-[#07100a] bg-lime rounded-[9px] font-black">B</span>
          <span>bildx<span className="text-muted font-medium ml-[3px]">creative</span></span>
        </a>
        <div className="text-muted text-[12px] uppercase tracking-[1.2px] flex items-center gap-[9px]">
          <span className="w-[7px] h-[7px] rounded-full bg-lime shadow-[0_0_12px_var(--color-lime)]" />
          AI studio online
        </div>
      </header>

      <main className="w-[min(1400px,92vw)] mx-auto">
        {/* ── Hero intro ── */}
        <section className="text-center py-[78px] px-5 pb-[58px] max-w-[820px] mx-auto max-md:pt-[55px]">
          <div className="inline-flex items-center gap-2 text-lime border border-[rgba(194,244,104,.22)] rounded-full py-[7px] px-[14px] text-[11px] uppercase tracking-[1.5px] bg-[rgba(194,244,104,.05)]">
            <span>✦</span> AI-powered creative studio
          </div>
          <h1 className="font-display text-[clamp(44px,6vw,76px)] leading-[.99] tracking-[-3px] mt-[25px] mb-[22px] text-cream font-semibold max-md:tracking-[-2px]">
            Turn any product into<br /><em className="text-lime font-normal">campaign-ready creative.</em>
          </h1>
          <p className="text-muted max-w-[650px] mx-auto text-[17px] leading-[1.65]">
            Bring the product facts. We'll create grounded copy and a polished, downloadable ad—without inventing a thing.
          </p>
        </section>

        {/* ── Workspace grid ── */}
        <div className="grid grid-cols-[minmax(0,1fr)_minmax(400px,.95fr)] gap-[18px] items-start pb-20 text-left max-[900px]:grid-cols-1">

          {/* ─ Form panel ─ */}
          <form className="bg-panel border border-line rounded-[20px] overflow-hidden shadow-[0_20px_70px_rgba(0,0,0,.18)] p-[30px] max-[560px]:p-5" onSubmit={submit}>
            {/* Panel heading */}
            <div className="flex gap-[14px] items-center pb-[25px] border-b border-line">
              <span className="grid place-items-center w-10 h-10 shrink-0 rounded-xl bg-soft text-lime font-mono text-[11px] border border-line">01</span>
              <div>
                <h2 className="m-0 mb-[3px] text-cream text-[18px] tracking-[-0.3px]">Product brief</h2>
                <p className="m-0 text-muted text-[12px]">Tell us what makes your product worth noticing.</p>
              </div>
            </div>

            {/* Sample pills */}
            {samples.length > 0 && (
              <div className="pt-5 pb-2">
                <span className="block text-muted text-[10px] uppercase tracking-[1px] mb-[9px]">Start with a sample</span>
                <div className="flex gap-[7px] flex-wrap">
                  {samples.map((sample) => (
                    <button type="button" key={sample.product_name} onClick={() => loadSample(sample)}
                      className="text-txt bg-soft border border-line rounded-lg py-[7px] px-[10px] text-[11px] cursor-pointer hover:border-[rgba(194,244,104,.45)] hover:text-lime transition-colors">
                      {sample.product_name}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Image URL */}
            <label className="block mt-[18px]">
              <span className="block text-[#d6d5cb] text-[11px] uppercase tracking-[.8px] mb-2">Product image URL <b className="text-lime font-normal">*</b></span>
              <input type="url" required placeholder="https://example.com/product.jpg"
                value={form.image_url} onChange={(e) => updateField('image_url', e.target.value)} />
              <small className="block text-[#62665e] text-[10px] mt-[6px]">Use a direct, publicly accessible JPG, PNG, WEBP, GIF, or BMP URL.</small>
            </label>

            {/* Source preview */}
            <div className="h-[115px] mt-[11px] border border-dashed border-line rounded-xl grid place-items-center overflow-hidden bg-[#111411]">
              {form.image_url && !previewFailed ? (
                <img src={form.image_url} onError={() => setPreviewFailed(true)} alt="Product source preview" className="w-full h-full object-contain" />
              ) : (
                <div className="text-center text-[#5d625a] text-[11px]">
                  <span className="text-[26px] text-[#3e433c]">◇</span>
                  <p className="mt-[2px]">{previewFailed ? 'Preview unavailable' : 'Image preview'}</p>
                </div>
              )}
            </div>

            {/* Name + Tone row */}
            <div className="grid grid-cols-2 gap-[14px] max-[560px]:grid-cols-1 max-[560px]:gap-0">
              <label className="block mt-[18px]">
                <span className="block text-[#d6d5cb] text-[11px] uppercase tracking-[.8px] mb-2">Product name <b className="text-lime font-normal">*</b></span>
                <input required maxLength={100} placeholder="e.g. ROAM Lock 750" value={form.product_name}
                  onChange={(e) => updateField('product_name', e.target.value)} />
              </label>
              <label className="block mt-[18px]">
                <span className="block text-[#d6d5cb] text-[11px] uppercase tracking-[.8px] mb-2">Tone <b className="text-lime font-normal">*</b></span>
                <input required maxLength={100} placeholder="e.g. Bold and adventurous" value={form.tone}
                  onChange={(e) => updateField('tone', e.target.value)} />
              </label>
            </div>

            {/* Description */}
            <label className="block mt-[18px]">
              <span className="block text-[#d6d5cb] text-[11px] uppercase tracking-[.8px] mb-2">Product description <b className="text-lime font-normal">*</b></span>
              <textarea required minLength={5} maxLength={1000} rows={3}
                placeholder="Describe the product using factual, verifiable details."
                value={form.product_description} onChange={(e) => updateField('product_description', e.target.value)} />
            </label>

            {/* Target audience */}
            <label className="block mt-[18px]">
              <span className="block text-[#d6d5cb] text-[11px] uppercase tracking-[.8px] mb-2">Target audience <b className="text-lime font-normal">*</b></span>
              <input required maxLength={200} placeholder="e.g. Commuters, gym users and day hikers"
                value={form.target_audience} onChange={(e) => updateField('target_audience', e.target.value)} />
            </label>

            {/* Key benefits */}
            <fieldset className="border-0 p-0 mt-5">
              <legend className="block text-[#d6d5cb] text-[11px] uppercase tracking-[.8px] mb-2">Key benefits <b className="text-lime font-normal">*</b></legend>
              {form.key_benefits.map((benefit, index) => (
                <div className="grid grid-cols-[28px_1fr_30px] items-center gap-[7px] mb-2" key={index}>
                  <span className="text-[#51564f] font-mono text-[10px]">{String(index + 1).padStart(2, '0')}</span>
                  <input required={index === 0} maxLength={160} value={benefit}
                    placeholder={index === 0 ? 'Up to 12 hours cold' : 'Add another factual benefit'}
                    onChange={(e) => updateBenefit(index, e.target.value)} />
                  {form.key_benefits.length > 1 && (
                    <button type="button" aria-label={`Remove benefit ${index + 1}`}
                      className="border-0 bg-transparent text-[#666b63] cursor-pointer text-[20px] hover:text-err"
                      onClick={() => updateField('key_benefits', form.key_benefits.filter((_, i) => i !== index))}>×</button>
                  )}
                </div>
              ))}
              {form.key_benefits.length < 10 && (
                <button className="ml-[35px] mt-[3px] text-txt bg-soft border border-line rounded-lg py-[7px] px-[10px] text-[11px] cursor-pointer hover:border-[rgba(194,244,104,.45)] hover:text-lime" type="button"
                  onClick={() => updateField('key_benefits', [...form.key_benefits, ''])}>+ Add benefit</button>
              )}
            </fieldset>

            {/* Generate button */}
            <button className="w-full border-0 rounded-[11px] py-[15px] px-[18px] mt-[25px] cursor-pointer flex justify-center items-center gap-[10px] text-[#10150d] bg-lime font-extrabold text-[13px] transition-[transform,box-shadow] duration-200 hover:not-disabled:-translate-y-[1px] hover:not-disabled:shadow-[0_10px_30px_rgba(194,244,104,.14)] disabled:cursor-wait disabled:opacity-75" type="submit" disabled={busy}>
              {busy ? <><span className="spinner" /> Creating your ad…</> : <>✦ Generate campaign creative <span className="ml-auto">→</span></>}
            </button>
            <p className="text-[#60655d] text-center text-[10px] mt-[10px] mx-[10px]">Facts stay grounded in your brief. No invented claims, discounts, or endorsements.</p>
          </form>

          {/* ─ Result panel ─ */}
          <section className={`bg-panel border border-line rounded-[20px] overflow-hidden shadow-[0_20px_70px_rgba(0,0,0,.18)] min-h-[735px] sticky top-[94px] max-[900px]:static max-[900px]:min-h-[640px]`} aria-live="polite">
            {/* Panel heading */}
            <div className="flex gap-[14px] items-center p-[30px] border-b border-line max-[560px]:p-5">
              <span className="grid place-items-center w-10 h-10 shrink-0 rounded-xl bg-soft text-lime font-mono text-[11px] border border-line">02</span>
              <div>
                <h2 className="m-0 mb-[3px] text-cream text-[18px] tracking-[-0.3px]">Campaign creative</h2>
                <p className="m-0 text-muted text-[12px]">Your generated ad and ready-to-use copy.</p>
              </div>
              {status !== 'idle' && (
                <span className={`ml-auto py-[6px] px-[9px] rounded-full font-mono text-[9px] uppercase tracking-[.7px] border border-line
                  ${status === 'completed' ? 'text-lime bg-[rgba(194,244,104,.08)]' : ''}
                  ${status === 'failed' ? 'text-err bg-[rgba(245,143,130,.08)]' : ''}
                  ${['pending','processing','retrying'].includes(status) ? 'text-warn bg-[rgba(240,209,120,.08)]' : ''}`}>
                  {status}
                </span>
              )}
            </div>

            {/* ── Idle state ── */}
            {status === 'idle' && (
              <div className="min-h-[600px] flex flex-col justify-center items-center text-center p-[30px]">
                <div className="empty-art">
                  <span>✦</span><i /><i />
                </div>
                <h3 className="text-cream m-0 mb-[9px] text-[18px]">Your canvas is ready</h3>
                <p className="text-muted text-[12px] max-w-[320px] leading-[1.6] m-0">Complete the product brief and generate your first campaign creative.</p>
                <div className="flex gap-[15px] mt-[22px] text-[#737970] text-[10px] flex-wrap justify-center">
                  <span>✓ Grounded copy</span><span>✓ Product fidelity</span><span>✓ Download ready</span>
                </div>
              </div>
            )}

            {/* ── Working state ── */}
            {busy && (
              <div className="min-h-[600px] flex flex-col justify-center items-center text-center p-[30px]">
                <div className="scan-card">
                  <div className="scan-line" />
                  <span>Analyzing product &amp; composing creative</span>
                </div>
                <h3 className="text-cream m-0 mb-[9px] text-[18px]">{status === 'retrying' ? 'A temporary issue—retrying safely' : 'Building your campaign'}</h3>
                <p className="text-muted text-[12px] max-w-[320px] leading-[1.6] m-0">This usually takes a few seconds. You can keep this tab open while we work.</p>
                <div className="flex gap-[5px] mt-[30px] flex-wrap justify-center">
                  <span className="done text-[9px] py-[6px] px-2 border border-[rgba(194,244,104,.25)] rounded-full text-lime">Brief received</span>
                  <span className={`text-[9px] py-[6px] px-2 border rounded-full ${status !== 'pending' ? 'done text-lime border-[rgba(194,244,104,.25)]' : 'text-[#596057] border-line'}`}>Copy generated</span>
                  <span className="text-[#596057] text-[9px] py-[6px] px-2 border border-line rounded-full">Ad composed</span>
                </div>
              </div>
            )}

            {/* ── Failed state ── */}
            {status === 'failed' && (
              <div className="min-h-[600px] flex flex-col justify-center items-center text-center p-[30px]">
                <div className="w-14 h-14 grid place-items-center text-err bg-[rgba(245,143,130,.08)] border border-[rgba(245,143,130,.2)] rounded-full text-[25px] mb-[22px]">!</div>
                <h3 className="text-cream m-0 mb-[9px] text-[18px]">We couldn't create this ad</h3>
                <p className="text-muted text-[12px] max-w-[320px] leading-[1.6] m-0">{generation?.error_message || error || 'Please check your product image URL and try again.'}</p>
                <button type="button" onClick={reset}
                  className="mt-6 border border-line bg-soft text-cream rounded-[9px] py-[10px] px-[15px] cursor-pointer hover:border-[rgba(194,244,104,.35)] transition-colors">Edit brief &amp; retry</button>
              </div>
            )}

            {/* ── Completed state ── */}
            {status === 'completed' && generation?.creative_output && (
              <div className="p-[22px]">
                {/* Ad frame */}
                <div className="relative bg-[#101210] rounded-xl overflow-hidden border border-line">
                  <img src={resultImage} alt={`Generated advertisement for ${form.product_name}`} className="block w-full max-h-[510px] object-contain" />
                  <a className="absolute right-3 bottom-3 py-[9px] px-3 rounded-lg text-[#11150e] bg-lime text-[10px] no-underline font-bold hover:shadow-lg transition-shadow" href={resultImage} download>↓ Download PNG</a>
                </div>

                {/* Copy block */}
                <div className="pt-[22px] px-[3px] pb-2">
                  <span className="text-[#62685f] text-[9px] uppercase tracking-[1px] block">Headline</span>
                  <h3 className="text-cream font-display font-medium text-[25px] leading-[1.2] mt-[5px] mb-[17px]">{generation.creative_output.headline}</h3>
                  <span className="text-[#62685f] text-[9px] uppercase tracking-[1px] block">Supporting copy</span>
                  <p className="text-[#aeb3a9] text-[12px] mt-[5px] mb-[18px]">{generation.creative_output.supporting_text}</p>
                  <div className="grid grid-cols-[.7fr_1.3fr] gap-3 max-[560px]:grid-cols-1">
                    <div className="bg-soft border border-line rounded-[9px] p-[11px]">
                      <span className="text-[#62685f] text-[9px] uppercase tracking-[1px] block">Call to action</span>
                      <strong className="block text-[#c9cdc4] text-[10px] mt-1 font-medium">{generation.creative_output.cta}</strong>
                    </div>
                    <div className="bg-soft border border-line rounded-[9px] p-[11px]">
                      <span className="text-[#62685f] text-[9px] uppercase tracking-[1px] block">Visual direction</span>
                      <strong className="block text-[#c9cdc4] text-[10px] mt-1 font-medium">{generation.creative_output.visual_direction}</strong>
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-2 mt-[14px]">
                  <a className="flex-1 text-center rounded-[9px] py-[11px] text-[11px] no-underline bg-lime text-[#11150e] font-bold hover:shadow-lg transition-shadow" href={resultImage} download>↓ Download ad</a>
                  <button type="button" onClick={reset}
                    className="flex-1 border border-line bg-soft text-cream rounded-[9px] py-[11px] text-[11px] cursor-pointer hover:border-[rgba(194,244,104,.35)] transition-colors">Create another</button>
                </div>
                <p className="text-[#4d534b] font-mono text-[8px] text-center mt-[13px]">
                  {generation.metadata?.model} · {generation.metadata?.execution_time_ms?.toFixed(0)} ms · ID {generation.id.slice(0, 8)}
                </p>
              </div>
            )}
          </section>
        </div>
      </main>

      <footer className="w-[min(1400px,92vw)] mx-auto py-[25px] pb-10 border-t border-line text-[#545a52] text-[10px] flex justify-between uppercase tracking-[1px] max-[560px]:w-[calc(100%-36px)] max-[560px]:gap-[10px] max-[560px]:flex-col">
        <span>bildx creative lab</span>
        <span>Grounded AI · Deterministic composition · Secure by design</span>
      </footer>
    </div>
  )
}

export default App
