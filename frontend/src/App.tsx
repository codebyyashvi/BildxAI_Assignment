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
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="Bildx Creative home">
          <span className="brand-mark">B</span>
          <span>bildx<span className="brand-accent">creative</span></span>
        </a>
        <div className="service-status">
          <span className="status-dot" />
          AI studio online
        </div>
      </header>

      <main>
        <section className="intro">
          <div className="eyebrow"><span>✦</span> AI-powered creative studio</div>
          <h1>Turn any product into<br /><em>campaign-ready creative.</em></h1>
          <p>Bring the product facts. We’ll create grounded copy and a polished, downloadable ad—without inventing a thing.</p>
        </section>

        <div className="workspace">
          <form className="panel form-panel" onSubmit={submit}>
            <div className="panel-heading">
              <span className="step">01</span>
              <div>
                <h2>Product brief</h2>
                <p>Tell us what makes your product worth noticing.</p>
              </div>
            </div>

            {samples.length > 0 && (
              <div className="samples">
                <span>Start with a sample</span>
                <div>
                  {samples.map((sample) => (
                    <button type="button" key={sample.product_name} onClick={() => loadSample(sample)}>
                      {sample.product_name}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <label className="field">
              <span>Product image URL <b>*</b></span>
              <input
                type="url"
                required
                placeholder="https://example.com/product.jpg"
                value={form.image_url}
                onChange={(event) => updateField('image_url', event.target.value)}
              />
              <small>Use a direct, publicly accessible JPG, PNG, WEBP, GIF, or BMP URL.</small>
            </label>

            <div className="source-preview">
              {form.image_url && !previewFailed ? (
                <img src={form.image_url} onError={() => setPreviewFailed(true)} alt="Product source preview" />
              ) : (
                <div className="preview-placeholder">
                  <span>◇</span>
                  <p>{previewFailed ? 'Preview unavailable' : 'Image preview'}</p>
                </div>
              )}
            </div>

            <div className="field-row">
              <label className="field">
                <span>Product name <b>*</b></span>
                <input required maxLength={100} placeholder="e.g. ROAM Lock 750" value={form.product_name}
                  onChange={(event) => updateField('product_name', event.target.value)} />
              </label>
              <label className="field">
                <span>Tone <b>*</b></span>
                <input required maxLength={100} placeholder="e.g. Bold and adventurous" value={form.tone}
                  onChange={(event) => updateField('tone', event.target.value)} />
              </label>
            </div>

            <label className="field">
              <span>Product description <b>*</b></span>
              <textarea required minLength={5} maxLength={1000} rows={3}
                placeholder="Describe the product using factual, verifiable details."
                value={form.product_description}
                onChange={(event) => updateField('product_description', event.target.value)} />
            </label>

            <label className="field">
              <span>Target audience <b>*</b></span>
              <input required maxLength={200} placeholder="e.g. Commuters, gym users and day hikers"
                value={form.target_audience}
                onChange={(event) => updateField('target_audience', event.target.value)} />
            </label>

            <fieldset className="benefits">
              <legend>Key benefits <b>*</b></legend>
              {form.key_benefits.map((benefit, index) => (
                <div className="benefit-row" key={index}>
                  <span>{String(index + 1).padStart(2, '0')}</span>
                  <input required={index === 0} maxLength={160} value={benefit}
                    placeholder={index === 0 ? 'Up to 12 hours cold' : 'Add another factual benefit'}
                    onChange={(event) => updateBenefit(index, event.target.value)} />
                  {form.key_benefits.length > 1 && (
                    <button type="button" aria-label={`Remove benefit ${index + 1}`}
                      onClick={() => updateField('key_benefits', form.key_benefits.filter((_, i) => i !== index))}>×</button>
                  )}
                </div>
              ))}
              {form.key_benefits.length < 10 && (
                <button className="add-benefit" type="button"
                  onClick={() => updateField('key_benefits', [...form.key_benefits, ''])}>+ Add benefit</button>
              )}
            </fieldset>

            <button className="generate-button" type="submit" disabled={busy}>
              {busy ? <><span className="spinner" /> Creating your ad…</> : <><span>✦</span> Generate campaign creative <span>→</span></>}
            </button>
            <p className="form-note">Facts stay grounded in your brief. No invented claims, discounts, or endorsements.</p>
          </form>

          <section className={`panel result-panel state-${status}`} aria-live="polite">
            <div className="panel-heading">
              <span className="step">02</span>
              <div>
                <h2>Campaign creative</h2>
                <p>Your generated ad and ready-to-use copy.</p>
              </div>
              {status !== 'idle' && <span className={`status-chip ${status}`}>{status}</span>}
            </div>

            {status === 'idle' && (
              <div className="empty-state">
                <div className="empty-art"><span>✦</span><i /><i /></div>
                <h3>Your canvas is ready</h3>
                <p>Complete the product brief and generate your first campaign creative.</p>
                <div className="feature-list">
                  <span>✓ Grounded copy</span><span>✓ Product fidelity</span><span>✓ Download ready</span>
                </div>
              </div>
            )}

            {busy && (
              <div className="working-state">
                <div className="scan-card">
                  <div className="scan-line" />
                  <span>Analyzing product & composing creative</span>
                </div>
                <h3>{status === 'retrying' ? 'A temporary issue—retrying safely' : 'Building your campaign'}</h3>
                <p>This usually takes a few seconds. You can keep this tab open while we work.</p>
                <div className="progress-steps">
                  <span className="done">Brief received</span>
                  <span className={status !== 'pending' ? 'done' : ''}>Copy generated</span>
                  <span>Ad composed</span>
                </div>
              </div>
            )}

            {status === 'failed' && (
              <div className="error-state">
                <div className="error-icon">!</div>
                <h3>We couldn’t create this ad</h3>
                <p>{generation?.error_message || error || 'Please check your product image URL and try again.'}</p>
                <button type="button" onClick={reset}>Edit brief & retry</button>
              </div>
            )}

            {status === 'completed' && generation?.creative_output && (
              <div className="completed-state">
                <div className="ad-frame">
                  <img src={resultImage} alt={`Generated advertisement for ${form.product_name}`} />
                  <a className="download-overlay" href={resultImage} download>↓ Download PNG</a>
                </div>
                <div className="copy-block">
                  <span>Headline</span>
                  <h3>{generation.creative_output.headline}</h3>
                  <span>Supporting copy</span>
                  <p>{generation.creative_output.supporting_text}</p>
                  <div className="copy-meta">
                    <div><span>Call to action</span><strong>{generation.creative_output.cta}</strong></div>
                    <div><span>Visual direction</span><strong>{generation.creative_output.visual_direction}</strong></div>
                  </div>
                </div>
                <div className="result-actions">
                  <a className="primary-action" href={resultImage} download>↓ Download ad</a>
                  <button type="button" onClick={reset}>Create another</button>
                </div>
                <p className="generation-meta">
                  {generation.metadata?.model} · {generation.metadata?.execution_time_ms?.toFixed(0)} ms · ID {generation.id.slice(0, 8)}
                </p>
              </div>
            )}
          </section>
        </div>
      </main>
      <footer><span>bildx creative lab</span><span>Grounded AI · Deterministic composition · Secure by design</span></footer>
    </div>
  )
}

export default App
