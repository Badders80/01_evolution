import { useState, useEffect } from 'react';
import { 
  Plus, 
  Trash2, 
  ArrowUp, 
  ArrowDown, 
  Sun, 
  Moon, 
  Copy, 
  Sparkles, 
  Eye, 
  FileText, 
  Mail,
  Palette,
  Clipboard,
  X,
  RefreshCw,
  Image as ImageIcon
} from 'lucide-react';
import { parseRawText } from './parser';
import { renderWeb, renderTeaser } from './renderers';
import './index.css';

const DEFAULT_TOKENS = {
  colorBrandGold: '#d4a964',
  colorBgPrimary: '#ffffff',
  colorBgDark: '#020202',
  colorTextMain: '#020202',
  colorTextMuted: '#747474',
  colorTextInv: '#ffffff',
  colorBorderLight: '#d2d2d2',
  colorBorderDark: '#1a1a1a',
  fontDisplay: 'Instrument Serif',
  fontInterface: 'Inter',
  containerWidth: 600,
};

const PRESETS = {
  evolution: {
    name: 'Evolution Gold',
    tokens: {
      colorBrandGold: '#d4a964',
      colorBgPrimary: '#ffffff',
      colorBgDark: '#020202',
      colorTextMain: '#020202',
      colorTextMuted: '#747474',
      colorTextInv: '#ffffff',
      colorBorderLight: '#d2d2d2',
      colorBorderDark: '#1a1a1a',
      fontDisplay: 'Instrument Serif',
      fontInterface: 'Inter',
      containerWidth: 600,
    }
  },
  minimalMono: {
    name: 'Minimalist Mono',
    tokens: {
      colorBrandGold: '#747474',
      colorBgPrimary: '#ffffff',
      colorBgDark: '#09090b',
      colorTextMain: '#09090b',
      colorTextMuted: '#737373',
      colorTextInv: '#f5f5f5',
      colorBorderLight: '#e4e4e7',
      colorBorderDark: '#27272a',
      fontDisplay: 'Inter',
      fontInterface: 'Inter',
      containerWidth: 620,
    }
  },
  warmEditorial: {
    name: 'Warm Editorial',
    tokens: {
      colorBrandGold: '#b8860b',
      colorBgPrimary: '#faf9f6',
      colorBgDark: '#1a1816',
      colorTextMain: '#1c1b18',
      colorTextMuted: '#7c7667',
      colorTextInv: '#faf9f6',
      colorBorderLight: '#e2decb',
      colorBorderDark: '#2c2a24',
      fontDisplay: 'Playfair Display',
      fontInterface: 'Inter',
      containerWidth: 600,
    }
  }
};

const SAMPLE_TEXT = `Distance the Key for First Gear

A tough run at Otaki provides the roadmap for a step up in trip as First Gear proves his grit in a difficult Rating 65 contest.

KEY INSIGHTS:
The 1200m distance proved too sharp, and a step up to 1400m+ is the next logical step.
He will likely have one more jumpout to maintain fitness before his next assignment.

Learning from Otaki
First Gear stepped out in what was always going to be a sharp 1200m test. From the jump, he found himself a little outpaced early, forced to settle further back than ideal on a track favoring front-runners.
Despite the tricky scenario, what impressed us most was his resilience through the line. He wasn't stopping at the post, indicating exactly what the data and his pedigree have been telling us: he is crying out for more ground.

"It was a tough ask over 1200m today. He was doing his best work late. Once we get him out over 1400m or a mile, you'll see a very different horse."
— Lance O'Sullivan, Wexford Stables

The Forward Plan
The roadmap from here is clear.
The priority is to keep him ticking over and stepping up the distance parameters as he matures into these longer trips.

01
Easy Recovery
We'll give him an easy week to recover from the travel down to Otaki.

02
1000m Jumpout
A scheduled jumpout to keep his cardiovascular fitness peaked.

03
1400m Options
Circling a couple of 1400m race options towards the end of the month.`;

function App() {
  const [blocks, setBlocks] = useState([]);
  const [tokens, setTokens] = useState(() => {
    const saved = localStorage.getItem('evolution-update-tokens');
    return saved ? JSON.parse(saved) : DEFAULT_TOKENS;
  });
  const [showTokensPanel, setShowTokensPanel] = useState(false);
  const [showPasteModal, setShowPasteModal] = useState(false);
  const [rawText, setRawText] = useState('');
  const [previewMode, setPreviewMode] = useState('web'); // 'web' | 'teaser'
  const [copied, setCopied] = useState(false);

  // Auto-save blocks and tokens
  useEffect(() => {
    const savedBlocks = localStorage.getItem('evolution-update-blocks');
    if (savedBlocks) {
      try {
        let parsed = JSON.parse(savedBlocks);
        // Seamlessly migrate old footer text if stored in localStorage
        parsed = parsed.map(b => {
          if (b.type === 'footer' && b.title === 'The Future of Ownership Has Arrived') {
            return { ...b, title: 'The Future of Ownership <br /> Has Arrived' };
          }
          if (b.type === 'numbered_grid') {
            return { ...b, type: 'box', title: '', text: '' };
          }
          return b;
        });

        // Migrate preceding paragraph section headers into box blocks
        const migrated = [];
        for (let j = 0; j < parsed.length; j++) {
          const current = parsed[j];
          const next = parsed[j + 1];
          if (current.type === 'paragraph' && next && next.type === 'box') {
            const lines = current.text.split('\n').map(l => l.trim()).filter(Boolean);
            if (lines.length > 0) {
              next.title = lines[0];
              next.text = lines.slice(1).join(' ');
              continue; // Skip paragraph block
            }
          }
          migrated.push(current);
        }
        setBlocks(migrated);
      } catch (e) {
        console.error('Failed to parse saved blocks', e);
      }
    } else {
      // Load sample text by default if nothing exists
      handleRawTextImport(SAMPLE_TEXT);
    }
  }, []);

  useEffect(() => {
    if (blocks.length > 0) {
      localStorage.setItem('evolution-update-blocks', JSON.stringify(blocks));
    }
  }, [blocks]);

  useEffect(() => {
    localStorage.setItem('evolution-update-tokens', JSON.stringify(tokens));
  }, [tokens]);

  const handleRawTextImport = (text) => {
    const parsed = parseRawText(text);
    setBlocks(parsed);
    setShowPasteModal(false);
  };

  const handlePresetSelect = (presetKey) => {
    setTokens(PRESETS[presetKey].tokens);
  };

  const updateBlockField = (blockId, field, value) => {
    setBlocks(prev => prev.map(b => b.id === blockId ? { ...b, [field]: value } : b));
  };

  // Specialized block updates
  const updateInsightsItem = (blockId, itemIndex, value) => {
    setBlocks(prev => prev.map(b => {
      if (b.id === blockId) {
        const newItems = [...b.items];
        newItems[itemIndex] = value;
        return { ...b, items: newItems };
      }
      return b;
    }));
  };

  const addInsightsItem = (blockId) => {
    setBlocks(prev => prev.map(b => {
      if (b.id === blockId) {
        return { ...b, items: [...b.items, ''] };
      }
      return b;
    }));
  };

  const removeInsightsItem = (blockId, itemIndex) => {
    setBlocks(prev => prev.map(b => {
      if (b.id === blockId) {
        return { ...b, items: b.items.filter((_, idx) => idx !== itemIndex) };
      }
      return b;
    }));
  };

  const updateGridItem = (blockId, itemIndex, field, value) => {
    setBlocks(prev => prev.map(b => {
      if (b.id === blockId) {
        const newItems = [...b.items];
        newItems[itemIndex] = { ...newItems[itemIndex], [field]: value };
        return { ...b, items: newItems };
      }
      return b;
    }));
  };

  const addGridItem = (blockId) => {
    setBlocks(prev => prev.map(b => {
      if (b.id === blockId) {
        const nextNum = String(b.items.length + 1).padStart(2, '0');
        return { 
          ...b, 
          items: [...b.items, { num: nextNum, title: '', text: '' }] 
        };
      }
      return b;
    }));
  };

  const removeGridItem = (blockId, itemIndex) => {
    setBlocks(prev => prev.map(b => {
      if (b.id === blockId) {
        return { ...b, items: b.items.filter((_, idx) => idx !== itemIndex) };
      }
      return b;
    }));
  };

  // Block management
  const moveBlock = (index, direction) => {
    if (direction === 'up' && index === 0) return;
    if (direction === 'down' && index === blocks.length - 1) return;

    const newBlocks = [...blocks];
    const swapWith = direction === 'up' ? index - 1 : index + 1;
    const temp = newBlocks[index];
    newBlocks[index] = newBlocks[swapWith];
    newBlocks[swapWith] = temp;
    setBlocks(newBlocks);
  };

  const toggleBlockTheme = (blockId) => {
    setBlocks(prev => prev.map(b => 
      b.id === blockId 
        ? { ...b, theme: b.theme === 'dark' ? 'light' : 'dark' } 
        : b
    ));
  };

  const toggleBlockLogoType = (blockId) => {
    setBlocks(prev => prev.map(b => {
      if (b.id === blockId) {
        // If not set yet, toggle from the implicit default (which is watermark for dark, logo for light)
        const currentType = b.logoType || (b.theme === 'dark' ? 'watermark' : 'logo');
        return { ...b, logoType: currentType === 'watermark' ? 'logo' : 'watermark' };
      }
      return b;
    }));
  };

  const deleteBlock = (blockId) => {
    if (confirm('Delete this block?')) {
      setBlocks(prev => prev.filter(b => b.id !== blockId));
    }
  };

  const addEmptyBlock = (type) => {
    let blockData = {
      id: 'block-' + Math.random().toString(36).substr(2, 9),
      type,
      theme: 'light'
    };

    // Populate default fields depending on type
    switch (type) {
      case 'header':
        blockData.title = '';
        blockData.subtitle = 'STABLE UPDATE';
        break;
      case 'paragraph':
        blockData.text = '';
        break;
      case 'insights':
        blockData.label = 'KEY INSIGHTS';
        blockData.items = [''];
        blockData.theme = 'dark'; // insights default to dark
        break;
      case 'quote':
        blockData.text = '';
        blockData.attribution = '';
        break;
      case 'numbered_grid':
        blockData.items = [{ num: '01', title: '', text: '' }];
        break;
      case 'box':
        blockData.title = '';
        blockData.text = '';
        blockData.items = [{ num: '01', title: '', text: '' }];
        break;
      case 'hero_image':
        blockData.url = '';
        blockData.caption = '';
        break;
      case 'footer':
        blockData.title = 'The Future of Ownership <br /> Has Arrived';
        blockData.subtitle = 'DIGITAL-SYNDICATION, BY EVOLUTION STABLES, POWERED BY TOKINVEST';
        blockData.theme = 'dark';
        break;
    }

    setBlocks(prev => [...prev, blockData]);
  };

  const copyHtml = () => {
    const html = previewMode === 'web' 
      ? renderWeb(blocks, tokens) 
      : renderTeaser(blocks, tokens);
    navigator.clipboard.writeText(html);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <>
      {/* HEADER BAR */}
      <header className="app-header">
        <div className="app-logo">
          Evolution Stables <span>Update Builder</span>
        </div>
        <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
          <button className="btn btn-secondary" onClick={() => {
            setRawText('');
            setShowPasteModal(true);
          }}>
            <Clipboard size={16} />
            Paste Raw Text
          </button>
          <button className="btn btn-secondary" onClick={() => setShowTokensPanel(!showTokensPanel)}>
            <Palette size={16} />
            Design Tokens
          </button>
          <button className="btn btn-primary" onClick={copyHtml}>
            <Copy size={16} />
            {copied ? 'Copied HTML!' : 'Copy Code'}
          </button>
        </div>
      </header>

      {/* DESIGN TOKENS DRAWER */}
      {showTokensPanel && (
        <div className="app-container" style={{ display: 'block', height: 'auto', paddingBottom: 0 }}>
          <div className="tokens-panel">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-4)' }}>
              <h3 style={{ fontFamily: 'var(--font-serif)', fontSize: '1.25rem', fontWeight: 'normal' }}>
                Design Tokens
              </h3>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Presets:</span>
                {Object.entries(PRESETS).map(([key, value]) => (
                  <button key={key} className="btn btn-secondary" style={{ padding: '4px 10px', fontSize: '0.75rem' }} onClick={() => handlePresetSelect(key)}>
                    {value.name}
                  </button>
                ))}
              </div>
            </div>
            
            <div className="tokens-grid">
              <div className="form-group">
                <label>Brand Gold</label>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <input type="color" value={tokens.colorBrandGold} onChange={(e) => setTokens(prev => ({ ...prev, colorBrandGold: e.target.value }))} style={{ width: '40px', padding: 0, height: '36px', border: 'none', cursor: 'pointer' }} />
                  <input type="text" value={tokens.colorBrandGold} onChange={(e) => setTokens(prev => ({ ...prev, colorBrandGold: e.target.value }))} />
                </div>
              </div>
              <div className="form-group">
                <label>Primary Light Background</label>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <input type="color" value={tokens.colorBgPrimary} onChange={(e) => setTokens(prev => ({ ...prev, colorBgPrimary: e.target.value }))} style={{ width: '40px', padding: 0, height: '36px', border: 'none', cursor: 'pointer' }} />
                  <input type="text" value={tokens.colorBgPrimary} onChange={(e) => setTokens(prev => ({ ...prev, colorBgPrimary: e.target.value }))} />
                </div>
              </div>
              <div className="form-group">
                <label>Secondary Dark Background</label>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <input type="color" value={tokens.colorBgDark} onChange={(e) => setTokens(prev => ({ ...prev, colorBgDark: e.target.value }))} style={{ width: '40px', padding: 0, height: '36px', border: 'none', cursor: 'pointer' }} />
                  <input type="text" value={tokens.colorBgDark} onChange={(e) => setTokens(prev => ({ ...prev, colorBgDark: e.target.value }))} />
                </div>
              </div>
              <div className="form-group">
                <label>Display Font (Serif)</label>
                <select value={tokens.fontDisplay} onChange={(e) => setTokens(prev => ({ ...prev, fontDisplay: e.target.value }))}>
                  <option value="Instrument Serif">Instrument Serif</option>
                  <option value="Playfair Display">Playfair Display</option>
                  <option value="Inter">Inter (Sans)</option>
                </select>
              </div>
              <div className="form-group">
                <label>Interface Font (Sans)</label>
                <select value={tokens.fontInterface} onChange={(e) => setTokens(prev => ({ ...prev, fontInterface: e.target.value }))}>
                  <option value="Inter">Inter</option>
                  <option value="Geist Sans">Geist Sans</option>
                  <option value="Arial">Arial</option>
                </select>
              </div>
              <div className="form-group">
                <label>Container Width (px)</label>
                <input type="text" value={tokens.containerWidth} onChange={(e) => setTokens(prev => ({ ...prev, containerWidth: parseInt(e.target.value) || 600 }))} />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* MAIN CONTAINER */}
      <main className="app-container">
        
        {/* EDITOR (WHITE SPACE CANVAS) */}
        <section className="editor-panel">
          <div style={{ marginBottom: 'var(--space-4)' }}>
            <h2 className="editor-section-header">Update Content Canvas</h2>
            <p className="editor-description">
              Edit block values directly. Toggle block styles (Light/Dark) on a per-block basis.
            </p>
          </div>

          {blocks.length === 0 ? (
            <div className="welcome-panel">
              <h2>Ready to create?</h2>
              <p>Paste a raw update from your clipboard or start adding custom content blocks manually.</p>
              <div style={{ display: 'flex', gap: '12px' }}>
                <button className="btn btn-primary" onClick={() => {
                  setRawText('');
                  setShowPasteModal(true);
                }}>
                  Paste Raw Update Text
                </button>
                <button className="btn btn-secondary" onClick={() => handleRawTextImport(SAMPLE_TEXT)}>
                  Load Sample First Gear Update
                </button>
              </div>
            </div>
          ) : (
            <>
              {blocks.map((block, index) => {
                const isDark = block.theme === 'dark';
                return (
                  <div key={block.id} className={`doc-block ${isDark ? 'dark-theme-active' : ''}`}>
                    
                    {/* Meta bar */}
                    <div className="block-meta">
                      <span className="block-badge">
                        <Sparkles size={12} />
                        {block.type}
                      </span>
                      <div className="block-controls">
                        {block.type === 'header' && (
                          <button className="btn-icon" onClick={() => toggleBlockLogoType(block.id)} title="Toggle Logo/Watermark style">
                            <ImageIcon size={14} />
                          </button>
                        )}
                        <button className="btn-icon" onClick={() => toggleBlockTheme(block.id)} title="Toggle block theme (Light/Dark)">
                          {isDark ? <Sun size={14} /> : <Moon size={14} />}
                        </button>
                        <button className="btn-icon" onClick={() => moveBlock(index, 'up')} disabled={index === 0}>
                          <ArrowUp size={14} />
                        </button>
                        <button className="btn-icon" onClick={() => moveBlock(index, 'down')} disabled={index === blocks.length - 1}>
                          <ArrowDown size={14} />
                        </button>
                        <button className="btn-icon btn-danger" onClick={() => deleteBlock(block.id)}>
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>

                    {/* Block Specific Form Fields */}
                    {block.type === 'header' && (
                      <div>
                        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap', marginBottom: '16px' }}>
                          {/* Logo Style */}
                          <div style={{ flex: '1 1 120px', minWidth: '100px' }}>
                            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', marginBottom: '6px', color: 'var(--text-muted)' }}>Style</label>
                            <select 
                              value={block.logoType || 'logo'} 
                              onChange={(e) => updateBlockField(block.id, 'logoType', e.target.value)}
                              style={{ width: '100%', padding: '6px 8px', fontSize: '0.85rem' }}
                            >
                              <option value="logo">Full Logo</option>
                              <option value="watermark">Watermark</option>
                            </select>
                          </div>

                          {/* Logo Color */}
                          <div style={{ flex: '1 1 140px', minWidth: '120px' }}>
                            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', marginBottom: '6px', color: 'var(--text-muted)' }}>Color</label>
                            <select 
                              value={block.logoColor || 'adaptive'} 
                              onChange={(e) => updateBlockField(block.id, 'logoColor', e.target.value)}
                              style={{ width: '100%', padding: '6px 8px', fontSize: '0.85rem' }}
                            >
                              <option value="adaptive">Adaptive</option>
                              <option value="dark">Dark (Black)</option>
                              <option value="dark-grey">Dark Grey</option>
                              <option value="grey">Grey</option>
                              <option value="white">White</option>
                            </select>
                          </div>

                          {/* Logo Size */}
                          <div style={{ flex: '1 1 120px', minWidth: '100px' }}>
                            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', marginBottom: '6px', color: 'var(--text-muted)' }}>Size</label>
                            <select 
                              value={block.logoSize || 'medium'} 
                              onChange={(e) => updateBlockField(block.id, 'logoSize', e.target.value)}
                              style={{ width: '100%', padding: '6px 8px', fontSize: '0.85rem' }}
                            >
                              <option value="small">Small (S - 64px)</option>
                              <option value="medium">Medium (M - 80px)</option>
                              <option value="large">Large (L - 96px)</option>
                              <option value="xlarge">Extra Large (XL - 112px)</option>
                            </select>
                          </div>
                        </div>
                        <div className="form-group">
                          <label>Title</label>
                          <input 
                            type="text" 
                            value={block.title || ''} 
                            onChange={(e) => updateBlockField(block.id, 'title', e.target.value)} 
                            placeholder="Heading of the update"
                          />
                        </div>
                        <div className="form-group">
                          <label>Subtitle Label</label>
                          <input 
                            type="text" 
                            value={block.subtitle || ''} 
                            onChange={(e) => updateBlockField(block.id, 'subtitle', e.target.value)} 
                          />
                        </div>
                      </div>
                    )}

                    {block.type === 'paragraph' && (
                      <div className="form-group">
                        <label>Paragraph Text</label>
                        <textarea 
                          value={block.text || ''} 
                          onChange={(e) => updateBlockField(block.id, 'text', e.target.value)} 
                          placeholder="Type paragraph content..."
                        />
                      </div>
                    )}

                    {block.type === 'insights' && (
                      <div>
                        <div className="form-group">
                          <label>Insights Box Title</label>
                          <input 
                            type="text" 
                            value={block.label || ''} 
                            onChange={(e) => updateBlockField(block.id, 'label', e.target.value)} 
                          />
                        </div>
                        <div className="form-group">
                          <label>Bullet Items</label>
                          {block.items.map((item, idx) => (
                            <div key={idx} className="bullet-item-editor">
                              <input 
                                type="text" 
                                value={item} 
                                onChange={(e) => updateInsightsItem(block.id, idx, e.target.value)} 
                                placeholder={`Insight bullet ${idx + 1}`}
                              />
                              <button className="btn btn-secondary btn-icon" onClick={() => removeInsightsItem(block.id, idx)}>
                                <Trash2 size={14} />
                              </button>
                            </div>
                          ))}
                          <button className="btn btn-secondary mt-4" style={{ padding: '6px 12px', fontSize: '0.8rem' }} onClick={() => addInsightsItem(block.id)}>
                            <Plus size={12} /> Add Insight Bullet
                          </button>
                        </div>
                      </div>
                    )}

                    {block.type === 'quote' && (
                      <div>
                        <div className="form-group">
                          <label>Quote Text</label>
                          <textarea 
                            value={block.text || ''} 
                            onChange={(e) => updateBlockField(block.id, 'text', e.target.value)} 
                            placeholder="Quote text..."
                          />
                        </div>
                        <div className="form-group">
                          <label>Attribution</label>
                          <input 
                            type="text" 
                            value={block.attribution || ''} 
                            onChange={(e) => updateBlockField(block.id, 'attribution', e.target.value)} 
                            placeholder="e.g. — Trainer Name"
                          />
                        </div>
                      </div>
                    )}

                    {block.type === 'numbered_grid' && (
                      <div>
                        <label>Grid Cells</label>
                        {block.items.map((item, idx) => (
                          <div key={idx} className="grid-item-editor">
                            <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
                              <input 
                                type="text" 
                                style={{ width: '60px' }} 
                                value={item.num || ''} 
                                onChange={(e) => updateGridItem(block.id, idx, 'num', e.target.value)} 
                                placeholder="Number"
                              />
                              <input 
                                type="text" 
                                value={item.title || ''} 
                                onChange={(e) => updateGridItem(block.id, idx, 'title', e.target.value)} 
                                placeholder="Cell Title"
                              />
                              <button className="btn btn-secondary btn-icon" onClick={() => removeGridItem(block.id, idx)}>
                                <Trash2 size={14} />
                              </button>
                            </div>
                            <textarea 
                              value={item.text || ''} 
                              onChange={(e) => updateGridItem(block.id, idx, 'text', e.target.value)} 
                              placeholder="Cell Description..."
                              style={{ minHeight: '60px' }}
                            />
                          </div>
                        ))}
                        <button className="btn btn-secondary mt-4" style={{ padding: '6px 12px', fontSize: '0.8rem' }} onClick={() => addGridItem(block.id)}>
                          <Plus size={12} /> Add Grid Cell
                        </button>
                      </div>
                    )}

                     {block.type === 'box' && (
                       <div>
                         <div className="form-group">
                           <label>Section Title (Optional)</label>
                           <input 
                             type="text" 
                             value={block.title || ''} 
                             onChange={(e) => updateBlockField(block.id, 'title', e.target.value)} 
                             placeholder="e.g. The Forward Plan"
                           />
                         </div>
                         <div className="form-group">
                           <label>Section Description (Optional)</label>
                           <textarea 
                             value={block.text || ''} 
                             onChange={(e) => updateBlockField(block.id, 'text', e.target.value)} 
                             placeholder="e.g. The roadmap from here is clear..."
                             style={{ minHeight: '60px' }}
                           />
                         </div>
                         <label>Box Cards</label>
                         {block.items.map((item, idx) => (
                           <div key={idx} className="grid-item-editor" style={{ borderLeft: '3px solid var(--color-brand-gold, #d4a964)', paddingLeft: '12px', marginBottom: '16px' }}>
                             <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
                               <input 
                                 type="text" 
                                 style={{ width: '60px' }} 
                                 value={item.num || ''} 
                                 onChange={(e) => updateGridItem(block.id, idx, 'num', e.target.value)} 
                                 placeholder="Number"
                               />
                               <input 
                                 type="text" 
                                 value={item.title || ''} 
                                 onChange={(e) => updateGridItem(block.id, idx, 'title', e.target.value)} 
                                 placeholder="Box Title"
                               />
                               <button className="btn btn-secondary btn-icon" onClick={() => removeGridItem(block.id, idx)}>
                                 <Trash2 size={14} />
                               </button>
                             </div>
                             <textarea 
                               value={item.text || ''} 
                               onChange={(e) => updateGridItem(block.id, idx, 'text', e.target.value)} 
                               placeholder="Box Description..."
                               style={{ minHeight: '60px' }}
                             />
                           </div>
                         ))}
                         <button className="btn btn-secondary mt-4" style={{ padding: '6px 12px', fontSize: '0.8rem' }} onClick={() => addGridItem(block.id)}>
                           <Plus size={12} /> Add Box Card
                         </button>
                       </div>
                     )}

                    {block.type === 'hero_image' && (
                      <div>
                        <div className="form-group">
                          <label>Image URL</label>
                          <input 
                            type="text" 
                            value={block.url || ''} 
                            onChange={(e) => updateBlockField(block.id, 'url', e.target.value)} 
                            placeholder="https://..."
                          />
                        </div>
                        <div className="form-group">
                          <label>Caption</label>
                          <input 
                            type="text" 
                            value={block.caption || ''} 
                            onChange={(e) => updateBlockField(block.id, 'caption', e.target.value)} 
                            placeholder="Image label / pedigree description"
                          />
                        </div>
                      </div>
                    )}

                    {block.type === 'footer' && (
                      <div>
                        <div className="form-group">
                          <label>Footer Headline</label>
                          <input 
                            type="text" 
                            value={block.title || ''} 
                            onChange={(e) => updateBlockField(block.id, 'title', e.target.value)} 
                          />
                        </div>
                        <div className="form-group">
                          <label>Footer Small Label</label>
                          <input 
                            type="text" 
                            value={block.subtitle || ''} 
                            onChange={(e) => updateBlockField(block.id, 'subtitle', e.target.value)} 
                          />
                        </div>
                      </div>
                    )}

                  </div>
                );
              })}

              {/* ADD BLOCK ROW */}
              <div style={{ 
                border: '1px dashed var(--border-editor)', 
                borderRadius: 'var(--radius-md)', 
                padding: 'var(--space-4)', 
                textAlign: 'center', 
                backgroundColor: 'var(--surface-editor)',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
                marginTop: '12px'
              }}>
                <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Insert Custom Block
                </div>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', justifyContent: 'center' }}>
                  <button className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.8rem' }} onClick={() => addEmptyBlock('header')}>
                    + Header
                  </button>
                  <button className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.8rem' }} onClick={() => addEmptyBlock('paragraph')}>
                    + Paragraph
                  </button>
                  <button className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.8rem' }} onClick={() => addEmptyBlock('insights')}>
                    + Insights Box
                  </button>
                  <button className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.8rem' }} onClick={() => addEmptyBlock('quote')}>
                    + Quote
                  </button>
                  <button className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.8rem' }} onClick={() => addEmptyBlock('numbered_grid')}>
                    + Grid
                  </button>
                  <button className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.8rem' }} onClick={() => addEmptyBlock('box')}>
                    + Box Section
                  </button>
                  <button className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.8rem' }} onClick={() => addEmptyBlock('hero_image')}>
                    + Hero Image
                  </button>
                  <button className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.8rem' }} onClick={() => addEmptyBlock('footer')}>
                    + Footer
                  </button>
                </div>
              </div>
            </>
          )}
        </section>

        {/* LIVE PREVIEW (IFRAME CANVAS) */}
        <section className="preview-panel">
          <div className="preview-header">
            <span className="block-badge" style={{ color: 'var(--text-muted)' }}>
              <Eye size={12} /> Live Preview
            </span>
            <div className="preview-actions">
              <button 
                className={`btn ${previewMode === 'web' ? 'btn-primary' : 'btn-secondary'}`} 
                onClick={() => setPreviewMode('web')}
                style={{ padding: '6px 12px', fontSize: '0.8rem' }}
              >
                <FileText size={14} /> Web
              </button>
              <button 
                className={`btn ${previewMode === 'teaser' ? 'btn-primary' : 'btn-secondary'}`} 
                onClick={() => setPreviewMode('teaser')}
                style={{ padding: '6px 12px', fontSize: '0.8rem' }}
              >
                <Mail size={14} /> Teaser
              </button>
            </div>
          </div>

          <div className="preview-content">
            <iframe 
              className="email-canvas"
              title="Investor Update Rendering"
              srcDoc={previewMode === 'web' ? renderWeb(blocks, tokens) : renderTeaser(blocks, tokens)}
            />
          </div>
        </section>

      </main>

      {/* PASTE RAW TEXT MODAL */}
      {showPasteModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3 className="modal-title">Paste Raw Investor Update</h3>
              <button className="btn-icon" onClick={() => setShowPasteModal(false)}>
                <X size={18} />
              </button>
            </div>
            <textarea
              className="raw-textarea"
              placeholder="Paste raw update copy from email or chat... (like First Gear context)"
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
            />
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <button className="btn btn-secondary" onClick={() => setShowPasteModal(false)}>Cancel</button>
              <button className="btn btn-primary" onClick={() => handleRawTextImport(rawText)}>Parse & Import</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default App;
