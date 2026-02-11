import { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';

interface MermaidDiagramProps {
  chart: string;
}

// Initialize mermaid with dark theme
mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  themeVariables: {
    primaryColor: '#03a9f4',
    primaryTextColor: '#e1e1e1',
    primaryBorderColor: '#03a9f4',
    lineColor: '#03a9f4',
    secondaryColor: '#4caf50',
    tertiaryColor: '#9b9b9b',
    background: 'transparent',
    mainBkg: 'rgba(3,169,244,0.1)',
    secondBkg: 'rgba(76,175,80,0.1)',
    tertiaryBkg: 'rgba(158,158,158,0.1)',
    fontFamily: 'inherit',
  },
});

export function MermaidDiagram({ chart }: MermaidDiagramProps) {
  const [svg, setSvg] = useState<string>('');
  const [error, setError] = useState<string>('');

  useEffect(() => {
    const renderDiagram = async () => {
      try {
        const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`;
        const { svg } = await mermaid.render(id, chart.trim());
        setSvg(svg);
        setError('');
      } catch (err) {
        console.error('Mermaid rendering error:', err);
        setError(err instanceof Error ? err.message : 'Failed to render diagram');
      }
    };

    renderDiagram();
  }, [chart]);

  if (error) {
    return (
      <div style={{
        padding: '16px',
        color: 'var(--error-color, #db4437)',
        fontSize: '12px',
        textAlign: 'center'
      }}>
        Failed to render diagram: {error}
      </div>
    );
  }

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        padding: '16px',
        overflow: 'auto',
      }}
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
