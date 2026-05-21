import { useState, useEffect } from 'react';
import { Copy, Plus, Trash2, Eye, FileText, Mail } from 'lucide-react';
import { updateSchema } from './schema';
import { renderV2, renderV3 } from './renderers';
import './index.css';

const DEFAULT_STATE = {
  preheader: '',
  slug: '',
  heading: '',
  subheaderLabel: '',
  subheaderBullets: [''],
  bodyParagraphs: [''],
  quoteText: '',
  quoteAttribution: '',
  linkLabel: '',
  linkUrl: '',
  heroImageUrl: '',
  heroImageCaption: '',
  signOffName: 'Alex Baddeley',
  signOffTitle: 'Evolution Stables',
};

function App() {
  const [view, setView] = useState('welcome'); // 'welcome' | 'editor'
  const [data, setData] = useState(() => {
    const saved = localStorage.getItem('evolution-update-draft-v2');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {
        console.error('Failed to parse saved draft', e);
      }
    }
    return DEFAULT_STATE;
  });

  const [errors, setErrors] = useState({});
  const [previewMode, setPreviewMode] = useState('v2'); // 'v2' | 'v3'

  // Auto-save
  useEffect(() => {
    localStorage.setItem('evolution-update-draft-v2', JSON.stringify(data));
  }, [data]);

  // Validate on change
  useEffect(() => {
    const result = updateSchema.safeParse(data);
    if (!result.success) {
      setErrors(result.error.flatten().fieldErrors);
    } else {
      setErrors({});
    }
  }, [data]);

  const updateField = (field, value) => {
    setData(prev => ({ ...prev, [field]: value }));
  };

  const updateBullet = (index, value) => {
    const newBullets = [...data.subheaderBullets];
    newBullets[index] = value;
    setData(prev => ({ ...prev, subheaderBullets: newBullets }));
  };

  const addBullet = () => {
    setData(prev => ({ ...prev, subheaderBullets: [...prev.subheaderBullets, ''] }));
  };

  const removeBullet = (index) => {
    if (data.subheaderBullets.length === 1) return;
    const newBullets = data.subheaderBullets.filter((_, i) => i !== index);
    setData(prev => ({ ...prev, subheaderBullets: newBullets }));
  };

  const updateParagraph = (index, value) => {
    const newParagraphs = [...data.bodyParagraphs];
    newParagraphs[index] = value;
    setData(prev => ({ ...prev, bodyParagraphs: newParagraphs }));
  };

  const addParagraph = () => {
    setData(prev => ({ ...prev, bodyParagraphs: [...prev.bodyParagraphs, ''] }));
  };

  const removeParagraph = (index) => {
    if (data.bodyParagraphs.length === 1) return;
    const newParagraphs = data.bodyParagraphs.filter((_, i) => i !== index);
    setData(prev => ({ ...prev, bodyParagraphs: newParagraphs }));
  };

  const copyHtml = (type) => {
    const html = type === 'v2' ? renderV2(data) : renderV3(data);
    navigator.clipboard.writeText(html);
    // Could add toast here
  };

  const startEditing = () => {
    setView('editor');
  };

  const clearDraft = () => {
    if (confirm('Clear all content and start over?')) {
      setData(DEFAULT_STATE);
      localStorage.removeItem('evolution-update-draft-v2');
    }
  };

  if (view === 'welcome') {
    return (
      <div className="app-container" style={{ display: 'block' }}>
        <div className="welcome-screen">
          <h1>Evolution Stables <span className="text-gold">Update Builder</span></h1>
          <p>
            Create production-quality investor updates with structured content entry.<br />
            Fill in the fields, see live preview, copy the HTML.
          </p>

          <div className="welcome-grid">
            <div className="welcome-card">
              <h3>Structured Input</h3>
              <p>No parsing, no guessing. Just fill in the fields for heading, body, quote, and more.</p>
            </div>
            <div className="welcome-card">
              <h3>Live Preview</h3>
              <p>See your update render in real-time with the exact v2 dark editorial template.</p>
            </div>
            <div className="welcome-card">
              <h3>Two Outputs</h3>
              <p>Copy v2 HTML for the website, or v3 HTML for Gmail teaser emails.</p>
            </div>
            <div className="welcome-card">
              <h3>Email-Safe</h3>
              <p>Table-based layouts, inline styles, tested in Gmail and major email clients.</p>
            </div>
          </div>

          <button 
            className="btn btn-primary" 
            style={{ fontSize: '1.125rem', padding: '1rem 3rem', marginTop: 'var(--space-8)' }}
            onClick={startEditing}
          >
            Start Building
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container">
      {/* EDITOR PANEL */}
      <div className="editor-panel">
        <div className="editor-header">
          <h1>Update Editor</h1>
          <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
            <button className="btn btn-secondary" onClick={clearDraft}>
              <Trash2 size={16} style={{ marginRight: 'var(--space-1)' }} />
              Clear
            </button>
          </div>
        </div>

        {/* Preheader */}
        <div className="form-section">
          <div className="form-group">
            <label>Preheader *</label>
            <input
              type="text"
              value={data.preheader}
              onChange={(e) => updateField('preheader', e.target.value)}
              placeholder="Hidden email preview text"
            />
            {errors.preheader && <div className="form-hint" style={{ color: '#ef4444' }}>{errors.preheader[0]}</div>}
          </div>

          <div className="form-group">
            <label>Slug *</label>
            <input
              type="text"
              value={data.slug}
              onChange={(e) => updateField('slug', e.target.value)}
              placeholder="Prudentia-Update-20May2026"
            />
            <div className="form-hint">URL-safe filename (lowercase, hyphens only)</div>
            {errors.slug && <div className="form-hint" style={{ color: '#ef4444' }}>{errors.slug[0]}</div>}
          </div>
        </div>

        {/* Heading */}
        <div className="form-section">
          <div className="form-group">
            <label>Heading *</label>
            <input
              type="text"
              value={data.heading}
              onChange={(e) => updateField('heading', e.target.value)}
              placeholder="Prudentia Steps Up to Benchmark 75 at Te Rapa"
            />
            {errors.heading && <div className="form-hint" style={{ color: '#ef4444' }}>{errors.heading[0]}</div>}
          </div>
        </div>

        {/* Subheader */}
        <div className="form-section">
          <div className="form-group">
            <label>Subheader Label *</label>
            <input
              type="text"
              value={data.subheaderLabel}
              onChange={(e) => updateField('subheaderLabel', e.target.value)}
              placeholder="FEATURED RUNNER"
            />
            {errors.subheaderLabel && <div className="form-hint" style={{ color: '#ef4444' }}>{errors.subheaderLabel[0]}</div>}
          </div>

          <div className="form-group">
            <label>Subheader Bullets * (2-5)</label>
            <div className="bullet-list-editor">
              {data.subheaderBullets.map((bullet, index) => (
                <div key={index} className="bullet-item">
                  <input
                    type="text"
                    value={bullet}
                    onChange={(e) => updateBullet(index, e.target.value)}
                    placeholder={`Bullet ${index + 1}`}
                  />
                  <button className="btn btn-secondary" onClick={() => removeBullet(index)}>
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>
            <button className="btn btn-secondary mt-4" onClick={addBullet}>
              <Plus size={14} style={{ marginRight: 'var(--space-1)' }} />
              Add Bullet
            </button>
            {errors.subheaderBullets && <div className="form-hint" style={{ color: '#ef4444' }}>{errors.subheaderBullets[0]}</div>}
          </div>
        </div>

        {/* Body */}
        <div className="form-section">
          <div className="form-group">
            <label>Body Paragraphs *</label>
            {data.bodyParagraphs.map((paragraph, index) => (
              <div key={index} style={{ marginBottom: 'var(--space-3)', position: 'relative' }}>
                <textarea
                  value={paragraph}
                  onChange={(e) => updateParagraph(index, e.target.value)}
                  placeholder={`Paragraph ${index + 1}`}
                  style={{ minHeight: '100px' }}
                />
                {data.bodyParagraphs.length > 1 && (
                  <button
                    className="btn btn-danger"
                    onClick={() => removeParagraph(index)}
                    style={{ position: 'absolute', top: 'var(--space-2)', right: 'var(--space-2)', padding: 'var(--space-1) var(--space-2)', fontSize: '0.75rem' }}
                  >
                    Remove
                  </button>
                )}
              </div>
            ))}
            <button className="btn btn-secondary" onClick={addParagraph}>
              <Plus size={14} style={{ marginRight: 'var(--space-1)' }} />
              Add Paragraph
            </button>
            {errors.bodyParagraphs && <div className="form-hint" style={{ color: '#ef4444' }}>{errors.bodyParagraphs[0]}</div>}
          </div>
        </div>

        {/* Quote */}
        <div className="form-section">
          <div className="form-group">
            <label>Quote Text *</label>
            <textarea
              value={data.quoteText}
              onChange={(e) => updateField('quoteText', e.target.value)}
              placeholder="She's taken the next step up..."
              style={{ fontStyle: 'italic' }}
            />
            {errors.quoteText && <div className="form-hint" style={{ color: '#ef4444' }}>{errors.quoteText[0]}</div>}
          </div>

          <div className="form-group">
            <label>Quote Attribution *</label>
            <input
              type="text"
              value={data.quoteAttribution}
              onChange={(e) => updateField('quoteAttribution', e.target.value)}
              placeholder="— Lance O'Sullivan, Wexford Stables"
            />
            {errors.quoteAttribution && <div className="form-hint" style={{ color: '#ef4444' }}>{errors.quoteAttribution[0]}</div>}
          </div>
        </div>

        {/* Link */}
        <div className="form-section">
          <div className="form-group-row">
            <div className="form-group">
              <label>Link Label</label>
              <input
                type="text"
                value={data.linkLabel}
                onChange={(e) => updateField('linkLabel', e.target.value)}
                placeholder="Current field: TAB Te Rapa"
              />
            </div>
            <div className="form-group">
              <label>Link URL</label>
              <input
                type="url"
                value={data.linkUrl}
                onChange={(e) => updateField('linkUrl', e.target.value)}
                placeholder="https://www.tab.co.nz/..."
              />
              {errors.linkUrl && <div className="form-hint" style={{ color: '#ef4444' }}>{errors.linkUrl[0]}</div>}
            </div>
          </div>
        </div>

        {/* Hero Image */}
        <div className="form-section">
          <div className="form-group-row">
            <div className="form-group">
              <label>Hero Image URL</label>
              <input
                type="url"
                value={data.heroImageUrl}
                onChange={(e) => updateField('heroImageUrl', e.target.value)}
                placeholder="https://evolutionstables.nz/updates/..."
              />
            </div>
            <div className="form-group">
              <label>Image Caption</label>
              <input
                type="text"
                value={data.heroImageCaption}
                onChange={(e) => updateField('heroImageCaption', e.target.value)}
                placeholder="Prudentia coming home strong..."
              />
            </div>
          </div>
        </div>

        {/* Sign-off */}
        <div className="form-section">
          <div className="form-group-row">
            <div className="form-group">
              <label>Sign-off Name *</label>
              <input
                type="text"
                value={data.signOffName}
                onChange={(e) => updateField('signOffName', e.target.value)}
              />
              {errors.signOffName && <div className="form-hint" style={{ color: '#ef4444' }}>{errors.signOffName[0]}</div>}
            </div>
            <div className="form-group">
              <label>Sign-off Title *</label>
              <input
                type="text"
                value={data.signOffTitle}
                onChange={(e) => updateField('signOffTitle', e.target.value)}
              />
              {errors.signOffTitle && <div className="form-hint" style={{ color: '#ef4444' }}>{errors.signOffTitle[0]}</div>}
            </div>
          </div>
        </div>
      </div>

      {/* PREVIEW PANEL */}
      <div className="preview-panel">
        <div className="preview-header">
          <span className="preview-title">
            <Eye size={16} style={{ marginRight: 'var(--space-2)', display: 'inline', verticalAlign: 'middle' }} />
            Live Preview
          </span>
          <div className="preview-actions">
            <button
              className={previewMode === 'v2' ? 'btn btn-primary' : 'btn btn-secondary'}
              onClick={() => setPreviewMode('v2')}
            >
              <FileText size={14} style={{ marginRight: 'var(--space-1)' }} />
              v2 Web
            </button>
            <button
              className={previewMode === 'v3' ? 'btn btn-primary' : 'btn btn-secondary'}
              onClick={() => setPreviewMode('v3')}
            >
              <Mail size={14} style={{ marginRight: 'var(--space-1)' }} />
              v3 Gmail
            </button>
            <button className="btn btn-secondary" onClick={() => copyHtml(previewMode)}>
              <Copy size={14} style={{ marginRight: 'var(--space-1)' }} />
              Copy {previewMode === 'v2' ? 'Web' : 'Gmail'} HTML
            </button>
          </div>
        </div>
        <div className="preview-content">
          <iframe
            className="email-canvas"
            title="Preview"
            srcDoc={previewMode === 'v2' ? renderV2(data) : renderV3(data)}
          />
        </div>
      </div>
    </div>
  );
}

export default App;
